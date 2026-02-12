#!/usr/bin/env python3
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time

from geometry_msgs.msg import PoseWithCovarianceStamped
from as2_swarm_person_interfaces.msg import TrackedPersonArray


# -------------------- Utils --------------------

def _sym(P: np.ndarray) -> np.ndarray:
    return 0.5 * (P + P.T)


def _ensure_spd(P: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """Make P symmetric positive definite (robust for inversions)."""
    P = _sym(P)
    e = eps
    for _ in range(6):
        try:
            np.linalg.cholesky(P + e * np.eye(P.shape[0]))
            return P + e * np.eye(P.shape[0])
        except np.linalg.LinAlgError:
            e *= 10.0
    return P + e * np.eye(P.shape[0])


def cov2_from_pose_cov(cov36: List[float]) -> np.ndarray:
    # PoseWithCovariance: cov[0]=xx, cov[1]=xy, cov[6]=yx, cov[7]=yy
    xx = float(cov36[0])
    xy = float(cov36[1])
    yx = float(cov36[6])
    yy = float(cov36[7])
    P = np.array([[xx, xy],
                  [yx, yy]], dtype=float)
    return _ensure_spd(P)


def pose_msg_from_state(x: np.ndarray, P: np.ndarray, stamp_msg, frame_id: str) -> PoseWithCovarianceStamped:
    out = PoseWithCovarianceStamped()
    out.header.stamp = stamp_msg
    out.header.frame_id = frame_id

    out.pose.pose.position.x = float(x[0])
    out.pose.pose.position.y = float(x[1])
    out.pose.pose.position.z = 0.0
    out.pose.pose.orientation.w = 1.0

    out.pose.covariance = [0.0] * 36
    out.pose.covariance[0] = float(P[0, 0])
    out.pose.covariance[1] = float(P[0, 1])
    out.pose.covariance[6] = float(P[1, 0])
    out.pose.covariance[7] = float(P[1, 1])
    return out


def maha_d2(y: np.ndarray, S: np.ndarray) -> float:
    S = _ensure_spd(S)
    try:
        invS = np.linalg.inv(S)
    except np.linalg.LinAlgError:
        invS = np.linalg.pinv(S)
    return float(y.reshape(1, 2) @ invS @ y.reshape(2, 1))


def quality_trace(P: np.ndarray) -> float:
    return float(np.trace(_ensure_spd(P)))


def _fmt_P(P: np.ndarray) -> str:
    P = _sym(P)
    return f"[[{P[0,0]:.3f},{P[0,1]:.3f}],[{P[1,0]:.3f},{P[1,1]:.3f}]]"


# -------------------- EKF per-ID state --------------------

class EKFState:
    def __init__(self, x: np.ndarray, P: np.ndarray, t_last: Time):
        self.x = x.astype(float).reshape(2,)
        self.P = _ensure_spd(P)
        self.t_last = t_last
        self.last_pub_ref_stamp_ns: Optional[int] = None


# -------------------- Node --------------------

class DistributedEKFPeopleNode(Node):
    """
    Multi-person Distributed EKF (per global ID).

    Consumes:
      /swarm/<droneX>/people_with_global_id   (TrackedPersonArray)
        - Each element contains:
            id (global)
            source (drone name)
            pose (PoseWithCovariance)

    Produces (per drone, per ID):
      <publish_prefix>/id_<ID>   (PoseWithCovarianceStamped)
        Example publish_prefix: /swarm/drone0/ekf_people
        => /swarm/drone0/ekf_people/id_1
    """

    def __init__(self):
        super().__init__("distributed_ekf_people_node")

        # ---------- Params ----------
        self.declare_parameter("self_drone", "drone0")
        self.declare_parameter("drones", ["drone0", "drone1", "drone2"])
        self.declare_parameter("in_topic_suffix", "people_with_global_id")

        self.declare_parameter("world_frame", "earth")
        self.declare_parameter("publish_prefix", "/swarm/drone0/ekf_people")

        # EKF model (random-walk on position)
        self.declare_parameter("q_sigma", 0.25)              # [m/sqrt(s)] process noise intensity
        self.declare_parameter("external_R_inflate", 5.0)    # multiply R for other drones' measurements

        # Temporal selection
        self.declare_parameter("max_age_sec", 3.0)
        self.declare_parameter("time_window_sec", 1.0)
        self.declare_parameter("min_sources", 1)
        self.declare_parameter("publish_hz", 20.0)
        self.declare_parameter("publish_only_on_new_ref", True)

        # Gating
        self.declare_parameter("use_gating", True)
        self.declare_parameter("gate_chi2", 5.99)  # ~95% in 2D

        # Housekeeping
        self.declare_parameter("track_timeout_sec", 5.0)  # remove EKFState if not seen for a while

        # Debug
        self.declare_parameter("debug", True)
        self.declare_parameter("debug_throttle_sec", 1.0)

        self.self_drone = str(self.get_parameter("self_drone").value)
        self.drones: List[str] = list(self.get_parameter("drones").value)
        self.in_topic_suffix = str(self.get_parameter("in_topic_suffix").value)

        self.world_frame = str(self.get_parameter("world_frame").value)
        self.publish_prefix = str(self.get_parameter("publish_prefix").value).rstrip("/")

        self.q_sigma = float(self.get_parameter("q_sigma").value)
        self.external_R_inflate = float(self.get_parameter("external_R_inflate").value)

        self.max_age_sec = float(self.get_parameter("max_age_sec").value)
        self.time_window_sec = float(self.get_parameter("time_window_sec").value)
        self.min_sources = int(self.get_parameter("min_sources").value)
        self.publish_hz = float(self.get_parameter("publish_hz").value)
        self.publish_only_on_new_ref = bool(self.get_parameter("publish_only_on_new_ref").value)

        self.use_gating = bool(self.get_parameter("use_gating").value)
        self.gate_chi2 = float(self.get_parameter("gate_chi2").value)

        self.track_timeout_sec = float(self.get_parameter("track_timeout_sec").value)

        self.debug = bool(self.get_parameter("debug").value)
        self.debug_throttle_sec = float(self.get_parameter("debug_throttle_sec").value)
        self._last_debug_log_time = 0.0

        # ---------- Buffers ----------
        # last_obs[id][drone] = (z(2,), R(2x2), stamp(Time))
        self.last_obs: Dict[int, Dict[str, Tuple[np.ndarray, np.ndarray, Time]]] = {}

        # EKF states per ID
        self.ekf: Dict[int, EKFState] = {}

        # last seen wall-time per ID for cleanup
        self.id_last_seen_wall: Dict[int, float] = {}

        # Publishers per ID (PoseWithCovarianceStamped)
        self.pub_by_id: Dict[int, any] = {}

        # ---------- Subscriptions ----------
        self.subs = []
        for d in self.drones:
            topic = f"/swarm/{d}/{self.in_topic_suffix}"
            sub = self.create_subscription(
                TrackedPersonArray,
                topic,
                lambda msg, drone=d: self.cb(msg, drone),
                qos_profile_sensor_data,
            )
            self.subs.append(sub)
            self.get_logger().info(f"Subscrito a: {topic}")

        # ---------- Timer ----------
        period = 1.0 / max(1e-3, self.publish_hz)
        self.timer = self.create_timer(period, self.tick)

        self._pub_count = 0
        self.get_logger().info(
            "Distributed EKF PEOPLE listo. "
            f"self={self.self_drone} publish_prefix={self.publish_prefix} "
            f"q_sigma={self.q_sigma:.3f} ext_R_inflate={self.external_R_inflate:.2f} "
            f"max_age={self.max_age_sec:.2f}s window={self.time_window_sec:.2f}s "
            f"min_sources={self.min_sources} publish_hz={self.publish_hz:.1f}"
        )

    # ---------- Logging helper ----------
    def _throttled_info(self, text: str):
        if not self.debug:
            return
        now_sec = self.get_clock().now().nanoseconds * 1e-9
        if (now_sec - self._last_debug_log_time) >= self.debug_throttle_sec:
            self._last_debug_log_time = now_sec
            self.get_logger().info(text)

    # ---------- Callback ----------
    def cb(self, msg: TrackedPersonArray, drone: str):
        now_wall = self.get_clock().now().nanoseconds * 1e-9
        for tp in msg.persons:
            pid = int(tp.id)
            # stamp: prefer tp.header.stamp; fallback to array header stamp
            stamp_msg = tp.header.stamp if (tp.header.stamp.sec or tp.header.stamp.nanosec) else msg.header.stamp
            t = Time.from_msg(stamp_msg)

            z = np.array([tp.pose.pose.position.x, tp.pose.pose.position.y], dtype=float)
            R = cov2_from_pose_cov(list(tp.pose.covariance))

            if pid not in self.last_obs:
                self.last_obs[pid] = {}
            self.last_obs[pid][drone] = (z, R, t)

            self.id_last_seen_wall[pid] = now_wall

            if self.debug:
                self._throttled_info(
                    f"RX id={pid} {drone} stamp={t.nanoseconds*1e-9:.3f}s "
                    f"pos=({z[0]:.2f},{z[1]:.2f}) trR={np.trace(R):.3f}"
                )

    # ---------- Selection for one ID ----------
    def _collect_valid_for_id(self, pid: int) -> List[Tuple[str, np.ndarray, np.ndarray, Time, float]]:
        """
        Returns list of (drone, z, R, stamp, age) for this pid:
        - not stale (age <= max_age_sec)
        - stamp within time_window_sec of newest stamp among fresh
        """
        now = self.get_clock().now()

        if pid not in self.last_obs:
            return []

        fresh: List[Tuple[str, np.ndarray, np.ndarray, Time, float]] = []
        for d, (z, R, t) in self.last_obs[pid].items():
            age = (now - t).nanoseconds * 1e-9
            if age <= self.max_age_sec:
                fresh.append((d, z, R, t, age))

        if not fresh:
            return []

        # Newest stamp reference
        t_ref = max(fresh, key=lambda e: e[3].nanoseconds)[3]
        ref_ns = t_ref.nanoseconds
        ref_sec = ref_ns * 1e-9

        selected: List[Tuple[str, np.ndarray, np.ndarray, Time, float]] = []
        for (d, z, R, t, age) in fresh:
            dt_stamp = abs((t.nanoseconds - ref_ns) * 1e-9)
            if dt_stamp <= self.time_window_sec:
                selected.append((d, z, R, t, age))

        selected.sort(key=lambda e: e[3].nanoseconds)

        if self.debug and selected:
            self._throttled_info(
                f"[id={pid}] selected=" +
                str([(d, round((t.nanoseconds - ref_ns)*1e-9, 3)) for d, _, _, t, _ in selected]) +
                f" (ref_stamp={ref_sec:.3f}s)"
            )

        return selected

    # ---------- EKF core ----------
    def _predict(self, st: EKFState, t_to: Time):
        dt = (t_to - st.t_last).nanoseconds * 1e-9
        if dt <= 0.0:
            return
        # Random walk on position: x = x + w, P = P + Q*dt
        q2 = (self.q_sigma ** 2) * max(dt, 0.0)
        st.P = _ensure_spd(st.P + q2 * np.eye(2))
        st.t_last = t_to

    def _update(self, st: EKFState, z: np.ndarray, R: np.ndarray) -> Tuple[bool, float]:
        R = _ensure_spd(R)
        y = (z - st.x).reshape(2,)

        S = _ensure_spd(st.P + R)
        d2 = maha_d2(y, S)

        if self.use_gating and (d2 > self.gate_chi2):
            return False, d2

        # Kalman update (H=I)
        try:
            invS = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            invS = np.linalg.pinv(S)

        K = st.P @ invS
        st.x = st.x + (K @ y)
        I = np.eye(2)
        st.P = _ensure_spd((I - K) @ st.P)
        return True, d2

    # ---------- Publisher per ID ----------
    def _get_pub(self, pid: int):
        if pid in self.pub_by_id:
            return self.pub_by_id[pid]
        topic = f"{self.publish_prefix}/id_{pid}"
        pub = self.create_publisher(PoseWithCovarianceStamped, topic, 10)
        self.pub_by_id[pid] = pub
        self.get_logger().info(f"Publishing EKF for id={pid} on: {topic}")
        return pub

    # ---------- Cleanup ----------
    def _cleanup(self):
        now_wall = self.get_clock().now().nanoseconds * 1e-9
        to_del = []
        for pid, t_last in self.id_last_seen_wall.items():
            if (now_wall - t_last) > self.track_timeout_sec:
                to_del.append(pid)

        for pid in to_del:
            self.id_last_seen_wall.pop(pid, None)
            self.last_obs.pop(pid, None)
            self.ekf.pop(pid, None)
            # keep publishers (cheap), or remove if you want:
            # self.pub_by_id.pop(pid, None)
            if self.debug:
                self.get_logger().info(f"[id={pid}] removed (timeout {self.track_timeout_sec:.1f}s)")

    # ---------- Tick ----------
    def tick(self):
        # housekeeping
        self._cleanup()

        # iterate all active IDs
        ids = sorted(self.last_obs.keys())
        if not ids:
            return

        for pid in ids:
            entries = self._collect_valid_for_id(pid)
            if len(entries) < self.min_sources:
                continue

            # reference time = newest stamp among selected
            ref_t = max(entries, key=lambda e: e[3].nanoseconds)[3]
            ref_ns = ref_t.nanoseconds

            # If publish_only_on_new_ref and we already published at this ref stamp, skip
            st = self.ekf.get(pid, None)
            if st is not None and self.publish_only_on_new_ref and st.last_pub_ref_stamp_ns == ref_ns:
                continue

            # Sort measurements by quality (smaller trace(R) first)
            def meas_quality(e):
                _, _, R, _, _ = e
                return quality_trace(R)

            entries_sorted = sorted(entries, key=meas_quality)

            # Initialize EKF if needed using best measurement
            if st is None:
                d0, z0, R0, t0, _ = entries_sorted[0]
                # Inflate if source is not self
                R0_eff = R0 * (self.external_R_inflate if d0 != self.self_drone else 1.0)
                st = EKFState(x=z0.copy(), P=R0_eff.copy(), t_last=t0)
                self.ekf[pid] = st
                if self.debug:
                    self.get_logger().info(
                        f"[ID {pid}] INIT from {d0}: x=({st.x[0]:.2f},{st.x[1]:.2f}) P={_fmt_P(st.P)}"
                    )

            # Predict up to ref_t
            self._predict(st, ref_t)

            # Sequential updates
            used = []
            rejected = []
            inputs_lines = []
            for (d, z, R, t, _) in entries_sorted:
                R_eff = R * (self.external_R_inflate if d != self.self_drone else 1.0)
                dt_i = (t.nanoseconds - ref_ns) * 1e-9
                inputs_lines.append(
                    f"  - {d}: dt={dt_i:+.3f}s pos=({z[0]:.2f},{z[1]:.2f}) R={_fmt_P(R_eff)}"
                )

                ok, d2 = self._update(st, z, R_eff)
                if ok:
                    used.append(d)
                else:
                    rejected.append((d, d2))

            if len(used) < self.min_sources:
                if self.debug:
                    rej_str = ", ".join([f"{d}(d2={d2:.2f})" for d, d2 in rejected]) if rejected else "[]"
                    self._throttled_info(f"[ID {pid}] not enough after gating: used={len(used)} rejected={rej_str}")
                continue

            # Publish
            pub = self._get_pub(pid)
            out_stamp = ref_t.to_msg()
            out = pose_msg_from_state(st.x, _sym(st.P), out_stamp, self.world_frame)
            pub.publish(out)

            st.last_pub_ref_stamp_ns = ref_ns
            self._pub_count += 1

            # Debug log (similar style to your CI logs)
            if self.debug:
                rej_str = ", ".join([f"{d}(d2={d2:.2f})" for d, d2 in rejected]) if rejected else "[]"
                self.get_logger().info(
                    f"[ID {pid}] EKF PUBLISHED #{self._pub_count}: used={len(used)}/{len(entries_sorted)} "
                    f"used_list={used}\n"
                    f"inputs:\n" + "\n".join(inputs_lines) + "\n"
                    f"fused: ({st.x[0]:.2f},{st.x[1]:.2f})  P={_fmt_P(_sym(st.P))}  rejected={rej_str}"
                )


def main(args=None):
    rclpy.init(args=args)
    node = DistributedEKFPeopleNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

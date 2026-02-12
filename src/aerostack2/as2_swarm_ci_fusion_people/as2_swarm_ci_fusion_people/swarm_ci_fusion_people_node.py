#!/usr/bin/env python3
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped

from as2_swarm_person_interfaces.msg import TrackedPerson, TrackedPersonArray


# -------------------- Utils (muy parecido a tu nodo 1-persona) --------------------

def parse_drones_csv(s: str) -> List[str]:
    return [d.strip().strip('/') for d in s.split(',') if d.strip()]


def cov2_from_tracked_person(tp: TrackedPerson) -> np.ndarray:
    c = tp.pose.covariance
    P = np.array([[c[0], c[1]],
                  [c[6], c[7]]], dtype=float)
    return P


def pose_from_state(
    x: np.ndarray,
    P: np.ndarray,
    stamp_msg,
    frame_id: str
) -> PoseWithCovarianceStamped:
    msg = PoseWithCovarianceStamped()
    msg.header.stamp = stamp_msg
    msg.header.frame_id = frame_id

    msg.pose.pose.position.x = float(x[0])
    msg.pose.pose.position.y = float(x[1])
    msg.pose.pose.position.z = 0.0
    msg.pose.pose.orientation.w = 1.0

    msg.pose.covariance = [0.0] * 36
    msg.pose.covariance[0] = float(P[0, 0])
    msg.pose.covariance[1] = float(P[0, 1])
    msg.pose.covariance[6] = float(P[1, 0])
    msg.pose.covariance[7] = float(P[1, 1])
    return msg


def _symmetrize(P: np.ndarray) -> np.ndarray:
    return 0.5 * (P + P.T)


def _ensure_spd(P: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    P = _symmetrize(P)
    e = eps
    for _ in range(6):
        try:
            np.linalg.cholesky(P + e * np.eye(P.shape[0]))
            return P + e * np.eye(P.shape[0])
        except np.linalg.LinAlgError:
            e *= 10.0
    return P + e * np.eye(P.shape[0])


def _logdet_spd(P: np.ndarray) -> float:
    sign, ld = np.linalg.slogdet(P)
    if sign <= 0:
        return float("inf")
    return float(ld)


def maha_d2(x1: np.ndarray, P1: np.ndarray, x2: np.ndarray, P2: np.ndarray) -> float:
    r = (x1 - x2).reshape(2, 1)
    S = _ensure_spd(P1) + _ensure_spd(P2)
    try:
        invS = np.linalg.inv(S)
    except np.linalg.LinAlgError:
        invS = np.linalg.pinv(S)
    return float((r.T @ invS @ r)[0, 0])


def _fmt_P(P: np.ndarray) -> str:
    return f"[[{P[0,0]:.3f},{P[0,1]:.3f}],[{P[1,0]:.3f},{P[1,1]:.3f}]]"


def covariance_intersection_pair(
    x1: np.ndarray,
    P1: np.ndarray,
    x2: np.ndarray,
    P2: np.ndarray,
    criterion: str = "logdet",
    max_iter: int = 40,
) -> Tuple[np.ndarray, np.ndarray, float]:
    P1 = _ensure_spd(P1)
    P2 = _ensure_spd(P2)

    invP1 = np.linalg.inv(P1)
    invP2 = np.linalg.inv(P2)

    def fused_cov(w: float) -> np.ndarray:
        invPf = w * invP1 + (1.0 - w) * invP2
        return np.linalg.inv(invPf)

    def objective(w: float) -> float:
        Pf = fused_cov(w)
        if criterion == "trace":
            return float(np.trace(Pf))
        return _logdet_spd(Pf)

    # golden-section en [0,1]
    a, b = 0.0, 1.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c = b - gr * (b - a)
    d = a + gr * (b - a)
    fc = objective(c)
    fd = objective(d)

    for _ in range(max_iter):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - gr * (b - a)
            fc = objective(c)
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b - a)
            fd = objective(d)

    w_opt = 0.5 * (a + b)

    invP_final = w_opt * invP1 + (1.0 - w_opt) * invP2
    P_final = np.linalg.inv(invP_final)
    x_final = P_final @ (w_opt * invP1 @ x1 + (1.0 - w_opt) * invP2 @ x2)

    return x_final, _symmetrize(P_final), float(w_opt)


# -------------------- Nodo CI Multi-Persona --------------------

class SwarmCIFusionPeopleAsync(Node):
    """
    Multi-person CI Fusion ASYNC:
    - Guarda el último TrackedPerson (por drone, por id)
    - Para cada id, en cada tick:
        * filtra por edad (max_age_sec)
        * filtra por simultaneidad (time_window_sec) usando stamps de header
        * aplica Mahalanobis gating
        * fusiona con CI secuencial
    - Publica:
        * TrackedPersonArray en /swarm/people_ci_fused
        * PoseWithCovarianceStamped por persona en /swarm/people_ci_fused/id_<ID>
    """

    def __init__(self):
        super().__init__("swarm_ci_fusion_people_async")

        # -------- Params --------
        self.declare_parameter("drones", "drone0,drone1,drone2")
        self.declare_parameter("in_topic_suffix", "people_with_global_id")  # /swarm/<drone>/<suffix>
        self.declare_parameter("out_array_topic", "/swarm/people_ci_fused")
        self.declare_parameter("out_topic_prefix", "/swarm/people_ci_fused")  # + "/id_<id>"
        self.declare_parameter("world_frame", "earth")

        self.declare_parameter("max_age_sec", 20.0)
        self.declare_parameter("time_window_sec", 0.75)
        self.declare_parameter("min_sources", 2)

        self.declare_parameter("criterion", "logdet")  # logdet / trace
        self.declare_parameter("publish_hz", 20.0)

        self.declare_parameter("maha_gate_chi2", 5.99)  # ~95% en 2D
        self.declare_parameter("publish_only_on_new_ref", True)

        # Debug
        self.declare_parameter("debug", True)
        self.declare_parameter("debug_throttle_sec", 1.0)

        # -------- Load params --------
        self.drones: List[str] = parse_drones_csv(str(self.get_parameter("drones").value))
        self.in_topic_suffix = str(self.get_parameter("in_topic_suffix").value)
        self.out_array_topic = str(self.get_parameter("out_array_topic").value)
        self.out_topic_prefix = str(self.get_parameter("out_topic_prefix").value)
        self.world_frame = str(self.get_parameter("world_frame").value)

        self.max_age_sec = float(self.get_parameter("max_age_sec").value)
        self.time_window_sec = float(self.get_parameter("time_window_sec").value)
        self.min_sources = int(self.get_parameter("min_sources").value)
        self.criterion = str(self.get_parameter("criterion").value).lower().strip()

        self.maha_gate_chi2 = float(self.get_parameter("maha_gate_chi2").value)
        self.publish_only_on_new_ref = bool(self.get_parameter("publish_only_on_new_ref").value)

        self.publish_hz = float(self.get_parameter("publish_hz").value)
        self.debug = bool(self.get_parameter("debug").value)
        self.debug_throttle_sec = float(self.get_parameter("debug_throttle_sec").value)
        self._last_debug_log_time = 0.0

        # Para evitar publicar lo mismo si no cambia la ref stamp (por ID)
        self._last_pub_ref_stamp_ns_by_id: Dict[int, int] = {}

        # last_msg[id][drone] = (TrackedPerson, stamp_time)
        self.last_msg: Dict[int, Dict[str, Tuple[TrackedPerson, rclpy.time.Time]]] = {}

        # Publishers dinámicos por ID: id -> pub PoseWithCovarianceStamped
        self.pub_pose_by_id: Dict[int, any] = {}

        # -------- Subs --------
        self.subs = []
        for d in self.drones:
            topic = f"/swarm/{d}/{self.in_topic_suffix}"
            sub = self.create_subscription(
                TrackedPersonArray,
                topic,
                lambda msg, drone=d: self.cb(msg, drone),
                10,
            )
            self.subs.append(sub)
            self.get_logger().info(f"Subscrito a: {topic}")

        # -------- Pub --------
        self.pub_array = self.create_publisher(TrackedPersonArray, self.out_array_topic, 10)
        self.get_logger().info(f"Publicando fusion (array) en: {self.out_array_topic}")
        self.get_logger().info(f"Publicando fusion (por ID) en: {self.out_topic_prefix}/id_<ID>")

        period = 1.0 / max(1e-3, self.publish_hz)
        self.timer = self.create_timer(period, self.tick)

        self._pub_count = 0
        self.get_logger().info(
            "Swarm CI Fusion PEOPLE ASYNC listo. "
            f"max_age_sec={self.max_age_sec:.2f}s time_window_sec={self.time_window_sec:.2f}s "
            f"min_sources={self.min_sources} criterion={self.criterion} publish_hz={self.publish_hz:.1f}"
        )

    def _throttled_info(self, text: str):
        if not self.debug:
            return
        now_sec = self.get_clock().now().nanoseconds * 1e-9
        if (now_sec - self._last_debug_log_time) >= self.debug_throttle_sec:
            self._last_debug_log_time = now_sec
            self.get_logger().info(text)

    def _get_pub_for_id(self, pid: int):
        pub = self.pub_pose_by_id.get(pid)
        if pub is None:
            topic = f"{self.out_topic_prefix}/id_{pid}"
            pub = self.create_publisher(PoseWithCovarianceStamped, topic, 10)
            self.pub_pose_by_id[pid] = pub
            self.get_logger().info(f"[CI] Created per-ID publisher: {topic}")
        return pub

    def cb(self, msg: TrackedPersonArray, drone: str):
        # guardamos última obs por (id, drone) usando stamp del header del TrackedPerson
        for tp in msg.persons:
            pid = int(tp.id)
            t = rclpy.time.Time.from_msg(tp.header.stamp)

            if pid not in self.last_msg:
                self.last_msg[pid] = {}
            self.last_msg[pid][drone] = (tp, t)

            if self.debug:
                P = _ensure_spd(cov2_from_tracked_person(tp))
                self._throttled_info(
                    f"RX id={pid} {drone} stamp={t.nanoseconds*1e-9:.3f}s "
                    f"pos=({tp.pose.pose.position.x:.2f},{tp.pose.pose.position.y:.2f}) "
                    f"Pxx={P[0,0]:.3f} Pyy={P[1,1]:.3f}"
                )

    def _collect_valid_for_id(self, pid: int) -> List[Tuple[str, TrackedPerson, rclpy.time.Time, float]]:
        """
        Devuelve tracks para ese id:
          - no-stale por max_age
          - dentro de ventana temporal respecto al stamp más nuevo disponible
        """
        now = self.get_clock().now()

        per_drone = self.last_msg.get(pid, {})
        if not per_drone:
            return []

        # 1) filtra por edad
        fresh = []
        for d, item in per_drone.items():
            tp, t = item
            age = (now - t).nanoseconds * 1e-9
            if age <= self.max_age_sec:
                fresh.append((d, tp, t, age))

        if not fresh:
            return []

        # 2) referencia: stamp más nuevo
        t_ref = max(fresh, key=lambda e: e[2].nanoseconds)[2]
        ref_sec = t_ref.nanoseconds * 1e-9

        # 3) filtra por simultaneidad
        selected = []
        for (d, tp, t, age) in fresh:
            dt_stamp = abs((t.nanoseconds - t_ref.nanoseconds) * 1e-9)
            if dt_stamp <= self.time_window_sec:
                selected.append((d, tp, t, age))

        selected.sort(key=lambda e: e[2].nanoseconds)

        # log corto
        self._throttled_info(
            f"[id={pid}] selected={[(d, round((t.nanoseconds*1e-9)-ref_sec,3)) for d,_,t,_ in selected]} "
            f"(ref_stamp={ref_sec:.3f}s)"
        )
        return selected

    def tick(self):
        # Publica un array con todos los IDs fusionados en este tick
        fused_array = TrackedPersonArray()
        fused_array.header.stamp = self.get_clock().now().to_msg()
        fused_array.header.frame_id = self.world_frame

        # Itera IDs activos
        for pid in list(self.last_msg.keys()):
            entries = self._collect_valid_for_id(pid)
            if len(entries) < self.min_sources:
                continue

            # Referencia: stamp más nuevo
            ref_t = max(entries, key=lambda e: e[2].nanoseconds)[2]
            ref_ns = ref_t.nanoseconds

            if self.publish_only_on_new_ref:
                last_ref = self._last_pub_ref_stamp_ns_by_id.get(pid)
                if last_ref == ref_ns:
                    continue

            # Ordena por calidad (logdet P)
            def quality(e):
                _, tp, _, _ = e
                P = _ensure_spd(cov2_from_tracked_person(tp))
                return _logdet_spd(P)

            entries.sort(key=quality)

            # inputs para log
            inputs_for_log = []
            for (d, tp, t, _) in entries:
                x_i = float(tp.pose.pose.position.x)
                y_i = float(tp.pose.pose.position.y)
                P_i = _ensure_spd(cov2_from_tracked_person(tp))
                dt_i = (t.nanoseconds - ref_ns) * 1e-9
                inputs_for_log.append((d, dt_i, x_i, y_i, P_i))

            # seed
            d0, tp0, t0, _ = entries[0]
            x = np.array([tp0.pose.pose.position.x, tp0.pose.pose.position.y], dtype=float)
            P = _ensure_spd(cov2_from_tracked_person(tp0))

            used = [(d0, t0.nanoseconds)]
            rejected = []
            pair_w = []

            alphas = {d0: 1.0}
            seed = d0

            # fusion secuencial
            for (d, tp, t, _) in entries[1:]:
                x2 = np.array([tp.pose.pose.position.x, tp.pose.pose.position.y], dtype=float)
                P2 = _ensure_spd(cov2_from_tracked_person(tp))

                d2 = maha_d2(x, P, x2, P2)
                if d2 > self.maha_gate_chi2:
                    rejected.append((d, d2))
                    continue

                x, P, w = covariance_intersection_pair(x, P, x2, P2, criterion=self.criterion)
                pair_w.append((d, w))

                for k in list(alphas.keys()):
                    alphas[k] *= w
                alphas[d] = 1.0 - w

                used.append((d, t.nanoseconds))

            if len(used) < self.min_sources:
                continue

            # publicar por ID: PoseWithCovarianceStamped
            stamp_sec = ref_ns * 1e-9
            out_stamp = rclpy.time.Time(seconds=stamp_sec).to_msg()
            pose_msg = pose_from_state(x, _symmetrize(P), out_stamp, self.world_frame)
            self._get_pub_for_id(pid).publish(pose_msg)

            # publicar en array como TrackedPerson
            tp_out = TrackedPerson()
            tp_out.header = fused_array.header
            tp_out.id = int(pid)
            tp_out.source = ""  # fused
            tp_out.pose.pose.position.x = float(x[0])
            tp_out.pose.pose.position.y = float(x[1])
            tp_out.pose.pose.position.z = 0.0
            tp_out.pose.pose.orientation.w = 1.0
            tp_out.pose.covariance = pose_msg.pose.covariance
            tp_out.confidence = 1.0
            fused_array.persons.append(tp_out)

            self._last_pub_ref_stamp_ns_by_id[pid] = ref_ns
            self._pub_count += 1

            # log completo estilo tu nodo 1-persona (por ID)
            if self.debug:
                dt_span = (max(ns for _, ns in used) - min(ns for _, ns in used)) * 1e-9

                s = sum(alphas.values()) if len(alphas) > 0 else 1.0
                alphas_norm = [(d, alphas[d] / s) for d, _ in used if d in alphas]
                alphas_norm.sort(key=lambda kv: kv[1], reverse=True)

                inputs_lines = []
                for (d, dt_i, x_i, y_i, P_i) in inputs_for_log:
                    inputs_lines.append(
                        f"  - {d}: dt={dt_i:+.3f}s  pos=({x_i:.2f},{y_i:.2f})  P={_fmt_P(P_i)}"
                    )

                pair_lines = []
                for (d, w) in pair_w:
                    pair_lines.append(f"  - fuse+{d}: w_prev={w:.2f}  w_new={1.0-w:.2f}")

                wfinal_str = ", ".join([f"{d}:{w:.2f}" for d, w in alphas_norm])
                used_names = [d for d, _ in used]
                rej_str = ", ".join([f"{d}(d2={d2:.2f})" for d, d2 in rejected]) if rejected else "[]"

                self.get_logger().info(
                    f"[ID {pid}] PUBLISHED #{self._pub_count}: seed={seed} used={len(used)}/{len(entries)} "
                    f"used_list={used_names} dt_span={dt_span:.3f}s\n"
                    f"inputs:\n" + "\n".join(inputs_lines) + "\n"
                    f"pairwise_w:\n" + ("\n".join(pair_lines) if pair_lines else "  - (no pair fusions)") + "\n"
                    f"w_final(norm): {wfinal_str}\n"
                    f"fused: ({x[0]:.2f},{x[1]:.2f})  P={_fmt_P(_symmetrize(P))}  rejected={rej_str}"
                )

        # publica el array (aunque venga vacío, no hace daño; si prefieres, puedes condicionar)
        self.pub_array.publish(fused_array)


def main(args=None):
    rclpy.init(args=args)
    node = SwarmCIFusionPeopleAsync()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

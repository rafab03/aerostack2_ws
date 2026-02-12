#!/usr/bin/env python3
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseWithCovarianceStamped


# ---------------- Utils ----------------

def cov2_from_pose(msg):
    c = msg.pose.covariance
    return np.array([[c[0], c[1]],
                     [c[6], c[7]]], dtype=float)


def sym(P):
    return 0.5 * (P + P.T)


def ensure_spd(P, eps=1e-9):
    P = sym(P)
    e = eps
    for _ in range(7):
        try:
            np.linalg.cholesky(P + e * np.eye(2))
            return P + e * np.eye(2)
        except np.linalg.LinAlgError:
            e *= 10.0
    return P + e * np.eye(2)


def maha_d2(x, P, z, R):
    r = (z - x).reshape(2, 1)
    S = ensure_spd(P + R)
    try:
        Sinv = np.linalg.inv(S)
    except np.linalg.LinAlgError:
        Sinv = np.linalg.pinv(S)
    return float(r.T @ Sinv @ r)


# ---------------- Node ----------------

class DistributedEKFWindow(Node):
    """
    EKF distribuido por dron con:
      - buffer por dron
      - ventana temporal
      - gating Mahalanobis
      - publicación periódica (como CI)
    """

    def __init__(self):
        super().__init__('distributed_ekf')

        # ---------- Params ----------

        self.declare_parameter('self_drone', 'drone0')
        self.declare_parameter('drones', ['drone0', 'drone1', 'drone2'])
        self.declare_parameter('in_topic_suffix', 'detections_ray_ground')

        self.declare_parameter('world_frame', 'earth')
        self.declare_parameter('publish_topic', '')

        # EKF
        self.declare_parameter('q_sigma', 0.25)
        self.declare_parameter('external_R_inflate', 5.0)

        # ---------- Logging ----------
        self.declare_parameter('debug', True)
        self.declare_parameter('debug_throttle_sec', 1.0)

        self.debug = bool(self.get_parameter('debug').value)
        self.debug_throttle_sec = float(self.get_parameter('debug_throttle_sec').value)
        self._last_debug_time = 0.0

        # Ventana / timing
        self.declare_parameter('publish_hz', 5.0)
        self.declare_parameter('time_window_sec', 5.0)
        self.declare_parameter('max_age_sec', 30.0)
        self.declare_parameter('min_sources', 1)
        self.declare_parameter('publish_only_on_new_ref', True)



        # Gating
        self.declare_parameter('use_gating', True)
        self.declare_parameter('gate_chi2', 5.99)

        # ---------- Get params ----------
        self.self_drone = self.get_parameter('self_drone').value
        self.drones = list(self.get_parameter('drones').value)
        self.suffix = self.get_parameter('in_topic_suffix').value
        self.world_frame = self.get_parameter('world_frame').value

        self._last_seen_stamp_ns = {d: None for d in self.drones}

        self.q_sigma = float(self.get_parameter('q_sigma').value)
        self.external_R_inflate = float(self.get_parameter('external_R_inflate').value)

        self.publish_hz = float(self.get_parameter('publish_hz').value)
        self.time_window_sec = float(self.get_parameter('time_window_sec').value)
        self.max_age_sec = float(self.get_parameter('max_age_sec').value)
        self.min_sources = int(self.get_parameter('min_sources').value)
        self.publish_only_on_new_ref = bool(self.get_parameter('publish_only_on_new_ref').value)

        self.use_gating = bool(self.get_parameter('use_gating').value)
        self.gate_chi2 = float(self.get_parameter('gate_chi2').value)

        pub_topic = self.get_parameter('publish_topic').value
        if not pub_topic:
            pub_topic = f'/swarm/{self.self_drone}/ekf_target'

        # ---------- EKF state ----------
        self.x = None
        self.P = None
        self.t_last = None
        self.last_pub_ref_ns = None

        # ---------- Buffer ----------
        self.last_msg = {d: None for d in self.drones}

        # ---------- Subs ----------
        for d in self.drones:
            topic = f'/swarm/{d}/{self.suffix}'
            self.create_subscription(
                PoseWithCovarianceStamped,
                topic,
                lambda msg, src=d: self.cb(msg, src),
                qos_profile_sensor_data
            )
            self.get_logger().info(f'[{self.self_drone}] sub {topic}')

        # ---------- Pub ----------
        self.pub = self.create_publisher(PoseWithCovarianceStamped, pub_topic, 10)
        self.get_logger().info(f'[{self.self_drone}] pub {pub_topic}')

        # ---------- Timer ----------
        self.timer = self.create_timer(1.0 / self.publish_hz, self.tick)

    # ---------- Callbacks ----------

    def cb(self, msg, src):
        t = rclpy.time.Time.from_msg(msg.header.stamp)
        self.last_msg[src] = (msg, t)
        if self.debug:
            self.log_throttled(
                f"[{self.self_drone}] RX {src}: "
                f"pos=({msg.pose.pose.position.x:.2f},"
                f"{msg.pose.pose.position.y:.2f}) "
                f"Pxx={msg.pose.covariance[0]:.2f} "
                f"Pyy={msg.pose.covariance[7]:.2f}"
            )

    def predict_to(self, t_now):
        if self.t_last is None:
            self.t_last = t_now
            return
        dt = max(0.0, (t_now - self.t_last).nanoseconds * 1e-9)
        self.t_last = t_now
        Q = (self.q_sigma ** 2) * dt * np.eye(2)
        self.P = ensure_spd(self.P + Q)

    def log_throttled(self, msg: str):
        if not self.debug:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        if now - self._last_debug_time >= self.debug_throttle_sec:
            self._last_debug_time = now
            self.get_logger().info(msg)

    def tick(self):
        now = self.get_clock().now()

        # ---- recolectar válidos ----
        valid = []
        for d, item in self.last_msg.items():
            if item is None:
                continue
            msg, t = item
            age = (now - t).nanoseconds * 1e-9
            if age <= self.max_age_sec:
                valid.append((d, msg, t))

        if len(valid) < self.min_sources:
            self.log_throttled(
                f"[{self.self_drone}] waiting: valid_sources={len(valid)} "
                f"(need {self.min_sources})"
            )
            return

        # ---- referencia temporal ----
        ref_t = max(valid, key=lambda e: e[2].nanoseconds)[2]
        ref_ns = ref_t.nanoseconds

        # ---- ventana temporal ----
        window = []
        for d, msg, t in valid:
            if abs((t.nanoseconds - ref_ns) * 1e-9) <= self.time_window_sec:
                window.append((d, msg, t))

        if len(window) < self.min_sources:
            self.log_throttled(
                f"[{self.self_drone}] window rejected: "
                f"{len(window)}/{len(valid)} inside time window"
            )
            return

        # ---- ¿hay medición nueva? (criterio robusto) ----
        any_new = False
        for d, _, t in window:
            ns = t.nanoseconds
            if self._last_seen_stamp_ns[d] != ns:
                any_new = True
                self._last_seen_stamp_ns[d] = ns

        # ordenar por tiempo
        window.sort(key=lambda e: e[2].nanoseconds)

        # ---- inicialización EKF ----
        if self.x is None:
            d0, m0, t0 = window[0]
            self.x = np.array([m0.pose.pose.position.x,
                            m0.pose.pose.position.y])
            self.P = ensure_spd(cov2_from_pose(m0))
            self.t_last = t0

        # ---- updates secuenciales ----
        rejected = 0
        for d, msg, t in window:
            z = np.array([msg.pose.pose.position.x,
                        msg.pose.pose.position.y])
            R = ensure_spd(cov2_from_pose(msg))

            if d != self.self_drone:
                R = ensure_spd(R * self.external_R_inflate)

            self.predict_to(t)

            if self.use_gating:
                d2 = maha_d2(self.x, self.P, z, R)
                if d2 > self.gate_chi2:
                    rejected += 1
                    continue

            S = ensure_spd(self.P + R)
            K = self.P @ np.linalg.inv(S)
            self.x = self.x + K @ (z - self.x)
            self.P = ensure_spd((np.eye(2) - K) @ self.P)

        # ---- publicar ----
        self.publish(ref_t)
        used_drones = [d for d, _, _ in window]
        span = (max(t.nanoseconds for _, _, t in window) -
                min(t.nanoseconds for _, _, t in window)) * 1e-9
        self.log_throttled(
            f"[{self.self_drone}] EKF PUBLISH | used={used_drones} "
            f"dt_span={span:.3f}s rejected={rejected} | "
            f"x=({self.x[0]:.2f},{self.x[1]:.2f}) | "
            f"Pxx={self.P[0,0]:.2f} Pyy={self.P[1,1]:.2f}"
        )

        # ---- publicar ----
        self.publish(ref_t)
        self.last_pub_ref_ns = ref_ns

    def publish(self, t_ref):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = t_ref.to_msg()
        msg.header.frame_id = self.world_frame
        msg.pose.pose.position.x = float(self.x[0])
        msg.pose.pose.position.y = float(self.x[1])
        msg.pose.pose.orientation.w = 1.0
        msg.pose.covariance = [0.0] * 36
        msg.pose.covariance[0] = float(self.P[0, 0])
        msg.pose.covariance[1] = float(self.P[0, 1])
        msg.pose.covariance[6] = float(self.P[1, 0])
        msg.pose.covariance[7] = float(self.P[1, 1])
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = DistributedEKFWindow()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import math
from typing import Dict, List, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseWithCovarianceStamped
from as2_swarm_person_interfaces.msg import TrackedPerson, TrackedPersonArray


def parse_drones_csv(s: str) -> List[str]:
    return [d.strip().strip('/') for d in s.split(',') if d.strip()]


def sym(P: np.ndarray) -> np.ndarray:
    return 0.5 * (P + P.T)


def ensure_spd_2x2(P: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """Asegura SPD (2x2) para poder invertir sin dramas."""
    P = sym(P)
    e = eps
    I = np.eye(2)
    for _ in range(8):
        try:
            np.linalg.cholesky(P + e * I)
            return P + e * I
        except np.linalg.LinAlgError:
            e *= 10.0
    return P + e * I


def maha_d2(mu: np.ndarray, P: np.ndarray, z: np.ndarray, R: np.ndarray) -> float:
    r = (z - mu).reshape(2, 1)
    S = ensure_spd_2x2(P + R)
    try:
        Sinv = np.linalg.inv(S)
    except np.linalg.LinAlgError:
        Sinv = np.linalg.pinv(S)
    return float(r.T @ Sinv @ r)


class Track:
    """Track simple: suaviza posición y covarianza con EMA."""
    def __init__(self, global_id: int, x: float, y: float, cov2: np.ndarray, stamp_sec: float):
        self.global_id = global_id
        self.x = float(x)
        self.y = float(y)
        self.cov2 = ensure_spd_2x2(cov2)
        self.last_update = float(stamp_sec)
        self.hits = 1
        self.misses = 0

    def reset(self, x: float, y: float, cov2: np.ndarray, stamp_sec: float):
        self.x = float(x)
        self.y = float(y)
        self.cov2 = ensure_spd_2x2(cov2)
        self.last_update = float(stamp_sec)
        self.hits = 1
        self.misses = 0

    def update(self, x: float, y: float, cov2: np.ndarray, stamp_sec: float, alpha: float, cov_floor: float):
        alpha = float(np.clip(alpha, 0.0, 0.999))

        # Suavizado de posición (EMA)
        self.x = alpha * self.x + (1.0 - alpha) * float(x)
        self.y = alpha * self.y + (1.0 - alpha) * float(y)

        # Suavizado covarianza
        cov2 = ensure_spd_2x2(cov2)
        self.cov2 = ensure_spd_2x2(alpha * self.cov2 + (1.0 - alpha) * cov2)

        # Suelo mínimo de cov para no sobreconfiar
        self.cov2 = ensure_spd_2x2(self.cov2 + (cov_floor ** 2) * np.eye(2))

        self.last_update = float(stamp_sec)
        self.hits += 1
        self.misses = 0


class MultiPersonTrackerNode(Node):
    """
    Tracker global para 2 personas (IDs fijos 1 y 2) con criterio de "nacimiento por separación".

    Idea clave:
    - Si solo existe 1 track y llega una medición a > spawn_separation_m,
      se crea el segundo ID (la otra persona).
    - El resto del tiempo, asociación por Mahalanobis + gating euclídeo.
    """

    FIXED_IDS = (1, 2)

    def __init__(self):
        super().__init__('multi_person_tracker_node')

        # ---- Params básicos
        self.declare_parameter('drones', 'drone0,drone1,drone2')
        self.declare_parameter('input_topic', 'detections_ray_ground')
        self.declare_parameter('publish_rate_hz', 10.0)

        self.declare_parameter('debug_print', True)
        self.declare_parameter('debug_print_rate_hz', 2.0)

        # ---- Asociación / robustez
        self.declare_parameter('gate_chi2', 5.99)          # 95% en 2D
        self.declare_parameter('track_timeout_s', 8.0)
        self.declare_parameter('min_hits_to_publish', 1)

        self.declare_parameter('alpha_smooth', 0.85)
        self.declare_parameter('cov_floor_sigma', 0.15)

        # NUEVO: criterio para crear el segundo ID cuando están separados
        # Si sabes que están a ~2m, un umbral 1.2–1.6 suele ir bien.
        self.declare_parameter('spawn_separation_m', 1.1)

        # NUEVO: gating euclídeo máximo para evitar asociaciones absurdas
        # (por si Mahalanobis se vuelve permisivo cuando R/P son grandes)
        self.declare_parameter('max_assoc_dist_m', 1.2)

        # Output
        self.declare_parameter('output_topic', '/swarm/tracked_persons_global')
        self.declare_parameter('per_drone_output_suffix', 'people_with_global_id')

        self.drones = parse_drones_csv(self.get_parameter('drones').value)
        self.input_topic = self.get_parameter('input_topic').value

        self.gate_chi2 = float(self.get_parameter('gate_chi2').value)
        self.track_timeout = float(self.get_parameter('track_timeout_s').value)
        self.min_hits = int(self.get_parameter('min_hits_to_publish').value)

        self.alpha_smooth = float(self.get_parameter('alpha_smooth').value)
        self.cov_floor_sigma = float(self.get_parameter('cov_floor_sigma').value)

        self.spawn_separation_m = float(self.get_parameter('spawn_separation_m').value)
        self.max_assoc_dist_m = float(self.get_parameter('max_assoc_dist_m').value)

        self.output_topic = self.get_parameter('output_topic').value
        self.per_drone_suffix = self.get_parameter('per_drone_output_suffix').value

        # ---- State
        self.tracks: Dict[int, Track] = {}
        self.pending_measurements: List[Tuple[str, PoseWithCovarianceStamped]] = []

        # ---- Subs
        self.subs = []
        for d in self.drones:
            topic = f'/swarm/{d}/{self.input_topic}'
            sub = self.create_subscription(
                PoseWithCovarianceStamped,
                topic,
                lambda msg, drone=d: self.on_measurement(drone, msg),
                qos_profile_sensor_data
            )
            self.subs.append(sub)
            self.get_logger().info(f'Subscribed: {topic}')

        # ---- Publishers per-drone
        self.pub_per_drone: Dict[str, any] = {}
        for d in self.drones:
            out_topic = f'/swarm/{d}/{self.per_drone_suffix}'
            self.pub_per_drone[d] = self.create_publisher(TrackedPersonArray, out_topic, 10)
            self.get_logger().info(f'Publishing per-drone observations: {out_topic}')

        # ---- Pub global
        self.pub_global = self.create_publisher(TrackedPersonArray, self.output_topic, 10)

        # ---- Debug timer
        self.debug_enabled = bool(self.get_parameter('debug_print').value)
        debug_rate = float(self.get_parameter('debug_print_rate_hz').value)
        if self.debug_enabled:
            self.debug_timer = self.create_timer(1.0 / max(debug_rate, 0.1), self.debug_print_tracks)

        # ---- Timer publish
        rate = float(self.get_parameter('publish_rate_hz').value)
        self.timer = self.create_timer(1.0 / max(rate, 1e-3), self.on_timer)

    def on_measurement(self, drone: str, msg: PoseWithCovarianceStamped):
        self.pending_measurements.append((drone, msg))

    @staticmethod
    def cov2_from_pose_cov(cov36: List[float]) -> np.ndarray:
        xx = float(cov36[0])
        xy = float(cov36[1])
        yx = float(cov36[6])
        yy = float(cov36[7])
        cov2 = np.array([[xx, xy], [yx, yy]], dtype=float)

        if not np.isfinite(cov2).all():
            cov2 = 0.25 * np.eye(2)

        cov2 = ensure_spd_2x2(cov2, eps=1e-9)
        return cov2

    def euclid_dist_to_track(self, gid: int, z: np.ndarray) -> float:
        tr = self.tracks[gid]
        return float(math.hypot(z[0] - tr.x, z[1] - tr.y))

    def associate_track_maha(self, z: np.ndarray, R: np.ndarray) -> int:
        """Nearest neighbor por Mahalanobis con gating chi2 + gating euclídeo máximo."""
        if not self.tracks:
            return -1

        best_gid = -1
        best_d2 = 1e18
        for gid, tr in self.tracks.items():
            mu = np.array([tr.x, tr.y], dtype=float)

            # Gating euclídeo duro para evitar asociaciones a “la otra persona” si están lejos
            d_e = float(math.hypot(z[0] - mu[0], z[1] - mu[1]))
            if d_e > self.max_assoc_dist_m:
                continue

            d2 = maha_d2(mu, tr.cov2, z, R)
            if d2 < best_d2:
                best_d2 = d2
                best_gid = gid

        return best_gid if (best_gid >= 0 and best_d2 <= self.gate_chi2) else -1

    def create_missing_fixed_id(self, x: float, y: float, cov2: np.ndarray, stamp_sec: float) -> int:
        """Crea el ID fijo que falte (si falta alguno). Si ya están ambos, recicla el más viejo."""
        for gid in self.FIXED_IDS:
            if gid not in self.tracks:
                self.tracks[gid] = Track(gid, x, y, cov2, stamp_sec)
                return gid

        gid_old = min(self.tracks.keys(), key=lambda g: self.tracks[g].last_update)
        self.tracks[gid_old].reset(x, y, cov2, stamp_sec)
        return gid_old

    def prune_tracks(self, now_sec: float):
        to_delete = []
        for gid, tr in self.tracks.items():
            if (now_sec - tr.last_update) > self.track_timeout:
                to_delete.append(gid)
        for gid in to_delete:
            del self.tracks[gid]

    def publish_observation_with_id(self, drone: str, gid: int, msg: PoseWithCovarianceStamped):
        out = TrackedPersonArray()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = msg.header.frame_id if msg.header.frame_id else 'earth'

        tp = TrackedPerson()
        tp.header = out.header
        tp.id = int(gid)
        tp.source = drone
        tp.pose = msg.pose
        tp.confidence = 1.0

        out.persons.append(tp)
        pub = self.pub_per_drone.get(drone, None)
        if pub is not None:
            pub.publish(out)

    def debug_print_tracks(self):
        if not self.tracks:
            return
        lines = []
        for gid, tr in sorted(self.tracks.items()):
            lines.append(f"ID {gid}: x={tr.x:.2f} y={tr.y:.2f} hits={tr.hits}")
        self.get_logger().info("[TRACKER] " + " | ".join(lines))

    def on_timer(self):
        now_sec = self.get_clock().now().nanoseconds * 1e-9

        if self.pending_measurements:
            meas = self.pending_measurements
            self.pending_measurements = []

            for drone, msg in meas:
                x = float(msg.pose.pose.position.x)
                y = float(msg.pose.pose.position.y)
                cov2 = self.cov2_from_pose_cov(list(msg.pose.covariance))

                z = np.array([x, y], dtype=float)
                R = ensure_spd_2x2(cov2 + (self.cov_floor_sigma ** 2) * np.eye(2))

                # --------- NUEVO: nacimiento del segundo track por separación ---------
                # Si solo hay 1 track, y esta medida está a > spawn_separation_m,
                # entonces asumimos que es la otra persona y creamos el ID faltante.
                if len(self.tracks) == 1:
                    only_gid = next(iter(self.tracks.keys()))
                    d_only = self.euclid_dist_to_track(only_gid, z)

                    if d_only >= self.spawn_separation_m:
                        # Crear el ID faltante (1 o 2) directamente
                        gid = self.create_missing_fixed_id(x, y, cov2, now_sec)
                        self.publish_observation_with_id(drone, gid, msg)
                        continue
                # -------------------------------------------------------------------

                gid = self.associate_track_maha(z, R)
                if gid < 0:
                    gid = self.create_missing_fixed_id(x, y, cov2, now_sec)
                else:
                    self.tracks[gid].update(
                        x, y, cov2, now_sec,
                        alpha=self.alpha_smooth,
                        cov_floor=self.cov_floor_sigma
                    )

                self.publish_observation_with_id(drone, gid, msg)

        self.prune_tracks(now_sec)

        # Publica el estado global (IDs fijos)
        out = TrackedPersonArray()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'earth'

        for gid in self.FIXED_IDS:
            tr = self.tracks.get(gid, None)
            if tr is None or tr.hits < self.min_hits:
                continue

            tp = TrackedPerson()
            tp.header = out.header
            tp.id = int(gid)
            tp.source = ''
            tp.pose.pose.position.x = float(tr.x)
            tp.pose.pose.position.y = float(tr.y)
            tp.pose.pose.position.z = 0.0
            tp.pose.pose.orientation.w = 1.0

            cov = [0.0] * 36
            cov[0] = float(tr.cov2[0, 0])
            cov[1] = float(tr.cov2[0, 1])
            cov[6] = float(tr.cov2[1, 0])
            cov[7] = float(tr.cov2[1, 1])
            tp.pose.covariance = cov

            tp.confidence = 1.0
            out.persons.append(tp)

        self.pub_global.publish(out)


def main():
    rclpy.init()
    node = MultiPersonTrackerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

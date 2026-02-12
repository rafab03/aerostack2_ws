#!/usr/bin/env python3
import math
import time
from typing import Dict, List, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseWithCovarianceStamped
from as2_swarm_person_interfaces.msg import TrackedPerson, TrackedPersonArray


def parse_drones_csv(s: str) -> List[str]:
    return [d.strip().strip('/') for d in s.split(',') if d.strip()]


class Track:
    def __init__(self, global_id: int, x: float, y: float, cov2: np.ndarray, stamp_sec: float):
        self.global_id = global_id
        self.x = x
        self.y = y
        self.cov2 = cov2  # 2x2
        self.last_update = stamp_sec
        self.hits = 1
        self.misses = 0

    def update(self, x: float, y: float, cov2: np.ndarray, stamp_sec: float):
        # Fusión muy simple (puedes cambiar a Kalman después)
        self.x = x
        self.y = y
        self.cov2 = cov2
        self.last_update = stamp_sec
        self.hits += 1
        self.misses = 0


class MultiPersonTrackerNode(Node):
    """
    Un único nodo:
    - Subscribes a /swarm/<droneX>/detections_ray_ground (PoseWithCovarianceStamped)
    - Mantiene tracks globales (IDs) y asocia mediciones por distancia / Mahalanobis (opcional)
    - Publica /swarm/tracked_persons_global (TrackedPersonArray)
    """

    def __init__(self):
        super().__init__('multi_person_tracker_node')

        # ---- Params
        self.declare_parameter('drones', 'drone0,drone1,drone2')
        self.declare_parameter('input_topic', 'detections_ray_ground')   # relativo a /swarm/<droneX>/
        self.declare_parameter('publish_rate_hz', 10.0)

        self.declare_parameter('debug_print', True)
        self.declare_parameter('debug_print_rate_hz', 2.0)


        # Asociación
        self.declare_parameter('gating_dist_m', 1.5)      # radio de asociación (m)
        self.declare_parameter('track_timeout_s', 1.0)    # si no llega update, se borra
        self.declare_parameter('min_hits_to_publish', 1)  # para filtrar falsos positivos

        # Output
        self.declare_parameter('output_topic', '/swarm/tracked_persons_global')

        self.drones = parse_drones_csv(self.get_parameter('drones').value)
        self.input_topic = self.get_parameter('input_topic').value
        self.gating_dist = float(self.get_parameter('gating_dist_m').value)
        self.track_timeout = float(self.get_parameter('track_timeout_s').value)
        self.min_hits = int(self.get_parameter('min_hits_to_publish').value)
        self.output_topic = self.get_parameter('output_topic').value

        # ---- State
        self.next_global_id = 1
        self.tracks: Dict[int, Track] = {}  # global_id -> Track

        # Buffer de mediciones recibidas desde cualquier dron (para publicar a ritmo fijo)
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

        # ---- Params extra (per-drone observations output)
        self.declare_parameter('per_drone_output_suffix', 'people_with_global_id')

        self.per_drone_suffix = self.get_parameter('per_drone_output_suffix').value

        # ---- Publishers per-drone (para CI)
        self.pub_per_drone: Dict[str, any] = {}
        for d in self.drones:
            out_topic = f'/swarm/{d}/{self.per_drone_suffix}'
            self.pub_per_drone[d] = self.create_publisher(TrackedPersonArray, out_topic, 10)
            self.get_logger().info(f'Publishing per-drone observations: {out_topic}')

        self.debug_enabled = bool(self.get_parameter('debug_print').value)
        debug_rate = float(self.get_parameter('debug_print_rate_hz').value)

        if self.debug_enabled:
            self.debug_timer = self.create_timer(
                1.0 / max(debug_rate, 0.1),
                self.debug_print_tracks
            )        

        # ---- Pub
        self.pub_global = self.create_publisher(TrackedPersonArray, self.output_topic, 10)

        # ---- Timer publish
        rate = float(self.get_parameter('publish_rate_hz').value)
        self.timer = self.create_timer(1.0 / max(rate, 1e-3), self.on_timer)

    def on_measurement(self, drone: str, msg: PoseWithCovarianceStamped):
        self.pending_measurements.append((drone, msg))

    @staticmethod
    def cov2_from_pose_cov(cov36: List[float]) -> np.ndarray:
        # PoseWithCovariance: cov[0]=xx, cov[1]=xy, cov[6]=yx, cov[7]=yy
        xx = cov36[0]
        xy = cov36[1]
        yx = cov36[6]
        yy = cov36[7]
        cov2 = np.array([[xx, xy], [yx, yy]], dtype=float)
        # Si viene a cero o mal condicionada, mete mínimo:
        eps = 1e-3
        if not np.isfinite(cov2).all():
            cov2 = np.eye(2) * 0.25
        if np.linalg.det(cov2) <= 0:
            cov2 = cov2 + np.eye(2) * eps
        return cov2

    def associate_track(self, x: float, y: float) -> int:
        """Asociación simple: nearest neighbor en distancia euclídea con gating."""
        best_id = -1
        best_d = 1e9
        for gid, tr in self.tracks.items():
            dx = tr.x - x
            dy = tr.y - y
            d = math.hypot(dx, dy)
            if d < best_d:
                best_d = d
                best_id = gid
        if best_d <= self.gating_dist:
            return best_id
        return -1

    def publish_observation_with_id(self, drone: str, gid: int, msg: PoseWithCovarianceStamped):
        out = TrackedPersonArray()
        out.header.stamp = msg.header.stamp  # usa el stamp de la medición
        out.header.frame_id = msg.header.frame_id if msg.header.frame_id else 'earth'

        tp = TrackedPerson()
        tp.header = out.header
        tp.id = int(gid)
        tp.source = drone  # MUY IMPORTANTE para CI
        tp.pose = msg.pose  # copia pose + cov tal cual
        tp.confidence = 1.0

        out.persons.append(tp)

        pub = self.pub_per_drone.get(drone, None)
        if pub is not None:
            pub.publish(out)

    def create_track(self, x: float, y: float, cov2: np.ndarray, stamp_sec: float) -> int:
        gid = self.next_global_id
        self.next_global_id += 1
        self.tracks[gid] = Track(gid, x, y, cov2, stamp_sec)
        return gid

    def prune_tracks(self, now_sec: float):
        to_delete = []
        for gid, tr in self.tracks.items():
            if (now_sec - tr.last_update) > self.track_timeout:
                to_delete.append(gid)
        for gid in to_delete:
            del self.tracks[gid]

    def debug_print_tracks(self):
        if not self.tracks:
            return

        lines = []
        for gid, tr in sorted(self.tracks.items()):
            lines.append(
                f"ID {gid}: x={tr.x:.2f}  y={tr.y:.2f}  hits={tr.hits}"
            )

        msg = " | ".join(lines)
        self.get_logger().info(f"[TRACKER] {msg}")

    def on_timer(self):
        now_sec = self.get_clock().now().nanoseconds * 1e-9

        # 1) Procesa todas las mediciones acumuladas
        if self.pending_measurements:
            meas = self.pending_measurements
            self.pending_measurements = []

            for drone, msg in meas:
                x = msg.pose.pose.position.x
                y = msg.pose.pose.position.y
                cov2 = self.cov2_from_pose_cov(list(msg.pose.covariance))

                gid = self.associate_track(x, y)
                if gid < 0:
                    gid = self.create_track(x, y, cov2, now_sec)
                else:
                    self.tracks[gid].update(x, y, cov2, now_sec)

                # NUEVO: publica la observación del dron con el global_id asignado (para CI)
                self.publish_observation_with_id(drone, gid, msg)

        # 2) Limpia tracks muertos
        self.prune_tracks(now_sec)

        # 3) Publica el estado global (a ritmo fijo)
        out = TrackedPersonArray()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'earth'  # o el que uses

        for gid, tr in self.tracks.items():
            if tr.hits < self.min_hits:
                continue

            tp = TrackedPerson()
            tp.header = out.header
            tp.id = int(gid)
            tp.source = ''  # global
            tp.pose.pose.position.x = float(tr.x)
            tp.pose.pose.position.y = float(tr.y)
            tp.pose.pose.position.z = 0.0
            tp.pose.pose.orientation.w = 1.0

            # mete cov XY en la 6x6
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

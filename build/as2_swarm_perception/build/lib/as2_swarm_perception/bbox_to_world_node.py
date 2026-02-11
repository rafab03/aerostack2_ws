#!/usr/bin/env python3
import math
import numpy as np

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from sensor_msgs.msg import CameraInfo
from vision_msgs.msg import Detection2DArray
from rclpy.qos import qos_profile_sensor_data


class BBoxToWorldNode(Node):
    """
    Convierte detecciones 2D (vision_msgs/Detection2DArray) a estimación (x,y) en frame global + covarianza.
    Frame global: earth (en Aerostack2).
    Baseline: pinhole con altura del bbox y altura real de persona.
    """

    def __init__(self):
        super().__init__('bbox_to_world_node')

        # Topics relativos al namespace (se resuelven bajo /droneX)
        self.declare_parameter('detections_topic', 'perception/person_detections')
        self.declare_parameter('pose_topic', 'self_localization/pose')
        self.declare_parameter('camera_info_topic', 'sensor_measurements/gimbal2/hd_camera1_d2/camera_info')

        # Output global (sin namespace normalmente)
        self.declare_parameter('swarm_out_topic', '/swarm/common_detections')

        # Modelo y filtros
        self.declare_parameter('real_person_height_m', 1.70)
        self.declare_parameter('min_conf', 0.35)
        self.declare_parameter('publish_only_best', True)

        # Incertidumbre (baseline)
        self.declare_parameter('sigma_pos_base', 0.30)     # m
        self.declare_parameter('sigma_range_per_m', 0.15)  # m/m
        self.declare_parameter('sigma_lat_per_m', 0.10)    # m/m

        self.last_pose: PoseStamped | None = None
        self.fx = self.fy = self.cx = self.cy = None

        self.sub_pose = self.create_subscription(
            PoseStamped,
            self.get_parameter('pose_topic').value,
            self.pose_cb,
            qos_profile_sensor_data
        )

        self.sub_cam = self.create_subscription(
            CameraInfo,
            self.get_parameter('camera_info_topic').value,
            self.caminfo_cb,
            qos_profile_sensor_data
        )

        self.sub_det = self.create_subscription(
            Detection2DArray,
            self.get_parameter('detections_topic').value,
            self.det_cb,
            qos_profile_sensor_data
        )

        self.pub_swarm = self.create_publisher(
            PoseWithCovarianceStamped,
            self.get_parameter('swarm_out_topic').value,
            10
        )

        self.get_logger().info("BBoxToWorldNode listo (publica en frame 'earth').")

    def pose_cb(self, msg: PoseStamped):
        self.last_pose = msg

    def caminfo_cb(self, msg: CameraInfo):
        self.fx = float(msg.k[0])
        self.fy = float(msg.k[4])
        self.cx = float(msg.k[2])
        self.cy = float(msg.k[5])

    def det_cb(self, msg: Detection2DArray):
        if self.last_pose is None:
            return
        if self.fx is None or self.fy is None or self.cx is None:
            return
        if not msg.detections:
            return

        min_conf = float(self.get_parameter('min_conf').value)
        only_best = bool(self.get_parameter('publish_only_best').value)

        candidates = []
        for det in msg.detections:
            if not det.results:
                continue

            best = det.results[0]
            score = float(best.hypothesis.score)
            cid = best.hypothesis.class_id  # puede ser str o int según el nodo

            # ✅ Soporta ambos formatos:
            is_person = False
            if isinstance(cid, str):
                is_person = (cid.lower() == 'person')
            else:
                try:
                    is_person = (int(cid) == 0)  # COCO person=0
                except Exception:
                    is_person = False

            if (not is_person) or (score < min_conf):
                continue

            u = float(det.bbox.center.position.x)
            h = float(det.bbox.size_y)
            candidates.append((score, u, h))

        if not candidates:
            return

        candidates.sort(key=lambda x: x[0], reverse=True)
        selected = [candidates[0]] if only_best else candidates

        for score, u_center, h_pixels in selected:
            self.process_one(score, u_center, h_pixels)
            if only_best:
                break


    def process_one(self, score: float, u_center: float, h_pixels: float):
        H = float(self.get_parameter('real_person_height_m').value)

        if h_pixels < 1.0:
            h_pixels = 1.0

        # Distancia por pinhole (usamos fy)
        D = (self.fy * H) / h_pixels

        # Local (forward, lateral)
        x_local = D
        x_pix = (u_center - self.cx)
        y_local = -(x_pix * D / self.fx)

        # Global usando yaw del dron
        yaw = self.get_yaw(self.last_pose.pose)
        dx = float(self.last_pose.pose.position.x)
        dy = float(self.last_pose.pose.position.y)

        x_global = dx + (x_local * math.cos(yaw) - y_local * math.sin(yaw))
        y_global = dy + (x_local * math.sin(yaw) + y_local * math.cos(yaw))

        # Covarianza anisótropa simple en local y rotación a global
        sigma_base = float(self.get_parameter('sigma_pos_base').value)
        sigma_r = sigma_base + float(self.get_parameter('sigma_range_per_m').value) * D
        sigma_lat = sigma_base + float(self.get_parameter('sigma_lat_per_m').value) * D

        P_local = np.array([[sigma_r**2, 0.0],
                            [0.0, sigma_lat**2]])

        c = math.cos(yaw)
        s = math.sin(yaw)
        R = np.array([[c, -s],
                      [s,  c]])
        P_global = R @ P_local @ R.T

        self.publish_swarm(x_global, y_global, P_global, score)

    def get_yaw(self, pose):
        q = pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y*q.y + q.z*q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def publish_swarm(self, x, y, P2, score):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'earth'  # ✅ tu caso

        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)

        msg.pose.covariance[0] = float(P2[0, 0])
        msg.pose.covariance[1] = float(P2[0, 1])
        msg.pose.covariance[6] = float(P2[1, 0])
        msg.pose.covariance[7] = float(P2[1, 1])

        self.pub_swarm.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = BBoxToWorldNode()
    rclpy.spin(node)
    rclpy.shutdown()

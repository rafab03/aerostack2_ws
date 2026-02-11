#!/usr/bin/env python3
import math
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import CameraInfo
from vision_msgs.msg import Detection2DArray
from geometry_msgs.msg import PoseWithCovarianceStamped

import tf2_ros


class RayToGroundNode(Node):
    """
    Estima (x,y) en world_frame intersectando un rayo pinhole (desde píxel) con el plano del suelo z=ground_z.
    Publica PoseWithCovarianceStamped con covarianza heurística mejorada:
      - distancia (range)
      - tamaño del bbox (area_px)
      - confianza de detección (score)
      - condición geométrica (|dz| del rayo en mundo)
      - anisotropía (peor a lo largo de la dirección horizontal del rayo)
    """

    def __init__(self):
        super().__init__('ray_to_ground_node')

        # Topics (relativos al namespace)
        self.declare_parameter('detections_topic', 'perception/person_detections')
        self.declare_parameter('camera_info_topic', 'sensor_measurements/gimbal0/hd_camera1_d0/camera_info')

        # Frames
        self.declare_parameter('world_frame', 'earth')
        self.declare_parameter('camera_frame', '')  # si vacío: usa CameraInfo.header.frame_id

        # Suelo
        self.declare_parameter('ground_z', 0.0)

        # Filtros
        self.declare_parameter('min_conf', 0.35)
        self.declare_parameter('publish_only_best', True)

        # Output
        self.declare_parameter('swarm_out_topic', '/swarm/common_detections')

        # ---- Incertidumbre (heurística mejorada) ----
        # distancia
        self.declare_parameter('sigma_base', 0.15)    # [m] error base mínimo
        self.declare_parameter('sigma_per_m', 0.03)   # [m/m] aumenta con distancia horizontal

        # --- GPS pose uncertainty injection (fallback when covariances are zero) ---
        self.declare_parameter('gps_sigma0_xy', 0.15)        # [m] base 1-sigma in XY
        self.declare_parameter('gps_rw_xy', 0.0)            # [m/sqrt(s)] random-walk intensity
        self.declare_parameter('gps_max_sigma_xy', 0.50)     # [m] cap so it doesn't grow unbounded

        self._t0 = self.get_clock().now()

        # bbox + confianza + geometría
        self.declare_parameter('sigma_area', 2.0)     # [m*sqrt(px^2)] (más alto => penaliza bbox pequeño)
        self.declare_parameter('sigma_conf', 0.10)    # [m] penalización por baja confianza
        self.declare_parameter('conf_min', 0.20)      # clamp para evitar infinidades

        self.declare_parameter('eps_dz', 0.02)        # evita división por 0 en dz
        self.declare_parameter('angle_gain', 0.30)    # 0 desactiva penalización geométrica

        self.declare_parameter('min_sigma', 0.05)     # [m]
        self.declare_parameter('max_sigma', 5.0)      # [m]

        self.declare_parameter('sigma_pix_base', 2.0)   # px
        self.declare_parameter('k_pix_area', 120.0)     # px*sqrt(px^2)
        self.declare_parameter('k_pix_conf', 2.0)       # px
        self.declare_parameter('gamma_v', 2.0)          # >=1

        self.declare_parameter('du_px', 1.0)           # px paso para derivada numérica
        self.declare_parameter('dv_px', 1.0)           # px

        # anisotropía: sigma_para = ratio * sigma_perp
        self.declare_parameter('anisotropy_ratio', 2.0)

        # Intrínsecos
        self.fx = self.fy = self.cx = self.cy = None
        self.camera_frame_runtime = None

        # TF2
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Subs/Pubs
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
        self.pub = self.create_publisher(
            PoseWithCovarianceStamped,
            self.get_parameter('swarm_out_topic').value,
            10
        )

        self.get_logger().info("RayToGroundNode listo: pinhole back-projection + TF + intersección con z=ground_z.")

    @staticmethod
    def _normalize_frame(frame: str) -> str:
        if frame is None:
            return None
        frame = frame.strip()
        frame = frame.strip('/')
        return frame

    def caminfo_cb(self, msg: CameraInfo):
        self.fx = float(msg.k[0])
        self.fy = float(msg.k[4])
        self.cx = float(msg.k[2])
        self.cy = float(msg.k[5])

        cam_frame_param = self.get_parameter('camera_frame').value
        if cam_frame_param:
            self.camera_frame_runtime = self._normalize_frame(cam_frame_param)
        else:
            self.camera_frame_runtime = self._normalize_frame(msg.header.frame_id) if msg.header.frame_id else None

    def det_cb(self, msg: Detection2DArray):
        # --- Guardas con logs ---
        if self.fx is None or self.fy is None or self.cx is None or self.cy is None:
            self.get_logger().warn("Aún sin intrínsecos (CameraInfo no recibido).", throttle_duration_sec=2.0)
            return

        if self.camera_frame_runtime is None:
            self.get_logger().warn(
                "camera_frame no disponible (param vacío y CameraInfo.frame_id vacío).",
                throttle_duration_sec=2.0
            )
            return

        if not msg.detections:
            self.get_logger().warn("Detection2DArray vacío: no hay detecciones.", throttle_duration_sec=2.0)
            return

        min_conf = float(self.get_parameter('min_conf').value)
        only_best = bool(self.get_parameter('publish_only_best').value)
        world_frame = self._normalize_frame(self.get_parameter('world_frame').value)
        cam_frame = self.camera_frame_runtime

        # --- TF: world <- camera ---
        try:
            tf = self.tf_buffer.lookup_transform(world_frame, cam_frame, rclpy.time.Time())
        except Exception as e:
            self.get_logger().warn(
                f"No TF '{world_frame}' <- '{cam_frame}': {e}",
                throttle_duration_sec=2.0
            )
            return

        origin_world = np.array([
            tf.transform.translation.x,
            tf.transform.translation.y,
            tf.transform.translation.z
        ], dtype=float)

        R = self.quat_to_rot(
            tf.transform.rotation.x,
            tf.transform.rotation.y,
            tf.transform.rotation.z,
            tf.transform.rotation.w
        )

        # --- Candidatos persona ---
        candidates = []
        total = 0
        for det in msg.detections:
            total += 1
            if not det.results:
                continue

            best = det.results[0]
            score = float(best.hypothesis.score)
            cid = best.hypothesis.class_id

            is_person = False
            if isinstance(cid, str):
                is_person = (cid.lower() == 'person')
            else:
                try:
                    is_person = (int(cid) == 0)
                except Exception:
                    is_person = False

            if (not is_person) or (score < min_conf):
                continue

            u = float(det.bbox.center.position.x)
            v = float(det.bbox.center.position.y)

            w = float(det.bbox.size_x)
            h = float(det.bbox.size_y)

            # Punto “pies”: borde inferior del bbox
            v_feet = v + 0.5 * h

            # guardamos score, u, v_feet, bbox_w, bbox_h
            candidates.append((score, u, v_feet, w, h))

        if not candidates:
            self.get_logger().warn(
                f"Detecciones recibidas={total}, pero 0 pasan filtro (min_conf={min_conf}). "
                "Revisa class_id='person' y/o umbral.",
                throttle_duration_sec=2.0
            )
            return

        candidates.sort(key=lambda x: x[0], reverse=True)
        selected = [candidates[0]] if only_best else candidates

        self.get_logger().info(
            f"Detecciones={total}, candidatos={len(candidates)}; usando {len(selected)}. "
            f"world='{world_frame}', cam='{cam_frame}', origin_z={origin_world[2]:.2f}",
            throttle_duration_sec=2.0
        )

        for score, u, v_feet, bbox_w, bbox_h in selected:
            ok = self.process_one(score, u, v_feet, bbox_w, bbox_h, origin_world, R, world_frame)
            if not ok:
                self.get_logger().warn(
                    f"Descartada detección (score={score:.2f}) u={u:.1f}, v_feet={v_feet:.1f}, "
                    f"w={bbox_w:.1f}, h={bbox_h:.1f} (no intersección válida con suelo).",
                    throttle_duration_sec=2.0
                )
            if only_best:
                break

    def process_one(self, score, u, v, bbox_w_px, bbox_h_px, origin_world, R_world_cam, world_frame):
        ground_z = float(self.get_parameter('ground_z').value)

        # ---- 1) back-project: píxel -> rayo en cámara ----
        xn = (u - self.cx) / self.fx
        yn = (v - self.cy) / self.fy
        d_cam = np.array([xn, yn, 1.0], dtype=float)
        d_cam /= (np.linalg.norm(d_cam) + 1e-12)

        # ---- 2) rayo en mundo ----
        d_world = R_world_cam @ d_cam

        dz = float(d_world[2])
        if abs(dz) < 1e-6:
            self.get_logger().warn(
                f"Rayo casi paralelo al suelo: dz={dz:.3e} (cam_frame probablemente mal orientado).",
                throttle_duration_sec=2.0
            )
            return False

        # ---- 3) intersección con plano z=ground_z ----
        t = (ground_z - float(origin_world[2])) / dz
        if t <= 0.0:
            self.get_logger().warn(
                f"Intersección no válida: t={t:.3f} (origin_z={origin_world[2]:.3f}, dz={dz:.3f}, ground_z={ground_z:.3f}). "
                "Suele indicar frame equivocado o eje Z apuntando hacia arriba.",
                throttle_duration_sec=2.0
            )
            return False

        p = origin_world + t * d_world

        # ---- 4) covarianza heurística mejorada ----
        sigma_base = float(self.get_parameter('sigma_base').value)      # [m]
        k_range = float(self.get_parameter('sigma_per_m').value)        # [m/m]

        k_area = float(self.get_parameter('sigma_area').value)          # [m*sqrt(px^2)]
        k_conf = float(self.get_parameter('sigma_conf').value)          # [m]
        conf_min = float(self.get_parameter('conf_min').value)          # 0..1

        eps_dz = float(self.get_parameter('eps_dz').value)              # ~1e-2
        angle_gain = float(self.get_parameter('angle_gain').value)      # >=0

        min_sigma = float(self.get_parameter('min_sigma').value)        # [m]
        max_sigma = float(self.get_parameter('max_sigma').value)        # [m]

        anis_ratio = float(self.get_parameter('anisotropy_ratio').value)

        # Distancia horizontal cámara->punto
        dist_xy = float(math.hypot(p[0] - origin_world[0], p[1] - origin_world[1]))

        # (1) distancia
        sigma_r = sigma_base + k_range * dist_xy

        # (2) bbox area (más área => menos sigma)
        area_px = float(max(1.0, bbox_w_px * bbox_h_px))
        sigma_a = k_area / math.sqrt(area_px)

        # (3) confianza (menos conf => más sigma)
        conf = float(max(conf_min, min(1.0, score)))
        sigma_c = k_conf * ((1.0 / conf) - 1.0)  # 0 si conf=1, crece si conf baja

        # (4) geometría: penalizar rayos casi paralelos al suelo
        dz_abs = float(abs(d_world[2]))
        g_angle = 1.0 + angle_gain * (1.0 / max(dz_abs, eps_dz) - 1.0)  # >=1

        # sigma isotrópico base (tu método)
        sigma_iso = (sigma_r + sigma_a + sigma_c) * g_angle
        sigma_iso = float(min(max(sigma_iso, min_sigma), max_sigma))

        # anisotropía: peor a lo largo de la dirección horizontal del rayo (tu método)
        dx, dy = float(d_world[0]), float(d_world[1])
        norm_xy = math.hypot(dx, dy)

        if norm_xy < 1e-6:
            P_heur = np.array([[sigma_iso**2, 0.0],
                            [0.0,          sigma_iso**2]], dtype=float)
        else:
            ux, uy = dx / norm_xy, dy / norm_xy
            vx, vy = -uy, ux

            anis_ratio = max(1.0, anis_ratio)

            sigma_perp = sigma_iso
            sigma_para = anis_ratio * sigma_iso

            uuT = np.array([[ux*ux, ux*uy],
                            [uy*ux, uy*uy]], dtype=float)
            vvT = np.array([[vx*vx, vx*vy],
                            [vy*vx, vy*vy]], dtype=float)

            P_heur = (sigma_para**2) * uuT + (sigma_perp**2) * vvT

        # >>> NUEVO (A): covarianza por propagación de error de píxel (u,v) mediante Jacobiano
        # Parámetros NUEVOS a declarar en __init__:
        #   sigma_pix_base [px], k_pix_area [px*sqrt(px^2)], k_pix_conf [px], gamma_v [>=1], du_px, dv_px
        sigma_pix_base = float(self.get_parameter('sigma_pix_base').value)  # [px]
        k_pix_area     = float(self.get_parameter('k_pix_area').value)      # [px*sqrt(px^2)]
        k_pix_conf     = float(self.get_parameter('k_pix_conf').value)      # [px]
        gamma_v        = float(self.get_parameter('gamma_v').value)         # [-]
        du_px          = float(self.get_parameter('du_px').value)           # [px]
        dv_px          = float(self.get_parameter('dv_px').value)           # [px]

        sigma_area_px = k_pix_area / math.sqrt(area_px)
        sigma_conf_px = k_pix_conf * ((1.0 / conf) - 1.0)

        sigma_u = math.sqrt(sigma_pix_base**2 + sigma_area_px**2 + sigma_conf_px**2)
        sigma_v = max(1.0, gamma_v) * sigma_u

        Sigma_uv = np.array([[sigma_u**2, 0.0],
                            [0.0,        sigma_v**2]], dtype=float)

        def intersect_xy(u0, v0):
            xn0 = (u0 - self.cx) / self.fx
            yn0 = (v0 - self.cy) / self.fy
            d_cam0 = np.array([xn0, yn0, 1.0], dtype=float)
            d_cam0 /= (np.linalg.norm(d_cam0) + 1e-12)

            d_world0 = R_world_cam @ d_cam0
            dz0 = float(d_world0[2])
            if abs(dz0) < 1e-6:
                return None

            t0 = (ground_z - float(origin_world[2])) / dz0
            if t0 <= 0.0:
                return None

            p0 = origin_world + t0 * d_world0
            return float(p0[0]), float(p0[1])

        # (x,y) nominal ya lo tienes en p
        x0, y0 = float(p[0]), float(p[1])

        xy_u = intersect_xy(u + du_px, v)
        xy_v = intersect_xy(u, v + dv_px)
        if (xy_u is None) or (xy_v is None):
            # Si la derivada no es válida, cae a tu heurística pura
            P_pix = np.zeros((2, 2), dtype=float)
        else:
            xu, yu = xy_u
            xv, yv = xy_v

            J = np.array([[(xu - x0) / du_px, (xv - x0) / dv_px],
                        [(yu - y0) / du_px, (yv - y0) / dv_px]], dtype=float)

            P_pix = J @ Sigma_uv @ J.T
            P_pix = 0.5 * (P_pix + P_pix.T)  # simetrizar por estabilidad numérica

        # >>> NUEVO (B): combinación (asumimos independencia aproximada)
        P = P_heur + P_pix

        # >>> NUEVO (C): añadir incertidumbre de pose tipo GPS (XY) si no hay covariancias publicadas
        gps_sigma0_xy    = float(self.get_parameter('gps_sigma0_xy').value)     # [m]
        gps_rw_xy        = float(self.get_parameter('gps_rw_xy').value)         # [m/sqrt(s)]
        gps_max_sigma_xy = float(self.get_parameter('gps_max_sigma_xy').value)  # [m]

        # tiempo desde arranque del nodo (seg)
        t_sec = (self.get_clock().now() - self._t0).nanoseconds * 1e-9
        t_sec = max(0.0, t_sec)

        # modelo tipo random-walk: sigma^2 = sigma0^2 + (rw^2)*t
        sigma_gps_xy = math.sqrt(gps_sigma0_xy**2 + (gps_rw_xy**2) * t_sec)
        sigma_gps_xy = min(sigma_gps_xy, gps_max_sigma_xy)

        P_gps = np.array([[sigma_gps_xy**2, 0.0],
                        [0.0,            sigma_gps_xy**2]], dtype=float)

        P = P + P_gps

        # (opcional suave) asegurar SPD si por numérico sale mal (raro)
        # clamp de autovalores a [min_sigma^2, max_sigma^2]
        lam, Q = np.linalg.eigh(0.5 * (P + P.T))
        lam = np.clip(lam, min_sigma**2, max_sigma**2)
        P = (Q * lam) @ Q.T

        self.publish_pose(p[0], p[1], P, world_frame)

        self.get_logger().info(
            f"PUBLICADO: x={p[0]:.2f}, y={p[1]:.2f}, dist={dist_xy:.2f}m, "
            f"sigma_iso={sigma_iso:.2f}, conf={conf:.2f}, area_px={area_px:.0f}, dz_abs={dz_abs:.3f}, "
            f"Pxx={P[0,0]:.3f}, Pyy={P[1,1]:.3f}",
            throttle_duration_sec=1.0
        )
        return True

    def publish_pose(self, x, y, P2, world_frame):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = world_frame

        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)

        # x,y (covarianza 6x6 en orden row-major)
        msg.pose.covariance[0] = float(P2[0, 0])
        msg.pose.covariance[1] = float(P2[0, 1])
        msg.pose.covariance[6] = float(P2[1, 0])
        msg.pose.covariance[7] = float(P2[1, 1])

        self.pub.publish(msg)

    @staticmethod
    def quat_to_rot(x, y, z, w):
        xx, yy, zz = x*x, y*y, z*z
        xy, xz, yz = x*y, x*z, y*z
        wx, wy, wz = w*x, w*y, w*z

        return np.array([
            [1 - 2*(yy + zz),     2*(xy - wz),       2*(xz + wy)],
            [2*(xy + wz),         1 - 2*(xx + zz),   2*(yz - wx)],
            [2*(xz - wy),         2*(yz + wx),       1 - 2*(xx + yy)]
        ], dtype=float)


def main(args=None):
    rclpy.init(args=args)
    node = RayToGroundNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()

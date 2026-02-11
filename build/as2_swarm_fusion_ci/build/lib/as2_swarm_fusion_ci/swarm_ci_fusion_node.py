#!/usr/bin/env python3
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped


def cov2_from_pose(msg: PoseWithCovarianceStamped) -> np.ndarray:
    """Extrae la submatriz 2x2 (x,y) de la covarianza 6x6 en ROS."""
    c = msg.pose.covariance
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
    """
    Regulariza para evitar singularidades:
    - simetriza
    - añade eps a la diagonal si hace falta
    """
    P = _symmetrize(P)
    # Intento rápido: si cholesky falla, incremento eps
    e = eps
    for _ in range(6):
        try:
            np.linalg.cholesky(P + e * np.eye(P.shape[0]))
            return P + e * np.eye(P.shape[0])
        except np.linalg.LinAlgError:
            e *= 10.0
    # Último recurso
    return P + e * np.eye(P.shape[0])

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


def _logdet_spd(P: np.ndarray) -> float:
    """log(det(P)) estable para SPD."""
    sign, ld = np.linalg.slogdet(P)
    if sign <= 0:
        # Si algo raro ocurre, penaliza fuerte
        return float("inf")
    return float(ld)


def covariance_intersection_pair(
    x1: np.ndarray,
    P1: np.ndarray,
    x2: np.ndarray,
    P2: np.ndarray,
    criterion: str = "logdet",
    max_iter: int = 40,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    CI en forma de información:
        P(w)^{-1} = w P1^{-1} + (1-w) P2^{-1}
        x(w)      = P(w) [ w P1^{-1} x1 + (1-w) P2^{-1} x2 ]

    Selección de w por búsqueda 1D (golden-section) minimizando:
      - "logdet": log(det(P(w))) (recomendado)
      - "trace":  trace(P(w))
    """
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
        # por defecto: logdet (equivalente a minimizar det, pero estable)
        return _logdet_spd(Pf)

    # Golden-section search en [0,1]
    a, b = 0.0, 1.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0  # ~0.618
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


class SwarmCIFusionAsync(Node):
    """
    Fusión TTF asincrónica (ventana temporal):
    - Guarda el último track (mu, Sigma) de cada dron.
    - Cada tick, selecciona los tracks cuyo stamp cae dentro de una ventana Δt
      respecto al stamp más nuevo disponible.
    - Aplica CI secuencial para fusionar.
    """

    def __init__(self):
        super().__init__("swarm_ci_fusion_async")

        # -------- Params --------
        self.declare_parameter("drones", ["drone0", "drone1", "drone2"])
        self.declare_parameter("in_topic_suffix", "detections_ray_ground")
        self.declare_parameter("out_topic", "/swarm/fused_target")
        self.declare_parameter("world_frame", "earth")

        # Mensajes demasiado viejos se ignoran
        self.declare_parameter("max_age_sec", 2.0)

        # Ventana de simultaneidad (stamps)
        self.declare_parameter("time_window_sec", 0.75)

        # Mínimo de drones para publicar fusión (2 recomendado)
        self.declare_parameter("min_sources", 2)

        # "logdet" (recomendado) o "trace"
        self.declare_parameter("criterion", "logdet")

        # Frecuencia de publicación
        self.declare_parameter("publish_hz", 20.0)

        # Debug
        self.declare_parameter("debug", True)
        self.declare_parameter("debug_throttle_sec", 1.0)

        self.drones: List[str] = list(self.get_parameter("drones").value)
        self.in_topic_suffix = str(self.get_parameter("in_topic_suffix").value)
        self.out_topic = str(self.get_parameter("out_topic").value)
        self.world_frame = str(self.get_parameter("world_frame").value)

        self.max_age_sec = float(self.get_parameter("max_age_sec").value)
        self.time_window_sec = float(self.get_parameter("time_window_sec").value)
        self.min_sources = int(self.get_parameter("min_sources").value)
        self.criterion = str(self.get_parameter("criterion").value).lower().strip()

        self.declare_parameter("maha_gate_chi2", 5.99)   # ~95% en 2D
        self.declare_parameter("publish_only_on_new_ref", True)

        self.maha_gate_chi2 = float(self.get_parameter("maha_gate_chi2").value)
        self.publish_only_on_new_ref = bool(self.get_parameter("publish_only_on_new_ref").value)

        self._last_pub_ref_stamp_ns = None

        self.publish_hz = float(self.get_parameter("publish_hz").value)
        self.debug = bool(self.get_parameter("debug").value)
        self.debug_throttle_sec = float(self.get_parameter("debug_throttle_sec").value)
        self._last_debug_log_time = 0.0

        # Último mensaje por dron: (msg, stamp_time)
        self.last_msg: Dict[str, Optional[Tuple[PoseWithCovarianceStamped, rclpy.time.Time]]] = {
            d: None for d in self.drones
        }

        # -------- Subs --------
        self.subs = []
        for d in self.drones:
            topic = f"/swarm/{d}/{self.in_topic_suffix}"
            sub = self.create_subscription(
                PoseWithCovarianceStamped,
                topic,
                lambda msg, drone=d: self.cb(msg, drone),
                10,
            )
            self.subs.append(sub)
            self.get_logger().info(f"Subscrito a: {topic}")
            

        # -------- Pub --------
        self.pub = self.create_publisher(PoseWithCovarianceStamped, self.out_topic, 10)
        self.get_logger().info(f"Publicando fusion en: {self.out_topic}")

        period = 1.0 / max(1e-3, self.publish_hz)
        self.timer = self.create_timer(period, self.tick)

        self._pub_count = 0
        self.get_logger().info(
            "Swarm CI Fusion ASYNC listo. "
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

    def cb(self, msg: PoseWithCovarianceStamped, drone: str):
        t = rclpy.time.Time.from_msg(msg.header.stamp)
        self.last_msg[drone] = (msg, t)
        if self.debug:
            self._throttled_info(
                f"RX {drone} stamp={t.nanoseconds*1e-9:.3f}s "
                f"pos=({msg.pose.pose.position.x:.2f},{msg.pose.pose.position.y:.2f}) "
                f"Pxx={msg.pose.covariance[0]:.3f} Pyy={msg.pose.covariance[7]:.3f}"
            )

    def _collect_valid(self) -> List[Tuple[str, PoseWithCovarianceStamped, rclpy.time.Time, float]]:
        """
        Devuelve los tracks no-stale y dentro de ventana temporal respecto al más nuevo.
        """
        now = self.get_clock().now()

        # 1) filtra por edad (max_age)
        fresh = []
        for d, item in self.last_msg.items():
            if item is None:
                continue
            m, t = item
            age = (now - t).nanoseconds * 1e-9
            if age <= self.max_age_sec:
                fresh.append((d, m, t, age))

        if not fresh:
            return []

        # 2) usa como referencia el stamp más nuevo
        t_ref = max(fresh, key=lambda e: e[2].nanoseconds)[2]
        ref_sec = t_ref.nanoseconds * 1e-9

        # 3) filtra por simultaneidad (ventana en stamps, no en "age")
        selected = []
        for (d, m, t, age) in fresh:
            dt_stamp = abs((t.nanoseconds - t_ref.nanoseconds) * 1e-9)
            if dt_stamp <= self.time_window_sec:
                selected.append((d, m, t, age))

        # ordena por stamp (opcional, solo para logs bonitos)
        selected.sort(key=lambda e: e[2].nanoseconds)
        self._throttled_info(
            f"selected={[(d, round((t.nanoseconds*1e-9)-ref_sec,3)) for d,_,t,_ in selected]} "
            f"(ref_stamp={ref_sec:.3f}s)"
        )
        return selected


    def tick(self):
        entries = self._collect_valid()
        if len(entries) < self.min_sources:
            self._throttled_info(f"waiting: have={len(entries)} need>={self.min_sources}")
            return

        # Referencia temporal: stamp más nuevo
        ref_t = max(entries, key=lambda e: e[2].nanoseconds)[2]
        ref_ns = ref_t.nanoseconds

        if self.publish_only_on_new_ref and self._last_pub_ref_stamp_ns == ref_ns:
            self._throttled_info("skip publish (no new ref stamp)")
            return

        # Calidad por logdet(P)
        def quality(e):
            _, m, _, _ = e
            P = _ensure_spd(cov2_from_pose(m))
            return _logdet_spd(P)

        entries.sort(key=quality)

        # ---------- Construye lista de inputs para log ----------
        inputs_for_log = []
        for (d, m, t, _) in entries:
            x_i = float(m.pose.pose.position.x)
            y_i = float(m.pose.pose.position.y)
            P_i = _ensure_spd(cov2_from_pose(m))
            dt_i = (t.nanoseconds - ref_ns) * 1e-9  # <= 0 si es más viejo que ref
            inputs_for_log.append((d, dt_i, x_i, y_i, P_i))

        # ---------- Seed ----------
        d0, m0, t0, _ = entries[0]
        x = np.array([m0.pose.pose.position.x, m0.pose.pose.position.y], dtype=float)
        P = _ensure_spd(cov2_from_pose(m0))

        used = [(d0, t0.nanoseconds)]
        rejected = []
        pair_w = []  # lista de fusiones pairwise: (d_new, w_prev)

        # Pesos efectivos sobre matrices de información (aprox. interpretable)
        # Regla: P_inv_new = w * P_inv_prev + (1-w) * P_inv_newDrone
        # => alphas_existentes *= w ; alpha_newDrone = (1-w)
        alphas = {d0: 1.0}
        seed = d0

        # ---------- Fusion secuencial ----------
        for (d, m, t, _) in entries[1:]:
            x2 = np.array([m.pose.pose.position.x, m.pose.pose.position.y], dtype=float)
            P2 = _ensure_spd(cov2_from_pose(m))

            d2 = maha_d2(x, P, x2, P2)
            if d2 > self.maha_gate_chi2:
                rejected.append((d, d2))
                continue

            x, P, w = covariance_intersection_pair(x, P, x2, P2, criterion=self.criterion)
            pair_w.append((d, w))

            # actualiza pesos efectivos
            for k in list(alphas.keys()):
                alphas[k] *= w
            alphas[d] = 1.0 - w

            used.append((d, t.nanoseconds))

        if len(used) < self.min_sources:
            self._throttled_info(f"not enough after gating: used={len(used)} rejected={rejected}")
            return

        # ---------- Publicación ----------
        stamp_sec = ref_ns * 1e-9
        out_stamp = rclpy.time.Time(seconds=stamp_sec).to_msg()
        out = pose_from_state(x, _symmetrize(P), out_stamp, self.world_frame)
        self.pub.publish(out)

        self._last_pub_ref_stamp_ns = ref_ns
        self._pub_count += 1

        # ---------- Log completo ----------
        if self.debug:
            # span temporal real de los usados
            dt_span = (max(ns for _, ns in used) - min(ns for _, ns in used)) * 1e-9

            # normaliza alphas para que sean legibles (suman 1)
            s = sum(alphas.values()) if len(alphas) > 0 else 1.0
            alphas_norm = [(d, alphas[d] / s) for d, _ in used if d in alphas]
            alphas_norm.sort(key=lambda kv: kv[1], reverse=True)

            # formato inputs (solo drones “frescos” en ventana, antes de gating)
            inputs_lines = []
            for (d, dt_i, x_i, y_i, P_i) in inputs_for_log:
                inputs_lines.append(
                    f"  - {d}: dt={dt_i:+.3f}s  pos=({x_i:.2f},{y_i:.2f})  P={_fmt_P(P_i)}"
                )

            # formato pairwise w (w es peso del acumulado previo; (1-w) el del dron nuevo en esa fusión)
            pair_lines = []
            for (d, w) in pair_w:
                pair_lines.append(f"  - fuse+{d}: w_prev={w:.2f}  w_new={1.0-w:.2f}")

            # formato pesos finales por dron
            wfinal_str = ", ".join([f"{d}:{w:.2f}" for d, w in alphas_norm])

            used_names = [d for d, _ in used]
            rej_str = ", ".join([f"{d}(d2={d2:.2f})" for d, d2 in rejected]) if rejected else "[]"

            self.get_logger().info(
                f"PUBLISHED #{self._pub_count}: seed={seed} used={len(used)}/{len(entries)} "
                f"used_list={used_names} dt_span={dt_span:.3f}s\n"
                f"inputs:\n" + "\n".join(inputs_lines) + "\n"
                f"pairwise_w:\n" + ("\n".join(pair_lines) if pair_lines else "  - (no pair fusions)") + "\n"
                f"w_final(norm): {wfinal_str}\n"
                f"fused: ({x[0]:.2f},{x[1]:.2f})  P={_fmt_P(_symmetrize(P))}  rejected={rej_str}"
            )

def main(args=None):
    rclpy.init(args=args)
    node = SwarmCIFusionAsync()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

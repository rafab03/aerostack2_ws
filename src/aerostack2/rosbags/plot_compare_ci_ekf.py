#!/usr/bin/env python3
import argparse
import glob
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message


# -----------------------------
# ROSBAG utils
# -----------------------------
def find_db3(bag_dir: str) -> str:
    dbs = sorted(glob.glob(f"{bag_dir}/*.db3"))
    if not dbs:
        raise RuntimeError(f"No encuentro .db3 dentro de: {bag_dir}")
    return dbs[0]


def list_topics(db_path: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name FROM topics ORDER BY name ASC")
    out = [r[0] for r in cur.fetchall()]
    con.close()
    return out


def load_topic_xy_abs_time(db_path: str, topic_name: str):
    """
    Carga un msg tipo PoseWithCovarianceStamped-like:
      msg.pose.pose.position.x/y
    Devuelve (t_abs [s], x, y)
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT id, name, type FROM topics WHERE name = ?", (topic_name,))
    row = cur.fetchone()
    if row is None:
        available = list_topics(db_path)
        raise RuntimeError(
            f"Topic no está en el bag: {topic_name}\nDisponibles:\n" + "\n".join(available)
        )

    topic_id, _, msg_type = row
    msg_cls = get_message(msg_type)

    cur.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id = ? ORDER BY timestamp ASC",
        (topic_id,)
    )
    rows = cur.fetchall()
    con.close()

    t, x, y = [], [], []
    for ts, data in rows:
        msg = deserialize_message(data, msg_cls)
        p = msg.pose.pose.position
        t.append(ts * 1e-9)
        x.append(float(p.x))
        y.append(float(p.y))

    return np.array(t), np.array(x), np.array(y)


# -----------------------------
# Smoothing (coherente con tus scripts)
# -----------------------------
def moving_median(y, k: int):
    if k <= 1:
        return y.astype(float).copy()
    k = int(k)
    if k % 2 == 0:
        k += 1
    pad = k // 2
    ypad = np.pad(y, (pad, pad), mode="edge")
    out = np.empty_like(y, dtype=float)
    for i in range(len(y)):
        out[i] = np.median(ypad[i:i + k])
    return out


def moving_average(y, k: int):
    if k <= 1:
        return y.astype(float).copy()
    k = int(k)
    w = np.ones(k, dtype=float) / float(k)
    ypad = np.pad(y, (k // 2, k - 1 - k // 2), mode="edge")
    return np.convolve(ypad, w, mode="valid")


def smooth_ekf(y, median_k=9, mean_k=5):
    # mediana quita outliers, media suaviza
    return moving_average(moving_median(y, median_k), mean_k)


def smooth_ci(y, smooth_k=9):
    # media móvil simple
    return moving_average(y, smooth_k)


# -----------------------------
# Helpers
# -----------------------------
def parse_int_list(s: str):
    if s is None or s.strip() == "":
        return []
    return [int(x) for x in s.split(",") if x.strip() != ""]


def interpolate_to(t_src, x_src, y_src, t_dst):
    x = np.interp(t_dst, t_src, x_src)
    y = np.interp(t_dst, t_src, y_src)
    return x, y


def metrics_from_error(err):
    """
    err: array de |pos - GT| [m]
    """
    err = np.asarray(err)
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    p95 = float(np.percentile(err, 95))
    osc = float(np.std(err - np.mean(err)))  # oscilación alrededor del error medio
    return mae, rmse, osc, p95


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bag", required=True, help="Directorio del rosbag2 (contiene .db3)")
    ap.add_argument("--ekf_drone", type=int, default=0, help="EKF a usar para comparar (default drone0)")
    ap.add_argument("--drones", default="0,1,2", help="Drones para plotear ray_ground (ej: 0,1,2)")

    # GT fija
    ap.add_argument("--gtx", type=float, default=5.0)
    ap.add_argument("--gty", type=float, default=0.0)

    # Suavizados
    ap.add_argument("--ekf_median_k", type=int, default=9)
    ap.add_argument("--ekf_mean_k", type=int, default=5)
    ap.add_argument("--ci_smooth_k", type=int, default=9)

    # Límites forzados
    ap.add_argument("--x_ylim", default="2,5.5", help="ylim para X(t) (default 2,5.5)")
    ap.add_argument("--y_ylim", default="-0.5,0.5", help="ylim para Y(t) (default -0.5,0.5)")
    ap.add_argument("--err_ylim", default="0,1.0", help="ylim para error(t) (default 0,1.0)")

    # Recuadro métricas
    ap.add_argument("--metrics_pos", default="upper right",
                    choices=["upper left", "upper right", "lower left", "lower right"],
                    help="Posición del recuadro de métricas dentro del subplot de error")

    ap.add_argument("--save_prefix", default="", help="Si se indica, guarda PNG: <prefix>_compare.png")
    args = ap.parse_args()

    def parse_lim(s):
        a, b = s.split(",")
        return float(a), float(b)

    x_ylim = parse_lim(args.x_ylim)
    y_ylim = parse_lim(args.y_ylim)
    err_ylim = parse_lim(args.err_ylim)

    db = find_db3(args.bag)
    drones = parse_int_list(args.drones)

    # Topics
    ekf_topic = f"/swarm/drone{args.ekf_drone}/ekf_target"
    ci_topic = "/swarm/fused_target"
    ray_topics = {d: f"/swarm/drone{d}/detections_ray_ground" for d in drones}

    # Load outputs
    t_ci_abs, x_ci_raw, y_ci_raw = load_topic_xy_abs_time(db, ci_topic)
    t_ekf_abs, x_ekf_raw, y_ekf_raw = load_topic_xy_abs_time(db, ekf_topic)

    # Load inputs (ray_ground)
    rays = {}
    for d, tp in ray_topics.items():
        try:
            rays[d] = load_topic_xy_abs_time(db, tp)
        except RuntimeError:
            rays[d] = None

    # Smooth outputs
    x_ci_s = smooth_ci(x_ci_raw, args.ci_smooth_k)
    y_ci_s = smooth_ci(y_ci_raw, args.ci_smooth_k)
    x_ekf_s = smooth_ekf(x_ekf_raw, args.ekf_median_k, args.ekf_mean_k)
    y_ekf_s = smooth_ekf(y_ekf_raw, args.ekf_median_k, args.ekf_mean_k)

    # ---------------------------------------------------------
    # SOLUCIÓN: que "empiecen en 0" SIN perder alineación
    # 1) recortamos todo al primer instante común entre CI y EKF
    # 2) hacemos t=0 en ese instante común
    # ---------------------------------------------------------
    t_common_start_abs = max(float(t_ci_abs[0]), float(t_ekf_abs[0]))
    t_common_end_abs = min(float(t_ci_abs[-1]), float(t_ekf_abs[-1]))
    if t_common_end_abs <= t_common_start_abs + 1e-3:
        raise RuntimeError("No hay solape temporal entre CI y EKF en este bag.")

    # recorta CI y EKF al solape y luego t=0 en el comienzo del solape
    m_ci = (t_ci_abs >= t_common_start_abs) & (t_ci_abs <= t_common_end_abs)
    m_ek = (t_ekf_abs >= t_common_start_abs) & (t_ekf_abs <= t_common_end_abs)

    t_ci = t_ci_abs[m_ci] - t_common_start_abs
    x_ci = x_ci_s[m_ci]
    y_ci = y_ci_s[m_ci]

    t_ek = t_ekf_abs[m_ek] - t_common_start_abs
    x_ek = x_ekf_s[m_ek]
    y_ek = y_ekf_s[m_ek]

    if len(t_ci) < 5 or len(t_ek) < 5:
        raise RuntimeError("Muy pocos puntos en el intervalo solapado para comparar.")

    # timeline común para comparar (usa CI)
    t_common = t_ci.copy()

    # interp EKF a timeline CI
    x_ek_c, y_ek_c = interpolate_to(t_ek, x_ek, y_ek, t_common)
    x_ci_c, y_ci_c = x_ci.copy(), y_ci.copy()

    # Errors
    err_ci = np.sqrt((x_ci_c - args.gtx)**2 + (y_ci_c - args.gty)**2)
    err_ekf = np.sqrt((x_ek_c - args.gtx)**2 + (y_ek_c - args.gty)**2)

    ci_mae, ci_rmse, ci_osc, ci_p95 = metrics_from_error(err_ci)
    ek_mae, ek_rmse, ek_osc, ek_p95 = metrics_from_error(err_ekf)

    # Para ray_ground: recortar al mismo solape absoluto y usar el MISMO 0
    # (solo para plot; no afecta a métricas)
    rays_rel = {}
    for d, data in rays.items():
        if data is None:
            rays_rel[d] = None
            continue
        t_abs_r, xr, yr = data
        mr = (t_abs_r >= t_common_start_abs) & (t_abs_r <= t_common_end_abs)
        tr = t_abs_r[mr] - t_common_start_abs
        rays_rel[d] = (tr, xr[mr], yr[mr])

    # -----------------------------
    # Plot layout como tu referencia
    # -----------------------------
    fig = plt.figure(figsize=(18, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.1, 1.0], hspace=0.35, wspace=0.25)

    ax_x = fig.add_subplot(gs[0, 0:2])
    ax_y = fig.add_subplot(gs[0, 2:4])
    ax_err = fig.add_subplot(gs[1, 0])
    ray_axes = [fig.add_subplot(gs[1, 1 + j]) for j in range(3)]

    # ---- X(t)
    ax_x.plot(t_common, x_ek_c, label=f"EKF x (drone{args.ekf_drone})")
    ax_x.plot(t_common, x_ci_c, label="CI x (fused_target)")
    ax_x.hlines(args.gtx, t_common[0], t_common[-1], linestyles="dashed", label="GT x")
    ax_x.set_title("X(t): GT vs EKF vs CI")
    ax_x.set_xlabel("t [s] (t=0 en comienzo del solape)")
    ax_x.set_ylabel("x [m]")
    ax_x.grid(True)
    ax_x.legend(fontsize=9)
    ax_x.set_ylim(*x_ylim)

    # ---- Y(t)
    ax_y.plot(t_common, y_ek_c, label=f"EKF y (drone{args.ekf_drone})")
    ax_y.plot(t_common, y_ci_c, label="CI y (fused_target)")
    ax_y.hlines(args.gty, t_common[0], t_common[-1], linestyles="dashed", label="GT y")
    ax_y.set_title("Y(t): GT vs EKF vs CI")
    ax_y.set_xlabel("t [s] (t=0 en comienzo del solape)")
    ax_y.set_ylabel("y [m]")
    ax_y.grid(True)
    ax_y.legend(fontsize=9)
    ax_y.set_ylim(*y_ylim)

    # ---- error(t)
    ax_err.plot(t_common, err_ekf, label="|error| EKF")
    ax_err.plot(t_common, err_ci, label="|error| CI")
    ax_err.set_title("Error absoluto de posición [m]")
    ax_err.set_xlabel("t [s] (t=0 en comienzo del solape)")
    ax_err.set_ylabel("error [m]")
    ax_err.grid(True)
    ax_err.legend(fontsize=9)
    ax_err.set_ylim(*err_ylim)

    # Recuadro métricas
    text = (
        f"EKF: MAE={ek_mae:.3f}  RMSE={ek_rmse:.3f}  P95={ek_p95:.3f}\n"
        f"     osc(σ[e-ē])={ek_osc:.3f}\n"
        f"CI : MAE={ci_mae:.3f}  RMSE={ci_rmse:.3f}  P95={ci_p95:.3f}\n"
        f"     osc(σ[e-ē])={ci_osc:.3f}"
    )

    pos_map = {
        "upper left": (0.02, 0.98, "top", "left"),
        "upper right": (0.98, 0.98, "top", "right"),
        "lower left": (0.02, 0.02, "bottom", "left"),
        "lower right": (0.98, 0.02, "bottom", "right"),
    }
    xA, yA, va, ha = pos_map[args.metrics_pos]
    ax_err.text(
        0.05, 0.50,   # <-- cambia estos valores
        text,
        transform=ax_err.transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round", alpha=0.85)
    )
    # ---- ray_ground x(t), y(t) por dron (hasta 3)
    for idx_plot, axr in enumerate(ray_axes):
        if idx_plot >= len(drones):
            axr.set_title("sin datos")
            axr.set_xlim(0, 1)
            axr.set_ylim(0, 1)
            axr.grid(True)
            continue

        d = drones[idx_plot]
        data = rays_rel.get(d, None)
        if data is None:
            axr.set_title(f"drone{d}: (sin datos)")
            axr.set_xlim(0, 1)
            axr.set_ylim(0, 1)
            axr.grid(True)
            continue

        tr, xr, yr = data
        if len(tr) == 0:
            axr.set_title(f"drone{d}: (sin datos en ventana)")
            axr.set_xlim(0, 1)
            axr.set_ylim(0, 1)
            axr.grid(True)
            continue

        axr.plot(tr, xr, label="x")
        axr.plot(tr, yr, label="y")
        axr.hlines(args.gtx, tr[0], tr[-1], linestyles="dashed", label="GT x")
        axr.hlines(args.gty, tr[0], tr[-1], linestyles="dashdot", label="GT y")

        axr.set_title(f"drone{d}: RayGround x(t), y(t)")
        axr.set_xlabel("t [s] (t=0 en comienzo del solape)")
        axr.set_ylabel("[m]")
        axr.grid(True)
        axr.legend(fontsize=8)

    fig.suptitle(
        f"Drone{args.ekf_drone} – Swarm target estimation (t=0 en el primer instante común CI/EKF)",
        fontsize=14
    )
    plt.tight_layout()

    if args.save_prefix:
        out = f"{args.save_prefix}_compare_ci_vs_ekf_like_ref_fixedylims_aligned0.png"
        plt.savefig(out, dpi=220, bbox_inches="tight")
        print(f"Guardado: {out}")

    plt.show()


if __name__ == "__main__":
    main()

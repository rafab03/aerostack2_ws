#!/usr/bin/env python3
import argparse
import glob
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message


# ---------------------------------------------------------
# ROSBAG utils
# ---------------------------------------------------------

def find_db3(bag_dir: str) -> str:
    dbs = sorted(glob.glob(f"{bag_dir}/*.db3"))
    if not dbs:
        raise RuntimeError(f"No encuentro .db3 dentro de: {bag_dir}")
    return dbs[0]


def load_topic_xy_abs_time(db_path: str, topic_name: str):
    """
    Carga PoseWithCovarianceStamped y devuelve:
      t_abs [s] (NO normalizado), x, y
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT id, name, type FROM topics WHERE name = ?", (topic_name,))
    row = cur.fetchone()
    if row is None:
        con.close()
        raise RuntimeError(f"Topic no encontrado: {topic_name}")

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
        t.append(ts * 1e-9)  # abs seconds
        x.append(float(p.x))
        y.append(float(p.y))

    return np.array(t), np.array(x), np.array(y)


# ---------------------------------------------------------
# Smoothing (anti spikes)
# ---------------------------------------------------------

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


def smooth_series(y, median_k=9, mean_k=5):
    # mediana quita picos, media suaviza
    y1 = moving_median(y, median_k)
    y2 = moving_average(y1, mean_k)
    return y2


# ---------------------------------------------------------
# Plot per drone (CI-like layout)
# ---------------------------------------------------------

def plot_drone(
    db_path: str,
    drone_id: int,
    drones=(0, 1, 2),
    gtx=5.0,
    gty=0.0,
    median_k=9,
    mean_k=5,
    show_raw=False,   # si quieres ver también sin suavizar, pon True
):
    # Topics
    ekf_topic = f"/swarm/drone{drone_id}/ekf_target"
    ray_topics = {j: f"/swarm/drone{j}/detections_ray_ground" for j in drones}

    # Load EKF self
    t_ekf, x_ekf, y_ekf = load_topic_xy_abs_time(db_path, ekf_topic)

    # Load rayground from all drones
    rays = {}
    for j in drones:
        try:
            t_r, x_r, y_r = load_topic_xy_abs_time(db_path, ray_topics[j])
            rays[j] = (t_r, x_r, y_r)
        except RuntimeError as e:
            # Si un dron no tiene ese topic en el bag, lo saltamos
            rays[j] = (np.array([]), np.array([]), np.array([]))
            print(f"[WARN] {e}")

    if len(t_ekf) == 0:
        print(f"[WARN] Drone{drone_id}: EKF vacío -> no ploteo figura.")
        return

    # ---- Align time to a common t0 (per-figure) ----
    t0_candidates = [t_ekf[0]]
    for j in drones:
        t_r, _, _ = rays[j]
        if len(t_r) > 0:
            t0_candidates.append(t_r[0])
    t0 = float(min(t0_candidates))

    tE = t_ekf - t0

    # ---- Smooth EKF and compute absolute position error (2D) ----
    xE_s = smooth_series(x_ekf, median_k, mean_k)
    yE_s = smooth_series(y_ekf, median_k, mean_k)
    err = np.sqrt((xE_s - gtx) ** 2 + (yE_s - gty) ** 2)
    err_s = smooth_series(err, median_k, mean_k)

    # ---- Figure layout like your CI screenshot, but per drone ----
    # Grid: 2 rows x 4 cols
    # Top: EKF x spans cols 0-1, EKF y spans cols 2-3
    # Bottom: error col0, measures drone0 col1, drone1 col2, drone2 col3
    fig = plt.figure(figsize=(18, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.05, 1.0])

    ax_x = fig.add_subplot(gs[0, 0:2])
    ax_y = fig.add_subplot(gs[0, 2:4])
    ax_err = fig.add_subplot(gs[1, 0])

    ax_meas = {}
    ax_meas[drones[0]] = fig.add_subplot(gs[1, 1])
    ax_meas[drones[1]] = fig.add_subplot(gs[1, 2])
    ax_meas[drones[2]] = fig.add_subplot(gs[1, 3])

    fig.suptitle(f"Drone{drone_id} – Swarm target estimation (GT fixed at ({gtx:.1f},{gty:.1f}))")

    # ---- Top-left: EKF x(t) ----
    ax_x.plot(tE, xE_s, label=f"EKF x (Drone{drone_id}) (MA{mean_k}+MED{median_k})")
    if show_raw:
        ax_x.plot(tE, x_ekf, alpha=0.25, label="EKF x raw")
    ax_x.hlines(gtx, 0, tE[-1], linestyles="dashed", label="GT x")
    ax_x.set_title("EKF X(t): GT vs EKF")
    ax_x.set_xlabel("t [s]")
    ax_x.set_ylabel("x [m]")
    ax_x.grid(True)
    ax_x.legend(fontsize=9)

    # ---- Top-right: EKF y(t) ----
    ax_y.plot(tE, yE_s, label=f"EKF y (Drone{drone_id}) (MA{mean_k}+MED{median_k})")
    if show_raw:
        ax_y.plot(tE, y_ekf, alpha=0.25, label="EKF y raw")
    ax_y.hlines(gty, 0, tE[-1], linestyles="dashed", label="GT y")
    ax_y.set_title("EKF Y(t): GT vs EKF")
    ax_y.set_xlabel("t [s]")
    ax_y.set_ylabel("y [m]")
    ax_y.grid(True)
    ax_y.legend(fontsize=9)

    # ---- Bottom-left: absolute position error ----
    ax_err.plot(tE, err_s, label=f"|pos error| (MA{mean_k}+MED{median_k})")
    if show_raw:
        err_raw = np.sqrt((x_ekf - gtx) ** 2 + (y_ekf - gty) ** 2)
        ax_err.plot(tE, err_raw, alpha=0.25, label="error raw")
    ax_err.set_title("Error absoluto de posición [m] (EKF)")
    ax_err.set_xlabel("t [s]")
    ax_err.set_ylabel("error [m]")
    ax_err.grid(True)
    ax_err.legend(fontsize=9)

    # ---- Bottom: measures used (RayGround) per drone ----
    for j in drones:
        ax = ax_meas[j]
        t_r, x_r, y_r = rays[j]
        if len(t_r) == 0:
            ax.set_title(f"drone{j}: (sin datos)")
            ax.grid(True)
            continue

        tR = t_r - t0
        xR_s = smooth_series(x_r, median_k, mean_k)
        yR_s = smooth_series(y_r, median_k, mean_k)

        ax.plot(tR, xR_s, label="x")
        ax.plot(tR, yR_s, label="y")
        if show_raw:
            ax.plot(tR, x_r, alpha=0.20, linestyle=":", label="x raw")
            ax.plot(tR, y_r, alpha=0.20, linestyle=":", label="y raw")

        ax.hlines(gtx, 0, max(tR[-1], tE[-1]), linestyles="dashed", label="GT x")
        ax.hlines(gty, 0, max(tR[-1], tE[-1]), linestyles="dashed", label="GT y")

        ax.set_title(f"drone{j}: RayGround x(t), y(t)")
        ax.set_xlabel("t [s]")
        ax.grid(True)
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bag", required=True, help="Directorio del rosbag2 (contiene .db3)")
    ap.add_argument("--gtx", type=float, default=5.0)
    ap.add_argument("--gty", type=float, default=0.0)
    ap.add_argument("--median_k", type=int, default=9, help="Ventana mediana (quita picos)")
    ap.add_argument("--mean_k", type=int, default=5, help="Ventana media (suaviza)")
    ap.add_argument("--show_raw", action="store_true", help="Muestra también curvas sin suavizar (alpha baja)")
    args = ap.parse_args()

    db = find_db3(args.bag)

    drones = (0, 1, 2)
    for drone_id in drones:
        plot_drone(
            db_path=db,
            drone_id=drone_id,
            drones=drones,
            gtx=args.gtx,
            gty=args.gty,
            median_k=args.median_k,
            mean_k=args.mean_k,
            show_raw=args.show_raw,
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import glob
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message


def find_db3(bag_dir: str) -> str:
    dbs = sorted(glob.glob(f"{bag_dir}/*.db3"))
    if not dbs:
        raise RuntimeError(f"No encuentro .db3 dentro de: {bag_dir}")
    return dbs[0]


def load_topic_xy(db_path: str, topic_name: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT id, name, type FROM topics WHERE name = ?", (topic_name,))
    row = cur.fetchone()
    if row is None:
        cur.execute("SELECT name FROM topics")
        available = [r[0] for r in cur.fetchall()]
        con.close()
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
        msg = deserialize_message(data, msg_cls)  # PoseWithCovarianceStamped
        p = msg.pose.pose.position
        t.append(ts * 1e-9)
        x.append(float(p.x))
        y.append(float(p.y))

    t = np.array(t)
    if len(t) > 0:
        t = t - t[0]
    return t, np.array(x), np.array(y)


def moving_average(v: np.ndarray, window: int) -> np.ndarray:
    """Media móvil simple; devuelve mismo tamaño. window impar recomendado."""
    if window <= 1 or len(v) < window:
        return v
    w = int(window)
    kernel = np.ones(w) / w
    # pad para mantener longitud
    pad = w // 2
    vpad = np.pad(v, (pad, pad), mode="edge")
    return np.convolve(vpad, kernel, mode="valid")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bag", required=True, help="Carpeta del rosbag (contiene metadata.yaml y .db3)")
    ap.add_argument("--gtx", type=float, default=5.0)
    ap.add_argument("--gty", type=float, default=0.0)
    ap.add_argument("--smooth", type=int, default=9, help="Ventana media móvil (samples). 1 desactiva.")
    ap.add_argument("--save", default="", help="Guarda PNG si lo indicas (ej: fig.png)")
    args = ap.parse_args()

    topics = {
        "CI": "/swarm/fused_target",
        "drone0": "/swarm/drone0/detections_ray_ground",
        "drone1": "/swarm/drone1/detections_ray_ground",
        "drone2": "/swarm/drone2/detections_ray_ground",
    }

    db_path = find_db3(args.bag)

    series = {name: load_topic_xy(db_path, topic) for name, topic in topics.items()}

    t_ci, x_ci, y_ci = series["CI"]
    if len(t_ci) < 2:
        raise RuntimeError("CI tiene muy pocos puntos. ¿Estás grabando /swarm/fused_target?")

    # Suavizado CI
    x_ci_s = moving_average(x_ci, args.smooth)
    y_ci_s = moving_average(y_ci, args.smooth)

    # GT en timeline CI
    gt_x_ci = np.full_like(t_ci, args.gtx)
    gt_y_ci = np.full_like(t_ci, args.gty)

    # Error SOLO CI (y suavizado)
    err_ci = np.sqrt((x_ci - args.gtx) ** 2 + (y_ci - args.gty) ** 2)
    err_ci_s = moving_average(err_ci, args.smooth)

    # ------- Layout (2 filas x 4 columnas)
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.1, 1.0], hspace=0.35, wspace=0.28)

    ax_x = fig.add_subplot(gs[0, 0:2])
    ax_y = fig.add_subplot(gs[0, 2:4])

    ax_err = fig.add_subplot(gs[1, 0])
    ax_d0 = fig.add_subplot(gs[1, 1])
    ax_d1 = fig.add_subplot(gs[1, 2])
    ax_d2 = fig.add_subplot(gs[1, 3])

    # ---- Arriba izquierda: X(t) SOLO GT vs CI
    ax_x.plot(t_ci, gt_x_ci, label="GT x")
    ax_x.plot(t_ci, x_ci_s, label=f"CI x (MA{args.smooth})" if args.smooth > 1 else "CI x")
    ax_x.set_title("X(t): GT vs CI")
    ax_x.set_xlabel("t [s]")
    ax_x.set_ylabel("x [m]")
    ax_x.set_ylim(0, 5.2)
    ax_x.grid(True)
    ax_x.legend(fontsize=9)

    # ---- Arriba derecha: Y(t) SOLO GT vs CI
    ax_y.plot(t_ci, gt_y_ci, label="GT y")
    ax_y.plot(t_ci, y_ci_s, label=f"CI y (MA{args.smooth})" if args.smooth > 1 else "CI y")
    ax_y.set_title("Y(t): GT vs CI")
    ax_y.set_xlabel("t [s]")
    ax_y.set_ylabel("y [m]")
    ax_y.set_ylim(-0.5, 0.5) 
    ax_y.grid(True)
    ax_y.legend(fontsize=9)

    # ---- Abajo izquierda: Error(t) SOLO CI
    ax_err.plot(t_ci, err_ci_s, label=f"CI error (MA{args.smooth})" if args.smooth > 1 else "CI error")
    ax_err.set_title("Error(t) [m] (CI only)")
    ax_err.set_xlabel("t [s]")
    ax_err.set_ylabel("error [m]")
    ax_err.set_ylim(0, 1.0)
    ax_err.grid(True)
    ax_err.legend(fontsize=9)

    # ---- Abajo: cajas por dron (x e y)
    def plot_drone_box(ax, name):
        t_d, x_d, y_d = series[name]
        # suavizado suave en drones para visual (opcional)
        x_ds = moving_average(x_d, max(3, args.smooth // 3)) if args.smooth > 1 else x_d
        y_ds = moving_average(y_d, max(3, args.smooth // 3)) if args.smooth > 1 else y_d

        ax.plot(t_d, x_ds, label="x")
        ax.plot(t_d, y_ds, label="y")
        # Líneas GT (x e y)
        tmax = max(float(t_ci[-1]), float(t_d[-1]) if len(t_d) else 0.0)
        ax.hlines(args.gtx, xmin=0, xmax=tmax, linestyles="dashed", alpha=0.6, label="GT x")
        ax.hlines(args.gty, xmin=0, xmax=tmax, linestyles="dashed", alpha=0.6, label="GT y")
        ax.set_title(f"{name}: x(t), y(t)")
        ax.set_xlabel("t [s]")
        ax.grid(True)
        ax.legend(fontsize=8)

    plot_drone_box(ax_d0, "drone0")
    plot_drone_box(ax_d1, "drone1")
    plot_drone_box(ax_d2, "drone2")

    fig.suptitle("Swarm target estimation (GT fixed at (5,0))", fontsize=14)

    if args.save:
        plt.savefig(args.save, dpi=220, bbox_inches="tight")
        print(f"Guardado: {args.save}")

    plt.show()


if __name__ == "__main__":
    main()

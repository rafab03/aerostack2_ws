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


def list_topics(db_path: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name, type FROM topics")
    rows = cur.fetchall()
    con.close()
    return rows


def _get_topic_info(db_path: str, topic_name: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id, name, type FROM topics WHERE name = ?", (topic_name,))
    row = cur.fetchone()
    con.close()
    return row  # (id, name, type) or None


def load_topic_pose_xy(db_path: str, topic_name: str):
    """
    Carga PoseWithCovarianceStamped -> arrays (t,x,y).
    """
    info = _get_topic_info(db_path, topic_name)
    if info is None:
        available = [n for n, _ in list_topics(db_path)]
        raise RuntimeError(
            f"Topic no está en el bag: {topic_name}\nDisponibles:\n" + "\n".join(available)
        )

    topic_id, _, msg_type = info
    msg_cls = get_message(msg_type)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
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

    t = np.array(t)
    if len(t) > 0:
        t = t - t[0]
    return t, np.array(x), np.array(y)


def load_topic_trackedperson_xy_for_id(db_path: str, topic_name: str, person_id: int):
    """
    Carga TrackedPersonArray, filtra por tp.id==person_id y devuelve (t,x,y) para ese ID.
    """
    info = _get_topic_info(db_path, topic_name)
    if info is None:
        available = [n for n, _ in list_topics(db_path)]
        raise RuntimeError(
            f"Topic no está en el bag: {topic_name}\nDisponibles:\n" + "\n".join(available)
        )

    topic_id, _, msg_type = info
    msg_cls = get_message(msg_type)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id = ? ORDER BY timestamp ASC",
        (topic_id,)
    )
    rows = cur.fetchall()
    con.close()

    t, x, y = [], [], []
    for ts, data in rows:
        msg = deserialize_message(data, msg_cls)  # TrackedPersonArray
        chosen = None
        for tp in msg.persons:
            if int(tp.id) == int(person_id):
                chosen = tp
                break
        if chosen is None:
            continue
        p = chosen.pose.pose.position
        t.append(ts * 1e-9)
        x.append(float(p.x))
        y.append(float(p.y))

    t = np.array(t)
    if len(t) > 0:
        t = t - t[0]
    return t, np.array(x), np.array(y)


def moving_average(v: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or len(v) < window:
        return v
    w = int(window)
    kernel = np.ones(w) / w
    pad = w // 2
    vpad = np.pad(v, (pad, pad), mode="edge")
    return np.convolve(vpad, kernel, mode="valid")


def auto_ylim(values, pad_abs: float, pad_rel: float, floor: float = None):
    """
    Calcula límites y del estilo: [min-pad, max+pad] con pad absoluto y relativo al rango.
    - values: iterable de arrays/listas (se concatenan)
    - pad_abs: margen mínimo absoluto
    - pad_rel: margen relativo al rango (0.1 = 10%)
    - floor: si no es None, fuerza límite inferior >= floor (útil para error con floor=0)
    """
    arrs = []
    for v in values:
        if v is None:
            continue
        v = np.asarray(v)
        if v.size == 0:
            continue
        arrs.append(v)

    if not arrs:
        return None

    allv = np.concatenate(arrs)
    vmin = float(np.min(allv))
    vmax = float(np.max(allv))

    if np.isclose(vmin, vmax):
        # si todo es casi constante, pon un pequeño rango
        base = abs(vmin) if abs(vmin) > 1e-6 else 1.0
        span = max(pad_abs, 0.02 * base)
        lo, hi = vmin - span, vmax + span
    else:
        span = vmax - vmin
        pad = max(pad_abs, pad_rel * span)
        lo, hi = vmin - pad, vmax + pad

    if floor is not None:
        lo = max(lo, float(floor))

    return (lo, hi)


def plot_for_id(
    db_path: str,
    person_id: int,
    gtx: float,
    gty: float,
    smooth: int,
    save_prefix: str,
    pad_x: float,
    pad_y: float,
    pad_err: float,
    pad_rel: float,
):
    # Topics:
    ci_topic = f"/swarm/people_ci_fused/id_{person_id}"
    per_drone_topics = {
        "drone0": "/swarm/drone0/people_with_global_id",
        "drone1": "/swarm/drone1/people_with_global_id",
        "drone2": "/swarm/drone2/people_with_global_id",
    }

    # Carga CI
    t_ci, x_ci, y_ci = load_topic_pose_xy(db_path, ci_topic)
    if len(t_ci) < 2:
        raise RuntimeError(f"CI tiene muy pocos puntos en {ci_topic}. ¿Se grabó ese topic?")

    x_ci_s = moving_average(x_ci, smooth)
    y_ci_s = moving_average(y_ci, smooth)

    gt_x_ci = np.full_like(t_ci, gtx)
    gt_y_ci = np.full_like(t_ci, gty)

    err_ci = np.sqrt((x_ci - gtx) ** 2 + (y_ci - gty) ** 2)
    err_ci_s = moving_average(err_ci, smooth)

    # Carga drones (filtrando por ID)
    series = {}
    for name, topic in per_drone_topics.items():
        t_d, x_d, y_d = load_topic_trackedperson_xy_for_id(db_path, topic, person_id)
        series[name] = (t_d, x_d, y_d)

    # --------- límites automáticos (zoom bonito)
    # Para x/y metemos CI + GT + drones (si existen)
    x_vals = [x_ci_s, gt_x_ci]
    y_vals = [y_ci_s, gt_y_ci]
    for (t_d, x_d, y_d) in series.values():
        if len(x_d) > 0:
            x_ds = moving_average(x_d, max(3, smooth // 3)) if smooth > 1 else x_d
            y_ds = moving_average(y_d, max(3, smooth // 3)) if smooth > 1 else y_d
            x_vals.append(x_ds)
            y_vals.append(y_ds)

    x_lim = auto_ylim(x_vals, pad_abs=pad_x, pad_rel=pad_rel)
    y_lim = auto_ylim(y_vals, pad_abs=pad_y, pad_rel=pad_rel)

    err_lim = auto_ylim([err_ci_s], pad_abs=pad_err, pad_rel=pad_rel, floor=0.0)

    # ------- Layout (2 filas x 4 columnas)
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.1, 1.0], hspace=0.35, wspace=0.28)

    ax_x = fig.add_subplot(gs[0, 0:2])
    ax_y = fig.add_subplot(gs[0, 2:4])

    ax_err = fig.add_subplot(gs[1, 0])
    ax_d0 = fig.add_subplot(gs[1, 1])
    ax_d1 = fig.add_subplot(gs[1, 2])
    ax_d2 = fig.add_subplot(gs[1, 3])

    # ---- X(t): GT vs CI
    ax_x.plot(t_ci, gt_x_ci, label="GT x")
    ax_x.plot(t_ci, x_ci_s, label=f"CI x (MA{smooth})" if smooth > 1 else "CI x")
    ax_x.set_title(f"ID {person_id} — X(t): GT vs CI")
    ax_x.set_xlabel("t [s]")
    ax_x.set_ylabel("x [m]")
    if x_lim is not None:
        ax_x.set_ylim(x_lim[0], x_lim[1])
    ax_x.grid(True)
    ax_x.legend(fontsize=9)

    # ---- Y(t): GT vs CI
    ax_y.plot(t_ci, gt_y_ci, label="GT y")
    ax_y.plot(t_ci, y_ci_s, label=f"CI y (MA{smooth})" if smooth > 1 else "CI y")
    ax_y.set_title(f"ID {person_id} — Y(t): GT vs CI")
    ax_y.set_xlabel("t [s]")
    ax_y.set_ylabel("y [m]")
    if y_lim is not None:
        ax_y.set_ylim(y_lim[0], y_lim[1])
    ax_y.grid(True)
    ax_y.legend(fontsize=9)

    # ---- Error(t): CI
    ax_err.plot(t_ci, err_ci_s, label=f"CI error (MA{smooth})" if smooth > 1 else "CI error")
    ax_err.set_title(f"ID {person_id} — Error(t) [m] (CI only)")
    ax_err.set_xlabel("t [s]")
    ax_err.set_ylabel("error [m]")
    if err_lim is not None:
        ax_err.set_ylim(err_lim[0], err_lim[1])
    ax_err.grid(True)
    ax_err.legend(fontsize=9)

    # ---- Drones: x(t), y(t) filtrados por ID
    def plot_drone_box(ax, name):
        t_d, x_d, y_d = series[name]
        if len(t_d) == 0:
            ax.set_title(f"{name}: (sin datos para ID {person_id})")
            ax.grid(True)
            return

        x_ds = moving_average(x_d, max(3, smooth // 3)) if smooth > 1 else x_d
        y_ds = moving_average(y_d, max(3, smooth // 3)) if smooth > 1 else y_d

        ax.plot(t_d, x_ds, label="x")
        ax.plot(t_d, y_ds, label="y")

        tmax = max(float(t_ci[-1]), float(t_d[-1]))
        ax.hlines(gtx, xmin=0, xmax=tmax, linestyles="dashed", alpha=0.6, label="GT x")
        ax.hlines(gty, xmin=0, xmax=tmax, linestyles="dashed", alpha=0.6, label="GT y")

        ax.set_title(f"{name} (ID {person_id}): x(t), y(t)")
        ax.set_xlabel("t [s]")
        ax.grid(True)
        ax.legend(fontsize=8)

    plot_drone_box(ax_d0, "drone0")
    plot_drone_box(ax_d1, "drone1")
    plot_drone_box(ax_d2, "drone2")

    fig.suptitle(f"Swarm CI fusion — Person ID {person_id} — GT=({gtx},{gty})", fontsize=14)

    if save_prefix:
        out = f"{save_prefix}_id{person_id}.png"
        plt.savefig(out, dpi=220, bbox_inches="tight")
        print(f"Guardado: {out}")

    plt.show()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bag", required=True, help="Carpeta del rosbag (contiene metadata.yaml y .db3)")
    ap.add_argument("--ids", default="1,2", help="IDs a plotear, ej: 1,2")
    ap.add_argument("--gt1x", type=float, default=5.0, help="GT x para ID1")
    ap.add_argument("--gt1y", type=float, default=0.0, help="GT y para ID1")
    ap.add_argument("--gt2x", type=float, default=5.0, help="GT x para ID2")
    ap.add_argument("--gt2y", type=float, default=2.0, help="GT y para ID2")
    ap.add_argument("--smooth", type=int, default=9, help="Ventana media móvil (samples). 1 desactiva.")
    ap.add_argument("--save_prefix", default="", help="Prefijo para guardar PNGs (ej: figs/ci)")

    # NUEVO: control de zoom
    ap.add_argument("--pad_x", type=float, default=0.25, help="Margen absoluto en eje Y de X(t) [m]")
    ap.add_argument("--pad_y", type=float, default=0.25, help="Margen absoluto en eje Y de Y(t) [m]")
    ap.add_argument("--pad_err", type=float, default=0.05, help="Margen absoluto en eje Y de Error(t) [m]")
    ap.add_argument("--pad_rel", type=float, default=0.10, help="Margen relativo (10%% del rango)")

    args = ap.parse_args()

    db_path = find_db3(args.bag)

    ids = [int(s.strip()) for s in args.ids.split(",") if s.strip()]
    gt_map = {
        1: (args.gt1x, args.gt1y),
        2: (args.gt2x, args.gt2y),
    }

    for pid in ids:
        if pid not in gt_map:
            raise RuntimeError(f"No tengo GT para ID {pid}. Ajusta gt_map/args.")
        gtx, gty = gt_map[pid]
        plot_for_id(
            db_path=db_path,
            person_id=pid,
            gtx=gtx,
            gty=gty,
            smooth=args.smooth,
            save_prefix=args.save_prefix,
            pad_x=args.pad_x,
            pad_y=args.pad_y,
            pad_err=args.pad_err,
            pad_rel=args.pad_rel,
        )


if __name__ == "__main__":
    main()

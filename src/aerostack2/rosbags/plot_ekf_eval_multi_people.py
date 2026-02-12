#!/usr/bin/env python3
import argparse
import glob
import sqlite3
from typing import Dict, List, Tuple, Optional

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


def list_topics(db_path: str) -> List[Tuple[str, str]]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name, type FROM topics ORDER BY name ASC")
    rows = cur.fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]


def _topic_meta(db_path: str, topic_name: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id, name, type FROM topics WHERE name = ?", (topic_name,))
    row = cur.fetchone()
    con.close()
    return row  # (topic_id, name, type) or None


def load_pose_topic_xy_abs_time(db_path: str, topic_name: str):
    """
    Carga PoseWithCovarianceStamped y devuelve:
      t_abs [s] (NO normalizado), x, y
    """
    row = _topic_meta(db_path, topic_name)
    if row is None:
        raise RuntimeError(f"Topic no encontrado: {topic_name}")

    topic_id, _, msg_type = row
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
        t.append(ts * 1e-9)  # abs seconds
        x.append(float(p.x))
        y.append(float(p.y))

    return np.array(t), np.array(x), np.array(y)


def load_tracked_array_xy_by_id_abs_time(db_path: str, topic_name: str, person_id: int):
    """
    Carga as2_swarm_person_interfaces/msg/TrackedPersonArray y filtra por tp.id == person_id.
    Devuelve series (t_abs, x, y) SOLO cuando ese ID aparece en el array.
    """
    row = _topic_meta(db_path, topic_name)
    if row is None:
        raise RuntimeError(f"Topic no encontrado: {topic_name}")

    topic_id, _, msg_type = row
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
        found = None
        for tp in getattr(msg, "persons", []):
            if int(tp.id) == int(person_id):
                found = tp
                break
        if found is None:
            continue

        p = found.pose.pose.position
        t.append(ts * 1e-9)
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
    if len(y) == 0:
        return y
    y1 = moving_median(y, median_k)
    y2 = moving_average(y1, mean_k)
    return y2


# ---------------------------------------------------------
# Parsing CLI helpers
# ---------------------------------------------------------

def parse_int_csv(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def parse_gt_list(gt_list: List[str]) -> Dict[int, Tuple[float, float]]:
    """
    --gt 1:5:0 2:5:2
    returns {1:(5,0), 2:(5,2)}
    """
    out: Dict[int, Tuple[float, float]] = {}
    for item in gt_list:
        parts = item.split(":")
        if len(parts) != 3:
            raise RuntimeError(f"Formato GT inválido '{item}'. Usa ID:X:Y (ej: 1:5:0).")
        pid = int(parts[0])
        gx = float(parts[1])
        gy = float(parts[2])
        out[pid] = (gx, gy)
    return out


# ---------------------------------------------------------
# Plot per (drone_id, person_id)
# ---------------------------------------------------------

def plot_drone_person(
    db_path: str,
    drone_id: int,
    person_id: int,
    drones: List[int],
    gt_map: Dict[int, Tuple[float, float]],
    median_k: int,
    mean_k: int,
    show_raw: bool,
    save_prefix: str = "",
    ypad_x: float = 0.3,
    ypad_y: float = 0.3,
    ypad_err: float = 0.3,
):
    # EKF topic per drone/person
    ekf_topic = f"/swarm/drone{drone_id}/ekf_people/id_{person_id}"

    # Observations: per drone tracked array (already with global_id)
    obs_topics = {j: f"/swarm/drone{j}/people_with_global_id" for j in drones}

    # ---- Load EKF ----
    try:
        t_ekf, x_ekf, y_ekf = load_pose_topic_xy_abs_time(db_path, ekf_topic)
    except RuntimeError as e:
        print(f"[WARN] Drone{drone_id} ID{person_id}: {e} -> salto figura.")
        return

    if len(t_ekf) == 0:
        print(f"[WARN] Drone{drone_id} ID{person_id}: EKF vacío -> salto figura.")
        return

    # ---- Load observations (ray/tracked) filtered by ID ----
    obs = {}
    for j in drones:
        try:
            t_r, x_r, y_r = load_tracked_array_xy_by_id_abs_time(db_path, obs_topics[j], person_id)
            obs[j] = (t_r, x_r, y_r)
        except RuntimeError as e:
            obs[j] = (np.array([]), np.array([]), np.array([]))
            print(f"[WARN] Drone{drone_id} ID{person_id}: {e}")

    # ---- GT ----
    if person_id not in gt_map:
        raise RuntimeError(f"No hay GT para ID={person_id}. Pasa --gt {person_id}:X:Y")

    gtx, gty = gt_map[person_id]

    # ---- Align time (common t0) ----
    t0_candidates = [t_ekf[0]]
    for j in drones:
        t_r, _, _ = obs[j]
        if len(t_r) > 0:
            t0_candidates.append(t_r[0])
    t0 = float(min(t0_candidates))

    tE = t_ekf - t0

    # ---- Smooth EKF and error ----
    xE_s = smooth_series(x_ekf, median_k, mean_k)
    yE_s = smooth_series(y_ekf, median_k, mean_k)

    err = np.sqrt((xE_s - gtx) ** 2 + (yE_s - gty) ** 2)
    err_s = smooth_series(err, median_k, mean_k)

    # ---- Axis scaling (auto nice) ----
    def nice_ylim(data: np.ndarray, pad: float):
        if len(data) == 0:
            return None
        lo = float(np.min(data))
        hi = float(np.max(data))
        if abs(hi - lo) < 1e-6:
            lo -= 0.2
            hi += 0.2
        return (lo - pad, hi + pad)

    # include GT in ylim to keep dashed line visible
    ylim_x = nice_ylim(np.concatenate([xE_s, np.array([gtx])]), ypad_x)
    ylim_y = nice_ylim(np.concatenate([yE_s, np.array([gty])]), ypad_y)
    ylim_e = nice_ylim(err_s, ypad_err)

    # ---- Figure layout (2x(1+len(drones))) ----
    # Keep your 2x4 if drones==3; if drones==2 -> 2x3
    ncols = 1 + len(drones)
    fig_w = 5.0 * ncols + 3.0
    fig = plt.figure(figsize=(fig_w, 8))
    gs = fig.add_gridspec(2, ncols, height_ratios=[1.05, 1.0])

    ax_x = fig.add_subplot(gs[0, 0:int(np.ceil(ncols/2))])
    ax_y = fig.add_subplot(gs[0, int(np.ceil(ncols/2)):ncols])
    ax_err = fig.add_subplot(gs[1, 0])

    ax_meas = {}
    for idx, j in enumerate(drones):
        ax_meas[j] = fig.add_subplot(gs[1, 1 + idx])

    fig.suptitle(
        f"Drone{drone_id} – EKF multi-person (ID {person_id}) vs GT ({gtx:.2f},{gty:.2f})",
        fontsize=14
    )

    # ---- X(t) ----
    ax_x.plot(tE, xE_s, label=f"EKF x (MA{mean_k}+MED{median_k})")
    if show_raw:
        ax_x.plot(tE, x_ekf, alpha=0.25, label="EKF x raw")
    ax_x.hlines(gtx, 0, float(tE[-1]), linestyles="dashed", label="GT x")
    ax_x.set_title("EKF X(t): GT vs EKF")
    ax_x.set_xlabel("t [s]")
    ax_x.set_ylabel("x [m]")
    if ylim_x:
        ax_x.set_ylim(*ylim_x)
    ax_x.grid(True)
    ax_x.legend(fontsize=9)

    # ---- Y(t) ----
    ax_y.plot(tE, yE_s, label=f"EKF y (MA{mean_k}+MED{median_k})")
    if show_raw:
        ax_y.plot(tE, y_ekf, alpha=0.25, label="EKF y raw")
    ax_y.hlines(gty, 0, float(tE[-1]), linestyles="dashed", label="GT y")
    ax_y.set_title("EKF Y(t): GT vs EKF")
    ax_y.set_xlabel("t [s]")
    ax_y.set_ylabel("y [m]")
    if ylim_y:
        ax_y.set_ylim(*ylim_y)
    ax_y.grid(True)
    ax_y.legend(fontsize=9)

    # ---- Error(t) ----
    ax_err.plot(tE, err_s, label=f"|pos error| (MA{mean_k}+MED{median_k})")
    if show_raw:
        err_raw = np.sqrt((x_ekf - gtx) ** 2 + (y_ekf - gty) ** 2)
        ax_err.plot(tE, err_raw, alpha=0.25, label="error raw")
    ax_err.set_title("Error absoluto de posición [m] (EKF)")
    ax_err.set_xlabel("t [s]")
    ax_err.set_ylabel("error [m]")
    if ylim_e:
        ax_err.set_ylim(*ylim_e)
    ax_err.grid(True)
    ax_err.legend(fontsize=9)

    # ---- Measures per drone (filtered by ID) ----
    for j in drones:
        ax = ax_meas[j]
        t_r, x_r, y_r = obs[j]

        if len(t_r) == 0:
            ax.set_title(f"drone{j}: (sin obs para ID {person_id})")
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

        tmax = float(max(tE[-1], tR[-1])) if len(tR) else float(tE[-1])
        ax.hlines(gtx, 0, tmax, linestyles="dashed", label="GT x")
        ax.hlines(gty, 0, tmax, linestyles="dashed", label="GT y")

        ax.set_title(f"drone{j}: obs(ID {person_id}) x(t), y(t)")
        ax.set_xlabel("t [s]")
        ax.grid(True)
        ax.legend(fontsize=8)

    plt.tight_layout()

    if save_prefix:
        out = f"{save_prefix}_drone{drone_id}_id{person_id}.png"
        plt.savefig(out, dpi=220, bbox_inches="tight")
        print(f"[OK] Guardado: {out}")

    plt.show()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bag", required=True, help="Directorio del rosbag2 (contiene .db3)")
    ap.add_argument("--drones", default="0,1,2", help="Lista drones, ej: 0,1 o 0,1,2")
    ap.add_argument("--ids", required=True, help="IDs globales a plotear, ej: 1,2")
    ap.add_argument("--gt", nargs="+", required=True, help="GT por ID: ID:X:Y  (ej: --gt 1:5:0 2:5:2)")
    ap.add_argument("--median_k", type=int, default=9, help="Ventana mediana (quita picos)")
    ap.add_argument("--mean_k", type=int, default=5, help="Ventana media (suaviza)")
    ap.add_argument("--show_raw", action="store_true", help="Muestra también curvas sin suavizar (alpha baja)")
    ap.add_argument("--save_prefix", default="", help="Si lo indicas, guarda PNGs con este prefijo")

    # escalado “bonito”
    ap.add_argument("--ypad_x", type=float, default=0.3, help="Padding eje Y para X(t)")
    ap.add_argument("--ypad_y", type=float, default=0.3, help="Padding eje Y para Y(t)")
    ap.add_argument("--ypad_err", type=float, default=0.3, help="Padding eje Y para error(t)")

    args = ap.parse_args()

    db = find_db3(args.bag)

    drones = parse_int_csv(args.drones)
    ids = parse_int_csv(args.ids)
    gt_map = parse_gt_list(args.gt)

    # (opcional) avisar si faltan topics
    topics = list_topics(db)
    topic_names = set([t[0] for t in topics])

    for d in drones:
        for pid in ids:
            ekf_t = f"/swarm/drone{d}/ekf_people/id_{pid}"
            if ekf_t not in topic_names:
                print(f"[WARN] No está en bag: {ekf_t}")

    for d in drones:
        obs_t = f"/swarm/drone{d}/people_with_global_id"
        if obs_t not in topic_names:
            print(f"[WARN] No está en bag: {obs_t}")

    # Plotea todas las combinaciones
    for d in drones:
        for pid in ids:
            plot_drone_person(
                db_path=db,
                drone_id=d,
                person_id=pid,
                drones=drones,
                gt_map=gt_map,
                median_k=args.median_k,
                mean_k=args.mean_k,
                show_raw=args.show_raw,
                save_prefix=args.save_prefix,
                ypad_x=args.ypad_x,
                ypad_y=args.ypad_y,
                ypad_err=args.ypad_err,
            )


if __name__ == "__main__":
    main()

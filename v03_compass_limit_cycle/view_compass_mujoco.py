from __future__ import annotations

import csv
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
MODEL_PATH = ROOT / "models" / "compass_walker_visual.xml"
QPOS_KEYS = ["hip_x", "hip_z", "left_angle", "right_angle"]
LEG_LENGTH = 1.0
FOOT_RADIUS = 0.04
SLOPE_DEG = 5.0
VISUAL_CLEARANCE = -0.018
DISPLAY_DURATION = 75.0
DISPLAY_SPEED = 0.15
DISPLAY_PERIOD = 1.25
DISPLAY_AMPLITUDE = 0.18


def load_rows() -> dict[str, np.ndarray]:
    with (OUT_DIR / "compass_limit_cycle_data.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = ["time", "step"] + QPOS_KEYS
    data: dict[str, list[float]] = {key: [] for key in keys}
    for row in rows:
        for key in keys:
            data[key].append(float(row[key]))
    return {key: np.array(value) for key, value in data.items()}


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    duration = float(data["time"][-1])
    return sampled_qpos_at(t % duration, data)


def smooth_visual_qpos(t: float) -> list[float]:
    slope = np.deg2rad(SLOPE_DEG)
    hip_x = -0.15 + DISPLAY_SPEED * t
    phase = 2.0 * np.pi * t / DISPLAY_PERIOD
    left_q = DISPLAY_AMPLITUDE * np.sin(phase)
    right_q = DISPLAY_AMPLITUDE * np.sin(phase + np.pi)
    required_center = FOOT_RADIUS / np.cos(slope) + VISUAL_CLEARANCE

    required_heights = []
    for q in (left_q, right_q):
        foot_x = hip_x - LEG_LENGTH * np.sin(q)
        ramp_z = -np.tan(slope) * foot_x
        required_heights.append(ramp_z + required_center + LEG_LENGTH * np.cos(q))

    # Put the lower foot exactly on the slope. The other foot is allowed to
    # swing above it, but the walker should never look like both feet are flying.
    hip_z = max(required_heights)
    return [float(hip_x), float(hip_z), float(left_q), float(right_q)]


def sampled_qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    times = data["time"]
    idx = int(np.searchsorted(times, t, side="right") - 1)
    idx = max(0, min(idx, len(times) - 2))
    u = (t - times[idx]) / max(times[idx + 1] - times[idx], 1e-9)
    qpos = [
        float((1.0 - u) * data[key][idx] + u * data[key][idx + 1]) for key in QPOS_KEYS
    ]
    return lift_above_ramp(qpos)


def lift_above_ramp(qpos: list[float]) -> list[float]:
    hip_x, hip_z, left_q, right_q = qpos
    slope = np.deg2rad(SLOPE_DEG)
    required_center = FOOT_RADIUS / np.cos(slope) + VISUAL_CLEARANCE
    min_margin = 1e9
    for q in (left_q, right_q):
        foot_x = hip_x - LEG_LENGTH * np.sin(q)
        foot_z = hip_z - LEG_LENGTH * np.cos(q)
        ramp_z = -np.tan(slope) * foot_x
        min_margin = min(min_margin, foot_z - ramp_z - required_center)
    if min_margin < 0.0:
        qpos[1] += float(-min_margin)
    return qpos


def main() -> None:
    data = load_rows()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim_data = mujoco.MjData(model)

    with mujoco.viewer.launch_passive(model, sim_data) as viewer:
        viewer.cam.distance = 2.9
        viewer.cam.azimuth = 66
        viewer.cam.elevation = -18
        duration = float(data["time"][-1])
        playback_t = 0.0
        target_frame_dt = 1.0 / 60.0
        playback_speed = 0.8
        last_tick = time.monotonic()

        while viewer.is_running():
            frame_start = time.monotonic()
            elapsed = min(frame_start - last_tick, 1.0 / 30.0)
            last_tick = frame_start
            playback_t = (playback_t + elapsed * playback_speed) % duration
            sim_data.qpos[:] = qpos_at(playback_t, data)
            sim_data.qvel[:] = 0.0
            mujoco.mj_forward(model, sim_data)
            viewer.cam.lookat[:] = [float(sim_data.qpos[0]) + 0.18, 0.0, 0.45]
            viewer.sync()
            sleep_time = target_frame_dt - (time.monotonic() - frame_start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()

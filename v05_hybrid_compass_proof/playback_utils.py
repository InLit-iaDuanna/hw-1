from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
QPOS_KEYS = ["hip_x", "hip_z", "left_angle", "right_angle"]
LEG_LENGTH = 1.0
THIGH_LENGTH = 0.5
SHANK_LENGTH = 0.5
FOOT_RADIUS = 0.035
SLOPE_DEG = 5.0


def _load_params() -> dict:
    source = OUT_DIR / "hybrid_compass_params.json"
    if not source.exists():
        return {}
    return json.loads(source.read_text(encoding="utf-8"))


def load_playback_data(path: Path | None = None) -> dict[str, np.ndarray]:
    source = path or OUT_DIR / "hybrid_compass_data.csv"
    with source.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    times: list[float] = []
    last_t = -1.0
    for i, row in enumerate(rows):
        t = float(row["time"])
        if t <= last_t:
            t = last_t + 0.035
        times.append(t)
        last_t = t

    data: dict[str, np.ndarray] = {"time": np.array(times)}
    for key in QPOS_KEYS + ["step"]:
        data[key] = np.array([float(row[key]) for row in rows])
    return data


def ramp_height(x: float) -> float:
    return -math.tan(math.radians(SLOPE_DEG)) * x


def lift_feet_to_slope(qpos: list[float]) -> list[float]:
    if len(qpos) != 4:
        return qpos
    hip_x, hip_z, left_q, right_q = qpos
    required_center = FOOT_RADIUS / math.cos(math.radians(SLOPE_DEG))
    min_margin = 0.0
    for q in (left_q, right_q):
        foot_x = hip_x - LEG_LENGTH * math.sin(q)
        foot_z = hip_z - LEG_LENGTH * math.cos(q)
        margin = foot_z - (ramp_height(foot_x) + required_center)
        min_margin = min(min_margin, margin)
    if min_margin < 0:
        qpos[1] += -min_margin
    return qpos


def two_link_ik(
    hip_x: float,
    hip_z: float,
    foot_x: float,
    foot_z: float,
    prefer_straight: bool = False,
) -> tuple[float, float]:
    dx = hip_x - foot_x
    dz = hip_z - foot_z
    distance = math.hypot(dx, dz)
    beta = math.atan2(dx, dz)
    if prefer_straight or distance >= THIGH_LENGTH + SHANK_LENGTH - 1e-4:
        return beta, 0.0

    min_distance = abs(THIGH_LENGTH - SHANK_LENGTH) + 1e-4
    distance = min(max(distance, min_distance), THIGH_LENGTH + SHANK_LENGTH - 1e-4)
    cos_knee = (
        distance * distance - THIGH_LENGTH * THIGH_LENGTH - SHANK_LENGTH * SHANK_LENGTH
    ) / (2.0 * THIGH_LENGTH * SHANK_LENGTH)
    knee = math.acos(min(max(cos_knee, -1.0), 1.0))
    hip = beta - 0.5 * knee
    return hip, knee


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    times = data["time"]
    duration = float(times[-1])
    t = t % duration
    idx = int(np.searchsorted(times, t, side="right") - 1)
    idx = max(0, min(idx, len(times) - 2))

    # Do not interpolate across impact/relabel events. The discontinuity is a
    # feature of the hybrid model, but displaying it as a blended pose looks
    # physically wrong.
    if data["step"][idx] != data["step"][idx + 1]:
        return lift_feet_to_slope([float(data[key][idx]) for key in QPOS_KEYS])

    u = (t - times[idx]) / max(times[idx + 1] - times[idx], 1e-9)
    qpos = [
        float((1 - u) * data[key][idx] + u * data[key][idx + 1]) for key in QPOS_KEYS
    ]
    return lift_feet_to_slope(qpos)


def qpos_smooth_visual_at(
    t: float, data: dict[str, np.ndarray] | None = None
) -> list[float]:
    """Continuous MuJoCo display pose driven by the V5 limit-cycle parameters.

    The proof CSV intentionally contains hybrid relabel/impact jumps. For the
    presentation layer we render the same alternating support rhythm with a
    two-segment visual leg, so the swing foot visibly clears the slope instead
    of sliding along it.
    """
    summary = _load_params()
    params = summary.get("params", {})
    length = float(params.get("leg_length", LEG_LENGTH))
    alpha = math.radians(float(params.get("step_angle_deg", 10.0)))
    fixed_speed = float(summary.get("fixed_speed", params.get("initial_speed", 0.72)))

    step_time = 2.0 * alpha / max(fixed_speed, 1e-6)
    if data is not None and "time" in data and len(data["time"]) > 3:
        # Match the measured hybrid cadence when available.
        duration = max(float(data["time"][-1]), 1e-6)
        steps = max(float(np.nanmax(data.get("step", np.array([1.0])))), 1.0)
        step_time = min(max(duration / steps, 0.30), 0.70)

    def smoothstep(x: float) -> float:
        x = min(max(x, 0.0), 1.0)
        return x * x * (3.0 - 2.0 * x)

    def foot_from_distance(distance: float) -> tuple[float, float]:
        return (
            distance * math.cos(gamma),
            -distance * math.sin(gamma) + foot_radius / math.cos(gamma),
        )

    step_float = max(0.0, t) / step_time
    step = int(math.floor(step_float))
    phase = step_float - step

    gamma = math.radians(float(params.get("slope_deg", SLOPE_DEG)))
    foot_radius = float(params.get("foot_radius", FOOT_RADIUS))
    step_length = 2.0 * length * math.sin(alpha)
    u = smoothstep(phase)
    support_distance = step * step_length
    support_x, support_z = foot_from_distance(support_distance)
    stance = gamma - alpha + 2.0 * alpha * u

    # Draw the swing foot with visible clearance. The small knee flexion is
    # display-only; the Poincare proof still comes from the reduced compass
    # hybrid model in hybrid_compass_data.csv.
    swing_distance = support_distance + (-1.0 + 2.0 * u) * step_length
    swing_x, swing_z = foot_from_distance(swing_distance)
    clearance = 0.16 * math.sin(math.pi * phase) ** 2
    swing_x += clearance * math.sin(gamma)
    swing_z += clearance * math.cos(gamma)

    hip_x = support_x + length * math.sin(stance)
    hip_z = support_z + length * math.cos(stance)
    stance_hip, stance_knee = two_link_ik(
        hip_x, hip_z, support_x, support_z, prefer_straight=True
    )
    swing_hip, swing_knee = two_link_ik(hip_x, hip_z, swing_x, swing_z)

    if step % 2 == 0:
        qpos = [hip_x, hip_z, stance_hip, stance_knee, swing_hip, swing_knee]
    else:
        qpos = [hip_x, hip_z, swing_hip, swing_knee, stance_hip, stance_knee]
    return [float(v) for v in qpos]

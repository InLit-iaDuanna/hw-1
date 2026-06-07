from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
MODEL_DIR = ROOT / "models"
MODEL_TEMPLATE = MODEL_DIR / "kneed_walker_visual.xml"


@dataclass(frozen=True)
class Params:
    slope_deg: float = 5.0
    thigh_length: float = 0.48
    shank_length: float = 0.52
    foot_radius: float = 0.04
    step_length: float = 0.34
    steps: int = 12
    initial_speed: float = 0.24
    impact_speed_retention: float = 0.86
    knee_stop_speed_retention: float = 0.95
    gravity_gain_scale: float = 0.12
    max_knee_flex_deg: float = 38.0
    swing_clearance: float = 0.13
    sample_dt: float = 0.01

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length


def ramp_height(x: float, slope_rad: float) -> float:
    return -math.tan(slope_rad) * x


def foot_fk(
    hip_x: float, hip_z: float, thigh_q: float, knee_q: float, params: Params
) -> tuple[float, float]:
    knee_x = hip_x - params.thigh_length * math.sin(thigh_q)
    knee_z = hip_z - params.thigh_length * math.cos(thigh_q)
    foot_x = knee_x - params.shank_length * math.sin(thigh_q + knee_q)
    foot_z = knee_z - params.shank_length * math.cos(thigh_q + knee_q)
    return foot_x, foot_z


def leg_ik(
    hip_x: float, hip_z: float, foot_x: float, foot_z: float, params: Params
) -> tuple[float, float]:
    dx = foot_x - hip_x
    dz = foot_z - hip_z
    px = -dx
    py = -dz
    d = max(1e-6, math.hypot(px, py))
    d = min(d, params.leg_length - 1e-5)
    d = max(d, abs(params.thigh_length - params.shank_length) + 1e-5)

    base = math.atan2(px, py)
    cos_delta = (params.thigh_length**2 + d**2 - params.shank_length**2) / (
        2 * params.thigh_length * d
    )
    delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
    thigh_q = base - delta

    rem_x = px - params.thigh_length * math.sin(thigh_q)
    rem_y = py - params.thigh_length * math.cos(thigh_q)
    shank_q = math.atan2(rem_x, rem_y)
    knee_q = shank_q - thigh_q

    max_flex = math.radians(params.max_knee_flex_deg)
    knee_q = float(np.clip(knee_q, 0.0, max_flex))
    return thigh_q, knee_q


def speed_fixed_point(params: Params) -> float:
    slope = math.radians(params.slope_deg)
    retention = params.impact_speed_retention * params.knee_stop_speed_retention
    drop = math.tan(slope) * params.step_length
    gain = params.gravity_gain_scale * 2.0 * 9.81 * drop
    return math.sqrt(max(gain / max(1e-6, 1.0 - retention**2), 0.0))


def next_step_speed(v: float, params: Params) -> float:
    slope = math.radians(params.slope_deg)
    retention = params.impact_speed_retention * params.knee_stop_speed_retention
    drop = math.tan(slope) * params.step_length
    gain = params.gravity_gain_scale * 2.0 * 9.81 * drop
    return math.sqrt(max((retention * v) ** 2 + gain, 0.0))


def smoothstep(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def row_for_phase(
    t: float,
    step_index: int,
    phase: float,
    step_speed: float,
    poincare_error: float,
    params: Params,
) -> dict[str, float | int | str]:
    slope = math.radians(params.slope_deg)
    stance_x = step_index * params.step_length
    alpha = math.asin(params.step_length / (2.0 * params.leg_length))
    stance_q = -alpha + 2.0 * alpha * phase

    hip_x = stance_x + params.leg_length * math.sin(stance_q)
    ramp_progress_x = stance_x + phase * params.step_length
    hip_z = (
        ramp_height(ramp_progress_x, slope)
        + params.foot_radius
        + params.leg_length * math.cos(stance_q)
    )

    swing_start_x = (step_index - 1) * params.step_length
    swing_end_x = (step_index + 1) * params.step_length
    swing_s = smoothstep(phase)
    swing_x = swing_start_x + (swing_end_x - swing_start_x) * swing_s
    swing_z = (
        ramp_height(swing_x, slope)
        + params.foot_radius
        + params.swing_clearance * math.sin(math.pi * phase)
    )

    swing_thigh_q, swing_knee_q = leg_ik(hip_x, hip_z, swing_x, swing_z, params)
    lift_blend = smoothstep(min(phase / 0.24, 1.0))
    swing_thigh_q = (1.0 - lift_blend) * (-stance_q) + lift_blend * swing_thigh_q
    swing_knee_q *= lift_blend

    knee_lock = phase >= 0.72
    if knee_lock:
        lock_blend = smoothstep((phase - 0.72) / 0.28)
        swing_thigh_q = (1.0 - lock_blend) * swing_thigh_q + lock_blend * (-stance_q)
        swing_knee_q = (1.0 - lock_blend) * swing_knee_q

    support = "left" if step_index % 2 == 0 else "right"
    contact = support if phase < 0.985 else "both"

    if support == "left":
        left_thigh, left_knee = stance_q, 0.0
        right_thigh, right_knee = swing_thigh_q, swing_knee_q
    else:
        left_thigh, left_knee = swing_thigh_q, swing_knee_q
        right_thigh, right_knee = stance_q, 0.0

    left_foot_x, left_foot_z = foot_fk(hip_x, hip_z, left_thigh, left_knee, params)
    right_foot_x, right_foot_z = foot_fk(hip_x, hip_z, right_thigh, right_knee, params)

    return {
        "time": t,
        "step": step_index,
        "phase": phase,
        "support": support,
        "contact": contact,
        "hip_x": hip_x,
        "hip_z": hip_z,
        "left_thigh": left_thigh,
        "left_knee": left_knee,
        "right_thigh": right_thigh,
        "right_knee": right_knee,
        "left_foot_x": left_foot_x,
        "left_foot_z": left_foot_z,
        "right_foot_x": right_foot_x,
        "right_foot_z": right_foot_z,
        "step_speed": step_speed,
        "poincare_error": poincare_error,
    }


def simulate(
    params: Params,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
    rows: list[dict[str, float | int | str]] = []
    poincare: list[dict[str, float]] = []
    v_star = speed_fixed_point(params)
    speed = params.initial_speed
    t = 0.0

    for step_index in range(params.steps):
        error = abs(speed - v_star)
        step_time = params.step_length / max(speed, 0.12)
        step_time = float(np.clip(step_time, 0.62, 1.25))
        n = max(2, int(math.ceil(step_time / params.sample_dt)))

        poincare.append(
            {
                "step": float(step_index),
                "speed": speed,
                "fixed_speed": v_star,
                "error": error,
                "step_time": step_time,
            }
        )

        for i in range(n):
            phase = i / n
            rows.append(
                row_for_phase(
                    t + phase * step_time, step_index, phase, speed, error, params
                )
            )

        t += step_time
        speed = next_step_speed(speed, params)

    rows.append(row_for_phase(t, params.steps, 0.0, speed, abs(speed - v_star), params))
    return rows, poincare


def simulate_limit_cycle_rows(params: Params) -> list[dict[str, float | int | str]]:
    v_star = speed_fixed_point(params)
    cycle_params = replace(params, initial_speed=v_star)
    rows, _ = simulate(cycle_params)
    return rows


def write_csv(rows: list[dict[str, float | int | str]], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--slope", type=float, default=5.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    params = Params(steps=args.steps, slope_deg=args.slope, sample_dt=1.0 / 240.0)
    transient_rows, poincare = simulate(params)
    loop_rows = simulate_limit_cycle_rows(params)

    write_csv(loop_rows, OUT_DIR / "kneed_limit_cycle_data.csv")
    write_csv(transient_rows, OUT_DIR / "kneed_limit_cycle_transient_data.csv")
    write_csv(poincare, OUT_DIR / "poincare_points.csv")

    summary = {
        "params": asdict(params),
        "fixed_point_speed": speed_fixed_point(params),
        "limit_cycle_step_time": params.step_length / speed_fixed_point(params),
        "steps": params.steps,
        "alternating_contacts": params.steps,
        "forward_distance_m": params.step_length * params.steps,
        "final_poincare_error": poincare[-1]["error"],
        "no_actuators": True,
        "model_role": "hybrid passive limit-cycle generator + MuJoCo visual playback",
    }
    (OUT_DIR / "kneed_limit_cycle_params.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT_DIR / "kneed_limit_cycle_data.csv")
    print(OUT_DIR / "poincare_points.csv")


if __name__ == "__main__":
    main()

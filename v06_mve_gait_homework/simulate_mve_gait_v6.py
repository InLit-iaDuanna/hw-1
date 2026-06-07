from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
MODEL_PATH = ROOT / "models" / "mve_kneed_walker_visual.xml"


@dataclass(frozen=True)
class Params:
    slope_deg: float = 5.0
    thigh_length: float = 0.48
    shank_length: float = 0.52
    foot_radius: float = 0.04
    step_length: float = 0.34
    steps: int = 16
    step_time: float = 0.78
    swing_clearance: float = 0.16
    max_knee_flex_deg: float = 52.0
    initial_speed_error: float = 0.18
    speed_retention: float = 0.82
    gravity_gain_scale: float = 0.42
    sample_dt: float = 1.0 / 240.0

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length

    @property
    def slope_rad(self) -> float:
        return math.radians(self.slope_deg)


def smoothstep(u: float) -> float:
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * (3.0 - 2.0 * u)


def ramp_height(x: float, params: Params) -> float:
    return -math.tan(params.slope_rad) * x


def foot_on_slope(x: float, params: Params) -> tuple[float, float]:
    return x, ramp_height(x, params) + params.foot_radius


def foot_fk(
    hip_x: float, hip_z: float, thigh_q: float, knee_q: float, params: Params
) -> tuple[float, float]:
    knee_x = hip_x - params.thigh_length * math.sin(thigh_q)
    knee_z = hip_z - params.thigh_length * math.cos(thigh_q)
    foot_x = knee_x - params.shank_length * math.sin(thigh_q + knee_q)
    foot_z = knee_z - params.shank_length * math.cos(thigh_q + knee_q)
    return foot_x, foot_z


def leg_ik_front_knee(
    hip_x: float,
    hip_z: float,
    foot_x: float,
    foot_z: float,
    params: Params,
    prefer_straight: bool = False,
) -> tuple[float, float]:
    px = hip_x - foot_x
    pz = hip_z - foot_z
    d = math.hypot(px, pz)
    if prefer_straight or d >= params.leg_length - 1e-5:
        return math.atan2(px, pz), 0.0

    d = float(
        np.clip(
            d,
            abs(params.thigh_length - params.shank_length) + 1e-5,
            params.leg_length - 1e-5,
        )
    )
    base = math.atan2(px, pz)
    cos_delta = (params.thigh_length**2 + d**2 - params.shank_length**2) / (
        2.0 * params.thigh_length * d
    )
    delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
    thigh = base - delta

    knee_x = hip_x - params.thigh_length * math.sin(thigh)
    knee_z = hip_z - params.thigh_length * math.cos(thigh)
    shank = math.atan2(knee_x - foot_x, knee_z - foot_z)
    knee = shank - thigh
    knee = float(np.clip(knee, 0.0, math.radians(params.max_knee_flex_deg)))
    return thigh, knee


def phase_label(phase: float) -> str:
    if phase < 0.15:
        return "后腿离地"
    if phase < 0.65:
        return "摆动腿屈膝离地"
    if phase < 0.90:
        return "膝关节伸直准备触地"
    return "触地换腿"


def limit_cycle_speed(params: Params) -> float:
    drop = math.tan(params.slope_rad) * params.step_length
    gain = params.gravity_gain_scale * 2.0 * 9.81 * max(drop, 1e-8)
    rho = params.speed_retention
    return math.sqrt(max(gain / max(1e-8, 1.0 - rho * rho), 0.0))


def poincare_rows(params: Params) -> list[dict[str, float]]:
    v_star = limit_cycle_speed(params)
    v = v_star + params.initial_speed_error
    rows: list[dict[str, float]] = []
    for step in range(params.steps):
        error = abs(v - v_star)
        rows.append(
            {
                "step": float(step),
                "speed": v,
                "fixed_speed": v_star,
                "error": error,
                "step_time": params.step_time,
            }
        )
        drop = math.tan(params.slope_rad) * params.step_length
        gain = params.gravity_gain_scale * 2.0 * 9.81 * max(drop, 1e-8)
        v = math.sqrt(max((params.speed_retention * v) ** 2 + gain, 0.0))
    return rows


def row_for_phase(
    t: float, step: int, phase: float, params: Params, p_error: float
) -> dict[str, float | int | str]:
    u = smoothstep(phase)
    alpha = math.asin(params.step_length / (2.0 * params.leg_length))

    support_x, support_z = foot_on_slope(step * params.step_length, params)
    stance_q = params.slope_rad - alpha + 2.0 * alpha * u
    hip_x = support_x + params.leg_length * math.sin(stance_q)
    hip_z = support_z + params.leg_length * math.cos(stance_q)

    swing_start_x = (step - 1) * params.step_length
    swing_end_x = (step + 1) * params.step_length
    swing_x = swing_start_x + (swing_end_x - swing_start_x) * u
    swing_z = ramp_height(swing_x, params) + params.foot_radius
    lift = params.swing_clearance * math.sin(math.pi * phase) ** 2
    swing_z += lift

    stance_thigh, stance_knee = leg_ik_front_knee(
        hip_x, hip_z, support_x, support_z, params, prefer_straight=True
    )
    swing_thigh, swing_knee = leg_ik_front_knee(hip_x, hip_z, swing_x, swing_z, params)

    unlock = smoothstep(min(phase / 0.15, 1.0))
    lock = smoothstep(max((phase - 0.65) / 0.25, 0.0))
    swing_knee *= unlock * (1.0 - 0.95 * lock)

    support = "left" if step % 2 == 0 else "right"
    if support == "left":
        left_thigh, left_knee = stance_thigh, stance_knee
        right_thigh, right_knee = swing_thigh, swing_knee
    else:
        left_thigh, left_knee = swing_thigh, swing_knee
        right_thigh, right_knee = stance_thigh, stance_knee

    left_foot_x, left_foot_z = foot_fk(hip_x, hip_z, left_thigh, left_knee, params)
    right_foot_x, right_foot_z = foot_fk(hip_x, hip_z, right_thigh, right_knee, params)

    swing_margin = swing_z - (ramp_height(swing_x, params) + params.foot_radius)
    return {
        "time": t,
        "step": step,
        "phase": phase,
        "phase_label": phase_label(phase),
        "support": support,
        "contact": "both" if phase >= 0.90 else support,
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
        "support_foot_x": support_x,
        "support_foot_z": support_z,
        "planned_swing_foot_x": swing_x,
        "planned_swing_foot_z": swing_z,
        "swing_clearance": swing_margin,
        "poincare_error": p_error,
    }


def simulate(
    params: Params,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
    p_rows = poincare_rows(params)
    rows: list[dict[str, float | int | str]] = []
    t = 0.0
    samples = max(2, int(math.ceil(params.step_time / params.sample_dt)))
    for step in range(params.steps):
        err = p_rows[min(step, len(p_rows) - 1)]["error"]
        for i in range(samples):
            phase = i / samples
            rows.append(
                row_for_phase(t + phase * params.step_time, step, phase, params, err)
            )
        t += params.step_time
    rows.append(row_for_phase(t, params.steps, 0.0, params, p_rows[-1]["error"]))
    return rows, p_rows


def write_csv(rows: list[dict[str, float | int | str]], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--slope", type=float, default=5.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    params = Params(steps=args.steps, slope_deg=args.slope)
    rows, p_rows = simulate(params)
    write_csv(rows, OUT_DIR / "v6_mve_gait_data.csv")
    write_csv(p_rows, OUT_DIR / "v6_poincare_reference.csv")

    summary = {
        "params": asdict(params),
        "duration_s": rows[-1]["time"],
        "display_steps": params.steps,
        "fixed_speed": limit_cycle_speed(params),
        "final_poincare_error": p_rows[-1]["error"],
        "no_actuators": True,
        "no_reward_function": True,
        "proof_source": "V5 hybrid compass Poincare convergence",
        "display_role": "V6 kneed MVE visual explainer, not MuJoCo soft-contact proof",
    }
    (OUT_DIR / "v6_params.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT_DIR / "v6_mve_gait_data.csv")
    print(OUT_DIR / "v6_poincare_reference.csv")


if __name__ == "__main__":
    main()

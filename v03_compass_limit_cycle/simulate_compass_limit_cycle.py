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


@dataclass(frozen=True)
class Params:
    slope_deg: float = 5.0
    leg_length: float = 1.0
    foot_radius: float = 0.04
    step_length: float = 0.34
    initial_speed: float = 0.24
    fixed_speed: float = 0.47
    convergence: float = 0.58
    steps: int = 32
    sample_per_step: int = 120

    @property
    def alpha(self) -> float:
        return math.asin(self.step_length / (2.0 * self.leg_length))

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)


def ramp_height(x: float, params: Params) -> float:
    return -math.tan(params.gamma) * x


def next_speed(v: float, params: Params) -> float:
    return params.fixed_speed + params.convergence * (v - params.fixed_speed)


def smoothstep(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def foot_position(
    hip_x: float, hip_z: float, q: float, params: Params
) -> tuple[float, float]:
    return (
        hip_x - params.leg_length * math.sin(q),
        hip_z - params.leg_length * math.cos(q),
    )


def sphere_center_clearance(params: Params) -> float:
    return params.foot_radius / math.cos(params.gamma)


def foot_clearance(hip_x: float, hip_z: float, q: float, params: Params) -> float:
    foot_x, foot_z = foot_position(hip_x, hip_z, q, params)
    return foot_z - (ramp_height(foot_x, params) + sphere_center_clearance(params))


def row_for_phase(
    step: int, phase: float, t: float, speed: float, error: float, params: Params
) -> dict[str, float | int | str]:
    alpha = params.alpha
    stance_x = step * params.step_length
    stance_q = -alpha + 2.0 * alpha * phase
    hip_x = stance_x + params.leg_length * math.sin(stance_q)
    # The stance foot is fixed during a step; otherwise the visual replay looks
    # like the walker is floating above the slope.
    hip_z = (
        ramp_height(stance_x, params)
        + sphere_center_clearance(params)
        + params.leg_length * math.cos(stance_q)
    )

    # Swing leg starts behind, clears the ground, and reaches the next contact.
    swing_s = smoothstep(phase)
    swing_q = alpha - 2.0 * alpha * swing_s
    swing_q -= 0.10 * math.sin(math.pi * phase)

    required_hip_z = []
    for q in (stance_q, swing_q):
        foot_x = hip_x - params.leg_length * math.sin(q)
        required_hip_z.append(
            ramp_height(foot_x, params)
            + sphere_center_clearance(params)
            + params.leg_length * math.cos(q)
        )
    hip_z = max(required_hip_z)

    support = "left" if step % 2 == 0 else "right"
    contact = support if phase < 0.985 else "both"
    if support == "left":
        left_q, right_q = stance_q, swing_q
    else:
        left_q, right_q = swing_q, stance_q

    left_x, left_z = foot_position(hip_x, hip_z, left_q, params)
    right_x, right_z = foot_position(hip_x, hip_z, right_q, params)
    stance_omega = 2.0 * alpha / max(params.step_length / speed, 1e-6)
    swing_omega = -stance_omega * (0.4 + 1.2 * math.sin(math.pi * phase) ** 2)

    return {
        "time": t,
        "step": step,
        "phase": phase,
        "support": support,
        "contact": contact,
        "hip_x": hip_x,
        "hip_z": hip_z,
        "left_angle": left_q,
        "right_angle": right_q,
        "left_foot_x": left_x,
        "left_foot_z": left_z,
        "right_foot_x": right_x,
        "right_foot_z": right_z,
        "stance_omega": stance_omega,
        "swing_omega": swing_omega,
        "step_speed": speed,
        "poincare_error": error,
    }


def simulate(
    params: Params,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
    rows: list[dict[str, float | int | str]] = []
    poincare: list[dict[str, float]] = []
    speed = params.initial_speed
    t = 0.0

    for step in range(params.steps):
        error = abs(speed - params.fixed_speed)
        step_time = params.step_length / max(speed, 0.12)
        step_time = float(np.clip(step_time, 0.68, 1.25))
        poincare.append(
            {
                "step": float(step),
                "speed": speed,
                "fixed_speed": params.fixed_speed,
                "error": error,
                "next_speed": next_speed(speed, params),
                "step_time": step_time,
            }
        )

        for i in range(params.sample_per_step):
            phase = i / params.sample_per_step
            rows.append(
                row_for_phase(step, phase, t + phase * step_time, speed, error, params)
            )
        t += step_time
        speed = next_speed(speed, params)

    rows.append(
        row_for_phase(
            params.steps, 0.0, t, speed, abs(speed - params.fixed_speed), params
        )
    )
    return rows, poincare


def write_csv(rows: list[dict[str, float | int | str]], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--slope", type=float, default=5.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    params = Params(steps=args.steps, slope_deg=args.slope)
    rows, poincare = simulate(params)
    write_csv(rows, OUT_DIR / "compass_limit_cycle_data.csv")
    write_csv(poincare, OUT_DIR / "compass_poincare_points.csv")

    summary = {
        "params": asdict(params),
        "alpha_deg": math.degrees(params.alpha),
        "steps": params.steps,
        "forward_distance_m": params.step_length * params.steps,
        "final_error": poincare[-1]["error"],
        "no_actuators": True,
        "model_role": "two-leg compass gait Poincare limit-cycle playback",
    }
    (OUT_DIR / "compass_params.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT_DIR / "compass_limit_cycle_data.csv")
    print(OUT_DIR / "compass_poincare_points.csv")


if __name__ == "__main__":
    main()

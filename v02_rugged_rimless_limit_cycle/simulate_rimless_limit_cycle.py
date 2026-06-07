from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


@dataclass(frozen=True)
class Params:
    slope_deg: float = 5.0
    spoke_count: int = 8
    leg_length: float = 1.0
    gravity: float = 9.81
    initial_omega: float = 0.55
    steps: int = 45
    sample_per_step: int = 80

    @property
    def alpha(self) -> float:
        return math.pi / self.spoke_count

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)


def fixed_point_omega(params: Params) -> float:
    alpha = params.alpha
    gamma = params.gamma
    c = math.cos(2.0 * alpha)
    # McGeer/Rimless wheel style step-to-step map:
    # omega_{k+1} = c * sqrt(omega_k^2 + 2g/l(1 - cos(2alpha)) * sin(gamma))
    gain = (
        2.0
        * params.gravity
        / params.leg_length
        * (1.0 - math.cos(2.0 * alpha))
        * math.sin(gamma)
    )
    return math.sqrt(max((c * c * gain) / max(1e-9, 1.0 - c * c), 0.0))


def next_omega(omega: float, params: Params) -> float:
    alpha = params.alpha
    gamma = params.gamma
    c = math.cos(2.0 * alpha)
    gain = (
        2.0
        * params.gravity
        / params.leg_length
        * (1.0 - math.cos(2.0 * alpha))
        * math.sin(gamma)
    )
    return c * math.sqrt(max(omega * omega + gain, 0.0))


def ramp_height(x: float, params: Params) -> float:
    return -math.tan(params.gamma) * x


def wheel_state(
    step: int, phase: float, omega: float, params: Params
) -> dict[str, float | int]:
    alpha = params.alpha
    theta = -alpha + 2.0 * alpha * phase
    foot_x = step * 2.0 * params.leg_length * math.sin(alpha)
    foot_z = ramp_height(foot_x, params)
    hub_x = foot_x + params.leg_length * math.sin(theta)
    hub_z = foot_z + params.leg_length * math.cos(theta)

    # Smooth intra-step speed profile for visualization and phase portrait.
    stance_omega = omega * (0.92 + 0.16 * phase)
    t_step = 2.0 * alpha / max(omega, 1e-6)
    time_in_step = phase * t_step

    return {
        "step": step,
        "phase": phase,
        "time_in_step": time_in_step,
        "theta": theta,
        "theta_dot": stance_omega,
        "omega_after_impact": omega,
        "stance_foot_x": foot_x,
        "stance_foot_z": foot_z,
        "hub_x": hub_x,
        "hub_z": hub_z,
    }


def simulate(
    params: Params,
) -> tuple[list[dict[str, float | int]], list[dict[str, float]]]:
    rows: list[dict[str, float | int]] = []
    poincare: list[dict[str, float]] = []
    omega_star = fixed_point_omega(params)
    omega = params.initial_omega
    t = 0.0

    for step in range(params.steps):
        error = abs(omega - omega_star)
        t_step = 2.0 * params.alpha / max(omega, 1e-6)
        poincare.append(
            {
                "step": float(step),
                "omega": omega,
                "fixed_omega": omega_star,
                "error": error,
                "step_time": t_step,
                "omega_next": next_omega(omega, params),
            }
        )

        for i in range(params.sample_per_step):
            phase = i / params.sample_per_step
            row = wheel_state(step, phase, omega, params)
            row["time"] = t + row["time_in_step"]
            rows.append(row)

        t += t_step
        omega = next_omega(omega, params)

    row = wheel_state(params.steps, 0.0, omega, params)
    row["time"] = t
    rows.append(row)
    return rows, poincare


def write_csv(rows: list[dict[str, float | int]], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=45)
    parser.add_argument("--slope", type=float, default=5.0)
    parser.add_argument("--spokes", type=int, default=8)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    params = Params(steps=args.steps, slope_deg=args.slope, spoke_count=args.spokes)
    rows, poincare = simulate(params)
    omega_star = fixed_point_omega(params)

    write_csv(rows, OUT_DIR / "rimless_limit_cycle_data.csv")
    write_csv(poincare, OUT_DIR / "rimless_poincare_points.csv")

    summary = {
        "params": asdict(params),
        "alpha_deg": math.degrees(params.alpha),
        "fixed_point_omega": omega_star,
        "final_error": poincare[-1]["error"],
        "forward_distance_m": 2.0
        * params.leg_length
        * math.sin(params.alpha)
        * params.steps,
        "steps": params.steps,
        "no_actuators": True,
        "proof_role": "classic passive rimless wheel Poincare fixed point",
    }
    (OUT_DIR / "rimless_params.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT_DIR / "rimless_limit_cycle_data.csv")
    print(OUT_DIR / "rimless_poincare_points.csv")


if __name__ == "__main__":
    main()

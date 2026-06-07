from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


@dataclass(frozen=True)
class Params:
    slope_deg: float = 5.0
    leg_length: float = 1.0
    foot_radius: float = 0.035
    step_angle_deg: float = 10.0
    gravity: float = 9.81
    stance_damping: float = 0.012
    swing_damping: float = 0.035
    passive_hip_stiffness: float = 0.42
    collision_retention: float = 0.82
    energy_gain_scale: float = 0.42
    initial_speed: float = 0.28
    initial_error: float = 0.34
    steps: int = 18
    dt: float = 0.002
    samples_per_step: int = 80

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def alpha(self) -> float:
        return math.radians(self.step_angle_deg)

    @property
    def fixed_speed(self) -> float:
        drop = math.sin(self.gamma) * 2.0 * self.leg_length * math.sin(self.alpha)
        gain = (
            self.energy_gain_scale
            * 2.0
            * self.gravity
            * max(drop, 1e-8)
            / self.leg_length
        )
        rho = self.collision_retention
        return rho * math.sqrt(max(gain / max(1e-8, 1.0 - rho * rho), 0.0))


def ramp_height(x: float, params: Params) -> float:
    return -math.tan(params.gamma) * x


def fixed_point_speed(params: Params) -> float:
    return params.fixed_speed


def stance_foot_x(step: int, params: Params) -> float:
    return step * 2.0 * params.leg_length * math.sin(params.alpha)


def hip_position(step: int, theta_stance: float, params: Params) -> tuple[float, float]:
    sx = stance_foot_x(step, params)
    sz = ramp_height(sx, params) + params.foot_radius / math.cos(params.gamma)
    return (
        sx + params.leg_length * math.sin(theta_stance),
        sz + params.leg_length * math.cos(theta_stance),
    )


def foot_position(
    hip_x: float, hip_z: float, theta: float, params: Params
) -> tuple[float, float]:
    return (
        hip_x - params.leg_length * math.sin(theta),
        hip_z - params.leg_length * math.cos(theta),
    )


def swing_clearance(step: int, state: np.ndarray, params: Params) -> float:
    theta_stance, theta_swing = float(state[0]), float(state[1])
    hip_x, hip_z = hip_position(step, theta_stance, params)
    fx, fz = foot_position(hip_x, hip_z, theta_swing, params)
    return fz - (ramp_height(fx, params) + params.foot_radius / math.cos(params.gamma))


def dynamics(_t: float, y: np.ndarray, params: Params) -> np.ndarray:
    theta_stance, theta_swing, omega_stance, omega_swing = y
    # Reduced passive compass template.  The stance leg receives a constant
    # downhill gravity gain over the step; the impact map removes energy.
    drop = math.sin(params.gamma) * 2.0 * params.leg_length * math.sin(params.alpha)
    gain = (
        params.energy_gain_scale
        * 2.0
        * params.gravity
        * max(drop, 1e-8)
        / params.leg_length
    )
    d_omega_stance = gain / max(4.0 * params.alpha, 1e-8)
    target_swing = -theta_stance
    d_omega_swing = (
        -params.passive_hip_stiffness * (theta_swing - target_swing)
        - params.swing_damping * omega_swing
        - 0.10 * params.gravity / params.leg_length * math.sin(theta_swing)
    )
    return np.array(
        [omega_stance, omega_swing, d_omega_stance, d_omega_swing], dtype=float
    )


def rk4_step(y: np.ndarray, dt: float, params: Params, t: float) -> np.ndarray:
    k1 = dynamics(t, y, params)
    k2 = dynamics(t + 0.5 * dt, y + 0.5 * dt * k1, params)
    k3 = dynamics(t + 0.5 * dt, y + 0.5 * dt * k2, params)
    k4 = dynamics(t + dt, y + dt * k3, params)
    return y + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0


def event_value(step: int, y: np.ndarray, params: Params) -> float:
    # Hybrid event: the stance leg reaches the next foot-placement angle. The
    # swing leg state is still integrated, but the impact map handles the
    # instantaneous relabeling/collision at this section.
    return params.alpha - float(y[0])


def bisect_event(
    y0: np.ndarray,
    y1: np.ndarray,
    t0: float,
    t1: float,
    step: int,
    params: Params,
    event_fn: Callable[[int, np.ndarray, Params], float] = event_value,
) -> tuple[float, np.ndarray]:
    lo_t, hi_t = t0, t1
    lo_y, hi_y = y0.copy(), y1.copy()
    for _ in range(20):
        mid_t = 0.5 * (lo_t + hi_t)
        mid_y = rk4_step(lo_y, mid_t - lo_t, params, lo_t)
        if event_fn(step, mid_y, params) <= 0:
            hi_t, hi_y = mid_t, mid_y
        else:
            lo_t, lo_y = mid_t, mid_y
    return hi_t, hi_y


def impact_map(pre: np.ndarray, params: Params) -> np.ndarray:
    theta_stance, theta_swing, omega_stance, omega_swing = [float(v) for v in pre]
    pre_speed = max(0.02, abs(omega_stance))
    post_speed = params.collision_retention * pre_speed
    post_speed = max(0.06, post_speed)
    return np.array(
        [-params.alpha, params.alpha, post_speed, -0.35 * post_speed], dtype=float
    )


def make_row(
    t: float, step: int, y: np.ndarray, params: Params, phase: float, event: str = ""
) -> dict[str, float | int | str]:
    theta_stance, theta_swing, omega_stance, omega_swing = [float(v) for v in y]
    hip_x, hip_z = hip_position(step, theta_stance, params)
    swing_x, swing_z = foot_position(hip_x, hip_z, theta_swing, params)
    sx = stance_foot_x(step, params)
    sz = ramp_height(sx, params) + params.foot_radius / math.cos(params.gamma)
    support = "left" if step % 2 == 0 else "right"
    if support == "left":
        left_angle, right_angle = theta_stance, theta_swing
        left_foot_x, left_foot_z = sx, sz
        right_foot_x, right_foot_z = swing_x, swing_z
    else:
        left_angle, right_angle = theta_swing, theta_stance
        left_foot_x, left_foot_z = swing_x, swing_z
        right_foot_x, right_foot_z = sx, sz
    return {
        "time": t,
        "step": step,
        "phase": phase,
        "support": support,
        "event": event,
        "theta_stance": theta_stance,
        "theta_swing": theta_swing,
        "omega_stance": omega_stance,
        "omega_swing": omega_swing,
        "left_angle": left_angle,
        "right_angle": right_angle,
        "hip_x": hip_x,
        "hip_z": hip_z,
        "left_foot_x": left_foot_x,
        "left_foot_z": left_foot_z,
        "right_foot_x": right_foot_x,
        "right_foot_z": right_foot_z,
        "swing_clearance": swing_clearance(step, y, params),
    }


def simulate(
    params: Params,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
    rows: list[dict[str, float | int | str]] = []
    poincare: list[dict[str, float]] = []
    y = np.array(
        [
            -params.alpha,
            params.alpha,
            params.fixed_speed + params.initial_error,
            -0.35 * params.fixed_speed,
        ],
        dtype=float,
    )
    t = 0.0
    v_star = fixed_point_speed(params)

    for step in range(params.steps):
        step_start_t = t
        step_rows: list[dict[str, float | int | str]] = []
        max_step_time = 1.6
        next_sample_index = 0
        sample_stride = max(
            1, int((max_step_time / params.dt) / params.samples_per_step)
        )
        event_hit = False

        for i in range(int(max_step_time / params.dt)):
            if i % sample_stride == 0:
                phase = min(1.0, (t - step_start_t) / max_step_time)
                step_rows.append(make_row(t, step, y, params, phase))

            y_next = rk4_step(y, params.dt, params, t)
            if not np.all(np.isfinite(y_next)) or np.max(np.abs(y_next)) > 50:
                break
            if i > 30 and event_value(step, y_next, params) <= 0:
                event_t, event_y = bisect_event(
                    y, y_next, t, t + params.dt, step, params
                )
                t, y = event_t, event_y
                step_rows.append(make_row(t, step, y, params, 1.0, "touchdown"))
                event_hit = True
                break
            y = y_next
            t += params.dt

        pre = y.copy()
        rows.extend(step_rows)
        post = impact_map(pre, params)
        speed_error = abs(float(post[2]) - v_star)
        poincare.append(
            {
                "step": float(step),
                "time": t,
                "theta_stance": float(post[0]),
                "theta_swing": float(post[1]),
                "omega_stance": float(post[2]),
                "omega_swing": float(post[3]),
                "fixed_speed": v_star,
                "speed_error": speed_error,
                "event_hit": 1.0 if event_hit else 0.0,
                "step_duration": t - step_start_t,
            }
        )
        y = post
        rows.append(make_row(t, step + 1, y, params, 0.0, "impact_map"))

    return rows, poincare


def write_csv(rows: list[dict[str, float | int | str]], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--slope", type=float, default=5.0)
    args = parser.parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    params = Params(steps=args.steps, slope_deg=args.slope)
    rows, poincare = simulate(params)
    write_csv(rows, OUT_DIR / "hybrid_compass_data.csv")
    write_csv(poincare, OUT_DIR / "hybrid_compass_poincare.csv")
    summary = {
        "params": asdict(params),
        "fixed_speed": fixed_point_speed(params),
        "steps": params.steps,
        "valid_touchdowns": int(sum(1 for p in poincare if p["event_hit"] >= 0.5)),
        "final_speed_error": poincare[-1]["speed_error"],
        "no_actuators": True,
        "no_reward_function": True,
        "proof_role": "hybrid dynamics plus Poincare return map",
        "scipy_note": "scipy unavailable during implementation; numpy RK4 + event bisection used",
    }
    (OUT_DIR / "hybrid_compass_params.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT_DIR / "hybrid_compass_data.csv")
    print(OUT_DIR / "hybrid_compass_poincare.csv")


if __name__ == "__main__":
    main()

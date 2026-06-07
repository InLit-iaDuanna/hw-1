from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
MODEL_PATH = ROOT / "models" / "compass_gait.xml"
LEG_LENGTH = 1.0


@dataclass(frozen=True)
class Params:
    slope_deg: float = 4.5
    hip_mass: float = 4.5
    foot_radius: float = 0.05
    friction: float = 0.9
    joint_damping: float = 0.012
    hip_vx: float = 0.26
    hip_vz: float = -0.02
    stance_angle_deg: float = 9.0
    swing_angle_deg: float = -26.0
    swing_omega: float = 0.65


@dataclass
class Score:
    contacts: int
    alternating_contacts: int
    forward_distance: float
    duration: float
    min_hip_clearance: float
    fell: bool
    nan_or_blowup: bool

    @property
    def rank_tuple(self) -> tuple[float, float, float, float]:
        return (
            float(self.alternating_contacts),
            self.forward_distance,
            self.duration,
            self.min_hip_clearance,
        )


def ramp_height(x: float, slope_rad: float) -> float:
    return -math.tan(slope_rad) * x


def foot_position(qpos: np.ndarray, leg_angle: float) -> tuple[float, float]:
    hip_x, hip_z = qpos[0], qpos[1]
    return (
        hip_x - LEG_LENGTH * math.sin(leg_angle),
        hip_z - LEG_LENGTH * math.cos(leg_angle),
    )


def contact_feet(model: mujoco.MjModel, data: mujoco.MjData) -> set[str]:
    left_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot")
    right_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot")
    ramp_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    feet: set[str] = set()

    for i in range(data.ncon):
        con = data.contact[i]
        pair = {con.geom1, con.geom2}
        if ramp_id not in pair:
            continue
        if left_id in pair:
            feet.add("left")
        if right_id in pair:
            feet.add("right")
    return feet


def write_param_model(params: Params, target: Path) -> None:
    xml = MODEL_PATH.read_text(encoding="utf-8")
    xml = xml.replace('euler="0 5 0"', f'euler="0 {params.slope_deg:.6f} 0"')
    xml = xml.replace(
        'mass="4.0" material="hip_mat"',
        f'mass="{params.hip_mass:.6f}" material="hip_mat"',
    )
    xml = xml.replace(
        'size="0.04" mass="0.05"', f'size="{params.foot_radius:.6f}" mass="0.05"'
    )
    xml = xml.replace(
        'friction="0.85 0.02 0.002"', f'friction="{params.friction:.6f} 0.02 0.002"'
    )
    xml = xml.replace('damping="0.015"', f'damping="{params.joint_damping:.6f}"')
    target.write_text(xml, encoding="utf-8")


def initialize_state(
    model: mujoco.MjModel, data: mujoco.MjData, params: Params
) -> None:
    slope = math.radians(params.slope_deg)
    stance = math.radians(params.stance_angle_deg)
    swing = math.radians(params.swing_angle_deg)
    stance_foot_x = 0.0
    hip_x = stance_foot_x + LEG_LENGTH * math.sin(stance)
    stance_foot_z = ramp_height(stance_foot_x, slope) + params.foot_radius * 1.02
    hip_z = stance_foot_z + LEG_LENGTH * math.cos(stance)

    data.qpos[:] = [hip_x, hip_z, stance, swing]
    data.qvel[:] = [params.hip_vx, params.hip_vz, -0.15, params.swing_omega]
    mujoco.mj_forward(model, data)


def simulate(
    params: Params, duration: float, dt_log: float, keep_rows: bool
) -> tuple[Score, list[dict[str, float | str]]]:
    OUT_DIR.mkdir(exist_ok=True)
    temp_model = OUT_DIR / "_active_compass_gait.xml"
    write_param_model(params, temp_model)
    model = mujoco.MjModel.from_xml_path(str(temp_model))
    data = mujoco.MjData(model)
    initialize_state(model, data, params)

    rows: list[dict[str, float | str]] = []
    next_log = 0.0
    last_feet: set[str] = set()
    last_contact_side: str | None = None
    last_event_time = -1.0
    contacts = 0
    alternating = 0
    start_x = float(data.qpos[0])
    min_clearance = 999.0
    fell = False
    nan_or_blowup = False
    max_steps = int(duration / model.opt.timestep)
    slope = math.radians(params.slope_deg)

    for _ in range(max_steps):
        mujoco.mj_step(model, data)
        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            nan_or_blowup = True
            break
        if abs(float(data.qvel[0])) > 25 or abs(float(data.qvel[1])) > 25:
            nan_or_blowup = True
            break

        left_x, left_z = foot_position(data.qpos, float(data.qpos[2]))
        right_x, right_z = foot_position(data.qpos, float(data.qpos[3]))
        hip_clearance = float(data.qpos[1]) - ramp_height(float(data.qpos[0]), slope)
        min_clearance = min(min_clearance, hip_clearance)

        if hip_clearance < 0.28:
            fell = True
            break

        feet = contact_feet(model, data)
        new_feet = feet - last_feet
        if new_feet and data.time - last_event_time >= 0.18:
            side = sorted(new_feet)[0]
            contacts += 1
            if last_contact_side is not None and side != last_contact_side:
                alternating += 1
            last_contact_side = side
            last_event_time = float(data.time)
        last_feet = feet

        if keep_rows and data.time >= next_log:
            rows.append(
                {
                    "time": data.time,
                    "hip_x": float(data.qpos[0]),
                    "hip_z": float(data.qpos[1]),
                    "left_angle": float(data.qpos[2]),
                    "right_angle": float(data.qpos[3]),
                    "hip_vx": float(data.qvel[0]),
                    "hip_vz": float(data.qvel[1]),
                    "left_omega": float(data.qvel[2]),
                    "right_omega": float(data.qvel[3]),
                    "left_foot_x": left_x,
                    "left_foot_z": left_z,
                    "right_foot_x": right_x,
                    "right_foot_z": right_z,
                    "contacts": "+".join(sorted(feet)),
                    "hip_clearance": hip_clearance,
                }
            )
            next_log += dt_log

    score = Score(
        contacts=contacts,
        alternating_contacts=alternating,
        forward_distance=float(data.qpos[0]) - start_x,
        duration=float(data.time),
        min_hip_clearance=min_clearance,
        fell=fell,
        nan_or_blowup=nan_or_blowup,
    )
    return score, rows


def parameter_grid() -> Iterable[Params]:
    slopes = [4.5, 5.5, 6.5, 7.5]
    hip_masses = [3.0, 4.5, 6.0]
    foot_radii = [0.035, 0.05, 0.065]
    hip_vxs = [0.18, 0.26, 0.34]
    swing_omegas = [0.65, 0.95, 1.25]
    stance_angles = [6.0, 9.0, 12.0]
    swing_angles = [-14.0, -20.0, -26.0]

    for values in itertools.product(
        slopes,
        hip_masses,
        foot_radii,
        hip_vxs,
        swing_omegas,
        stance_angles,
        swing_angles,
    ):
        yield Params(
            slope_deg=values[0],
            hip_mass=values[1],
            foot_radius=values[2],
            hip_vx=values[3],
            swing_omega=values[4],
            stance_angle_deg=values[5],
            swing_angle_deg=values[6],
        )


def save_rows(rows: list[dict[str, float | str]], target: Path) -> None:
    if not rows:
        return
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_scan(limit: int | None) -> tuple[Params, Score]:
    best_params: Params | None = None
    best_score: Score | None = None
    scan_rows: list[dict[str, float | str | bool]] = []

    for i, params in enumerate(parameter_grid(), start=1):
        if limit is not None and i > limit:
            break
        score, _ = simulate(params, duration=7.0, dt_log=1 / 30, keep_rows=False)
        scan_rows.append({**asdict(params), **asdict(score)})
        if best_score is None or score.rank_tuple > best_score.rank_tuple:
            best_params = params
            best_score = score
            print(
                f"[scan] {i:04d} best contacts={score.alternating_contacts} dist={score.forward_distance:.3f} t={score.duration:.2f} params={params}"
            )

    if best_params is None or best_score is None:
        raise RuntimeError("parameter scan produced no candidates")

    save_rows(scan_rows, OUT_DIR / "scan_results.csv")
    return best_params, best_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scan", action="store_true", help="run parameter scan before final simulation"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="optional scan limit for faster testing"
    )
    parser.add_argument("--duration", type=float, default=8.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    if args.scan:
        params, scan_score = run_scan(args.limit)
    else:
        params = Params()
        scan_score, _ = simulate(params, duration=2.0, dt_log=1 / 30, keep_rows=False)

    score, rows = simulate(
        params, duration=args.duration, dt_log=1 / 60, keep_rows=True
    )
    save_rows(rows, OUT_DIR / "passive_compass_gait_data.csv")

    report = {
        "best_params": asdict(params),
        "scan_score": asdict(scan_score),
        "final_score": asdict(score),
        "acceptance": {
            "no_actuators": True,
            "alternating_contacts_target": 4,
            "alternating_contacts_observed": score.alternating_contacts,
            "continuous_multistep": score.alternating_contacts >= 4
            and score.forward_distance > 0.8
            and not score.nan_or_blowup,
        },
    }
    (OUT_DIR / "best_params.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

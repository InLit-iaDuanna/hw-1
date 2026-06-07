"""V15.1 scan: k_sea x foot_radius x leg_scale grid scan.

Fixed arm_mass=0.01. k_sea in {200, 500, 1000, 5000} x 6x6 geometry = 144 cells.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))

from simulate_v151 import (  # noqa: E402
    OUT_DIR,
    PassiveArmsParams,
    V151Params,
    make_v151_fsm,
    run_simulation_v151,
)

K_SEA_VALUES = [500.0, 1000.0, 5000.0, 10000.0]
ARM_MASS = 0.01
ARM_LENGTH = 0.40


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def make_params(
    k_sea: float, foot_radius: float, leg_scale: float, duration: float
) -> V151Params:
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=duration,
        arm_mass=ARM_MASS,
        arm_length=ARM_LENGTH,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=float(foot_radius),
        thigh_length=base0.thigh_length * leg_scale,
        shank_length=base0.shank_length * leg_scale,
        step_length=base0.step_length * leg_scale,
    )
    return V151Params(
        base=base,
        fsm=make_v151_fsm(base),
        k_sea=float(k_sea),
    )


def evaluate(
    k_sea: float,
    foot_radius: float,
    leg_scale: float,
    duration: float,
    sample_hz: float,
) -> dict:
    params = make_params(k_sea, foot_radius, leg_scale, duration)
    _, summary = run_simulation_v151(params, sample_hz=sample_hz)
    p = params.base
    return {
        "k_sea": k_sea,
        "foot_radius_x": float(foot_radius),
        "leg_scale_y": float(leg_scale),
        "arm_mass": ARM_MASS,
        "arm_length": ARM_LENGTH,
        "thigh_length": p.thigh_length,
        "shank_length": p.shank_length,
        "step_length": p.step_length,
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "net_actuator_work_j": float(summary["net_actuator_work_j"]),
        "energy_per_alternation_j": float(summary["energy_per_alternation_j"]),
        "score": float(summary["score"]),
        "phase_transitions": int(summary["phase_transitions"]),
        "spring_pe_max_J": float(summary["v151_extra"]["spring_pe_max_J"]),
        "spring_pe_mean_J": float(summary["v151_extra"]["spring_pe_mean_J"]),
        "q_link_max_left_deg": float(summary["v151_extra"]["q_link_max_left_deg"]),
        "q_link_max_right_deg": float(summary["v151_extra"]["q_link_max_right_deg"]),
        "failure": str(summary["failure"]),
    }


def run_scan(grid: int, duration: float, sample_hz: float) -> list[dict]:
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    total = len(K_SEA_VALUES) * grid * grid
    rows: list[dict] = []
    t0 = time.time()
    print(f"[v151.scan] k_sea={K_SEA_VALUES}, grid={grid}x{grid}, total={total}")
    for ik, k_sea in enumerate(K_SEA_VALUES):
        for ix, foot_radius in enumerate(xs):
            for iy, leg_scale in enumerate(ys):
                try:
                    row = evaluate(k_sea, foot_radius, leg_scale, duration, sample_hz)
                except Exception as exc:
                    row = {
                        "k_sea": k_sea,
                        "foot_radius_x": float(foot_radius),
                        "leg_scale_y": float(leg_scale),
                        "arm_mass": ARM_MASS,
                        "arm_length": ARM_LENGTH,
                        "success": False,
                        "alternating_touchdowns": 0,
                        "forward_distance": 0.0,
                        "simulated_time": 0.0,
                        "active_input_energy_j": 0.0,
                        "net_actuator_work_j": 0.0,
                        "energy_per_alternation_j": 0.0,
                        "score": -1e6,
                        "phase_transitions": 0,
                        "spring_pe_max_J": 0.0,
                        "spring_pe_mean_J": 0.0,
                        "q_link_max_left_deg": 0.0,
                        "q_link_max_right_deg": 0.0,
                        "failure": f"exception:{exc.__class__.__name__}",
                    }
                row["slice"] = "v151_C_k_geom"
                row["k_index"] = ik
                row["ix"] = ix
                row["iy"] = iy
                rows.append(row)
                done = len(rows)
                elapsed = time.time() - t0
                eta = elapsed / done * (total - done) if done > 0 else 0
                print(
                    f"  [{done}/{total}] k={k_sea:.0f} foot={foot_radius:.3f} "
                    f"leg={leg_scale:.3f} success={row['success']} "
                    f"td={row['alternating_touchdowns']} fail={row['failure']} "
                    f"({elapsed:.0f}s, ETA {eta:.0f}s)"
                )
    return rows


def write_results(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "v151_C_k_geom.csv"
    priority = [
        "slice",
        "k_index",
        "k_sea",
        "ix",
        "iy",
        "arm_mass",
        "arm_length",
        "foot_radius_x",
        "leg_scale_y",
        "success",
        "alternating_touchdowns",
        "forward_distance",
        "simulated_time",
        "failure",
        "score",
        "active_input_energy_j",
        "net_actuator_work_j",
        "energy_per_alternation_j",
        "spring_pe_max_J",
        "spring_pe_mean_J",
        "q_link_max_left_deg",
        "q_link_max_right_deg",
        "phase_transitions",
        "thigh_length",
        "shank_length",
        "step_length",
    ]
    keys = priority + sorted(
        {key for row in rows for key in row.keys()} - set(priority)
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[v151.scan] -> {csv_path}")

    by_k = {}
    for k in K_SEA_VALUES:
        kr = [r for r in rows if abs(float(r.get("k_sea", -1.0)) - k) < 1e-9]
        by_k[f"{k:.0f}"] = {
            "success_n": sum(1 for r in kr if bool(r.get("success"))),
            "n_total": len(kr),
            "fall_down_n": sum(
                1 for r in kr if str(r.get("failure", "")) == "fall_down"
            ),
            "stuck_n": sum(1 for r in kr if str(r.get("failure", "")) == "stuck"),
        }
    status = {
        "k_sea_values": K_SEA_VALUES,
        "arm_mass": ARM_MASS,
        "grid": int(len(rows) / len(K_SEA_VALUES)) if K_SEA_VALUES else 0,
        "scan_rows": len(rows),
        "success_by_k": by_k,
        "v14c_baseline_success_rate": "5/36 = 13.9%",
    }
    status_path = OUT_DIR / "v151_scan_status.json"
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[v151.scan] -> {status_path}")
    print(json.dumps(status, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--sample-hz", type=float, default=160.0)
    args = parser.parse_args()
    rows = run_scan(args.grid, args.duration, args.sample_hz)
    write_results(rows)


if __name__ == "__main__":
    main()

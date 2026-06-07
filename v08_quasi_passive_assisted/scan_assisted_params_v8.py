from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_assisted_gait_v8 import OUT_DIR, AssistedParams, run_simulation


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    slopes = [2.0, 3.5, 5.0, 0.0]
    foot_radii = [0.055, 0.04, 0.07]
    initial_vxs = [0.10, 0.08, 0.15, 0.25]
    assist_torques = [0.45, 0.60, 0.35, 0.25, 0.15]
    assist_durations = [0.70, 0.40, 1.20, 0.18, 0.12]
    knee_stiffnesses = [1.00, 0.60, 2.00, 0.25, 0.12, 0.05]
    knee_dampings = [0.12, 0.08, 0.20, 0.035]
    hip_stiffnesses = [0.15, 0.08, 0.30, 0.03, 0.0, 0.60]
    hip_dampings = [0.02, 0.05, 0.10, 0.20]
    swing_foot_xs = [0.45, 0.42, 0.50, 0.58, 0.36]
    target_degs = [-20.0, -16.0, -8.0, 0.0, 8.0, -24.0]

    results: list[dict] = []
    best_summary: dict | None = None
    best_params: AssistedParams | None = None

    max_trials = 1200
    for values in product(
        slopes,
        foot_radii,
        initial_vxs,
        assist_torques,
        assist_durations,
        knee_stiffnesses,
        knee_dampings,
        hip_stiffnesses,
        hip_dampings,
        swing_foot_xs,
        target_degs,
    ):
        params = AssistedParams(
            slope_deg=values[0],
            foot_radius=values[1],
            initial_vx=values[2],
            assist_torque=values[3],
            assist_duration=values[4],
            knee_stiffness=values[5],
            knee_damping=values[6],
            hip_joint_stiffness=values[7],
            hip_joint_damping=values[8],
            swing_foot_x=values[9],
            assist_target_deg=values[10],
            duration=12.0,
        )
        _, summary = run_simulation(params, save_prefix=None, sample_hz=50.0)
        flat = {
            **asdict(params),
            "score": summary["score"],
            "alternating_touchdowns": summary["alternating_touchdowns"],
            "forward_distance": summary["forward_distance"],
            "simulated_time": summary["simulated_time"],
            "failure": summary["failure"],
            "active_input_energy_j": summary["active_input_energy_j"],
            "energy_per_alternation_j": summary["energy_per_alternation_j"],
        }
        results.append(flat)
        if best_summary is None or summary["score"] > best_summary["score"]:
            best_summary = summary
            best_params = params
        if len(results) >= max_trials:
            break
        if (
            best_summary
            and best_summary["alternating_touchdowns"] >= 10
            and best_summary["simulated_time"] >= 10.0
        ):
            break

    results.sort(key=lambda r: r["score"], reverse=True)
    with (OUT_DIR / "v8_scan_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    assert best_summary is not None and best_params is not None
    _, best_summary = run_simulation(
        best_params, save_prefix="v8_assisted_walk", sample_hz=160.0
    )
    best_summary["params"] = asdict(best_params)
    (OUT_DIR / "v8_best_params.json").write_text(
        json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT_DIR / "v8_scan_results.csv")
    print(OUT_DIR / "v8_best_params.json")


if __name__ == "__main__":
    main()

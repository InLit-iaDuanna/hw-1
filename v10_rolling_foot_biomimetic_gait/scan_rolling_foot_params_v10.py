from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_rolling_foot_gait_v10 import OUT_DIR, RollingFootParams, run_simulation


def candidate_params() -> list[RollingFootParams]:
    candidates = [
        RollingFootParams(
            slope_deg=0.0,
            gait_period=0.80,
            hip_torque_limit=4.0,
            knee_torque_limit=4.0,
            hip_kp=30.0,
            hip_kd=6.0,
            knee_kp=16.0,
            knee_kd=2.0,
            initial_vx=0.03,
            torso_mass=0.05,
            foot_length=0.12,
            foot_radius=0.04,
            ankle_stiffness=10.0,
            ankle_damping=0.08,
            duration=12.0,
        )
    ]
    for foot_length, ankle_stiffness, ankle_damping, period, htau, ktau in product(
        [0.10, 0.12, 0.14, 0.16],
        [2.5, 5.0, 10.0],
        [0.08, 0.20, 0.50],
        [0.60, 0.80, 1.00],
        [4.0, 8.0],
        [2.0, 4.0],
    ):
        candidates.append(
            RollingFootParams(
                slope_deg=0.0,
                gait_period=period,
                hip_torque_limit=htau,
                knee_torque_limit=ktau,
                hip_kp=30.0,
                hip_kd=6.0,
                knee_kp=16.0,
                knee_kd=2.0,
                initial_vx=0.03,
                torso_mass=0.05,
                foot_length=foot_length,
                foot_radius=0.04,
                ankle_stiffness=ankle_stiffness,
                ankle_damping=ankle_damping,
                duration=12.0,
            )
        )
    return candidates


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    results: list[dict] = []
    best_summary: dict | None = None
    best_params: RollingFootParams | None = None
    for index, params in enumerate(candidate_params()):
        _, summary = run_simulation(params, sample_hz=20.0)
        flat = {
            **asdict(params),
            "score": summary["score"],
            "success": summary["success"],
            "alternating_touchdowns": summary["alternating_touchdowns"],
            "forward_distance": summary["forward_distance"],
            "simulated_time": summary["simulated_time"],
            "failure": summary["failure"],
            "active_input_energy_j": summary["active_input_energy_j"],
        }
        results.append(flat)
        if best_summary is None or summary["score"] > best_summary["score"]:
            best_summary = summary
            best_params = params
        if index >= 80 and best_summary and best_summary["success"]:
            break

    results.sort(key=lambda item: item["score"], reverse=True)
    with (OUT_DIR / "v10_scan_results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    assert best_params is not None
    _, best_summary = run_simulation(
        best_params, save_prefix="v10_rolling_foot_walk", sample_hz=160.0
    )
    best_summary["params"] = asdict(best_params)
    (OUT_DIR / "v10_best_params.json").write_text(
        json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT_DIR / "v10_scan_results.csv")
    print(OUT_DIR / "v10_best_params.json")


if __name__ == "__main__":
    main()

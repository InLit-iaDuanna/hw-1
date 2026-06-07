from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_stable_gait_v9 import OUT_DIR, StableParams, run_simulation


def candidate_params() -> list[StableParams]:
    candidates = [
        StableParams(
            slope_deg=0.0,
            gait_period=0.45,
            hip_torque_limit=4.0,
            knee_torque_limit=4.0,
            hip_kp=30.0,
            hip_kd=6.0,
            knee_kp=16.0,
            knee_kd=2.0,
            initial_vx=0.03,
            torso_mass=0.05,
            foot_length=0.08,
            foot_radius=0.04,
            duration=12.0,
        )
    ]
    for slope, period, htau, ktau, hkp, hkd in product(
        [0.0, 1.0, 2.0, 3.5],
        [0.45, 0.60, 0.80, 1.00],
        [4.0, 8.0, 12.0],
        [1.0, 2.0, 4.0],
        [18.0, 30.0, 45.0],
        [4.0, 6.0, 8.0],
    ):
        candidates.append(
            StableParams(
                slope_deg=slope,
                gait_period=period,
                hip_torque_limit=htau,
                knee_torque_limit=ktau,
                hip_kp=hkp,
                hip_kd=hkd,
                knee_kp=16.0,
                knee_kd=2.0,
                initial_vx=0.03,
                torso_mass=0.05,
                foot_length=0.08,
                foot_radius=0.04,
                duration=12.0,
            )
        )
    return candidates


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    results: list[dict] = []
    best_summary: dict | None = None
    best_params: StableParams | None = None
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
        if index >= 180 and best_summary and best_summary["success"]:
            break

    results.sort(key=lambda item: item["score"], reverse=True)
    with (OUT_DIR / "v9_scan_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    assert best_params is not None
    _, best_summary = run_simulation(
        best_params, save_prefix="v9_stable_walk", sample_hz=160.0
    )
    best_summary["params"] = asdict(best_params)
    (OUT_DIR / "v9_best_params.json").write_text(
        json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT_DIR / "v9_scan_results.csv")
    print(OUT_DIR / "v9_best_params.json")


if __name__ == "__main__":
    main()

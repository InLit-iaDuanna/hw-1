from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_contact_gait_v7 import OUT_DIR, ContactParams, run_simulation


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    slopes = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    foot_radii = [0.04, 0.055, 0.07, 0.085]
    frictions = [0.9, 1.2, 1.5]
    hip_masses = [3.5, 4.5, 5.5]
    initial_vxs = [0.15, 0.25, 0.35, 0.45, 0.60]
    knee_limits = [45.0, 55.0, 65.0]
    release_phases = [0.04, 0.10, 0.16]
    swing_hip_vels = [0.25, 0.45, 0.65]
    swing_clearances = [0.06, 0.10]

    results: list[dict] = []
    best_summary: dict | None = None
    best_params: ContactParams | None = None
    best_rows = None

    max_trials = 420
    for values in product(
        slopes,
        foot_radii,
        frictions,
        hip_masses,
        initial_vxs,
        knee_limits,
        release_phases,
        swing_hip_vels,
        swing_clearances,
    ):
        params = ContactParams(
            slope_deg=values[0],
            foot_radius=values[1],
            friction=values[2],
            hip_mass=values[3],
            initial_vx=values[4],
            knee_limit_deg=values[5],
            release_phase=values[6],
            swing_hip_vel=values[7],
            swing_foot_clearance=values[8],
            duration=8.0,
        )
        rows, summary = run_simulation(params, save_prefix=None, sample_hz=60.0)
        flat = {
            **asdict(params),
            "score": summary["score"],
            "alternating_touchdowns": summary["alternating_touchdowns"],
            "forward_distance": summary["forward_distance"],
            "simulated_time": summary["simulated_time"],
            "failure": summary["failure"],
        }
        results.append(flat)
        if best_summary is None or summary["score"] > best_summary["score"]:
            best_summary = summary
            best_params = params
            best_rows = rows
        if len(results) >= max_trials:
            break
        if (
            len(results) >= 120
            and best_summary
            and best_summary["alternating_touchdowns"] >= 3
            and best_summary["simulated_time"] > 2.0
        ):
            # A real passive-contact success is enough for this homework
            # exploration; keep the scan practical.
            break

    results.sort(key=lambda r: r["score"], reverse=True)
    with (OUT_DIR / "v7_scan_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    assert (
        best_summary is not None and best_params is not None and best_rows is not None
    )
    run_simulation(best_params, save_prefix="v7_best_attempt", sample_hz=120.0)
    best_summary["params"] = asdict(best_params)
    (OUT_DIR / "v7_best_params.json").write_text(
        json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT_DIR / "v7_scan_results.csv")
    print(OUT_DIR / "v7_best_params.json")


if __name__ == "__main__":
    main()

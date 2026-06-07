"""Scan the V14 passive-arm grid using the V13.6 FSM hip controller."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_passive_arms_v136 import (
    OUT_DIR,
    PassiveArmsParams,
    make_v14b_params,
    run_simulation,
)

ARM_MASS = [0.001, 0.05, 0.10, 0.20, 0.30, 0.45, 0.60]
ARM_LENGTH = [0.20, 0.30, 0.40, 0.50, 0.60]


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    best = None
    for arm_mass, arm_length in product(ARM_MASS, ARM_LENGTH):
        base = PassiveArmsParams(
            arm_mass=arm_mass,
            arm_length=arm_length,
            arm_damping=0.02,
            arm_stiffness=0.0,
            duration=12.0,
        )
        params = make_v14b_params(base)
        _, summary = run_simulation(params, sample_hz=20.0)
        flat = {
            "arm_mass": arm_mass,
            "arm_length": arm_length,
            "arm_damping": base.arm_damping,
            "arm_stiffness": base.arm_stiffness,
            "total_mass_kg": summary["total_mass_kg"],
            "score": summary["score"],
            "success": summary["success"],
            "alternating_touchdowns": summary["alternating_touchdowns"],
            "forward_distance": summary["forward_distance"],
            "simulated_time": summary["simulated_time"],
            "failure": summary["failure"],
            "active_input_energy_j": summary["active_input_energy_j"],
            "energy_per_alternation_j": summary["energy_per_alternation_j"],
            "phase_transitions": summary["phase_transitions"],
            "stance_early_s": summary["phase_durations_s"]["stance_early"],
            "stance_late_s": summary["phase_durations_s"]["stance_late"],
            "swing_thrust_s": summary["phase_durations_s"]["swing_thrust"],
            "swing_retract_s": summary["phase_durations_s"]["swing_retract"],
            "controller": summary["controller"],
        }
        rows.append(flat)
        marker = "OK" if summary["success"] else summary["failure"]
        print(
            f"  arm_mass={arm_mass:.3f} arm_length={arm_length:.2f} -> {marker}  "
            f"alt={summary['alternating_touchdowns']}  fwd={summary['forward_distance']:.2f}"
        )
        if best is None or summary["score"] > best[1]["score"]:
            best = (base, summary)

    rows.sort(key=lambda row: row["score"], reverse=True)
    csv_path = OUT_DIR / "v14b_arm_scan.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    success = [row for row in rows if row["success"]]
    mass_005 = [row for row in rows if abs(row["arm_mass"] - 0.05) < 1e-9]
    mass_005_success = sum(1 for row in mass_005 if row["success"])
    if mass_005_success >= 2:
        verdict = "pass"
    elif mass_005_success == 1:
        verdict = "borderline_sensitivity_followup"
    else:
        verdict = "reject"

    summary_idx = {
        "n_total": len(rows),
        "n_success": len(success),
        "success_rate": len(success) / len(rows),
        "best_arm_mass": rows[0]["arm_mass"],
        "best_arm_length": rows[0]["arm_length"],
        "best_score": rows[0]["score"],
        "scan_axes": {"arm_mass": ARM_MASS, "arm_length": ARM_LENGTH},
        "controller": "v13_6_fsm_on_v14_passive_arms",
        "fixed_arm_damping": 0.02,
        "fixed_arm_stiffness": 0.0,
        "critical_row_arm_mass_0_05": {
            "success": mass_005_success,
            "total": len(mass_005),
            "verdict": verdict,
        },
        "v13_6_prereq": {
            "slice_C_success": "4/36",
            "slice_C_rate_pct": 11.11111111111111,
            "verdict": "tier_B_partial",
            "note": "Exploratory V14b回流; not a strong pass over V10.",
        },
    }
    (OUT_DIR / "v14b_arm_scan_summary.json").write_text(
        json.dumps(summary_idx, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if best is not None:
        best_params, best_summary = best
        _, saved_summary = run_simulation(
            make_v14b_params(best_params), save_prefix="v14b_best", sample_hz=160.0
        )
        saved_summary["params"] = asdict(best_params)
        (OUT_DIR / "v14b_best_params.json").write_text(
            json.dumps(saved_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(OUT_DIR / "v14b_best_params.json")
        print(f"best score: {best_summary['score']:.2f}")
    print(csv_path)
    print(f"success: {len(success)}/{len(rows)} = {len(success)/len(rows):.1%}")
    print(f"arm_mass=0.05: {mass_005_success}/{len(mass_005)} -> {verdict}")


if __name__ == "__main__":
    main()

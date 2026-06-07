"""V15.1L1 smoke: SEA + motor dynamics experimental matrix.

Research question: does SEA compliance buffer Coulomb friction?
9 conditions: 3 k_sea × {ideal, mx64ar_raw, mx64ar_comp}
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))

from simulate_v151_L1 import (  # noqa: E402
    OUT_DIR,
    PassiveArmsParams,
    V151L1Params,
    make_v151L1_fsm,
    run_simulation_v151_L1,
)

CONDITIONS = [
    {"k_sea": 500, "preset": "ideal", "comp": False, "tag": "ideal_k0500"},
    {"k_sea": 5000, "preset": "ideal", "comp": False, "tag": "ideal_k5000"},
    {"k_sea": 10000, "preset": "ideal", "comp": False, "tag": "ideal_k10000"},
    {"k_sea": 500, "preset": "mx64ar", "comp": False, "tag": "mx64ar_raw_k0500"},
    {"k_sea": 5000, "preset": "mx64ar", "comp": False, "tag": "mx64ar_raw_k5000"},
    {"k_sea": 10000, "preset": "mx64ar", "comp": False, "tag": "mx64ar_raw_k10000"},
    {"k_sea": 500, "preset": "mx64ar", "comp": True, "tag": "mx64ar_comp_k0500"},
    {"k_sea": 5000, "preset": "mx64ar", "comp": True, "tag": "mx64ar_comp_k5000"},
    {"k_sea": 10000, "preset": "mx64ar", "comp": True, "tag": "mx64ar_comp_k10000"},
]

FOOT_RADIUS = 0.042
LEG_SCALE = 1.02
DURATION = 12.0


def make_params(k_sea: float, preset: str, comp: bool) -> V151L1Params:
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=DURATION,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=FOOT_RADIUS,
        thigh_length=base0.thigh_length * LEG_SCALE,
        shank_length=base0.shank_length * LEG_SCALE,
        step_length=base0.step_length * LEG_SCALE,
    )
    return V151L1Params(
        base=base,
        fsm=make_v151L1_fsm(base),
        k_sea=float(k_sea),
        motor_preset=preset,
        compensate_friction=comp,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for cond in CONDITIONS:
        tag = cond["tag"]
        print(f"[v151L1.smoke] {tag} ...", flush=True)
        params = make_params(cond["k_sea"], cond["preset"], cond["comp"])
        summary = run_simulation_v151_L1(params, save_prefix=f"v151L1_{tag}")
        summary["tag"] = tag
        results.append(summary)
        status = "OK" if summary["success"] else summary["failure"]
        print(
            f"  -> {status} fwd={summary['forward_distance']:.2f}m td={summary['alternating_touchdowns']}"
        )

    # Verdicts
    ideal_ok = all(r["success"] for r in results if r["tag"].startswith("ideal_"))
    raw_successes = [r for r in results if "mx64ar_raw" in r["tag"] and r["success"]]
    comp_successes = [r for r in results if "mx64ar_comp" in r["tag"] and r["success"]]

    verdict = {
        "ideal_baseline_all_pass": ideal_ok,
        "sea_buffers_friction": len(raw_successes) > 0,
        "sea_buffers_friction_tags": [r["tag"] for r in raw_successes],
        "compensation_works_with_sea": len(comp_successes) > 0,
        "compensation_tags": [r["tag"] for r in comp_successes],
    }
    if len(raw_successes) > 0:
        verdict["primary_finding"] = "sea_mechanical_friction_buffering_confirmed"
        verdict["note"] = (
            f"SEA at k={raw_successes[0]['k_sea']} buffers MX-64AR Coulomb friction without software compensation"
        )
    elif len(comp_successes) > 0:
        verdict["primary_finding"] = "sea_needs_compensation_same_as_rigid"
        verdict["note"] = (
            "SEA spring does not buffer Coulomb friction; V13.7 compensation still required"
        )
    else:
        verdict["primary_finding"] = "motor_integration_failed"
        verdict["note"] = "Neither raw nor compensated mx64ar works — check integration"

    table = {"conditions": CONDITIONS, "results": results, "verdict": verdict}
    out_path = OUT_DIR / "smoke_v151_L1_table.json"
    out_path.write_text(
        json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("V15.1L1 Verdict:")
    print(json.dumps(verdict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""
Contact stiffness robustness test for V13.6.1 best FSM.

Compares V13.6.1 best control params on slice C (6x6 grid) with:
  - Soft contact: solref=(0.006, 1)   [current V10]
  - Stiff contact: solref=(0.0007, 1) [FEA-calibrated]

If success rate drops >5pp, FSM is sensitive to contact stiffness.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import json

from simulate_v13_6 import *

# V13.6.1 best params (from phase search, candidate 6)
BEST_PARAMS = V136Params(
    stance_early=PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0),
    stance_late=PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0),
    swing_thrust=PhaseParams(k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0),
    swing_retract=PhaseParams(k_E=0.0, k_PD=10.0, tau_max=3.0, kd=6.0),
    base=V10Params(knee_kp=16.0, knee_kd=2.0, knee_torque_limit=4.0),
)

# Slice C grid (from V13 atlas)
SLOPE_VALS = [0.02, 0.026, 0.032, 0.038, 0.044, 0.05]
STEP_VALS = [0.32, 0.34, 0.36, 0.38, 0.40, 0.42]


def run_grid(model_xml_name, label):
    """Run grid with specified model XML (temporarily patch MODEL_PATH)."""
    import simulate_v13_6

    original_path = simulate_v13_6.MODEL_PATH

    # Patch MODEL_PATH to use the specified XML
    simulate_v13_6.MODEL_PATH = V10_DIR / "models" / model_xml_name

    results = []
    success_count = 0
    try:
        for slope in SLOPE_VALS:
            for step in STEP_VALS:
                v10_p = V10Params(slope_deg=slope * 180 / 3.14159, step_length=step)
                params_with_base = replace(BEST_PARAMS, base=v10_p)
                _, summary = run_simulation(params_with_base)
                success = summary["success"]
                results.append(
                    {
                        "slope": slope,
                        "step": step,
                        "success": success,
                        "failure": summary["failure"],
                        "forward": summary["forward_distance"],
                    }
                )
                if success:
                    success_count += 1
                print(
                    f"{label} | slope={slope:.3f} step={step:.2f} -> {'OK' if success else 'FAIL'}"
                )
    finally:
        # Restore original MODEL_PATH
        simulate_v13_6.MODEL_PATH = original_path

    rate = success_count / len(results)
    print(f"\n{label} success: {success_count}/36 = {rate*100:.1f}%")
    return results, rate


def main():
    OUT = ROOT / "out"
    OUT.mkdir(exist_ok=True)

    # Soft contact (baseline)
    print("=== SOFT CONTACT (solref=0.006) ===")
    res_soft, rate_soft = run_grid("rolling_foot_walker.xml", "SOFT")

    # Stiff contact (calibrated)
    print("\n=== STIFF CONTACT (solref=0.0007, FEA-calibrated) ===")
    res_stiff, rate_stiff = run_grid("rolling_foot_walker_stiff.xml", "STIFF")

    delta_pp = (rate_stiff - rate_soft) * 100

    summary = {
        "test": "V13.6.1 best FSM contact stiffness robustness",
        "soft_contact_solref": [0.006, 1.0],
        "stiff_contact_solref": [0.0007, 1.0],
        "soft_success_rate": round(rate_soft, 3),
        "stiff_success_rate": round(rate_stiff, 3),
        "delta_percentage_points": round(delta_pp, 2),
        "verdict": "",
        "results_soft": res_soft,
        "results_stiff": res_stiff,
    }

    if abs(delta_pp) <= 5:
        summary["verdict"] = (
            "ROBUST: FSM tolerates FEA-calibrated contact (Δ=%.1fpp)" % delta_pp
        )
    elif delta_pp < -5:
        summary["verdict"] = (
            "SENSITIVE: FSM success drops %.1fpp with stiff contact -> needs V13.7 tuning"
            % abs(delta_pp)
        )
    else:
        summary["verdict"] = (
            "IMPROVED: FSM works better with stiff contact (+%.1fpp)" % delta_pp
        )

    with open(OUT / "contact_stiffness_robustness.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(summary["verdict"])
    print("Saved: out/contact_stiffness_robustness.json")


if __name__ == "__main__":
    main()

"""V13.7 smoke：验证前馈摩擦补偿是否使 mx64ar_full 恢复行走。

对照组：
- compensated_mx64ar   : V13.7 完整补偿 + mx64ar_full（核心验证目标）
- no_comp_mx64ar       : 不补偿 + mx64ar_full（应与 V16 mx64ar_full 一致=失败）
- compensated_ideal    : V13.7 补偿 + ideal（退化对照，应与 V14c 基本一致）
- compensated_ec_i40   : V13.7 补偿 + ec_i40_53（高 J 对照）

verdict:
- L0：compensated_ideal 严格还原 V14c (≤1%)       → 失败=v13_7_implementation_bug
- 核心：compensated_mx64ar success=True            → friction_compensation_effective
- 对照：no_comp_mx64ar success=False               → v16_regression_confirmed
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

from simulate_v13_7 import (  # noqa: E402
    OUT_DIR,
    PassiveArmsParams,
    V137Params,
    make_v137_fsm,
    run_simulation_v137,
)

from common.motor_dynamics import PRESETS  # noqa: E402

ARM_MASS = 0.01
FOOT_RADIUS = 0.042
LEG_SCALE = 1.02
DURATION = 12.0
V14C_REFERENCE = (
    HW1_ROOT
    / "v14c_arm_mass_lightening"
    / "out"
    / "v14c_critical_f042_l102_summary.json"
)

L0_THRESHOLD = 0.01
RECOVERY_THRESHOLD = 0.05


def make_params(motor_preset: str, compensate: bool) -> V137Params:
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=DURATION,
        arm_mass=ARM_MASS,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=FOOT_RADIUS,
        thigh_length=base0.thigh_length * LEG_SCALE,
        shank_length=base0.shank_length * LEG_SCALE,
        step_length=base0.step_length * LEG_SCALE,
    )
    motor = PRESETS[motor_preset]
    return V137Params(
        base=base,
        fsm=make_v137_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=compensate,
    )


SMOKE_CASES = [
    ("compensated_mx64ar", "mx64ar", True),
    ("no_comp_mx64ar", "mx64ar", False),
    ("compensated_ideal", "ideal", True),
    ("compensated_ec_i40", "ec_i40_53", True),
]


def relative_diff(a: float, b: float) -> float:
    if abs(b) < 1e-9:
        return float("inf") if abs(a) > 1e-9 else 0.0
    return abs(a - b) / abs(b)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v14c = (
        json.loads(V14C_REFERENCE.read_text(encoding="utf-8"))
        if V14C_REFERENCE.exists()
        else None
    )

    rows = []
    for tag, preset, compensate in SMOKE_CASES:
        params = make_params(preset, compensate)
        prefix = f"v13_7_smoke_{tag}"
        _, summary = run_simulation_v137(params, save_prefix=prefix, sample_hz=160.0)
        rows.append(
            {
                "tag": tag,
                "motor_preset": preset,
                "compensate_friction": compensate,
                "motor_name": params.hip_motor.name,
                "joint_tau_C_eff": params.hip_motor.joint_tau_C_eff(),
                "success": bool(summary["success"]),
                "alt_touchdowns": int(summary["alternating_touchdowns"]),
                "forward_distance": float(summary["forward_distance"]),
                "simulated_time": float(summary["simulated_time"]),
                "active_input_energy_mech_j": float(
                    summary["active_input_energy_mech_j"]
                ),
                "active_input_energy_elec_j": float(
                    summary["active_input_energy_elec_j"]
                ),
                "coulomb_friction_dissipation_j": float(
                    summary["coulomb_friction_dissipation_j"]
                ),
                "motor_saturation_count_total": sum(
                    summary["motor_saturation_count"].values()
                ),
                "phase_saturation_rate": summary["phase_saturation_rate"],
                "failure": str(summary["failure"]),
            }
        )

    table: dict = {"reference": str(V14C_REFERENCE), "rows": rows}

    if v14c is None:
        table["smoke_verdict"] = "no_v14c_reference"
        _write_and_print(table)
        return

    ref = {
        "alt_touchdowns": int(v14c["alternating_touchdowns"]),
        "forward_distance": float(v14c["forward_distance"]),
        "active_input_energy_j": float(v14c["active_input_energy_j"]),
    }
    table["v14c_reference"] = ref

    ideal_row = next(r for r in rows if r["tag"] == "compensated_ideal")
    ideal_fwd_diff = relative_diff(
        ideal_row["forward_distance"], ref["forward_distance"]
    )
    ideal_energy_diff = relative_diff(
        ideal_row["active_input_energy_mech_j"], ref["active_input_energy_j"]
    )
    table["ideal_vs_v14c"] = {
        "alt_td_match": ideal_row["alt_touchdowns"] == ref["alt_touchdowns"],
        "forward_rel_diff": ideal_fwd_diff,
        "energy_rel_diff": ideal_energy_diff,
        "passes_l0_threshold": (
            ideal_row["alt_touchdowns"] == ref["alt_touchdowns"]
            and ideal_fwd_diff <= L0_THRESHOLD
            and ideal_energy_diff <= L0_THRESHOLD
        ),
    }

    comp_row = next(r for r in rows if r["tag"] == "compensated_mx64ar")
    no_comp_row = next(r for r in rows if r["tag"] == "no_comp_mx64ar")
    table["core_test"] = {
        "compensated_mx64ar_success": comp_row["success"],
        "compensated_mx64ar_alt_td": comp_row["alt_touchdowns"],
        "compensated_mx64ar_forward": comp_row["forward_distance"],
        "no_comp_mx64ar_success": no_comp_row["success"],
        "no_comp_mx64ar_failure": no_comp_row["failure"],
        "v16_regression_confirmed": not no_comp_row["success"],
    }

    if not table["ideal_vs_v14c"]["passes_l0_threshold"]:
        verdict = "v13_7_implementation_bug"
    elif comp_row["success"]:
        recovery_diff = relative_diff(
            comp_row["forward_distance"], ref["forward_distance"]
        )
        table["core_test"]["recovery_vs_v14c_fwd_diff"] = recovery_diff
        if recovery_diff <= RECOVERY_THRESHOLD:
            verdict = "friction_compensation_full_recovery"
        else:
            verdict = "friction_compensation_partial_recovery"
    else:
        verdict = "friction_compensation_ineffective"
    table["smoke_verdict"] = verdict

    _write_and_print(table)


def _write_and_print(table: dict) -> None:
    out = OUT_DIR / "smoke_v13_7_table.json"
    out.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(table, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

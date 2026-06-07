"""V16 smoke：5 档电机预设对照固定 V14c baseline 工作格 (0.01, 0.042, 1.02)。

预设：
- ideal           : J=b=τ_C=0, τ_sat=∞       (L0 退化对照, 严格 ≤1% 还原 V14c)
- mx64ar_J_only   : 只开 J_eff               (验证惯量单独效应)
- mx64ar_friction : 只开 b + τ_C             (验证摩擦单独效应)
- mx64ar_full     : 完整 MX-64AR             (L1 健康检查, ≤5% 偏差 V14c)
- ec_i40_53_full  : 完整 Maxon EC-i 40 53:1 (高 J 对照, 强制暴露惯量效应)

verdict:
- L0：ideal 行严格还原 V14c (≤1%)         → 失败=v16_implementation_bug
- L1：mx64ar_full 偏差 ≤5%                 → health_check_passed
- 电机生效：除 ideal 外至少一行偏离 ≥5%   → motor_effect_visible
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

from simulate_v16 import (  # noqa: E402
    OUT_DIR,
    PassiveArmsParams,
    V16Params,
    make_v16_fsm,
    run_simulation_v16,
)

from common.motor_dynamics import PRESETS, MotorParams  # noqa: E402

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
L1_THRESHOLD = 0.05
EFFECT_THRESHOLD = 0.05


def _mx64_J_only() -> MotorParams:
    base = PRESETS["mx64ar"]
    return MotorParams(
        name="MX-64AR (J_only)",
        Kt=base.Kt,
        J_rotor=base.J_rotor,
        N=base.N,
        eta=base.eta,
        I_max=1.0e9,
        I_cont=1.0e9,
        R_arm=0.0,
        tau_C_motor=0.0,
        b_visc_motor=0.0,
    )


def _mx64_friction_only() -> MotorParams:
    base = PRESETS["mx64ar"]
    return MotorParams(
        name="MX-64AR (friction_only)",
        Kt=base.Kt,
        J_rotor=0.0,
        N=base.N,
        eta=base.eta,
        I_max=1.0e9,
        I_cont=1.0e9,
        R_arm=base.R_arm,
        tau_C_motor=base.tau_C_motor,
        b_visc_motor=base.b_visc_motor,
    )


def smoke_motor_set() -> dict[str, MotorParams]:
    return {
        "ideal": PRESETS["ideal"],
        "mx64ar_J_only": _mx64_J_only(),
        "mx64ar_friction": _mx64_friction_only(),
        "mx64ar_full": PRESETS["mx64ar"],
        "ec_i40_53_full": PRESETS["ec_i40_53"],
    }


def make_params(motor: MotorParams) -> V16Params:
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
    return V16Params(
        base=base,
        fsm=make_v16_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
    )


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
    motor_set = smoke_motor_set()

    rows = []
    for tag, motor in motor_set.items():
        params = make_params(motor)
        prefix = f"v16_smoke_{tag}"
        _, summary = run_simulation_v16(params, save_prefix=prefix, sample_hz=160.0)
        rows.append(
            {
                "tag": tag,
                "motor_name": motor.name,
                "joint_J_eff": motor.joint_J_eff(),
                "joint_b_eff": motor.joint_b_eff(),
                "joint_tau_C_eff": motor.joint_tau_C_eff(),
                "joint_tau_sat_peak": motor.joint_tau_sat_peak(),
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
        out = OUT_DIR / "smoke_v16_table.json"
        out.write_text(
            json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(table, ensure_ascii=False, indent=2))
        return

    ref = {
        "alt_touchdowns": int(v14c["alternating_touchdowns"]),
        "forward_distance": float(v14c["forward_distance"]),
        "active_input_energy_j": float(v14c["active_input_energy_j"]),
    }
    table["v14c_reference"] = ref

    def diff_vs_v14c(row: dict) -> dict:
        return {
            "alt_td_match": row["alt_touchdowns"] == ref["alt_touchdowns"],
            "forward_rel_diff": relative_diff(
                row["forward_distance"], ref["forward_distance"]
            ),
            "energy_rel_diff": relative_diff(
                row["active_input_energy_mech_j"], ref["active_input_energy_j"]
            ),
        }

    ideal_row = next(r for r in rows if r["tag"] == "ideal")
    full_row = next(r for r in rows if r["tag"] == "mx64ar_full")
    ideal_diff = diff_vs_v14c(ideal_row)
    full_diff = diff_vs_v14c(full_row)
    table["ideal_vs_v14c"] = {
        **ideal_diff,
        "passes_l0_threshold": (
            ideal_diff["alt_td_match"]
            and ideal_diff["forward_rel_diff"] <= L0_THRESHOLD
            and ideal_diff["energy_rel_diff"] <= L0_THRESHOLD
        ),
    }
    table["mx64ar_full_vs_v14c"] = {
        **full_diff,
        "passes_l1_threshold": (
            full_diff["alt_td_match"]
            and full_diff["forward_rel_diff"] <= L1_THRESHOLD
            and full_diff["energy_rel_diff"] <= L1_THRESHOLD
        ),
    }

    baseline_fwd = ideal_row["forward_distance"]
    motor_devs = {
        r["tag"]: relative_diff(r["forward_distance"], baseline_fwd)
        for r in rows
        if r["tag"] != "ideal"
    }
    table["motor_effect_dev_vs_ideal"] = motor_devs
    table["motor_effect_visible"] = any(
        d >= EFFECT_THRESHOLD for d in motor_devs.values()
    )

    if not table["ideal_vs_v14c"]["passes_l0_threshold"]:
        verdict = "v16_implementation_bug"
    elif not table["mx64ar_full_vs_v14c"]["passes_l1_threshold"]:
        verdict = "health_check_failed"
    elif not table["motor_effect_visible"]:
        verdict = "motor_effect_not_visible"
    else:
        verdict = "passed"
    table["smoke_verdict"] = verdict

    out = OUT_DIR / "smoke_v16_table.json"
    out.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(table, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

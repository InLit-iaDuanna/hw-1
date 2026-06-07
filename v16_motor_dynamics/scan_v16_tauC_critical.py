"""V16 τ_C 临界扫描：固定 mx64ar baseline 工作格 + 真实 J/b/τ_sat，仅变库仑摩擦。

目的：smoke 揭示 mx64ar_full 失败而 mx64ar_J_only 成功，电机生效项中库仑+粘滞摩擦
是支配主因。本脚本在保留 J_eff=2.8e-3 / b_eff=0.05 / τ_sat=6.0 的真实 mx64
惯量+粘滞+饱和环境下，仅扫 τ_C_eff，找到 V13.6.1 FSM 的库仑摩擦临界阈值。

输出 V22 硬件选型约束：τ_C_eff ≤ X N·m 才能保留当前 FSM。
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

TAU_C_MOTOR_GRID = [
    0.0,
    1.0e-4,
    2.5e-4,
    5.0e-4,
    7.5e-4,
    1.0e-3,
    1.25e-3,
    1.5e-3,
    2.0e-3,
    3.0e-3,
]


def make_motor(tau_C_motor: float) -> MotorParams:
    base = PRESETS["mx64ar"]
    return MotorParams(
        name=f"MX-64AR_tauC{tau_C_motor*1000:.2f}mNm",
        Kt=base.Kt,
        J_rotor=base.J_rotor,
        N=base.N,
        eta=base.eta,
        I_max=base.I_max,
        I_cont=base.I_cont,
        R_arm=base.R_arm,
        tau_C_motor=tau_C_motor,
        b_visc_motor=base.b_visc_motor,
    )


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
        base=base, fsm=make_v16_fsm(base), hip_motor=motor, knee_motor=motor
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v14c = (
        json.loads(V14C_REFERENCE.read_text(encoding="utf-8"))
        if V14C_REFERENCE.exists()
        else None
    )
    rows = []
    for tau_C_motor in TAU_C_MOTOR_GRID:
        motor = make_motor(tau_C_motor)
        prefix = f"v16_tauC_scan_tc{int(tau_C_motor*1e6):04d}"
        _, summary = run_simulation_v16(
            make_params(motor), save_prefix=prefix, sample_hz=160.0
        )
        rows.append(
            {
                "tau_C_motor_Nm": tau_C_motor,
                "tau_C_eff_joint_Nm": motor.joint_tau_C_eff(),
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
                "failure": str(summary["failure"]),
            }
        )

    last_success_idx = max((i for i, r in enumerate(rows) if r["success"]), default=-1)
    first_fail_idx = next((i for i, r in enumerate(rows) if not r["success"]), -1)

    if last_success_idx >= 0 and first_fail_idx > last_success_idx:
        critical_lower = rows[last_success_idx]["tau_C_eff_joint_Nm"]
        critical_upper = rows[first_fail_idx]["tau_C_eff_joint_Nm"]
        verdict = "critical_threshold_found"
    elif last_success_idx == len(rows) - 1:
        critical_lower = rows[-1]["tau_C_eff_joint_Nm"]
        critical_upper = float("inf")
        verdict = "all_succeeded_extend_grid"
    elif last_success_idx < 0:
        critical_lower = -1.0
        critical_upper = rows[0]["tau_C_eff_joint_Nm"]
        verdict = "all_failed_even_at_lowest_tauC"
    else:
        critical_lower = rows[last_success_idx]["tau_C_eff_joint_Nm"]
        critical_upper = float("inf")
        verdict = "non_monotonic_recheck"

    table = {
        "reference": str(V14C_REFERENCE),
        "v14c_reference": {
            "alt_touchdowns": int(v14c["alternating_touchdowns"]) if v14c else None,
            "forward_distance": float(v14c["forward_distance"]) if v14c else None,
            "active_input_energy_j": (
                float(v14c["active_input_energy_j"]) if v14c else None
            ),
        },
        "fixed_motor_baseline": {
            "Kt": PRESETS["mx64ar"].Kt,
            "J_rotor": PRESETS["mx64ar"].J_rotor,
            "N": PRESETS["mx64ar"].N,
            "eta": PRESETS["mx64ar"].eta,
            "I_max": PRESETS["mx64ar"].I_max,
            "joint_J_eff": PRESETS["mx64ar"].joint_J_eff(),
            "joint_b_eff": PRESETS["mx64ar"].joint_b_eff(),
            "joint_tau_sat_peak": PRESETS["mx64ar"].joint_tau_sat_peak(),
            "joint_tau_C_eff_at_baseline_tauC": PRESETS["mx64ar"].joint_tau_C_eff(),
        },
        "rows": rows,
        "critical_band_joint_tau_C_Nm": [critical_lower, critical_upper],
        "verdict": verdict,
    }
    out = OUT_DIR / "scan_v16_tauC_critical.json"
    out.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(table, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

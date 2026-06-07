"""V13.7 τ_C 扫描验证：证明前馈摩擦补偿消除 V16 发现的非单调失败带。

与 V16 scan_v16_tauC_critical.py 相同网格，每点双跑（补偿开/关），
输出对比表证明失败带 [0.013, 0.201] N·m 在补偿后消除。
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

from common.motor_dynamics import PRESETS, MotorParams  # noqa: E402

ARM_MASS = 0.01
FOOT_RADIUS = 0.042
LEG_SCALE = 1.02
DURATION = 12.0

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


def make_params(motor: MotorParams, compensate: bool) -> V137Params:
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
    return V137Params(
        base=base,
        fsm=make_v137_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=compensate,
    )


def run_one(tau_C_motor: float, compensate: bool) -> dict:
    motor = make_motor(tau_C_motor)
    comp_tag = "comp" if compensate else "nocomp"
    prefix = f"v13_7_tauC_scan_{comp_tag}_tc{int(tau_C_motor*1e6):04d}"
    _, summary = run_simulation_v137(
        make_params(motor, compensate), save_prefix=prefix, sample_hz=160.0
    )
    return {
        "tau_C_motor_Nm": tau_C_motor,
        "tau_C_eff_joint_Nm": motor.joint_tau_C_eff(),
        "compensate_friction": compensate,
        "success": bool(summary["success"]),
        "alt_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "active_input_energy_elec_j": float(summary["active_input_energy_elec_j"]),
        "coulomb_friction_dissipation_j": float(
            summary["coulomb_friction_dissipation_j"]
        ),
        "failure": str(summary["failure"]),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows_comp = []
    rows_nocomp = []

    for tau_C_motor in TAU_C_MOTOR_GRID:
        rows_comp.append(run_one(tau_C_motor, compensate=True))
        rows_nocomp.append(run_one(tau_C_motor, compensate=False))

    comp_successes = sum(1 for r in rows_comp if r["success"])
    nocomp_successes = sum(1 for r in rows_nocomp if r["success"])

    v16_fail_band = [r for r in rows_nocomp if not r["success"]]
    v16_fail_band_fixed = [
        r_c
        for r_c, r_n in zip(rows_comp, rows_nocomp)
        if not r_n["success"] and r_c["success"]
    ]

    verdict = (
        "compensation_eliminates_fail_band"
        if comp_successes == len(TAU_C_MOTOR_GRID)
        else "partial_recovery"
    )

    result = {
        "sweep_grid_tau_C_motor_Nm": TAU_C_MOTOR_GRID,
        "compensated_rows": rows_comp,
        "uncompensated_rows": rows_nocomp,
        "summary": {
            "compensated_success_count": comp_successes,
            "uncompensated_success_count": nocomp_successes,
            "total_points": len(TAU_C_MOTOR_GRID),
            "fail_band_points_fixed": len(v16_fail_band_fixed),
            "fail_band_points_total": len(v16_fail_band),
        },
        "verdict": verdict,
    }

    out_path = OUT_DIR / "scan_v13_7_tauC_verify.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*60}")
    print("V13.7 τ_C 扫描验证结果")
    print(f"{'='*60}")
    print(f"补偿开: {comp_successes}/{len(TAU_C_MOTOR_GRID)} 通过")
    print(f"补偿关: {nocomp_successes}/{len(TAU_C_MOTOR_GRID)} 通过")
    print(f"失败带修复: {len(v16_fail_band_fixed)}/{len(v16_fail_band)} 点恢复")
    print(f"Verdict: {verdict}")
    print(f"{'='*60}\n")

    print(f"{'tau_C_eff (Nm)':<16} {'无补偿':<10} {'有补偿':<10} {'修复?':<6}")
    print("-" * 42)
    for r_c, r_n in zip(rows_comp, rows_nocomp):
        fixed = "Y" if (not r_n["success"] and r_c["success"]) else ""
        print(
            f"{r_c['tau_C_eff_joint_Nm']:<16.4f} {'PASS' if r_n['success'] else 'FAIL':<10} {'PASS' if r_c['success'] else 'FAIL':<10} {fixed:<6}"
        )


if __name__ == "__main__":
    main()

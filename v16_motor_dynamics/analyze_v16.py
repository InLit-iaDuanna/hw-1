"""分析 V16 结果，产出 verdict + CoT + Floquet 报告。

读取 smoke_v16_table.json + scan_v16_tauC_critical.json，写出 v16_verdict.json
（含 four-branch verdict 推理链 + V22 选型约束）+ CoT_mech vs CoT_elec 对照。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(HW1_ROOT))

from common.energy_metrics import cost_of_transport  # noqa: E402

OUT_DIR = ROOT / "out"


def main() -> None:
    smoke = json.loads((OUT_DIR / "smoke_v16_table.json").read_text(encoding="utf-8"))
    scan = json.loads(
        (OUT_DIR / "scan_v16_tauC_critical.json").read_text(encoding="utf-8")
    )

    smoke_rows = {r["tag"]: r for r in smoke["rows"]}
    v14c_ref = smoke["v14c_reference"]

    cot_table = []
    for tag, r in smoke_rows.items():
        mass_eff = 5.6
        cot_mech = cost_of_transport(
            r["active_input_energy_mech_j"], mass_eff, max(r["forward_distance"], 1e-6)
        )
        cot_elec = cost_of_transport(
            r["active_input_energy_elec_j"], mass_eff, max(r["forward_distance"], 1e-6)
        )
        cot_table.append(
            {
                "tag": tag,
                "success": r["success"],
                "forward_m": r["forward_distance"],
                "active_mech_j": r["active_input_energy_mech_j"],
                "active_elec_j": r["active_input_energy_elec_j"],
                "CoT_mech": cot_mech,
                "CoT_elec": cot_elec,
                "elec_to_mech_ratio": (
                    (r["active_input_energy_elec_j"] / r["active_input_energy_mech_j"])
                    if r["active_input_energy_mech_j"] > 1e-6
                    else None
                ),
            }
        )

    success_band = [r for r in scan["rows"] if r["success"]]
    fail_band = [r for r in scan["rows"] if not r["success"]]
    success_tau_C = [r["tau_C_eff_joint_Nm"] for r in success_band]
    fail_tau_C = [r["tau_C_eff_joint_Nm"] for r in fail_band]

    is_monotonic = True
    seen_fail = False
    for r in scan["rows"]:
        if not r["success"]:
            seen_fail = True
        elif seen_fail:
            is_monotonic = False
            break

    if smoke["smoke_verdict"] == "v16_implementation_bug":
        primary = "v16_implementation_bug"
    elif smoke["smoke_verdict"] == "passed":
        primary = "motor_dynamics_compatible"
    elif not is_monotonic:
        primary = "motor_dynamics_breaks_fsm_revisit_control"
        sub_finding = "tau_C_FSM_resonant_coupling_non_monotonic"
    else:
        primary = "motor_dynamics_breaks_fsm_revisit_control"
        sub_finding = "tau_C_monotonic_threshold"

    mx64_spec_tauC = scan["fixed_motor_baseline"]["joint_tau_C_eff_at_baseline_tauC"]
    mx64_falls_in_fail_band = any(
        abs(t - mx64_spec_tauC) < 1e-3 for t in fail_tau_C
    ) or any(fail_tau_C and (min(fail_tau_C) <= mx64_spec_tauC <= max(fail_tau_C)))

    verdict = {
        "primary_verdict": primary,
        "sub_finding": sub_finding if "sub_finding" in dir() else None,
        "smoke_verdict": smoke["smoke_verdict"],
        "ideal_l0_pass": smoke["ideal_vs_v14c"]["passes_l0_threshold"],
        "mx64ar_full_l1_pass": smoke["mx64ar_full_vs_v14c"]["passes_l1_threshold"],
        "tau_C_scan": {
            "is_monotonic": is_monotonic,
            "success_tau_C_eff_joint_Nm": success_tau_C,
            "fail_tau_C_eff_joint_Nm": fail_tau_C,
            "critical_band_joint_tau_C_Nm": scan["critical_band_joint_tau_C_Nm"],
            "non_monotonic_recovery_pockets": [
                r["tau_C_eff_joint_Nm"]
                for r in success_band
                if r["tau_C_eff_joint_Nm"] > 0
            ],
        },
        "mx64ar_at_spec_tau_C_eff_joint_Nm": mx64_spec_tauC,
        "mx64ar_falls_in_fail_band": mx64_falls_in_fail_band,
        "v22_selection_constraint": (
            "MX-64AR 在 spec τ_C_eff=0.20 N·m 时落入 V13.6.1 FSM 失败带；非单调恢复带 "
            "(0, 0.034) 与 (0.27, ∞) 存在但与 spec 不重合。V22 选型必须：(a) 选 τ_C_eff < 0.013 N·m "
            "的低摩擦关节模组（背靠背双 BLDC + 谐波减速器），或 (b) V13.7 引入摩擦补偿项 "
            "τ_compensation = τ_C_eff·sign_smooth(ω_des) 让 FSM 在 spec τ_C 下恢复工作。"
            "(c) 不可仅按上界保证选型，必须 FSM 实测。"
        ),
        "cot_table_mass_eff_5.6kg": cot_table,
        "next_steps": [
            "V13.7 摩擦补偿增量版本：在 control_v136 hip 输出端加 τ_C_compensation = τ_C_eff·sign_smooth(ω)，"
            "重跑 mx64ar_full smoke 验证是否恢复 (>5pct 偏差或 alt_td=10)。",
            "若 V13.7 通过，V16 verdict 升级为 motor_dynamics_compatible_with_friction_compensation。",
            "若 V13.7 仍失败，验证 V14c 决策门 §2 假设 'V13.6.1 FSM 是 (kp,kd) 孤立点解' 在真实摩擦下"
            "崩溃，回到 V13.6.1 phase grid search 在含真实 τ_C 的 motor_dynamics 在线下重扫。",
        ],
    }

    if "sub_finding" not in dir():
        verdict.pop("sub_finding")

    out = OUT_DIR / "v16_verdict.json"
    out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

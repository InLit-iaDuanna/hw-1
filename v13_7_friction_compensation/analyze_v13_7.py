"""V13.7 analyze：汇总 smoke 结果，产出 verdict + 与 V16 的对比结论。

读取 smoke_v13_7_table.json，写出 v13_7_verdict.json。
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
V16_VERDICT = HW1_ROOT / "v16_motor_dynamics" / "out" / "v16_verdict.json"


def main() -> None:
    smoke = json.loads((OUT_DIR / "smoke_v13_7_table.json").read_text(encoding="utf-8"))
    v16_verdict = (
        json.loads(V16_VERDICT.read_text(encoding="utf-8"))
        if V16_VERDICT.exists()
        else None
    )

    rows_by_tag = {r["tag"]: r for r in smoke["rows"]}
    mass_eff = 5.6

    cot_table = []
    for r in smoke["rows"]:
        fwd = max(r["forward_distance"], 1e-6)
        cot_mech = cost_of_transport(r["active_input_energy_mech_j"], mass_eff, fwd)
        cot_elec = cost_of_transport(r["active_input_energy_elec_j"], mass_eff, fwd)
        cot_table.append(
            {
                "tag": r["tag"],
                "success": r["success"],
                "forward_m": r["forward_distance"],
                "CoT_mech": cot_mech,
                "CoT_elec": cot_elec,
                "coulomb_dissipation_j": r["coulomb_friction_dissipation_j"],
            }
        )

    comp = rows_by_tag.get("compensated_mx64ar", {})
    no_comp = rows_by_tag.get("no_comp_mx64ar", {})

    if smoke["smoke_verdict"] == "v13_7_implementation_bug":
        primary = "v13_7_implementation_bug"
        upgrade_v16 = False
    elif smoke["smoke_verdict"] == "friction_compensation_full_recovery":
        primary = "friction_compensation_validated"
        upgrade_v16 = True
    elif smoke["smoke_verdict"] == "friction_compensation_partial_recovery":
        primary = "friction_compensation_partial"
        upgrade_v16 = True
    else:
        primary = "friction_compensation_failed"
        upgrade_v16 = False

    verdict = {
        "primary_verdict": primary,
        "smoke_verdict": smoke["smoke_verdict"],
        "compensated_mx64ar": {
            "success": comp.get("success"),
            "alt_touchdowns": comp.get("alt_touchdowns"),
            "forward_distance": comp.get("forward_distance"),
            "failure": comp.get("failure"),
        },
        "no_comp_mx64ar": {
            "success": no_comp.get("success"),
            "failure": no_comp.get("failure"),
        },
        "v16_verdict_upgrade": upgrade_v16,
        "v16_original_verdict": v16_verdict["primary_verdict"] if v16_verdict else None,
        "v16_new_verdict": (
            "motor_dynamics_compatible_with_friction_compensation"
            if upgrade_v16
            else v16_verdict["primary_verdict"] if v16_verdict else None
        ),
        "cot_table_mass_eff_5.6kg": cot_table,
        "v22_implication": (
            "mx64ar 可用（需前馈摩擦补偿），V17 状态估计前提恢复"
            if upgrade_v16
            else "mx64ar 仍不可用，需换低摩擦电机或重新设计 FSM"
        ),
        "next_steps": [],
    }

    if upgrade_v16:
        verdict["next_steps"] = [
            "V16 verdict 升级为 motor_dynamics_compatible_with_friction_compensation",
            "V17 状态估计前提恢复，可启动 V17",
            "V15.2 strict SEA + V13.7 补偿协同版可考虑",
        ]
    else:
        verdict["next_steps"] = [
            "V13.6.1 FSM 在真实摩擦下不可恢复",
            "需回到 V13.6.1 phase grid search 在含 motor_dynamics 的模型上重扫",
            "或换 τ_C_eff < 0.013 的低摩擦关节模组",
        ]

    out = OUT_DIR / "v13_7_verdict.json"
    out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

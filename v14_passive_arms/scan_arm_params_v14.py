"""V14 摆臂参数扫描：在 V10 baseline 控制律下扫 (arm_mass, arm_length)
两个核心轴，固定 arm_damping=0.02、arm_stiffness=0。

科学问题：被动摆臂作为机构扰动，能否落入 V10 (kp,kd) 孤立点的稳定盆地？
失败如实记录（V13 决策门已预警）。
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from itertools import product

from simulate_passive_arms_v14 import OUT_DIR, PassiveArmsParams, run_simulation

ARM_MASS = [0.001, 0.05, 0.10, 0.20, 0.30, 0.45, 0.60]  # kg
ARM_LENGTH = [0.20, 0.30, 0.40, 0.50, 0.60]  # m


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    best = None
    for am, al in product(ARM_MASS, ARM_LENGTH):
        params = PassiveArmsParams(arm_mass=am, arm_length=al, duration=12.0)
        _, summary = run_simulation(params, sample_hz=20.0)
        flat = {
            "arm_mass": am,
            "arm_length": al,
            "arm_damping": params.arm_damping,
            "arm_stiffness": params.arm_stiffness,
            "total_mass_kg": summary["total_mass_kg"],
            "score": summary["score"],
            "success": summary["success"],
            "alternating_touchdowns": summary["alternating_touchdowns"],
            "forward_distance": summary["forward_distance"],
            "simulated_time": summary["simulated_time"],
            "failure": summary["failure"],
            "active_input_energy_j": summary["active_input_energy_j"],
            "energy_per_alternation_j": summary["energy_per_alternation_j"],
        }
        rows.append(flat)
        marker = "OK" if summary["success"] else summary["failure"]
        print(
            f"  arm_mass={am:.3f} arm_length={al:.2f} -> {marker}  alt={summary['alternating_touchdowns']}  fwd={summary['forward_distance']:.2f}"
        )
        if best is None or summary["score"] > best[1]["score"]:
            best = (params, summary)

    csv_path = OUT_DIR / "v14_arm_scan.csv"
    rows.sort(key=lambda r: r["score"], reverse=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    success = [r for r in rows if r["success"]]
    summary_idx = {
        "n_total": len(rows),
        "n_success": len(success),
        "success_rate": len(success) / len(rows),
        "best_arm_mass": rows[0]["arm_mass"],
        "best_arm_length": rows[0]["arm_length"],
        "best_score": rows[0]["score"],
        "scan_axes": {"arm_mass": ARM_MASS, "arm_length": ARM_LENGTH},
        "control_law_inherits": "V10 best (hip_kp=30 hip_kd=6 gait_period=0.80)",
        "decision_gate_note": "V13 标记 V10 控制律为 (kp,kd) 孤立点解；本扫描即测试机构扰动能否保留稳定。",
    }
    (OUT_DIR / "v14_arm_scan_summary.json").write_text(
        json.dumps(summary_idx, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if best is not None:
        bp, _ = best
        _, bs = run_simulation(bp, save_prefix="v14_baseline", sample_hz=160.0)
        bs["params"] = asdict(bp)
        (OUT_DIR / "v14_best_params.json").write_text(
            json.dumps(bs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(OUT_DIR / "v14_best_params.json")
    print(csv_path)
    print(f"success: {len(success)}/{len(rows)} = {len(success)/len(rows):.1%}")


if __name__ == "__main__":
    main()

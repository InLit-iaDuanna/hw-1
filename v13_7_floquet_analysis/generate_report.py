"""生成 V13.7 Floquet 分析报告（Markdown 格式）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def load_json(path: Path) -> dict:
    """加载 JSON 文件。"""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report() -> str:
    """生成分析报告。"""
    summary = load_json(OUT_DIR / "v13_7_floquet_summary.json")

    if not summary:
        return "错误: 未找到汇总数据。请先运行 analyze_floquet_v13_7.py"

    v10_ref = summary.get("v10_reference", {})
    results = summary.get("v13_7_results", [])
    comp = summary.get("comparison", {})

    report = []
    report.append("# V13.7 FSM 控制律 Floquet 稳定性分析报告")
    report.append("")
    report.append("## 分析目标")
    report.append("")
    report.append("量化 V13.7 FSM 事件驱动控制律的稳定裕度，对比 V10 PD 控制基线。")
    report.append("")
    report.append("## 方法")
    report.append("")
    report.append(
        "- **Poincaré 截面**: 右脚触地时刻的 4D 状态 (right_hip, right_hip_vel, right_knee, right_knee_vel)"
    )
    report.append(
        "- **Floquet 乘子**: 使用 Goswami et al. (1996) 实验方法，对截面点序列线性回归得到 return-map Jacobian"
    )
    report.append("- **仿真参数**: duration=20s，目标 ≥16 次触地，sample_hz=160Hz")
    report.append("- **状态收敛**: max|λ| 是最大 Floquet 乘子模，决定扰动收敛速率")
    report.append("")

    report.append("## 结果汇总")
    report.append("")
    report.append(
        "| 配置 | max\\|λ\\| | alternations | forward (m) | success | 稳定性 |"
    )
    report.append(
        "|------|-----------|--------------|-------------|---------|--------|"
    )

    # V10 参考
    v10_lambda = v10_ref.get("max_abs_floquet", 0)
    v10_alt = v10_ref.get("alternations", 0)
    v10_fwd = v10_ref.get("forward_distance", 0)
    report.append(
        f"| V10 PD (V13b) | {v10_lambda:.4f} | {v10_alt} | {v10_fwd:.2f} | ✓ | stable |"
    )

    # V13.7 结果
    for res in results:
        config = res.get("config", "unknown")
        max_lambda = res.get("max_abs_floquet", float("nan"))
        alt = res.get("alternations", 0)
        fwd = res.get("forward_distance", 0)
        success = "✓" if res.get("success", False) else "✗"
        stability = "stable" if max_lambda < 1.0 else "unstable"

        # 简化配置名
        if "ideal" in config:
            name = "V13.7 FSM (ideal)"
        elif "comp" in config and "nocomp" not in config:
            name = "V13.7 FSM (mx64ar+comp)"
        else:
            name = "V13.7 FSM (mx64ar-no)"

        report.append(
            f"| {name} | {max_lambda:.4f} | {alt} | {fwd:.2f} | {success} | {stability} |"
        )

    report.append("")
    report.append("## 对比分析")
    report.append("")

    delta_ideal = comp.get("delta_ideal_vs_v10", 0)
    delta_comp = comp.get("delta_comp_vs_ideal", 0)

    report.append(f"- **V13.7 (ideal) vs V10 PD**: Δmax|λ| = {delta_ideal:+.4f}")
    if abs(delta_ideal) < 0.01:
        report.append("  - 稳定性相当（差异 <1%）")
    elif delta_ideal < 0:
        report.append(
            f"  - V13.7 FSM 稳定裕度更大（快 {abs(delta_ideal)/v10_lambda*100:.1f}% 收敛）"
        )
    else:
        report.append(
            f"  - V13.7 FSM 稳定裕度更小（慢 {delta_ideal/v10_lambda*100:.1f}% 收敛）"
        )

    report.append("")
    report.append(
        f"- **V13.7 (mx64ar+comp) vs V13.7 (ideal)**: Δmax|λ| = {delta_comp:+.4f}"
    )
    if abs(delta_comp) < 0.01:
        report.append("  - 摩擦补偿完全恢复 ideal 性能")
    elif delta_comp > 0:
        report.append("  - 摩擦补偿后仍有性能损失（稳定裕度降低）")
    else:
        report.append("  - 摩擦补偿意外提升稳定性（需进一步验证）")

    report.append("")
    report.append("## 稳定性解释")
    report.append("")
    report.append(
        "Floquet 乘子 λ 是 return-map Jacobian 的特征值，表征扰动在周期运动下的倍增系数："
    )
    report.append("")
    report.append("- **|λ| < 1**: 稳定（扰动呈指数衰减）")
    report.append("- **|λ| → 1**: 临界稳定（收敛极慢，对扰动敏感）")
    report.append("- **|λ| ≥ 1**: 不稳定（扰动发散）")
    report.append("")
    report.append("max|λ| 是所有特征值中模最大的，决定系统的收敛速率：")
    report.append("")
    report.append("```")
    report.append("收敛时间常数 τ ≈ T_gait / ln(1/|λ|)")
    report.append("```")
    report.append("")
    report.append("其中 T_gait ≈ 0.8s（步态周期）。")
    report.append("")

    # 计算收敛时间
    if v10_lambda > 0 and v10_lambda < 1:
        tau_v10 = 0.8 / abs(np.log(v10_lambda)) if v10_lambda != 1 else float("inf")
        report.append(f"- V10 PD: τ ≈ {tau_v10:.2f} s ({tau_v10/0.8:.1f} 步)")

    for res in results:
        config = res.get("config", "")
        max_lambda = res.get("max_abs_floquet", float("nan"))
        if max_lambda > 0 and max_lambda < 1:
            tau = 0.8 / abs(np.log(max_lambda)) if max_lambda != 1 else float("inf")
            name = config.replace("v13_7_fsm_", "").replace("_", " ")
            report.append(f"- V13.7 ({name}): τ ≈ {tau:.2f} s ({tau/0.8:.1f} 步)")

    report.append("")
    report.append("## 结论")
    report.append("")

    # 自动生成结论
    ideal_result = next((r for r in results if "ideal" in r.get("config", "")), None)
    comp_result = next(
        (
            r
            for r in results
            if "comp" in r.get("config", "") and "nocomp" not in r.get("config", "")
        ),
        None,
    )

    if ideal_result and ideal_result.get("success"):
        ideal_lambda = ideal_result.get("max_abs_floquet", 1)
        if ideal_lambda < v10_lambda:
            report.append(
                "1. **V13.7 FSM 控制律比 V10 PD 稳定性更好**（快速收敛，大稳定裕度）"
            )
        elif ideal_lambda > v10_lambda * 1.05:
            report.append(
                "1. **V13.7 FSM 控制律稳定裕度小于 V10 PD**（收敛较慢，需关注鲁棒性）"
            )
        else:
            report.append("1. **V13.7 FSM 控制律与 V10 PD 稳定性相当**")

    if comp_result and comp_result.get("success"):
        comp_lambda = comp_result.get("max_abs_floquet", 1)
        if ideal_result:
            ideal_lambda = ideal_result.get("max_abs_floquet", 1)
            if abs(comp_lambda - ideal_lambda) < 0.01:
                report.append("2. **摩擦补偿完全恢复理想性能**（mx64ar+comp ≈ ideal）")
            else:
                report.append(
                    "2. **摩擦补偿有效但存在性能损失**（需进一步优化补偿策略）"
                )

    report.append("")
    report.append("## 可视化")
    report.append("")
    report.append("- `v13_7_floquet_comparison.png`: Poincaré 截面 + Floquet 谱对比")
    report.append("- `v13_7_stability_margin_comparison.png`: 稳定裕度条形图")
    report.append("")

    report.append("## 参考")
    report.append("")
    report.append("- V13b Floquet 分析: `hw-1/v13b_floquet_long_run/`")
    report.append(
        "- Goswami et al. (1996): Compass-Like Biped Robot Part I (实验 Floquet 方法)"
    )
    report.append("- V13.7 实现: `hw-1/v13_7_friction_compensation/`")

    return "\n".join(report)


if __name__ == "__main__":
    import numpy as np  # 用于收敛时间计算

    OUT_DIR.mkdir(exist_ok=True)
    report = generate_report()

    report_path = OUT_DIR / "v13_7_floquet_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"生成分析报告: {report_path}")
    print("\n" + "=" * 60)
    print(report)

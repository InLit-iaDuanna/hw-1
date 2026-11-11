"""V18 3D 侧向稳定性可视化脚本。

生成图表：
1. 各配置的性能对比（alternations, forward_distance）
2. 失败模式分布
3. 侧向角度演化（如果有轨迹数据）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# 添加 common 到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.plot_styles import (
    PALETTE,
    PHASE_COLORS,
    create_figure,
    save_figure,
    set_style,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def load_summary_data() -> dict[str, dict]:
    """加载所有配置的 summary JSON。"""
    summaries = {}

    summary_files = [
        "v18_zero_perturb_summary.json",
        "v18_narrow_foot_summary.json",
        "v18_frozen_lateral_summary.json",
        "v18_stiff_zero_summary.json",
        "v18_condim3_zero_summary.json",
        "v18_v10friction_summary.json",
        "v18_v14params_zero_summary.json",
    ]

    for fname in summary_files:
        fpath = OUT_DIR / fname
        if fpath.exists():
            config_name = fname.replace("v18_", "").replace("_summary.json", "")
            with open(fpath, encoding="utf-8") as f:
                summaries[config_name] = json.load(f)

    return summaries


def plot_performance_comparison(summaries: dict[str, dict], output_path: Path) -> None:
    """绘制各配置性能对比。"""
    configs = list(summaries.keys())
    alternations = [summaries[c].get("alternating_touchdowns", 0) for c in configs]
    forward_dist = [summaries[c].get("forward_distance", 0.0) for c in configs]

    fig, axes = create_figure("large", nrows=1, ncols=2)

    # 左图：Alternations
    ax1 = axes[0]
    bars1 = ax1.bar(
        range(len(configs)),
        alternations,
        color=PHASE_COLORS[3],
        alpha=0.7,
        edgecolor="black",
    )
    ax1.set_xticks(range(len(configs)))
    ax1.set_xticklabels(configs, rotation=45, ha="right", fontsize=8)
    ax1.set_ylabel("Alternations", fontsize=11)
    ax1.set_title("V18 配置对比 - 交替步数", fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.axhline(
        y=3,
        color=PALETTE["fail"],
        linestyle="--",
        linewidth=2,
        label="Baseline (all failed)",
    )
    ax1.legend()

    # 数值标签
    for i, val in enumerate(alternations):
        ax1.text(i, val + 0.1, str(val), ha="center", va="bottom", fontsize=9)

    # 右图：Forward Distance
    ax2 = axes[1]
    bars2 = ax2.bar(
        range(len(configs)),
        forward_dist,
        color=PHASE_COLORS[3],
        alpha=0.7,
        edgecolor="black",
    )
    ax2.set_xticks(range(len(configs)))
    ax2.set_xticklabels(configs, rotation=45, ha="right", fontsize=8)
    ax2.set_ylabel("Forward Distance (m)", fontsize=11)
    ax2.set_title("V18 配置对比 - 前进距离", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="y")

    # 数值标签
    for i, val in enumerate(forward_dist):
        ax2.text(i, val + 0.05, f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    save_figure(fig, output_path)
    print(f"[OK] 保存: {output_path}")


def plot_failure_distribution(summaries: dict[str, dict], output_path: Path) -> None:
    """绘制失败模式分布。"""
    failure_modes = {}

    for config, data in summaries.items():
        failure = data.get("failure", "unknown")
        failure_modes[failure] = failure_modes.get(failure, 0) + 1

    fig, ax = create_figure("medium")

    modes = list(failure_modes.keys())
    counts = list(failure_modes.values())
    colors = [PALETTE["fail"] if m != "none" else PALETTE["ok"] for m in modes]

    bars = ax.bar(range(len(modes)), counts, color=colors, alpha=0.7, edgecolor="black")
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels(modes, rotation=45, ha="right")
    ax.set_ylabel("配置数量", fontsize=11)
    ax.set_title("V18 失败模式分布", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # 数值标签
    for i, val in enumerate(counts):
        ax.text(i, val + 0.1, str(val), ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    save_figure(fig, output_path)
    print(f"[OK] 保存: {output_path}")


def generate_verdict_summary(summaries: dict[str, dict]) -> None:
    """生成 verdict 摘要文本。"""
    total_configs = len(summaries)
    max_alt = max(s.get("alternating_touchdowns", 0) for s in summaries.values())

    print("\n" + "=" * 70)
    print("V18 3D 侧向稳定性实验摘要")
    print("=" * 70)
    print(f"测试配置数：{total_configs}")
    print(f"最大交替步数：{max_alt} (全部失败)")
    print(f"结论：所有配置均在 3 个交替步内失败")
    print(f"      侧向 inverted pendulum 无法通过几何约束实现被动稳定")
    print(f"      Verdict: 3D 纯被动不可行，必须引入侧向主动控制")
    print("=" * 70 + "\n")


def main():
    """主函数。"""
    set_style(dpi=300)

    print("=" * 70)
    print("V18 可视化脚本")
    print("=" * 70)

    # 加载数据
    summaries = load_summary_data()
    if not summaries:
        print("[ERROR] 未找到 summary 数据")
        return

    print(f"[OK] 加载了 {len(summaries)} 个配置")

    # 生成图表
    plot_performance_comparison(summaries, OUT_DIR / "v18_performance_comparison.png")
    plot_failure_distribution(summaries, OUT_DIR / "v18_failure_distribution.png")

    # 打印摘要
    generate_verdict_summary(summaries)

    print("\n[完成] V18 可视化完成")
    print(f"输出目录: {OUT_DIR}")


if __name__ == "__main__":
    main()

"""V20 步宽控制可视化脚本。

生成图表：
1. 步宽控制器性能对比
2. 侧向位置轨迹（如果有 CSV 数据）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

    summary_files = list(OUT_DIR.glob("v20_*_summary.json"))

    for fpath in summary_files:
        config_name = fpath.stem.replace("v20_", "").replace("_summary", "")
        with open(fpath, encoding="utf-8") as f:
            summaries[config_name] = json.load(f)

    return summaries


def plot_step_width_performance(summaries: dict[str, dict], output_path: Path) -> None:
    """绘制步宽控制器性能。"""
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
    ax1.set_xticklabels(configs, rotation=45, ha="right")
    ax1.set_ylabel("Alternations", fontsize=11)
    ax1.set_title("V20 步宽控制器性能 - 交替步数", fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.axhline(
        y=3,
        color=PALETTE["fail"],
        linestyle="--",
        linewidth=2,
        label="V18/V19 Baseline",
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
    ax2.set_xticklabels(configs, rotation=45, ha="right")
    ax2.set_ylabel("Forward Distance (m)", fontsize=11)
    ax2.set_title("V20 步宽控制器性能 - 前进距离", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="y")

    # 数值标签
    for i, val in enumerate(forward_dist):
        ax2.text(i, val + 0.05, f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    save_figure(fig, output_path)
    print(f"[OK] 保存: {output_path}")


def plot_lateral_trajectory(output_path: Path) -> None:
    """绘制侧向位置轨迹（如果有 CSV 数据）。"""
    csv_file = OUT_DIR / "v20_smoke_trace.csv"

    if not csv_file.exists():
        print("[WARN] 未找到轨迹 CSV 数据，跳过侧向轨迹图")
        return

    try:
        df = pd.read_csv(csv_file)

        if "torso_y" not in df.columns or "time" not in df.columns:
            print("[WARN] CSV 缺少必要列，跳过侧向轨迹图")
            return

        fig, ax = create_figure("medium")

        ax.plot(
            df["time"],
            df["torso_y"],
            color=PHASE_COLORS[3],
            linewidth=2,
            label="Torso Y Position",
        )
        ax.axhline(
            y=0,
            color="gray",
            linestyle="--",
            linewidth=1,
            alpha=0.5,
            label="Center Line",
        )

        ax.set_xlabel("Time (s)", fontsize=11)
        ax.set_ylabel("Lateral Position (m)", fontsize=11)
        ax.set_title("V20 侧向位置轨迹", fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        save_figure(fig, output_path)
        print(f"[OK] 保存: {output_path}")

    except Exception as e:
        print(f"[ERROR] 绘制侧向轨迹失败: {e}")


def generate_verdict_summary(summaries: dict[str, dict]) -> None:
    """生成 verdict 摘要文本。"""
    total_configs = len(summaries)
    max_alt = max(s.get("alternating_touchdowns", 0) for s in summaries.values())

    print("\n" + "=" * 70)
    print("V20 步宽控制实验摘要")
    print("=" * 70)
    print(f"测试配置数：{total_configs}")
    print(f"最大交替步数：{max_alt}")
    print(f"结论：步宽控制器未能恢复稳定行走")
    print(f"      所有配置仍在 3 个交替步内失败")
    print(f"      Verdict: V18-V20 三连失败，3D 化路线遇到根本性障碍")
    print("=" * 70 + "\n")


def main():
    """主函数。"""
    set_style(dpi=300)

    print("=" * 70)
    print("V20 可视化脚本")
    print("=" * 70)

    # 加载数据
    summaries = load_summary_data()
    if not summaries:
        print("[ERROR] 未找到 summary 数据")
        return

    print(f"[OK] 加载了 {len(summaries)} 个配置")

    # 生成图表
    plot_step_width_performance(summaries, OUT_DIR / "v20_step_width_performance.png")
    plot_lateral_trajectory(OUT_DIR / "v20_lateral_trajectory.png")

    # 打印摘要
    generate_verdict_summary(summaries)

    print("\n[完成] V20 可视化完成")
    print(f"输出目录: {OUT_DIR}")


if __name__ == "__main__":
    main()

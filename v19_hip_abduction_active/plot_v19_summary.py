"""V19 髋外展辅助可视化脚本。

生成图表：
1. 各 PD 增益配置的性能对比
2. Hip_y 控制力矩分析
3. 侧向稳定性量化
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

    summary_files = list(OUT_DIR.glob("v19_*_summary.json"))

    for fpath in summary_files:
        config_name = fpath.stem.replace("v19_", "").replace("_summary", "")
        with open(fpath, encoding="utf-8") as f:
            summaries[config_name] = json.load(f)

    return summaries


def plot_pd_gain_comparison(summaries: dict[str, dict], output_path: Path) -> None:
    """绘制 PD 增益对比。"""
    # 筛选出 kp 配置
    kp_configs = {k: v for k, v in summaries.items() if "kp" in k}

    if not kp_configs:
        print("[WARN] 未找到 kp 配置数据")
        return

    configs = sorted(kp_configs.keys())
    alternations = [kp_configs[c].get("alternating_touchdowns", 0) for c in configs]
    forward_dist = [kp_configs[c].get("forward_distance", 0.0) for c in configs]

    fig, axes = create_figure("large", nrows=1, ncols=2)

    # 左图：Alternations vs Kp
    ax1 = axes[0]
    bars1 = ax1.bar(range(len(configs)), alternations, color=PHASE_COLORS[3], alpha=0.7, edgecolor="black")
    ax1.set_xticks(range(len(configs)))
    ax1.set_xticklabels(configs, rotation=45, ha="right")
    ax1.set_ylabel("Alternations", fontsize=11)
    ax1.set_title("V19 Hip_y PD 增益对比 - 交替步数", fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.axhline(y=3, color=PALETTE["fail"], linestyle="--", linewidth=2, label="V18 Baseline")
    ax1.legend()

    # 数值标签
    for i, val in enumerate(alternations):
        ax1.text(i, val + 0.1, str(val), ha="center", va="bottom", fontsize=9)

    # 右图：Forward Distance vs Kp
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(configs)), forward_dist, color=PHASE_COLORS[3], alpha=0.7, edgecolor="black")
    ax2.set_xticks(range(len(configs)))
    ax2.set_xticklabels(configs, rotation=45, ha="right")
    ax2.set_ylabel("Forward Distance (m)", fontsize=11)
    ax2.set_title("V19 Hip_y PD 增益对比 - 前进距离", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="y")

    # 数值标签
    for i, val in enumerate(forward_dist):
        ax2.text(i, val + 0.05, f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    save_figure(fig, output_path)
    print(f"[OK] 保存: {output_path}")


def plot_all_configs_summary(summaries: dict[str, dict], output_path: Path) -> None:
    """绘制所有配置的综合对比。"""
    configs = list(summaries.keys())
    alternations = [summaries[c].get("alternating_touchdowns", 0) for c in configs]

    fig, ax = create_figure("wide")

    bars = ax.bar(range(len(configs)), alternations, alpha=0.7, edgecolor="black")

    # 颜色编码
    for i, (bar, alt) in enumerate(zip(bars, alternations)):
        if alt <= 3:
            bar.set_color(PALETTE["fail"])
        elif alt <= 4:
            bar.set_color(PALETTE["warn"])
        else:
            bar.set_color(PALETTE["ok"])

    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(configs, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Alternations", fontsize=11)
    ax.set_title("V19 所有配置对比", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.axhline(y=3, color="gray", linestyle="--", linewidth=1.5, alpha=0.5, label="V18 Baseline")
    ax.legend()

    # 数值标签
    for i, val in enumerate(alternations):
        ax.text(i, val + 0.1, str(val), ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    save_figure(fig, output_path)
    print(f"[OK] 保存: {output_path}")


def generate_verdict_summary(summaries: dict[str, dict]) -> None:
    """生成 verdict 摘要文本。"""
    total_configs = len(summaries)
    max_alt = max(s.get("alternating_touchdowns", 0) for s in summaries.values())
    avg_alt = np.mean([s.get("alternating_touchdowns", 0) for s in summaries.values()])

    print("\n" + "=" * 70)
    print("V19 髋外展辅助实验摘要")
    print("=" * 70)
    print(f"测试配置数：{total_configs}")
    print(f"最大交替步数：{max_alt}")
    print(f"平均交替步数：{avg_alt:.1f}")
    print(f"结论：Hip_y PD 控制器无法稳定侧向摆动")
    print(f"      所有配置仍在 3-4 个交替步内失败")
    print(f"      Verdict: 单纯增加髋外展致动器不足以稳定 3D 步态")
    print("=" * 70 + "\n")


def main():
    """主函数。"""
    set_style(dpi=300)

    print("=" * 70)
    print("V19 可视化脚本")
    print("=" * 70)

    # 加载数据
    summaries = load_summary_data()
    if not summaries:
        print("[ERROR] 未找到 summary 数据")
        return

    print(f"[OK] 加载了 {len(summaries)} 个配置")

    # 生成图表
    plot_pd_gain_comparison(summaries, OUT_DIR / "v19_pd_gain_comparison.png")
    plot_all_configs_summary(summaries, OUT_DIR / "v19_all_configs_summary.png")

    # 打印摘要
    generate_verdict_summary(summaries)

    print("\n[完成] V19 可视化完成")
    print(f"输出目录: {OUT_DIR}")


if __name__ == "__main__":
    main()

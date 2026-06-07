"""跨版本性能对比工具。

读取 V01-V24 各版本的仿真结果，对比关键指标并生成趋势图。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 添加 common 到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.plot_styles import PALETTE, set_style

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)


@dataclass
class VersionMetrics:
    """版本关键指标。"""

    version: str
    forward_distance: float | None = None
    alternations: int | None = None
    cot: float | None = None
    success_rate: float | None = None
    simulated_time: float | None = None
    notes: str = ""


# 手动汇总的版本里程碑（从项目记忆和README提取）
VERSION_MILESTONES = {
    "V01": {"desc": "Compass Gait 基线", "focus": "被动步态"},
    "V02": {"desc": "Rimless Wheel", "focus": "极限环"},
    "V03": {"desc": "Compass 极限环", "focus": "稳定性验证"},
    "V04": {"desc": "膝关节步态", "focus": "摆动相膝折叠"},
    "V05": {"desc": "混合系统证明", "focus": "理论验证"},
    "V06": {"desc": "MVE 步态", "focus": "最小能耗"},
    "V07": {"desc": "真实接触探索", "focus": "MuJoCo接触模型"},
    "V08": {"desc": "准被动辅助", "focus": "髋关节控制"},
    "V09": {"desc": "稳定仿生步态", "focus": "鲁棒步态"},
    "V10": {"desc": "滚动足仿生步态", "focus": "圆弧足"},
    "V11": {"desc": "崎岖地形鲁棒性", "focus": "地形适应"},
    "V12": {"desc": "能量CoT分析", "focus": "运输成本"},
    "V13": {"desc": "参数敏感度图集", "focus": "稳定域映射"},
    "V14": {"desc": "状态机+轻量化", "focus": "FSM相位识别"},
    "V15": {"desc": "串联弹性驱动器", "focus": "SEA柔顺"},
    "V16": {"desc": "电机动力学", "focus": "真实执行器"},
    "V17": {"desc": "状态估计", "focus": "传感器噪声"},
    "V18": {"desc": "3D侧向稳定性", "focus": "3D平衡"},
    "V19": {"desc": "髋外展主动控制", "focus": "侧向步宽"},
    "V20": {"desc": "步宽控制", "focus": "3D步态调节"},
    "V21": {"desc": "3D扰动鲁棒性", "focus": "推搡恢复"},
    "V22": {"desc": "硬件设计", "focus": "物理原型"},
    "V23": {"desc": "系统辨识", "focus": "参数校准"},
    "V24": {"desc": "Sim-to-Real", "focus": "仿真到现实"},
}


def scan_version_data() -> list[VersionMetrics]:
    """扫描各版本目录，提取关键指标。"""
    metrics_list = []

    for v in range(1, 25):
        version_key = f"V{v:02d}"

        # 查找版本目录
        version_dirs = list(ROOT.glob(f"v{v:02d}_*")) + list(ROOT.glob(f"v{v}_*"))
        if not version_dirs:
            continue

        version_dir = version_dirs[0]
        out_dir = version_dir / "out"

        metrics = VersionMetrics(version=version_key)

        # 尝试读取 summary JSON（如果存在）
        summary_files = list(out_dir.glob("*summary*.json")) if out_dir.exists() else []
        if summary_files:
            try:
                with open(summary_files[0], encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        results = data.get("results", {})
                        metrics.forward_distance = results.get("forward_distance")
                        metrics.alternations = results.get(
                            "alternations"
                        ) or results.get("alternating_touchdowns")
                        metrics.cot = results.get("cot")
                        metrics.success_rate = 1.0 if results.get("success") else 0.0
                        metrics.simulated_time = results.get("simulated_time")
            except Exception:
                pass

        # 尝试读取 CSV 汇总（V13 等）
        csv_files = list(out_dir.glob("*summary*.csv")) if out_dir.exists() else []
        if csv_files and not summary_files:
            try:
                df = pd.read_csv(csv_files[0])
                if "success_rate" in df.columns:
                    metrics.success_rate = df["success_rate"].mean()
                if "cot_median" in df.columns:
                    metrics.cot = df["cot_median"].mean()
                if "n_success" in df.columns and "n_total" in df.columns:
                    metrics.success_rate = df["n_success"].sum() / df["n_total"].sum()
            except Exception:
                pass

        # 添加里程碑注释
        if version_key in VERSION_MILESTONES:
            metrics.notes = VERSION_MILESTONES[version_key]["desc"]

        metrics_list.append(metrics)

    return metrics_list


def plot_forward_distance_trend(metrics: list[VersionMetrics]) -> None:
    """绘制前向距离趋势图。"""
    versions = [m.version for m in metrics if m.forward_distance is not None]
    distances = [m.forward_distance for m in metrics if m.forward_distance is not None]

    if not versions:
        print("[WARN] 无前向距离数据")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        versions, distances, marker="o", linewidth=2, markersize=8, color=PALETTE["ok"]
    )
    ax.set_xlabel("版本", fontsize=12)
    ax.set_ylabel("前向距离 (m)", fontsize=12)
    ax.set_title("跨版本前向距离演化", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = OUT_DIR / "forward_distance_trend.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def plot_cot_trend(metrics: list[VersionMetrics]) -> None:
    """绘制CoT（运输成本）趋势图。"""
    versions = [m.version for m in metrics if m.cot is not None and not np.isnan(m.cot)]
    cots = [m.cot for m in metrics if m.cot is not None and not np.isnan(m.cot)]

    if not versions:
        print("[WARN] 无CoT数据")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [
        PALETTE["ok"] if c < 0.1 else PALETTE["warn"] if c < 0.15 else PALETTE["fail"]
        for c in cots
    ]
    ax.bar(versions, cots, color=colors, alpha=0.8)
    ax.axhline(0.1, color="gray", linestyle="--", linewidth=1, label="目标 CoT < 0.1")
    ax.set_xlabel("版本", fontsize=12)
    ax.set_ylabel("CoT (无量纲)", fontsize=12)
    ax.set_title("跨版本运输成本（Cost of Transport）", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = OUT_DIR / "cot_trend.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def plot_success_rate_trend(metrics: list[VersionMetrics]) -> None:
    """绘制成功率趋势图。"""
    versions = [m.version for m in metrics if m.success_rate is not None]
    success_rates = [
        m.success_rate * 100 for m in metrics if m.success_rate is not None
    ]

    if not versions:
        print("[WARN] 无成功率数据")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [
        PALETTE["ok"] if s > 80 else PALETTE["warn"] if s > 50 else PALETTE["fail"]
        for s in success_rates
    ]
    ax.bar(versions, success_rates, color=colors, alpha=0.8)
    ax.axhline(80, color="gray", linestyle="--", linewidth=1, label="目标成功率 > 80%")
    ax.set_xlabel("版本", fontsize=12)
    ax.set_ylabel("成功率 (%)", fontsize=12)
    ax.set_title("跨版本稳定性（成功率）", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 105)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = OUT_DIR / "success_rate_trend.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def generate_comparison_table(metrics: list[VersionMetrics]) -> None:
    """生成版本对比表格。"""
    rows = []
    for m in metrics:
        milestone = VERSION_MILESTONES.get(m.version, {})
        rows.append(
            {
                "版本": m.version,
                "描述": milestone.get("desc", ""),
                "重点": milestone.get("focus", ""),
                "前向距离(m)": (
                    f"{m.forward_distance:.2f}" if m.forward_distance else "-"
                ),
                "交替步数": str(m.alternations) if m.alternations else "-",
                "CoT": f"{m.cot:.3f}" if m.cot and not np.isnan(m.cot) else "-",
                "成功率(%)": (
                    f"{m.success_rate*100:.1f}" if m.success_rate is not None else "-"
                ),
            }
        )

    df = pd.DataFrame(rows)

    # 保存 CSV
    csv_path = OUT_DIR / "version_comparison.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 保存对比表格: {csv_path}")

    # 打印到控制台
    print("\n" + "=" * 100)
    print("版本对比表格")
    print("=" * 100)
    print(df.to_string(index=False))
    print("=" * 100 + "\n")


def plot_milestone_timeline() -> None:
    """绘制版本里程碑时间线。"""
    versions = list(VERSION_MILESTONES.keys())
    version_nums = [int(v[1:]) for v in versions]
    descs = [VERSION_MILESTONES[v]["desc"] for v in versions]

    fig, ax = plt.subplots(figsize=(14, 8))

    # 按主题分组着色
    passive_versions = list(range(1, 7))
    active_versions = list(range(7, 14))
    sea_versions = list(range(14, 18))
    three_d_versions = list(range(18, 22))
    hardware_versions = list(range(22, 25))

    colors = []
    for vn in version_nums:
        if vn in passive_versions:
            colors.append("#4a7ba7")  # 蓝色 - 被动步态
        elif vn in active_versions:
            colors.append("#2a7a3b")  # 绿色 - 主动控制
        elif vn in sea_versions:
            colors.append("#d68b00")  # 橙色 - 柔顺驱动
        elif vn in three_d_versions:
            colors.append("#8b4789")  # 紫色 - 3D扩展
        elif vn in hardware_versions:
            colors.append("#b3331b")  # 红色 - 硬件实现
        else:
            colors.append(PALETTE["neutral"])

    ax.scatter(
        version_nums,
        [1] * len(version_nums),
        s=200,
        c=colors,
        alpha=0.8,
        edgecolors="black",
        linewidth=1.5,
    )

    # 添加标签
    for i, (vn, desc) in enumerate(zip(version_nums, descs)):
        y_offset = 1.02 if i % 2 == 0 else 0.98
        va = "bottom" if i % 2 == 0 else "top"
        ax.text(
            vn,
            y_offset,
            f"V{vn:02d}\n{desc}",
            ha="center",
            va=va,
            fontsize=8,
            rotation=0,
        )

    ax.set_xlabel("版本编号", fontsize=12)
    ax.set_yticks([])
    ax.set_title("HW-1 项目版本演化时间线", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 25)
    ax.set_ylim(0.9, 1.1)
    ax.grid(True, alpha=0.2, axis="x")

    # 图例
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#4a7ba7", label="被动步态探索 (V01-V06)"),
        Patch(facecolor="#2a7a3b", label="主动控制优化 (V07-V13)"),
        Patch(facecolor="#d68b00", label="柔顺驱动器 (V14-V17)"),
        Patch(facecolor="#8b4789", label="3D扩展 (V18-V21)"),
        Patch(facecolor="#b3331b", label="硬件实现 (V22-V24)"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

    plt.tight_layout()
    out_path = OUT_DIR / "version_timeline.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存时间线: {out_path}")
    plt.close()


def main() -> None:
    """主函数。"""
    set_style()
    print("=" * 80)
    print("跨版本性能对比工具")
    print("=" * 80)

    print("\n[1/6] 扫描版本数据...")
    metrics = scan_version_data()
    print(f"    找到 {len(metrics)} 个版本")

    print("\n[2/6] 生成对比表格...")
    generate_comparison_table(metrics)

    print("\n[3/6] 绘制前向距离趋势...")
    plot_forward_distance_trend(metrics)

    print("\n[4/6] 绘制CoT趋势...")
    plot_cot_trend(metrics)

    print("\n[5/6] 绘制成功率趋势...")
    plot_success_rate_trend(metrics)

    print("\n[6/6] 绘制版本时间线...")
    plot_milestone_timeline()

    print("\n" + "=" * 80)
    print(f"[OK] 所有图表已保存到: {OUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()

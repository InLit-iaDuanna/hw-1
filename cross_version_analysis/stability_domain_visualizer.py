"""稳定域可视化工具。

对比不同版本（主要是 V13）的参数空间稳定域，2D/3D 可视化。
"""

from __future__ import annotations

import sys
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


def load_v13_slice(slice_name: str) -> pd.DataFrame | None:
    """加载 V13 参数图集切片数据。"""
    v13_dir = ROOT / "v13_parameter_sensitivity_atlas" / "out"
    csv_path = v13_dir / f"v13_{slice_name}.csv"

    if not csv_path.exists():
        print(f"[WARN] 未找到切片: {csv_path}")
        return None

    try:
        df = pd.read_csv(csv_path)
        print(f"[OK] 加载切片 {slice_name}: {len(df)} 行数据")
        return df
    except Exception as e:
        print(f"❌ 加载失败 {slice_name}: {e}")
        return None


def plot_2d_stability_domain(
    df: pd.DataFrame, x_col: str, y_col: str, title: str, filename: str
) -> None:
    """绘制 2D 稳定域热图。"""
    # 提取 x, y 轴变量名（去掉 _x / _y 后缀）
    x_key = x_col.replace("_x", "")
    y_key = y_col.replace("_y", "")

    # 获取网格数据
    x_vals = df[x_col].unique()
    y_vals = df[y_col].unique()
    x_vals.sort()
    y_vals.sort()

    grid_x = len(x_vals)
    grid_y = len(y_vals)

    # 创建成功率矩阵
    success_matrix = np.zeros((grid_y, grid_x))
    cot_matrix = np.full((grid_y, grid_x), np.nan)

    for _, row in df.iterrows():
        ix = row["ix"]
        iy = row["iy"]
        success_matrix[iy, ix] = 1.0 if row["success"] else 0.0
        if row["success"] and not np.isnan(row["cot"]):
            cot_matrix[iy, ix] = row["cot"]

    # 绘制成功域
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 左图：成功/失败二值图
    ax1 = axes[0]
    im1 = ax1.imshow(
        success_matrix,
        cmap="RdYlGn",
        aspect="auto",
        origin="lower",
        extent=[x_vals[0], x_vals[-1], y_vals[0], y_vals[-1]],
        vmin=0,
        vmax=1,
    )
    ax1.set_xlabel(x_key, fontsize=11)
    ax1.set_ylabel(y_key, fontsize=11)
    ax1.set_title(f"{title} - 成功域", fontsize=12, fontweight="bold")
    plt.colorbar(im1, ax=ax1, label="成功 (1) / 失败 (0)")

    # 标注成功点
    for _, row in df.iterrows():
        if row["success"]:
            ax1.plot(row[x_col], row[y_col], "go", markersize=6, alpha=0.6)

    # 右图：CoT 热图（仅成功点）
    ax2 = axes[1]
    im2 = ax2.imshow(
        cot_matrix,
        cmap="viridis",
        aspect="auto",
        origin="lower",
        extent=[x_vals[0], x_vals[-1], y_vals[0], y_vals[-1]],
        vmin=0.05,
        vmax=0.15,
    )
    ax2.set_xlabel(x_key, fontsize=11)
    ax2.set_ylabel(y_key, fontsize=11)
    ax2.set_title(f"{title} - CoT 分布", fontsize=12, fontweight="bold")
    plt.colorbar(im2, ax=ax2, label="CoT (运输成本)")

    plt.tight_layout()
    out_path = OUT_DIR / filename
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def plot_3d_stability_surface(
    df: pd.DataFrame, x_col: str, y_col: str, title: str, filename: str
) -> None:
    """绘制 3D 稳定域表面图。"""
    x_key = x_col.replace("_x", "")
    y_key = y_col.replace("_y", "")

    # 提取成功点的 CoT
    success_df = df[df["success"] & ~df["cot"].isna()].copy()

    if len(success_df) < 3:
        print(f"[WARN] {title} 成功点不足，跳过 3D 图")
        return

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection="3d")

    # 绘制成功点（绿色）
    x_success = success_df[x_col].values
    y_success = success_df[y_col].values
    z_success = success_df["cot"].values
    scatter = ax.scatter(
        x_success,
        y_success,
        z_success,
        c=z_success,
        cmap="viridis",
        s=100,
        alpha=0.8,
        edgecolors="black",
        linewidth=0.5,
    )

    # 绘制失败点（红色，z=0）
    fail_df = df[~df["success"]].copy()
    if len(fail_df) > 0:
        x_fail = fail_df[x_col].values
        y_fail = fail_df[y_col].values
        z_fail = np.zeros(len(fail_df))
        ax.scatter(
            x_fail, y_fail, z_fail, c=PALETTE["fail"], s=50, alpha=0.3, marker="x"
        )

    ax.set_xlabel(x_key, fontsize=11)
    ax.set_ylabel(y_key, fontsize=11)
    ax.set_zlabel("CoT", fontsize=11)
    ax.set_title(f"{title} - 3D 稳定域", fontsize=13, fontweight="bold")

    # 颜色条
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
    cbar.set_label("CoT (运输成本)", fontsize=10)

    plt.tight_layout()
    out_path = OUT_DIR / filename
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def plot_success_rate_by_slice() -> None:
    """绘制各切片的成功率对比。"""
    slices = [
        "A_slope_foot",
        "B_slope_leg",
        "C_foot_leg",
        "D_slope_torso",
        "E_hip_gains",
        "F_kp_ratio",
        "G_kp_torque",
    ]

    success_rates = []
    slice_labels = []

    for slice_name in slices:
        df = load_v13_slice(slice_name)
        if df is None:
            continue

        success_rate = df["success"].sum() / len(df) * 100
        success_rates.append(success_rate)
        slice_labels.append(slice_name.replace("_", " "))

    if not success_rates:
        print("[WARN] 无切片数据")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [
        PALETTE["ok"] if sr > 15 else PALETTE["warn"] if sr > 10 else PALETTE["fail"]
        for sr in success_rates
    ]
    bars = ax.bar(
        slice_labels,
        success_rates,
        color=colors,
        alpha=0.8,
        edgecolor="black",
        linewidth=1.2,
    )

    # 在柱子上标注数值
    for bar, sr in zip(bars, success_rates):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 1,
            f"{sr:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_ylabel("成功率 (%)", fontsize=12)
    ax.set_title(
        "V13 参数敏感度图集 - 各切片稳定性对比", fontsize=14, fontweight="bold"
    )
    ax.set_ylim(0, max(success_rates) * 1.2)
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()

    out_path = OUT_DIR / "v13_slice_success_rates.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def plot_parameter_correlation_heatmap() -> None:
    """绘制参数相关性热图（基于所有切片的汇总数据）。"""
    all_data = []

    slices = [
        "A_slope_foot",
        "B_slope_leg",
        "C_foot_leg",
        "D_slope_torso",
        "E_hip_gains",
        "F_kp_ratio",
        "G_kp_torque",
    ]

    for slice_name in slices:
        df = load_v13_slice(slice_name)
        if df is not None:
            all_data.append(df)

    if not all_data:
        print("[WARN] 无数据可用于相关性分析")
        return

    combined_df = pd.concat(all_data, ignore_index=True)

    # 选择关键数值列
    numeric_cols = [
        "slope_deg",
        "foot_radius",
        "hip_kp",
        "hip_kd",
        "cot",
        "forward_distance",
        "alternating_touchdowns",
    ]
    available_cols = [col for col in numeric_cols if col in combined_df.columns]

    if len(available_cols) < 2:
        print("[WARN] 可用数值列不足")
        return

    # 仅使用成功的样本
    success_df = combined_df[combined_df["success"]].copy()

    if len(success_df) < 10:
        print("[WARN] 成功样本不足，跳过相关性分析")
        return

    corr_matrix = success_df[available_cols].corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")

    # 设置刻度标签
    ax.set_xticks(range(len(available_cols)))
    ax.set_yticks(range(len(available_cols)))
    ax.set_xticklabels(available_cols, rotation=45, ha="right")
    ax.set_yticklabels(available_cols)

    # 在格子中标注相关系数
    for i in range(len(available_cols)):
        for j in range(len(available_cols)):
            text = ax.text(
                j,
                i,
                f"{corr_matrix.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="black",
                fontsize=9,
            )

    ax.set_title("V13 参数相关性热图（成功样本）", fontsize=14, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Pearson 相关系数")
    plt.tight_layout()

    out_path = OUT_DIR / "v13_parameter_correlation.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"[OK] 保存: {out_path}")
    plt.close()


def main() -> None:
    """主函数。"""
    set_style()
    print("=" * 80)
    print("稳定域可视化工具")
    print("=" * 80)

    # V13 关键切片
    slices_to_plot = [
        ("A_slope_foot", "slope_deg_x", "foot_radius_y", "Slope vs Foot Radius"),
        ("B_slope_leg", "slope_deg_x", "leg_scale_y", "Slope vs Leg Scale"),
        ("C_foot_leg", "foot_radius_x", "leg_scale_y", "Foot Radius vs Leg Scale"),
        ("E_hip_gains", "hip_kp_x", "hip_kd_y", "Hip Kp vs Kd"),
    ]

    print("\n[1/4] 绘制 2D 稳定域切片...")
    for slice_name, x_col, y_col, title in slices_to_plot:
        df = load_v13_slice(slice_name)
        if df is not None:
            filename = f"v13_stability_{slice_name}.png"
            plot_2d_stability_domain(df, x_col, y_col, title, filename)

    print("\n[2/4] 绘制 3D 稳定域表面...")
    for slice_name, x_col, y_col, title in slices_to_plot:
        df = load_v13_slice(slice_name)
        if df is not None:
            filename = f"v13_stability_3d_{slice_name}.png"
            plot_3d_stability_surface(df, x_col, y_col, title, filename)

    print("\n[3/4] 绘制切片成功率对比...")
    plot_success_rate_by_slice()

    print("\n[4/4] 绘制参数相关性热图...")
    plot_parameter_correlation_heatmap()

    print("\n" + "=" * 80)
    print(f"[OK] 所有图表已保存到: {OUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()

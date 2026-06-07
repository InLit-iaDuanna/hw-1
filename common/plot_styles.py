"""统一画图风格 + 中文字体 + 高级可视化工具。

版本：v2.0 (2026-06-05)
优化点：
- 统一 DPI 和字体大小
- 扩展调色板（Phase 颜色、状态颜色）
- 添加常用图表模板函数
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional

CHINESE_FONTS = ["Microsoft YaHei", "SimHei", "DengXian", "Arial Unicode MS"]

# 基础调色板
PALETTE = {
    "ok": "#2a7a3b",
    "warn": "#d68b00",
    "fail": "#b3331b",
    "neutral": "#3a3a3a",
    "left": "#0c789f",
    "right": "#b34a36",
}

# Phase 颜色（与 dashboard 一致）
PHASE_COLORS = {
    1: "#1f6feb",  # 蓝色 - Phase 1: 2D Fundamental
    2: "#238636",  # 绿色 - Phase 2: 2D Mechanical
    3: "#d97706",  # 橙色 - Phase 3: 3D Extension
    4: "#dc2626",  # 红色 - Phase 4: Hardware
}

# 状态颜色
STATUS_COLORS = {
    "done": "#34d399",      # 绿色
    "next": "#fbbf24",      # 黄色
    "planned": "#6b7a96",   # 灰色
    "failed": "#ef4444",    # 红色
}

# 图表尺寸预设
FIGURE_SIZES = {
    "small": (8, 5),
    "medium": (10, 6),
    "large": (12, 7),
    "wide": (14, 5),
    "square": (8, 8),
}

# DPI 预设
DPI_SCREEN = 110
DPI_PRINT = 300
DPI_WEB = 150


def set_style(dpi: int = DPI_PRINT, grid: bool = True) -> None:
    """设置全局绘图风格。

    Args:
        dpi: 保存 DPI（默认 300 用于论文）
        grid: 是否显示网格
    """
    matplotlib.rcParams["font.sans-serif"] = CHINESE_FONTS + matplotlib.rcParams.get(
        "font.sans-serif", []
    )
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["figure.dpi"] = DPI_SCREEN
    matplotlib.rcParams["savefig.dpi"] = dpi
    matplotlib.rcParams["axes.grid"] = grid
    matplotlib.rcParams["grid.alpha"] = 0.3
    matplotlib.rcParams["axes.labelsize"] = 11
    matplotlib.rcParams["axes.titlesize"] = 13
    matplotlib.rcParams["xtick.labelsize"] = 9
    matplotlib.rcParams["ytick.labelsize"] = 9
    matplotlib.rcParams["legend.fontsize"] = 9
    matplotlib.rcParams["figure.titlesize"] = 14


def create_figure(size: str = "medium", **kwargs) -> tuple:
    """创建标准图形。

    Args:
        size: 预设尺寸名称或 (width, height) 元组
        **kwargs: 传递给 plt.subplots 的其他参数

    Returns:
        fig, ax(es)
    """
    if isinstance(size, str):
        figsize = FIGURE_SIZES.get(size, FIGURE_SIZES["medium"])
    else:
        figsize = size

    return plt.subplots(figsize=figsize, **kwargs)


def save_figure(fig, path: str, dpi: Optional[int] = None, tight: bool = True) -> None:
    """保存图形（统一参数）。

    Args:
        fig: matplotlib 图形对象
        path: 保存路径
        dpi: 覆盖 DPI（None 则使用全局设置）
        tight: 是否使用 tight_layout
    """
    save_kwargs = {"bbox_inches": "tight"} if tight else {}
    if dpi is not None:
        save_kwargs["dpi"] = dpi

    fig.savefig(path, **save_kwargs)
    plt.close(fig)


def plot_phase_diagram(
    x: np.ndarray,
    y: np.ndarray,
    time: Optional[np.ndarray] = None,
    xlabel: str = "Position",
    ylabel: str = "Velocity",
    title: str = "Phase Diagram",
    output_path: Optional[str] = None,
    phase: Optional[int] = None,
) -> tuple:
    """绘制相位图（带时间颜色编码）。

    Args:
        x, y: 相位空间坐标
        time: 时间数组（用于颜色编码，可选）
        xlabel, ylabel, title: 图表标签
        output_path: 保存路径（None 则不保存）
        phase: Phase 编号（用于颜色主题）

    Returns:
        fig, ax
    """
    fig, ax = create_figure("medium")

    if time is not None:
        scatter = ax.scatter(x, y, c=time, cmap="viridis", s=10, alpha=0.7)
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Time (s)")
    else:
        color = PHASE_COLORS.get(phase, PALETTE["neutral"]) if phase else PALETTE["ok"]
        ax.plot(x, y, color=color, linewidth=1.5, alpha=0.8)

    # 起点和终点标记
    ax.plot(x[0], y[0], "go", markersize=10, label="Start", zorder=5)
    ax.plot(x[-1], y[-1], "r^", markersize=10, label="End", zorder=5)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    if output_path:
        save_figure(fig, output_path)

    return fig, ax


def plot_robustness_heatmap(
    success_matrix: np.ndarray,
    x_labels: list[str],
    y_labels: list[str],
    xlabel: str = "Parameter X",
    ylabel: str = "Parameter Y",
    title: str = "Robustness Heatmap",
    output_path: Optional[str] = None,
) -> tuple:
    """绘制鲁棒性热图。

    Args:
        success_matrix: 成功率矩阵 (M x N)
        x_labels, y_labels: 轴标签列表
        xlabel, ylabel, title: 图表标签
        output_path: 保存路径

    Returns:
        fig, ax
    """
    fig, ax = create_figure("square")

    im = ax.imshow(
        success_matrix,
        cmap="RdYlGn",
        aspect="auto",
        origin="lower",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )

    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticklabels(y_labels)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Success Rate")

    # 标注成功/失败
    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            text = ax.text(
                j, i, "✓" if success_matrix[i, j] > 0.5 else "✗",
                ha="center", va="center",
                color="white" if success_matrix[i, j] > 0.5 else "black",
                fontsize=12, fontweight="bold",
            )

    plt.tight_layout()

    if output_path:
        save_figure(fig, output_path)

    return fig, ax


def plot_version_comparison(
    versions: list[str],
    metrics: dict[str, list[float]],
    title: str = "Version Comparison",
    output_path: Optional[str] = None,
) -> tuple:
    """绘制版本对比柱状图。

    Args:
        versions: 版本列表
        metrics: 指标字典 {"metric_name": [values]}
        title: 图表标题
        output_path: 保存路径

    Returns:
        fig, axes
    """
    n_metrics = len(metrics)
    fig, axes = create_figure("large", nrows=(n_metrics + 1) // 2, ncols=2)
    axes = axes.flatten() if n_metrics > 1 else [axes]

    x = np.arange(len(versions))
    width = 0.6

    for idx, (metric_name, values) in enumerate(metrics.items()):
        if idx >= len(axes):
            break

        ax = axes[idx]
        bars = ax.bar(x, values, width, alpha=0.8, edgecolor="black")

        # 颜色编码（根据值大小）
        for bar, val in zip(bars, values):
            if val >= np.mean(values):
                bar.set_color(PALETTE["ok"])
            else:
                bar.set_color(PALETTE["warn"])

        ax.set_xticks(x)
        ax.set_xticklabels(versions, rotation=45, ha="right")
        ax.set_ylabel(metric_name.replace("_", " ").title())
        ax.grid(True, alpha=0.3, axis="y")

        # 数值标签
        for i, val in enumerate(values):
            ax.text(i, val, f"{val:.3f}", ha="center", va="bottom", fontsize=8)

    # 隐藏多余子图
    for idx in range(n_metrics, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    if output_path:
        save_figure(fig, output_path)

    return fig, axes


__all__ = [
    "set_style",
    "create_figure",
    "save_figure",
    "plot_phase_diagram",
    "plot_robustness_heatmap",
    "plot_version_comparison",
    "PALETTE",
    "PHASE_COLORS",
    "STATUS_COLORS",
    "FIGURE_SIZES",
    "plt",
    "np",
]

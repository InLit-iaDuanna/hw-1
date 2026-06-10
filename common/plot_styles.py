"""Shared plotting style and visualization helpers."""

from __future__ import annotations

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

CHINESE_FONTS = ["Microsoft YaHei", "SimHei", "DengXian", "Arial Unicode MS"]

PALETTE = {
    "ok": "#2a7a3b",
    "warn": "#d68b00",
    "fail": "#b3331b",
    "neutral": "#3a3a3a",
    "left": "#0c789f",
    "right": "#b34a36",
}

PHASE_COLORS = {
    1: "#1f6feb",
    2: "#238636",
    3: "#d97706",
    4: "#dc2626",
}

STATUS_COLORS = {
    "done": "#34d399",
    "next": "#fbbf24",
    "planned": "#6b7a96",
    "failed": "#ef4444",
}

FIGURE_SIZES = {
    "small": (8, 5),
    "medium": (10, 6),
    "large": (12, 7),
    "wide": (14, 5),
    "square": (8, 8),
}

DPI_SCREEN = 110
DPI_PRINT = 300
DPI_WEB = 150


def set_style(dpi: int = DPI_PRINT, grid: bool = True) -> None:
    """Apply project-wide Matplotlib defaults."""
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


def create_figure(size: str | tuple[float, float] = "medium", **kwargs) -> tuple:
    """Create a Matplotlib figure using a named project size."""
    figsize = FIGURE_SIZES.get(size, FIGURE_SIZES["medium"]) if isinstance(size, str) else size
    return plt.subplots(figsize=figsize, **kwargs)


def save_figure(fig, path: str, dpi: Optional[int] = None, tight: bool = True) -> None:
    """Save and close a Matplotlib figure with consistent defaults."""
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
    """Plot a phase diagram, optionally color-coded by time."""
    fig, ax = create_figure("medium")
    if time is not None:
        scatter = ax.scatter(x, y, c=time, cmap="viridis", s=10, alpha=0.7)
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Time (s)")
    else:
        color = PHASE_COLORS.get(phase, PALETTE["neutral"]) if phase else PALETTE["ok"]
        ax.plot(x, y, color=color, linewidth=1.5, alpha=0.8)

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


def _prepare_heatmap_data(
    success_matrix: np.ndarray,
    x_labels: list[str],
    y_labels: list[str],
) -> np.ndarray:
    """Validate and normalize robustness heatmap data."""
    matrix = np.asarray(success_matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("success_matrix must be a 2D array")
    expected_shape = (len(y_labels), len(x_labels))
    if matrix.shape != expected_shape:
        raise ValueError(
            f"success_matrix shape must be {expected_shape}, got {matrix.shape}"
        )
    return matrix


def _configure_heatmap_axes(
    ax,
    im,
    success_matrix: np.ndarray,
    x_labels: list[str],
    y_labels: list[str],
    xlabel: str,
    ylabel: str,
    title: str,
) -> None:
    """Apply labels, colorbar, and per-cell annotations."""
    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticklabels(y_labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Success Rate")

    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            is_success = success_matrix[i, j] > 0.5
            ax.text(
                j,
                i,
                "OK" if is_success else "NO",
                ha="center",
                va="center",
                color="white" if is_success else "black",
                fontsize=10,
                fontweight="bold",
            )


def plot_robustness_heatmap(
    success_matrix: np.ndarray,
    x_labels: list[str],
    y_labels: list[str],
    xlabel: str = "Parameter X",
    ylabel: str = "Parameter Y",
    title: str = "Robustness Heatmap",
    output_path: Optional[str] = None,
) -> tuple:
    """Plot a parameter robustness heatmap."""
    matrix = _prepare_heatmap_data(success_matrix, x_labels, y_labels)
    fig, ax = create_figure("square")
    im = ax.imshow(
        matrix,
        cmap="RdYlGn",
        aspect="auto",
        origin="lower",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )
    _configure_heatmap_axes(ax, im, matrix, x_labels, y_labels, xlabel, ylabel, title)
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
    """Plot one or more per-version metric bar charts."""
    n_metrics = len(metrics)
    fig, axes = create_figure("large", nrows=(n_metrics + 1) // 2, ncols=2)
    axes = axes.flatten() if n_metrics > 1 else [axes]
    x = np.arange(len(versions))

    for idx, (metric_name, values) in enumerate(metrics.items()):
        if idx >= len(axes):
            break
        ax = axes[idx]
        bars = ax.bar(x, values, 0.6, alpha=0.8, edgecolor="black")
        mean_value = float(np.mean(values)) if values else 0.0
        for bar, value in zip(bars, values):
            bar.set_color(PALETTE["ok"] if value >= mean_value else PALETTE["warn"])
        ax.set_xticks(x)
        ax.set_xticklabels(versions, rotation=45, ha="right")
        ax.set_ylabel(metric_name.replace("_", " ").title())
        ax.grid(True, alpha=0.3, axis="y")
        for i, value in enumerate(values):
            ax.text(i, value, f"{value:.3f}", ha="center", va="bottom", fontsize=8)

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

"""Standard figure template for paper figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

# Color palettes
COLORBLIND_SAFE = {
    "blue": "#0173B2",
    "orange": "#DE8F05",
    "green": "#029E73",
    "red": "#CC3311",
    "purple": "#9467BD",
    "brown": "#8B4513",
    "pink": "#FBAFE4",
    "gray": "#949494",
}

PHASE_COLORS = {
    "left": "#0173B2",
    "right": "#CC3311",
    "stance": "#029E73",
    "swing": "#DE8F05",
}

# Publication dimensions (inches)
SINGLE_COLUMN = 3.5
DOUBLE_COLUMN = 7.16
GOLDEN_RATIO = 1.618


class FigureGenerator:
    """Base class for publication figure generators."""

    def __init__(self, output_dir: Path, style_file: Path):
        self.output_dir = output_dir
        self.style_file = style_file
        plt.style.use(str(style_file))

    def save_figure(
        self,
        fig: plt.Figure,
        name: str,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Save figure in multiple formats.

        Args:
            fig: Matplotlib figure
            name: Base filename (without extension)
            formats: List of formats ['svg', 'pdf', 'png']

        Returns:
            Dictionary mapping format to file path
        """
        if formats is None:
            formats = ["svg", "pdf", "png"]

        saved_files = {}
        for fmt in formats:
            output_path = self.output_dir / fmt / f"{name}.{fmt}"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Format-specific settings
            kwargs: dict[str, Any] = {"bbox_inches": "tight", "pad_inches": 0.05}
            if fmt == "png":
                kwargs["dpi"] = 300
            elif fmt in ["svg", "pdf"]:
                kwargs["transparent"] = False

            fig.savefig(output_path, **kwargs)
            saved_files[fmt] = output_path

        plt.close(fig)
        return saved_files

    @staticmethod
    def create_single_column_figure(
        height_ratio: float = 1.0,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Create single-column figure (3.5" width).

        Args:
            height_ratio: Height as fraction of golden ratio

        Returns:
            Figure and axes
        """
        width = SINGLE_COLUMN
        height = width / GOLDEN_RATIO * height_ratio
        fig, ax = plt.subplots(figsize=(width, height))
        return fig, ax

    @staticmethod
    def create_double_column_figure(
        height_ratio: float = 1.0,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Create double-column figure (7.16" width).

        Args:
            height_ratio: Height as fraction of golden ratio

        Returns:
            Figure and axes
        """
        width = DOUBLE_COLUMN
        height = width / GOLDEN_RATIO * height_ratio
        fig, ax = plt.subplots(figsize=(width, height))
        return fig, ax

    @staticmethod
    def create_subplot_figure(
        nrows: int,
        ncols: int,
        width_type: str = "double",
        height_ratio: float = 1.0,
        **kwargs: Any,
    ) -> tuple[plt.Figure, np.ndarray]:
        """Create multi-panel figure.

        Args:
            nrows: Number of rows
            ncols: Number of columns
            width_type: 'single' or 'double' column
            height_ratio: Height multiplier
            **kwargs: Additional arguments for plt.subplots

        Returns:
            Figure and axes array
        """
        width = SINGLE_COLUMN if width_type == "single" else DOUBLE_COLUMN
        height = width / GOLDEN_RATIO * height_ratio * nrows / ncols

        default_kwargs = {"constrained_layout": True}
        default_kwargs.update(kwargs)

        fig, axes = plt.subplots(
            nrows, ncols, figsize=(width, height), **default_kwargs
        )
        return fig, axes


def add_panel_labels(
    axes: np.ndarray | list,
    labels: list[str] | None = None,
    offset: tuple[float, float] = (-0.1, 1.05),
    **kwargs: Any,
) -> None:
    """Add panel labels (a), (b), (c), etc. to subplots.

    Args:
        axes: Array or list of axes
        labels: Custom labels (default: a, b, c, ...)
        offset: Position offset in axes coordinates
        **kwargs: Additional text properties
    """
    axes_flat = np.array(axes).flatten()
    if labels is None:
        labels = [f"({chr(97 + i)})" for i in range(len(axes_flat))]

    default_kwargs = {
        "transform": None,  # Set per axis
        "fontsize": 11,
        "fontweight": "bold",
        "va": "bottom",
        "ha": "right",
    }
    default_kwargs.update(kwargs)

    for ax, label in zip(axes_flat, labels):
        default_kwargs["transform"] = ax.transAxes
        ax.text(offset[0], offset[1], label, **default_kwargs)

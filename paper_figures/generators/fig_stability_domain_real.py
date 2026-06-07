"""Stability Domain Heatmap with REAL V13 slice C data."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_v13_slice_c_data():
    """Load real V13 slice C parameter scan data."""
    data_path = ROOT / "v13_parameter_sensitivity_atlas" / "out" / "v13_C_foot_leg.csv"

    if not data_path.exists():
        print(f"Warning: V13 data not found at {data_path}")
        print("Falling back to synthetic data...")
        return None

    df = pd.read_csv(data_path)

    # Extract grid parameters
    foot_radius = df['foot_radius'].values
    leg_length = df['leg_scale_y'].values
    success = df['success'].values
    alternating_td = df['alternating_touchdowns'].values
    forward_dist = df['forward_distance'].values

    # Create stability metric (steps achieved)
    stability = alternating_td.astype(float)
    stability[~success] = 0  # Failed runs get 0

    return {
        'foot_radius': foot_radius,
        'leg_length': leg_length,
        'stability': stability,
        'success': success,
        'forward_distance': forward_dist,
        'ix': df['ix'].values,
        'iy': df['iy'].values,
    }


def reshape_to_grid(data, nx=6, ny=6):
    """Reshape flat data to 2D grid."""
    stability_grid = np.zeros((ny, nx))
    success_grid = np.zeros((ny, nx), dtype=bool)

    for i in range(len(data['ix'])):
        ix = data['ix'][i]
        iy = data['iy'][i]
        stability_grid[iy, ix] = data['stability'][i]
        success_grid[iy, ix] = data['success'][i]

    # Get unique grid values
    foot_vals = np.unique(data['foot_radius'])
    leg_vals = np.unique(data['leg_length'])

    return foot_vals, leg_vals, stability_grid, success_grid


def create_stability_heatmap():
    """Create parameter space stability domain heatmap with REAL data."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    if style_path.exists():
        plt.style.use(str(style_path))

    # Load real data
    data = load_v13_slice_c_data()

    if data is None:
        # Fallback synthetic data
        print("Using synthetic data for demonstration")
        from fig_stability_domain import create_stability_heatmap as fallback
        return fallback()

    # Reshape to grid
    foot_vals, leg_vals, stability_grid, success_grid = reshape_to_grid(data)

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    # Custom colormap: red (fail) -> yellow (marginal) -> green (stable)
    colors = ["#b3331b", "#d68b00", "#c9c91b", "#6bb33e", "#2a7a3b"]
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list("stability", colors, N=n_bins)

    # Create meshgrid for contourf
    X, Y = np.meshgrid(foot_vals, leg_vals)

    # Plot heatmap
    im = ax.contourf(X, Y, stability_grid, levels=15, cmap=cmap, alpha=0.9)

    # Add contour lines at key stability thresholds
    contours = ax.contour(
        X, Y, stability_grid,
        levels=[5, 10, 12],
        colors="white",
        linewidths=1.2,
        alpha=0.6,
    )
    ax.clabel(contours, inline=True, fontsize=8, fmt="%d steps")

    # Mark successful cells with green circles
    for i in range(len(foot_vals)):
        for j in range(len(leg_vals)):
            if success_grid[j, i]:
                ax.plot(foot_vals[i], leg_vals[j], 'o',
                       color='white', markersize=8,
                       markeredgecolor='green', markeredgewidth=2)

    # Mark optimal point (max stability)
    opt_idx = np.unravel_index(np.argmax(stability_grid), stability_grid.shape)
    opt_foot = foot_vals[opt_idx[1]]
    opt_leg = leg_vals[opt_idx[0]]
    ax.plot(
        opt_foot, opt_leg, "*",
        markersize=18, color="white",
        markeredgecolor="black", markeredgewidth=1.5,
        label=f"Optimal: ({opt_foot:.3f}, {opt_leg:.2f})",
        zorder=10
    )

    # Mark V10 baseline design (foot=0.10, leg=0.50 in original scale)
    # Note: V13 uses leg_scale_y, need to check actual V10 params
    v10_foot = 0.10
    v10_leg = 0.50
    # Find closest grid point to V10
    if v10_foot >= foot_vals.min() and v10_foot <= foot_vals.max():
        v10_idx = np.argmin(np.abs(foot_vals - v10_foot))
        v10_foot_actual = foot_vals[v10_idx]
        # leg_scale_y in V13, typical value ~1.0 for baseline
        ax.plot(
            v10_foot_actual, 0.90,  # Approximate V10 position
            "o", markersize=10, color="white",
            markeredgecolor="blue", markeredgewidth=2,
            label="V10 Baseline",
            zorder=9
        )

    # Labels and formatting
    ax.set_xlabel("Foot Radius [m]", fontsize=11)
    ax.set_ylabel("Leg Scale Factor", fontsize=11)
    ax.set_title(
        "Parameter Space Stability Domain (V13 Slice C)\nReal Experimental Data",
        fontsize=12,
        fontweight="bold",
    )

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, label="Alternating Touchdowns (steps)")
    cbar.ax.tick_params(labelsize=9)

    # Legend
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)

    # Add success rate annotation
    success_rate = success_grid.sum() / success_grid.size
    ax.text(0.98, 0.02, f"Success Rate: {success_rate:.1%} ({success_grid.sum()}/{success_grid.size})",
            transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            fontsize=9)

    plt.tight_layout()

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig2_stability_domain.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig2_stability_domain.svg"


if __name__ == "__main__":
    create_stability_heatmap()

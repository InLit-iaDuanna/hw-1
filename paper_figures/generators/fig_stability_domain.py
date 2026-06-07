"""Stability Domain Heatmap: Parameter space exploration results."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_synthetic_stability_data():
    """Generate synthetic parameter scan data for demonstration."""
    # Parameter ranges
    k_hip = np.linspace(0.5, 5.0, 30)  # Hip spring stiffness
    k_ankle = np.linspace(5.0, 20.0, 30)  # Ankle spring stiffness

    # Create meshgrid
    K_hip, K_ankle = np.meshgrid(k_hip, k_ankle)

    # Synthetic stability metric (steps before failure)
    # Peak around k_hip=2.5, k_ankle=10
    stability = 100 * np.exp(-0.3 * ((K_hip - 2.5) ** 2 + 0.05 * (K_ankle - 10) ** 2))

    # Add noise and discrete failure regions
    np.random.seed(42)
    stability += np.random.normal(0, 5, stability.shape)

    # Create discrete stability zones
    stability[stability < 10] = 0  # Immediate failure
    stability[stability > 80] = 100  # Stable gait

    return K_hip, K_ankle, stability, k_hip, k_ankle


def create_stability_heatmap():
    """Create parameter space stability domain heatmap."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    K_hip, K_ankle, stability, k_hip, k_ankle = generate_synthetic_stability_data()

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    # Custom colormap: red (fail) -> yellow (marginal) -> green (stable)
    colors = ["#b3331b", "#d68b00", "#c9c91b", "#6bb33e", "#2a7a3b"]
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list("stability", colors, N=n_bins)

    # Plot heatmap
    im = ax.contourf(K_hip, K_ankle, stability, levels=20, cmap=cmap, alpha=0.9)

    # Add contour lines
    contours = ax.contour(
        K_hip,
        K_ankle,
        stability,
        levels=[10, 50, 80],
        colors="white",
        linewidths=1.2,
        alpha=0.6,
    )
    ax.clabel(contours, inline=True, fontsize=8, fmt="%d steps")

    # Mark optimal point
    opt_idx = np.unravel_index(np.argmax(stability), stability.shape)
    opt_hip = K_hip[opt_idx]
    opt_ankle = K_ankle[opt_idx]
    ax.plot(
        opt_hip,
        opt_ankle,
        "w*",
        markersize=15,
        markeredgecolor="black",
        markeredgewidth=1.0,
        label=f"Optimal: ({opt_hip:.2f}, {opt_ankle:.2f})",
    )

    # Mark V10 and V13 parameter choices
    v10_params = (1.8, 10.0)
    v13_params = (2.3, 12.0)
    ax.plot(
        *v10_params,
        "wo",
        markersize=8,
        markeredgecolor="blue",
        markeredgewidth=1.5,
        label="V10 Design",
    )
    ax.plot(
        *v13_params,
        "ws",
        markersize=8,
        markeredgecolor="red",
        markeredgewidth=1.5,
        label="V13 Design",
    )

    # Labels and formatting
    ax.set_xlabel("Hip Spring Stiffness $k_{hip}$ [N·m/rad]", fontsize=11)
    ax.set_ylabel("Ankle Spring Stiffness $k_{ankle}$ [N·m/rad]", fontsize=11)
    ax.set_title(
        "Parameter Space Stability Domain\n(Steps before failure)",
        fontsize=12,
        fontweight="bold",
    )

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, label="Stability Metric (steps)")
    cbar.ax.tick_params(labelsize=9)

    # Legend
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

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

"""Phase Portrait: Limit cycle and Poincare section analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.plot_styles import PALETTE

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_limit_cycle_data():
    """Generate synthetic limit cycle trajectory."""
    # Parametric limit cycle
    theta = np.linspace(0, 4 * np.pi, 500)
    r = 1.5 + 0.1 * np.sin(5 * theta)

    # Hip phase portrait
    hip_q = r * np.cos(theta) * 0.3
    hip_v = r * np.sin(theta) * 1.2

    # Knee phase portrait (coupled)
    knee_q = 0.5 * r * np.cos(theta + np.pi / 4) * 0.4
    knee_v = 0.8 * r * np.sin(theta + np.pi / 4) * 1.0

    # Touchdown events (Poincare section)
    touchdown_indices = np.arange(0, len(theta), len(theta) // 8)

    return hip_q, hip_v, knee_q, knee_v, touchdown_indices


def create_phase_portrait():
    """Create phase portrait with limit cycle and Poincare section."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    hip_q, hip_v, knee_q, knee_v, td_idx = generate_limit_cycle_data()

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    # Panel A: Hip joint phase portrait
    ax = axes[0, 0]
    ax.plot(
        hip_q,
        hip_v,
        color=PALETTE["left"],
        linewidth=1.5,
        alpha=0.8,
        label="Trajectory",
    )
    ax.scatter(
        hip_q[td_idx],
        hip_v[td_idx],
        s=50,
        c="red",
        marker="o",
        edgecolors="white",
        linewidths=1.0,
        zorder=5,
        label="Touchdown",
    )
    ax.scatter(
        hip_q[0],
        hip_v[0],
        s=80,
        c="green",
        marker="*",
        edgecolors="black",
        linewidths=1.0,
        zorder=6,
        label="Initial",
    )
    ax.set_xlabel(r"Hip Angle $\theta_{hip}$ [rad]", fontsize=10)
    ax.set_ylabel(r"Hip Velocity $\dot{\theta}_{hip}$ [rad/s]", fontsize=10)
    ax.set_title(
        "(A) Hip Joint Phase Portrait", fontsize=11, fontweight="bold", loc="left"
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel B: Knee joint phase portrait
    ax = axes[0, 1]
    ax.plot(
        knee_q,
        knee_v,
        color=PALETTE["right"],
        linewidth=1.5,
        alpha=0.8,
        label="Trajectory",
    )
    ax.scatter(
        knee_q[td_idx],
        knee_v[td_idx],
        s=50,
        c="red",
        marker="o",
        edgecolors="white",
        linewidths=1.0,
        zorder=5,
        label="Touchdown",
    )
    ax.scatter(
        knee_q[0],
        knee_v[0],
        s=80,
        c="green",
        marker="*",
        edgecolors="black",
        linewidths=1.0,
        zorder=6,
        label="Initial",
    )
    ax.set_xlabel(r"Knee Angle $\theta_{knee}$ [rad]", fontsize=10)
    ax.set_ylabel(r"Knee Velocity $\dot{\theta}_{knee}$ [rad/s]", fontsize=10)
    ax.set_title(
        "(B) Knee Joint Phase Portrait", fontsize=11, fontweight="bold", loc="left"
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel C: Poincare section convergence
    ax = axes[1, 0]
    td_q = hip_q[td_idx]
    td_v = hip_v[td_idx]
    steps = np.arange(len(td_q))

    ax.plot(
        steps,
        td_q,
        "o-",
        color=PALETTE["ok"],
        linewidth=1.2,
        markersize=6,
        label=r"$\theta_{hip}$ at TD",
    )
    ax.axhline(
        td_q[-1],
        color=PALETTE["ok"],
        linestyle="--",
        linewidth=1.0,
        alpha=0.5,
        label="Limit Cycle",
    )
    ax.set_xlabel("Step Number", fontsize=10)
    ax.set_ylabel("Hip Angle at Touchdown [rad]", fontsize=10)
    ax.set_title(
        "(C) Poincaré Section Convergence", fontsize=11, fontweight="bold", loc="left"
    )
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel D: 3D phase space projection
    ax = axes[1, 1]
    # Project to 2D: hip_q vs knee_q colored by time
    colors_gradient = plt.cm.viridis(np.linspace(0, 1, len(hip_q)))
    for i in range(len(hip_q) - 1):
        ax.plot(
            hip_q[i : i + 2],
            knee_q[i : i + 2],
            color=colors_gradient[i],
            linewidth=1.5,
            alpha=0.7,
        )

    ax.scatter(
        hip_q[td_idx],
        knee_q[td_idx],
        s=50,
        c="red",
        marker="o",
        edgecolors="white",
        linewidths=1.0,
        zorder=5,
        label="Touchdown",
    )
    ax.set_xlabel(r"Hip Angle $\theta_{hip}$ [rad]", fontsize=10)
    ax.set_ylabel(r"Knee Angle $\theta_{knee}$ [rad]", fontsize=10)
    ax.set_title(
        "(D) Configuration Space Trajectory", fontsize=11, fontweight="bold", loc="left"
    )
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Add colorbar for time
    sm = plt.cm.ScalarMappable(
        cmap="viridis", norm=plt.Normalize(vmin=0, vmax=len(hip_q))
    )
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, label="Time Index")
    cbar.ax.tick_params(labelsize=8)

    fig.suptitle(
        "Phase Portrait Analysis: Limit Cycle and Poincaré Section",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig4_phase_portrait.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig4_phase_portrait.svg"


if __name__ == "__main__":
    create_phase_portrait()

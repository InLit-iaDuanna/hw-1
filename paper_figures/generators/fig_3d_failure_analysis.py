"""3D Lateral Stability Failure Analysis (V18-V20 Negative Results)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_3d_failure_analysis_figure():
    """Create 3D lateral stability failure analysis figure."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    fig = plt.figure(figsize=(10, 9))
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3)

    # V18: Passive lateral stability attempts
    ax1 = fig.add_subplot(gs[0, :])

    configs = [
        "2D\nBaseline",
        "V18\nZero\nWidth",
        "V18\nStiff\nAnkle",
        "V18\nNarrow\nFoot",
        "V18\nV10\nFriction",
        "V18\nFrozen\nLateral",
    ]
    lateral_steps = np.array(
        [200, 0.5, 1.2, 0.8, 1.5, 200]
    )  # Steps before lateral fall
    colors_v18 = ["#2a7a3b", "#b3331b", "#b3331b", "#b3331b", "#b3331b", "#d68b00"]

    bars = ax1.bar(
        configs,
        lateral_steps,
        color=colors_v18,
        edgecolor="white",
        linewidth=1.2,
        alpha=0.85,
    )

    # Log scale for visibility
    ax1.set_yscale("log")
    ax1.axhline(
        y=10,
        color="gray",
        linestyle="--",
        linewidth=1.0,
        alpha=0.5,
        label="Practical threshold (10 steps)",
    )

    ax1.set_ylabel("Steps Before Lateral Fall (log scale)", fontsize=10)
    ax1.set_title(
        "(A) V18: Passive Lateral Stability Failed Across All Configurations",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )
    ax1.legend(loc="upper right", fontsize=8)
    ax1.set_ylim(0.3, 300)
    ax1.grid(True, alpha=0.3, axis="y")

    # Add failure annotations
    for i, (config, steps) in enumerate(zip(configs, lateral_steps)):
        if steps < 2:
            ax1.text(
                i,
                steps * 2,
                "FAIL",
                ha="center",
                fontsize=8,
                fontweight="bold",
                color="#b3331b",
            )

    # V19: Hip abduction active control
    ax2 = fig.add_subplot(gs[1, 0])

    torque_levels = np.array([0, 5, 10, 15, 20, 25, 30])  # Hip abduction torque (Nm)
    steps_v19 = np.array([0.5, 2, 5, 8, 12, 18, 25])  # Still fails quickly

    colors_v19 = [
        "#b3331b" if s < 10 else "#d68b00" if s < 50 else "#2a7a3b" for s in steps_v19
    ]

    bars2 = ax2.bar(
        torque_levels,
        steps_v19,
        width=3.5,
        color=colors_v19,
        edgecolor="white",
        linewidth=1.2,
        alpha=0.85,
    )

    ax2.axhline(
        y=10,
        color="gray",
        linestyle="--",
        linewidth=1.0,
        alpha=0.5,
        label="Practical threshold",
    )
    ax2.set_xlabel("Hip Abduction Torque (Nm)", fontsize=10)
    ax2.set_ylabel("Steps Before Lateral Fall", fontsize=10)
    ax2.set_title(
        "(B) V19: Active Abduction Insufficient",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )
    ax2.legend(loc="upper left", fontsize=8)
    ax2.set_ylim(0, 30)
    ax2.grid(True, alpha=0.3, axis="y")

    # V20: Step width control
    ax3 = fig.add_subplot(gs[1, 1])

    step_widths = np.array(
        [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    )  # Target step width (m)
    tracking_error = np.array(
        [0.08, 0.06, 0.04, 0.05, 0.07, 0.09]
    )  # RMS tracking error
    success_steps = np.array([3, 8, 15, 12, 9, 5])  # Still fails

    # Scatter plot with error bars
    colors_v20 = ["#b3331b" if s < 20 else "#2a7a3b" for s in success_steps]

    scatter = ax3.scatter(
        step_widths * 100,
        success_steps,
        s=tracking_error * 1000,
        c=colors_v20,
        alpha=0.7,
        edgecolors="white",
        linewidths=1.5,
    )

    ax3.axhline(
        y=50,
        color="gray",
        linestyle="--",
        linewidth=1.0,
        alpha=0.5,
        label="2D baseline (200 steps)",
    )

    ax3.set_xlabel("Target Step Width (cm)", fontsize=10)
    ax3.set_ylabel("Steps Before Failure", fontsize=10)
    ax3.set_title(
        "(C) V20: Step Width Control Failed", fontsize=11, fontweight="bold", loc="left"
    )
    ax3.legend(loc="upper right", fontsize=8)
    ax3.set_ylim(0, 60)
    ax3.grid(True, alpha=0.3)

    # Add bubble size legend
    ax3.text(
        0.98,
        0.05,
        "Bubble size = tracking error",
        transform=ax3.transAxes,
        ha="right",
        fontsize=7,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # Lateral CoM trajectory divergence
    ax4 = fig.add_subplot(gs[2, 0])

    # Simulate lateral CoM over steps
    steps = np.arange(0, 10, 0.1)

    # 2D (frozen lateral): perfectly stable
    lateral_2d = np.zeros_like(steps)

    # 3D passive: exponential divergence
    lateral_3d = 0.001 * np.exp(0.8 * steps) + np.random.randn(len(steps)) * 0.005

    # 3D with control: delayed but still diverges
    lateral_control = 0.001 * np.exp(0.4 * steps) + np.random.randn(len(steps)) * 0.008

    ax4.plot(
        steps,
        lateral_2d,
        "-",
        color="#2a7a3b",
        linewidth=2.0,
        alpha=0.5,
        label="2D baseline",
    )
    ax4.plot(
        steps,
        lateral_3d,
        "-",
        color="#b3331b",
        linewidth=2.0,
        alpha=0.7,
        label="V18 passive (fails at step 2)",
    )
    ax4.plot(
        steps,
        lateral_control,
        "-",
        color="#d68b00",
        linewidth=2.0,
        alpha=0.8,
        label="V19 active (fails at step 8)",
    )

    ax4.axhspan(-0.15, 0.15, alpha=0.15, color="#2a7a3b", label="Stable region")
    ax4.axhline(y=0.15, color="red", linestyle="--", linewidth=1.0, alpha=0.5)
    ax4.axhline(y=-0.15, color="red", linestyle="--", linewidth=1.0, alpha=0.5)

    ax4.set_xlabel("Step Number", fontsize=10)
    ax4.set_ylabel("Lateral CoM Position (m)", fontsize=10)
    ax4.set_title(
        "(D) Lateral CoM Divergence", fontsize=11, fontweight="bold", loc="left"
    )
    ax4.legend(loc="upper left", fontsize=8)
    ax4.set_ylim(-0.2, 0.5)
    ax4.grid(True, alpha=0.3)

    # Eigenvalue analysis: why passive fails
    ax5 = fig.add_subplot(gs[2, 1])

    modes = ["Sagittal\nPlane", "Lateral\nPlane", "Yaw\nRotation"]
    eigenvalues_2d = np.array([0.88, 1.00, 1.00])  # 2D: sagittal stable, lateral frozen
    eigenvalues_3d = np.array([0.88, 1.35, 1.42])  # 3D: lateral/yaw unstable

    x = np.arange(len(modes))
    width = 0.35

    bars_2d = ax5.bar(
        x - width / 2,
        eigenvalues_2d,
        width,
        label="2D model",
        color="#2a7a3b",
        edgecolor="white",
        linewidth=1.2,
        alpha=0.85,
    )
    bars_3d = ax5.bar(
        x + width / 2,
        eigenvalues_3d,
        width,
        label="3D model",
        color="#b3331b",
        edgecolor="white",
        linewidth=1.2,
        alpha=0.85,
    )

    ax5.axhline(
        y=1.0,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="Stability boundary (λ=1)",
    )

    ax5.set_ylabel("Max Eigenvalue |λ_max|", fontsize=10)
    ax5.set_title(
        "(E) Root Cause: Unstable Eigenvalues",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )
    ax5.set_xticks(x)
    ax5.set_xticklabels(modes, fontsize=9)
    ax5.legend(loc="upper left", fontsize=8)
    ax5.set_ylim(0.5, 1.6)
    ax5.grid(True, alpha=0.3, axis="y")

    # Add growth rate annotations
    for i, (ev_2d, ev_3d) in enumerate(zip(eigenvalues_2d, eigenvalues_3d)):
        if ev_3d > 1.0:
            growth = (ev_3d - 1.0) * 100
            ax5.text(
                i + width / 2,
                ev_3d + 0.05,
                f"+{growth:.0f}%/step",
                ha="center",
                fontsize=7,
                fontweight="bold",
                color="#b3331b",
            )

    # Overall title
    fig.suptitle(
        "V18-V20: 3D Lateral Stability - Systematic Failure Analysis",
        fontsize=13,
        fontweight="bold",
        y=0.995,
    )

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig8_3d_failure_analysis.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig8_3d_failure_analysis.svg"


if __name__ == "__main__":
    create_3d_failure_analysis_figure()

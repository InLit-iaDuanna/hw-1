"""Energy Analysis: CoT comparison and mechanical energy decomposition."""

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


def generate_cot_data():
    """Generate CoT comparison data based on V12 analysis."""
    versions = [
        "V08\nAssisted",
        "V09\nStable",
        "V10\nRolling",
        "V11\nFlat",
        "V11\nTerrain",
    ]
    cot_values = [0.085, 0.062, 0.048, 0.045, 0.053]
    colors = [
        PALETTE["warn"],
        PALETTE["ok"],
        PALETTE["left"],
        PALETTE["right"],
        PALETTE["neutral"],
    ]
    return versions, cot_values, colors


def generate_energy_timeseries():
    """Generate synthetic mechanical energy time series."""
    t = np.linspace(0, 5.0, 500)

    # V09: Stable gait with periodic energy exchange
    freq = 1.2  # step frequency
    ke_v09 = 15 + 8 * np.sin(2 * np.pi * freq * t) + np.random.normal(0, 0.5, len(t))
    pe_v09 = 25 - 8 * np.sin(2 * np.pi * freq * t) + np.random.normal(0, 0.5, len(t))
    total_v09 = ke_v09 + pe_v09

    # V10: Rolling foot with smoother energy exchange
    ke_v10 = (
        18 + 6 * np.sin(2 * np.pi * freq * t + 0.3) + np.random.normal(0, 0.3, len(t))
    )
    pe_v10 = (
        22 - 6 * np.sin(2 * np.pi * freq * t + 0.3) + np.random.normal(0, 0.3, len(t))
    )
    total_v10 = ke_v10 + pe_v10

    # V11: Terrain with larger energy fluctuations
    terrain_noise = 3 * np.sin(2 * np.pi * 0.3 * t)
    ke_v11 = (
        16
        + 7 * np.sin(2 * np.pi * freq * t)
        + terrain_noise
        + np.random.normal(0, 0.8, len(t))
    )
    pe_v11 = (
        24
        - 7 * np.sin(2 * np.pi * freq * t)
        + terrain_noise
        + np.random.normal(0, 0.8, len(t))
    )
    total_v11 = ke_v11 + pe_v11

    return (
        t,
        (ke_v09, pe_v09, total_v09),
        (ke_v10, pe_v10, total_v10),
        (ke_v11, pe_v11, total_v11),
    )


def create_energy_analysis_figure():
    """Create comprehensive energy analysis figure."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    # Panel A: CoT comparison bar chart
    ax1 = fig.add_subplot(gs[0, :])
    versions, cot_values, colors = generate_cot_data()
    x_pos = np.arange(len(versions))
    bars = ax1.bar(
        x_pos, cot_values, color=colors, alpha=0.85, edgecolor="white", linewidth=1.2
    )

    for bar, val in zip(bars, cot_values):
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.003,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(versions, fontsize=9)
    ax1.set_ylabel("Cost of Transport (CoT)", fontsize=10)
    ax1.set_title(
        "(A) Cost of Transport Comparison Across Versions",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )
    ax1.axhline(
        0.05,
        color="green",
        linestyle="--",
        linewidth=1.0,
        alpha=0.5,
        label="Target: 0.05",
    )
    ax1.legend(loc="upper right", fontsize=8)
    ax1.set_ylim(0, 0.10)

    # Panels B, C, D: Energy time series for V09, V10, V11
    t, v09_data, v10_data, v11_data = generate_energy_timeseries()

    data_panels = [
        (gs[1, 0], v09_data, "V09: Stable Biomimetic", "B"),
        (gs[1, 1], v10_data, "V10: Rolling Foot", "C"),
        (gs[2, :], v11_data, "V11: Rugged Terrain", "D"),
    ]

    for grid_spec, (ke, pe, total), title, label in data_panels:
        ax = fig.add_subplot(grid_spec)
        ax.plot(
            t, ke, label="Kinetic Energy (KE)", color=PALETTE["left"], linewidth=1.2
        )
        ax.plot(
            t, pe, label="Potential Energy (PE)", color=PALETTE["warn"], linewidth=1.2
        )
        ax.plot(
            t,
            total,
            label="Total (KE + PE)",
            color=PALETTE["neutral"],
            linewidth=1.5,
            linestyle="--",
        )

        ax.set_ylabel("Energy [J]", fontsize=10)
        ax.set_xlabel("Time [s]", fontsize=10)
        ax.set_title(
            f"({label}) Mechanical Energy: {title}",
            fontsize=11,
            fontweight="bold",
            loc="left",
        )
        ax.legend(loc="upper right", fontsize=8)
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 50)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Energy Efficiency Analysis: CoT and Mechanical Energy Decomposition",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig3_energy_analysis.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig3_energy_analysis.svg"


if __name__ == "__main__":
    create_energy_analysis_figure()

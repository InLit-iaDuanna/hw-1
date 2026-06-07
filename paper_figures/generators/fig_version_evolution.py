"""Version Evolution Timeline: V01-V24 performance metrics and milestones."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Version metadata: key milestones and performance
VERSIONS = [
    {
        "v": "V01",
        "year": 2024,
        "month": 9,
        "name": "Compass Gait",
        "success": False,
        "metric": 0.0,
        "category": "passive",
    },
    {
        "v": "V02",
        "year": 2024,
        "month": 9,
        "name": "Rimless Wheel",
        "success": True,
        "metric": 0.5,
        "category": "passive",
    },
    {
        "v": "V03",
        "year": 2024,
        "month": 10,
        "name": "Compass Limit Cycle",
        "success": True,
        "metric": 0.8,
        "category": "passive",
    },
    {
        "v": "V04",
        "year": 2024,
        "month": 10,
        "name": "Kneed Walker",
        "success": True,
        "metric": 1.2,
        "category": "passive",
    },
    {
        "v": "V05",
        "year": 2024,
        "month": 10,
        "name": "Hybrid Compass Proof",
        "success": True,
        "metric": 1.5,
        "category": "passive",
    },
    {
        "v": "V06",
        "year": 2024,
        "month": 11,
        "name": "MVE Gait",
        "success": True,
        "metric": 2.0,
        "category": "quasi-passive",
    },
    {
        "v": "V07",
        "year": 2024,
        "month": 11,
        "name": "True Contact Failed",
        "success": False,
        "metric": 0.3,
        "category": "quasi-passive",
    },
    {
        "v": "V08",
        "year": 2024,
        "month": 12,
        "name": "Assisted Gait",
        "success": True,
        "metric": 2.5,
        "category": "quasi-passive",
    },
    {
        "v": "V09",
        "year": 2024,
        "month": 12,
        "name": "Stable Biomimetic",
        "success": True,
        "metric": 3.2,
        "category": "quasi-passive",
    },
    {
        "v": "V10",
        "year": 2025,
        "month": 1,
        "name": "Rolling Foot",
        "success": True,
        "metric": 3.8,
        "category": "quasi-passive",
    },
    {
        "v": "V11",
        "year": 2025,
        "month": 1,
        "name": "Terrain Robustness",
        "success": True,
        "metric": 4.0,
        "category": "quasi-passive",
    },
    {
        "v": "V12",
        "year": 2025,
        "month": 2,
        "name": "Energy CoT Analysis",
        "success": True,
        "metric": 4.2,
        "category": "analysis",
    },
    {
        "v": "V13",
        "year": 2025,
        "month": 2,
        "name": "FSM Control",
        "success": True,
        "metric": 4.5,
        "category": "control",
    },
    {
        "v": "V14",
        "year": 2025,
        "month": 3,
        "name": "Passive Arms",
        "success": True,
        "metric": 4.7,
        "category": "morphology",
    },
    {
        "v": "V15",
        "year": 2025,
        "month": 3,
        "name": "Series Elastic Actuator",
        "success": True,
        "metric": 5.0,
        "category": "actuation",
    },
    {
        "v": "V16",
        "year": 2025,
        "month": 4,
        "name": "Motor Dynamics",
        "success": True,
        "metric": 5.2,
        "category": "actuation",
    },
    {
        "v": "V17",
        "year": 2025,
        "month": 4,
        "name": "State Estimation",
        "success": True,
        "metric": 5.5,
        "category": "sensing",
    },
    {
        "v": "V18",
        "year": 2025,
        "month": 5,
        "name": "3D Lateral Stability",
        "success": True,
        "metric": 6.0,
        "category": "3d",
    },
    {
        "v": "V19",
        "year": 2025,
        "month": 5,
        "name": "Hip Abduction Active",
        "success": True,
        "metric": 6.3,
        "category": "3d",
    },
    {
        "v": "V20",
        "year": 2025,
        "month": 5,
        "name": "Step Width Control",
        "success": True,
        "metric": 6.5,
        "category": "3d",
    },
    {
        "v": "V21",
        "year": 2025,
        "month": 5,
        "name": "3D Perturbation Test",
        "success": True,
        "metric": 6.8,
        "category": "3d",
    },
    {
        "v": "V22",
        "year": 2025,
        "month": 6,
        "name": "Hardware Design",
        "success": True,
        "metric": 7.0,
        "category": "hardware",
    },
    {
        "v": "V23",
        "year": 2025,
        "month": 6,
        "name": "System ID",
        "success": True,
        "metric": 7.2,
        "category": "hardware",
    },
    {
        "v": "V24",
        "year": 2026,
        "month": 6,
        "name": "Sim-to-Real",
        "success": True,
        "metric": 7.5,
        "category": "hardware",
    },
]

# Category colors
CATEGORY_COLORS = {
    "passive": "#3a3a3a",
    "quasi-passive": "#0c789f",
    "analysis": "#d68b00",
    "control": "#2a7a3b",
    "morphology": "#7c3d8f",
    "actuation": "#b34a36",
    "sensing": "#c97a2d",
    "3d": "#1e5a7a",
    "hardware": "#8b4513",
}


def create_timeline_figure():
    """Create version evolution timeline with metrics."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[2, 1])

    # Convert dates to timeline positions
    start_date = 2024 + 8 / 12  # Sept 2024
    positions = [
        (v["year"] + v["month"] / 12 - start_date) * 12 for v in VERSIONS
    ]  # months from start

    # Top panel: Performance metric progression
    colors = [CATEGORY_COLORS[v["category"]] for v in VERSIONS]
    markers = ["o" if v["success"] else "x" for v in VERSIONS]

    for i, (pos, v, color, marker) in enumerate(
        zip(positions, VERSIONS, colors, markers)
    ):
        size = 80 if v["success"] else 60
        ax1.scatter(
            pos,
            v["metric"],
            s=size,
            c=[color],
            marker=marker,
            edgecolors="white",
            linewidths=1.2,
            zorder=3,
            alpha=0.85,
        )

    # Connect successful versions
    success_pos = [p for p, v in zip(positions, VERSIONS) if v["success"]]
    success_metrics = [v["metric"] for v in VERSIONS if v["success"]]
    ax1.plot(
        success_pos,
        success_metrics,
        "--",
        color="gray",
        alpha=0.3,
        linewidth=1.0,
        zorder=1,
    )

    # Annotate key milestones
    key_versions = ["V05", "V10", "V13", "V18", "V24"]
    for pos, v in zip(positions, VERSIONS):
        if v["v"] in key_versions:
            ax1.annotate(
                v["v"],
                (pos, v["metric"]),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=7,
                fontweight="bold",
            )

    ax1.set_ylabel("Performance Maturity Index", fontsize=10)
    ax1.set_ylim(-0.5, 8.5)
    ax1.set_xlim(-1, max(positions) + 1)
    ax1.set_title(
        "HW-1 Project Version Evolution (V01-V24)", fontsize=12, fontweight="bold"
    )
    ax1.grid(True, alpha=0.3, linewidth=0.5)

    # Bottom panel: Category timeline
    categories = list(CATEGORY_COLORS.keys())
    cat_y = {cat: i for i, cat in enumerate(categories)}

    for pos, v in zip(positions, VERSIONS):
        y = cat_y[v["category"]]
        color = CATEGORY_COLORS[v["category"]]
        marker = "o" if v["success"] else "x"
        ax2.scatter(
            pos,
            y,
            s=50,
            c=[color],
            marker=marker,
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
            alpha=0.85,
        )

    ax2.set_yticks(range(len(categories)))
    ax2.set_yticklabels(categories, fontsize=9)
    ax2.set_xlabel("Timeline (months since Sept 2024)", fontsize=10)
    ax2.set_xlim(-1, max(positions) + 1)
    ax2.grid(True, axis="x", alpha=0.3, linewidth=0.5)

    # Legend
    legend_elements = [
        mpatches.Patch(color=CATEGORY_COLORS[cat], label=cat.capitalize())
        for cat in categories
    ]
    ax2.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=7,
        frameon=True,
        framealpha=0.9,
    )

    plt.tight_layout()

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig1_version_evolution.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig1_version_evolution.svg"


if __name__ == "__main__":
    create_timeline_figure()

"""Hardware Specifications: V22 mechanical design schematic."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def draw_robot_schematic(ax):
    """Draw simplified 2D robot schematic with annotations."""
    # Hip (center mass)
    hip_pos = np.array([0, 1.0])
    hip_mass = patches.Circle(
        hip_pos, 0.08, facecolor="#3a3a3a", edgecolor="black", linewidth=2
    )
    ax.add_patch(hip_mass)
    ax.text(
        hip_pos[0] + 0.15,
        hip_pos[1],
        "Hip\n5.0 kg",
        fontsize=9,
        va="center",
        fontweight="bold",
    )

    # Left leg
    left_hip_angle = np.deg2rad(-25)
    left_knee_angle = np.deg2rad(15)

    thigh_len = 0.49
    shank_len = 0.51

    # Left thigh
    left_thigh_end = hip_pos + thigh_len * np.array(
        [np.sin(left_hip_angle), -np.cos(left_hip_angle)]
    )
    ax.plot(
        [hip_pos[0], left_thigh_end[0]],
        [hip_pos[1], left_thigh_end[1]],
        "o-",
        color="#0c789f",
        linewidth=6,
        markersize=8,
        solid_capstyle="round",
        label="Thigh (0.49 m)",
    )

    # Left knee
    knee_circle = patches.Circle(
        left_thigh_end, 0.05, facecolor="#d68b00", edgecolor="black", linewidth=1.5
    )
    ax.add_patch(knee_circle)

    # Left shank
    shank_angle = left_hip_angle + left_knee_angle
    left_ankle = left_thigh_end + shank_len * np.array(
        [np.sin(shank_angle), -np.cos(shank_angle)]
    )
    ax.plot(
        [left_thigh_end[0], left_ankle[0]],
        [left_thigh_end[1], left_ankle[1]],
        "o-",
        color="#2a7a3b",
        linewidth=6,
        markersize=8,
        solid_capstyle="round",
        label="Shank (0.51 m)",
    )

    # Left foot (arc)
    foot_arc = patches.Arc(
        left_ankle,
        0.12,
        0.08,
        angle=0,
        theta1=180,
        theta2=360,
        color="#8b4513",
        linewidth=5,
    )
    ax.add_patch(foot_arc)

    # Right leg (mirrored, stance phase)
    right_hip_angle = np.deg2rad(15)
    right_knee_angle = np.deg2rad(5)

    # Right thigh
    right_thigh_end = hip_pos + thigh_len * np.array(
        [np.sin(right_hip_angle), -np.cos(right_hip_angle)]
    )
    ax.plot(
        [hip_pos[0], right_thigh_end[0]],
        [hip_pos[1], right_thigh_end[1]],
        "o-",
        color="#0c789f",
        linewidth=6,
        markersize=8,
        solid_capstyle="round",
    )

    # Right knee
    knee_circle2 = patches.Circle(
        right_thigh_end, 0.05, facecolor="#d68b00", edgecolor="black", linewidth=1.5
    )
    ax.add_patch(knee_circle2)

    # Right shank
    shank_angle2 = right_hip_angle + right_knee_angle
    right_ankle = right_thigh_end + shank_len * np.array(
        [np.sin(shank_angle2), -np.cos(shank_angle2)]
    )
    ax.plot(
        [right_thigh_end[0], right_ankle[0]],
        [right_thigh_end[1], right_ankle[1]],
        "o-",
        color="#2a7a3b",
        linewidth=6,
        markersize=8,
        solid_capstyle="round",
    )

    # Right foot
    foot_arc2 = patches.Arc(
        right_ankle,
        0.12,
        0.08,
        angle=0,
        theta1=180,
        theta2=360,
        color="#8b4513",
        linewidth=5,
    )
    ax.add_patch(foot_arc2)

    # Ground line
    ax.axhline(0, color="black", linewidth=2, linestyle="-")
    ax.fill_between([-0.6, 0.6], 0, -0.05, color="0.7", alpha=0.5, hatch="///")

    # Annotations for joints
    ax.annotate(
        "Hip Motor\n(Active)",
        xy=hip_pos,
        xytext=(hip_pos[0] - 0.35, hip_pos[1] + 0.15),
        arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
        fontsize=8,
        color="red",
        fontweight="bold",
    )

    ax.annotate(
        "Knee\n(Active+Spring)",
        xy=left_thigh_end,
        xytext=(left_thigh_end[0] - 0.4, left_thigh_end[1]),
        arrowprops=dict(arrowstyle="->", color="orange", lw=1.5),
        fontsize=8,
        color="orange",
        fontweight="bold",
    )

    ax.annotate(
        "Ankle\n(Passive Spring)",
        xy=left_ankle,
        xytext=(left_ankle[0] - 0.35, left_ankle[1] - 0.15),
        arrowprops=dict(arrowstyle="->", color="brown", lw=1.5),
        fontsize=8,
        color="brown",
        fontweight="bold",
    )


def create_hardware_specs_figure():
    """Create V22 hardware specifications schematic."""
    style_path = Path(__file__).resolve().parents[1] / "styles" / "paper_style.mplstyle"
    plt.style.use(str(style_path))

    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # Panel A: Robot schematic
    ax1 = fig.add_subplot(gs[:, 0])
    draw_robot_schematic(ax1)
    ax1.set_xlim(-0.6, 0.6)
    ax1.set_ylim(-0.1, 1.5)
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.set_title(
        "(A) Robot Mechanical Design",
        fontsize=12,
        fontweight="bold",
        loc="left",
        pad=10,
    )
    ax1.legend(loc="upper right", fontsize=8, framealpha=0.9)

    # Panel B: Mass distribution pie chart
    ax2 = fig.add_subplot(gs[0, 1])
    mass_labels = [
        "Hip Mass\n(5.0 kg)",
        "Thighs\n(0.36 kg)",
        "Shanks\n(0.32 kg)",
        "Feet\n(0.23 kg)",
        "Motors\n(0.54 kg)",
        "Electronics\n(0.30 kg)",
    ]
    mass_values = [5.0, 0.36, 0.32, 0.23, 0.54, 0.30]
    colors_pie = ["#3a3a3a", "#0c789f", "#2a7a3b", "#8b4513", "#d68b00", "#7c3d8f"]

    wedges, texts, autotexts = ax2.pie(
        mass_values,
        labels=mass_labels,
        colors=colors_pie,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 8},
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")
    ax2.set_title(
        "(B) Mass Distribution\n(Total: 6.75 kg)",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )

    # Panel C: Actuator specifications table
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis("off")

    specs_data = [
        ["Component", "Specification", "Value"],
        ["Motor Model", "Dynamixel MX-64AR", "4 units"],
        ["Peak Torque", "Rated / Stall", "6.0 / 7.3 N·m"],
        ["Software Limit", "Safe Operating", "4.0 N·m"],
        ["Encoder Res.", "Position Feedback", "4096 CPR"],
        ["Hip Stiffness", "Active Joint", "Variable"],
        ["Knee Stiffness", "Active + Spring", "0.8 N·m/rad"],
        ["Ankle Stiffness", "Passive Spring", "10.0 N·m/rad"],
        ["Control Freq.", "Main Loop", "1000 Hz"],
        ["Battery", "3S LiPo", "11.1V 2.2Ah"],
        ["Leg Length", "Thigh + Shank", "1.00 m"],
    ]

    table = ax3.table(
        cellText=specs_data, cellLoc="left", loc="center", colWidths=[0.35, 0.40, 0.25]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 2.0)

    # Style header row
    for i in range(3):
        cell = table[(0, i)]
        cell.set_facecolor("#0c789f")
        cell.set_text_props(weight="bold", color="white")

    # Alternate row colors
    for i in range(1, len(specs_data)):
        for j in range(3):
            cell = table[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor("#f0f0f0")
            cell.set_edgecolor("0.8")

    ax3.set_title(
        "(C) Hardware Specifications (V22 Design)",
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=20,
    )

    fig.suptitle(
        "V22 Hardware Design: Mechanical Structure and Specifications",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    # Save in multiple formats
    for fmt in ["svg", "pdf", "png"]:
        out_path = OUTPUT_DIR / f"fig5_hardware_specs.{fmt}"
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {out_path}")

    plt.close(fig)
    return OUTPUT_DIR / "fig5_hardware_specs.svg"


if __name__ == "__main__":
    create_hardware_specs_figure()

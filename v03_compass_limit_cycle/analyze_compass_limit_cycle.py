from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    numeric: dict[str, list[float]] = {}
    text: dict[str, list[str]] = {}
    for row in rows:
        for key, value in row.items():
            try:
                numeric.setdefault(key, []).append(float(value))
            except ValueError:
                text.setdefault(key, []).append(value)
    data: dict[str, np.ndarray] = {
        key: np.array(value) for key, value in numeric.items()
    }
    for key, value in text.items():
        data[key] = np.array(value)
    return data


def main() -> None:
    data = load_csv(OUT_DIR / "compass_limit_cycle_data.csv")
    poincare = load_csv(OUT_DIR / "compass_poincare_points.csv")
    params = json.loads((OUT_DIR / "compass_params.json").read_text(encoding="utf-8"))

    t = data["time"]
    left_omega = np.gradient(data["left_angle"]) / np.gradient(t)
    right_omega = np.gradient(data["right_angle"]) / np.gradient(t)
    support_code = np.where(data["support"] == "left", 1, 2)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(
        "V4 Two-Leg Compass Passive Limit Cycle", fontsize=17, fontweight="bold"
    )

    ax = axes[0, 0]
    ax.plot(
        data["hip_x"],
        data["hip_z"],
        color="#143642",
        linewidth=2.2,
        label="hip trajectory",
    )
    ax.scatter(
        data["left_foot_x"],
        data["left_foot_z"],
        s=4,
        color="#0f7891",
        alpha=0.35,
        label="left foot",
    )
    ax.scatter(
        data["right_foot_x"],
        data["right_foot_z"],
        s=4,
        color="#d45132",
        alpha=0.35,
        label="right foot",
    )
    ax.set_title("Alternating foot contacts")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(
        t,
        np.rad2deg(data["left_angle"]),
        color="#0f7891",
        linewidth=1.5,
        label="left leg angle",
    )
    ax.plot(
        t,
        np.rad2deg(data["right_angle"]),
        color="#d45132",
        linewidth=1.5,
        label="right leg angle",
    )
    ax.step(
        t,
        support_code * 16 - 50,
        where="post",
        color="#62516d",
        alpha=0.75,
        label="support leg",
    )
    ax.set_title("Periodic leg switching")
    ax.set_xlabel("time / s")
    ax.set_ylabel("angle / deg")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    ax.plot(
        data["left_angle"],
        left_omega,
        color="#0f7891",
        linewidth=1.2,
        label="left phase",
    )
    ax.plot(
        data["right_angle"],
        right_omega,
        color="#d45132",
        linewidth=1.2,
        label="right phase",
    )
    ax.set_title("Phase portrait")
    ax.set_xlabel("angle / rad")
    ax.set_ylabel("angular velocity / rad/s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    ax.plot(
        poincare["step"],
        poincare["speed"],
        marker="o",
        color="#143642",
        label="step speed",
    )
    ax.axhline(
        poincare["fixed_speed"][0], color="#d45132", linestyle="--", label="fixed point"
    )
    ax2 = ax.twinx()
    ax2.plot(
        poincare["step"], poincare["error"], marker="s", color="#907f2e", label="error"
    )
    ax.set_title("Poincare convergence")
    ax.set_xlabel("step")
    ax.set_ylabel("speed / m/s")
    ax2.set_ylabel("error")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")

    caption = (
        f"no actuator | slope {params['params']['slope_deg']} deg | "
        f"forward distance {params['forward_distance_m']:.2f} m | "
        f"final error {params['final_error']:.5f}"
    )
    fig.tight_layout(rect=[0.0, 0.07, 1.0, 0.94])
    fig.text(0.5, 0.025, caption, ha="center", fontsize=11)
    fig.savefig(OUT_DIR / "compass_limit_cycle_report.png", dpi=180)
    print(OUT_DIR / "compass_limit_cycle_report.png")


if __name__ == "__main__":
    main()

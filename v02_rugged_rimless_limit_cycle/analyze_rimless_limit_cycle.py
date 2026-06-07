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
    data: dict[str, list[float]] = {}
    for row in rows:
        for key, value in row.items():
            data.setdefault(key, []).append(float(value))
    return {key: np.array(value) for key, value in data.items()}


def main() -> None:
    data = load_csv(OUT_DIR / "rimless_limit_cycle_data.csv")
    poincare = load_csv(OUT_DIR / "rimless_poincare_points.csv")
    params = json.loads((OUT_DIR / "rimless_params.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(
        "V3 Rimless Passive Limit-Cycle Evidence", fontsize=17, fontweight="bold"
    )

    ax = axes[0, 0]
    ax.plot(
        data["hub_x"],
        data["hub_z"],
        color="#143642",
        linewidth=2.0,
        label="hub trajectory",
    )
    ax.scatter(
        data["stance_foot_x"],
        data["stance_foot_z"],
        s=6,
        color="#d45132",
        alpha=0.35,
        label="contact samples",
    )
    ax.set_title("Passive downhill progression")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(
        data["time"],
        np.rad2deg(data["theta"]),
        color="#0f7891",
        linewidth=1.6,
        label="stance spoke angle",
    )
    ax.plot(
        data["time"],
        data["theta_dot"],
        color="#907f2e",
        linewidth=1.5,
        label="angular speed",
    )
    ax.set_title("Continuous stance phase and impact reset")
    ax.set_xlabel("time / s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    ax.plot(data["theta"], data["theta_dot"], color="#62516d", linewidth=1.5)
    ax.scatter(
        data["theta"][::80],
        data["theta_dot"][::80],
        s=15,
        color="#d45132",
        label="Poincare samples",
    )
    ax.set_title("Phase portrait")
    ax.set_xlabel("theta / rad")
    ax.set_ylabel("theta_dot / rad/s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    ax.plot(
        poincare["step"],
        poincare["omega"],
        marker="o",
        color="#143642",
        label="post-impact omega",
    )
    ax.axhline(
        poincare["fixed_omega"][0], color="#d45132", linestyle="--", label="fixed point"
    )
    ax2 = ax.twinx()
    ax2.plot(
        poincare["step"], poincare["error"], marker="s", color="#907f2e", label="error"
    )
    ax.set_title("Poincare map convergence")
    ax.set_xlabel("step")
    ax.set_ylabel("omega / rad/s")
    ax2.set_ylabel("error")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")

    caption = (
        f"no actuator | slope {params['params']['slope_deg']} deg | "
        f"spoke half-angle {params['alpha_deg']:.1f} deg | "
        f"fixed omega {params['fixed_point_omega']:.3f} rad/s | "
        f"final error {params['final_error']:.5f}"
    )
    fig.tight_layout(rect=[0.0, 0.07, 1.0, 0.94])
    fig.text(0.5, 0.025, caption, ha="center", fontsize=11)
    fig.savefig(OUT_DIR / "rimless_poincare_report.png", dpi=180)
    print(OUT_DIR / "rimless_poincare_report.png")


if __name__ == "__main__":
    main()

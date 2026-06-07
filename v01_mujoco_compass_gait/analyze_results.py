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
    contacts: list[str] = []
    for row in rows:
        contacts.append(row["contacts"])
        for key, value in row.items():
            if key == "contacts":
                continue
            numeric.setdefault(key, []).append(float(value))
    data = {key: np.array(value) for key, value in numeric.items()}
    data["contact_code"] = np.array(
        [
            1 if c == "left" else 2 if c == "right" else 3 if "+" in c else 0
            for c in contacts
        ]
    )
    return data


def main() -> None:
    data_path = OUT_DIR / "passive_compass_gait_data.csv"
    params_path = OUT_DIR / "best_params.json"
    data = load_csv(data_path)
    params = json.loads(params_path.read_text(encoding="utf-8"))

    t = data["time"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("Passive Compass Gait MuJoCo Report", fontsize=16, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(data["hip_x"], data["hip_z"], label="hip trajectory", linewidth=2)
    ax.scatter(
        data["left_foot_x"], data["left_foot_z"], s=3, label="left foot", alpha=0.35
    )
    ax.scatter(
        data["right_foot_x"], data["right_foot_z"], s=3, label="right foot", alpha=0.35
    )
    ax.set_title("Trajectory")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(t, np.rad2deg(data["left_angle"]), label="left leg angle", linewidth=1.8)
    ax.plot(t, np.rad2deg(data["right_angle"]), label="right leg angle", linewidth=1.8)
    ax.set_title("Leg Angles")
    ax.set_xlabel("time / s")
    ax.set_ylabel("angle / deg")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[1, 0]
    ax.step(t, data["contact_code"], where="post", linewidth=1.8)
    ax.set_title("Foot Contact Sequence")
    ax.set_xlabel("time / s")
    ax.set_yticks([0, 1, 2, 3], ["none", "left", "right", "both"])
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(data["left_angle"], data["left_omega"], label="left phase", linewidth=1.5)
    ax.plot(
        data["right_angle"], data["right_omega"], label="right phase", linewidth=1.5
    )
    ax.set_title("Phase Portrait")
    ax.set_xlabel("angle / rad")
    ax.set_ylabel("angular velocity / rad/s")
    ax.grid(True, alpha=0.3)
    ax.legend()

    score = params["final_score"]
    caption = (
        f"alternating contacts: {score['alternating_contacts']} | "
        f"forward distance: {score['forward_distance']:.3f} m | "
        f"duration: {score['duration']:.2f} s"
    )
    fig.text(0.5, 0.01, caption, ha="center", fontsize=11)
    fig.savefig(OUT_DIR / "passive_compass_gait_report.png", dpi=180)
    print(OUT_DIR / "passive_compass_gait_report.png")


if __name__ == "__main__":
    main()

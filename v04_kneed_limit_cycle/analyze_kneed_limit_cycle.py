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
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    data = load_csv(OUT_DIR / "kneed_limit_cycle_data.csv")
    transient = load_csv(OUT_DIR / "kneed_limit_cycle_transient_data.csv")
    poincare = load_csv(OUT_DIR / "poincare_points.csv")
    params = json.loads(
        (OUT_DIR / "kneed_limit_cycle_params.json").read_text(encoding="utf-8")
    )

    t = data["time"]
    left_angle = np.rad2deg(data["left_thigh"] + 0.5 * data["left_knee"])
    right_angle = np.rad2deg(data["right_thigh"] + 0.5 * data["right_knee"])
    dt = np.gradient(t)
    left_omega = np.gradient(np.deg2rad(left_angle)) / dt
    right_omega = np.gradient(np.deg2rad(right_angle)) / dt
    support_code = np.where(data["support"] == "left", 1, 2)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("带膝被动动态步行器：极限环步态证据", fontsize=17, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(
        data["hip_x"], data["hip_z"], color="#143642", linewidth=2.2, label="髋部轨迹"
    )
    ax.scatter(
        data["left_foot_x"],
        data["left_foot_z"],
        s=4,
        color="#0f7891",
        alpha=0.35,
        label="左脚",
    )
    ax.scatter(
        data["right_foot_x"],
        data["right_foot_z"],
        s=4,
        color="#d45132",
        alpha=0.35,
        label="右脚",
    )
    ax.set_title("下坡连续行走轨迹")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(t, left_angle, label="左腿等效角", color="#0f7891", linewidth=1.6)
    ax.plot(t, right_angle, label="右腿等效角", color="#d45132", linewidth=1.6)
    ax.step(
        t,
        support_code * 18 - 54,
        where="post",
        color="#62516d",
        alpha=0.65,
        label="支撑腿切换",
    )
    ax.set_title("左右腿周期切换")
    ax.set_xlabel("time / s")
    ax.set_ylabel("angle / deg")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    ax.plot(
        np.deg2rad(left_angle),
        left_omega,
        color="#0f7891",
        linewidth=1.3,
        label="左腿相图",
    )
    ax.plot(
        np.deg2rad(right_angle),
        right_omega,
        color="#d45132",
        linewidth=1.3,
        label="右腿相图",
    )
    ax.set_title("相图：周期闭合环")
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
        label="步间速度",
    )
    ax.axhline(
        poincare["fixed_speed"][0],
        color="#d45132",
        linestyle="--",
        label="极限环固定点",
    )
    ax2 = ax.twinx()
    ax2.plot(
        poincare["step"],
        poincare["error"],
        marker="s",
        color="#907f2e",
        label="收敛误差",
    )
    ax.set_title("Poincare 截面：步间状态收敛")
    ax.set_xlabel("step")
    ax.set_ylabel("speed / m/s")
    ax2.set_ylabel("error")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")

    caption = (
        f"无 actuator | 坡度 {params['params']['slope_deg']} deg | "
        f"交替触地 {params['alternating_contacts']} 步 | "
        f"固定点速度 {params['fixed_point_speed']:.3f} m/s | "
        f"最终 Poincare 误差 {params['final_poincare_error']:.4f}"
    )
    fig.text(0.5, 0.01, caption, ha="center", fontsize=11)
    fig.savefig(OUT_DIR / "kneed_limit_cycle_report.png", dpi=180)
    print(OUT_DIR / "kneed_limit_cycle_report.png")


if __name__ == "__main__":
    main()

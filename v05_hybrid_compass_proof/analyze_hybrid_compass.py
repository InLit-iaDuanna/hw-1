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

    data = load_csv(OUT_DIR / "hybrid_compass_data.csv")
    poincare = load_csv(OUT_DIR / "hybrid_compass_poincare.csv")
    params = json.loads(
        (OUT_DIR / "hybrid_compass_params.json").read_text(encoding="utf-8")
    )

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle(
        "V5 混合动力学指南针步态：Poincare 极限环证明", fontsize=17, fontweight="bold"
    )

    ax = axes[0, 0]
    ax.plot(
        data["hip_x"], data["hip_z"], color="#143642", linewidth=2.0, label="髋部轨迹"
    )
    ax.scatter(
        data["left_foot_x"],
        data["left_foot_z"],
        s=4,
        color="#0f7891",
        alpha=0.3,
        label="左脚轨迹",
    )
    ax.scatter(
        data["right_foot_x"],
        data["right_foot_z"],
        s=4,
        color="#d45132",
        alpha=0.3,
        label="右脚轨迹",
    )
    ax.set_title("连续单支撑 + 离散换腿")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(
        data["time"],
        np.rad2deg(data["theta_stance"]),
        label="支撑腿角",
        color="#143642",
    )
    ax.plot(
        data["time"], np.rad2deg(data["theta_swing"]), label="摆动腿角", color="#d45132"
    )
    event_mask = data["event"] != ""
    ax.scatter(
        data["time"][event_mask],
        np.rad2deg(data["theta_stance"][event_mask]),
        s=18,
        color="#907f2e",
        label="事件截面",
    )
    ax.set_title("触地事件检测")
    ax.set_xlabel("time / s")
    ax.set_ylabel("angle / deg")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    ax.plot(
        data["theta_stance"],
        data["omega_stance"],
        color="#0f7891",
        linewidth=1.4,
        label="支撑相图",
    )
    ax.scatter(
        poincare["theta_stance"],
        poincare["omega_stance"],
        s=25,
        color="#d45132",
        label="Poincare 点",
    )
    ax.set_title("相图与截面")
    ax.set_xlabel("theta / rad")
    ax.set_ylabel("omega / rad/s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    ax.plot(
        poincare["step"],
        poincare["omega_stance"],
        marker="o",
        color="#143642",
        label="碰撞后速度",
    )
    ax.axhline(
        poincare["fixed_speed"][0], linestyle="--", color="#d45132", label="固定点"
    )
    ax2 = ax.twinx()
    ax2.plot(
        poincare["step"],
        poincare["speed_error"],
        marker="s",
        color="#907f2e",
        label="收敛误差",
    )
    ax.set_title("Poincare 映射收敛")
    ax.set_xlabel("step")
    ax.set_ylabel("omega / rad/s")
    ax2.set_ylabel("error")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")

    caption = (
        f"无 actuator / 无奖励函数 | 有效事件 {params['valid_touchdowns']} 次 | "
        f"固定点速度 {params['fixed_speed']:.3f} rad/s | 最终误差 {params['final_speed_error']:.5f}"
    )
    fig.text(0.5, 0.01, caption, ha="center", fontsize=11)
    out = OUT_DIR / "hybrid_compass_poincare_report.png"
    fig.savefig(out, dpi=180)
    print(out)


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def load_rows(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data: dict[str, np.ndarray] = {}
    for key in rows[0].keys():
        try:
            data[key] = np.array([float(row[key]) for row in rows])
        except ValueError:
            continue
    return data


def plot_joint_phase(
    ax,
    data: dict[str, np.ndarray],
    left_q: str,
    left_v: str,
    right_q: str,
    right_v: str,
    title: str,
    xlabel: str,
) -> None:
    ax.plot(data[left_q], data[left_v], lw=1.1, color="#0b7285", label="左侧")
    ax.plot(data[right_q], data[right_v], lw=1.1, color="#c92a2a", label="右侧")
    ax.scatter(data[left_q][0], data[left_v][0], s=35, color="#0b7285", marker="o")
    ax.scatter(data[right_q][0], data[right_v][0], s=35, color="#c92a2a", marker="o")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("角速度 / rad/s")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")


def touchdown_indices(data: dict[str, np.ndarray], key: str) -> np.ndarray:
    contact = data[key] > 0.5
    return np.flatnonzero(np.diff(np.r_[False, contact]) == 1)


def main() -> None:
    data = load_rows(OUT_DIR / "v10_rolling_foot_walk_data.csv")
    summary = json.loads((OUT_DIR / "v10_best_params.json").read_text(encoding="utf-8"))

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("V10 相位图：足踝滚动准被动步态的周期性状态轨迹", fontsize=17)

    plot_joint_phase(
        axes[0, 0],
        data,
        "left_hip",
        "left_hip_vel",
        "right_hip",
        "right_hip_vel",
        "髋关节相图",
        "髋角 / rad",
    )
    plot_joint_phase(
        axes[0, 1],
        data,
        "left_knee",
        "left_knee_vel",
        "right_knee",
        "right_knee_vel",
        "膝关节相图",
        "膝角 / rad",
    )
    plot_joint_phase(
        axes[1, 0],
        data,
        "left_ankle",
        "left_ankle_vel",
        "right_ankle",
        "right_ankle_vel",
        "被动踝关节相图",
        "踝角 / rad",
    )

    ax = axes[1, 1]
    left_td = touchdown_indices(data, "left_contact")
    right_td = touchdown_indices(data, "right_contact")
    ax.plot(
        data["left_hip"],
        data["left_hip_vel"],
        lw=0.9,
        color="#0b7285",
        alpha=0.65,
        label="左髋连续轨迹",
    )
    ax.plot(
        data["right_hip"],
        data["right_hip_vel"],
        lw=0.9,
        color="#c92a2a",
        alpha=0.65,
        label="右髋连续轨迹",
    )
    ax.scatter(
        data["left_hip"][left_td],
        data["left_hip_vel"][left_td],
        s=34,
        color="#0b7285",
        edgecolor="white",
        label="左脚触地点",
    )
    ax.scatter(
        data["right_hip"][right_td],
        data["right_hip_vel"][right_td],
        s=34,
        color="#c92a2a",
        edgecolor="white",
        label="右脚触地点",
    )
    ax.set_title("触地截面点叠加")
    ax.set_xlabel("髋角 / rad")
    ax.set_ylabel("髋角速度 / rad/s")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    note = (
        f"交替触地：{summary['alternating_touchdowns']} 次\n"
        f"仿真时长：{summary['simulated_time']:.2f} s\n"
        f"前进距离：{summary['forward_distance']:.2f} m\n"
        "说明：V10 相图用于展示周期性运动；纯被动极限环证明仍引用 V5。"
    )
    ax.text(
        0.02,
        0.98,
        note,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "0.82"},
    )

    out = OUT_DIR / "v10_phase_portrait.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

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


def contact_rise_count(contact: np.ndarray) -> int:
    return int(np.sum(np.diff(np.r_[False, contact > 0.5]) == 1))


def main() -> None:
    data = load_rows(OUT_DIR / "v10_rolling_foot_walk_data.csv")
    summary = json.loads((OUT_DIR / "v10_best_params.json").read_text(encoding="utf-8"))
    t = data["time"]

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("V10 足踝滚动仿生步态报告", fontsize=17)

    ax = axes[0, 0]
    ax.plot(t, data["hip_x"], lw=1.8, color="#1c7ed6", label="髋部 x")
    ax.set_title("髋部前进轨迹")
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("位置 / m")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.text(
        0.03,
        0.92,
        f"前进 {summary['forward_distance']:.2f} m\n时长 {summary['simulated_time']:.2f} s",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    ax = axes[0, 1]
    ax.step(
        t, data["left_contact"], where="post", lw=1.3, color="#0b7285", label="左脚"
    )
    ax.step(
        t, -data["right_contact"], where="post", lw=1.3, color="#c92a2a", label="右脚"
    )
    ax.set_title("左右脚接触时序")
    ax.set_yticks([-1, 0, 1], ["右脚", "无", "左脚"])
    ax.set_xlabel("时间 / s")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.text(
        0.03,
        0.92,
        f"交替触地 {summary['alternating_touchdowns']} 次\n左 {contact_rise_count(data['left_contact'])} / 右 {contact_rise_count(data['right_contact'])}",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    ax = axes[1, 0]
    ax.plot(t, np.rad2deg(data["left_hip"]), lw=1.0, color="#0b7285", label="左髋")
    ax.plot(t, np.rad2deg(data["right_hip"]), lw=1.0, color="#c92a2a", label="右髋")
    ax.plot(t, np.rad2deg(data["left_ankle"]), lw=1.0, color="#2f9e44", label="左踝")
    ax.plot(t, np.rad2deg(data["right_ankle"]), lw=1.0, color="#f08c00", label="右踝")
    ax.set_title("关节角度变化")
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("角度 / deg")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncol=2)
    ax.text(
        0.03,
        0.92,
        "踝部为被动弹簧/阻尼\n无踝部 actuator",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    ax = axes[1, 1]
    ax.plot(
        data["left_hip"],
        data["left_hip_vel"],
        lw=1.2,
        color="#0b7285",
        label="左髋相轨迹",
    )
    ax.plot(
        data["right_hip"],
        data["right_hip_vel"],
        lw=1.2,
        color="#c92a2a",
        label="右髋相轨迹",
    )
    ax.set_title("相位图")
    ax.set_xlabel("髋角 / rad")
    ax.set_ylabel("髋角速度 / rad/s")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.text(
        0.03,
        0.96,
        "周期性状态轨迹\n纯被动证明引用 V5",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    out = OUT_DIR / "v10_rolling_foot_report.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

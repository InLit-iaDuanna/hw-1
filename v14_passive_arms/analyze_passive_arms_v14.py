"""V14 主分析报告：步态、摆臂相位、CoT、与 V10 对比。"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from common import cost_of_transport, set_style  # noqa: E402

OUT_DIR = ROOT / "out"
PREFIX = "v14_baseline"


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for k in rows[0].keys():
        try:
            out[k] = np.array([float(r[k]) for r in rows])
        except ValueError:
            continue
    return out, rows


def main() -> None:
    data, _rows = load_rows(OUT_DIR / f"{PREFIX}_data.csv")
    summary = json.loads(
        (OUT_DIR / f"{PREFIX}_summary.json").read_text(encoding="utf-8")
    )
    params = summary["params"]
    t = data["time"]

    set_style()
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("V14 被动摆臂版 — 步态与能量报告", fontsize=17)

    ax = axes[0, 0]
    ax.plot(t, data["hip_x"], lw=1.6, color="#1c7ed6", label="髋部 x")
    ax.set_title("髋部前进")
    ax.set_xlabel("t / s")
    ax.set_ylabel("x / m")
    ax.grid(True, alpha=0.3)
    cot = cost_of_transport(
        summary["active_input_energy_j"],
        summary["total_mass_kg"],
        summary["forward_distance"],
    )
    ax.text(
        0.03,
        0.92,
        f"前进 {summary['forward_distance']:.2f} m\n时长 {summary['simulated_time']:.2f} s\nCoT = {cot:.3f}",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    ax = axes[0, 1]
    ax.plot(t, np.rad2deg(data["left_arm"]), lw=1.4, color="#2b8a8a", label="左臂")
    ax.plot(t, np.rad2deg(data["right_arm"]), lw=1.4, color="#c2654d", label="右臂")
    ax.plot(
        t,
        np.rad2deg(data["left_hip"]),
        lw=0.9,
        color="#0b7285",
        ls="--",
        alpha=0.6,
        label="左髋",
    )
    ax.plot(
        t,
        np.rad2deg(data["right_hip"]),
        lw=0.9,
        color="#c92a2a",
        ls="--",
        alpha=0.6,
        label="右髋",
    )
    ax.set_title("摆臂 vs 髋角（被动反相位检验）")
    ax.set_xlabel("t / s")
    ax.set_ylabel("角度 / deg")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2, loc="best")

    ax = axes[1, 0]
    ax.step(
        t, data["left_contact"], where="post", lw=1.3, color="#0b7285", label="左脚"
    )
    ax.step(
        t, -data["right_contact"], where="post", lw=1.3, color="#c92a2a", label="右脚"
    )
    ax.set_title("左右脚接触")
    ax.set_yticks([-1, 0, 1], ["右脚", "无", "左脚"])
    ax.set_xlabel("t / s")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[1, 1]
    ax.plot(
        data["left_arm"],
        data["left_arm_vel"],
        lw=1.0,
        color="#2b8a8a",
        label="左臂相轨迹",
    )
    ax.plot(
        data["right_arm"],
        data["right_arm_vel"],
        lw=1.0,
        color="#c2654d",
        label="右臂相轨迹",
    )
    ax.set_title("摆臂相图")
    ax.set_xlabel("臂角 / rad")
    ax.set_ylabel("臂角速度 / rad/s")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.text(
        0.03,
        0.96,
        f"摆臂质量 {params['arm_mass']:.2f} kg\n长度 {params['arm_length']:.2f} m\n阻尼 {params['arm_damping']:.3f}\n弹簧 {params['arm_stiffness']:.2f}",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )

    out = OUT_DIR / f"{PREFIX}_report.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

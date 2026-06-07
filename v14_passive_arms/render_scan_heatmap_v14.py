"""V14 扫描热图：在 (arm_mass, arm_length) 平面把 success/failure/score 可视化。"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from common import set_style  # noqa: E402

OUT_DIR = ROOT / "out"


def main() -> None:
    with (OUT_DIR / "v14_arm_scan.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    summary = json.loads(
        (OUT_DIR / "v14_arm_scan_summary.json").read_text(encoding="utf-8")
    )
    masses = sorted({float(r["arm_mass"]) for r in rows})
    lengths = sorted({float(r["arm_length"]) for r in rows})

    grid_success = np.zeros((len(masses), len(lengths)))
    grid_fwd = np.zeros_like(grid_success)
    grid_fail = np.empty(grid_success.shape, dtype=object)
    for r in rows:
        i = masses.index(float(r["arm_mass"]))
        j = lengths.index(float(r["arm_length"]))
        grid_success[i, j] = 1.0 if r["success"] == "True" else 0.0
        grid_fwd[i, j] = float(r["forward_distance"])
        grid_fail[i, j] = r["failure"]

    set_style()
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), constrained_layout=True)
    fig.suptitle(
        f"V14 摆臂扫描：成功 {summary['n_success']}/{summary['n_total']} = {summary['success_rate']:.1%}（V10 控制律孤立点验证）",
        fontsize=15,
    )

    ax = axes[0]
    im = ax.imshow(
        grid_success,
        origin="lower",
        aspect="auto",
        cmap="RdYlGn",
        extent=[
            lengths[0] - 0.05,
            lengths[-1] + 0.05,
            masses[0] - 0.02,
            masses[-1] + 0.02,
        ],
        vmin=0,
        vmax=1,
    )
    ax.set_xticks(lengths)
    ax.set_yticks(masses)
    ax.set_xlabel("arm_length / m")
    ax.set_ylabel("arm_mass / kg")
    ax.set_title("成功（绿）/ 失败（红）")
    for i, m in enumerate(masses):
        for j, l in enumerate(lengths):
            ax.text(
                l,
                m,
                grid_fail[i, j]
                .replace("completed", "OK")
                .replace("fall_down", "fall")
                .replace("nan_or_unstable", "nan"),
                ha="center",
                va="center",
                fontsize=7,
                color="black",
            )
    fig.colorbar(im, ax=ax)

    ax = axes[1]
    im = ax.imshow(
        grid_fwd,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=[
            lengths[0] - 0.05,
            lengths[-1] + 0.05,
            masses[0] - 0.02,
            masses[-1] + 0.02,
        ],
    )
    ax.set_xticks(lengths)
    ax.set_yticks(masses)
    ax.set_xlabel("arm_length / m")
    ax.set_ylabel("arm_mass / kg")
    ax.set_title("前进距离 / m")
    fig.colorbar(im, ax=ax)

    out = OUT_DIR / "v14_arm_scan_heatmap.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

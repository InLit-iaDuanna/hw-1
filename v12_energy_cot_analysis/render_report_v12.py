"""V12 报告图：把已有四张子图拼成一张总览。"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import set_style  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    set_style()
    panels = [
        ("v12_mechanical_energy.png", "机械能时序（hip 平动近似）"),
        ("v12_collision_loss_per_step.png", "每步能量跳变"),
        ("v12_cot_comparison.png", "CoT 对比"),
        ("v12_floquet_spectrum.png", "Floquet 乘子谱"),
        ("v12_poincare_convergence.png", "Poincaré 收敛"),
    ]
    paths = [(OUT / n, t) for n, t in panels]
    missing = [p for p, _ in paths if not p.exists()]
    if missing:
        print("缺图，先跑 analyze_*：", missing)
        return

    fig = plt.figure(figsize=(15, 13))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.2, 1, 1])
    ax_energy = fig.add_subplot(gs[0, :])
    axes = [
        ax_energy,
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[2, 0]),
        fig.add_subplot(gs[2, 1]),
    ]
    for ax, (p, title) in zip(axes, paths):
        ax.imshow(mpimg.imread(p))
        ax.set_title(title, fontsize=12)
        ax.axis("off")
    fig.suptitle("V12 V07-V11 能量 / CoT / Floquet 横向对比报告", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_path = OUT / "v12_report.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()

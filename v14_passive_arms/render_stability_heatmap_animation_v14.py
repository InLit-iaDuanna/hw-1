"""V14 扫描热图动画：逐格显示 (arm_mass, arm_length) 扫描过程。"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
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

    # 构建网格
    grid_success = np.full((len(masses), len(lengths)), np.nan)
    grid_fwd = np.full_like(grid_success, np.nan)
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

    frames = []
    total = len(rows)

    for frame_idx in range(total + 30):  # 额外30帧保持最终状态
        current_idx = min(frame_idx, total - 1)

        # 创建当前帧的网格（只显示到当前索引）
        grid_success_partial = np.full((len(masses), len(lengths)), np.nan)
        grid_fwd_partial = np.full_like(grid_success_partial, np.nan)
        grid_fail_partial = np.empty(grid_success_partial.shape, dtype=object)

        for idx, r in enumerate(rows[: current_idx + 1]):
            i = masses.index(float(r["arm_mass"]))
            j = lengths.index(float(r["arm_length"]))
            grid_success_partial[i, j] = 1.0 if r["success"] == "True" else 0.0
            grid_fwd_partial[i, j] = float(r["forward_distance"])
            grid_fail_partial[i, j] = r["failure"]

        # 绘制当前帧
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), constrained_layout=True)
        fig.suptitle(
            f"V14 摆臂扫描 [{current_idx + 1}/{total}]：成功 {summary['n_success']}/{summary['n_total']} = {summary['success_rate']:.1%}",
            fontsize=15,
        )

        # 左图：成功/失败
        ax = axes[0]
        im = ax.imshow(
            grid_success_partial,
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
                if not np.isnan(grid_success_partial[i, j]):
                    ax.text(
                        l,
                        m,
                        grid_fail_partial[i, j]
                        .replace("completed", "OK")
                        .replace("fall_down", "fall")
                        .replace("nan_or_unstable", "nan"),
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="black",
                    )
        fig.colorbar(im, ax=ax)

        # 右图：前进距离
        ax = axes[1]
        im = ax.imshow(
            grid_fwd_partial,
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

        # 转换为图像
        fig.canvas.draw()
        # 使用 buffer_rgba() 代替已弃用的 tostring_rgb()
        buf = fig.canvas.buffer_rgba()
        frame = np.asarray(buf)
        # 去掉 alpha 通道，只保留 RGB
        frame = frame[:, :, :3]
        frames.append(frame)
        plt.close(fig)

    # 保存动画
    out = OUT_DIR / "v14_stability_heatmap.mp4"
    imageio.mimsave(out, frames, fps=10)
    print(f"已生成热力图动画: {out}")


if __name__ == "__main__":
    main()

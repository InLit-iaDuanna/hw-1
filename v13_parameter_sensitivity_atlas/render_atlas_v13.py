"""V13 渲染：四张 slice 各画两张热图（success / CoT），最后拼成 v13_atlas_report.png。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"

SLICES = [
    "A_slope_foot",
    "B_slope_leg",
    "C_foot_leg",
    "D_slope_torso",
    "E_hip_gains",
    "F_kp_ratio",
    "G_kp_torque",
]


def grid_from_csv(name: str):
    import csv

    meta = json.loads((OUT_DIR / f"v13_{name}_meta.json").read_text(encoding="utf-8"))
    with (OUT_DIR / f"v13_{name}.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    g = meta["grid"]
    success = np.zeros((g, g), dtype=float)
    touchdowns = np.zeros((g, g), dtype=float)
    cot = np.full((g, g), np.nan, dtype=float)
    xs = np.zeros(g)
    ys = np.zeros(g)
    for r in rows:
        ix = int(r["ix"])
        iy = int(r["iy"])
        success[iy, ix] = 1.0 if r["success"] in ("True", "true", True) else 0.0
        try:
            touchdowns[iy, ix] = float(r["alternating_touchdowns"])
        except (TypeError, ValueError):
            pass
        try:
            cv = float(r.get("cot", "nan"))
            if cv == cv:
                cot[iy, ix] = cv
        except (TypeError, ValueError):
            pass
        xkey = meta["x"][0] + "_x"
        ykey = meta["y"][0] + "_y"
        xs[ix] = float(r[xkey])
        ys[iy] = float(r[ykey])
    return meta, xs, ys, success, touchdowns, cot


def plot_slice(ax_success, ax_cot, name: str) -> None:
    meta, xs, ys, success, touchdowns, cot = grid_from_csv(name)
    extent = [xs.min(), xs.max(), ys.min(), ys.max()]
    aspect = "auto"

    im1 = ax_success.imshow(
        success,
        origin="lower",
        extent=extent,
        aspect=aspect,
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
    )
    ax_success.set_title(f"{name}: success")
    ax_success.set_xlabel(meta["x"][0])
    ax_success.set_ylabel(meta["y"][0])
    plt.colorbar(im1, ax=ax_success, fraction=0.046)

    cot_disp = np.where(success > 0.5, cot, np.nan)
    im2 = ax_cot.imshow(
        cot_disp, origin="lower", extent=extent, aspect=aspect, cmap="viridis"
    )
    ax_cot.set_title(f"{name}: CoT (success only)")
    ax_cot.set_xlabel(meta["x"][0])
    ax_cot.set_ylabel(meta["y"][0])
    plt.colorbar(im2, ax=ax_cot, fraction=0.046)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    available = [n for n in SLICES if (OUT_DIR / f"v13_{n}_meta.json").exists()]
    if not available:
        print("no slices to render")
        return

    fig, axes = plt.subplots(len(available), 2, figsize=(11, 4 * len(available)))
    if len(available) == 1:
        axes = np.array([axes])
    for i, name in enumerate(available):
        plot_slice(axes[i, 0], axes[i, 1], name)
    fig.suptitle("V13 Parameter Sensitivity Atlas (quasi-passive, V10 base)")
    fig.tight_layout()
    out = OUT_DIR / "v13_atlas_report.png"
    fig.savefig(out, dpi=140)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

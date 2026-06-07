"""V11 分析与报告生成：盆地热图、失败模式分布、Poincaré 漂移、相位噪声灵敏度。"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulate_rugged_gait_v11 import (  # noqa: E402
    OUT_DIR,
    RuggedScenario,
    load_v10_best_params,
    run_rugged_simulation,
)

from common.plot_styles import PALETTE, plt, set_style  # noqa: E402
from common.poincare import collect_section  # noqa: E402

set_style()

FAIL_COLORS = {
    "completed": PALETTE["ok"],
    "fall_down": PALETTE["fail"],
    "stuck": PALETTE["warn"],
    "penetration": "#7a3b8c",
    "fly_away": "#4a4a4a",
    "nan_or_unstable": "#000000",
}


def plot_basin(ax, grid: np.lib.npyio.NpzFile) -> None:
    amp = grid["amp_grid"] * 1000.0  # mm
    imp = grid["impulse_grid"]
    succ = grid["success_rate"]
    pcm = ax.pcolormesh(imp, amp, succ, cmap="RdYlGn", vmin=0, vmax=1, shading="auto")
    ax.set_xlabel("脉冲幅值 (N)")
    ax.set_ylabel("地形振幅 (mm)")
    ax.set_title("(a) 稳定盆地热图：成功率")
    plt.colorbar(pcm, ax=ax, label="成功率")


def plot_failure_distribution(ax, csv_path: Path) -> None:
    """按地形振幅分组堆叠失败模式柱状图。"""
    by_amp: dict[float, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            amp_mm = round(float(row["amplitude_m"]) * 1000.0, 1)
            by_amp[amp_mm][row["failure"]] += 1
    amps_sorted = sorted(by_amp.keys())
    fail_keys = [
        "completed",
        "fall_down",
        "stuck",
        "penetration",
        "fly_away",
        "nan_or_unstable",
    ]
    bottom = np.zeros(len(amps_sorted))
    width = (amps_sorted[1] - amps_sorted[0]) * 0.8 if len(amps_sorted) > 1 else 1.0
    for fk in fail_keys:
        counts = np.array([by_amp[a].get(fk, 0) for a in amps_sorted], dtype=float)
        if counts.sum() == 0:
            continue
        ax.bar(
            amps_sorted,
            counts,
            width=width,
            bottom=bottom,
            label=fk,
            color=FAIL_COLORS.get(fk, "#888"),
        )
        bottom += counts
    ax.set_xlabel("地形振幅 (mm)")
    ax.set_ylabel("仿真次数")
    ax.set_title("(b) 失败模式分布（按地形振幅聚合）")
    ax.legend(fontsize=8, ncol=2)


def plot_poincare_drift(ax) -> None:
    """对 3 个代表性场景采集 Poincaré 截面点：平地、中等地形、大地形。"""
    base = load_v10_best_params()
    scenarios = [
        ("平地", RuggedScenario(terrain_amplitude_m=0.0)),
        ("地形 10 mm", RuggedScenario(terrain_amplitude_m=0.010, terrain_seed=1)),
        ("地形 25 mm", RuggedScenario(terrain_amplitude_m=0.025, terrain_seed=1)),
    ]
    colors = [PALETTE["ok"], PALETTE["warn"], PALETTE["fail"]]
    for (label, sc), color in zip(scenarios, colors):
        params = base.__class__(**{**asdict(base), "duration": 12.0})
        rows, _ = run_rugged_simulation(params, sc, save_prefix=None)
        pts = collect_section(rows, ("left_hip", "left_hip_vel"))
        if pts.size > 0:
            ax.scatter(pts[:, 0], pts[:, 1], s=30, alpha=0.75, label=label, color=color)
            ax.plot(pts[:, 0], pts[:, 1], "-", lw=0.6, alpha=0.3, color=color)
    ax.set_xlabel("左髋角 (rad)")
    ax.set_ylabel("左髋角速度 (rad/s)")
    ax.set_title("(c) Poincaré 截面：触地切换处")
    ax.legend()


def plot_touchdown_intervals(ax) -> None:
    """触地事件间隔时序对比：平地 vs 崎岖。"""
    base = load_v10_best_params()
    scenarios = [
        ("平地", RuggedScenario(terrain_amplitude_m=0.0), PALETTE["ok"]),
        (
            "崎岖 20 mm",
            RuggedScenario(terrain_amplitude_m=0.020, terrain_seed=2),
            PALETTE["fail"],
        ),
    ]
    for label, sc, color in scenarios:
        params = base.__class__(**{**asdict(base), "duration": 12.0})
        _, summary = run_rugged_simulation(params, sc, save_prefix=None)
        events = [e["time"] for e in summary["contact_events"]]
        if len(events) < 2:
            continue
        intervals = np.diff(events)
        ax.plot(range(1, len(intervals) + 1), intervals, "o-", label=label, color=color)
    ax.axhline(0.6, ls="--", color="#888", lw=0.8, label="V10 名义周期 ≈ 0.6 s")
    ax.set_xlabel("第 n 次触地")
    ax.set_ylabel("相邻触地间隔 (s)")
    ax.set_title("(d) 触地间隔对比")
    ax.legend()


def plot_phase_noise(ax, sweep_path: Path) -> None:
    if not sweep_path.exists():
        ax.text(
            0.5,
            0.5,
            "v11_phase_noise_sweep.json 未生成",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        return
    data = json.loads(sweep_path.read_text(encoding="utf-8"))
    sig = [d["sigma_s"] * 1000.0 for d in data]
    succ = [d["success_rate"] for d in data]
    td = [d["mean_touchdowns"] for d in data]
    ax.plot(sig, succ, "o-", color=PALETTE["fail"], label="成功率")
    ax2 = ax.twinx()
    ax2.plot(sig, td, "s--", color=PALETTE["left"], label="平均触地次数", alpha=0.7)
    ax.set_xlabel("触地相位噪声 σ (ms)")
    ax.set_ylabel("成功率", color=PALETTE["fail"])
    ax2.set_ylabel("平均触地次数", color=PALETTE["left"])
    ax.set_title("一维灵敏度：触地相位噪声")
    ax.set_ylim(-0.05, 1.05)


def main() -> None:
    grid_path = OUT_DIR / "v11_basin_grid.npz"
    csv_path = OUT_DIR / "v11_basin_results.csv"
    sweep_path = OUT_DIR / "v11_phase_noise_sweep.json"

    fig = plt.figure(figsize=(15.5, 11), constrained_layout=True)
    gs = fig.add_gridspec(3, 2)
    ax_basin = fig.add_subplot(gs[0, 0])
    ax_fail = fig.add_subplot(gs[0, 1])
    ax_poin = fig.add_subplot(gs[1, 0])
    ax_td = fig.add_subplot(gs[1, 1])
    ax_phn = fig.add_subplot(gs[2, :])

    if grid_path.exists():
        plot_basin(ax_basin, np.load(grid_path))
    else:
        ax_basin.text(
            0.5,
            0.5,
            "v11_basin_grid.npz 未生成\n先跑 scan_robustness_basin_v11.py",
            ha="center",
            va="center",
            transform=ax_basin.transAxes,
        )
    if csv_path.exists():
        plot_failure_distribution(ax_fail, csv_path)
    else:
        ax_fail.text(
            0.5,
            0.5,
            "v11_basin_results.csv 未生成",
            ha="center",
            va="center",
            transform=ax_fail.transAxes,
        )
    plot_poincare_drift(ax_poin)
    plot_touchdown_intervals(ax_td)
    plot_phase_noise(ax_phn, sweep_path)

    fig.suptitle(
        "V11 鲁棒性 / 敏感性分析报告（准被动 V10 基础上加扰动）",
        fontsize=15,
        fontweight="bold",
    )
    out_png = OUT_DIR / "v11_robustness_report.png"
    fig.savefig(out_png)
    print(out_png)


if __name__ == "__main__":
    main()

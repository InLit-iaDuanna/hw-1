"""V13.6 切片 C 复扫：foot_radius x leg_scale 6x6（与 V13 / plan C 同栅格）。

主交付：在 V13 切片 C 同栅格跑 V13.6 FSM 控制律，
直接对比成功率（V13 V10=16.7%，plan C=0%，V13.6=?）。

输出：
  out/v13_6_C_foot_leg.csv          — 36 点扫描结果
  out/v13_6_C_foot_leg_meta.json    — 元数据
  out/v13_6_C_heatmap.png           — 6x6 热图（success / touchdowns / failure mode）
  out/v13_6_vs_v10_planC.json       — 三列横向对比表
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(ROOT))

from simulate_v13_6 import V136Params, _baseline_v10, run_simulation  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

OUT_DIR = ROOT / "out"


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def make_v136_geom(foot_radius: float, leg_scale: float, duration: float) -> V136Params:
    base = _baseline_v10()
    base = replace(
        base,
        foot_radius=float(foot_radius),
        thigh_length=float(base.thigh_length * leg_scale),
        shank_length=float(base.shank_length * leg_scale),
        step_length=float(base.step_length * leg_scale),
        duration=duration,
    )
    return V136Params(base=base)


def evaluate(params: V136Params, sample_hz: float = 40.0) -> dict:
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    p = params.base
    mass = p.hip_mass + 2 * p.torso_mass
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], mass, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    return {
        **asdict(p),
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "failure": str(summary["failure"]),
        "cot": float(cot),
        "score": float(summary["score"]),
        "phase_transitions": int(summary["phase_transitions"]),
    }


def run_slice_C(grid: int, duration: float) -> tuple[Path, list[dict]]:
    name = "C_foot_leg"
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    rows: list[dict] = []
    t0 = time.time()
    total = grid * grid
    print(f"[v13_6.{name}] grid={grid}x{grid} = {total} pts, duration={duration}s/pt")

    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            params = make_v136_geom(foot_radius=xv, leg_scale=yv, duration=duration)
            try:
                r = evaluate(params)
            except Exception as exc:  # noqa: BLE001
                r = {
                    "success": False,
                    "failure": f"exception:{exc.__class__.__name__}",
                    "cot": float("nan"),
                    "alternating_touchdowns": 0,
                    "forward_distance": 0.0,
                    "simulated_time": 0.0,
                    "active_input_energy_j": 0.0,
                    "score": -1e6,
                    "phase_transitions": 0,
                }
            r["slice"] = "v13_6_" + name
            r["ix"] = ix
            r["iy"] = iy
            r["foot_radius_x"] = xv
            r["leg_scale_y"] = yv
            rows.append(r)
            elapsed = time.time() - t0
            done = ix * grid + iy + 1
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] foot_radius={xv:.3f} leg_scale={yv:.3f} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"fail={r['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
            )

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / f"v13_6_{name}.csv"
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    meta = {
        "slice": "v13_6_" + name,
        "grid": grid,
        "duration": duration,
        "x": ("foot_radius", 0.030, 0.050),
        "y": ("leg_scale", 0.90, 1.10),
        "title": "[V13.6 FSM] foot_radius vs leg_scale",
    }
    (OUT_DIR / f"v13_6_{name}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[v13_6.{name}] -> {csv_path}")
    return csv_path, rows


def plot_heatmap(rows: list[dict], grid: int, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    succ = np.zeros((grid, grid))
    td = np.zeros((grid, grid))
    fail_mode = np.full((grid, grid), "", dtype=object)
    for r in rows:
        succ[r["ix"], r["iy"]] = 1.0 if r["success"] else 0.0
        td[r["ix"], r["iy"]] = r["alternating_touchdowns"]
        fail_mode[r["ix"], r["iy"]] = r["failure"]
    xs = sorted({r["foot_radius_x"] for r in rows})
    ys = sorted({r["leg_scale_y"] for r in rows})

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    ax = axes[0]
    im = ax.imshow(
        succ.T,
        origin="lower",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        aspect="auto",
        extent=[xs[0], xs[-1], ys[0], ys[-1]],
    )
    ax.set_xlabel("foot_radius (m)")
    ax.set_ylabel("leg_scale")
    ax.set_title(
        f"[V13.6] Success (green) / Fail (red)\n"
        f"rate = {int(succ.sum())}/{grid*grid} = {succ.sum()/(grid*grid)*100:.1f}%"
    )
    plt.colorbar(im, ax=ax)

    ax = axes[1]
    im2 = ax.imshow(
        td.T,
        origin="lower",
        cmap="viridis",
        aspect="auto",
        extent=[xs[0], xs[-1], ys[0], ys[-1]],
    )
    ax.set_xlabel("foot_radius (m)")
    ax.set_ylabel("leg_scale")
    ax.set_title("[V13.6] alternating touchdowns (12 = success threshold ~)")
    plt.colorbar(im2, ax=ax)

    fig.suptitle("V13.6 FSM hip control — V13 slice C re-scan (6x6)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[v13_6.heatmap] -> {out_path}")


def write_comparison(rows_C: list[dict]) -> Path:
    n = len(rows_C)
    succ = sum(1 for r in rows_C if r["success"])
    rate = succ / max(1, n) * 100.0
    succ_cells = [
        (round(r["foot_radius_x"], 3), round(r["leg_scale_y"], 3))
        for r in rows_C
        if r["success"]
    ]
    fail_counter = Counter(r["failure"] for r in rows_C)
    v10_rate = 16.7  # 6/36
    planC_rate = 0.0  # 0/36
    out = {
        "slice": "C_foot_leg",
        "grid": 6,
        "n_total": n,
        "v10_baseline": {"rate_pct": v10_rate, "succ_n": 6},
        "v13_5_planC": {"rate_pct": planC_rate, "succ_n": 0},
        "v13_6_fsm": {
            "rate_pct": rate,
            "succ_n": succ,
            "success_cells": succ_cells,
            "failure_distribution": dict(fail_counter),
        },
        "delta_vs_v10_pp": rate - v10_rate,
        "delta_vs_planC_pp": rate - planC_rate,
        "verdict": (
            "tier_A_>=v10"
            if rate >= 16.7
            else "tier_B_partial" if rate > 5.0 else "tier_C_failed"
        ),
    }
    path = OUT_DIR / "v13_6_vs_v10_planC.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[v13_6.compare] -> {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    args = parser.parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    _, rows = run_slice_C(args.grid, args.duration)
    plot_heatmap(rows, args.grid, OUT_DIR / "v13_6_C_heatmap.png")
    summary_path = write_comparison(rows)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rate = summary["v13_6_fsm"]["rate_pct"]
    n = summary["v13_6_fsm"]["succ_n"]
    fd = summary["v13_6_fsm"]["failure_distribution"]
    print("=" * 70)
    print(
        f"DECISION: V13.6 FSM = {n}/36 = {rate:.1f}% "
        f"(vs V10 16.7%, plan C 0.0%) -> {summary['verdict']}"
    )
    print(f"failure dist: {fd}")
    print("=" * 70)


if __name__ == "__main__":
    main()

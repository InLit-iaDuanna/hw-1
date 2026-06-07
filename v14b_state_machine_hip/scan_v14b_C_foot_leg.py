"""V14b x V13 slice-C geometry scan.

This keeps the V14b critical arm setting fixed at arm_mass=0.05 kg and
arm_length=0.40 m, then rescans the V13 foot_radius x leg_scale slice.
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v136 import (
    OUT_DIR,
    PassiveArmsParams,
    make_v14b_params,
    run_simulation,
)  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

ARM_MASS = 0.05
ARM_LENGTH = 0.40
V10_SUCCESS_CELLS = {
    # From v13_parameter_sensitivity_atlas/out/v13_C_foot_leg.csv.
    (0.034, 0.900),
    (0.038, 0.900),
    (0.038, 0.940),
    (0.038, 0.980),
    (0.046, 1.060),
    (0.046, 1.100),
}
V136_SUCCESS_CELLS = {
    # From v13_6_event_driven_fsm/out/v13_6_vs_v10_planC.json.
    (0.038, 1.020),
    (0.042, 0.980),
    (0.042, 1.020),
    (0.042, 1.060),
}


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def cell(x: float, y: float) -> tuple[float, float]:
    return (round(float(x), 3), round(float(y), 3))


def make_v14b_geom(foot_radius: float, leg_scale: float, duration: float):
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        foot_radius=float(foot_radius),
        thigh_length=float(base0.thigh_length * leg_scale),
        shank_length=float(base0.shank_length * leg_scale),
        step_length=float(base0.step_length * leg_scale),
        arm_mass=ARM_MASS,
        arm_length=ARM_LENGTH,
        arm_damping=0.02,
        arm_stiffness=0.0,
        duration=duration,
    )
    return make_v14b_params(base)


def evaluate(params, sample_hz: float) -> dict:
    _, summary = run_simulation(params, sample_hz=sample_hz)
    p = params.base
    mass = p.total_mass
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


def run_slice_C(grid: int, duration: float, sample_hz: float) -> list[dict]:
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    rows: list[dict] = []
    total = grid * grid
    t0 = time.time()
    print(
        f"[v14b.C_foot_leg] grid={grid}x{grid}={total}, duration={duration}s, "
        f"arm_mass={ARM_MASS}, arm_length={ARM_LENGTH}"
    )
    for ix, foot_radius in enumerate(xs):
        for iy, leg_scale in enumerate(ys):
            params = make_v14b_geom(foot_radius, leg_scale, duration)
            try:
                row = evaluate(params, sample_hz=sample_hz)
            except Exception as exc:  # noqa: BLE001
                row = {
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
            row["slice"] = "v14b_C_foot_leg"
            row["ix"] = ix
            row["iy"] = iy
            row["foot_radius_x"] = foot_radius
            row["leg_scale_y"] = leg_scale
            rows.append(row)
            done = ix * grid + iy + 1
            elapsed = time.time() - t0
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] foot_radius={foot_radius:.3f} leg_scale={leg_scale:.3f} "
                f"success={row['success']} td={row['alternating_touchdowns']} "
                f"fail={row['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
            )
    return rows


def write_csv(rows: list[dict]) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "v14b_C_foot_leg.csv"
    priority = [
        "slice",
        "ix",
        "iy",
        "foot_radius_x",
        "leg_scale_y",
        "success",
        "alternating_touchdowns",
        "forward_distance",
        "simulated_time",
        "failure",
        "score",
        "active_input_energy_j",
        "phase_transitions",
        "arm_mass",
        "arm_length",
    ]
    keys = priority + sorted(
        {key for row in rows for key in row.keys()} - set(priority)
    )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[v14b.C_foot_leg] -> {path}")
    return path


def plot_heatmap(rows: list[dict], grid: int) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    succ = np.zeros((grid, grid))
    td = np.zeros((grid, grid))
    for row in rows:
        succ[int(row["ix"]), int(row["iy"])] = 1.0 if row["success"] else 0.0
        td[int(row["ix"]), int(row["iy"])] = float(row["alternating_touchdowns"])
    xs = sorted({float(row["foot_radius_x"]) for row in rows})
    ys = sorted({float(row["leg_scale_y"]) for row in rows})

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
        f"[V14b] Success (green) / Fail (red)\n"
        f"rate = {int(succ.sum())}/{grid * grid} = {succ.sum() / (grid * grid) * 100:.1f}%"
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
    ax.set_title("[V14b] alternating touchdowns")
    plt.colorbar(im2, ax=ax)

    fig.suptitle("V14b FSM + passive arms - V13 slice C re-scan (6x6)", fontsize=12)
    fig.tight_layout()
    out = OUT_DIR / "v14b_C_heatmap.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"[v14b.heatmap] -> {out}")
    return out


def verdict_for(success_n: int, total: int) -> str:
    rate = success_n / max(1, total) * 100.0
    if rate >= 17.0:
        return "tier_A_pass_geometry_and_arm_dims_v15_ready"
    if success_n >= 4:
        return "tier_B_pass_section_3_1_wait_v13_6_1_best_for_v15_baseline"
    return "tier_C_failed_geometry_edge_arm_destabilization"


def write_comparison(rows: list[dict]) -> Path:
    total = len(rows)
    success_cells = {
        cell(row["foot_radius_x"], row["leg_scale_y"]) for row in rows if row["success"]
    }
    success_n = len(success_cells)
    rate = success_n / max(1, total) * 100.0
    fail_counter = Counter(str(row["failure"]) for row in rows)
    overlap_v10 = sorted(success_cells & V10_SUCCESS_CELLS)
    overlap_v136 = sorted(success_cells & V136_SUCCESS_CELLS)
    v14b_only = sorted(success_cells - V10_SUCCESS_CELLS - V136_SUCCESS_CELLS)
    out = {
        "slice": "C_foot_leg",
        "grid": 6,
        "n_total": total,
        "arm_params_fixed": {"arm_mass": ARM_MASS, "arm_length": ARM_LENGTH},
        "v10_pd": {
            "succ_n": 6,
            "n_total": 36,
            "rate_pct": 16.7,
            "success_cells": sorted(V10_SUCCESS_CELLS),
        },
        "v13_6_fsm": {
            "succ_n": 4,
            "n_total": 36,
            "rate_pct": 11.1,
            "success_cells": sorted(V136_SUCCESS_CELLS),
        },
        "v14b_fsm_passive_arms": {
            "succ_n": success_n,
            "n_total": total,
            "rate_pct": rate,
            "success_cells": sorted(success_cells),
            "failure_distribution": dict(fail_counter),
        },
        "overlap": {
            "with_v10_pd": overlap_v10,
            "with_v13_6_fsm": overlap_v136,
            "v14b_only": v14b_only,
            "overlaps_v10": bool(overlap_v10),
            "overlaps_v13_6": bool(overlap_v136),
        },
        "delta_vs_v10_pp": rate - 16.7,
        "delta_vs_v13_6_pp": rate - 11.1,
        "verdict": verdict_for(success_n, total),
        "verdict_rules": {
            ">=17pct": "V14b passes geometry + arm dimensions; V15 may proceed.",
            "11_to_17pct": "V14b passes ROADMAP section 3.1, but V15 baseline waits for V13.6.1 best.",
            "<11pct": "Arm mechanism destabilizes geometry edges; reduce arm mass or wait for V13.6.1 best.",
        },
    }
    path = OUT_DIR / "v14b_vs_v10_v136_C.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[v14b.compare] -> {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--sample-hz", type=float, default=40.0)
    args = parser.parse_args()

    rows = run_slice_C(args.grid, args.duration, args.sample_hz)
    write_csv(rows)
    plot_heatmap(rows, args.grid)
    summary_path = write_comparison(rows)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    v14b = summary["v14b_fsm_passive_arms"]
    overlap = summary["overlap"]
    print("=" * 72)
    print(
        f"DECISION: V14b C slice = {v14b['succ_n']}/{v14b['n_total']} "
        f"= {v14b['rate_pct']:.1f}% -> {summary['verdict']}"
    )
    print(f"success cells: {v14b['success_cells']}")
    print(f"overlap with V10 PD: {overlap['with_v10_pd']}")
    print(f"overlap with V13.6 FSM: {overlap['with_v13_6_fsm']}")
    print(f"V14b-only cells: {overlap['v14b_only']}")
    print("=" * 72)


if __name__ == "__main__":
    main()

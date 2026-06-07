"""V14b x V13 slice-C scan using the V13.6.1 best phase parameters."""

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
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(V136_DIR))

from simulate_passive_arms_v136 import (
    OUT_DIR,
    PassiveArmsParams,
    make_v14b_params,
    run_simulation,
)  # noqa: E402
from simulate_v13_6 import PhaseParams, V136Params  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

ARM_MASS = 0.05
ARM_LENGTH = 0.40
BASELINE_V14B_V136_SUCCESS_N = 3
BASELINE_V14B_V136_RATE = 8.333333333333332

V10_SUCCESS_CELLS = {
    (0.034, 0.900),
    (0.038, 0.900),
    (0.038, 0.940),
    (0.038, 0.980),
    (0.046, 1.060),
    (0.046, 1.100),
}
V136_SUCCESS_CELLS = {
    (0.038, 1.020),
    (0.042, 0.980),
    (0.042, 1.020),
    (0.042, 1.060),
}
V1361_BEST_SUCCESS_CELLS = {
    (0.042, 0.980),
    (0.042, 1.020),
    (0.042, 1.060),
    (0.046, 1.060),
    (0.046, 1.100),
}
V14B_V136_SUCCESS_CELLS = {
    (0.038, 1.020),
    (0.042, 0.980),
    (0.042, 1.020),
}


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def cell(x: float, y: float) -> tuple[float, float]:
    return (round(float(x), 3), round(float(y), 3))


def make_v1361_best_v14b_geom(foot_radius: float, leg_scale: float, duration: float):
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
    defaults = V136Params()
    return make_v14b_params(
        base,
        stance_early=defaults.stance_early,
        stance_late=PhaseParams(
            k_E=0.0,
            k_PD=defaults.stance_late.k_PD,
            tau_max=4.0,
            kd=defaults.stance_late.kd,
            E_target=defaults.stance_late.E_target,
        ),
        swing_thrust=PhaseParams(
            k_E=7.5,
            k_PD=10.0,
            tau_max=4.0,
            kd=defaults.swing_thrust.kd,
            E_target=defaults.swing_thrust.E_target,
        ),
        swing_retract=PhaseParams(
            k_E=0.0,
            k_PD=defaults.swing_retract.k_PD,
            tau_max=3.0,
            kd=defaults.swing_retract.kd,
            E_target=defaults.swing_retract.E_target,
        ),
    )


def evaluate(params, sample_hz: float) -> dict:
    _, summary = run_simulation(params, sample_hz=sample_hz)
    p = params.base
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], p.total_mass, summary["forward_distance"]
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
        "swing_thrust_k_E": 7.5,
        "swing_thrust_k_PD": 10.0,
        "swing_thrust_tau_max": 4.0,
        "swing_retract_tau_max": 3.0,
        "stance_late_tau_max": 4.0,
    }


def run_slice_C(grid: int, duration: float, sample_hz: float) -> list[dict]:
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    rows: list[dict] = []
    total = grid * grid
    t0 = time.time()
    print(
        f"[v14b.C_foot_leg.v1361best] grid={grid}x{grid}={total}, duration={duration}s, "
        f"arm_mass={ARM_MASS}, arm_length={ARM_LENGTH}, swing_retract_tau_max=3.0"
    )
    for ix, foot_radius in enumerate(xs):
        for iy, leg_scale in enumerate(ys):
            params = make_v1361_best_v14b_geom(foot_radius, leg_scale, duration)
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
                    "swing_thrust_k_E": 7.5,
                    "swing_thrust_k_PD": 10.0,
                    "swing_thrust_tau_max": 4.0,
                    "swing_retract_tau_max": 3.0,
                    "stance_late_tau_max": 4.0,
                }
            row["slice"] = "v14b_C_foot_leg_v1361best"
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
    path = OUT_DIR / "v14b_C_foot_leg_v1361best.csv"
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
        "swing_thrust_k_E",
        "swing_thrust_k_PD",
        "swing_thrust_tau_max",
        "swing_retract_tau_max",
        "stance_late_tau_max",
    ]
    keys = priority + sorted(
        {key for row in rows for key in row.keys()} - set(priority)
    )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[v14b.C_foot_leg.v1361best] -> {path}")
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
        f"[V14b + V13.6.1 best] Success\n"
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
    ax.set_title("[V14b + V13.6.1 best] alternating touchdowns")
    plt.colorbar(im2, ax=ax)

    fig.suptitle(
        "V14b passive arms with V13.6.1 best phase params - slice C", fontsize=12
    )
    fig.tight_layout()
    out = OUT_DIR / "v14b_C_heatmap_v1361best.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"[v14b.heatmap.v1361best] -> {out}")
    return out


def verdict_for(success_n: int) -> str:
    if success_n > BASELINE_V14B_V136_SUCCESS_N:
        return "improved_vs_v14b_v136_recommend_stage2_fsm_baseline"
    if success_n == BASELINE_V14B_V136_SUCCESS_N:
        return "same_as_v14b_v136_gain_erased_by_arms_needs_v14c_arm_mechanics"
    return "worse_than_v14b_v136_new_interaction_instability"


def relation(
    success_cells: set[tuple[float, float]], reference: set[tuple[float, float]]
) -> dict:
    overlap = sorted(success_cells & reference)
    return {
        "overlap": overlap,
        "overlap_n": len(overlap),
        "is_subset_of_reference": success_cells <= reference,
        "contains_reference": reference <= success_cells,
        "new_cells_vs_reference": sorted(success_cells - reference),
        "lost_reference_cells": sorted(reference - success_cells),
    }


def write_comparison(rows: list[dict]) -> Path:
    total = len(rows)
    success_cells = {
        cell(row["foot_radius_x"], row["leg_scale_y"]) for row in rows if row["success"]
    }
    success_n = len(success_cells)
    rate = success_n / max(1, total) * 100.0
    fail_counter = Counter(str(row["failure"]) for row in rows)
    out = {
        "slice": "C_foot_leg",
        "grid": 6,
        "n_total": total,
        "arm_params_fixed": {"arm_mass": ARM_MASS, "arm_length": ARM_LENGTH},
        "phase_params": {
            "source": "V13.6.1 best candidate 6",
            "swing_thrust_k_E": 7.5,
            "swing_thrust_k_PD": 10.0,
            "swing_thrust_tau_max": 4.0,
            "swing_retract_tau_max": 3.0,
            "stance_late_tau_max": 4.0,
            "only_difference_vs_v13_6": "swing_retract_tau_max 2.0 -> 3.0",
        },
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
        "v13_6_1_best_no_arms": {
            "candidate_id": 6,
            "succ_n": 5,
            "n_total": 36,
            "rate_pct": 13.9,
            "success_cells": sorted(V1361_BEST_SUCCESS_CELLS),
        },
        "v14b_v13_6_params": {
            "succ_n": BASELINE_V14B_V136_SUCCESS_N,
            "n_total": 36,
            "rate_pct": BASELINE_V14B_V136_RATE,
            "success_cells": sorted(V14B_V136_SUCCESS_CELLS),
        },
        "v14b_v13_6_1_best": {
            "succ_n": success_n,
            "n_total": total,
            "rate_pct": rate,
            "success_cells": sorted(success_cells),
            "failure_distribution": dict(fail_counter),
        },
        "overlap_and_containment": {
            "vs_v10_pd": relation(success_cells, V10_SUCCESS_CELLS),
            "vs_v13_6_fsm": relation(success_cells, V136_SUCCESS_CELLS),
            "vs_v13_6_1_best_no_arms": relation(
                success_cells, V1361_BEST_SUCCESS_CELLS
            ),
            "vs_v14b_v13_6_params": relation(success_cells, V14B_V136_SUCCESS_CELLS),
        },
        "delta_vs_v14b_v13_6_pp": rate - BASELINE_V14B_V136_RATE,
        "delta_vs_v13_6_1_best_no_arms_pp": rate - 13.9,
        "verdict": verdict_for(success_n),
        "verdict_rules": {
            ">8.3pct": "V13.6.1 best recovers geometry edge under arms; recommend as stage-2 FSM baseline.",
            "=8.3pct": "V13.6.1 gain is erased under arms; V14c arm mechanics needed.",
            "<8.3pct": "V13.6.1 best and arms create a new interaction instability.",
        },
    }
    path = OUT_DIR / "v14b_vs_v10_v136_v1361_C.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[v14b.compare.v1361best] -> {path}")
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
    v14b = summary["v14b_v13_6_1_best"]
    overlap = summary["overlap_and_containment"]
    print("=" * 78)
    print(
        f"DECISION: V14b + V13.6.1 best = {v14b['succ_n']}/{v14b['n_total']} "
        f"= {v14b['rate_pct']:.1f}% -> {summary['verdict']}"
    )
    print(f"delta vs V14b(V13.6 params): {summary['delta_vs_v14b_v13_6_pp']:+.1f} pp")
    print(f"success cells: {v14b['success_cells']}")
    print(
        f"overlap with V13.6.1 best no-arms: {overlap['vs_v13_6_1_best_no_arms']['overlap']}"
    )
    print(
        f"lost no-arms cells: {overlap['vs_v13_6_1_best_no_arms']['lost_reference_cells']}"
    )
    print(
        f"new cells vs no-arms: {overlap['vs_v13_6_1_best_no_arms']['new_cells_vs_reference']}"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()

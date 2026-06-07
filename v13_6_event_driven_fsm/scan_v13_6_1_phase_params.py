"""V13.6.1 phase-parameter search and diagnostics.

This script keeps the V13.6 event-driven FSM structure intact and only varies
phase-local force parameters. It runs in two stages:

1. Baseline-geometry smoke search over phase parameters.
2. Slice-C 6x6 rescans for the best smoke candidates.

Outputs are written under v13_6_event_driven_fsm/out/.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(ROOT))

import simulate_v13_6 as sim_v136  # noqa: E402
from simulate_v13_6 import (  # noqa: E402
    PhaseParams,
    V136Params,
    _baseline_v10,
    make_v136_params,
    run_simulation,
)

from common.energy_metrics import cost_of_transport  # noqa: E402
from common.poincare import collect_section, floquet_multipliers  # noqa: E402

OUT_DIR = ROOT / "out"
ISOLATED_MODEL_DIR = OUT_DIR / "v13_6_1_models"
ISOLATED_MODEL_PATH = ISOLATED_MODEL_DIR / "rolling_foot_walker.xml"
_ORIGINAL_WRITE_MODEL = sim_v136.write_model
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")
V10_C_SUCCESS_CELLS = {
    (0.034, 0.90),
    (0.038, 0.90),
    (0.038, 0.94),
    (0.038, 0.98),
    (0.046, 1.06),
    (0.046, 1.10),
}
V136_C_SUCCESS_CELLS = {
    (0.038, 1.02),
    (0.042, 0.98),
    (0.042, 1.02),
    (0.042, 1.06),
}


def configure_isolated_model_output() -> None:
    """Keep V13.6.1 scans from rewriting the shared V10 XML model path."""
    ISOLATED_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    def write_model_isolated(params, path=ISOLATED_MODEL_PATH):
        _ORIGINAL_WRITE_MODEL(params, path=path)

    sim_v136.MODEL_PATH = ISOLATED_MODEL_PATH
    sim_v136.write_model = write_model_isolated


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def cell_key(x: float, y: float) -> tuple[float, float]:
    return (round(float(x), 3), round(float(y), 2))


def classify_cell(x: float, y: float) -> str:
    key = cell_key(x, y)
    if key in V136_C_SUCCESS_CELLS:
        return "v13_6_success"
    if key in V10_C_SUCCESS_CELLS:
        return "v10_success_v13_6_fail"
    return "shared_fail"


def candidate_grid() -> list[dict]:
    k_E_values = [4.0, 6.0, 7.5, 9.0, 11.0]
    k_PD_values = [0.0, 5.0, 10.0, 15.0, 20.0]
    thrust_tau_values = [3.0, 4.0, 5.0]
    retract_tau_values = [1.5, 2.0, 3.0]
    stance_late_tau_values = [4.0, 5.0, 6.0]
    raw: list[dict] = []
    for values in itertools.product(
        k_E_values,
        k_PD_values,
        thrust_tau_values,
        retract_tau_values,
        stance_late_tau_values,
    ):
        k_E, k_PD, thrust_tau, retract_tau, stance_late_tau = values
        raw.append(
            {
                "swing_thrust_k_E": k_E,
                "swing_thrust_k_PD": k_PD,
                "swing_thrust_tau_max": thrust_tau,
                "swing_retract_tau_max": retract_tau,
                "stance_late_tau_max": stance_late_tau,
            }
        )

    # Put the known V13.6 point and a few spread-out probes first so a short
    # default smoke run still covers meaningful parts of the search space.
    seeds = [
        # Existing V13.6 baseline.
        (7.5, 10.0, 4.0, 2.0, 4.0),
        # Lower and higher energy gains around the baseline.
        (6.0, 10.0, 4.0, 2.0, 4.0),
        (9.0, 10.0, 4.0, 2.0, 4.0),
        # More/less swing PD contribution.
        (7.5, 5.0, 4.0, 2.0, 4.0),
        (7.5, 15.0, 4.0, 2.0, 4.0),
        # Torque-budget probes for late stance and retract.
        (7.5, 10.0, 5.0, 2.0, 4.0),
        (7.5, 10.0, 4.0, 3.0, 4.0),
        (7.5, 10.0, 4.0, 2.0, 5.0),
    ]
    by_key = {
        (
            r["swing_thrust_k_E"],
            r["swing_thrust_k_PD"],
            r["swing_thrust_tau_max"],
            r["swing_retract_tau_max"],
            r["stance_late_tau_max"],
        ): r
        for r in raw
    }
    ordered: list[dict] = []
    seen: set[tuple[float, float, float, float, float]] = set()
    for key in seeds:
        if key in by_key and key not in seen:
            ordered.append(dict(by_key[key]))
            seen.add(key)
    for r in raw:
        key = (
            r["swing_thrust_k_E"],
            r["swing_thrust_k_PD"],
            r["swing_thrust_tau_max"],
            r["swing_retract_tau_max"],
            r["stance_late_tau_max"],
        )
        if key not in seen:
            ordered.append(dict(r))
            seen.add(key)
    for idx, c in enumerate(ordered):
        c["candidate_id"] = idx
    return ordered


def params_from_candidate(c: dict, duration: float = 12.0) -> V136Params:
    base = replace(_baseline_v10(), duration=duration)
    defaults = V136Params()
    return make_v136_params(
        base=base,
        stance_early=defaults.stance_early,
        stance_late=PhaseParams(
            k_E=0.0,
            k_PD=defaults.stance_late.k_PD,
            tau_max=float(c["stance_late_tau_max"]),
            kd=defaults.stance_late.kd,
            E_target=defaults.stance_late.E_target,
        ),
        swing_thrust=PhaseParams(
            k_E=float(c["swing_thrust_k_E"]),
            k_PD=float(c["swing_thrust_k_PD"]),
            tau_max=float(c["swing_thrust_tau_max"]),
            kd=defaults.swing_thrust.kd,
            E_target=defaults.swing_thrust.E_target,
        ),
        swing_retract=PhaseParams(
            k_E=0.0,
            k_PD=defaults.swing_retract.k_PD,
            tau_max=float(c["swing_retract_tau_max"]),
            kd=defaults.swing_retract.kd,
            E_target=defaults.swing_retract.E_target,
        ),
    )


def params_for_cell(
    c: dict, foot_radius: float, leg_scale: float, duration: float
) -> V136Params:
    params = params_from_candidate(c, duration=duration)
    base = params.base
    scaled = replace(
        base,
        foot_radius=float(foot_radius),
        thigh_length=float(base.thigh_length * leg_scale),
        shank_length=float(base.shank_length * leg_scale),
        step_length=float(base.step_length * leg_scale),
        duration=duration,
    )
    return V136Params(
        base=scaled,
        stance_early=params.stance_early,
        stance_late=params.stance_late,
        swing_thrust=params.swing_thrust,
        swing_retract=params.swing_retract,
    )


def contact_interval_stats(summary: dict) -> tuple[float, float]:
    times = [float(e["time"]) for e in summary.get("contact_events", [])]
    if len(times) < 2:
        return float("nan"), float("nan")
    intervals = [b - a for a, b in zip(times, times[1:])]
    mean = sum(intervals) / len(intervals)
    var = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    return float(mean), float(math.sqrt(var))


def diagnostic_stats(rows: list[dict], summary: dict, params: V136Params) -> dict:
    mass = params.base.hip_mass + 2.0 * params.base.torso_mass
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], mass, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    total_phase_time = max(
        1e-9, 2.0 * max(summary["simulated_time"], params.base.timestep)
    )
    phase_durations = summary.get("phase_durations_s", {})
    phase_torque = summary.get("phase_torque_integral_Nms", {})
    A_values = [float(r.get("A_swing", 0.0)) for r in rows]
    thrust_tau_max = params.swing_thrust.tau_max
    active_A = [v for v in A_values if v > 1e-9]
    A_sat = sum(1 for v in active_A if v >= 0.95 * thrust_tau_max)
    td_mean, td_std = contact_interval_stats(summary)
    phase_map = {
        "stance_early": params.stance_early,
        "stance_late": params.stance_late,
        "swing_thrust": params.swing_thrust,
        "swing_retract": params.swing_retract,
    }
    phase_samples = dict.fromkeys(phase_map, 0)
    phase_sat = dict.fromkeys(phase_map, 0)
    phase_abs_tau_sum = dict.fromkeys(phase_map, 0.0)
    for r in rows:
        for side, tau_key, phase_key in [
            ("left", "left_hip_tau", "left_phase"),
            ("right", "right_hip_tau", "right_phase"),
        ]:
            phase = str(r.get(phase_key, ""))
            if phase not in phase_map:
                continue
            tau_abs = abs(float(r.get(tau_key, 0.0)))
            phase_samples[phase] += 1
            phase_abs_tau_sum[phase] += tau_abs
            if tau_abs >= 0.95 * phase_map[phase].tau_max:
                phase_sat[phase] += 1
    active_e = [
        float(r.get("e_E_swing", 0.0))
        for r in rows
        if float(r.get("A_swing", 0.0)) > 1e-9
    ]
    e_mean = sum(active_e) / len(active_e) if active_e else 0.0
    e_var = (
        sum((x - e_mean) ** 2 for x in active_e) / len(active_e) if active_e else 0.0
    )
    last = rows[-1] if rows else {}
    return {
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "failure": str(summary["failure"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "cot": float(cot),
        "score": float(summary["score"]),
        "phase_transitions": int(summary["phase_transitions"]),
        "stance_early_frac": float(
            phase_durations.get("stance_early", 0.0) / total_phase_time
        ),
        "stance_late_frac": float(
            phase_durations.get("stance_late", 0.0) / total_phase_time
        ),
        "swing_thrust_frac": float(
            phase_durations.get("swing_thrust", 0.0) / total_phase_time
        ),
        "swing_retract_frac": float(
            phase_durations.get("swing_retract", 0.0) / total_phase_time
        ),
        "swing_thrust_torque_Nms": float(phase_torque.get("swing_thrust", 0.0)),
        "A_swing_mean": float(sum(active_A) / len(active_A)) if active_A else 0.0,
        "A_swing_sat_frac": float(A_sat / len(active_A)) if active_A else 0.0,
        "e_E_swing_mean": float(e_mean),
        "e_E_swing_std": float(math.sqrt(e_var)),
        "touchdown_interval_mean_s": td_mean,
        "touchdown_interval_std_s": td_std,
        "failure_left_phase": str(last.get("left_phase", "")),
        "failure_right_phase": str(last.get("right_phase", "")),
        "stance_early_tau_sat_frac": (
            float(phase_sat["stance_early"] / phase_samples["stance_early"])
            if phase_samples["stance_early"]
            else 0.0
        ),
        "stance_late_tau_sat_frac": (
            float(phase_sat["stance_late"] / phase_samples["stance_late"])
            if phase_samples["stance_late"]
            else 0.0
        ),
        "swing_thrust_tau_sat_frac": (
            float(phase_sat["swing_thrust"] / phase_samples["swing_thrust"])
            if phase_samples["swing_thrust"]
            else 0.0
        ),
        "swing_retract_tau_sat_frac": (
            float(phase_sat["swing_retract"] / phase_samples["swing_retract"])
            if phase_samples["swing_retract"]
            else 0.0
        ),
        "stance_early_mean_abs_tau": (
            float(phase_abs_tau_sum["stance_early"] / phase_samples["stance_early"])
            if phase_samples["stance_early"]
            else 0.0
        ),
        "stance_late_mean_abs_tau": (
            float(phase_abs_tau_sum["stance_late"] / phase_samples["stance_late"])
            if phase_samples["stance_late"]
            else 0.0
        ),
        "swing_thrust_mean_abs_tau": (
            float(phase_abs_tau_sum["swing_thrust"] / phase_samples["swing_thrust"])
            if phase_samples["swing_thrust"]
            else 0.0
        ),
        "swing_retract_mean_abs_tau": (
            float(phase_abs_tau_sum["swing_retract"] / phase_samples["swing_retract"])
            if phase_samples["swing_retract"]
            else 0.0
        ),
    }


def run_baseline_search(
    limit: int | None, duration: float, sample_hz: float
) -> list[dict]:
    candidates = candidate_grid()
    if limit is not None:
        candidates = candidates[:limit]
    rows_out: list[dict] = []
    total = len(candidates)
    t0 = time.time()
    for done, c in enumerate(candidates, start=1):
        params = params_from_candidate(c, duration=duration)
        try:
            rows, summary = run_simulation(params, sample_hz=sample_hz)
            r = diagnostic_stats(rows, summary, params)
        except Exception as exc:  # noqa: BLE001
            r = {
                "success": False,
                "alternating_touchdowns": 0,
                "forward_distance": 0.0,
                "simulated_time": 0.0,
                "failure": f"exception:{exc.__class__.__name__}",
                "active_input_energy_j": 0.0,
                "cot": float("nan"),
                "score": -1e6,
                "phase_transitions": 0,
                "stance_early_frac": float("nan"),
                "stance_late_frac": float("nan"),
                "swing_thrust_frac": float("nan"),
                "swing_retract_frac": float("nan"),
                "swing_thrust_torque_Nms": 0.0,
                "A_swing_mean": 0.0,
                "A_swing_sat_frac": 0.0,
                "e_E_swing_mean": 0.0,
                "e_E_swing_std": 0.0,
                "touchdown_interval_mean_s": float("nan"),
                "touchdown_interval_std_s": float("nan"),
                "failure_left_phase": "",
                "failure_right_phase": "",
                "stance_early_tau_sat_frac": 0.0,
                "stance_late_tau_sat_frac": 0.0,
                "swing_thrust_tau_sat_frac": 0.0,
                "swing_retract_tau_sat_frac": 0.0,
                "stance_early_mean_abs_tau": 0.0,
                "stance_late_mean_abs_tau": 0.0,
                "swing_thrust_mean_abs_tau": 0.0,
                "swing_retract_mean_abs_tau": 0.0,
            }
        r.update(c)
        r["baseline_smoke_pass"] = (
            r["success"]
            and r["alternating_touchdowns"] >= 10
            and r["forward_distance"] >= 4.0
            and 0.04 <= r["cot"] <= 0.12
        )
        rows_out.append(r)
        elapsed = time.time() - t0
        eta = elapsed / done * (total - done) if done else 0.0
        print(
            f"[baseline {done}/{total}] id={c['candidate_id']} "
            f"pass={r['baseline_smoke_pass']} success={r['success']} "
            f"td={r['alternating_touchdowns']} dist={r['forward_distance']:.2f} "
            f"cot={r['cot']:.3f} fail={r['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
        )
    return rows_out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def select_candidates(rows: list[dict], max_candidates: int) -> list[dict]:
    ranked = sorted(
        rows,
        key=lambda r: (
            bool(r.get("baseline_smoke_pass", False)),
            bool(r.get("success", False)),
            int(r.get("alternating_touchdowns", 0)),
            float(r.get("forward_distance", 0.0)),
            (
                -abs(float(r.get("cot", 999.0)) - 0.072)
                if not math.isnan(float(r.get("cot", float("nan"))))
                else -999.0
            ),
            float(r.get("score", -1e9)),
        ),
        reverse=True,
    )
    return ranked[:max_candidates]


def run_slice_C_for_candidate(
    c: dict, grid: int, duration: float, sample_hz: float
) -> list[dict]:
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    rows_out: list[dict] = []
    total = grid * grid
    t0 = time.time()
    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            params = params_for_cell(c, xv, yv, duration)
            try:
                rows, summary = run_simulation(params, sample_hz=sample_hz)
                r = diagnostic_stats(rows, summary, params)
            except Exception as exc:  # noqa: BLE001
                r = {
                    "success": False,
                    "alternating_touchdowns": 0,
                    "forward_distance": 0.0,
                    "simulated_time": 0.0,
                    "failure": f"exception:{exc.__class__.__name__}",
                    "active_input_energy_j": 0.0,
                    "cot": float("nan"),
                    "score": -1e6,
                    "phase_transitions": 0,
                    "stance_early_frac": float("nan"),
                    "stance_late_frac": float("nan"),
                    "swing_thrust_frac": float("nan"),
                    "swing_retract_frac": float("nan"),
                    "swing_thrust_torque_Nms": 0.0,
                    "A_swing_mean": 0.0,
                    "A_swing_sat_frac": 0.0,
                    "e_E_swing_mean": 0.0,
                    "e_E_swing_std": 0.0,
                    "touchdown_interval_mean_s": float("nan"),
                    "touchdown_interval_std_s": float("nan"),
                    "failure_left_phase": "",
                    "failure_right_phase": "",
                    "stance_early_tau_sat_frac": 0.0,
                    "stance_late_tau_sat_frac": 0.0,
                    "swing_thrust_tau_sat_frac": 0.0,
                    "swing_retract_tau_sat_frac": 0.0,
                    "stance_early_mean_abs_tau": 0.0,
                    "stance_late_mean_abs_tau": 0.0,
                    "swing_thrust_mean_abs_tau": 0.0,
                    "swing_retract_mean_abs_tau": 0.0,
                }
            r.update(
                {
                    k: c[k]
                    for k in c
                    if k.startswith(("candidate_", "swing_", "stance_"))
                }
            )
            r["ix"] = ix
            r["iy"] = iy
            r["foot_radius_x"] = float(xv)
            r["leg_scale_y"] = float(yv)
            r["slice"] = "v13_6_1_C_foot_leg"
            r["cell_class"] = (
                classify_cell(xv, yv) if grid == 6 else "dev_grid_unclassified"
            )
            rows_out.append(r)
            done = ix * grid + iy + 1
            elapsed = time.time() - t0
            eta = elapsed / done * (total - done)
            print(
                f"  [C {done}/{total}] cand={c['candidate_id']} "
                f"foot={xv:.3f} leg={yv:.3f} class={r['cell_class']} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"fail={r['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
            )
    return rows_out


def summarize_slice(rows: list[dict], grid: int, candidate_rows: list[dict]) -> dict:
    official_grid = grid == 6
    by_candidate: dict[int, list[dict]] = {}
    for r in rows:
        by_candidate.setdefault(int(r["candidate_id"]), []).append(r)

    candidates_summary = []
    best = None
    for cid, rs in sorted(by_candidate.items()):
        succ = [r for r in rs if r["success"]]
        failures = Counter(r["failure"] for r in rs)
        by_class = {}
        classes = (
            ["v13_6_success", "v10_success_v13_6_fail", "shared_fail"]
            if official_grid
            else ["dev_grid_unclassified"]
        )
        for cls in classes:
            cr = [r for r in rs if r["cell_class"] == cls]
            by_class[cls] = {
                "n": len(cr),
                "success_n": sum(1 for r in cr if r["success"]),
            }
        item = {
            "candidate_id": cid,
            "success_n": len(succ),
            "n_total": len(rs),
            "rate_pct": len(succ) / max(1, len(rs)) * 100.0,
            "success_cells": [
                [round(float(r["foot_radius_x"]), 3), round(float(r["leg_scale_y"]), 2)]
                for r in succ
            ],
            "failure_distribution": dict(failures),
            "cell_class_success": by_class,
        }
        source = next(
            (r for r in candidate_rows if int(r["candidate_id"]) == cid), None
        )
        if source:
            for key in [
                "swing_thrust_k_E",
                "swing_thrust_k_PD",
                "swing_thrust_tau_max",
                "swing_retract_tau_max",
                "stance_late_tau_max",
            ]:
                item[key] = source[key]
        candidates_summary.append(item)
        if best is None or (item["success_n"], item["rate_pct"]) > (
            best["success_n"],
            best["rate_pct"],
        ):
            best = item

    best_succ = int(best["success_n"]) if best else 0
    if not official_grid:
        verdict = "dev_smoke_not_official"
    elif best_succ >= 7:
        verdict = "advance_to_20s_floquet"
    elif best_succ >= 5:
        verdict = "partial_recovery_continue_search"
    else:
        verdict = "no_gain_over_v13_6_consider_imitation_rl"

    return {
        "slice": "C_foot_leg",
        "grid": grid,
        "official_comparison_grid": official_grid,
        "v10_baseline": {"succ_n": 6, "rate_pct": 16.7} if official_grid else None,
        "v13_5_planC": {"succ_n": 0, "rate_pct": 0.0} if official_grid else None,
        "v13_6_fsm": (
            {
                "succ_n": 4,
                "rate_pct": 11.11111111111111,
                "success_cells": [[x, y] for x, y in sorted(V136_C_SUCCESS_CELLS)],
            }
            if official_grid
            else None
        ),
        "v13_6_1_best": best,
        "delta_best_vs_v10_pp": (
            (best["rate_pct"] - 16.7) if best and official_grid else None
        ),
        "delta_best_vs_v13_6_pp": (
            (best["rate_pct"] - 11.11111111111111) if best and official_grid else None
        ),
        "verdict": verdict,
        "candidates": candidates_summary,
    }


def plot_heatmap(
    rows: list[dict], grid: int, out_path: Path, candidate_id: int
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rs = [r for r in rows if int(r["candidate_id"]) == int(candidate_id)]
    succ = np.zeros((grid, grid))
    td = np.zeros((grid, grid))
    for r in rs:
        succ[int(r["ix"]), int(r["iy"])] = 1.0 if r["success"] else 0.0
        td[int(r["ix"]), int(r["iy"])] = float(r["alternating_touchdowns"])
    xs = sorted({float(r["foot_radius_x"]) for r in rs})
    ys = sorted({float(r["leg_scale_y"]) for r in rs})
    x0, x1 = xs[0], xs[-1]
    y0, y1 = ys[0], ys[-1]
    if x0 == x1:
        x0 -= 0.001
        x1 += 0.001
    if y0 == y1:
        y0 -= 0.01
        y1 += 0.01

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    im0 = axes[0].imshow(
        succ.T,
        origin="lower",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        aspect="auto",
        extent=[x0, x1, y0, y1],
    )
    axes[0].set_title(
        f"V13.6.1 success, candidate {candidate_id}\n"
        f"rate={int(succ.sum())}/{grid * grid}={succ.sum() / (grid * grid) * 100:.1f}%"
    )
    axes[0].set_xlabel("foot_radius (m)")
    axes[0].set_ylabel("leg_scale")
    plt.colorbar(im0, ax=axes[0])

    im1 = axes[1].imshow(
        td.T,
        origin="lower",
        cmap="viridis",
        aspect="auto",
        extent=[x0, x1, y0, y1],
    )
    axes[1].set_title("Alternating touchdowns")
    axes[1].set_xlabel("foot_radius (m)")
    axes[1].set_ylabel("leg_scale")
    plt.colorbar(im1, ax=axes[1])
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def run_geometry_stress_smoke(
    candidate: dict, duration: float, sample_hz: float
) -> dict:
    # This uses a V10-success / V13.6-fail slice-C cell rather than hip kp/kd.
    # V13.6 hip kp/kd are metadata only because hip torque comes from phase params.
    foot_radius = 0.038
    leg_scale = 0.90
    params = params_for_cell(candidate, foot_radius, leg_scale, duration)
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    out = diagnostic_stats(rows, summary, params)
    out["candidate_id"] = candidate["candidate_id"]
    out["smoke"] = "v10_success_v13_6_fail_geometry"
    out["foot_radius_x"] = foot_radius
    out["leg_scale_y"] = leg_scale
    out["cell_class"] = classify_cell(foot_radius, leg_scale)
    return out


def run_legacy_f02_metadata_smoke(
    candidate: dict, duration: float, sample_hz: float
) -> dict:
    base = replace(_baseline_v10(), hip_kp=15.0, hip_kd=2.7, duration=duration)
    params = params_from_candidate(candidate, duration=duration)
    params = V136Params(
        base=base,
        stance_early=params.stance_early,
        stance_late=params.stance_late,
        swing_thrust=params.swing_thrust,
        swing_retract=params.swing_retract,
    )
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    out = diagnostic_stats(rows, summary, params)
    out["candidate_id"] = candidate["candidate_id"]
    out["smoke"] = "legacy_F_0_2_metadata_only"
    out["note"] = (
        "V13.6 phase hip control ignores base hip_kp/hip_kd; this is not V10 F(0,2) evidence."
    )
    return out


def run_20s_floquet(candidate: dict, sample_hz: float) -> dict:
    params = params_from_candidate(candidate, duration=20.0)
    rows, summary = run_simulation(
        params, save_prefix="v13_6_1_best_20s", sample_hz=sample_hz
    )
    section_pts = collect_section(rows, STATE_KEYS)
    floq = floquet_multipliers(section_pts, skip_head=2)
    eig = floq["eigvals"]
    max_abs = float(max(abs(v) for v in eig)) if eig.size else float("nan")
    result = diagnostic_stats(rows, summary, params)
    result.update(
        {
            "candidate_id": candidate["candidate_id"],
            "n_section_points": int(len(section_pts)),
            "n_pairs_used": int(floq["n_pairs"]),
            "fixed_point": floq["fixed_point"].tolist(),
            "eigvals_real": [float(v.real) for v in eig],
            "eigvals_imag": [float(v.imag) for v in eig],
            "eigvals_abs": [float(abs(v)) for v in eig],
            "max_abs_floquet": max_abs,
            "floquet_comparable_method": "empirical return-map spectrum using same state keys as V13b",
            "floquet_qualified": bool(
                summary["success"]
                and len(section_pts) >= 16
                and int(floq["n_pairs"]) >= 12
            ),
            "max_abs_below_v10": bool(max_abs < 0.9439820184605064),
        }
    )
    path = OUT_DIR / "v13_6_1_best_20s_floquet.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    configure_isolated_model_output()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline-limit",
        type=int,
        default=30,
        help="Number of baseline candidates to smoke-test. Use -1 for the full 675 grid.",
    )
    parser.add_argument(
        "--top-candidates",
        type=int,
        default=2,
        help="Number of baseline-ranked candidates to run on slice C.",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Reuse out/v13_6_1_phase_param_candidates.csv.",
    )
    parser.add_argument(
        "--skip-slice", action="store_true", help="Only run baseline candidate search."
    )
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--sample-hz", type=float, default=40.0)
    parser.add_argument("--floquet-if-qualified", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    candidates_path = OUT_DIR / "v13_6_1_phase_param_candidates.csv"

    if args.skip_baseline:
        with candidates_path.open("r", encoding="utf-8") as f:
            candidate_rows = list(csv.DictReader(f))
        for row in candidate_rows:
            for key, value in list(row.items()):
                if value in {"True", "False"}:
                    row[key] = value == "True"
                else:
                    try:
                        row[key] = float(value)
                    except ValueError:
                        pass
            row["candidate_id"] = int(float(row["candidate_id"]))
    else:
        limit = None if args.baseline_limit < 0 else args.baseline_limit
        candidate_rows = run_baseline_search(limit, args.duration, args.sample_hz)
        write_csv(candidates_path, candidate_rows)
        print(f"[write] {candidates_path}")

    if args.skip_slice:
        return

    selected = select_candidates(candidate_rows, args.top_candidates)
    all_slice_rows: list[dict] = []
    for c in selected:
        print(f"[slice] candidate {c['candidate_id']} -> C grid")
        all_slice_rows.extend(
            run_slice_C_for_candidate(c, args.grid, args.duration, args.sample_hz)
        )

    slice_path = OUT_DIR / "v13_6_1_C_foot_leg.csv"
    write_csv(slice_path, all_slice_rows)
    print(f"[write] {slice_path}")

    summary = summarize_slice(all_slice_rows, args.grid, selected)
    summary_path = OUT_DIR / "v13_6_1_vs_v10_planC_v136.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[write] {summary_path}")

    if summary["v13_6_1_best"]:
        best_id = int(summary["v13_6_1_best"]["candidate_id"])
        plot_path = OUT_DIR / "v13_6_1_C_heatmap.png"
        plot_heatmap(all_slice_rows, args.grid, plot_path, best_id)
        print(f"[write] {plot_path}")

        best_candidate = next(c for c in selected if int(c["candidate_id"]) == best_id)
        stress = run_geometry_stress_smoke(
            best_candidate, args.duration, args.sample_hz
        )
        stress_path = OUT_DIR / "v13_6_1_geometry_stress_smoke.json"
        stress_path.write_text(
            json.dumps(stress, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[write] {stress_path}")

        legacy_f02 = run_legacy_f02_metadata_smoke(
            best_candidate, args.duration, args.sample_hz
        )
        f02_path = OUT_DIR / "v13_6_1_legacy_F02_metadata_smoke.json"
        f02_path.write_text(
            json.dumps(legacy_f02, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[write] {f02_path}")

        if args.floquet_if_qualified and int(summary["v13_6_1_best"]["success_n"]) >= 7:
            floq = run_20s_floquet(best_candidate, args.sample_hz)
            print(f"[floquet] max|lambda|={floq['max_abs_floquet']:.3f}")

    print("=" * 72)
    best = summary["v13_6_1_best"]
    if best:
        print(
            f"V13.6.1 best candidate {best['candidate_id']}: "
            f"{best['success_n']}/{summary['grid'] * summary['grid']} = {best['rate_pct']:.1f}%"
        )
    print(f"verdict: {summary['verdict']}")
    print("=" * 72)


if __name__ == "__main__":
    main()

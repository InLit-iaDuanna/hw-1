"""V13.6.1 best-candidate scan on V13 slice A.

The requested script name says "slope_step", but this script deliberately reuses
the repository's V13 slice-A definition from scan_atlas_v13.SLICES:
    A_slope_foot = slope_deg x foot_radius
This avoids redefining slice A differently from the atlas.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V13_DIR = HW1_ROOT / "v13_parameter_sensitivity_atlas"
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(V13_DIR))

from scan_atlas_v13 import SLICES, linspace  # noqa: E402
from scan_v13_6_1_phase_params import (  # noqa: E402
    configure_isolated_model_output,
    diagnostic_stats,
    params_from_candidate,
)
from simulate_v13_6 import V136Params, run_simulation  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

OUT_DIR = ROOT / "out"
BEST_CANDIDATE = {
    "candidate_id": 6,
    "swing_thrust_k_E": 7.5,
    "swing_thrust_k_PD": 10.0,
    "swing_thrust_tau_max": 4.0,
    "swing_retract_tau_max": 3.0,
    "stance_late_tau_max": 4.0,
}
V136_CANDIDATE = {
    "candidate_id": 0,
    "swing_thrust_k_E": 7.5,
    "swing_thrust_k_PD": 10.0,
    "swing_thrust_tau_max": 4.0,
    "swing_retract_tau_max": 2.0,
    "stance_late_tau_max": 4.0,
}


def make_params_for_A(
    candidate: dict, slope_deg: float, foot_radius: float, duration: float
) -> V136Params:
    params = params_from_candidate(candidate, duration=duration)
    base = replace(
        params.base,
        slope_deg=float(slope_deg),
        foot_radius=float(foot_radius),
        duration=duration,
    )
    return V136Params(
        base=base,
        stance_early=params.stance_early,
        stance_late=params.stance_late,
        swing_thrust=params.swing_thrust,
        swing_retract=params.swing_retract,
    )


def evaluate(params: V136Params, sample_hz: float) -> dict:
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    out = diagnostic_stats(rows, summary, params)
    mass = params.base.hip_mass + 2.0 * params.base.torso_mass
    out["cot"] = (
        cost_of_transport(
            summary["active_input_energy_j"], mass, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    return out


def run_scan_for_candidate(
    candidate: dict, grid: int, duration: float, sample_hz: float, label: str
) -> list[dict]:
    spec = SLICES["A_slope_foot"]
    xkey, x0, x1 = spec["x"]
    ykey, y0, y1 = spec["y"]
    xs = linspace(x0, x1, grid)
    ys = linspace(y0, y1, grid)
    rows: list[dict] = []
    total = grid * grid
    t0 = time.time()
    print(f"[{label}] V13 slice A = {xkey} x {ykey}, grid={grid}x{grid}")
    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            params = make_params_for_A(
                candidate, slope_deg=xv, foot_radius=yv, duration=duration
            )
            try:
                r = evaluate(params, sample_hz=sample_hz)
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
                }
            r.update(
                {
                    "controller_label": label,
                    "candidate_id": int(candidate["candidate_id"]),
                    "swing_thrust_k_E": float(candidate["swing_thrust_k_E"]),
                    "swing_thrust_k_PD": float(candidate["swing_thrust_k_PD"]),
                    "swing_thrust_tau_max": float(candidate["swing_thrust_tau_max"]),
                    "swing_retract_tau_max": float(candidate["swing_retract_tau_max"]),
                    "stance_late_tau_max": float(candidate["stance_late_tau_max"]),
                    "slice": "v13_6_1_A_slope_step",
                    "actual_slice": "A_slope_foot",
                    "ix": ix,
                    "iy": iy,
                    xkey + "_x": float(xv),
                    ykey + "_y": float(yv),
                }
            )
            rows.append(r)
            done = ix * grid + iy + 1
            elapsed = time.time() - t0
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] {label} {xkey}={xv:.3f} {ykey}={yv:.3f} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"fail={r['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
            )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def summarize_controller(rows: list[dict]) -> dict:
    n = len(rows)
    succ = [r for r in rows if as_bool(r["success"])]
    return {
        "success_n": len(succ),
        "n_total": n,
        "rate_pct": len(succ) / max(1, n) * 100.0,
        "success_cells": [
            [round(float(r["slope_deg_x"]), 3), round(float(r["foot_radius_y"]), 3)]
            for r in succ
        ],
        "failure_distribution": dict(Counter(r["failure"] for r in rows)),
    }


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_v10_A_reference() -> dict | None:
    path = V13_DIR / "out" / "v13_A_slope_foot.csv"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return summarize_controller(rows)


def verdict_for(best_rate: float) -> str:
    if best_rate >= 17.0:
        return "advance"
    if best_rate >= 11.0:
        return "partial"
    return "no_gain"


def plot_heatmap(best_rows: list[dict], v136_rows: list[dict], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    def grid(rows: list[dict], key: str):
        xs = sorted({float(r["slope_deg_x"]) for r in rows})
        ys = sorted({float(r["foot_radius_y"]) for r in rows})
        arr = np.zeros((len(xs), len(ys)))
        for r in rows:
            ix = xs.index(float(r["slope_deg_x"]))
            iy = ys.index(float(r["foot_radius_y"]))
            if key == "success":
                arr[ix, iy] = 1.0 if r["success"] else 0.0
            else:
                arr[ix, iy] = float(r[key])
        return xs, ys, arr

    xs, ys, best_succ = grid(best_rows, "success")
    _, _, v136_succ = grid(v136_rows, "success")
    _, _, best_td = grid(best_rows, "alternating_touchdowns")
    extent = [xs[0], xs[-1], ys[0], ys[-1]]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, arr, title, cmap, vmin, vmax in [
        (axes[0], best_succ, "V13.6.1 best success", "RdYlGn", 0, 1),
        (axes[1], v136_succ, "V13.6 original success", "RdYlGn", 0, 1),
        (axes[2], best_td, "V13.6.1 touchdowns", "viridis", None, None),
    ]:
        im = ax.imshow(
            arr.T,
            origin="lower",
            aspect="auto",
            extent=extent,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )
        ax.set_xlabel("slope_deg")
        ax.set_ylabel("foot_radius")
        ax.set_title(title)
        plt.colorbar(im, ax=ax)
    fig.suptitle("V13.6.1 slice A scan (repo definition: slope_deg x foot_radius)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> None:
    configure_isolated_model_output()
    OUT_DIR.mkdir(exist_ok=True)
    grid = 6
    duration = 12.0
    sample_hz = 40.0

    best_rows = run_scan_for_candidate(
        BEST_CANDIDATE, grid, duration, sample_hz, "v13_6_1_best"
    )
    v136_rows = run_scan_for_candidate(
        V136_CANDIDATE, grid, duration, sample_hz, "v13_6_original"
    )
    all_rows = best_rows + v136_rows

    csv_path = OUT_DIR / "v13_6_1_A_slope_step.csv"
    write_csv(csv_path, all_rows)
    heatmap_path = OUT_DIR / "v13_6_1_A_heatmap.png"
    plot_heatmap(best_rows, v136_rows, heatmap_path)

    best_summary = summarize_controller(best_rows)
    v136_summary = summarize_controller(v136_rows)
    v10_summary = load_v10_A_reference()
    delta_pp = best_summary["rate_pct"] - v136_summary["rate_pct"]
    summary = {
        "slice": "A_slope_step",
        "actual_reused_v13_slice": "A_slope_foot",
        "note": "Script name follows request; scan dimensions follow scan_atlas_v13.SLICES['A_slope_foot'].",
        "grid": grid,
        "duration": duration,
        "sample_hz": sample_hz,
        "x": SLICES["A_slope_foot"]["x"],
        "y": SLICES["A_slope_foot"]["y"],
        "v13_6_1_best_candidate": BEST_CANDIDATE,
        "v13_6_1_best": best_summary,
        "v13_6_original": v136_summary,
        "delta_vs_v13_6_pp": delta_pp,
        "v10_reference_from_v13_A": v10_summary,
        "delta_vs_v10_pp": (
            best_summary["rate_pct"] - v10_summary["rate_pct"] if v10_summary else None
        ),
        "verdict": verdict_for(best_summary["rate_pct"]),
        "outputs": {
            "csv": str(csv_path),
            "heatmap": str(heatmap_path),
        },
    }
    summary_path = OUT_DIR / "v13_6_1_A_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[write] {csv_path}")
    print(f"[write] {heatmap_path}")
    print(f"[write] {summary_path}")
    print("=" * 72)
    print(
        f"V13.6.1 best slice A: {best_summary['success_n']}/36 = "
        f"{best_summary['rate_pct']:.1f}% | verdict={summary['verdict']} | "
        f"delta_vs_v13_6={delta_pp:+.1f} pp"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()

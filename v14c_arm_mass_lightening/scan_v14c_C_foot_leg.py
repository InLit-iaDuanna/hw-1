"""V14c arm-mass lightening x V13 slice-C geometry scan.

V14c keeps the V14 passive-arm mechanism and V13.6.1 best candidate 6 FSM
fixed, then scans passive arm mass against the foot_radius x leg_scale geometry
slice. It is still quasi-passive: hip+knee active, arms/ankle passive.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))

from simulate_v14c import (
    OUT_DIR,
    PassiveArmsParams,
    V136Params,
    make_v14c_params,
    run_simulation,
)  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

ARM_MASSES = [0.01, 0.02, 0.03, 0.05]
ARM_LENGTH = 0.40
V14B_REPRO_MASS = 0.05
V14B_EXPECTED_SUCCESS_N = 3
V14B_REPRO_TOL_CELLS = 1

PHASES = ("stance_early", "stance_late", "swing_thrust", "swing_retract")


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def make_params(
    arm_mass: float, foot_radius: float, leg_scale: float, duration: float
) -> V136Params:
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        foot_radius=float(foot_radius),
        thigh_length=float(base0.thigh_length * leg_scale),
        shank_length=float(base0.shank_length * leg_scale),
        step_length=float(base0.step_length * leg_scale),
        arm_mass=float(arm_mass),
        arm_length=ARM_LENGTH,
        arm_damping=0.02,
        arm_stiffness=0.0,
        duration=float(duration),
    )
    return make_v14c_params(base)


def contact_interval_stats(summary: dict) -> tuple[float, float]:
    times = [float(e["time"]) for e in summary.get("contact_events", [])]
    if len(times) < 2:
        return float("nan"), float("nan")
    intervals = [b - a for a, b in zip(times, times[1:])]
    mean = sum(intervals) / len(intervals)
    var = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    return float(mean), float(math.sqrt(var))


def diagnostic_stats(rows: list[dict], summary: dict, params: V136Params) -> dict:
    p = params.base
    mass_eff = p.hip_mass + 2.0 * p.torso_mass
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], mass_eff, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    total_phase_time = max(
        1e-9, 2.0 * max(float(summary["simulated_time"]), p.timestep)
    )
    phase_durations = summary.get("phase_durations_s", {})
    phase_torque = summary.get("phase_torque_integral_abs_Nms", {})
    phase_map = {
        "stance_early": params.stance_early,
        "stance_late": params.stance_late,
        "swing_thrust": params.swing_thrust,
        "swing_retract": params.swing_retract,
    }
    phase_samples = dict.fromkeys(PHASES, 0)
    phase_sat = dict.fromkeys(PHASES, 0)
    phase_abs_tau_sum = dict.fromkeys(PHASES, 0.0)
    for row in rows:
        for tau_key, phase_key in [
            ("left_hip_tau", "left_phase"),
            ("right_hip_tau", "right_phase"),
        ]:
            phase = str(row.get(phase_key, ""))
            if phase not in phase_map:
                continue
            tau_abs = abs(float(row.get(tau_key, 0.0) or 0.0))
            phase_samples[phase] += 1
            phase_abs_tau_sum[phase] += tau_abs
            if tau_abs >= 0.95 * phase_map[phase].tau_max:
                phase_sat[phase] += 1

    active_A = [
        float(row.get("A_swing", 0.0) or 0.0)
        for row in rows
        if float(row.get("A_swing", 0.0) or 0.0) > 1e-9
    ]
    active_e = [
        float(row.get("e_E_swing", 0.0) or 0.0)
        for row in rows
        if float(row.get("A_swing", 0.0) or 0.0) > 1e-9
    ]
    A_sat = sum(1 for v in active_A if v >= 0.95 * params.swing_thrust.tau_max)
    e_mean = sum(active_e) / len(active_e) if active_e else 0.0
    e_var = (
        sum((x - e_mean) ** 2 for x in active_e) / len(active_e) if active_e else 0.0
    )
    td_mean, td_std = contact_interval_stats(summary)
    last = rows[-1] if rows else {}

    out = {
        **asdict(p),
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "failure": str(summary["failure"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "net_actuator_work_j": float(summary.get("net_actuator_work_j", 0.0)),
        "energy_per_alternation_j": float(summary.get("energy_per_alternation_j", 0.0)),
        "cot": float(cot),
        "score": float(summary["score"]),
        "phase_transitions": int(summary["phase_transitions"]),
        "mass_eff_energy_kg": float(mass_eff),
        "energy_excludes_passive_arm_mass": True,
        "quasi_passive": True,
        "pure_passive": False,
        "passive_arms": True,
        "swing_thrust_k_E": float(params.swing_thrust.k_E),
        "swing_thrust_k_PD": float(params.swing_thrust.k_PD),
        "swing_thrust_tau_max": float(params.swing_thrust.tau_max),
        "swing_retract_tau_max": float(params.swing_retract.tau_max),
        "stance_late_tau_max": float(params.stance_late.tau_max),
        "A_swing_mean": float(sum(active_A) / len(active_A)) if active_A else 0.0,
        "A_swing_sat_frac": float(A_sat / len(active_A)) if active_A else 0.0,
        "e_E_swing_mean": float(e_mean),
        "e_E_swing_std": float(math.sqrt(e_var)),
        "touchdown_interval_mean_s": td_mean,
        "touchdown_interval_std_s": td_std,
        "failure_left_phase": str(last.get("left_phase", "")),
        "failure_right_phase": str(last.get("right_phase", "")),
    }
    for phase in PHASES:
        samples = phase_samples[phase]
        out[f"{phase}_frac"] = float(phase_durations.get(phase, 0.0) / total_phase_time)
        out[f"{phase}_torque_Nms"] = float(phase_torque.get(phase, 0.0))
        out[f"{phase}_tau_sat_frac"] = (
            float(phase_sat[phase] / samples) if samples else 0.0
        )
        out[f"{phase}_mean_abs_tau"] = (
            float(phase_abs_tau_sum[phase] / samples) if samples else 0.0
        )
    return out


def evaluate(
    arm_mass: float,
    foot_radius: float,
    leg_scale: float,
    duration: float,
    sample_hz: float,
) -> dict:
    params = make_params(arm_mass, foot_radius, leg_scale, duration)
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    return diagnostic_stats(rows, summary, params)


def smoke_checks(duration: float, sample_hz: float) -> list[dict]:
    checks = [
        {
            "name": "baseline_light_arm",
            "arm_mass": 0.01,
            "foot_radius": 0.04,
            "leg_scale": 1.0,
            "requires_success": True,
            "min_touchdowns": 10,
            "min_forward": 4.0,
        },
        {
            "name": "v14b_known_success_cell",
            "arm_mass": 0.05,
            "foot_radius": 0.042,
            "leg_scale": 1.02,
            "requires_success": True,
            "min_touchdowns": 0,
            "min_forward": 0.0,
        },
    ]
    results = []
    for check in checks:
        row = evaluate(
            check["arm_mass"],
            check["foot_radius"],
            check["leg_scale"],
            duration,
            sample_hz,
        )
        passed = (
            (bool(row["success"]) or not check["requires_success"])
            and int(row["alternating_touchdowns"]) >= int(check["min_touchdowns"])
            and float(row["forward_distance"]) >= float(check["min_forward"])
        )
        result = {
            **check,
            "passed": bool(passed),
            "success": bool(row["success"]),
            "alternating_touchdowns": int(row["alternating_touchdowns"]),
            "forward_distance": float(row["forward_distance"]),
            "failure": str(row["failure"]),
        }
        results.append(result)
        print(
            f"[smoke] {check['name']} passed={passed} success={row['success']} "
            f"td={row['alternating_touchdowns']} dist={row['forward_distance']:.2f} fail={row['failure']}"
        )
    return results


def write_smoke_diagnostics(results: list[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "v14c_smoke_diagnostics.json"
    path.write_text(
        json.dumps({"smoke_checks": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[v14c.smoke] -> {path}")
    return path


def run_scan(grid: int, duration: float, sample_hz: float) -> list[dict]:
    xs = linspace(0.030, 0.050, grid)
    ys = linspace(0.90, 1.10, grid)
    total = len(ARM_MASSES) * grid * grid
    rows: list[dict] = []
    t0 = time.time()
    print(
        f"[v14c.C] masses={ARM_MASSES}, grid={grid}x{grid}, total={total}, duration={duration}s"
    )
    for im, arm_mass in enumerate(ARM_MASSES):
        for ix, foot_radius in enumerate(xs):
            for iy, leg_scale in enumerate(ys):
                try:
                    row = evaluate(
                        arm_mass, foot_radius, leg_scale, duration, sample_hz
                    )
                except Exception as exc:  # noqa: BLE001
                    row = {
                        "success": False,
                        "failure": f"exception:{exc.__class__.__name__}",
                        "cot": float("nan"),
                        "alternating_touchdowns": 0,
                        "forward_distance": 0.0,
                        "simulated_time": 0.0,
                        "active_input_energy_j": 0.0,
                        "net_actuator_work_j": 0.0,
                        "energy_per_alternation_j": 0.0,
                        "score": -1e6,
                        "phase_transitions": 0,
                        "arm_mass": arm_mass,
                        "arm_length": ARM_LENGTH,
                        "swing_thrust_k_E": 7.5,
                        "swing_thrust_k_PD": 10.0,
                        "swing_thrust_tau_max": 4.0,
                        "swing_retract_tau_max": 3.0,
                        "stance_late_tau_max": 4.0,
                    }
                row["slice"] = "v14c_C_foot_leg"
                row["arm_mass_index"] = im
                row["ix"] = ix
                row["iy"] = iy
                row["foot_radius_x"] = float(foot_radius)
                row["leg_scale_y"] = float(leg_scale)
                row["arm_length_fixed"] = ARM_LENGTH
                rows.append(row)
                done = len(rows)
                elapsed = time.time() - t0
                eta = elapsed / done * (total - done)
                print(
                    f"  [{done}/{total}] m={arm_mass:.3f} foot={foot_radius:.3f} leg={leg_scale:.3f} "
                    f"success={row['success']} td={row['alternating_touchdowns']} "
                    f"fail={row['failure']} ({elapsed:.0f}s, ETA {eta:.0f}s)"
                )
    return rows


def write_csv(rows: list[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "v14c_C_foot_leg.csv"
    priority = [
        "slice",
        "arm_mass_index",
        "ix",
        "iy",
        "arm_mass",
        "arm_length",
        "arm_length_fixed",
        "foot_radius_x",
        "leg_scale_y",
        "success",
        "alternating_touchdowns",
        "forward_distance",
        "simulated_time",
        "failure",
        "score",
        "active_input_energy_j",
        "net_actuator_work_j",
        "energy_per_alternation_j",
        "cot",
        "phase_transitions",
        "stance_early_frac",
        "stance_late_frac",
        "swing_thrust_frac",
        "swing_retract_frac",
        "stance_early_tau_sat_frac",
        "stance_late_tau_sat_frac",
        "swing_thrust_tau_sat_frac",
        "swing_retract_tau_sat_frac",
        "A_swing_mean",
        "A_swing_sat_frac",
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
    print(f"[v14c.C] -> {path}")
    return path


def write_run_status(rows: list[dict], smoke: list[dict]) -> Path:
    by_mass = {}
    for arm_mass in ARM_MASSES:
        mass_rows = [
            r for r in rows if abs(float(r.get("arm_mass", -1.0)) - arm_mass) < 1e-9
        ]
        by_mass[f"{arm_mass:.2f}"] = {
            "success_n": sum(1 for r in mass_rows if bool(r.get("success"))),
            "n_total": len(mass_rows),
        }
    m005 = by_mass.get(f"{V14B_REPRO_MASS:.2f}", {"success_n": 0})
    health_pass = (
        abs(int(m005["success_n"]) - V14B_EXPECTED_SUCCESS_N) <= V14B_REPRO_TOL_CELLS
    )
    path = OUT_DIR / "v14c_scan_status.json"
    path.write_text(
        json.dumps(
            {
                "smoke_checks": smoke,
                "scan_rows": len(rows),
                "success_by_mass": by_mass,
                "health_check_verdict": (
                    "v14b_reproduction_passed"
                    if health_pass
                    else "v14b_reproduction_failed_must_diagnose"
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[v14c.status] -> {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--sample-hz", type=float, default=40.0)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    smoke = [] if args.skip_smoke else smoke_checks(args.duration, args.sample_hz)
    if smoke:
        write_smoke_diagnostics(smoke)
        failed = [r for r in smoke if not r["passed"]]
        if failed:
            print("[v14c.C] smoke failed; stopping before full scan.")
            return
    if args.smoke_only:
        return

    rows = run_scan(args.grid, args.duration, args.sample_hz)
    write_csv(rows)
    write_run_status(rows, smoke)


if __name__ == "__main__":
    main()

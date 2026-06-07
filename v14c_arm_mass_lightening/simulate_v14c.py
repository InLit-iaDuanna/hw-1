"""V14c: V14 passive arms model with V13.6.1 best FSM hip control.

This module intentionally writes generated XML and outputs only under
``v14c_arm_mass_lightening``.  The source V14 and V13.6 experiments are
imported as read-only implementation references.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import mujoco

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))

from simulate_passive_arms_v14 import (  # noqa: E402
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    PassiveArmsParams,
    actuator_names,
    build_model_xml,
    classify_failure,
    contact_flags,
    initialize,
    make_row,
)
from simulate_v13_6 import (  # noqa: E402
    PhaseParams,
    V136Params,
    _mechanical_energy,
    control_v136,
)

OUT_DIR = ROOT / "out"
MODEL_DIR = OUT_DIR / "v14c_models"
MODEL_PATH = MODEL_DIR / "passive_arms_v136_walker.xml"
ENERGY_MODEL_NOTE = (
    "Controller energy uses the original V13.6 calibrated effective mass "
    "(hip_mass + 2*torso_mass), intentionally excluding passive arm mass."
)


def write_model(p: PassiveArmsParams, path: Path = MODEL_PATH) -> None:
    resolved_path = path.resolve()
    resolved_model_dir = MODEL_DIR.resolve()
    if resolved_model_dir not in (resolved_path, *resolved_path.parents):
        raise ValueError(
            f"V14c XML output must stay under {resolved_model_dir}: {resolved_path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml(p), encoding="utf-8")


def make_v14c_params(
    base: PassiveArmsParams | None = None, **phase_overrides
) -> V136Params:
    """Build V14c params: V14 passive arms + V13.6.1 best candidate 6 FSM."""
    base = base or PassiveArmsParams()
    defaults = V136Params()
    return V136Params(
        base=base,
        stance_early=phase_overrides.get("stance_early", defaults.stance_early),
        stance_late=phase_overrides.get(
            "stance_late",
            PhaseParams(
                k_E=0.0,
                k_PD=defaults.stance_late.k_PD,
                tau_max=4.0,
                kd=defaults.stance_late.kd,
                E_target=defaults.stance_late.E_target,
            ),
        ),
        swing_thrust=phase_overrides.get(
            "swing_thrust",
            PhaseParams(
                k_E=7.5,
                k_PD=10.0,
                tau_max=4.0,
                kd=defaults.swing_thrust.kd,
                E_target=defaults.swing_thrust.E_target,
            ),
        ),
        swing_retract=phase_overrides.get(
            "swing_retract",
            PhaseParams(
                k_E=0.0,
                k_PD=defaults.swing_retract.k_PD,
                tau_max=3.0,
                kd=defaults.swing_retract.kd,
                E_target=defaults.swing_retract.E_target,
            ),
        ),
    )


make_v14b_params = make_v14c_params


def run_simulation(
    params: V136Params,
    save_prefix: str | None = None,
    sample_hz: float = 120.0,
):
    p = params.base
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, p)

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -p.gait_period
    alternations = 0
    contact_events: list[dict] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    phase_timeline: list[tuple[float, str, str]] = []
    last_left_phase = ""
    last_right_phase = ""
    phase_durations = {
        "stance_early": 0.0,
        "stance_late": 0.0,
        "swing_thrust": 0.0,
        "swing_retract": 0.0,
    }
    phase_torque_int = dict.fromkeys(phase_durations, 0.0)

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        E_current = _mechanical_energy(p, data)
        tau = control_v136(params, data, t, support_foot, burst_start_t, E_current)
        l_hip, l_knee, r_hip, r_knee = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]
        left_phase = tau[5]
        right_phase = tau[6]
        eE_diag = tau[7]
        A_diag = tau[8]
        data.ctrl[:] = (l_hip, l_knee, r_hip, r_knee)

        input_power = sum(
            float(data.ctrl[i]) * float(data.qvel[j])
            for i, j in zip(range(4), [2, 3, 5, 6])
        )
        positive_input_energy += max(0.0, input_power) * p.timestep
        net_work += input_power * p.timestep

        phase_durations[left_phase] += p.timestep
        phase_durations[right_phase] += p.timestep
        phase_torque_int[left_phase] += abs(l_hip) * p.timestep
        phase_torque_int[right_phase] += abs(r_hip) * p.timestep

        if (left_phase != last_left_phase) or (right_phase != last_right_phase):
            phase_timeline.append((t, left_phase, right_phase))
            last_left_phase, last_right_phase = left_phase, right_phase

        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: list[str] = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= p.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > p.min_event_interval
            ):
                if accepted_contact in {"left", "right"}:
                    alternations += 1
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                contact_reported[foot] = True
                contact_events.append({"time": t, "foot": foot, "E": E_current})
                break

        if step % sample_stride == 0:
            row = make_row(
                model,
                data,
                p,
                t,
                left_contact,
                right_contact,
                support_foot,
                mode_label,
                (l_hip, l_knee, r_hip, r_knee),
                input_power,
                positive_input_energy,
            )
            row["E_current"] = float(E_current)
            row["e_E_swing"] = float(eE_diag)
            row["A_swing"] = float(A_diag)
            row["left_phase"] = left_phase
            row["right_phase"] = right_phase
            rows.append(row)

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        fallback = make_row(
            model,
            data,
            p,
            0.0,
            left_contact,
            right_contact,
            support_foot,
            "left_stance",
            (0, 0, 0, 0),
            0.0,
            positive_input_energy,
        )
        fallback["E_current"] = float(_mechanical_energy(p, data))
        fallback["e_E_swing"] = 0.0
        fallback["A_swing"] = 0.0
        fallback["left_phase"] = "stance_early"
        fallback["right_phase"] = "swing_thrust"
        rows.append(fallback)

    simulated_time = float(rows[-1]["time"])
    forward = max_x - start_x
    success = (
        simulated_time >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and not failure
    )
    score = (
        alternations * 200.0
        + simulated_time * 80.0
        + forward * 60.0
        - 3.0 * positive_input_energy
    )
    if success:
        score += 2000.0
    if failure:
        score -= 300.0
    if failure in {"nan_or_unstable", "fly_away", "penetration"}:
        score -= 500.0

    summary = {
        "params": asdict(p),
        "v136_phase_params": {
            "stance_early": asdict(params.stance_early),
            "stance_late": asdict(params.stance_late),
            "swing_thrust": asdict(params.swing_thrust),
            "swing_retract": asdict(params.swing_retract),
        },
        "score": score,
        "success": success,
        "success_criteria": {
            "simulated_time_s": SUCCESS_TIME,
            "alternating_touchdowns": SUCCESS_TOUCHDOWNS,
            "forward_distance_m": SUCCESS_FORWARD,
            "must_complete_without_failure": True,
        },
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "actuator_count": int(model.nu),
        "actuator_names": actuator_names(model),
        "knee_actuators": ["left_knee_stabilizer", "right_knee_stabilizer"],
        "ankle_actuators": [],
        "arm_actuators": [],
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "total_mass_kg": p.total_mass,
        "phase_transitions": len(phase_timeline),
        "phase_durations_s": phase_durations,
        "phase_torque_integral_abs_Nms": phase_torque_int,
        "controller_energy_model": {
            "mass_eff_kg": float(p.hip_mass + 2.0 * p.torso_mass),
            "excludes_passive_arm_mass": True,
            "note": ENERGY_MODEL_NOTE,
        },
        "quasi_passive": True,
        "pure_passive": False,
        "passive_arms": True,
        "uses_reward_function": False,
        "controller": "v13_6_1_best_fsm_on_v14_passive_arms_v14c",
        "v13_6_prereq": {
            "slice_C_success": "4/36",
            "slice_C_rate_pct": 11.11111111111111,
            "verdict": "tier_B_partial",
            "note": "V14c uses V13.6.1 best candidate 6 while scanning passive arm mass.",
        },
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        with (OUT_DIR / f"{save_prefix}_data.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        with (OUT_DIR / f"{save_prefix}_phases.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["time", "left_phase", "right_phase"])
            writer.writerows(phase_timeline)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--slope", type=float, default=0.0)
    parser.add_argument("--arm-mass", type=float, default=0.01)
    parser.add_argument("--arm-length", type=float, default=0.40)
    parser.add_argument("--arm-damping", type=float, default=0.02)
    parser.add_argument("--arm-stiffness", type=float, default=0.0)
    parser.add_argument(
        "--foot-radius",
        type=float,
        default=None,
        help="覆盖 PassiveArmsParams.foot_radius (默认沿用 V14 baseline=0.04)",
    )
    parser.add_argument(
        "--leg-scale",
        type=float,
        default=1.0,
        help="按比例缩放 thigh_length / shank_length / step_length，与 scan_v14c_C_foot_leg.py 一致",
    )
    parser.add_argument(
        "--save-prefix", "--prefix", dest="save_prefix", default="v14c_baseline"
    )
    args = parser.parse_args()

    base0 = PassiveArmsParams()
    overrides = dict(
        duration=args.duration,
        slope_deg=args.slope,
        arm_mass=args.arm_mass,
        arm_length=args.arm_length,
        arm_damping=args.arm_damping,
        arm_stiffness=args.arm_stiffness,
        thigh_length=float(base0.thigh_length * args.leg_scale),
        shank_length=float(base0.shank_length * args.leg_scale),
        step_length=float(base0.step_length * args.leg_scale),
    )
    if args.foot_radius is not None:
        overrides["foot_radius"] = float(args.foot_radius)
    base = replace(base0, **overrides)
    params = make_v14c_params(base)
    _, summary = run_simulation(params, save_prefix=args.save_prefix, sample_hz=160.0)
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "params"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

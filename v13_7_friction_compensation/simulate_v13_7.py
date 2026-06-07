"""V13.7: V13.6.1 FSM + 前馈库仑摩擦补偿 + L1 电机动力学。

在 V16 基础上，在 FSM 输出端加 τ_C_eff·sign_smooth(ω_joint) 前馈补偿项，
使电机模型的库仑摩擦扣减被精确对消。验证 mx64ar_full 在补偿后恢复行走。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import mujoco

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14C_DIR))

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
    V136Params,
    _mechanical_energy,
    control_v136,
)
from simulate_v14c import make_v14c_params  # noqa: E402

sys.path.insert(0, str(HW1_ROOT))
from common.motor_dynamics import (  # noqa: E402
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (
    L1MotorActuator,
    MotorParams,
    _sign_smooth,
    joint_armature_with_motor,
    joint_damping_with_motor,
)

OUT_DIR = ROOT / "out"
MODEL_DIR = OUT_DIR / "v13_7_models"
MODEL_PATH = MODEL_DIR / "friction_comp_walker.xml"

DEFAULT_BASE_ARMATURE = 0.004
PHASE_NAMES = ("stance_early", "stance_late", "swing_thrust", "swing_retract")


@dataclass(frozen=True)
class V137Params:
    base: PassiveArmsParams
    fsm: V136Params
    hip_motor: MotorParams = field(default_factory=lambda: MOTOR_PRESETS["mx64ar"])
    knee_motor: MotorParams = field(default_factory=lambda: MOTOR_PRESETS["mx64ar"])
    compensate_friction: bool = True


def _compensate(tau_fsm: float, omega_joint: float, motor: MotorParams) -> float:
    """前馈摩擦补偿：在 FSM 力矩上加 τ_C_eff·sign_smooth(ω) 以对消电机库仑摩擦。"""
    tau_C_eff = motor.joint_tau_C_eff()
    return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor.omega_eps)


def make_v137_fsm(base: PassiveArmsParams) -> V136Params:
    return make_v14c_params(base)


def build_model_xml_v137(p: V137Params) -> str:
    """注入电机折算 armature + damping 到 V14 XML。"""
    import re

    xml = build_model_xml(p.base)
    xml = xml.replace(
        'model="passive_arms_walker_v14"', 'model="friction_comp_walker_v137"'
    )

    hip_arm = joint_armature_with_motor(DEFAULT_BASE_ARMATURE, p.hip_motor)
    hip_damp = joint_damping_with_motor(p.base.hip_joint_damping, p.hip_motor)
    knee_arm = joint_armature_with_motor(DEFAULT_BASE_ARMATURE, p.knee_motor)
    knee_damp = joint_damping_with_motor(p.base.knee_damping, p.knee_motor)

    targets = [
        ("left_hip", hip_arm, hip_damp),
        ("right_hip", hip_arm, hip_damp),
        ("left_knee", knee_arm, knee_damp),
        ("right_knee", knee_arm, knee_damp),
    ]
    for jname, J, b in targets:
        new_xml, n = re.subn(
            rf'(<joint name="{jname}"[^/>]*?)damping="[^"]+"',
            rf'\1damping="{b:.6f}" armature="{J:.6f}"',
            xml,
            count=1,
        )
        if n != 1:
            raise RuntimeError(
                f"V13.7 XML injection failed for joint '{jname}': matched {n} times"
            )
        xml = new_xml
    return xml


def write_model_v137(p: V137Params, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml_v137(p), encoding="utf-8")


def _motor_summary(motor: MotorParams) -> dict:
    return {
        "name": motor.name,
        "Kt": motor.Kt,
        "J_rotor": motor.J_rotor,
        "N": motor.N,
        "eta": motor.eta,
        "I_max": motor.I_max,
        "I_cont": motor.I_cont,
        "R_arm": motor.R_arm,
        "tau_C_motor": motor.tau_C_motor,
        "b_visc_motor": motor.b_visc_motor,
        "joint_J_eff": motor.joint_J_eff(),
        "joint_b_eff": motor.joint_b_eff(),
        "joint_tau_C_eff": motor.joint_tau_C_eff(),
        "joint_tau_sat_peak": motor.joint_tau_sat_peak(),
        "joint_tau_sat_cont": motor.joint_tau_sat_cont(),
    }


def run_simulation_v137(
    params: V137Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
):
    p = params.base
    fsm = params.fsm
    write_model_v137(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, p)

    actuators = {
        "left_hip": L1MotorActuator(params.hip_motor),
        "left_knee": L1MotorActuator(params.knee_motor),
        "right_hip": L1MotorActuator(params.hip_motor),
        "right_knee": L1MotorActuator(params.knee_motor),
    }
    qvel_addr = {"left_hip": 2, "left_knee": 3, "right_hip": 5, "right_knee": 6}

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
    positive_input_energy_elec = 0.0
    coulomb_dissipation = 0.0
    rows: list[dict] = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    phase_timeline: list[tuple[float, str, str]] = []
    last_left_phase = ""
    last_right_phase = ""
    phase_durations = dict.fromkeys(PHASE_NAMES, 0.0)
    phase_torque_int = dict.fromkeys(PHASE_NAMES, 0.0)
    phase_saturation_steps = dict.fromkeys(PHASE_NAMES, 0)
    phase_total_steps = dict.fromkeys(PHASE_NAMES, 0)

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        E_current = _mechanical_energy(p, data)
        tau = control_v136(fsm, data, t, support_foot, burst_start_t, E_current)
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]
        left_phase = tau[5]
        right_phase = tau[6]
        eE_diag = tau[7]
        A_diag = tau[8]

        # --- V13.7 核心：前馈摩擦补偿 ---
        if params.compensate_friction:
            l_hip_des = _compensate(
                l_hip_des, float(data.qvel[qvel_addr["left_hip"]]), params.hip_motor
            )
            l_knee_des = _compensate(
                l_knee_des, float(data.qvel[qvel_addr["left_knee"]]), params.knee_motor
            )
            r_hip_des = _compensate(
                r_hip_des, float(data.qvel[qvel_addr["right_hip"]]), params.hip_motor
            )
            r_knee_des = _compensate(
                r_knee_des, float(data.qvel[qvel_addr["right_knee"]]), params.knee_motor
            )

        sat_before = {k: a.saturation_count for k, a in actuators.items()}
        l_hip_out, _ = actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(data.qvel[qvel_addr["left_hip"]])
        )
        l_knee_out, _ = actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(data.qvel[qvel_addr["left_knee"]])
        )
        r_hip_out, _ = actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(data.qvel[qvel_addr["right_hip"]])
        )
        r_knee_out, _ = actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(data.qvel[qvel_addr["right_knee"]])
        )
        data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

        omega = [
            float(data.qvel[qvel_addr[k]])
            for k in ("left_hip", "left_knee", "right_hip", "right_knee")
        ]
        tau_out = [l_hip_out, l_knee_out, r_hip_out, r_knee_out]
        tau_des = [l_hip_des, l_knee_des, r_hip_des, r_knee_des]

        input_power_mech = sum(tau_out[i] * omega[i] for i in range(4))
        positive_input_energy += max(0.0, input_power_mech) * p.timestep
        net_work += input_power_mech * p.timestep

        p_resistive_step = 0.0
        for key, t_des in zip(
            ("left_hip", "left_knee", "right_hip", "right_knee"), tau_des
        ):
            act = actuators[key]
            tau_after_sat = max(-act._tau_sat, min(act._tau_sat, t_des))
            if act._kt_joint > 0.0:
                i_motor = tau_after_sat / act._kt_joint
                p_resistive_step += i_motor * i_motor * act.motor.R_arm
        p_elec_step = max(0.0, input_power_mech) + p_resistive_step
        positive_input_energy_elec += p_elec_step * p.timestep

        for key, om in zip(("left_hip", "left_knee", "right_hip", "right_knee"), omega):
            act = actuators[key]
            coulomb_dissipation += act._tau_C_eff * abs(om) * p.timestep

        any_hip_sat_this_step = (
            actuators["left_hip"].saturation_count > sat_before["left_hip"]
            or actuators["right_hip"].saturation_count > sat_before["right_hip"]
        )

        phase_durations[left_phase] += p.timestep
        phase_durations[right_phase] += p.timestep
        phase_torque_int[left_phase] += abs(l_hip_out) * p.timestep
        phase_torque_int[right_phase] += abs(r_hip_out) * p.timestep
        phase_total_steps[left_phase] += 1
        phase_total_steps[right_phase] += 1
        if any_hip_sat_this_step:
            phase_saturation_steps[left_phase] += 1
            phase_saturation_steps[right_phase] += 1

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
                (l_hip_out, l_knee_out, r_hip_out, r_knee_out),
                input_power_mech,
                positive_input_energy,
            )
            row["E_current"] = float(E_current)
            row["e_E_swing"] = float(eE_diag)
            row["A_swing"] = float(A_diag)
            row["left_phase"] = left_phase
            row["right_phase"] = right_phase
            row["tau_l_hip_des"] = float(l_hip_des)
            row["tau_r_hip_des"] = float(r_hip_des)
            row["tau_l_hip_out"] = float(l_hip_out)
            row["tau_r_hip_out"] = float(r_hip_out)
            row["P_elec"] = float(p_elec_step)
            row["pos_input_energy_elec"] = float(positive_input_energy_elec)
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
        fallback["tau_l_hip_des"] = 0.0
        fallback["tau_r_hip_des"] = 0.0
        fallback["tau_l_hip_out"] = 0.0
        fallback["tau_r_hip_out"] = 0.0
        fallback["P_elec"] = 0.0
        fallback["pos_input_energy_elec"] = 0.0
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

    motor_saturation_count = {k: a.saturation_count for k, a in actuators.items()}
    phase_saturation_rate = {
        name: (
            (phase_saturation_steps[name] / phase_total_steps[name])
            if phase_total_steps[name] > 0
            else 0.0
        )
        for name in PHASE_NAMES
    }

    summary = {
        "params": asdict(p),
        "v136_phase_params": {
            "stance_early": asdict(fsm.stance_early),
            "stance_late": asdict(fsm.stance_late),
            "swing_thrust": asdict(fsm.swing_thrust),
            "swing_retract": asdict(fsm.swing_retract),
        },
        "v13_7_motor": {
            "hip": _motor_summary(params.hip_motor),
            "knee": _motor_summary(params.knee_motor),
        },
        "compensate_friction": params.compensate_friction,
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
        "active_input_energy_j": positive_input_energy,
        "active_input_energy_mech_j": positive_input_energy,
        "active_input_energy_elec_j": positive_input_energy_elec,
        "coulomb_friction_dissipation_j": coulomb_dissipation,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "total_mass_kg": p.total_mass,
        "phase_transitions": len(phase_timeline),
        "phase_durations_s": phase_durations,
        "phase_torque_integral_abs_Nms": phase_torque_int,
        "motor_saturation_count": motor_saturation_count,
        "phase_saturation_rate": phase_saturation_rate,
        "quasi_passive": True,
        "pure_passive": False,
        "passive_arms": True,
        "uses_reward_function": False,
        "controller": "v13_7_friction_compensated_fsm",
        "v137_actuator_model": "L1_motor_dynamics_with_feedforward_compensation",
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
    parser.add_argument("--foot-radius", type=float, default=0.042)
    parser.add_argument("--leg-scale", type=float, default=1.02)
    parser.add_argument(
        "--motor-preset", choices=list(MOTOR_PRESETS.keys()), default="mx64ar"
    )
    parser.add_argument(
        "--no-compensate", action="store_true", help="禁用摩擦补偿（用于 L0 回归对照）"
    )
    parser.add_argument(
        "--save-prefix", "--prefix", dest="save_prefix", default="v13_7_baseline"
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
        foot_radius=float(args.foot_radius),
    )
    base = replace(base0, **overrides)
    fsm = make_v137_fsm(base)
    motor = MOTOR_PRESETS[args.motor_preset]
    params = V137Params(
        base=base,
        fsm=fsm,
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=not args.no_compensate,
    )
    _, summary = run_simulation_v137(
        params, save_prefix=args.save_prefix, sample_hz=160.0
    )
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "params"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""V15.1L1: SEA direct-drive + L1 motor dynamics (Coulomb + saturation).

Combines V15.1 topology (motor_rotor → series spring → link) with V16 motor
model (J_eff, b_eff on motor joint; tau_sat + tau_C via L1MotorActuator).

Research question: does SEA compliance naturally buffer Coulomb friction,
allowing stable walking WITHOUT V13.7's feedforward compensation?
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
COMMON_DIR = HW1_ROOT / "common"
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v14 import (  # noqa: E402
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    PassiveArmsParams,
    classify_failure,
    contact_flags,
    foot_center_z_on_ramp,
    leg_ik_front_knee,
)
from simulate_passive_arms_v14 import (
    build_model_xml as build_model_xml_v14,
)
from simulate_v13_6 import (  # noqa: E402
    PhaseParams,
    V136Params,
    _mechanical_energy,
    control_v136,
)

from common.motor_dynamics import (
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (  # noqa: E402
    L1MotorActuator,
    MotorParams,
    _sign_smooth,
)

OUT_DIR = ROOT / "out"
MODEL_DIR_L1 = OUT_DIR / "v151L1_models"
MODEL_PATH_L1 = MODEL_DIR_L1 / "sea_motor_walker.xml"

QPOS_KEYS = [
    "hip_x",
    "hip_z",
    "left_hip_motor",
    "left_hip_link",
    "left_knee",
    "left_ankle",
    "right_hip_motor",
    "right_hip_link",
    "right_knee",
    "right_ankle",
    "left_arm",
    "right_arm",
]
QVEL_KEYS = [f"{k}_vel" for k in QPOS_KEYS]
QPOS_HIP_X, QPOS_HIP_Z = 0, 1
QPOS_L_MOTOR, QPOS_L_LINK, QPOS_L_KNEE = 2, 3, 4
QPOS_R_MOTOR, QPOS_R_LINK, QPOS_R_KNEE = 6, 7, 8


@dataclass(frozen=True)
class V151L1Params:
    base: PassiveArmsParams
    fsm: V136Params
    k_sea: float = 500.0
    c_sea: float = -1.0
    motor_rotor_mass: float = 0.01
    motor_rotor_iyy: float = 0.004
    motor_rotor_iiyt: float = 0.002
    motor_bearing_damping: float = 0.001
    timestep_override: float = -1.0
    motor_preset: str = "ideal"
    compensate_friction: bool = False

    @property
    def hip_motor(self) -> MotorParams:
        return MOTOR_PRESETS[self.motor_preset]

    @property
    def knee_motor(self) -> MotorParams:
        return MOTOR_PRESETS[self.motor_preset]

    @property
    def damping_resolved(self) -> float:
        if self.c_sea >= 0:
            return float(self.c_sea)
        return 0.1 * 2.0 * math.sqrt(max(self.k_sea, 1e-9) * self.motor_rotor_iyy)

    @property
    def timestep_resolved(self) -> float:
        if self.timestep_override > 0:
            return float(self.timestep_override)
        if self.k_sea >= 5e3:
            return 0.0005
        return float(self.base.timestep)


def make_v151L1_fsm(base: PassiveArmsParams) -> V136Params:
    """V13.6.1 best candidate 6."""
    defaults = V136Params()
    return V136Params(
        base=base,
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


def build_model_xml_v151_L1(p: V151L1Params) -> str:
    """SEA topology + motor dynamics on motor joint and knee joints."""
    base_xml = build_model_xml_v14(p.base)
    k_sea = float(p.k_sea)
    c_sea = float(p.damping_resolved)
    motor_damp = float(p.motor_bearing_damping)
    rotor_mass = float(p.motor_rotor_mass)
    iyy = float(p.motor_rotor_iyy)
    iiyt = float(p.motor_rotor_iiyt)
    timestep = float(p.timestep_resolved)
    hjd = float(p.base.hip_joint_damping)

    hip_m = p.hip_motor
    hip_arm = hip_m.joint_J_eff()
    hip_damp_total = motor_damp + hip_m.joint_b_eff()

    xml = base_xml.replace(
        'model="passive_arms_walker_v14"',
        'model="sea_motor_walker_v151L1"',
    )
    xml = re.sub(
        r'<option timestep="[^"]*"',
        f'<option timestep="{timestep}"',
        xml,
        count=1,
    )

    def insert_rotor(s: str, side: str, lat: float) -> str:
        old = (
            f'<body name="{side}_thigh" pos="0 {lat} 0">\n'
            f'        <joint name="{side}_hip" type="hinge" axis="0 1 0" '
            f'range="-95 95" limited="true" damping="{hjd}"/>'
        )
        new = (
            f'<body name="{side}_motor_rotor" pos="0 {lat} 0">\n'
            f'        <inertial pos="0 0 0" mass="{rotor_mass}" '
            f'diaginertia="{iiyt} {iyy} {iiyt}"/>\n'
            f'        <joint name="{side}_hip_motor" type="hinge" axis="0 1 0" '
            f'range="-95 95" limited="true" armature="{hip_arm}" damping="{hip_damp_total}"/>\n'
            f'        <body name="{side}_thigh" pos="0 0 0">\n'
            f'        <joint name="{side}_hip_link" type="hinge" axis="0 1 0" '
            f'range="-95 95" limited="true" armature="0" '
            f'damping="{c_sea}" stiffness="{k_sea}" springref="0"/>'
        )
        if old not in s:
            raise RuntimeError(f"V151L1 XML anchor not found for side={side}")
        return s.replace(old, new, 1)

    xml = insert_rotor(xml, "left", -0.055)
    xml = insert_rotor(xml, "right", 0.055)

    xml = xml.replace(
        '      <body name="right_motor_rotor"',
        '      </body>\n      <body name="right_motor_rotor"',
        1,
    )
    xml = xml.replace(
        '      <body name="left_arm"',
        '      </body>\n      <body name="left_arm"',
        1,
    )
    xml = xml.replace(
        '<motor name="left_hip_muscle" joint="left_hip"',
        '<motor name="left_hip_muscle" joint="left_hip_motor"',
        1,
    )
    xml = xml.replace(
        '<motor name="right_hip_muscle" joint="right_hip"',
        '<motor name="right_hip_muscle" joint="right_hip_motor"',
        1,
    )

    # Inject knee motor dynamics (armature + damping) same as V16
    knee_m = p.knee_motor
    knee_J = knee_m.joint_J_eff()
    knee_b = knee_m.joint_b_eff()
    if knee_J > 0 or knee_b > 0:
        for side in ("left", "right"):
            old_knee = f'<joint name="{side}_knee" type="hinge" axis="0 1 0" range="0 70.0" limited="true" damping="{p.base.knee_damping}" stiffness="{p.base.knee_stiffness}"'
            new_damp = p.base.knee_damping + knee_b
            new_arm_str = f' armature="{knee_J}"' if knee_J > 0 else ""
            new_knee = f'<joint name="{side}_knee" type="hinge" axis="0 1 0" range="0 70.0" limited="true" damping="{new_damp}" stiffness="{p.base.knee_stiffness}"{new_arm_str}'
            if old_knee in xml:
                xml = xml.replace(old_knee, new_knee, 1)

    return xml


def write_model_v151_L1(p: V151L1Params, path: Path = MODEL_PATH_L1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml_v151_L1(p), encoding="utf-8")


def initialize_v151_L1(model, data, p: PassiveArmsParams) -> None:
    u_release = float(np.clip(p.release_phase, 0.0, 1.0))
    u_release = u_release * u_release * (3.0 - 2.0 * u_release)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    support_x = 0.0
    support_z = foot_center_z_on_ramp(support_x, p)
    left_hip = p.gamma + alpha - 2.0 * alpha * u_release
    hip_x = support_x + p.leg_length * math.sin(left_hip)
    hip_z = support_z + p.leg_length * math.cos(left_hip)
    right_hip, right_knee = leg_ik_front_knee(
        hip_x,
        hip_z,
        p.swing_foot_x,
        foot_center_z_on_ramp(p.swing_foot_x, p) + p.swing_foot_clearance,
        p,
    )
    arm_init = math.radians(p.arm_init_deg)
    data.qpos[:] = [
        hip_x,
        hip_z,
        left_hip,
        0.0,
        0.0,
        0.0,
        right_hip,
        0.0,
        right_knee,
        0.0,
        -arm_init,
        arm_init,
    ]
    data.qvel[:] = [
        p.initial_vx,
        -math.tan(p.gamma) * p.initial_vx,
        0.04,
        0.0,
        0.0,
        0.0,
        p.swing_hip_vel,
        0.0,
        p.swing_knee_vel,
        0.0,
        0.0,
        0.0,
    ]
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)


class _FsmDataView:
    """Maps nq=12 SEA layout to FSM's expected nq=7 view (absolute angles)."""

    def __init__(self, model, real_data):
        def jq(name):
            return int(
                model.jnt_qposadr[
                    mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
                ]
            )

        def jd(name):
            return int(
                model.jnt_dofadr[
                    mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
                ]
            )

        self._real = real_data
        self._q_l_motor = jq("left_hip_motor")
        self._q_l_link = jq("left_hip_link")
        self._q_l_knee = jq("left_knee")
        self._q_r_motor = jq("right_hip_motor")
        self._q_r_link = jq("right_hip_link")
        self._q_r_knee = jq("right_knee")
        self._d_l_motor = jd("left_hip_motor")
        self._d_l_link = jd("left_hip_link")
        self._d_l_knee = jd("left_knee")
        self._d_r_motor = jd("right_hip_motor")
        self._d_r_link = jd("right_hip_link")
        self._d_r_knee = jd("right_knee")
        self._qpos_buf = np.zeros(7, dtype=float)
        self._qvel_buf = np.zeros(7, dtype=float)
        self.refresh()

    def refresh(self) -> None:
        rq = self._real.qpos
        rv = self._real.qvel
        self._qpos_buf[0] = rq[QPOS_HIP_X]
        self._qpos_buf[1] = rq[QPOS_HIP_Z]
        self._qpos_buf[2] = rq[self._q_l_motor] + rq[self._q_l_link]
        self._qpos_buf[3] = rq[self._q_l_knee]
        self._qpos_buf[4] = 0.0
        self._qpos_buf[5] = rq[self._q_r_motor] + rq[self._q_r_link]
        self._qpos_buf[6] = rq[self._q_r_knee]
        self._qvel_buf[0] = rv[0]
        self._qvel_buf[1] = rv[1]
        self._qvel_buf[2] = rv[self._d_l_motor] + rv[self._d_l_link]
        self._qvel_buf[3] = rv[self._d_l_knee]
        self._qvel_buf[4] = 0.0
        self._qvel_buf[5] = rv[self._d_r_motor] + rv[self._d_r_link]
        self._qvel_buf[6] = rv[self._d_r_knee]

    @property
    def qpos(self):
        return self._qpos_buf

    @property
    def qvel(self):
        return self._qvel_buf


def run_simulation_v151_L1(
    params: V151L1Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
):
    p = params.base
    write_model_v151_L1(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH_L1))
    data = mujoco.MjData(model)
    initialize_v151_L1(model, data, p)
    fsm_view = _FsmDataView(model, data)

    timestep = float(params.timestep_resolved)
    k_sea = float(params.k_sea)
    c_sea = float(params.damping_resolved)
    hip_lim = float(p.hip_torque_limit)

    d_l_motor = fsm_view._d_l_motor
    d_l_link = fsm_view._d_l_link
    d_r_motor = fsm_view._d_r_motor
    d_r_link = fsm_view._d_r_link
    d_l_knee = fsm_view._d_l_knee
    d_r_knee = fsm_view._d_r_knee
    q_l_link = fsm_view._q_l_link
    q_r_link = fsm_view._q_r_link

    hip_actuator = L1MotorActuator(params.hip_motor)
    knee_actuator = L1MotorActuator(params.knee_motor)
    compensate = params.compensate_friction
    tau_C_hip = params.hip_motor.joint_tau_C_eff()
    tau_C_knee = params.knee_motor.joint_tau_C_eff()
    eps_hip = params.hip_motor.omega_eps
    eps_knee = params.knee_motor.omega_eps

    start_x = float(data.qpos[QPOS_HIP_X])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -p.gait_period
    alternations = 0
    contact_events: list = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (timestep * sample_hz))))

    spring_pe_max = 0.0
    q_link_max_left = 0.0
    q_link_max_right = 0.0
    coulomb_dissipation = 0.0

    n_steps = int(p.duration / timestep)
    for step in range(n_steps):
        t = step * timestep
        E_current = _mechanical_energy(p, data)
        fsm_view.refresh()
        tau = control_v136(
            params.fsm, fsm_view, t, support_foot, burst_start_t, E_current
        )
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]

        qd_motor_l = float(data.qvel[d_l_motor])
        qd_motor_r = float(data.qvel[d_r_motor])
        qd_knee_l = float(data.qvel[d_l_knee])
        qd_knee_r = float(data.qvel[d_r_knee])
        ql_link = float(data.qpos[q_l_link])
        qr_link = float(data.qpos[q_r_link])

        if compensate:
            l_hip_des += tau_C_hip * _sign_smooth(qd_motor_l, eps_hip)
            r_hip_des += tau_C_hip * _sign_smooth(qd_motor_r, eps_hip)
            l_knee_des += tau_C_knee * _sign_smooth(qd_knee_l, eps_knee)
            r_knee_des += tau_C_knee * _sign_smooth(qd_knee_r, eps_knee)

        l_hip_out, _ = hip_actuator.compute_actual_torque(l_hip_des, qd_motor_l)
        r_hip_out, _ = hip_actuator.compute_actual_torque(r_hip_des, qd_motor_r)
        l_knee_out, _ = knee_actuator.compute_actual_torque(l_knee_des, qd_knee_l)
        r_knee_out, _ = knee_actuator.compute_actual_torque(r_knee_des, qd_knee_r)

        data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

        input_power = (
            l_hip_out * qd_motor_l
            + l_knee_out * qd_knee_l
            + r_hip_out * qd_motor_r
            + r_knee_out * qd_knee_r
        )
        positive_input_energy += max(0.0, input_power) * timestep
        net_work += input_power * timestep

        spring_pe = 0.5 * k_sea * (ql_link**2 + qr_link**2)
        spring_pe_max = max(spring_pe_max, spring_pe)
        q_link_max_left = max(q_link_max_left, abs(ql_link))
        q_link_max_right = max(q_link_max_right, abs(qr_link))
        coulomb_dissipation += (
            tau_C_hip * (abs(qd_motor_l) + abs(qd_motor_r)) * timestep
        )

        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[QPOS_HIP_X]))

        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: list = []
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
            rows.append({"time": t, "hip_x": float(data.qpos[QPOS_HIP_X])})

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    simulated_time = t if rows else 0.0
    forward = max_x - start_x
    success = (
        simulated_time >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and not failure
    )

    summary = {
        "motor_preset": params.motor_preset,
        "compensate_friction": params.compensate_friction,
        "k_sea": k_sea,
        "success": success,
        "alternating_touchdowns": alternations,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "active_input_energy_j": positive_input_energy,
        "spring_pe_max_J": spring_pe_max,
        "q_link_max_left_deg": math.degrees(q_link_max_left),
        "q_link_max_right_deg": math.degrees(q_link_max_right),
        "hip_saturation_count": hip_actuator.saturation_count,
        "knee_saturation_count": knee_actuator.saturation_count,
        "coulomb_dissipation_J": coulomb_dissipation,
        "tau_C_hip_Nm": tau_C_hip,
        "tau_sat_hip_Nm": params.hip_motor.joint_tau_sat_peak(),
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="V15.1L1 SEA + motor dynamics")
    parser.add_argument("--k-sea", type=float, default=500.0)
    parser.add_argument(
        "--motor-preset", default="ideal", choices=list(MOTOR_PRESETS.keys())
    )
    parser.add_argument("--compensate", action="store_true")
    parser.add_argument("--foot-radius", type=float, default=0.042)
    parser.add_argument("--leg-scale", type=float, default=1.02)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--save-prefix", default="v151L1_test")
    args = parser.parse_args()

    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=args.duration,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=args.foot_radius,
        thigh_length=base0.thigh_length * args.leg_scale,
        shank_length=base0.shank_length * args.leg_scale,
        step_length=base0.step_length * args.leg_scale,
    )
    params = V151L1Params(
        base=base,
        fsm=make_v151L1_fsm(base),
        k_sea=args.k_sea,
        motor_preset=args.motor_preset,
        compensate_friction=args.compensate,
    )
    summary = run_simulation_v151_L1(params, save_prefix=args.save_prefix)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

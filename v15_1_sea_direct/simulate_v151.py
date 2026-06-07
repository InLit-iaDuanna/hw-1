"""V15.1 SEA direct-drive: motor_rotor body + series spring, no inner loop.

Fork of V15.2 topology with two critical fixes:
1. _FsmDataView feeds ABSOLUTE hip angles (q_motor + q_link) to FSM
2. Direct torque passthrough (no Pratt inner loop, ctrl_limit = base 4 N·m)

Series spring sits between motor rotor and thigh link. When k_sea -> inf,
q_link -> 0 and the system degenerates to V14c (direct drive).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v14 import (  # noqa: E402
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    PassiveArmsParams,
    actuator_names,
    classify_failure,
    contact_flags,
    foot_center_z_on_ramp,
    foot_contact_detail,
    leg_ik_front_knee,
    ramp_height,
    site_margin,
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

OUT_DIR = ROOT / "out"
MODEL_DIR = OUT_DIR / "v151_models"
MODEL_PATH = MODEL_DIR / "sea_direct_walker.xml"
QPOS_KEYS_V151 = [
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
QVEL_KEYS_V151 = [f"{k}_vel" for k in QPOS_KEYS_V151]

QPOS_HIP_X = 0
QPOS_HIP_Z = 1
QPOS_L_MOTOR = 2
QPOS_L_LINK = 3
QPOS_L_KNEE = 4
QPOS_L_ANKLE = 5
QPOS_R_MOTOR = 6
QPOS_R_LINK = 7
QPOS_R_KNEE = 8
QPOS_R_ANKLE = 9
QPOS_L_ARM = 10
QPOS_R_ARM = 11

ENERGY_MODEL_NOTE = (
    "V15.1 SEA direct-drive: motor applies FSM torque directly; link couples "
    "through series hinge spring. Energy audit: "
    "W_motor_input - W_link_useful - W_damper_loss - dPE_spring ~ 0."
)


@dataclass(frozen=True)
class V151Params:
    base: PassiveArmsParams
    fsm: V136Params
    k_sea: float = 1000.0
    c_sea: float = -1.0  # <0 => auto subcritical damping
    motor_rotor_mass: float = 0.01
    motor_rotor_iyy: float = 0.004
    motor_rotor_iiyt: float = 0.002
    motor_bearing_damping: float = 0.001
    timestep_override: float = -1.0

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


def make_v151_fsm(base: PassiveArmsParams) -> V136Params:
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


def build_model_xml_v151(p: V151Params) -> str:
    """Insert motor_rotor body between hip and thigh; spring on link joint."""
    base_xml = build_model_xml_v14(p.base)
    k_sea = float(p.k_sea)
    c_sea = float(p.damping_resolved)
    motor_damp = float(p.motor_bearing_damping)
    rotor_mass = float(p.motor_rotor_mass)
    iyy = float(p.motor_rotor_iyy)
    iiyt = float(p.motor_rotor_iiyt)
    timestep = float(p.timestep_resolved)
    hjd = float(p.base.hip_joint_damping)
    hip_lim = float(p.base.hip_torque_limit)

    xml = base_xml.replace(
        'model="passive_arms_walker_v14"',
        'model="sea_direct_walker_v151"',
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
            f'range="-95 95" limited="true" armature="0" damping="{motor_damp}"/>\n'
            f'        <body name="{side}_thigh" pos="0 0 0">\n'
            f'        <joint name="{side}_hip_link" type="hinge" axis="0 1 0" '
            f'range="-95 95" limited="true" armature="0" '
            f'damping="{c_sea}" stiffness="{k_sea}" springref="0"/>'
        )
        if old not in s:
            raise RuntimeError(f"V15.1 XML anchor not found for side={side}")
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
    return xml


def write_model_v151(p: V151Params, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml_v151(p), encoding="utf-8")


def initialize_v151(model, data, p: PassiveArmsParams) -> None:
    """nq=12 init: motor carries full hip angle, link at 0 (zero spring deflection)."""
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
    """Map nq=12 SEA layout to nq=7 view expected by control_v136.

    Critical fix vs V15.2: feeds ABSOLUTE hip angles (q_motor + q_link)
    so the FSM sees the real thigh orientation, not just spring deflection.
    """

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


def make_row_v151(
    model, data, p: PassiveArmsParams, t, lc, rc, support, mode, tau, in_p, in_e
):
    out: dict = {"time": t}
    for k, v in zip(QPOS_KEYS_V151, data.qpos):
        out[k] = float(v)
    for k, v in zip(QVEL_KEYS_V151, data.qvel):
        out[k] = float(v)
    d = foot_contact_detail(model, data)
    out.update(
        {
            "left_contact": int(lc),
            "right_contact": int(rc),
            "left_heel_contact": int(d["left_heel"]),
            "left_sole_contact": int(d["left_sole"]),
            "left_toe_contact": int(d["left_toe"]),
            "right_heel_contact": int(d["right_heel"]),
            "right_sole_contact": int(d["right_sole"]),
            "right_toe_contact": int(d["right_toe"]),
            "support_foot": support,
            "mode": mode,
            "left_margin": site_margin(model, data, "left_foot_site", p),
            "right_margin": site_margin(model, data, "right_foot_site", p),
            "left_heel_margin": site_margin(model, data, "left_heel_site", p),
            "left_toe_margin": site_margin(model, data, "left_toe_site", p),
            "right_heel_margin": site_margin(model, data, "right_heel_site", p),
            "right_toe_margin": site_margin(model, data, "right_toe_site", p),
            "hip_clearance": float(data.qpos[QPOS_HIP_Z])
            - ramp_height(float(data.qpos[QPOS_HIP_X]), p),
            "left_hip_tau": tau[0],
            "left_knee_tau": tau[1],
            "left_ankle_tau": 0.0,
            "right_hip_tau": tau[2],
            "right_knee_tau": tau[3],
            "right_ankle_tau": 0.0,
            "left_arm_tau": 0.0,
            "right_arm_tau": 0.0,
            "input_power": in_p,
            "input_energy": in_e,
        }
    )
    return out


def run_simulation_v151(
    params: V151Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
):
    """V15.1 SEA direct-drive main loop."""
    p = params.base
    write_model_v151(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize_v151(model, data, p)
    fsm_view = _FsmDataView(model, data)

    timestep = float(params.timestep_resolved)
    k_sea = float(params.k_sea)
    c_sea = float(params.damping_resolved)
    d_l_link = fsm_view._d_l_link
    d_l_motor = fsm_view._d_l_motor
    d_r_link = fsm_view._d_r_link
    d_r_motor = fsm_view._d_r_motor
    q_l_link = fsm_view._q_l_link
    q_r_link = fsm_view._q_r_link
    d_l_knee = fsm_view._d_l_knee
    d_r_knee = fsm_view._d_r_knee
    hip_lim = float(p.hip_torque_limit)

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

    phase_timeline: list = []
    last_left_phase = ""
    last_right_phase = ""
    phase_durations = {
        "stance_early": 0.0,
        "stance_late": 0.0,
        "swing_thrust": 0.0,
        "swing_retract": 0.0,
    }
    phase_torque_int = dict.fromkeys(phase_durations, 0.0)

    W_motor_input = 0.0
    W_link_useful = 0.0
    W_damper_loss = 0.0
    spring_pe_max = 0.0
    spring_pe_sum = 0.0
    q_link_max_left = 0.0
    q_link_max_right = 0.0
    audit_samples = 0
    pe_spring_initial = (
        0.5
        * k_sea
        * (float(data.qpos[q_l_link]) ** 2 + float(data.qpos[q_r_link]) ** 2)
    )

    n_steps = int(p.duration / timestep)
    for step in range(n_steps):
        t = step * timestep
        E_current = _mechanical_energy(p, data)
        fsm_view.refresh()
        tau = control_v136(
            params.fsm, fsm_view, t, support_foot, burst_start_t, E_current
        )
        l_hip_des, l_knee, r_hip_des, r_knee = tau[0], tau[1], tau[2], tau[3]
        mode_label, left_phase, right_phase = tau[4], tau[5], tau[6]
        eE_diag, A_diag = tau[7], tau[8]

        qd_motor_l = float(data.qvel[d_l_motor])
        qd_motor_r = float(data.qvel[d_r_motor])
        qd_link_l = float(data.qvel[d_l_link])
        qd_link_r = float(data.qvel[d_r_link])
        qd_knee_l = float(data.qvel[d_l_knee])
        qd_knee_r = float(data.qvel[d_r_knee])
        ql_link = float(data.qpos[q_l_link])
        qr_link = float(data.qpos[q_r_link])

        tau_spring_l = -k_sea * ql_link - c_sea * qd_link_l
        tau_spring_r = -k_sea * qr_link - c_sea * qd_link_r

        # Direct torque passthrough — no inner loop
        motor_force_l = float(np.clip(l_hip_des, -hip_lim, hip_lim))
        motor_force_r = float(np.clip(r_hip_des, -hip_lim, hip_lim))
        data.ctrl[:] = (motor_force_l, l_knee, motor_force_r, r_knee)

        input_power = (
            motor_force_l * qd_motor_l
            + l_knee * qd_knee_l
            + motor_force_r * qd_motor_r
            + r_knee * qd_knee_r
        )
        positive_input_energy += max(0.0, input_power) * timestep
        net_work += input_power * timestep

        W_motor_input += (
            motor_force_l * qd_motor_l + motor_force_r * qd_motor_r
        ) * timestep
        W_link_useful += (
            tau_spring_l * qd_link_l + tau_spring_r * qd_link_r
        ) * timestep
        W_damper_loss += c_sea * (qd_link_l**2 + qd_link_r**2) * timestep
        spring_pe = 0.5 * k_sea * (ql_link**2 + qr_link**2)
        spring_pe_max = max(spring_pe_max, spring_pe)
        spring_pe_sum += spring_pe
        audit_samples += 1
        q_link_max_left = max(q_link_max_left, abs(ql_link))
        q_link_max_right = max(q_link_max_right, abs(qr_link))

        phase_durations[left_phase] += timestep
        phase_durations[right_phase] += timestep
        phase_torque_int[left_phase] += abs(l_hip_des) * timestep
        phase_torque_int[right_phase] += abs(r_hip_des) * timestep
        if (left_phase != last_left_phase) or (right_phase != last_right_phase):
            phase_timeline.append((t, left_phase, right_phase))
            last_left_phase, last_right_phase = left_phase, right_phase

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
            row = make_row_v151(
                model,
                data,
                p,
                t,
                left_contact,
                right_contact,
                support_foot,
                mode_label,
                (tau_spring_l, l_knee, tau_spring_r, r_knee),
                input_power,
                positive_input_energy,
            )
            row["E_current"] = float(E_current)
            row["e_E_swing"] = float(eE_diag)
            row["A_swing"] = float(A_diag)
            row["left_phase"] = left_phase
            row["right_phase"] = right_phase
            row["spring_PE_link_J"] = float(spring_pe)
            row["q_link_left_deg"] = math.degrees(ql_link)
            row["q_link_right_deg"] = math.degrees(qr_link)
            row["q_motor_left_deg"] = math.degrees(float(data.qpos[QPOS_L_MOTOR]))
            row["q_motor_right_deg"] = math.degrees(float(data.qpos[QPOS_R_MOTOR]))
            row["motor_force_left"] = float(motor_force_l)
            row["motor_force_right"] = float(motor_force_r)
            rows.append(row)

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        fallback = make_row_v151(
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
        fallback["spring_PE_link_J"] = float(pe_spring_initial)
        fallback["q_link_left_deg"] = 0.0
        fallback["q_link_right_deg"] = 0.0
        fallback["q_motor_left_deg"] = 0.0
        fallback["q_motor_right_deg"] = 0.0
        fallback["motor_force_left"] = 0.0
        fallback["motor_force_right"] = 0.0
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

    pe_spring_final = (
        0.5
        * k_sea
        * (float(data.qpos[q_l_link]) ** 2 + float(data.qpos[q_r_link]) ** 2)
    )
    dPE_spring = pe_spring_final - pe_spring_initial

    energy_audit = {
        "W_motor_input_J": W_motor_input,
        "W_link_useful_J": W_link_useful,
        "W_damper_loss_J": W_damper_loss,
        "dPE_spring_J": dPE_spring,
        "PE_spring_initial_J": pe_spring_initial,
        "PE_spring_final_J": pe_spring_final,
    }

    summary = {
        "params": asdict(p),
        "v151_extra": {
            "k_sea": k_sea,
            "c_sea": c_sea,
            "motor_rotor_mass": float(params.motor_rotor_mass),
            "motor_rotor_iyy": float(params.motor_rotor_iyy),
            "motor_bearing_damping": float(params.motor_bearing_damping),
            "timestep_used": timestep,
            "spring_pe_max_J": spring_pe_max,
            "spring_pe_mean_J": spring_pe_sum / max(1, audit_samples),
            "q_link_max_left_deg": math.degrees(q_link_max_left),
            "q_link_max_right_deg": math.degrees(q_link_max_right),
            "energy_audit": energy_audit,
        },
        "v136_phase_params": {
            "stance_early": asdict(params.fsm.stance_early),
            "stance_late": asdict(params.fsm.stance_late),
            "swing_thrust": asdict(params.fsm.swing_thrust),
            "swing_retract": asdict(params.fsm.swing_retract),
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
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "total_mass_kg": p.total_mass,
        "phase_transitions": len(phase_timeline),
        "phase_durations_s": phase_durations,
        "phase_torque_integral_abs_Nms": phase_torque_int,
        "controller_energy_model": {
            "mass_eff_kg": float(p.hip_mass + 2.0 * p.torso_mass),
            "note": ENERGY_MODEL_NOTE,
        },
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v13_6_1_best_fsm_via_FsmDataView_absolute_angles",
        "topology": "sea_direct_drive_motor_rotor_series_spring",
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
    parser = argparse.ArgumentParser(description="V15.1 SEA direct-drive simulate")
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--slope", type=float, default=0.0)
    parser.add_argument("--arm-mass", type=float, default=0.01)
    parser.add_argument("--arm-length", type=float, default=0.40)
    parser.add_argument("--arm-damping", type=float, default=0.02)
    parser.add_argument("--arm-stiffness", type=float, default=0.0)
    parser.add_argument("--foot-radius", type=float, default=None)
    parser.add_argument("--leg-scale", type=float, default=1.0)
    parser.add_argument("--k-sea", type=float, default=1000.0)
    parser.add_argument("--c-sea", type=float, default=-1.0)
    parser.add_argument("--rotor-mass", type=float, default=0.01)
    parser.add_argument("--rotor-iyy", type=float, default=0.004)
    parser.add_argument("--rotor-iiyt", type=float, default=0.002)
    parser.add_argument("--motor-damp", type=float, default=0.001)
    parser.add_argument("--timestep", type=float, default=-1.0)
    parser.add_argument(
        "--save-prefix", "--prefix", dest="save_prefix", default="v151_smoke"
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
    params = V151Params(
        base=base,
        fsm=make_v151_fsm(base),
        k_sea=float(args.k_sea),
        c_sea=float(args.c_sea),
        motor_rotor_mass=float(args.rotor_mass),
        motor_rotor_iyy=float(args.rotor_iyy),
        motor_rotor_iiyt=float(args.rotor_iiyt),
        motor_bearing_damping=float(args.motor_damp),
        timestep_override=float(args.timestep),
    )
    _, summary = run_simulation_v151(
        params, save_prefix=args.save_prefix, sample_hz=160.0
    )
    show = {k: v for k, v in summary.items() if k != "params"}
    print(json.dumps(show, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

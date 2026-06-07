"""V15.2 严格 SEA：hip 插入 motor_rotor 刚体 + series elastic spring。

电机端 q_motor 与连杆端 q_link 通过 hip-axis 弹簧串联耦合，区别于 V15.0
PEA prototype（fixed tendon 单关节并联弹簧）。FSM 控制律 (V13.6.1 best) 不变，
通过 _FsmDataView 适配 nq=12 新自由度布局。

仍属准被动 + 弹性元件：hip motor + V13.6.1 FSM 闭环全保留，不可宣称纯被动
或被动恢复。
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
MODEL_DIR = OUT_DIR / "v152_models"
MODEL_PATH = MODEL_DIR / "strict_sea_walker.xml"

# nq=12 布局（依据 MuJoCo body tree 顺序遍历）
QPOS_KEYS_V152 = [
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
QVEL_KEYS_V152 = [f"{k}_vel" for k in QPOS_KEYS_V152]

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
    "V15.2 strict SEA: actuator drives motor_rotor (q_motor); link side (q_link) "
    "couples through hip-axis hinge spring. Energy audit: "
    "W_motor_input - W_link_useful - W_damper_loss - dPE_spring ~ 0."
)


@dataclass(frozen=True)
class V152Params:
    base: PassiveArmsParams
    fsm: V136Params
    k_sea: float = 1000.0
    c_sea: float = -1.0
    motor_rotor_mass: float = 0.05
    motor_rotor_iyy: float = 0.004
    motor_rotor_iiyt: float = 0.0021
    motor_bearing_damping: float = 0.02
    timestep_override: float = -1.0
    # SEA inner torque-control loop：FSM 输出 τ_desired 当 spring 期望扭矩，内环
    # 用 spring 形变 + motor 加速度反馈算电机力。motor_ctrl_limit 单独放大，
    # 因为 motor 端要同时克服弹簧反作用 + 加速自身。
    motor_ctrl_limit: float = 30.0
    # 标准 SEA inner loop（Pratt 1995 等价形式）：motor 位置 PD 跟踪
    # u = Kp_pos * (q_link + τ_desired/k_sea) - Kd_motor * qd_motor
    # 含义：要 spring force = τ_desired 稳态 ⇒ q_link 稳态 = -τ_desired/k_sea ⇒
    #       motor 必须"超前" link 一个 τ_desired/k_sea，即 q_motor_target - q_motor = q_link + τ_desired/k_sea
    inner_kp_pos: float = 1000.0  # N·m/rad，motor 位置 P 增益
    inner_kd_motor: float = -1.0  # <0 自动取 ζ=0.7 临界
    inner_zeta: float = 0.7

    @property
    def inner_kd_resolved(self) -> float:
        if self.inner_kd_motor >= 0:
            return float(self.inner_kd_motor)
        # ω_n = sqrt(Kp_pos / I), Kd = 2*ζ*I*ω_n = 2*ζ*sqrt(Kp_pos * I)
        return (
            2.0
            * self.inner_zeta
            * math.sqrt(max(self.inner_kp_pos, 1e-9) * max(self.motor_rotor_iyy, 1e-9))
        )

    @property
    def damping_resolved(self) -> float:
        if self.c_sea >= 0:
            return float(self.c_sea)
        # 0.2 倍临界阻尼（亚阻尼，弹簧响应可观测）
        return 0.2 * 2.0 * math.sqrt(max(self.k_sea, 1e-9) * self.motor_rotor_iyy)

    @property
    def timestep_resolved(self) -> float:
        if self.timestep_override > 0:
            return float(self.timestep_override)
        if self.k_sea >= 5e3:
            return 0.0005
        return float(self.base.timestep)


def make_v152_fsm(base: PassiveArmsParams) -> V136Params:
    """V13.6.1 best candidate 6 (与 V14c/V15.0 一致)。"""
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


def build_model_xml_v152(p: V152Params) -> str:
    """从 V14 base XML re.sub 改造为 V15.2 strict SEA 拓扑。

    在 hip ↔ thigh 之间插入 motor_rotor body：
      motor_rotor (mass + diaginertia, 实体化反射惯量)
        joint *_hip_motor (armature=0)  ← actuator 挂这里
        thigh body (pos=0 0 0)
          joint *_hip_link (armature=0, stiffness=k_sea, damping=c_sea)
          原 shank/foot 子树原样
    """
    base_xml = build_model_xml_v14(p.base)
    k_sea = float(p.k_sea)
    c_sea = float(p.damping_resolved)
    motor_damp = float(p.motor_bearing_damping)
    rotor_mass = float(p.motor_rotor_mass)
    iyy = float(p.motor_rotor_iyy)
    iiyt = float(p.motor_rotor_iiyt)
    timestep = float(p.timestep_resolved)
    hjd = float(p.base.hip_joint_damping)

    xml = base_xml.replace(
        'model="passive_arms_walker_v14"',
        'model="strict_sea_walker_v152"',
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
            raise RuntimeError(f"V15.2 XML anchor not found for side={side}")
        return s.replace(old, new, 1)

    xml = insert_rotor(xml, "left", -0.055)
    xml = insert_rotor(xml, "right", 0.055)

    # 闭合 motor_rotor: 在 right_motor_rotor / left_arm 开标签前插一个 </body>
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

    # actuator joint 改名：hip motor 挂在 motor body 关节上
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
    # hip motor ctrlrange 单独放大（克服弹簧反作用 + 加速 motor）
    motor_lim = float(p.motor_ctrl_limit)
    base_lim = max(p.base.hip_torque_limit, p.base.knee_torque_limit, 1.0)
    base_range = f'ctrlrange="-{base_lim} {base_lim}"'
    new_range = f'ctrlrange="-{motor_lim} {motor_lim}"'
    for side in ("left", "right"):
        anchor = f'<motor name="{side}_hip_muscle" joint="{side}_hip_motor" gear="1" ctrllimited="true" {base_range}'
        target = f'<motor name="{side}_hip_muscle" joint="{side}_hip_motor" gear="1" ctrllimited="true" {new_range}'
        if anchor not in xml:
            raise RuntimeError(
                f"V15.2 actuator ctrlrange anchor not found for side={side}"
            )
        xml = xml.replace(anchor, target, 1)
    return xml


def write_model_v152(p: V152Params, path: Path = MODEL_PATH) -> None:
    resolved_path = path.resolve()
    resolved_model_dir = MODEL_DIR.resolve()
    if resolved_model_dir not in (resolved_path, *resolved_path.parents):
        raise ValueError(
            f"V15.2 XML output must stay under {resolved_model_dir}: {resolved_path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml_v152(p), encoding="utf-8")


def initialize_v152(model, data, p: PassiveArmsParams) -> None:
    """V14 initialize 的 nq=12 fork：motor 端初始与 link 端同角（弹簧零形变）。"""
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
    # nq=12 顺序：[hip_x, hip_z,
    #             l_motor=l_hip, l_link=0, l_knee, l_ankle,
    #             r_motor=r_hip, r_link=0, r_knee, r_ankle,
    #             l_arm, r_arm]
    # 弹簧零形变 => motor 与 link 角和 = 期望 hip 角，初始把全角加在 motor 端，link 端置 0
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
    """给 control_v136 看的 nq=10 view：把 V15.2 link/knee 角度填到 FSM 期望槽位。

    FSM 在 simulate_v13_6.py:197-241 按 qpos 索引硬编码读 [0,1,2,3,5,6]。
    V15.2 真实 nq=12，索引语义错位，本类做读视图（不写）。
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
        self._q_l_link = jq("left_hip_link")
        self._q_l_knee = jq("left_knee")
        self._q_r_link = jq("right_hip_link")
        self._q_r_knee = jq("right_knee")
        self._d_l_link = jd("left_hip_link")
        self._d_l_knee = jd("left_knee")
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
        self._qpos_buf[2] = rq[self._q_l_link]
        self._qpos_buf[3] = rq[self._q_l_knee]
        self._qpos_buf[4] = 0.0
        self._qpos_buf[5] = rq[self._q_r_link]
        self._qpos_buf[6] = rq[self._q_r_knee]
        self._qvel_buf[0] = rv[0]
        self._qvel_buf[1] = rv[1]
        self._qvel_buf[2] = rv[self._d_l_link]
        self._qvel_buf[3] = rv[self._d_l_knee]
        self._qvel_buf[4] = 0.0
        self._qvel_buf[5] = rv[self._d_r_link]
        self._qvel_buf[6] = rv[self._d_r_knee]

    @property
    def qpos(self):
        return self._qpos_buf

    @property
    def qvel(self):
        return self._qvel_buf


def make_row_v152(
    model, data, p: PassiveArmsParams, t, lc, rc, support, mode, tau, in_p, in_e
):
    """V14 make_row 的 nq=12 fork：QPOS_KEYS_V152 取代 QPOS_KEYS。"""
    out: dict = {"time": t}
    for k, v in zip(QPOS_KEYS_V152, data.qpos):
        out[k] = float(v)
    for k, v in zip(QVEL_KEYS_V152, data.qvel):
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


def run_simulation_v152(
    params: V152Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
    debug_print_jntmap: bool = False,
):
    """V15.2 strict SEA 主仿真循环 + 能量审计。"""
    p = params.base
    write_model_v152(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize_v152(model, data, p)
    fsm_view = _FsmDataView(model, data)

    if debug_print_jntmap:
        print("[v152.jntmap] nq=", model.nq, "nv=", model.nv, "nu=", model.nu)
        for i in range(model.njnt):
            n = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
            print(
                f"  joint[{i}] {n}: qposadr={model.jnt_qposadr[i]}, dofadr={model.jnt_dofadr[i]}"
            )
        for i in range(model.nu):
            n = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            print(f"  actuator[{i}] {n}")

    timestep = float(params.timestep_resolved)
    k_sea = float(params.k_sea)
    c_sea = float(params.damping_resolved)
    d_l_link = fsm_view._d_l_link
    d_l_motor = int(
        model.jnt_dofadr[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "left_hip_motor")
        ]
    )
    d_r_link = fsm_view._d_r_link
    d_r_motor = int(
        model.jnt_dofadr[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "right_hip_motor")
        ]
    )
    q_l_link = fsm_view._q_l_link
    q_r_link = fsm_view._q_r_link
    d_l_knee = fsm_view._d_l_knee
    d_r_knee = fsm_view._d_r_knee

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

    # 能量审计累计
    W_motor_input = 0.0
    W_link_useful = 0.0
    W_damper_loss = 0.0
    spring_pe_max = 0.0
    spring_pe_sum = 0.0
    q_link_max_left = 0.0
    q_link_max_right = 0.0
    q_motor_link_sq_sum = 0.0
    audit_samples = 0
    pe_spring_initial = (
        0.5
        * k_sea
        * (float(data.qpos[q_l_link]) ** 2 + float(data.qpos[q_r_link]) ** 2)
    )
    # SEA inner loop 跟踪误差累计
    tau_desired_abs_sum = 0.0
    tau_track_err_abs_sum = 0.0

    motor_lim = float(params.motor_ctrl_limit)
    inner_kp = float(params.inner_kp_pos)
    inner_kd = float(params.inner_kd_resolved)
    k_sea_safe = max(k_sea, 1e-9)

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

        # 读 motor / link / knee dof 速度（inner loop 与 audit 都用）
        qd_motor_l = float(data.qvel[d_l_motor])
        qd_motor_r = float(data.qvel[d_r_motor])
        qd_link_l = float(data.qvel[d_l_link])
        qd_link_r = float(data.qvel[d_r_link])
        qd_knee_l = float(data.qvel[d_l_knee])
        qd_knee_r = float(data.qvel[d_r_knee])
        ql_link = float(data.qpos[q_l_link])
        qr_link = float(data.qpos[q_r_link])

        # 弹簧实际扭矩（作用在 link 上）
        tau_spring_l = -k_sea * ql_link - c_sea * qd_link_l
        tau_spring_r = -k_sea * qr_link - c_sea * qd_link_r

        # SEA inner loop (motor position PD + feedforward)
        # 控制律：u = τ_des + Kp_pos*(q_link + τ_des/k_sea) - Kd*qd_motor
        # 稳态：spring 输出 -k*q_link = τ_des  ⇒  q_link = -τ_des/k_sea
        # feedforward τ_des 抵消 spring 反作用让稳态精确；Kp_pos 处理 link 端摆动跟踪
        motor_force_l = (
            l_hip_des
            + inner_kp * (ql_link + l_hip_des / k_sea_safe)
            - inner_kd * qd_motor_l
        )
        motor_force_r = (
            r_hip_des
            + inner_kp * (qr_link + r_hip_des / k_sea_safe)
            - inner_kd * qd_motor_r
        )
        motor_force_l = float(np.clip(motor_force_l, -motor_lim, motor_lim))
        motor_force_r = float(np.clip(motor_force_r, -motor_lim, motor_lim))
        data.ctrl[:] = (motor_force_l, l_knee, motor_force_r, r_knee)

        # input_power 用真实电机力（已经是内环输出）* motor 角速度；knee 直接 PD
        input_power = (
            motor_force_l * qd_motor_l
            + l_knee * qd_knee_l
            + motor_force_r * qd_motor_r
            + r_knee * qd_knee_r
        )
        positive_input_energy += max(0.0, input_power) * timestep
        net_work += input_power * timestep

        # 能量审计 + SEA 跟踪误差
        W_motor_input += (
            motor_force_l * qd_motor_l + motor_force_r * qd_motor_r
        ) * timestep
        W_link_useful += (
            tau_spring_l * qd_link_l + tau_spring_r * qd_link_r
        ) * timestep
        W_damper_loss += (
            c_sea * (qd_link_l * qd_link_l + qd_link_r * qd_link_r) * timestep
        )
        tau_desired_abs_sum += abs(l_hip_des) + abs(r_hip_des)
        tau_track_err_abs_sum += abs(l_hip_des - tau_spring_l) + abs(
            r_hip_des - tau_spring_r
        )
        spring_pe = 0.5 * k_sea * (ql_link * ql_link + qr_link * qr_link)
        spring_pe_max = max(spring_pe_max, spring_pe)
        spring_pe_sum += spring_pe
        audit_samples += 1
        q_link_max_left = max(q_link_max_left, abs(ql_link))
        q_link_max_right = max(q_link_max_right, abs(qr_link))
        diff_l = float(data.qpos[QPOS_L_MOTOR]) - ql_link
        diff_r = float(data.qpos[QPOS_R_MOTOR]) - qr_link
        q_motor_link_sq_sum += diff_l * diff_l + diff_r * diff_r

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
            row = make_row_v152(
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
            row["left_hip_tau_desired"] = float(l_hip_des)
            row["right_hip_tau_desired"] = float(r_hip_des)
            row["left_motor_force"] = float(motor_force_l)
            row["right_motor_force"] = float(motor_force_r)
            rows.append(row)

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        fallback = make_row_v152(
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
    inner_track_err_pct = 100.0 * tau_track_err_abs_sum / max(tau_desired_abs_sum, 1e-9)

    energy_audit = {
        "W_motor_input_J": W_motor_input,
        "W_link_useful_J": W_link_useful,
        "W_damper_loss_J": W_damper_loss,
        "dPE_spring_J": dPE_spring,
        "PE_spring_initial_J": pe_spring_initial,
        "PE_spring_final_J": pe_spring_final,
        "inner_loop_track_err_pct": inner_track_err_pct,
        "track_err_note": "mean(|tau_desired - tau_spring|) / mean(|tau_desired|), "
        "<5% => SEA 内环正确跟踪 FSM 期望力矩",
    }

    q_motor_link_rms = math.sqrt(q_motor_link_sq_sum / max(1, audit_samples) / 2.0)
    summary = {
        "params": asdict(p),
        "v152_extra": {
            "k_sea": k_sea,
            "c_sea": c_sea,
            "motor_rotor_mass": float(params.motor_rotor_mass),
            "motor_rotor_iyy": float(params.motor_rotor_iyy),
            "motor_bearing_damping": float(params.motor_bearing_damping),
            "inner_kp_pos": float(params.inner_kp_pos),
            "inner_kd_motor": float(params.inner_kd_resolved),
            "motor_ctrl_limit": float(params.motor_ctrl_limit),
            "timestep_used": timestep,
            "spring_pe_max_J": spring_pe_max,
            "spring_pe_mean_J": spring_pe_sum / max(1, audit_samples),
            "q_link_max_left_deg": math.degrees(q_link_max_left),
            "q_link_max_right_deg": math.degrees(q_link_max_right),
            "q_motor_link_rms_deg": math.degrees(q_motor_link_rms),
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
        "controller": "v13_6_1_best_fsm_via_FsmDataView_on_strict_sea",
        "topology": "strict_sea_motor_rotor_with_hinge_spring",
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
    parser = argparse.ArgumentParser(
        description="V15.2 strict SEA single-shot simulate"
    )
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--slope", type=float, default=0.0)
    parser.add_argument("--arm-mass", type=float, default=0.01)
    parser.add_argument("--arm-length", type=float, default=0.40)
    parser.add_argument("--arm-damping", type=float, default=0.02)
    parser.add_argument("--arm-stiffness", type=float, default=0.0)
    parser.add_argument("--foot-radius", type=float, default=None)
    parser.add_argument("--leg-scale", type=float, default=1.0)
    parser.add_argument("--k-sea", type=float, default=1000.0)
    parser.add_argument(
        "--c-sea", type=float, default=-1.0, help="<0 => 自动取临界阻尼 0.6 倍"
    )
    parser.add_argument("--rotor-mass", type=float, default=0.05)
    parser.add_argument("--rotor-iyy", type=float, default=0.004)
    parser.add_argument(
        "--rotor-iiyt",
        type=float,
        default=0.0021,
        help="rotor 绕非轴方向 inertia (Ixx=Izz)，需满足 2*Iiyt >= Iyy",
    )
    parser.add_argument("--motor-damp", type=float, default=0.02)
    parser.add_argument("--motor-ctrl-limit", type=float, default=30.0)
    parser.add_argument(
        "--inner-kp",
        type=float,
        default=1000.0,
        help="motor 位置 P 增益 (N·m/rad)；标准 SEA Pratt control",
    )
    parser.add_argument(
        "--inner-kd", type=float, default=-1.0, help="<0 自动取 ζ=0.7 临界阻尼"
    )
    parser.add_argument(
        "--timestep",
        type=float,
        default=-1.0,
        help="<0 => k_sea>=5e3 自动 0.5ms 否则沿用 base 1ms",
    )
    parser.add_argument(
        "--debug-jntmap",
        action="store_true",
        help="打印 mj_name2id 索引表用于核对 qpos 布局",
    )
    parser.add_argument(
        "--save-prefix", "--prefix", dest="save_prefix", default="v152_smoke"
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
    params = V152Params(
        base=base,
        fsm=make_v152_fsm(base),
        k_sea=float(args.k_sea),
        c_sea=float(args.c_sea),
        motor_rotor_mass=float(args.rotor_mass),
        motor_rotor_iyy=float(args.rotor_iyy),
        motor_rotor_iiyt=float(args.rotor_iiyt),
        motor_bearing_damping=float(args.motor_damp),
        motor_ctrl_limit=float(args.motor_ctrl_limit),
        inner_kp_pos=float(args.inner_kp),
        inner_kd_motor=float(args.inner_kd),
        timestep_override=float(args.timestep),
    )
    _, summary = run_simulation_v152(
        params,
        save_prefix=args.save_prefix,
        sample_hz=160.0,
        debug_print_jntmap=args.debug_jntmap,
    )
    show = {k: v for k, v in summary.items() if k != "params"}
    print(json.dumps(show, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""详细对比V2和Identity Test的执行差异。"""

import sys
from pathlib import Path
import numpy as np
import mujoco

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))
sys.path.insert(0, str(HW1_ROOT / "v13_7_friction_compensation"))
sys.path.insert(0, str(HW1_ROOT / "v13_6_event_driven_fsm"))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from train_residual_rl_v2 import ResidualRLEnvV2
from simulate_v13_7 import (
    V137Params,
    make_v137_fsm,
    write_model_v137,
    MODEL_PATH,
    _compensate,
    _mechanical_energy,
)
from simulate_v13_6 import control_v136
from simulate_passive_arms_v14 import PassiveArmsParams, initialize, contact_flags
from common.motor_dynamics import L1MotorActuator, PRESETS as MOTOR_PRESETS
from dataclasses import replace

print("=" * 80)
print("Side-by-Side Comparison: V2 vs Identity Test")
print("=" * 80)

# 构建相同参数
base0 = PassiveArmsParams()
overrides = dict(
    duration=12.0,
    slope_deg=0.0,
    arm_mass=0.01,
    arm_length=0.40,
    arm_damping=0.02,
    arm_stiffness=0.0,
    thigh_length=float(base0.thigh_length * 1.02),
    shank_length=float(base0.shank_length * 1.02),
    step_length=float(base0.step_length * 1.02),
    foot_radius=0.042,
)
base = replace(base0, **overrides)
fsm = make_v137_fsm(base)
motor = MOTOR_PRESETS["mx64ar"]
params = V137Params(
    base=base, fsm=fsm, hip_motor=motor, knee_motor=motor, compensate_friction=True
)

# 写模型
write_model_v137(params)
model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
data = mujoco.MjData(model)

# Identity Test方式初始化
initialize(model, data, base)

# 创建电机
actuators = {
    "left_hip": L1MotorActuator(motor),
    "left_knee": L1MotorActuator(motor),
    "right_hip": L1MotorActuator(motor),
    "right_knee": L1MotorActuator(motor),
}
qvel_addr = {"left_hip": 2, "left_knee": 3, "right_hip": 5, "right_knee": 6}

# FSM状态
support_foot = "left"
burst_start_t = -base.gait_period
accepted_contact = ""
candidate_start_t = {"left": None, "right": None}
contact_reported = {"left": False, "right": False}
last_event_t = -1.0

print("\nRunning Identity Test method for 12 seconds...")
print(f"{'Step':<6} {'Time':<8} {'hip_x':<10} {'Support':<8} {'E_curr':<10}")
print("-" * 60)

fsm_events_identity = []

for step in range(12000):  # 12秒
    t = step * 0.001

    # 计算能量
    E_current = _mechanical_energy(base, data)

    # control_v136
    tau = control_v136(fsm, data, t, support_foot, burst_start_t, E_current)
    l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

    # 摩擦补偿
    l_hip_des = _compensate(l_hip_des, float(data.qvel[qvel_addr["left_hip"]]), motor)
    l_knee_des = _compensate(
        l_knee_des, float(data.qvel[qvel_addr["left_knee"]]), motor
    )
    r_hip_des = _compensate(r_hip_des, float(data.qvel[qvel_addr["right_hip"]]), motor)
    r_knee_des = _compensate(
        r_knee_des, float(data.qvel[qvel_addr["right_knee"]]), motor
    )

    # L1电机
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

    # Step
    mujoco.mj_step(model, data)

    # FSM更新
    left_c, right_c = contact_flags(model, data)
    contacts = {"left": left_c, "right": right_c}
    stable_feet = []

    for foot, has_contact in contacts.items():
        if has_contact:
            if candidate_start_t[foot] is None:
                candidate_start_t[foot] = t
                contact_reported[foot] = False
            if t - float(candidate_start_t[foot]) >= base.stable_contact_time:
                stable_feet.append(foot)
        else:
            candidate_start_t[foot] = None
            contact_reported[foot] = False

    for foot in stable_feet:
        if (
            not contact_reported[foot]
            and foot != accepted_contact
            and t - last_event_t > base.min_event_interval
        ):
            accepted_contact = foot
            support_foot = foot
            burst_start_t = t
            last_event_t = t
            contact_reported[foot] = True
            fsm_events_identity.append({"time": t, "foot": foot})
            break

    if step % 500 == 0:
        print(
            f"{step:<6} {t:<8.3f} {data.qpos[0]:<10.6f} {support_foot:<8} {E_current:<10.3f}"
        )

print(f"\nIdentity Test FSM events: {len(fsm_events_identity)}")
for i, e in enumerate(fsm_events_identity[:10]):
    print(f"  Event {i+1}: t={e['time']:.3f}s, foot={e['foot']}")

print("\n" + "=" * 80)
print("Now testing V2 Environment...")
print("=" * 80)

env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

fsm_events_v2 = []
last_support_v2 = env.support_foot
last_burst_v2 = env.burst_start_t

for step in range(2400):  # 12秒
    obs, reward, terminated, truncated, info = env.step(action)

    if env.support_foot != last_support_v2 or env.burst_start_t != last_burst_v2:
        fsm_events_v2.append({"time": env.sim_time, "foot": env.support_foot})
        last_support_v2 = env.support_foot
        last_burst_v2 = env.burst_start_t

    if terminated or truncated:
        break

print(f"\nV2 Environment FSM events: {len(fsm_events_v2)}")
for i, e in enumerate(fsm_events_v2[:10]):
    print(f"  Event {i+1}: t={e['time']:.3f}s, foot={e['foot']}")

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
print(f"Identity Test events: {len(fsm_events_identity)}")
print(f"V2 Environment events: {len(fsm_events_v2)}")

if len(fsm_events_v2) < len(fsm_events_identity) - 2:
    print("\n[PROBLEM] V2 has significantly fewer FSM events!")
    print("This explains why the robot stops switching support and falls.")
else:
    print("\n[OK] FSM event counts are similar.")

env.close()

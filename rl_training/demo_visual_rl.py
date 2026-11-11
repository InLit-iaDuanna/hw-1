"""可视化演示：100k RL 策略行走

展示机器人使用深度强化学习策略的实际行走效果
"""

import sys
from pathlib import Path
import numpy as np
from stable_baselines3 import PPO
import mujoco
import mujoco.viewer
import time

HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14_DIR = HW1_ROOT / "v14_passive_arms"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from simulate_v13_7 import (
    V137Params,
    MODEL_PATH,
    _compensate,
    _mechanical_energy,
    write_model_v137,
    make_v137_fsm,
)
from simulate_v13_6 import control_v136
from simulate_passive_arms_v14 import (
    contact_flags,
    PassiveArmsParams,
)
from simulate_v14c import make_v14c_params
from common.motor_dynamics import L1MotorActuator, PRESETS as MOTOR_PRESETS
from dataclasses import replace


def setup_v137_model():
    """创建 V13.7 模型"""
    base_params = PassiveArmsParams()
    base_params = replace(
        base_params,
        duration=12.0,
        slope_deg=0.0,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        thigh_length=float(base_params.thigh_length * 1.02),
        shank_length=float(base_params.shank_length * 1.02),
        step_length=float(base_params.step_length * 1.02),
        foot_radius=0.042,
    )

    fsm_params = make_v14c_params(base_params)
    v137_params = V137Params(
        base=base_params,
        fsm=fsm_params,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
        compensate_friction=True,
    )

    # Write model
    write_model_v137(v137_params)
    return v137_params


def run_rl_walker_visual():
    """可视化运行 100k RL 策略"""
    print("=" * 80)
    print("100k PPO 深度强化学习行走演示")
    print("=" * 80)
    print()

    # 加载 PPO 模型
    model_path = (
        HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"
    )

    if not model_path.exists():
        print(f"错误：模型文件不存在")
        print(f"路径：{model_path}")
        return

    print("正在加载 PPO 模型...")
    model = PPO.load(str(model_path))
    print("模型加载成功！")
    print()

    # 创建环境
    print("正在创建仿真环境...")
    v137_params = setup_v137_model()
    mj_model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    mj_data = mujoco.MjData(mj_model)

    # 配置参数
    residual_scale = 0.2
    prior_action = np.array([0.5, 1.0])
    delta_scale = 0.3

    # 初始化
    from simulate_passive_arms_v14 import initialize

    initialize(mj_model, mj_data, v137_params.base)

    # FSM 状态
    support_foot = "left"
    burst_start_t = 0.0
    last_contact_t = -1.0
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}

    # 电机模型
    actuators = {
        "left_hip": L1MotorActuator(v137_params.hip_motor),
        "left_knee": L1MotorActuator(v137_params.knee_motor),
        "right_hip": L1MotorActuator(v137_params.hip_motor),
        "right_knee": L1MotorActuator(v137_params.knee_motor),
    }

    qvel_addr = {
        "left_hip": mujoco.mj_name2id(
            mj_model, mujoco.mjtObj.mjOBJ_JOINT, "left_hip_joint"
        ),
        "left_knee": mujoco.mj_name2id(
            mj_model, mujoco.mjtObj.mjOBJ_JOINT, "left_knee_joint"
        ),
        "right_hip": mujoco.mj_name2id(
            mj_model, mujoco.mjtObj.mjOBJ_JOINT, "right_hip_joint"
        ),
        "right_knee": mujoco.mj_name2id(
            mj_model, mujoco.mjtObj.mjOBJ_JOINT, "right_knee_joint"
        ),
    }

    print("正在启动可视化窗口...")
    print()
    print("=" * 80)
    print("演示说明：")
    print("  - 机器人使用 PPO 策略进行行走")
    print("  - 左下角显示实时距离和相位信息")
    print("  - 按 ESC 或关闭窗口退出")
    print("  - 行走时长：12 秒")
    print("=" * 80)
    print()

    # 创建 observation（42维）
    def get_observation():
        # 前 20 维（原始观测）
        joint_angles = mj_data.qpos[2:8].copy()  # 6个关节角度
        joint_velocities = mj_data.qvel[2:8].copy()  # 6个关节角速度
        hip_pos = mj_data.qpos[[0, 1]].copy()  # hip x, z
        hip_vel = mj_data.qvel[[0, 1]].copy()  # hip vx, vz

        left_c, right_c = contact_flags(mj_model, mj_data)
        contact_states = np.array(
            [float(left_c), float(not left_c), float(right_c), float(not right_c)],
            dtype=np.float32,
        )

        # 后 22 维（扩展观测）- 简化版
        left_phase_onehot = np.array([1, 0, 0, 0], dtype=np.float32)  # stance_early
        right_phase_onehot = np.array([0, 0, 1, 0], dtype=np.float32)  # swing_thrust
        support_onehot = (
            np.array([1, 0], dtype=np.float32)
            if support_foot == "left"
            else np.array([0, 1], dtype=np.float32)
        )
        t_since_contact_norm = 0.5
        t_since_burst_norm = 0.5
        E_current_norm = 1.0
        E_diff_norm = 0.0
        base_torques_norm = np.zeros(4, dtype=np.float32)
        last_residuals_norm = np.zeros(4, dtype=np.float32)

        obs = np.concatenate(
            [
                joint_angles,
                joint_velocities,
                hip_pos,
                hip_vel,
                contact_states,
                left_phase_onehot,
                right_phase_onehot,
                support_onehot,
                [t_since_contact_norm],
                [t_since_burst_norm],
                [E_current_norm],
                [E_diff_norm],
                base_torques_norm,
                last_residuals_norm,
            ]
        ).astype(np.float32)

        return obs

    # 使用 passive viewer
    with mujoco.viewer.launch_passive(mj_model, mj_data) as viewer:
        viewer.cam.distance = 3.5
        viewer.cam.elevation = -15
        viewer.cam.azimuth = 90
        viewer.cam.lookat[:] = [0, 0, 0.5]

        start_time = time.time()
        dt = 0.001
        max_steps = 12000
        step = 0

        while viewer.is_running() and step < max_steps:
            step_start = time.time()
            t = step * dt

            # FSM 状态更新
            left_c, right_c = contact_flags(mj_model, mj_data)
            contacts = {"left": left_c, "right": right_c}

            for foot, has_contact in contacts.items():
                if has_contact:
                    if candidate_start_t[foot] is None:
                        candidate_start_t[foot] = t
                        contact_reported[foot] = False
                    elif t - candidate_start_t[foot] >= 0.015:  # 15ms latch duration
                        if not contact_reported[foot]:
                            support_foot = foot
                            burst_start_t = t
                            last_contact_t = t
                            contact_reported[foot] = True
                else:
                    candidate_start_t[foot] = None
                    contact_reported[foot] = False

            # V13.6 FSM 控制
            E_current = _mechanical_energy(v137_params.base, mj_data)
            tau = control_v136(
                v137_params.fsm, mj_data, t, support_foot, burst_start_t, E_current
            )

            l_hip_des, l_knee_des = tau[0], tau[1]
            r_hip_des, r_knee_des = tau[2], tau[3]
            left_phase, right_phase = str(tau[5]), str(tau[6])

            # 摩擦补偿
            l_hip_des = _compensate(
                l_hip_des,
                float(mj_data.qvel[qvel_addr["left_hip"]]),
                v137_params.hip_motor,
            )
            l_knee_des = _compensate(
                l_knee_des,
                float(mj_data.qvel[qvel_addr["left_knee"]]),
                v137_params.knee_motor,
            )
            r_hip_des = _compensate(
                r_hip_des,
                float(mj_data.qvel[qvel_addr["right_hip"]]),
                v137_params.hip_motor,
            )
            r_knee_des = _compensate(
                r_knee_des,
                float(mj_data.qvel[qvel_addr["right_knee"]]),
                v137_params.knee_motor,
            )

            # 每 5 步运行一次 PPO（200Hz）
            if step % 5 == 0:
                obs = get_observation()
                ppo_action, _ = model.predict(obs, deterministic=True)
                # 转换 action: delta -> actual
                actual_action = np.clip(
                    prior_action + delta_scale * ppo_action, -1.0, 1.0
                )
                residual = actual_action * residual_scale

            # 添加 residual
            l_hip_des += residual[0]
            r_hip_des += residual[1]

            # L1 电机模型
            l_hip_out, _ = actuators["left_hip"].compute_actual_torque(
                l_hip_des, float(mj_data.qvel[qvel_addr["left_hip"]])
            )
            l_knee_out, _ = actuators["left_knee"].compute_actual_torque(
                l_knee_des, float(mj_data.qvel[qvel_addr["left_knee"]])
            )
            r_hip_out, _ = actuators["right_hip"].compute_actual_torque(
                r_hip_des, float(mj_data.qvel[qvel_addr["right_hip"]])
            )
            r_knee_out, _ = actuators["right_knee"].compute_actual_torque(
                r_knee_des, float(mj_data.qvel[qvel_addr["right_knee"]])
            )

            # 应用控制
            mj_data.ctrl[0] = l_hip_out
            mj_data.ctrl[1] = l_knee_out
            mj_data.ctrl[2] = r_hip_out
            mj_data.ctrl[3] = r_knee_out

            # 仿真步进
            mujoco.mj_step(mj_model, mj_data)

            # 更新显示
            viewer.sync()

            # 显示信息
            distance = mj_data.qpos[0]
            hip_height = mj_data.qpos[2]

            if step % 100 == 0:  # 每 100ms 打印一次
                print(
                    f"\r时间: {t:.2f}s | 距离: {distance:.3f}m | 支撑脚: {support_foot} | 左相位: {left_phase} | 右相位: {right_phase}",
                    end="",
                )

            # 控制帧率
            time_until_next_step = dt - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

            step += 1

        elapsed = time.time() - start_time
        final_distance = mj_data.qpos[0]

        print()
        print()
        print("=" * 80)
        print("演示完成！")
        print("=" * 80)
        print(f"最终距离: {final_distance:.3f}m")
        print(f"行走时长: {elapsed:.2f}s")
        print(f"平均速度: {final_distance/12:.3f} m/s")
        print("=" * 80)


if __name__ == "__main__":
    try:
        run_rl_walker_visual()
    except KeyboardInterrupt:
        print("\n\n用户中断演示")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback

        traceback.print_exc()

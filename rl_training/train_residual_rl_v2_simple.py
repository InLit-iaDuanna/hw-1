"""简化版ResidualRLEnvV2 - 直接基于test_v137_identity的成功代码。

策略：
1. 先确保zero residual能达到4.63m（完全复现Identity Test）
2. 再逐步添加42维observation和hip-only action
3. 避免引入任何可能破坏V13.7控制器的修改
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np
from dataclasses import replace

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "v13_7_friction_compensation"))
sys.path.insert(0, str(HW1_ROOT / "v13_6_event_driven_fsm"))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from simulate_v13_7 import (
    V137Params,
    make_v137_fsm,
    write_model_v137,
    MODEL_PATH,
    _compensate,
    _mechanical_energy,
)
from simulate_v13_6 import control_v136
from simulate_passive_arms_v14 import (
    PassiveArmsParams,
    initialize,
    contact_flags,
    classify_failure,
)
from common.motor_dynamics import L1MotorActuator, PRESETS as MOTOR_PRESETS


class ResidualRLEnvV2Simple(gym.Env):
    """简化版V2环境 - 直接复现test_v137_identity的控制循环。"""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(
        self,
        params: Optional[V137Params] = None,
        residual_scale: float = 0.05,
        max_steps: int = 12000,  # 12秒 * 1000Hz = 12000步
        render_mode: Optional[str] = None,
    ):
        super().__init__()

        # 构建V13.7参数（与test_v137_identity完全一致）
        if params is None:
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
                base=base,
                fsm=fsm,
                hip_motor=motor,
                knee_motor=motor,
                compensate_friction=True,
            )

        self.params = params
        self.residual_scale = residual_scale
        self.max_steps = max_steps
        self.render_mode = render_mode
        self.dt = 0.001  # 1kHz

        # 写模型
        write_model_v137(params)
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
        self.data = mujoco.MjData(self.model)

        # 电机模型
        self.actuators = {
            "left_hip": L1MotorActuator(params.hip_motor),
            "left_knee": L1MotorActuator(params.knee_motor),
            "right_hip": L1MotorActuator(params.hip_motor),
            "right_knee": L1MotorActuator(params.knee_motor),
        }
        self.qvel_addr = {
            "left_hip": 2,
            "left_knee": 3,
            "right_hip": 5,
            "right_knee": 6,
        }

        # Gym spaces
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(2,), dtype=np.float32  # hip-only
        )
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(42,), dtype=np.float32
        )

        # 状态变量（会在reset中初始化）
        self.steps = 0
        self.start_x = 0.0
        self.support_foot = "left"
        self.accepted_contact = ""
        self.candidate_start_t: Dict[str, Optional[float]] = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}
        self.last_event_t = -1.0
        self.burst_start_t = 0.0

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        super().reset(seed=seed)

        p = self.params.base

        # 使用V13.7的initialize()函数
        initialize(self.model, self.data, p)

        # 重置电机
        for act in self.actuators.values():
            act.saturation_count = 0

        # FSM状态初始化（与test_v137_identity完全一致）
        self.steps = 0
        self.start_x = float(self.data.qpos[0])
        self.support_foot = "left"
        self.accepted_contact = ""
        self.candidate_start_t = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}
        self.last_event_t = -1.0
        self.burst_start_t = -p.gait_period  # 关键：初始化为负值

        observation = self._get_obs()
        info = {"hip_x": self.start_x}

        return observation, info

    def step(self, action: np.ndarray):
        """执行1ms步骤（完全复现test_v137_identity的控制循环）。"""

        p = self.params.base
        fsm = self.params.fsm
        t = self.steps * self.dt

        # 计算能量
        E_current = _mechanical_energy(p, self.data)

        # V13.6 FSM控制律（与Identity Test完全一致）
        tau = control_v136(fsm, self.data, t, self.support_foot, self.burst_start_t, E_current)
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        # V13.7摩擦补偿
        if self.params.compensate_friction:
            l_hip_des = _compensate(l_hip_des, float(self.data.qvel[self.qvel_addr["left_hip"]]), self.params.hip_motor)
            l_knee_des = _compensate(l_knee_des, float(self.data.qvel[self.qvel_addr["left_knee"]]), self.params.knee_motor)
            r_hip_des = _compensate(r_hip_des, float(self.data.qvel[self.qvel_addr["right_hip"]]), self.params.hip_motor)
            r_knee_des = _compensate(r_knee_des, float(self.data.qvel[self.qvel_addr["right_knee"]]), self.params.knee_motor)

        # L1电机模型
        l_hip_out, _ = self.actuators["left_hip"].compute_actual_torque(l_hip_des, float(self.data.qvel[self.qvel_addr["left_hip"]]))
        l_knee_out, _ = self.actuators["left_knee"].compute_actual_torque(l_knee_des, float(self.data.qvel[self.qvel_addr["left_knee"]]))
        r_hip_out, _ = self.actuators["right_hip"].compute_actual_torque(r_hip_des, float(self.data.qvel[self.qvel_addr["right_hip"]]))
        r_knee_out, _ = self.actuators["right_knee"].compute_actual_torque(r_knee_des, float(self.data.qvel[self.qvel_addr["right_knee"]]))

        # TODO: 添加residual（当前是zero residual）
        self.data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

        # MuJoCo step
        mujoco.mj_step(self.model, self.data)

        # FSM状态更新（与Identity Test完全一致）
        left_c, right_c = contact_flags(self.model, self.data)
        contacts = {"left": left_c, "right": right_c}
        stable_feet = []

        for foot, has_contact in contacts.items():
            if has_contact:
                if self.candidate_start_t[foot] is None:
                    self.candidate_start_t[foot] = t
                    self.contact_reported[foot] = False
                if t - float(self.candidate_start_t[foot]) >= p.stable_contact_time:
                    stable_feet.append(foot)
            else:
                self.candidate_start_t[foot] = None
                self.contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not self.contact_reported[foot]
                and foot != self.accepted_contact
                and t - self.last_event_t > p.min_event_interval
            ):
                self.accepted_contact = foot
                self.support_foot = foot
                self.burst_start_t = t
                self.last_event_t = t
                self.contact_reported[foot] = True
                break

        # 步数+1
        self.steps += 1

        # 终止条件
        failure = classify_failure(self.model, self.data, p, self.start_x, t)
        terminated = bool(failure)
        truncated = self.steps >= self.max_steps

        # 计算距离
        current_x = float(self.data.qpos[0])
        distance = current_x - self.start_x

        # 简单reward
        reward = 0.0

        # Observation
        observation = self._get_obs()

        # Info
        hip_body_id = self.model.body("hip").id
        info = {
            "hip_x": self.data.xpos[hip_body_id][0],
            "hip_height": self.data.xpos[hip_body_id][2],
            "episode_distance": distance,
            "sim_time": t,
        }

        return observation, reward, terminated, truncated, info

    def _get_obs(self) -> np.ndarray:
        """构建42维observation（暂时返回零向量）。"""
        return np.zeros(42, dtype=np.float32)

    def close(self):
        pass


# 测试代码
if __name__ == "__main__":
    print("Testing ResidualRLEnvV2Simple...")
    env = ResidualRLEnvV2Simple(residual_scale=0.05, max_steps=12000)
    obs, info = env.reset()
    action = np.array([0.0, 0.0], dtype=np.float32)

    for step in range(12000):
        obs, reward, terminated, truncated, info = env.step(action)

        if step % 1000 == 0:
            print(f"Step {step}, t={info['sim_time']:.3f}s, distance={info['episode_distance']:.3f}m")

        if terminated:
            print(f"\n[TERMINATED] at t={info['sim_time']:.3f}s, distance={info['episode_distance']:.3f}m")
            break

        if truncated:
            print(f"\n[COMPLETED] t={info['sim_time']:.3f}s, distance={info['episode_distance']:.3f}m")
            break

    env.close()
    print("\nExpected: 4.630m in 12.00s")

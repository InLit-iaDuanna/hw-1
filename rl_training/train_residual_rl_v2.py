"""Residual RL V2: Hip-only residual with extended observations.

核心改进：
1. Action维度从4降至2（仅控制hip joint）
2. Observation增加至42维（20原始 + 22新增）
3. Baseline-relative reward（与V13.7基线对比）
4. 新增FSM phase信息、时间编码、能量反馈

新增观测（22维）：
- left_phase one-hot (4维)
- right_phase one-hot (4维)
- support_foot one-hot (2维)
- time_since_last_contact (1维)
- time_since_burst_start (1维)
- E_current, E_current-E_ref (2维)
- V13.7 base torques (4维)
- last residuals (4维)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json

import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_v13_7 import (
    MODEL_PATH,
    V137Params,
    _compensate,
    _mechanical_energy,
    write_model_v137,
    make_v137_fsm,
)
from simulate_v13_6 import control_v136
from simulate_passive_arms_v14 import contact_flags, initialize, classify_failure
from simulate_v14c import make_v14c_params
from common.motor_dynamics import L1MotorActuator, PRESETS as MOTOR_PRESETS


class ResidualRLEnvV2(gym.Env):
    """Residual RL V2: Hip-only control with extended observations."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(
        self,
        params: Optional[V137Params] = None,
        residual_scale: float = 0.05,
        inner_steps: int = 5,
        max_steps: int = 500,
        render_mode: Optional[str] = None,
    ):
        """初始化ResidualRLEnvV2环境。

        Args:
            params: V13.7参数
            residual_scale: residual缩放系数（初始值0.05）
            inner_steps: 每个PPO step内部运行多少个1ms step（5=200Hz PPO）
            max_steps: 最大episode步数（500步=2.5秒）
            render_mode: 渲染模式
        """
        super().__init__()

        # 参数（与test_v137_identity.py一致）
        if params is None:
            from simulate_passive_arms_v14 import PassiveArmsParams
            from dataclasses import replace

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
        self.inner_steps = inner_steps
        self.max_steps = max_steps
        self.render_mode = render_mode
        self.dt = 0.001  # 1kHz

        # 计算episode实际时长
        self.episode_duration = max_steps * inner_steps * self.dt  # 秒

        # 加载模型
        write_model_v137(params)
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
        self.data = mujoco.MjData(self.model)

        # V13.7控制器组件
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

        # FSM隐状态（初始值将在reset()中正确设置）
        self.support_foot = "left"
        self.burst_start_t = -self.params.base.gait_period  # 与V13.7一致
        self.last_contact_t = 0.0
        self.accepted_contact = ""
        self.candidate_start_t = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}
        self.last_event_t = -1.0

        # 参考基线（从V13.7获取）
        self.E_ref_mean = 52.66  # 归一化用，使用swing_thrust.E_target
        # baseline_dx_per_step: V13.7在12s内走4.63m，在2.5s内应该走约0.965m
        # 每个PPO step (5ms): 0.965m / 500steps = 0.00193m/step
        self.baseline_dx_per_step = (
            4.63 / 12.0 * (self.inner_steps * self.dt)
        )  # 每PPO step的baseline距离

        # Action空间：仅2维 [left_hip, right_hip]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # Observation空间：42维
        obs_dim = 42
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # 状态跟踪
        self.steps = 0
        # 1 kHz control time is derived from this integer counter.  This keeps
        # the V13.6 FSM aligned with the validated identity-test loop.
        self.micro_steps = 0
        self.sim_time = 0.0
        self.last_control_t = 0.0
        self.start_x = 0.0
        self.max_x = 0.0
        self.last_hip_x = 0.0
        self.last_residuals = np.zeros(4, dtype=np.float32)
        self.last_base_torques = np.zeros(4, dtype=np.float32)
        self.last_mode_label = ""
        self.last_left_phase_label = ""
        self.last_right_phase_label = ""
        self.failure_reason = ""

        # 统计
        self.episode_distance = 0.0
        self.episode_work = 0.0

        # 渲染器
        self.renderer = None

    def _get_phase_labels(self, t: Optional[float] = None) -> tuple[str, str]:
        """Return the V13.7 controller phase labels for the current state."""
        if t is None:
            t = self.micro_steps * self.dt

        E_current = _mechanical_energy(self.params.base, self.data)
        tau = control_v136(
            self.params.fsm,
            self.data,
            t,
            self.support_foot,
            self.burst_start_t,
            E_current,
        )
        return str(tau[5]), str(tau[6])

    def _get_phase(self, foot: str) -> int:
        """Return the current V13.7 phase index for a foot."""
        left_phase, right_phase = self._get_phase_labels()
        phase_name = left_phase if foot == "left" else right_phase
        phase_to_idx = {
            "stance_early": 0,
            "stance_late": 1,
            "swing_thrust": 2,
            "swing_retract": 3,
        }
        return phase_to_idx[phase_name]

    def _compute_v137_base_control(self, t: float) -> np.ndarray:
        """计算V13.7基础控制力矩（完整版本，1kHz更新）。

        Returns:
            4维力矩数组 [left_hip, left_knee, right_hip, right_knee]
        """
        E_current = _mechanical_energy(self.params.base, self.data)

        # V13.6 FSM控制律
        tau = control_v136(
            self.params.fsm,
            self.data,
            t,
            self.support_foot,
            self.burst_start_t,
            E_current,
        )
        self.last_mode_label = str(tau[4])
        self.last_left_phase_label = str(tau[5])
        self.last_right_phase_label = str(tau[6])
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        # 前馈摩擦补偿
        if self.params.compensate_friction:
            l_hip_des = _compensate(
                l_hip_des,
                float(self.data.qvel[self.qvel_addr["left_hip"]]),
                self.params.hip_motor,
            )
            l_knee_des = _compensate(
                l_knee_des,
                float(self.data.qvel[self.qvel_addr["left_knee"]]),
                self.params.knee_motor,
            )
            r_hip_des = _compensate(
                r_hip_des,
                float(self.data.qvel[self.qvel_addr["right_hip"]]),
                self.params.hip_motor,
            )
            r_knee_des = _compensate(
                r_knee_des,
                float(self.data.qvel[self.qvel_addr["right_knee"]]),
                self.params.knee_motor,
            )

        # L1电机模型
        l_hip_out, _ = self.actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(self.data.qvel[self.qvel_addr["left_hip"]])
        )
        l_knee_out, _ = self.actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(self.data.qvel[self.qvel_addr["left_knee"]])
        )
        r_hip_out, _ = self.actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(self.data.qvel[self.qvel_addr["right_hip"]])
        )
        r_knee_out, _ = self.actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(self.data.qvel[self.qvel_addr["right_knee"]])
        )

        return np.array(
            [l_hip_out, l_knee_out, r_hip_out, r_knee_out], dtype=np.float32
        )

    def _update_fsm_state(self, t: float):
        """更新FSM状态（触地事件检测）。"""
        left_c, right_c = contact_flags(self.model, self.data)

        p = self.params.base
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
                # 与V13.7一致：仅在已有accepted_contact时才计数（此处不计数alternations，仅更新状态）
                self.accepted_contact = foot
                self.support_foot = foot
                self.burst_start_t = t
                self.last_event_t = t
                self.last_contact_t = t
                self.contact_reported[foot] = True  # 标记已报告，防止重复触发
                break  # 每次只处理一个事件

    def _get_obs(self) -> np.ndarray:
        """构建42维观测向量。

        Returns:
            42维观测数组
        """
        # 原始20维观测
        joint_angles = np.array(
            [
                self.data.qpos[2],  # left_hip
                self.data.qpos[3],  # left_knee
                self.data.qpos[4],  # left_ankle
                self.data.qpos[5],  # right_hip
                self.data.qpos[6],  # right_knee
                self.data.qpos[7],  # right_ankle
            ],
            dtype=np.float32,
        )

        joint_velocities = np.array(
            [
                self.data.qvel[2],  # left_hip
                self.data.qvel[3],  # left_knee
                self.data.qvel[4],  # left_ankle
                self.data.qvel[5],  # right_hip
                self.data.qvel[6],  # right_knee
                self.data.qvel[7],  # right_ankle
            ],
            dtype=np.float32,
        )

        hip_body_id = self.model.body("hip").id
        hip_pos = self.data.xpos[hip_body_id][[0, 2]].astype(np.float32)
        hip_vel = self.data.cvel[hip_body_id][[3, 5]].astype(np.float32)

        contact_states = self._get_contact_states()

        # 新增22维观测
        # 1. left_phase one-hot (4维)
        left_phase = self._get_phase("left")
        left_phase_onehot = np.zeros(4, dtype=np.float32)
        left_phase_onehot[left_phase] = 1.0

        # 2. right_phase one-hot (4维)
        right_phase = self._get_phase("right")
        right_phase_onehot = np.zeros(4, dtype=np.float32)
        right_phase_onehot[right_phase] = 1.0

        # 3. support_foot one-hot (2维)
        support_onehot = np.zeros(2, dtype=np.float32)
        if self.support_foot == "left":
            support_onehot[0] = 1.0
        else:
            support_onehot[1] = 1.0

        # 4. time_since_last_contact (1维，归一化)
        t = self.micro_steps * self.dt
        t_since_contact = t - self.last_contact_t if self.last_event_t >= 0 else 0.0
        t_since_contact_norm = np.clip(t_since_contact / 1.5, 0.0, 2.0)

        # 5. time_since_burst_start (1维，归一化)
        t_since_burst = t - self.burst_start_t
        t_since_burst_norm = np.clip(t_since_burst / 1.5, 0.0, 2.0)

        # 6. E_current, E_current-E_ref (2维，归一化)
        E_current = _mechanical_energy(self.params.base, self.data)
        E_ref = (
            self.params.fsm.swing_thrust.E_target
        )  # 从swing_thrust phase获取E_target
        E_current_norm = E_current / self.E_ref_mean
        E_diff_norm = (E_current - E_ref) / self.E_ref_mean

        # 7. V13.7 base torques (4维，归一化)
        base_torques_norm = self.last_base_torques / 4.0

        # 8. last residuals (4维，归一化)
        last_residuals_norm = self.last_residuals / max(self.residual_scale, 1e-6)

        # 拼接所有观测
        obs = np.concatenate(
            [
                joint_angles,  # 6
                joint_velocities,  # 6
                hip_pos,  # 2
                hip_vel,  # 2
                contact_states,  # 4
                left_phase_onehot,  # 4
                right_phase_onehot,  # 4
                support_onehot,  # 2
                [t_since_contact_norm],  # 1
                [t_since_burst_norm],  # 1
                [E_current_norm],  # 1
                [E_diff_norm],  # 1
                base_torques_norm,  # 4
                last_residuals_norm,  # 4
            ]
        ).astype(np.float32)

        return obs

    def _get_contact_states(self) -> np.ndarray:
        """检测足部接触状态。

        Returns:
            4维二进制数组 [left_heel, left_toe, right_heel, right_toe]
        """
        foot_geom_names = ["left_heel", "left_toe", "right_heel", "right_toe"]
        foot_geom_ids = [self.model.geom(name).id for name in foot_geom_names]
        contact_states = np.zeros(4, dtype=np.float32)

        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            geom1 = contact.geom1
            geom2 = contact.geom2

            for j, foot_geom_id in enumerate(foot_geom_ids):
                if geom1 == foot_geom_id or geom2 == foot_geom_id:
                    if np.linalg.norm(contact.frame[:3]) > 0.1:
                        contact_states[j] = 1.0

        return contact_states

    def _compute_reward(self, dx: float) -> float:
        """计算baseline-relative reward。

        Args:
            dx: 当前step的前进距离

        Returns:
            标量奖励值
        """
        # 1. 前进奖励（与baseline对比）
        dx_ref = self.baseline_dx_per_step
        forward_reward = 50.0 * (dx - dx_ref)

        # 2. Residual cost（鼓励小修正）
        residual_cost = np.sum(self.last_residuals**2)

        # 3. Smoothness cost（动作平滑）
        if hasattr(self, "prev_residuals"):
            smooth_cost = np.sum((self.last_residuals - self.prev_residuals) ** 2)
        else:
            smooth_cost = 0.0
        self.prev_residuals = self.last_residuals.copy()

        # 4. Excess work（相对baseline的额外功耗）
        # 近似：residual力矩 × 关节速度
        work = 0.0
        work += abs(self.last_residuals[0] * self.data.qvel[self.qvel_addr["left_hip"]])
        work += abs(
            self.last_residuals[2] * self.data.qvel[self.qvel_addr["right_hip"]]
        )
        excess_work = work * self.dt * self.inner_steps
        self.episode_work += excess_work

        reward = (
            forward_reward
            - 0.02 * residual_cost
            - 0.01 * smooth_cost
            - 0.02 * excess_work
        )

        return reward

    def _is_terminated(self) -> bool:
        """检查是否摔倒。"""
        failure = classify_failure(
            self.model, self.data, self.params.base, self.start_x, self.last_control_t
        )
        self.failure_reason = failure or ""
        return bool(failure)

    def _is_truncated(self) -> bool:
        """检查是否达到最大步数。"""
        return self.steps >= self.max_steps

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        """重置环境。"""
        super().reset(seed=seed)

        # 重置MuJoCo仿真
        initialize(self.model, self.data, self.params.base)

        # 重置电机
        for act in self.actuators.values():
            act.saturation_count = 0

        # 重置状态
        self.steps = 0
        self.micro_steps = 0
        self.sim_time = 0.0
        self.last_control_t = 0.0
        self.start_x = float(self.data.qpos[0])
        self.max_x = self.start_x
        self.last_hip_x = self.start_x
        self.support_foot = "left"
        self.burst_start_t = -self.params.base.gait_period  # 初始化为负值，与V13.7一致
        self.last_contact_t = 0.0
        self.accepted_contact = ""
        self.candidate_start_t = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}
        self.last_event_t = -1.0
        self.last_residuals = np.zeros(4, dtype=np.float32)
        self.last_base_torques = np.zeros(4, dtype=np.float32)
        self.last_mode_label = ""
        self.last_left_phase_label = ""
        self.last_right_phase_label = ""
        self.failure_reason = ""
        self.episode_distance = 0.0
        self.episode_work = 0.0

        if hasattr(self, "prev_residuals"):
            delattr(self, "prev_residuals")

        observation = self._get_obs()
        info = {"hip_x": self.last_hip_x}

        return observation, info

    def step(self, action: np.ndarray):
        """执行一步（200Hz PPO频率，内部运行5个1ms步）。

        Args:
            action: 2维residual动作 [left_hip, right_hip]

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Clip action
        action = np.clip(action, self.action_space.low, self.action_space.high)

        # 映射到4维residual [left_hip, 0, right_hip, 0]
        residual = np.zeros(4, dtype=np.float32)
        residual[0] = self.residual_scale * action[0]  # left_hip
        residual[1] = 0.0  # left_knee
        residual[2] = self.residual_scale * action[1]  # right_hip
        residual[3] = 0.0  # right_knee

        self.last_residuals = residual.copy()

        total_reward = 0.0
        hip_x_start = float(self.data.qpos[0])
        terminated = False

        # 内环：运行inner_steps个1ms步
        for k in range(self.inner_steps):
            # V13.7计算基础力矩（1kHz更新）
            t = self.micro_steps * self.dt
            self.last_control_t = t

            tau_v137 = self._compute_v137_base_control(t)
            self.last_base_torques = tau_v137.copy()

            # PPO添加residual修正
            tau_total = tau_v137 + residual

            # Clip到硬件限制
            tau_total = np.clip(tau_total, -4.0, 4.0)

            # 应用控制
            self.data.ctrl[:] = tau_total

            # 仿真步进
            mujoco.mj_step(self.model, self.data)

            # 更新FSM状态
            self._update_fsm_state(t)

            self.micro_steps += 1
            self.sim_time = self.micro_steps * self.dt
            self.max_x = max(self.max_x, float(self.data.qpos[0]))

            self.failure_reason = classify_failure(
                self.model,
                self.data,
                self.params.base,
                self.start_x,
                t,
            )
            if self.failure_reason:
                terminated = True
                break

        # PPO步数+1
        self.steps += 1

        # 计算前进距离
        hip_x_end = float(self.data.qpos[0])
        dx = hip_x_end - hip_x_start
        self.episode_distance = self.max_x - self.start_x

        # 计算奖励
        reward = self._compute_reward(dx)
        total_reward = reward

        # 获取新观测
        observation = self._get_obs()

        # 检查终止条件
        terminated = terminated or self._is_terminated()
        truncated = self._is_truncated()

        # Episode结束时的额外奖励
        if truncated:
            # 完整episode成功，给予改进奖励
            final_improvement = self.episode_distance - (
                self.baseline_dx_per_step * self.max_steps
            )
            total_reward += 100.0 * final_improvement

        if terminated:
            # 摔倒惩罚
            total_reward -= 50.0

        # Info
        hip_body_id = self.model.body("hip").id
        hip_x = self.data.xpos[hip_body_id][0]
        hip_height = self.data.xpos[hip_body_id][2]
        hip_vel_x = self.data.cvel[hip_body_id][3]

        info = {
            "hip_x": hip_x,
            "hip_height": hip_height,
            "hip_vel_x": hip_vel_x,
            "episode_distance": self.episode_distance,
            "forward_distance": self.episode_distance,
            "episode_work": self.episode_work,
            "sim_time": self.last_control_t,
            "residual_scale": self.residual_scale,
            "failure_reason": self.failure_reason or "",
            "left_phase": self.last_left_phase_label,
            "right_phase": self.last_right_phase_label,
            "mode_label": self.last_mode_label,
        }

        return observation, total_reward, terminated, truncated, info

    def render(self):
        """渲染环境。"""
        if self.render_mode == "human":
            if self.renderer is not None:
                self.renderer.sync()
        elif self.render_mode == "rgb_array":
            if self.renderer is not None:
                self.renderer.update_scene(self.data)
                return self.renderer.render()
        return None

    def close(self):
        """清理资源。"""
        if self.renderer is not None:
            if self.render_mode == "human":
                self.renderer.close()
            self.renderer = None


def make_residual_env_v2(**kwargs):
    """创建Residual RL V2环境工厂函数。"""

    def _init():
        env = ResidualRLEnvV2(**kwargs)
        return env

    return _init


def train_residual_rl_v2(
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    residual_scale: float = 0.05,
    inner_steps: int = 5,
    max_steps: int = 500,
    log_dir: str = "rl_training/logs/residual_rl_v2",
    model_save_path: str = "rl_training/models/residual_rl_v2",
):
    """训练Residual RL V2策略。

    Args:
        total_timesteps: 总训练步数
        learning_rate: 学习率
        n_steps: 每次更新收集的步数
        batch_size: 小批量大小
        n_epochs: 每次更新的epoch数
        residual_scale: Residual缩放系数
        inner_steps: 内环步数（5=200Hz PPO频率）
        max_steps: 最大episode步数（500步=2.5秒）
        log_dir: 日志目录
        model_save_path: 模型保存路径
    """
    # 创建目录
    log_path = HW1_ROOT / log_dir
    model_path = HW1_ROOT / model_save_path
    log_path.mkdir(parents=True, exist_ok=True)
    model_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Residual RL V2训练配置")
    print("=" * 80)
    print(f"总训练步数: {total_timesteps}")
    print(f"PPO频率: {1000 / inner_steps:.0f} Hz (inner_steps={inner_steps})")
    print(f"Episode长度: {max_steps} steps = {max_steps * inner_steps / 1000:.2f}s")
    print(f"Residual scale: {residual_scale}")
    print(f"Action维度: 2 (hip-only)")
    print(f"Observation维度: 42 (20原始 + 22新增)")
    print(f"学习率: {learning_rate}")
    print("=" * 80)

    # 创建环境
    def make_env():
        return ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )

    env = DummyVecEnv([make_env])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # 创建PPO模型
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=str(log_path / "tensorboard"),
    )

    # 训练
    print("\n开始训练...")
    model.learn(
        total_timesteps=total_timesteps,
        progress_bar=True,
    )

    # 保存最终模型
    final_model_path = model_path / "final_model"
    model.save(str(final_model_path))
    env.save(str(model_path / "vec_normalize.pkl"))

    print(f"\n训练完成！模型已保存到: {final_model_path}")

    return model, env


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="训练Residual RL V2策略")
    parser.add_argument("--total-timesteps", type=int, default=100000)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--residual-scale", type=float, default=0.05)

    args = parser.parse_args()

    train_residual_rl_v2(
        total_timesteps=args.total_timesteps,
        learning_rate=args.learning_rate,
        residual_scale=args.residual_scale,
    )

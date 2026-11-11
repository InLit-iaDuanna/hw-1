"""Residual RL训练：PPO学习在V13.7基础上的微调。

核心思想：
- V13.7控制器在1kHz内环运行，提供基础步态
- PPO每20ms输出小幅residual修正（±0.5 N·m）
- PPO只需学习微调，不需要从零发明步态
- 基础控制器维护所有FSM隐状态

优势：
- 样本效率高（基础步态已稳定）
- 动作空间小（residual范围小）
- 物理可解释（V13.7 + 修正项）
- 训练稳定（不会破坏基础步态）

运行方式：
    cd D:\\Dunna\\Documents\\hw-1
    .venv-mujoco\\Scripts\activate
    python rl_training\train_residual_rl.py --total-timesteps 500000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
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

from simulate_passive_arms_v14 import contact_flags
from simulate_v13_6 import control_v136
from simulate_v13_7 import (
    MODEL_PATH,
    V137Params,
    _compensate,
    _mechanical_energy,
    write_model_v137,
)

from common.motor_dynamics import PRESETS as MOTOR_PRESETS
from common.motor_dynamics import L1MotorActuator


class ResidualRLEnv(gym.Env):
    """Residual RL环境：V13.7 + PPO微调。

    V13.7在1kHz内环运行，PPO每20ms输出residual修正。
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(
        self,
        params: Optional[V137Params] = None,
        residual_limit: float = 0.5,
        residual_scale: float = 1.0,
        inner_steps: int = 20,
        max_steps: int = 500,
        reward_type: str = "forward_velocity",
        fall_height_threshold: float = 0.2,
        render_mode: Optional[str] = None,
    ):
        """初始化Residual RL环境。

        Args:
            params: V13.7参数（None则使用默认）
            residual_limit: residual动作范围 (±residual_limit N·m)
            residual_scale: curriculum缩放系数（0.0-1.0，训练时动态调整）
            inner_steps: 每个PPO step内部运行多少个1ms step（20=50Hz PPO频率）
            max_steps: 最大episode步数（PPO steps，不是1ms steps）
            reward_type: 奖励类型 ("forward_velocity", "energy_efficient")
            fall_height_threshold: 髋部高度阈值（低于此高度判定摔倒）
            render_mode: 渲染模式
        """
        super().__init__()

        # 参数
        if params is None:
            from simulate_v14c import make_v14c_params

            base_params = make_v14c_params(slope_deg=0.0)
            params = V137Params(
                base=base_params,
                fsm=base_params,
                hip_motor=MOTOR_PRESETS["mx64ar"],
                knee_motor=MOTOR_PRESETS["mx64ar"],
                compensate_friction=True,
            )
        self.params = params
        self.residual_limit = residual_limit
        self.residual_scale = residual_scale
        self.inner_steps = inner_steps
        self.max_steps = max_steps
        self.reward_type = reward_type
        self.fall_height_threshold = fall_height_threshold
        self.render_mode = render_mode
        self.dt = 0.001  # 1kHz仿真步长

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

        # FSM隐状态（由V13.7维护）
        self.support_foot = "left"
        self.burst_start_t = 0.0

        # 添加扩展观测支持
        self.use_extended_obs = False  # 可选：FSM隐状态 + 机械能

        # Gymnasium空间定义
        # Action: 4维residual [left_hip, left_knee, right_hip, right_knee]
        self.action_space = spaces.Box(
            low=-residual_limit, high=residual_limit, shape=(4,), dtype=np.float32
        )

        # Observation: 20维或24维（可选扩展）
        if self.use_extended_obs:
            # 扩展观测：20维基础 + 4维额外 [support_left, support_right, time_since_touchdown, E_current]
            obs_dim = 24
        else:
            # 基础观测：20维 [joint_angles(6), joint_velocities(6), hip_pos(2), hip_vel(2), contact(4)]
            obs_dim = 20

        obs_low = np.array(
            [
                -np.pi,
                0,
                -np.pi / 6,
                -np.pi,
                0,
                -np.pi / 6,  # joint angles (rad)
                -10,
                -10,
                -10,
                -10,
                -10,
                -10,  # joint velocities (rad/s)
                -np.inf,
                0.0,  # hip position x, z
                -10,
                -10,  # hip velocity vx, vz
                0,
                0,
                0,
                0,  # contact states
            ],
            dtype=np.float32,
        )

        obs_high = np.array(
            [
                np.pi,
                np.pi * 70 / 180,
                np.pi / 6,
                np.pi,
                np.pi * 70 / 180,
                np.pi / 6,
                10,
                10,
                10,
                10,
                10,
                10,
                np.inf,
                2.0,
                10,
                10,
                1,
                1,
                1,
                1,
            ],
            dtype=np.float32,
        )

        if self.use_extended_obs:
            # 添加扩展维度
            obs_low = np.concatenate([obs_low, [0, 0, 0, 0]])
            obs_high = np.concatenate([obs_high, [1, 1, 1.0, 10.0]])

        self.observation_space = spaces.Box(
            low=obs_low, high=obs_high, dtype=np.float32
        )

        # 状态跟踪
        self.steps = 0
        self.sim_time = 0.0
        self.last_hip_x = 0.0
        self.cumulative_energy = 0.0

        # 渲染
        self.renderer = None
        if self.render_mode is not None:
            self._setup_renderer()

    def _setup_renderer(self):
        """初始化渲染器。"""
        if self.render_mode == "human":
            from mujoco import viewer

            self.renderer = viewer.launch_passive(self.model, self.data)
        elif self.render_mode == "rgb_array":
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)

    def _compute_v137_base_control(self) -> np.ndarray:
        """计算V13.7基础控制力矩（完整版本，1kHz更新）。

        Returns:
            4维力矩数组 [left_hip, left_knee, right_hip, right_knee]
        """
        E_current = _mechanical_energy(self.params.base, self.data)

        # V13.6 FSM控制律
        tau = control_v136(
            self.params.fsm,
            self.data,
            self.sim_time,
            self.support_foot,
            self.burst_start_t,
            E_current,
        )
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
            [l_hip_out, l_knee_out, r_hip_out, r_knee_out], dtype=np.float64
        )

    def _update_fsm_state(self):
        """更新FSM状态（触地事件检测）。"""
        left_c, right_c = contact_flags(self.model, self.data)

        # 检测新触地事件
        if left_c and self.support_foot != "left":
            self.support_foot = "left"
            self.burst_start_t = self.sim_time
        elif right_c and self.support_foot != "right":
            self.support_foot = "right"
            self.burst_start_t = self.sim_time

    def _get_obs(self) -> np.ndarray:
        """构建观测向量（20维或24维）。

        Returns:
            观测数组
        """
        # Joint angles (6): [left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle]
        joint_angles = np.array(
            [
                self.data.qpos[2],  # left_hip
                self.data.qpos[3],  # left_knee
                self.data.qpos[4],  # left_ankle
                self.data.qpos[5],  # right_hip
                self.data.qpos[6],  # right_knee
                self.data.qpos[7],  # right_ankle
            ]
        )

        # Joint velocities (6)
        joint_velocities = np.array(
            [
                self.data.qvel[2],  # left_hip
                self.data.qvel[3],  # left_knee
                self.data.qvel[4],  # left_ankle
                self.data.qvel[5],  # right_hip
                self.data.qvel[6],  # right_knee
                self.data.qvel[7],  # right_ankle
            ]
        )

        # Hip position (2): x, z
        hip_body_id = self.model.body("hip").id
        hip_pos = self.data.xpos[hip_body_id][[0, 2]]

        # Hip velocity (2): vx, vz
        hip_vel = self.data.cvel[hip_body_id][[3, 5]]

        # Contact states (4): binary indicator
        contact_states = self._get_contact_states()

        obs = np.concatenate(
            [joint_angles, joint_velocities, hip_pos, hip_vel, contact_states]
        ).astype(np.float32)

        # 可选：添加扩展观测
        if self.use_extended_obs:
            support_left = 1.0 if self.support_foot == "left" else 0.0
            support_right = 1.0 if self.support_foot == "right" else 0.0
            time_since_touchdown = min(self.sim_time - self.burst_start_t, 1.0)
            E_current = _mechanical_energy(self.params.base, self.data)

            extended_obs = np.array(
                [support_left, support_right, time_since_touchdown, E_current],
                dtype=np.float32,
            )
            obs = np.concatenate([obs, extended_obs])

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

    def _compute_reward(self, action: np.ndarray) -> float:
        """计算奖励（改进版本）。

        Args:
            action: Residual动作

        Returns:
            标量奖励值
        """
        hip_body_id = self.model.body("hip").id
        hip_vel_x = self.data.cvel[hip_body_id][3]
        hip_height = self.data.xpos[hip_body_id][2]
        hip_x = self.data.xpos[hip_body_id][0]

        if self.reward_type == "forward_velocity":
            # 前进奖励（主要目标）
            forward_reward = 10.0 * hip_vel_x

            # Residual惩罚（鼓励小修正，使用L2范数）
            residual_penalty = 0.1 * np.sum(action**2)

            # 能耗惩罚（近似：力矩×角速度）
            energy_cost = 0.0
            for i, joint_name in enumerate(
                ["left_hip", "left_knee", "right_hip", "right_knee"]
            ):
                qvel_idx = self.qvel_addr[joint_name]
                tau = self.data.ctrl[i]
                vel = self.data.qvel[qvel_idx]
                energy_cost += abs(tau * vel)
            energy_penalty = 0.01 * energy_cost

            # 存活奖励
            alive_bonus = 1.0

            return forward_reward - residual_penalty - energy_penalty + alive_bonus

        elif self.reward_type == "energy_efficient":
            # 能量高效奖励
            forward_reward = 5.0 * hip_vel_x

            # 能量成本（包括residual）
            energy_cost = np.sum(action**2)
            self.cumulative_energy += energy_cost
            energy_penalty = 0.01 * energy_cost

            # 平滑性惩罚
            if hasattr(self, "last_action"):
                smoothness_penalty = 0.001 * np.sum((action - self.last_action) ** 2)
            else:
                smoothness_penalty = 0.0

            self.last_action = action.copy()

            return forward_reward - energy_penalty - smoothness_penalty

        else:
            raise ValueError(f"Unknown reward type: {self.reward_type}")

    def _is_terminated(self) -> bool:
        """检查是否摔倒。"""
        hip_body_id = self.model.body("hip").id
        hip_height = self.data.xpos[hip_body_id][2]
        hip_y = self.data.xpos[hip_body_id][1]

        # 髋部过低或侧倾过大
        return hip_height < self.fall_height_threshold or abs(hip_y) > 0.5

    def _is_truncated(self) -> bool:
        """检查是否达到最大步数。"""
        return self.steps >= self.max_steps

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        """重置环境。"""
        super().reset(seed=seed)

        # 重置MuJoCo仿真
        mujoco.mj_resetData(self.model, self.data)

        # 初始姿态
        self.data.qpos[0] = 0.0  # hip_x
        self.data.qpos[1] = 1.0  # hip_z

        # 添加小扰动
        if self.np_random is not None:
            noise = self.np_random.normal(0, 0.01, size=6)
            for i in range(6):
                self.data.qpos[i + 2] += noise[i]

        mujoco.mj_forward(self.model, self.data)

        # 重置状态
        self.steps = 0
        self.sim_time = 0.0
        hip_body_id = self.model.body("hip").id
        self.last_hip_x = self.data.xpos[hip_body_id][0]
        self.cumulative_energy = 0.0
        self.support_foot = "left"
        self.burst_start_t = 0.0

        if hasattr(self, "last_action"):
            delattr(self, "last_action")

        observation = self._get_obs()
        info = {"hip_x": self.last_hip_x}

        return observation, info

    def step(self, action: np.ndarray):
        """执行一步（PPO频率，内部运行inner_steps个1ms步）。

        Args:
            action: 4维residual动作 [left_hip, left_knee, right_hip, right_knee]

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Clip action
        action = np.clip(action, self.action_space.low, self.action_space.high)

        # 应用residual_scale进行curriculum learning
        scaled_action = action * self.residual_scale

        total_reward = 0.0

        # 内环：运行inner_steps个1ms步
        for k in range(self.inner_steps):
            # V13.7计算基础力矩（1kHz更新）
            tau_v137 = self._compute_v137_base_control()

            # PPO添加residual修正
            tau_total = tau_v137 + scaled_action

            # Clip到硬件限制
            tau_total = np.clip(tau_total, -4.0, 4.0)

            # 应用控制
            self.data.ctrl[:] = tau_total

            # 仿真步进
            mujoco.mj_step(self.model, self.data)
            self.sim_time += self.dt

            # 更新FSM状态
            self._update_fsm_state()

            # 累积奖励
            total_reward += self._compute_reward(scaled_action)

        # PPO步数+1
        self.steps += 1

        # 获取新观测
        observation = self._get_obs()

        # 检查终止条件
        terminated = self._is_terminated()
        truncated = self._is_truncated()

        # Info
        hip_body_id = self.model.body("hip").id
        hip_x = self.data.xpos[hip_body_id][0]
        hip_height = self.data.xpos[hip_body_id][2]
        hip_vel_x = self.data.cvel[hip_body_id][3]

        info = {
            "hip_x": hip_x,
            "hip_height": hip_height,
            "hip_vel_x": hip_vel_x,
            "distance_traveled": hip_x - self.last_hip_x,
            "sim_time": self.sim_time,
            "residual_scale": self.residual_scale,
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


def make_residual_env(residual_scale: float = 1.0, **kwargs):
    """创建Residual RL环境工厂函数。

    Args:
        residual_scale: curriculum缩放系数
        **kwargs: 其他ResidualRLEnv参数
    """

    def _init():
        env = ResidualRLEnv(residual_scale=residual_scale, **kwargs)
        return env

    return _init


def train_residual_rl(
    total_timesteps: int = 500000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    residual_limit: float = 0.5,
    inner_steps: int = 20,
    log_dir: str = "logs/residual_rl",
    model_save_path: str = "models/residual_rl",
):
    """训练Residual RL策略。

    Args:
        total_timesteps: 总训练步数
        learning_rate: 学习率
        n_steps: 每次更新收集的步数
        batch_size: 小批量大小
        n_epochs: 每次更新的epoch数
        residual_limit: Residual动作范围
        inner_steps: 内环步数（20=50Hz PPO频率）
        log_dir: 日志目录
        model_save_path: 模型保存路径
    """
    # 创建目录
    log_path = HW1_ROOT / log_dir
    model_path = HW1_ROOT / model_save_path
    log_path.mkdir(parents=True, exist_ok=True)
    model_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Residual RL训练配置")
    print("=" * 80)
    print(f"总训练步数: {total_timesteps}")
    print(f"PPO频率: {1000 / inner_steps:.0f} Hz (inner_steps={inner_steps})")
    print(f"Residual范围: ±{residual_limit} N·m")
    print(f"学习率: {learning_rate}")
    print(f"n_steps: {n_steps}")
    print(f"batch_size: {batch_size}")
    print(f"n_epochs: {n_epochs}")
    print("=" * 80)

    # 创建环境
    def make_env():
        return ResidualRLEnv(
            residual_limit=residual_limit,
            inner_steps=inner_steps,
            max_steps=500,
            reward_type="forward_velocity",
        )

    env = DummyVecEnv([make_env])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # 创建评估环境
    eval_env = DummyVecEnv([make_env])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.0)

    # 回调
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(model_path / "best"),
        log_path=str(log_path / "eval"),
        eval_freq=10000,
        deterministic=True,
        render=False,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(model_path / "checkpoints"),
        name_prefix="residual_rl",
    )

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
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True,
    )

    # 保存最终模型
    final_model_path = model_path / "final_model"
    model.save(str(final_model_path))
    env.save(str(model_path / "vec_normalize.pkl"))

    print(f"\n训练完成！模型已保存到: {final_model_path}")
    print(f"最佳模型: {model_path / 'best'}")

    return model, env


def main():
    parser = argparse.ArgumentParser(description="训练Residual RL策略")
    parser.add_argument(
        "--total-timesteps", type=int, default=500000, help="总训练步数"
    )
    parser.add_argument("--learning-rate", type=float, default=3e-4, help="学习率")
    parser.add_argument(
        "--residual-limit", type=float, default=0.5, help="Residual动作范围"
    )
    parser.add_argument(
        "--inner-steps", type=int, default=20, help="内环步数（20=50Hz）"
    )
    parser.add_argument(
        "--log-dir", type=str, default="logs/residual_rl", help="日志目录"
    )
    parser.add_argument(
        "--model-save-path", type=str, default="models/residual_rl", help="模型保存路径"
    )

    args = parser.parse_args()

    train_residual_rl(
        total_timesteps=args.total_timesteps,
        learning_rate=args.learning_rate,
        residual_limit=args.residual_limit,
        inner_steps=args.inner_steps,
        log_dir=args.log_dir,
        model_save_path=args.model_save_path,
    )


if __name__ == "__main__":
    main()

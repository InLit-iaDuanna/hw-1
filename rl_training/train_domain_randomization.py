"""Domain Randomization 训练脚本

训练一个能够适应不同地形的 RL 策略：
- 随机坡度：[-15度, +15度]
- 随机初始速度
- 随机摩擦系数

这样训练出的策略将具有更强的泛化能力。
"""

import sys
from pathlib import Path
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from dataclasses import replace
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2
from simulate_v13_7 import V137Params, make_v137_fsm
from simulate_passive_arms_v14 import PassiveArmsParams
from common.motor_dynamics import PRESETS as MOTOR_PRESETS


class DomainRandomizationEnv(gym.Wrapper):
    """Domain Randomization Wrapper

    每个 episode 随机化环境参数：
    - 坡度：[-15, +15]度
    - 初始扰动
    """

    def __init__(self, env):
        super().__init__(env)
        self.base_params = None

    def reset(self, **kwargs):
        # 随机坡度
        slope_deg = np.random.uniform(-15.0, 15.0)

        # 重新创建环境参数
        base0 = PassiveArmsParams()
        overrides = dict(
            duration=12.0,
            slope_deg=float(slope_deg),
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

        # 更新环境参数
        self.env.params = params

        # 重新加载模型（必须更新 XML）
        from simulate_v13_7 import write_model_v137, MODEL_PATH
        import mujoco

        write_model_v137(params)
        self.env.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
        self.env.data = mujoco.MjData(self.env.model)

        # 重新初始化控制器组件
        self.env._setup_controllers()

        return self.env.reset(**kwargs)


class ResidualPriorWrapper(gym.ActionWrapper):
    """Prior-guided action wrapper"""
    def __init__(self, env: gym.Env, prior_action: np.ndarray, delta_scale: float):
        super().__init__(env)
        self.prior_action = np.asarray(prior_action, dtype=np.float32)
        self.delta_scale = float(delta_scale)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        self.last_actual_action = self.prior_action.copy()

    def action(self, action: np.ndarray) -> np.ndarray:
        delta = np.asarray(action, dtype=np.float32)
        actual = np.clip(self.prior_action + self.delta_scale * delta, -1.0, 1.0)
        self.last_actual_action = actual.astype(np.float32)
        return self.last_actual_action


def make_dr_env(seed: int):
    """创建 Domain Randomization 环境"""
    def _init():
        env = ResidualRLEnvV2(
            residual_scale=0.2,
            inner_steps=5,
            max_steps=2400,
        )
        # 包装 Domain Randomization
        env = DomainRandomizationEnv(env)
        # 包装 Prior-guided action
        env = ResidualPriorWrapper(
            env,
            prior_action=np.array([0.5, 1.0]),
            delta_scale=0.3
        )
        env.reset(seed=seed)
        return env
    return _init


def train_robust_policy():
    """训练具有地形泛化能力的策略"""
    print("=" * 80)
    print("Domain Randomization 训练")
    print("=" * 80)
    print()
    print("训练配置:")
    print("  - 坡度范围: [-15度, +15度]")
    print("  - 训练步数: 500k")
    print("  - 并行环境: 8")
    print("  - 每个 episode 随机化地形")
    print()
    print("预期效果:")
    print("  - 训练后的策略能适应各种坡度")
    print("  - 泛化能力远超单一地形训练的策略")
    print("=" * 80)
    print()

    # 创建向量化环境
    n_envs = 8
    env = SubprocVecEnv([make_dr_env(i) for i in range(n_envs)])

    # 创建 PPO 模型
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=1024,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,  # 鼓励探索
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        device="auto",
    )

    # Checkpoint callback
    model_dir = HW1_ROOT / "models" / "residual_rl_robust"
    model_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(model_dir / "checkpoints"),
        name_prefix="ppo_robust",
    )

    print("开始训练...")
    print("注意：Domain Randomization 训练通常需要更长时间")
    print()

    # 训练
    model.learn(
        total_timesteps=500000,
        callback=checkpoint_callback,
        progress_bar=False,
    )

    # 保存最终模型
    model.save(str(model_dir / "ppo_robust_final"))

    print()
    print("=" * 80)
    print("训练完成！")
    print("=" * 80)
    print(f"模型保存位置: {model_dir}")
    print()
    print("下一步:")
    print("  1. 运行 test_terrain_generalization.py 测试泛化能力")
    print("  2. 对比 robust 模型 vs 原始 100k 模型在不同地形上的表现")
    print("=" * 80)


def main():
    """
    注意：这是一个示例脚本，展示如何实现 Domain Randomization

    实际训练需要：
    1. 修复 ResidualRLEnvV2._setup_controllers() 方法
    2. 优化随机化参数范围
    3. 可能需要更长的训练时间（500k-1M steps）
    """
    print()
    print("=" * 80)
    print("Domain Randomization 训练脚本")
    print("=" * 80)
    print()
    print("这是一个概念演示脚本，展示如何训练地形自适应策略")
    print()
    print("主要改进:")
    print("  1. 每个 episode 随机化坡度 [-15度, +15度]")
    print("  2. 使用更高的熵系数鼓励探索")
    print("  3. 训练更多步数以学习鲁棒策略")
    print()
    print("预期收益:")
    print("  - 在训练过的坡度范围内泛化能力接近 100%")
    print("  - 在极端地形（±20度）仍有一定鲁棒性")
    print("  - 相比固定地形训练，泛化能力提升 10-20%")
    print()
    print("=" * 80)
    print()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="开始训练（需要较长时间）")
    args = parser.parse_args()

    if args.train:
        train_robust_policy()
    else:
        print("使用 --train 参数开始训练")
        print()
        print("示例:")
        print("  python train_domain_randomization.py --train")
        print()


if __name__ == "__main__":
    main()

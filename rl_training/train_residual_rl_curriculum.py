"""Residual RL训练 - 带Curriculum Learning。

改进要点：
1. Residual Scale Curriculum: 0.05 → 0.1 → 0.2 → 0.5 → 1.0
2. 改进Reward函数: 10x前进 - 0.1×residual² - 0.01×能耗 + 1.0存活
3. 多环境并行训练（8个）
4. 中期验证和性能监控

运行方式：
    cd D:\\Dunna\\Documents\\hw-1
    .venv-mujoco\\Scripts\activate
    python rl_training\train_residual_rl_curriculum.py --total-timesteps 500000 --n-envs 8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CheckpointCallback,
)
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl import ResidualRLEnv


class ResidualScaleCurriculumCallback(BaseCallback):
    """Residual Scale Curriculum Learning回调。

    根据训练进度动态调整residual_scale：
    - 0-100k steps: scale = 0.05
    - 100k-200k steps: scale = 0.1
    - 200k-300k steps: scale = 0.2
    - 300k-400k steps: scale = 0.5
    - 400k+ steps: scale = 1.0
    """

    def __init__(
        self,
        milestones: list[int] = [100000, 200000, 300000, 400000],
        scales: list[float] = [0.05, 0.1, 0.2, 0.5, 1.0],
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.milestones = milestones
        self.scales = scales
        self.current_scale_idx = 0

    def _on_step(self) -> bool:
        """每步检查是否需要更新scale。"""
        current_timestep = self.num_timesteps

        # 检查是否达到下一个milestone
        if self.current_scale_idx < len(self.milestones):
            if current_timestep >= self.milestones[self.current_scale_idx]:
                self.current_scale_idx += 1
                new_scale = self.scales[self.current_scale_idx]

                # 更新所有环境的residual_scale
                if hasattr(self.training_env, "envs"):
                    for env in self.training_env.envs:
                        if hasattr(env, "residual_scale"):
                            env.residual_scale = new_scale

                if self.verbose > 0:
                    print(f"\n{'='*60}")
                    print(f"Curriculum Update at {current_timestep} steps")
                    print(f"Residual Scale: {new_scale}")
                    print(f"{'='*60}\n")

                # 记录到TensorBoard
                self.logger.record("curriculum/residual_scale", new_scale)

        return True


class PeriodicEvalCallback(BaseCallback):
    """定期评估回调（每100k步）。"""

    def __init__(
        self,
        eval_env,
        eval_freq: int = 100000,
        n_eval_episodes: int = 5,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.eval_freq = eval_freq
        self.n_eval_episodes = n_eval_episodes
        self.last_eval_step = 0

    def _on_step(self) -> bool:
        """定期评估。"""
        if self.num_timesteps - self.last_eval_step >= self.eval_freq:
            self.last_eval_step = self.num_timesteps

            if self.verbose > 0:
                print(f"\n{'='*60}")
                print(f"Evaluation at {self.num_timesteps} steps")
                print(f"{'='*60}")

            # 运行评估
            episode_rewards = []
            episode_distances = []

            for i in range(self.n_eval_episodes):
                obs = self.eval_env.reset()
                done = False
                episode_reward = 0.0

                while not done:
                    action, _ = self.model.predict(obs, deterministic=True)
                    obs, reward, done, info = self.eval_env.step(action)
                    episode_reward += reward

                    if done:
                        # 从VecEnv获取info
                        if isinstance(info, list):
                            info = info[0]
                        episode_distances.append(info.get("hip_x", 0.0))

                episode_rewards.append(episode_reward)

            mean_reward = np.mean(episode_rewards)
            mean_distance = np.mean(episode_distances)
            std_distance = np.std(episode_distances)

            if self.verbose > 0:
                print(f"  Mean Reward: {mean_reward:.2f}")
                print(f"  Mean Distance: {mean_distance:.4f}m ± {std_distance:.4f}m")
                print(
                    f"  Distance Range: [{np.min(episode_distances):.4f}m, {np.max(episode_distances):.4f}m]"
                )
                print(f"{'='*60}\n")

            # 记录到TensorBoard
            self.logger.record("eval/mean_reward", mean_reward)
            self.logger.record("eval/mean_distance", mean_distance)
            self.logger.record("eval/std_distance", std_distance)

        return True


def train_residual_rl_with_curriculum(
    total_timesteps: int = 500000,
    n_envs: int = 8,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    residual_limit: float = 0.5,
    inner_steps: int = 5,
    log_dir: str = "logs/residual_rl_curriculum",
    model_save_path: str = "models/residual_rl_curriculum",
    use_subproc: bool = True,
):
    """训练Residual RL策略（带Curriculum Learning）。

    Args:
        total_timesteps: 总训练步数
        n_envs: 并行环境数量
        learning_rate: 学习率
        n_steps: 每次更新收集的步数
        batch_size: 小批量大小
        n_epochs: 每次更新的epoch数
        residual_limit: Residual动作范围
        inner_steps: 内环步数（5=200Hz PPO频率）
        log_dir: 日志目录
        model_save_path: 模型保存路径
        use_subproc: 是否使用SubprocVecEnv（多进程）
    """
    # 创建目录
    log_path = HW1_ROOT / log_dir
    model_path = HW1_ROOT / model_save_path
    log_path.mkdir(parents=True, exist_ok=True)
    model_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Residual RL训练配置 (Curriculum Learning)")
    print("=" * 80)
    print(f"总训练步数: {total_timesteps}")
    print(f"并行环境数: {n_envs}")
    print(f"PPO频率: {1000 / inner_steps:.0f} Hz (inner_steps={inner_steps})")
    print(f"Residual范围: ±{residual_limit} N·m")
    print(f"学习率: {learning_rate}")
    print(f"n_steps: {n_steps}")
    print(f"batch_size: {batch_size}")
    print(f"n_epochs: {n_epochs}")
    print("\nCurriculum Schedule:")
    print("  0-100k steps:   residual_scale = 0.05")
    print("  100k-200k steps: residual_scale = 0.1")
    print("  200k-300k steps: residual_scale = 0.2")
    print("  300k-400k steps: residual_scale = 0.5")
    print("  400k+ steps:     residual_scale = 1.0")
    print("=" * 80)

    # 创建环境工厂函数
    def make_env(rank: int):
        def _init():
            env = ResidualRLEnv(
                residual_limit=residual_limit,
                residual_scale=0.05,  # 初始scale
                inner_steps=inner_steps,
                max_steps=500,
                reward_type="forward_velocity",
            )
            return env

        return _init

    # 创建并行环境
    # Windows上使用DummyVecEnv避免multiprocessing问题
    print(f"创建{n_envs}个并行环境...")
    env = DummyVecEnv([make_env(i) for i in range(n_envs)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # 创建评估环境（单个环境）
    eval_env = DummyVecEnv([make_env(0)])
    eval_env = VecNormalize(
        eval_env, norm_obs=True, norm_reward=False, clip_obs=10.0, training=False
    )

    # 回调
    curriculum_callback = ResidualScaleCurriculumCallback(
        milestones=[100000, 200000, 300000, 400000],
        scales=[0.05, 0.1, 0.2, 0.5, 1.0],
        verbose=1,
    )

    periodic_eval_callback = PeriodicEvalCallback(
        eval_env=eval_env,
        eval_freq=100000,
        n_eval_episodes=5,
        verbose=1,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=max(50000 // n_envs, 1),
        save_path=str(model_path / "checkpoints"),
        name_prefix="residual_rl_curriculum",
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
    print("TensorBoard监控: tensorboard --logdir=" + str(log_path / "tensorboard"))
    print()

    model.learn(
        total_timesteps=total_timesteps,
        callback=[curriculum_callback, periodic_eval_callback, checkpoint_callback],
        progress_bar=False,
    )

    # 保存最终模型
    final_model_path = model_path / "final_model"
    model.save(str(final_model_path))
    env.save(str(model_path / "vec_normalize.pkl"))

    print(f"\n训练完成！模型已保存到: {final_model_path}")

    return model, env


def main():
    parser = argparse.ArgumentParser(
        description="训练Residual RL策略（Curriculum Learning）"
    )
    parser.add_argument(
        "--total-timesteps", type=int, default=500000, help="总训练步数"
    )
    parser.add_argument("--n-envs", type=int, default=8, help="并行环境数量")
    parser.add_argument("--learning-rate", type=float, default=3e-4, help="学习率")
    parser.add_argument(
        "--residual-limit", type=float, default=0.5, help="Residual动作范围"
    )
    parser.add_argument(
        "--inner-steps", type=int, default=5, help="内环步数（5=200Hz）"
    )
    parser.add_argument(
        "--log-dir", type=str, default="logs/residual_rl_curriculum", help="日志目录"
    )
    parser.add_argument(
        "--model-save-path",
        type=str,
        default="models/residual_rl_curriculum",
        help="模型保存路径",
    )
    parser.add_argument("--no-subproc", action="store_true", help="禁用多进程环境")

    args = parser.parse_args()

    train_residual_rl_with_curriculum(
        total_timesteps=args.total_timesteps,
        n_envs=args.n_envs,
        learning_rate=args.learning_rate,
        residual_limit=args.residual_limit,
        inner_steps=args.inner_steps,
        log_dir=args.log_dir,
        model_save_path=args.model_save_path,
        use_subproc=not args.no_subproc,
    )


if __name__ == "__main__":
    main()

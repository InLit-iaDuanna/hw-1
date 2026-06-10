"""训练sanity check：100k步训练，每25k评估一次。

目标：
1. 运行100k步PPO训练
2. 每25k评估10个episodes
3. 验证最终performance > baseline + 2σ
4. 验证failure_rate = 0

验收标准：
- Final distance > baseline + 2σ (即 > 4.63 + 0.2 = 4.83m)
- Final failure rate = 0% (所有episodes都完成)
- 训练过程中reward曲线上升
"""

from __future__ import annotations

import sys
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import BaseCallback

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


@dataclass
class EvalResult:
    """评估结果"""
    timestep: int
    avg_distance: float
    std_distance: float
    avg_reward: float
    success_rate: float
    failure_rate: float
    distances: List[float]


class EvalCallbackV2(BaseCallback):
    """自定义评估回调"""

    def __init__(self, eval_freq: int, n_eval_episodes: int, verbose: int = 1):
        super().__init__(verbose)
        self.eval_freq = eval_freq
        self.n_eval_episodes = n_eval_episodes
        self.eval_results: List[EvalResult] = []

    def _on_step(self) -> bool:
        if self.n_calls % self.eval_freq == 0:
            # 评估
            result = self.evaluate()
            self.eval_results.append(result)

            if self.verbose > 0:
                print()
                print("=" * 80)
                print(f"Evaluation at timestep {result.timestep}")
                print("=" * 80)
                print(f"  Average distance: {result.avg_distance:.3f} +/- {result.std_distance:.3f} m")
                print(f"  Average reward: {result.avg_reward:.1f}")
                print(f"  Success rate: {result.success_rate * 100:.0f}%")
                print(f"  Failure rate: {result.failure_rate * 100:.0f}%")
                print(f"  Baseline: 4.63m")
                print(f"  Improvement: {result.avg_distance - 4.63:+.3f}m ({(result.avg_distance / 4.63 - 1) * 100:+.1f}%)")
                print("=" * 80)
                print()

        return True

    def evaluate(self) -> EvalResult:
        """运行评估"""
        # 创建临时评估环境
        eval_env = ResidualRLEnvV2(
            residual_scale=0.05,
            inner_steps=5,
            max_steps=500,
        )

        distances = []
        rewards = []
        successes = []
        failures = []

        for ep in range(self.n_eval_episodes):
            obs, info = eval_env.reset(seed=ep)

            terminated = False
            truncated = False
            total_reward = 0.0

            while not (terminated or truncated):
                # 使用当前策略预测action
                action, _states = self.model.predict(obs, deterministic=True)

                obs, reward, terminated, truncated, info = eval_env.step(action)
                total_reward += reward

            distance = info["episode_distance"]
            success = truncated and not terminated
            failure = terminated

            distances.append(distance)
            rewards.append(total_reward)
            successes.append(success)
            failures.append(failure)

        eval_env.close()

        # 统计
        avg_distance = np.mean(distances)
        std_distance = np.std(distances)
        avg_reward = np.mean(rewards)
        success_rate = sum(successes) / len(successes)
        failure_rate = sum(failures) / len(failures)

        return EvalResult(
            timestep=self.num_timesteps,
            avg_distance=avg_distance,
            std_distance=std_distance,
            avg_reward=avg_reward,
            success_rate=success_rate,
            failure_rate=failure_rate,
            distances=distances,
        )


def train_v2_sanity(
    total_timesteps: int = 100000,
    eval_freq: int = 25000,
    n_eval_episodes: int = 10,
) -> Dict[str, Any]:
    """运行100k训练sanity check。

    Args:
        total_timesteps: 总训练步数
        eval_freq: 评估频率
        n_eval_episodes: 每次评估的episode数

    Returns:
        训练结果字典
    """
    print("=" * 80)
    print("Train V2 Sanity Check")
    print("=" * 80)
    print(f"Total timesteps: {total_timesteps}")
    print(f"Eval frequency: {eval_freq}")
    print(f"Eval episodes: {n_eval_episodes}")
    print()
    print("Acceptance criteria:")
    print("  - Final distance > baseline + 2σ (> 4.83m)")
    print("  - Final failure rate = 0%")
    print("=" * 80)
    print()

    # 创建环境
    def make_env():
        return ResidualRLEnvV2(
            residual_scale=0.05,
            inner_steps=5,
            max_steps=500,
        )

    env = DummyVecEnv([make_env])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # 创建PPO模型
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=str(HW1_ROOT / "rl_training" / "logs" / "residual_rl_v2_sanity" / "tensorboard"),
    )

    # 创建评估回调
    eval_callback = EvalCallbackV2(
        eval_freq=eval_freq,
        n_eval_episodes=n_eval_episodes,
        verbose=1,
    )

    # 训练
    print("Starting training...")
    print()
    model.learn(
        total_timesteps=total_timesteps,
        callback=eval_callback,
        progress_bar=True,
    )

    # 最终评估
    print()
    print("=" * 80)
    print("FINAL EVALUATION")
    print("=" * 80)

    final_result = eval_callback.eval_results[-1] if len(eval_callback.eval_results) > 0 else None

    if final_result is None:
        print("[ERROR] No evaluation results available")
        return {"diagnosis": "ERROR", "error": "No evaluation results"}

    print(f"Final average distance: {final_result.avg_distance:.3f} +/- {final_result.std_distance:.3f} m")
    print(f"Final average reward: {final_result.avg_reward:.1f}")
    print(f"Final success rate: {final_result.success_rate * 100:.0f}%")
    print(f"Final failure rate: {final_result.failure_rate * 100:.0f}%")
    print()

    # 诊断
    print("=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    baseline_distance = 4.63
    baseline_sigma = 0.1
    threshold = baseline_distance + 2 * baseline_sigma  # 4.83m

    pass_distance = final_result.avg_distance > threshold
    pass_failure = final_result.failure_rate == 0.0

    if pass_distance and pass_failure:
        print("[PASS] Sanity check passed!")
        print(f"  - Final distance {final_result.avg_distance:.3f}m > threshold {threshold:.3f}m")
        print(f"  - Failure rate {final_result.failure_rate * 100:.0f}% = 0%")
        print()
        print("Conclusion: PPO successfully learns to improve over baseline.")
        print("Recommendation: Ready for longer training runs.")
        diagnosis = "PASS"
    else:
        print("[FAIL] Sanity check failed")
        if not pass_distance:
            print(f"  - Final distance {final_result.avg_distance:.3f}m <= threshold {threshold:.3f}m")
        if not pass_failure:
            print(f"  - Failure rate {final_result.failure_rate * 100:.0f}% > 0%")
        print()
        print("Possible causes:")
        print("  1. Learning rate may be too high or too low")
        print("  2. Reward shaping may need adjustment")
        print("  3. Observation normalization may be incorrect")
        print("  4. residual_scale may be too small")
        diagnosis = "FAIL"

    print()

    # 训练曲线分析
    print("Training progression:")
    print("-" * 80)
    for result in eval_callback.eval_results:
        improvement = result.avg_distance - baseline_distance
        print(
            f"  Timestep {result.timestep:6d}: "
            f"distance={result.avg_distance:.3f}m, "
            f"improvement={improvement:+.3f}m, "
            f"failure={result.failure_rate * 100:.0f}%"
        )
    print()

    # 保存结果
    summary = {
        "diagnosis": diagnosis,
        "total_timesteps": total_timesteps,
        "baseline_distance": baseline_distance,
        "threshold": threshold,
        "final_result": asdict(final_result),
        "eval_history": [asdict(r) for r in eval_callback.eval_results],
    }

    # 保存模型
    model_path = HW1_ROOT / "rl_training" / "models" / "residual_rl_v2_sanity"
    model_path.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path / "final_model"))
    env.save(str(model_path / "vec_normalize.pkl"))
    print(f"Model saved to: {model_path}")
    print()

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train V2 sanity check")
    parser.add_argument("--timesteps", type=int, default=100000, help="Total training timesteps")
    parser.add_argument("--eval-freq", type=int, default=25000, help="Evaluation frequency")
    parser.add_argument("--eval-episodes", type=int, default=10, help="Number of eval episodes")
    parser.add_argument("--save", type=str, default="train_v2_sanity_report.json",
                        help="Save path for results")

    args = parser.parse_args()

    # 运行训练
    summary = train_v2_sanity(
        total_timesteps=args.timesteps,
        eval_freq=args.eval_freq,
        n_eval_episodes=args.eval_episodes,
    )

    # 保存结果
    save_path = HW1_ROOT / "rl_training" / args.save
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Results saved to: {save_path}")
    print()

    # 返回退出码
    exit_code = 0 if summary["diagnosis"] == "PASS" else 1
    return exit_code


if __name__ == "__main__":
    exit(main())

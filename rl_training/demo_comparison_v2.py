"""正确的对比演示：Constant vs 100k RL

使用与训练时相同的配置（ResidualPriorWrapper）
"""

import sys
import time
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2


class ResidualPriorWrapper(gym.ActionWrapper):
    """Map PPO delta actions to residual actions near a known good prior."""

    def __init__(
        self,
        env: gym.Env,
        prior_action: np.ndarray,
        delta_scale: float,
    ):
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


def run_constant_residual(episodes=5):
    """运行 Constant Residual（直接输入到环境）"""
    print("=" * 80)
    print("方案 A: Constant Residual [0.5, 1.0] (直接模式)")
    print("=" * 80)

    # 配置与训练时相同
    residual_scale = 0.2
    inner_steps = 5
    max_steps = 2400

    # Constant action 直接作用于环境
    constant_action = np.array([0.5, 1.0], dtype=np.float32)

    distances = []
    successes = []

    for ep in range(episodes):
        env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )

        obs, info = env.reset(seed=ep)
        done = False
        step = 0
        start_time = time.time()

        while not done and step < max_steps:
            obs, reward, terminated, truncated, info = env.step(constant_action)
            done = terminated or truncated
            step += 1

        elapsed = time.time() - start_time

        final_distance = float(env.data.qpos[0])
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        status = "SUCCESS" if success else "FAIL"
        print(
            f"  Episode {ep+1}: {final_distance:.3f}m [{status}] (耗时: {elapsed:.2f}s, {step} steps)"
        )

        env.close()

    mean_dist = np.mean(distances)
    std_dist = np.std(distances)
    success_rate = np.mean(successes)

    print()
    print("结果汇总:")
    print(f"  平均距离: {mean_dist:.3f} ± {std_dist:.3f} m")
    print(f"  成功率: {success_rate*100:.0f}%")
    print(f"  行走速度: ~{mean_dist/12:.3f} m/s")
    print()

    return {
        "mean_distance": mean_dist,
        "std_distance": std_dist,
        "success_rate": success_rate,
        "distances": distances,
    }


def run_rl_policy(episodes=5):
    """运行 100k PPO RL 策略（使用 wrapper）"""
    print("=" * 80)
    print("方案 B: 100k PPO 深度强化学习策略 (Prior-guided)")
    print("=" * 80)

    # 配置与训练时相同
    residual_scale = 0.2
    inner_steps = 5
    max_steps = 2400
    prior_action = np.array([0.5, 1.0], dtype=np.float32)
    delta_scale = 0.3

    # 加载模型
    model_path = (
        HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"
    )

    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {model_path}")
        return None

    print(f"加载模型: {model_path}")
    model = PPO.load(str(model_path))
    print("模型加载成功")
    print()

    distances = []
    successes = []
    actual_actions_all = []

    for ep in range(episodes):
        base_env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )
        env = ResidualPriorWrapper(
            base_env, prior_action=prior_action, delta_scale=delta_scale
        )

        obs, info = env.reset(seed=ep)
        done = False
        step = 0
        start_time = time.time()

        actual_actions_ep = []

        while not done and step < max_steps:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            actual_actions_ep.append(env.last_actual_action.copy())
            done = terminated or truncated
            step += 1

        elapsed = time.time() - start_time

        final_distance = float(base_env.data.qpos[0])
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)
        actual_actions_all.extend(actual_actions_ep)

        status = "SUCCESS" if success else "FAIL"
        print(
            f"  Episode {ep+1}: {final_distance:.3f}m [{status}] (耗时: {elapsed:.2f}s, {step} steps)"
        )

        env.close()

    mean_dist = np.mean(distances)
    std_dist = np.std(distances)
    success_rate = np.mean(successes)

    # 统计实际 action
    actual_actions_arr = np.array(actual_actions_all)
    mean_action = actual_actions_arr.mean(axis=0)
    std_action = actual_actions_arr.std(axis=0)

    print()
    print("结果汇总:")
    print(f"  平均距离: {mean_dist:.3f} ± {std_dist:.3f} m")
    print(f"  成功率: {success_rate*100:.0f}%")
    print(f"  行走速度: ~{mean_dist/12:.3f} m/s")
    print(f"  平均 action: [{mean_action[0]:.3f}, {mean_action[1]:.3f}]")
    print(f"  Action std: [{std_action[0]:.3f}, {std_action[1]:.3f}]")
    print()

    return {
        "mean_distance": mean_dist,
        "std_distance": std_dist,
        "success_rate": success_rate,
        "distances": distances,
        "mean_action": mean_action.tolist(),
        "std_action": std_action.tolist(),
    }


def print_comparison(constant_result, rl_result):
    """打印对比分析"""
    print("=" * 80)
    print("对比分析")
    print("=" * 80)
    print()

    print(f"{'指标':<25} {'Constant':<20} {'100k RL':<20} {'差异':<20}")
    print("-" * 85)

    # 距离对比
    const_dist = constant_result["mean_distance"]
    rl_dist = rl_result["mean_distance"]
    diff_dist = rl_dist - const_dist
    pct_dist = (diff_dist / const_dist) * 100 if const_dist > 0 else 0

    print(
        f"{'平均距离 (m)':<25} {const_dist:<20.3f} {rl_dist:<20.3f} {diff_dist:+.3f} ({pct_dist:+.1f}%)"
    )

    # 成功率对比
    const_success = constant_result["success_rate"]
    rl_success = rl_result["success_rate"]

    print(f"{'成功率':<25} {const_success*100:<20.0f}% {rl_success*100:<20.0f}%")

    # 稳定性对比
    const_std = constant_result["std_distance"]
    rl_std = rl_result["std_distance"]

    print(f"{'标准差 (m)':<25} {const_std:<20.3f} {rl_std:<20.3f}")

    # Action 对比
    if "mean_action" in rl_result:
        rl_action = rl_result["mean_action"]
        print(
            f"{'Action (平均值)':<25} [0.500, 1.000]      [{rl_action[0]:.3f}, {rl_action[1]:.3f}]"
        )

    print()
    print("结论:")

    if const_success > 0 and rl_success > 0:
        if rl_dist > const_dist:
            print(f"  [+] PPO RL 优于 Constant，提升 {pct_dist:.1f}%")
        elif abs(diff_dist) < 0.1:
            print("  [=] 两者性能相当（差异 < 0.1m）")
        else:
            print(f"  [-] Constant 优于 PPO RL，领先 {-pct_dist:.1f}%")
    elif rl_success == 0:
        print("  [-] PPO RL 完全失败")
    elif const_success == 0:
        print("  [-] Constant 完全失败")

    if const_success == 1.0 and rl_success == 1.0:
        print("  [+] 两种方案都达到 100% 成功率，都是可用的策略")
    elif rl_success == 1.0:
        print("  [+] PPO RL 达到 100% 成功率")
    elif const_success == 1.0:
        print("  [+] Constant 达到 100% 成功率")

    if rl_std < const_std:
        print(f"  [+] PPO RL 更稳定（标准差 {rl_std:.3f}m < {const_std:.3f}m）")
    elif abs(rl_std - const_std) < 0.001:
        print("  [=] 两者稳定性相当")
    else:
        print(f"  [+] Constant 更稳定（标准差 {const_std:.3f}m < {rl_std:.3f}m）")

    print()
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="对比 Constant vs 100k RL 策略")
    parser.add_argument(
        "--episodes", type=int, default=10, help="每个方案运行的 episode 数"
    )
    parser.add_argument("--only-constant", action="store_true", help="只运行 Constant")
    parser.add_argument("--only-rl", action="store_true", help="只运行 RL")

    args = parser.parse_args()

    print()
    print("=" * 80)
    print("ResidualRL V2 行走策略对比演示（正确配置版）")
    print("=" * 80)
    print(f"每个方案运行 {args.episodes} 个 episodes，每个 episode 12 秒")
    print("配置: residual_scale=0.2, inner_steps=5, prior=[0.5, 1.0]")
    print()

    constant_result = None
    rl_result = None

    if not args.only_rl:
        constant_result = run_constant_residual(episodes=args.episodes)

    if not args.only_constant:
        rl_result = run_rl_policy(episodes=args.episodes)

    if constant_result and rl_result:
        print_comparison(constant_result, rl_result)

    print()
    print("演示完成！")
    print()
    print("推荐使用场景:")
    print("  1. 如果想展示深度学习成果 -> 使用 100k RL")
    print("  2. 如果追求最简单实现 -> 使用 Constant")
    print("  3. 两者性能接近，都是可用的方案")
    print()


if __name__ == "__main__":
    main()

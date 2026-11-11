"""演示对比：100k PPO RL vs Constant Residual

展示两种方案的行走效果和性能对比。
"""

import sys
import time
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2


def run_constant_residual(episodes=5, render=False):
    """运行 Constant Residual 方案"""
    print("=" * 80)
    print("方案 A: Constant Residual [0.5, 1.0]")
    print("=" * 80)

    env = ResidualRLEnvV2(
        max_steps=2400, render_mode="human" if render else None  # 12秒
    )

    constant_action = np.array([0.5, 1.0], dtype=np.float32)

    distances = []
    successes = []

    for ep in range(episodes):
        obs, info = env.reset()
        done = False
        step = 0

        start_time = time.time()

        while not done and step < 2400:
            obs, reward, terminated, truncated, info = env.step(constant_action)
            done = terminated or truncated
            step += 1

        elapsed = time.time() - start_time

        final_distance = float(info.get("episode_distance", env.data.qpos[0]))
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        status = "SUCCESS" if success else "FAIL"
        print(
            f"  Episode {ep+1}: {final_distance:.3f}m [{status}] (耗时: {elapsed:.2f}s)"
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


def run_rl_policy(episodes=5, render=False):
    """运行 100k PPO RL 策略"""
    print("=" * 80)
    print("方案 B: 100k PPO 深度强化学习策略")
    print("=" * 80)

    # 加载模型
    model_path = (
        HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"
    )

    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {model_path}")
        print("请先运行训练或使用其他 checkpoint")
        return None

    print(f"加载模型: {model_path}")
    model = PPO.load(str(model_path))
    print("模型加载成功")
    print()

    env = ResidualRLEnvV2(
        max_steps=2400, render_mode="human" if render else None  # 12秒
    )

    distances = []
    successes = []

    for ep in range(episodes):
        obs, info = env.reset()
        done = False
        step = 0

        start_time = time.time()

        while not done and step < 2400:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            step += 1

        elapsed = time.time() - start_time

        final_distance = float(info.get("episode_distance", env.data.qpos[0]))
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        status = "SUCCESS" if success else "FAIL"
        print(
            f"  Episode {ep+1}: {final_distance:.3f}m [{status}] (耗时: {elapsed:.2f}s)"
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


def print_comparison(constant_result, rl_result):
    """打印对比分析"""
    print("=" * 80)
    print("对比分析")
    print("=" * 80)
    print()

    print(f"{'指标':<20} {'Constant':<20} {'100k RL':<20} {'差异':<20}")
    print("-" * 80)

    # 距离对比
    const_dist = constant_result["mean_distance"]
    rl_dist = rl_result["mean_distance"]
    diff_dist = rl_dist - const_dist
    pct_dist = (diff_dist / const_dist) * 100

    print(
        f"{'平均距离 (m)':<20} {const_dist:<20.3f} {rl_dist:<20.3f} {diff_dist:+.3f} ({pct_dist:+.1f}%)"
    )

    # 成功率对比
    const_success = constant_result["success_rate"]
    rl_success = rl_result["success_rate"]

    print(f"{'成功率':<20} {const_success*100:<20.0f}% {rl_success*100:<20.0f}%")

    # 稳定性对比
    const_std = constant_result["std_distance"]
    rl_std = rl_result["std_distance"]

    print(f"{'标准差 (m)':<20} {const_std:<20.3f} {rl_std:<20.3f}")

    print()
    print("结论:")
    if rl_dist > const_dist:
        print(f"  [+] PPO RL 优于 Constant，提升 {pct_dist:.1f}%")
    else:
        print(f"  [-] Constant 优于 PPO RL，领先 {-pct_dist:.1f}%")

    if const_success == 1.0 and rl_success == 1.0:
        print("  [+] 两种方案都达到 100% 成功率")
    elif rl_success == 1.0:
        print("  [+] PPO RL 达到 100% 成功率")
    elif const_success == 1.0:
        print("  [+] Constant 达到 100% 成功率")

    if rl_std < const_std:
        print("  [+] PPO RL 更稳定（标准差更小）")
    else:
        print("  [-] Constant 更稳定（标准差更小）")

    print()
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="对比 Constant vs 100k RL 策略")
    parser.add_argument(
        "--episodes", type=int, default=5, help="每个方案运行的 episode 数"
    )
    parser.add_argument("--render", action="store_true", help="是否渲染可视化")
    parser.add_argument("--only-constant", action="store_true", help="只运行 Constant")
    parser.add_argument("--only-rl", action="store_true", help="只运行 RL")

    args = parser.parse_args()

    print()
    print("=" * 80)
    print("ResidualRL V2 行走策略对比演示")
    print("=" * 80)
    print(f"每个方案运行 {args.episodes} 个 episodes，每个 episode 12 秒")
    print()

    constant_result = None
    rl_result = None

    if not args.only_rl:
        constant_result = run_constant_residual(
            episodes=args.episodes, render=args.render
        )

    if not args.only_constant:
        rl_result = run_rl_policy(episodes=args.episodes, render=args.render)

    if constant_result and rl_result:
        print_comparison(constant_result, rl_result)

    print()
    print("演示完成！")
    print()
    print("使用说明:")
    print("  --episodes N      # 每个方案运行 N 个 episodes（默认 5）")
    print("  --render          # 打开可视化窗口（会变慢）")
    print("  --only-constant   # 只测试 Constant 方案")
    print("  --only-rl         # 只测试 RL 方案")
    print()


if __name__ == "__main__":
    main()

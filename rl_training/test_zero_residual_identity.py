"""Zero Residual Identity Test - 验证Residual RL环境的基线一致性。

目标：在ResidualRLEnv中设置residual=0，验证能否复现V13.7的1.05m±0.012m基线性能。
如果不能，则说明环境实现有差异，需要诊断并修复。

运行方式：
    cd D:\\Dunna\\Documents\\hw-1
    .venv-mujoco\\Scripts\activate
    python rl_training\test_zero_residual_identity.py
"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl import ResidualRLEnv


def run_zero_residual_episode(env, seed: int, verbose: bool = False):
    """运行一个零residual的episode。

    Args:
        env: ResidualRLEnv实例
        seed: 随机种子
        verbose: 是否打印详细信息

    Returns:
        final_distance: 最终前进距离 (m)
        episode_length: episode长度 (steps)
        sim_time: 仿真时间 (s)
        terminated: 是否因摔倒终止
    """
    obs, info = env.reset(seed=seed)

    episode_length = 0
    total_reward = 0.0
    zero_action = np.zeros(4, dtype=np.float32)

    while True:
        obs, reward, terminated, truncated, info = env.step(zero_action)
        total_reward += reward
        episode_length += 1

        if verbose and episode_length % 50 == 0:
            print(
                f"    Step {episode_length}: hip_x={info['hip_x']:.3f}m, "
                f"hip_vel_x={info['hip_vel_x']:.3f}m/s, height={info['hip_height']:.3f}m"
            )

        if terminated or truncated:
            break

    return info["hip_x"], episode_length, info["sim_time"], terminated


def test_zero_residual_identity(n_episodes: int = 20):
    """Zero Residual Identity Test主函数。

    Args:
        n_episodes: 测试的episode数量
    """
    print("=" * 80)
    print("Zero Residual Identity Test")
    print("=" * 80)
    print("\n目标: 在residual=0条件下复现V13.7基线性能 (1.05m±0.012m)")
    print(f"测试episodes: {n_episodes}")
    print("\n创建环境...")

    # 创建环境（使用200Hz配置，与ABLATION_SUMMARY.md一致）
    env = ResidualRLEnv(
        residual_limit=0.5,
        inner_steps=5,  # 200Hz PPO频率
        max_steps=500,
        reward_type="forward_velocity",
    )

    print(f"  PPO频率: {1000 / env.inner_steps:.0f} Hz")
    print(
        f"  最大episode长度: {env.max_steps} PPO steps = {env.max_steps * env.inner_steps / 1000:.1f}s"
    )

    # 运行测试
    print(f"\n运行{n_episodes}个episodes（residual=0）...\n")

    distances = []
    success_count = 0

    for i in range(n_episodes):
        seed = 1000 + i
        distance, ep_len, sim_time, terminated = run_zero_residual_episode(
            env, seed, verbose=(i < 3)  # 前3个打印详细信息
        )

        distances.append(distance)
        if not terminated:
            success_count += 1

        status = "摔倒" if terminated else "完成"
        print(
            f"  Episode {i+1:2d} (seed={seed}): {distance:.4f}m | {ep_len:3d} steps | "
            f"{sim_time:.2f}s | {status}"
        )

    env.close()

    # 统计分析
    distances = np.array(distances)
    mean_dist = np.mean(distances)
    std_dist = np.std(distances)
    min_dist = np.min(distances)
    max_dist = np.max(distances)
    success_rate = success_count / n_episodes * 100

    print("\n" + "=" * 80)
    print("统计结果")
    print("=" * 80)
    print("前进距离:")
    print(f"  Mean:    {mean_dist:.4f}m")
    print(f"  Std:     {std_dist:.4f}m")
    print(f"  Min:     {min_dist:.4f}m")
    print(f"  Max:     {max_dist:.4f}m")
    print(f"  Range:   [{mean_dist - std_dist:.4f}m, {mean_dist + std_dist:.4f}m]")
    print(f"\n成功率: {success_rate:.1f}% ({success_count}/{n_episodes})")

    # 与基线对比
    baseline_mean = 1.05
    baseline_std = 0.012

    print("\n" + "=" * 80)
    print("基线对比 (V13.7 @ 200Hz)")
    print("=" * 80)
    print(f"期望:    {baseline_mean:.4f}m ± {baseline_std:.4f}m")
    print(f"实际:    {mean_dist:.4f}m ± {std_dist:.4f}m")
    print(
        f"差异:    {mean_dist - baseline_mean:+.4f}m ({(mean_dist/baseline_mean - 1)*100:+.1f}%)"
    )

    # 判定
    tolerance = 0.05  # 5%容差
    mean_diff_pct = abs(mean_dist - baseline_mean) / baseline_mean

    print("\n" + "=" * 80)
    if mean_diff_pct < tolerance:
        print("[PASS] Zero Residual Identity Test passed!")
        print("  Environment correctly reproduces V13.7 baseline at residual=0")
        print(
            f"  Error within {tolerance*100:.0f}% tolerance ({mean_diff_pct*100:.2f}%)"
        )
        print("\nReady to start Residual RL training.")
    else:
        print("[FAIL] Zero Residual Identity Test failed!")
        print(
            f"  Environment output ({mean_dist:.4f}m) differs too much from baseline ({baseline_mean:.4f}m)"
        )
        print(
            f"  Error {mean_diff_pct*100:.2f}% exceeds {tolerance*100:.0f}% tolerance"
        )
        print("\nDiagnosis needed:")
        print("  1. Check V13.7 controller integration")
        print("  2. Check FSM state update logic")
        print("  3. Check initialization conditions")
        print("  4. Check simulation timestep and control frequency")
    print("=" * 80)

    return mean_dist, std_dist, success_rate


if __name__ == "__main__":
    test_zero_residual_identity(n_episodes=20)

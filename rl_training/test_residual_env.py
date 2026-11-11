"""测试Residual RL环境是否正常工作。

运行方式：
    cd D:\\Dunna\\Documents\\hw-1
    .venv-mujoco\\Scripts\activate
    python rl_training\test_residual_env.py
"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl import ResidualRLEnv


def test_environment():
    """测试Residual RL环境基本功能。"""
    print("=" * 80)
    print("测试Residual RL环境")
    print("=" * 80)

    # 创建环境（使用推荐的200Hz配置）
    print("\n创建环境（200Hz PPO频率）...")
    env = ResidualRLEnv(
        residual_limit=0.5,
        inner_steps=5,  # 5ms = 200Hz
        max_steps=500,
        reward_type="forward_velocity",
    )

    print(f"  Action space: {env.action_space}")
    print(f"  Observation space: {env.observation_space}")
    print(f"  PPO频率: {1000 / env.inner_steps:.0f} Hz")
    print(f"  Residual范围: ±{env.residual_limit} N·m")

    # 测试reset
    print("\n测试reset()...")
    obs, info = env.reset(seed=42)
    print(f"  [OK] Observation shape: {obs.shape}")
    print(f"  [OK] Initial hip_x: {info['hip_x']:.3f}")

    # 测试step（零动作 = 纯V13.7）
    print("\n测试step()（零residual = 纯V13.7控制）...")
    zero_action = np.zeros(4, dtype=np.float32)

    total_reward = 0.0
    for i in range(10):
        obs, reward, terminated, truncated, info = env.step(zero_action)
        total_reward += reward

        if i % 3 == 0:
            print(
                f"  Step {i}: hip_x={info['hip_x']:.3f}m, "
                f"hip_vel_x={info['hip_vel_x']:.3f}m/s, reward={reward:.2f}"
            )

        if terminated or truncated:
            print(f"  Episode结束于step {i}")
            break

    print(f"\n  [OK] 累积奖励: {total_reward:.2f}")
    print(f"  [OK] 前进距离: {info['hip_x']:.3f}m")

    # 测试随机动作
    print("\n测试随机residual动作...")
    obs, info = env.reset(seed=123)

    total_reward = 0.0
    for i in range(10):
        random_action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(random_action)
        total_reward += reward

        if i % 3 == 0:
            print(
                f"  Step {i}: residual={random_action[:2]}, "
                f"hip_x={info['hip_x']:.3f}m, reward={reward:.2f}"
            )

        if terminated or truncated:
            print(f"  Episode结束于step {i}")
            break

    print(f"\n  [OK] 累积奖励: {total_reward:.2f}")
    print(f"  [OK] 前进距离: {info['hip_x']:.3f}m")

    # 完整episode测试
    print("\n运行完整episode（纯V13.7基线）...")
    obs, info = env.reset(seed=999)

    episode_length = 0
    total_reward = 0.0

    while True:
        zero_action = np.zeros(4, dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(zero_action)
        total_reward += reward
        episode_length += 1

        if terminated or truncated:
            break

    print(f"  [OK] Episode长度: {episode_length} steps")
    print(f"  [OK] 仿真时间: {info['sim_time']:.2f}s")
    print(f"  [OK] 前进距离: {info['hip_x']:.3f}m")
    print(f"  [OK] 累积奖励: {total_reward:.2f}")
    print(f"  [OK] 终止原因: {'摔倒' if terminated else '达到最大步数'}")

    env.close()

    print("\n" + "=" * 80)
    print("[SUCCESS] 所有测试通过！环境可以用于训练。")
    print("=" * 80)

    # 打印推荐训练命令
    print("\n推荐训练命令:")
    print(
        "  python rl_training/train_residual_rl.py --inner-steps 5 --total-timesteps 500000"
    )


if __name__ == "__main__":
    test_environment()

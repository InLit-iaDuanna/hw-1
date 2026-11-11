"""无可视化演示：展示 RL 策略的实际性能

使用与训练完全相同的环境配置，输出详细的行走数据
"""

import sys
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2


class ResidualPriorWrapper(gym.ActionWrapper):
    """与训练时相同的 wrapper"""

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


def demo_rl_with_wrapper():
    """使用与训练完全相同的配置演示 RL"""
    print("=" * 80)
    print("100k PPO 深度强化学习策略演示（完整版）")
    print("=" * 80)
    print()

    # 加载模型
    model_path = (
        HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"
    )

    if not model_path.exists():
        print("错误：模型文件不存在")
        return

    print("正在加载 PPO 模型...")
    model = PPO.load(str(model_path))
    print("[OK] 模型加载成功")
    print()

    # 配置（与训练完全相同）
    residual_scale = 0.2
    inner_steps = 5
    max_steps = 2400
    prior_action = np.array([0.5, 1.0], dtype=np.float32)
    delta_scale = 0.3

    print("配置参数:")
    print(f"  residual_scale: {residual_scale}")
    print(f"  inner_steps: {inner_steps} (PPO 频率: 200Hz)")
    print(f"  prior_action: {prior_action}")
    print(f"  delta_scale: {delta_scale}")
    print()

    # 运行多个 episodes
    print("=" * 80)
    print("开始演示（5 个 episodes）")
    print("=" * 80)
    print()

    distances = []
    successes = []

    for ep in range(5):
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

        action_history = []
        distance_history = []

        while not done and step < max_steps:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            action_history.append(env.last_actual_action.copy())
            distance_history.append(float(base_env.data.qpos[0]))

            step += 1

            # 每 1 秒打印一次
            if step % 200 == 0:
                t = step * 0.005
                distance = distance_history[-1]
                print(
                    f"  Episode {ep+1} | 时间: {t:5.2f}s | 距离: {distance:6.3f}m",
                    end="\r",
                )

        final_distance = distance_history[-1]
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        # 统计 action
        actions_arr = np.array(action_history)
        mean_action = actions_arr.mean(axis=0)
        std_action = actions_arr.std(axis=0)

        status = "成功" if success else "失败"
        print(
            f"  Episode {ep+1} | 最终距离: {final_distance:6.3f}m | 状态: {status:4s} | Action均值: [{mean_action[0]:.3f}, {mean_action[1]:.3f}]"
        )

        env.close()

    print()
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)
    print()

    mean_dist = np.mean(distances)
    std_dist = np.std(distances)
    success_rate = np.mean(successes)

    print("统计结果:")
    print(f"  平均距离: {mean_dist:.3f} ± {std_dist:.3f} m")
    print(f"  成功率: {success_rate*100:.0f}%")
    print(f"  行走速度: ~{mean_dist/12:.3f} m/s")
    print()

    if success_rate == 1.0:
        print("所有 episodes 都成功完成！")
        print(
            f"相比 V13.7 baseline (4.63m)，提升了 {(mean_dist - 4.63) / 4.63 * 100:.1f}%"
        )
    else:
        print(f"注意：有 {int((1-success_rate)*5)} 个 episodes 失败")

    print("=" * 80)


def demo_constant():
    """演示 Constant Residual"""
    print("=" * 80)
    print("Constant Residual [0.5, 1.0] 演示")
    print("=" * 80)
    print()

    residual_scale = 0.2
    inner_steps = 5
    max_steps = 2400
    constant_action = np.array([0.5, 1.0], dtype=np.float32)

    print("配置参数:")
    print(f"  residual_scale: {residual_scale}")
    print(f"  constant_action: {constant_action}")
    print()

    print("=" * 80)
    print("开始演示（5 个 episodes）")
    print("=" * 80)
    print()

    distances = []
    successes = []

    for ep in range(5):
        env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )

        obs, info = env.reset(seed=ep)
        done = False
        step = 0

        while not done and step < max_steps:
            obs, reward, terminated, truncated, info = env.step(constant_action)
            done = terminated or truncated
            step += 1

            if step % 200 == 0:
                t = step * 0.005
                distance = float(env.data.qpos[0])
                print(
                    f"  Episode {ep+1} | 时间: {t:5.2f}s | 距离: {distance:6.3f}m",
                    end="\r",
                )

        final_distance = float(env.data.qpos[0])
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        status = "成功" if success else "失败"
        print(
            f"  Episode {ep+1} | 最终距离: {final_distance:6.3f}m | 状态: {status:4s}"
        )

        env.close()

    print()
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)
    print()

    mean_dist = np.mean(distances)
    std_dist = np.std(distances)
    success_rate = np.mean(successes)

    print("统计结果:")
    print(f"  平均距离: {mean_dist:.3f} ± {std_dist:.3f} m")
    print(f"  成功率: {success_rate*100:.0f}%")
    print(f"  行走速度: ~{mean_dist/12:.3f} m/s")
    print()

    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="演示行走策略（无可视化）")
    parser.add_argument(
        "--mode", choices=["rl", "constant", "both"], default="both", help="演示模式"
    )

    args = parser.parse_args()

    if args.mode == "rl":
        demo_rl_with_wrapper()
    elif args.mode == "constant":
        demo_constant()
    elif args.mode == "both":
        demo_rl_with_wrapper()
        print("\n" * 3)
        demo_constant()

        print("\n" * 2)
        print("=" * 80)
        print("两种策略演示完成！")
        print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断演示")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback

        traceback.print_exc()

"""简化版可视化演示：直接使用训练环境

这个版本直接使用 ResidualRLEnvV2，保证与训练时完全一致
"""

import sys
from pathlib import Path
import numpy as np
from stable_baselines3 import PPO
import time

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2


def demo_rl_policy():
    """演示 100k RL 策略"""
    print("=" * 80)
    print("100k PPO 深度强化学习行走演示")
    print("=" * 80)
    print()

    # 加载模型
    model_path = HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"

    if not model_path.exists():
        print(f"错误：模型文件不存在")
        print(f"路径：{model_path}")
        return

    print("正在加载 PPO 模型...")
    model = PPO.load(str(model_path))
    print("[OK] 模型加载成功")
    print()

    # 创建环境（使用与训练完全相同的配置）
    print("正在创建仿真环境...")
    env = ResidualRLEnvV2(
        residual_scale=0.2,
        inner_steps=5,
        max_steps=2400,  # 12秒
        render_mode="human"  # 打开可视化
    )
    print("[OK] 环境创建成功")
    print()

    print("=" * 80)
    print("开始演示（可视化窗口将打开）")
    print("=" * 80)
    print("说明：")
    print("  - 机器人使用 PPO 深度强化学习策略控制")
    print("  - 只控制两个髋关节（左右各 1 个）")
    print("  - 其他关节由 V13.7 FSM 基础控制器管理")
    print("  - 预期行走距离：~5.1m（12秒）")
    print("  - 按 ESC 或关闭窗口提前退出")
    print("=" * 80)
    print()

    # 运行一个 episode
    obs, info = env.reset(seed=42)
    done = False
    step = 0

    start_time = time.time()
    last_print_time = start_time

    while not done and step < 2400:
        # PPO 预测 action
        action, _ = model.predict(obs, deterministic=True)

        # 环境步进
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        step += 1

        # 每 0.5 秒打印一次进度
        current_time = time.time()
        if current_time - last_print_time >= 0.5:
            t = step * 0.005  # step * dt * inner_steps
            distance = float(env.data.qpos[0])
            hip_height = float(env.data.qpos[2])
            print(f"时间: {t:5.2f}s | 距离: {distance:6.3f}m | 髋高: {hip_height:5.3f}m | Step: {step:4d}/2400", end="\r")
            last_print_time = current_time

    elapsed = time.time() - start_time

    print()  # 换行
    print()
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)

    final_distance = float(env.data.qpos[0])
    success = truncated and not terminated

    print(f"最终距离: {final_distance:.3f}m")
    print(f"运行时长: {elapsed:.2f}s (真实时间)")
    print(f"仿真时长: {step * 0.005:.2f}s")
    print(f"平均速度: {final_distance / (step * 0.005):.3f} m/s")
    print(f"状态: {'成功' if success else '失败'}")

    if success:
        print()
        print("PPO 策略成功完成 12 秒行走！")
        print(f"   相比 V13.7 baseline (4.63m)，提升了 {(final_distance - 4.63) / 4.63 * 100:.1f}%")

    print("=" * 80)

    env.close()


def demo_constant_policy():
    """演示 Constant Residual"""
    print("=" * 80)
    print("Constant Residual [0.5, 1.0] 行走演示")
    print("=" * 80)
    print()

    print("正在创建仿真环境...")
    env = ResidualRLEnvV2(
        residual_scale=0.2,
        inner_steps=5,
        max_steps=2400,
        render_mode="human"
    )
    print("✓ 环境创建成功")
    print()

    print("=" * 80)
    print("开始演示（可视化窗口将打开）")
    print("=" * 80)
    print("说明：")
    print("  - 使用固定的 constant residual")
    print("  - Action: [0.5, 1.0] (左髋, 右髋)")
    print("  - 预期行走距离：~5.14m（12秒）")
    print("=" * 80)
    print()

    constant_action = np.array([0.5, 1.0], dtype=np.float32)

    obs, info = env.reset(seed=42)
    done = False
    step = 0

    start_time = time.time()
    last_print_time = start_time

    while not done and step < 2400:
        obs, reward, terminated, truncated, info = env.step(constant_action)
        done = terminated or truncated
        step += 1

        current_time = time.time()
        if current_time - last_print_time >= 0.5:
            t = step * 0.005
            distance = float(env.data.qpos[0])
            hip_height = float(env.data.qpos[2])
            print(f"时间: {t:5.2f}s | 距离: {distance:6.3f}m | 髋高: {hip_height:5.3f}m | Step: {step:4d}/2400", end="\r")
            last_print_time = current_time

    elapsed = time.time() - start_time

    print()
    print()
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)

    final_distance = float(env.data.qpos[0])
    success = truncated and not terminated

    print(f"最终距离: {final_distance:.3f}m")
    print(f"运行时长: {elapsed:.2f}s (真实时间)")
    print(f"仿真时长: {step * 0.005:.2f}s")
    print(f"平均速度: {final_distance / (step * 0.005):.3f} m/s")
    print(f"状态: {'成功 ✓' if success else '失败 ✗'}")

    print("=" * 80)

    env.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="可视化演示行走策略")
    parser.add_argument("--mode", choices=["rl", "constant", "both"], default="rl",
                       help="演示模式: rl=100k RL策略, constant=固定策略, both=两者对比")

    args = parser.parse_args()

    if args.mode == "rl":
        demo_rl_policy()
    elif args.mode == "constant":
        demo_constant_policy()
    elif args.mode == "both":
        print("先演示 100k RL 策略...\n")
        demo_rl_policy()

        print("\n\n按回车继续演示 Constant 策略...")
        input()

        demo_constant_policy()

        print("\n\n两种策略演示完成！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断演示")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()

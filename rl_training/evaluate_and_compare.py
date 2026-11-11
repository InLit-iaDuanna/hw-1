"""
阶段4：对比评估

评估并对比3个模型的性能：
1. 纯BC模型
2. BC+PPO微调模型
3. 原始PPO模型（从零训练）
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from environment import CompassGaitEnv
from stable_baselines3 import PPO


class BCPolicyWrapper:
    """BC模型包装器（兼容SB3接口）"""

    def __init__(self, bc_weights_path: str, device: str = "auto"):
        from train_behavioral_cloning import MLPPolicy

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = torch.device(device)

        # 加载BC模型
        self.policy = MLPPolicy(obs_dim=20, action_dim=4, hidden_dim=128).to(
            self.device
        )

        checkpoint = torch.load(bc_weights_path, map_location=self.device)
        self.policy.load_state_dict(checkpoint["model_state_dict"])
        self.policy.eval()

        print(f"BC模型已加载 (device: {self.device})")

    def predict(self, obs: np.ndarray, deterministic: bool = True):
        """预测动作（兼容SB3接口）"""
        with torch.no_grad():
            obs_tensor = torch.from_numpy(obs).float().to(self.device)
            if len(obs_tensor.shape) == 1:
                obs_tensor = obs_tensor.unsqueeze(0)

            action = self.policy(obs_tensor).cpu().numpy()

            if len(action.shape) == 2 and action.shape[0] == 1:
                action = action[0]

            return action, None


def evaluate_model(
    model,
    model_name: str,
    num_episodes: int = 20,
    max_steps: int = 1000,
    render: bool = False,
) -> Dict:
    """
    评估单个模型

    Args:
        model: 模型实例（SB3 PPO或BCPolicyWrapper）
        model_name: 模型名称
        num_episodes: 评估的episode数
        max_steps: 每个episode的最大步数
        render: 是否渲染

    Returns:
        评估结果字典
    """
    print(f"评估模型: {model_name}")
    print("-" * 60)

    # 创建环境
    env = CompassGaitEnv(
        reward_type="energy_efficient",
        fall_height_threshold=0.2,
        max_steps=max_steps,
        frame_skip=20,
        render_mode="human" if render else None,
    )

    results = {"model_name": model_name, "episodes": [], "statistics": {}}

    for ep in range(num_episodes):
        obs, info = env.reset()
        total_reward = 0.0
        steps = 0
        terminated = False
        truncated = False

        start_x = info["hip_x"]

        for step in range(max_steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)

            total_reward += reward
            steps += 1

            if terminated or truncated:
                break

        # 记录结果
        episode_result = {
            "episode": ep,
            "total_reward": float(total_reward),
            "steps": steps,
            "forward_distance": float(info["hip_x"] - start_x),
            "final_hip_x": float(info["hip_x"]),
            "final_hip_height": float(info["hip_height"]),
            "final_hip_vel_x": float(info["hip_vel_x"]),
            "cumulative_energy": float(info["cumulative_energy"]),
            "terminated": terminated,
            "truncated": truncated,
            "success": not terminated and steps > 500,  # 简单成功标准
        }
        results["episodes"].append(episode_result)

        status = "[SUCCESS]" if episode_result["success"] else "[FAIL]"
        print(
            f"  Episode {ep + 1}/{num_episodes} {status} | "
            f"reward={total_reward:.2f} | "
            f"dist={episode_result['forward_distance']:.3f}m | "
            f"steps={steps}"
        )

    env.close()

    # 统计
    rewards = [ep["total_reward"] for ep in results["episodes"]]
    distances = [ep["forward_distance"] for ep in results["episodes"]]
    steps_list = [ep["steps"] for ep in results["episodes"]]
    successes = [ep["success"] for ep in results["episodes"]]
    energies = [ep["cumulative_energy"] for ep in results["episodes"]]

    results["statistics"] = {
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_distance": float(np.mean(distances)),
        "std_distance": float(np.std(distances)),
        "mean_steps": float(np.mean(steps_list)),
        "std_steps": float(np.std(steps_list)),
        "success_rate": float(np.mean(successes)),
        "mean_energy": float(np.mean(energies)),
        "std_energy": float(np.std(energies)),
    }

    print("\n统计结果:")
    print(
        f"  平均奖励: {results['statistics']['mean_reward']:.2f} ± {results['statistics']['std_reward']:.2f}"
    )
    print(
        f"  平均距离: {results['statistics']['mean_distance']:.3f} ± {results['statistics']['std_distance']:.3f} m"
    )
    print(
        f"  平均步数: {results['statistics']['mean_steps']:.1f} ± {results['statistics']['std_steps']:.1f}"
    )
    print(f"  成功率: {results['statistics']['success_rate'] * 100:.1f}%")
    print(
        f"  平均能量: {results['statistics']['mean_energy']:.2f} ± {results['statistics']['std_energy']:.2f}"
    )
    print()

    return results


def compare_models(
    bc_weights_path: str = "best_bc_policy_weights.pth",
    bc_ppo_model_path: str = "./models_bc_warmstart/ppo_bc_warmstart_final.zip",
    vanilla_ppo_model_path: str = "./models_fixed/ppo_gait_final.zip",
    num_episodes: int = 20,
    output_dir: str = "./evaluation_results",
):
    """
    对比评估多个模型

    Args:
        bc_weights_path: BC模型权重路径
        bc_ppo_model_path: BC+PPO模型路径
        vanilla_ppo_model_path: 原始PPO模型路径
        num_episodes: 每个模型评估的episode数
        output_dir: 结果输出目录
    """
    print("=" * 80)
    print("模型对比评估")
    print("=" * 80)
    print()

    RL_TRAINING_DIR = Path(__file__).resolve().parent
    os.makedirs(output_dir, exist_ok=True)

    all_results = []

    # 1. 评估纯BC模型
    print("\n[1/3] 评估纯BC模型")
    print("=" * 80)
    bc_path = RL_TRAINING_DIR / bc_weights_path
    if bc_path.exists():
        try:
            bc_model = BCPolicyWrapper(str(bc_path))
            bc_results = evaluate_model(bc_model, "BC (Imitation Only)", num_episodes)
            all_results.append(bc_results)
        except Exception as e:
            print(f"[ERROR] BC模型加载失败: {e}")
    else:
        print(f"[SKIP] BC模型不存在: {bc_path}")

    # 2. 评估BC+PPO模型
    print("\n[2/3] 评估BC+PPO微调模型")
    print("=" * 80)
    bc_ppo_path = Path(bc_ppo_model_path)
    if bc_ppo_path.exists():
        try:
            bc_ppo_model = PPO.load(str(bc_ppo_path))
            bc_ppo_results = evaluate_model(
                bc_ppo_model, "BC + PPO (Warm-Start)", num_episodes
            )
            all_results.append(bc_ppo_results)
        except Exception as e:
            print(f"[ERROR] BC+PPO模型加载失败: {e}")
    else:
        print(f"[SKIP] BC+PPO模型不存在: {bc_ppo_path}")

    # 3. 评估原始PPO模型
    print("\n[3/3] 评估原始PPO模型")
    print("=" * 80)
    vanilla_ppo_path = Path(vanilla_ppo_model_path)
    if vanilla_ppo_path.exists():
        try:
            vanilla_ppo_model = PPO.load(str(vanilla_ppo_path))
            vanilla_results = evaluate_model(
                vanilla_ppo_model, "PPO (From Scratch)", num_episodes
            )
            all_results.append(vanilla_results)
        except Exception as e:
            print(f"[ERROR] 原始PPO模型加载失败: {e}")
    else:
        print(f"[SKIP] 原始PPO模型不存在: {vanilla_ppo_path}")

    if not all_results:
        print("\n[ERROR] 没有成功评估的模型")
        return

    # 保存详细结果
    results_path = Path(output_dir) / "comparison_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {results_path}")

    # 生成对比报告
    print("\n" + "=" * 80)
    print("对比总结")
    print("=" * 80)
    print()

    comparison_table = []
    comparison_table.append(
        ["模型", "平均奖励", "平均距离(m)", "成功率(%)", "平均能量"]
    )
    comparison_table.append(["-" * 20, "-" * 12, "-" * 14, "-" * 12, "-" * 12])

    for result in all_results:
        stats = result["statistics"]
        comparison_table.append(
            [
                result["model_name"],
                f"{stats['mean_reward']:.2f} ± {stats['std_reward']:.2f}",
                f"{stats['mean_distance']:.3f} ± {stats['std_distance']:.3f}",
                f"{stats['success_rate'] * 100:.1f}",
                f"{stats['mean_energy']:.2f}",
            ]
        )

    for row in comparison_table:
        print(f"  {row[0]:25} {row[1]:15} {row[2]:18} {row[3]:15} {row[4]:15}")

    print()

    # 绘制对比图
    plot_comparison(all_results, output_dir)

    print(f"\n对比评估完成，结果保存在: {output_dir}")


def plot_comparison(results: List[Dict], output_dir: str):
    """绘制对比图表"""

    model_names = [r["model_name"] for r in results]
    mean_rewards = [r["statistics"]["mean_reward"] for r in results]
    std_rewards = [r["statistics"]["std_reward"] for r in results]
    mean_distances = [r["statistics"]["mean_distance"] for r in results]
    std_distances = [r["statistics"]["std_distance"] for r in results]
    success_rates = [r["statistics"]["success_rate"] * 100 for r in results]

    # 创建子图
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 1. 平均奖励对比
    axes[0].bar(model_names, mean_rewards, yerr=std_rewards, capsize=5, alpha=0.7)
    axes[0].set_ylabel("Average Reward", fontsize=12)
    axes[0].set_title("Average Reward Comparison", fontsize=13, fontweight="bold")
    axes[0].grid(axis="y", alpha=0.3)

    # 2. 平均距离对比
    axes[1].bar(
        model_names,
        mean_distances,
        yerr=std_distances,
        capsize=5,
        alpha=0.7,
        color="orange",
    )
    axes[1].set_ylabel("Average Distance (m)", fontsize=12)
    axes[1].set_title("Average Distance Comparison", fontsize=13, fontweight="bold")
    axes[1].grid(axis="y", alpha=0.3)

    # 3. 成功率对比
    axes[2].bar(model_names, success_rates, alpha=0.7, color="green")
    axes[2].set_ylabel("Success Rate (%)", fontsize=12)
    axes[2].set_title("Success Rate Comparison", fontsize=13, fontweight="bold")
    axes[2].set_ylim([0, 100])
    axes[2].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plot_path = Path(output_dir) / "comparison_plot.png"
    plt.savefig(plot_path, dpi=150)
    print(f"对比图表已保存到: {plot_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="模型对比评估")
    parser.add_argument(
        "--bc-weights",
        type=str,
        default="best_bc_policy_weights.pth",
        help="BC模型权重路径",
    )
    parser.add_argument(
        "--bc-ppo-model",
        type=str,
        default="./models_bc_warmstart/ppo_bc_warmstart_final.zip",
        help="BC+PPO模型路径",
    )
    parser.add_argument(
        "--vanilla-ppo-model",
        type=str,
        default="./models_fixed/ppo_gait_final.zip",
        help="原始PPO模型路径",
    )
    parser.add_argument(
        "--episodes", type=int, default=20, help="每个模型评估的episode数"
    )
    parser.add_argument(
        "--output-dir", type=str, default="./evaluation_results", help="结果输出目录"
    )

    args = parser.parse_args()

    compare_models(
        bc_weights_path=args.bc_weights,
        bc_ppo_model_path=args.bc_ppo_model,
        vanilla_ppo_model_path=args.vanilla_ppo_model,
        num_episodes=args.episodes,
        output_dir=args.output_dir,
    )

"""Policy Fingerprint 诊断工具

目标：对比 100k/150k/200k/350k checkpoint 的 phase-conditioned action delta，
定位 350k 在哪个 phase 出现异常偏置导致性能崩溃。

参考：logs/residual_rl_v2/GPT5_ANALYSIS_RESPONSE.md 优先级1
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
import json
from typing import Dict, Any

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2


def collect_fingerprint(model_path: str, env: ResidualRLEnvV2, episodes: int = 10) -> pd.DataFrame:
    """收集策略的 phase-conditioned action fingerprint

    Args:
        model_path: PPO checkpoint 路径
        env: ResidualRLEnvV2 环境实例
        episodes: 收集的 episode 数量

    Returns:
        包含详细 action/phase/state 信息的 DataFrame
    """
    print(f"Loading model from {model_path}")
    model = PPO.load(model_path)
    prior = np.array([0.5, 1.0])  # 从 train_residual_rl_v2.py 获取的 prior

    rows = []
    for ep in range(episodes):
        obs, info = env.reset()
        done = False
        step = 0

        while not done and step < 12000:  # 最多 12 秒
            action, _ = model.predict(obs, deterministic=True)
            delta = action - prior

            # 收集详细信息
            row = {
                "episode": ep,
                "step": step,
                "t": step * env.dt * env.inner_steps,  # 实际仿真时间
                "action_l": float(action[0]),
                "action_r": float(action[1]),
                "delta_l": float(delta[0]),
                "delta_r": float(delta[1]),
            }

            # 从 observation 中提取 phase 信息
            # 根据 train_residual_rl_v2.py:L354-361，phase onehot 在 obs[20:28]
            left_phase_idx = int(np.argmax(obs[20:24]))
            right_phase_idx = int(np.argmax(obs[24:28]))
            phase_names = ["stance_early", "stance_late", "swing_thrust", "swing_retract"]

            row["left_phase"] = phase_names[left_phase_idx]
            row["right_phase"] = phase_names[right_phase_idx]

            # 从 env.data 获取其他信息
            row["hip_height"] = float(env.data.qpos[2])
            row["x_position"] = float(env.data.qpos[0])

            # Step environment
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            row["reward"] = float(reward)
            row["terminated"] = terminated
            row["truncated"] = truncated

            rows.append(row)
            step += 1

            if done:
                row["final_distance"] = float(env.data.qpos[0])
                print(f"  Episode {ep}: distance={row['final_distance']:.3f}m, "
                      f"steps={step}, terminated={terminated}")

    return pd.DataFrame(rows)


def analyze_checkpoint(checkpoint_path: str, checkpoint_name: str, env: ResidualRLEnvV2) -> Dict[str, Any]:
    """分析单个 checkpoint 的行为模式

    Args:
        checkpoint_path: checkpoint 完整路径
        checkpoint_name: checkpoint 简短名称（如 "200k"）
        env: 环境实例

    Returns:
        分析结果字典
    """
    print(f"\n{'='*80}")
    print(f"Analyzing {checkpoint_name}")
    print(f"{'='*80}")

    df = collect_fingerprint(checkpoint_path, env, episodes=10)

    # 1. 全局统计
    print(f"\n## Global Statistics")
    global_stats = df[["action_l", "action_r", "delta_l", "delta_r", "hip_height", "reward"]].describe()
    print(global_stats)

    # 2. Phase-conditioned 统计
    print(f"\n## Phase-Conditioned Action Delta")
    phase_stats = df.groupby(["left_phase", "right_phase"])[
        ["delta_l", "delta_r", "hip_height", "reward"]
    ].agg(["mean", "std", "min", "max", "count"])
    print(phase_stats)

    # 3. 失败分析
    failed_episodes = df[df["terminated"] == True].groupby("episode").first()
    success_count = 10 - len(failed_episodes)

    print(f"\n## Success/Failure Summary")
    print(f"Success: {success_count}/10")
    print(f"Failure: {len(failed_episodes)}/10")

    if len(failed_episodes) > 0:
        print(f"\n## Failure Details")
        print(f"Mean failure time: {failed_episodes['t'].mean():.3f}s")
        print(f"Mean failure distance: {failed_episodes['x_position'].mean():.3f}m")

        # 失败前 500ms 的行为
        for ep_id in failed_episodes.index[:3]:  # 只显示前3个失败案例
            fail_data = df[df["episode"] == ep_id]
            fail_t = fail_data[fail_data["terminated"] == True]["t"].iloc[0]
            pre_fail = fail_data[(fail_data["t"] >= fail_t - 0.5) & (fail_data["t"] <= fail_t)]

            print(f"\n### Episode {ep_id} (fail at {fail_t:.3f}s):")
            print(pre_fail[["t", "left_phase", "right_phase", "delta_l", "delta_r", "hip_height"]].tail(10).to_string())

    # 4. 计算 final distance 统计
    final_distances = []
    for ep in df["episode"].unique():
        ep_data = df[df["episode"] == ep]
        final_distances.append(ep_data["x_position"].iloc[-1])

    print(f"\n## Final Distance Statistics")
    print(f"Mean: {np.mean(final_distances):.3f}m")
    print(f"Std: {np.std(final_distances):.3f}m")
    print(f"Min: {np.min(final_distances):.3f}m")
    print(f"Max: {np.max(final_distances):.3f}m")

    # 保存详细数据
    output_path = HW1_ROOT / "logs" / "residual_rl_v2" / f"fingerprint_{checkpoint_name}.csv"
    df.to_csv(output_path, index=False)
    print(f"\n[OK] Saved to {output_path}")

    return {
        "name": checkpoint_name,
        "success_rate": success_count / 10.0,
        "mean_distance": float(np.mean(final_distances)),
        "std_distance": float(np.std(final_distances)),
        "global_stats": global_stats.to_dict(),
        "failure_count": len(failed_episodes),
    }


def compare_checkpoints(results: Dict[str, Dict[str, Any]]):
    """对比不同 checkpoint 的行为差异"""
    print(f"\n{'='*80}")
    print("COMPARISON REPORT")
    print(f"{'='*80}")

    # 1. 成功率和距离对比
    print(f"\n## Performance Comparison")
    print(f"{'Checkpoint':<10} {'Success Rate':<15} {'Mean Distance':<15} {'Std Distance':<15}")
    print("-" * 55)
    for name in ["100k", "150k", "200k", "350k"]:
        if name in results:
            r = results[name]
            print(f"{name:<10} {r['success_rate']:<15.1%} {r['mean_distance']:<15.3f} {r['std_distance']:<15.3f}")

    # 2. 读取原始数据进行 phase-level 对比
    print(f"\n## Phase-Level Action Delta Comparison (200k vs 350k)")

    if "200k" in results and "350k" in results:
        df_200k = pd.read_csv(HW1_ROOT / "logs" / "residual_rl_v2" / "fingerprint_200k.csv")
        df_350k = pd.read_csv(HW1_ROOT / "logs" / "residual_rl_v2" / "fingerprint_350k.csv")

        # 对比每个 phase pair 的 delta 均值
        phase_pairs = [
            ("stance_early", "swing_retract"),
            ("stance_late", "swing_thrust"),
            ("swing_thrust", "stance_late"),
            ("swing_retract", "stance_early"),
        ]

        print(f"\n{'Left Phase':<15} {'Right Phase':<15} {'200k delta_l':<12} {'350k delta_l':<12} {'Diff':<10} {'200k delta_r':<12} {'350k delta_r':<12} {'Diff':<10}")
        print("-" * 110)

        for left_p, right_p in phase_pairs:
            mask_200k = (df_200k["left_phase"] == left_p) & (df_200k["right_phase"] == right_p)
            mask_350k = (df_350k["left_phase"] == left_p) & (df_350k["right_phase"] == right_p)

            if mask_200k.sum() > 0 and mask_350k.sum() > 0:
                delta_l_200k = df_200k[mask_200k]["delta_l"].mean()
                delta_l_350k = df_350k[mask_350k]["delta_l"].mean()
                delta_r_200k = df_200k[mask_200k]["delta_r"].mean()
                delta_r_350k = df_350k[mask_350k]["delta_r"].mean()

                diff_l = delta_l_350k - delta_l_200k
                diff_r = delta_r_350k - delta_r_200k

                print(f"{left_p:<15} {right_p:<15} {delta_l_200k:<12.4f} {delta_l_350k:<12.4f} {diff_l:<10.4f} {delta_r_200k:<12.4f} {delta_r_350k:<12.4f} {diff_r:<10.4f}")


def main():
    """主函数：执行 Policy Fingerprint 诊断"""
    print("="*80)
    print("Policy Fingerprint Diagnosis Tool")
    print("Goal: Locate which phase causes 350k checkpoint collapse")
    print("="*80)

    # 创建环境（修正：12秒 duration = 12000ms / 5ms = 2400 steps）
    print("\nInitializing environment...")
    env = ResidualRLEnvV2(max_steps=2400)  # 12 秒

    # 定义 checkpoints
    checkpoints = [
        ("models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip", "100k"),
        ("models/residual_rl_v2_500k/checkpoints/ppo_500k_150000_steps.zip", "150k"),
        ("models/residual_rl_v2_500k/ppo_best.zip", "200k"),
        ("models/residual_rl_v2_500k/checkpoints/ppo_500k_350000_steps.zip", "350k"),
    ]

    results = {}
    for path, name in checkpoints:
        full_path = HW1_ROOT / path
        if full_path.exists():
            results[name] = analyze_checkpoint(str(full_path), name, env)
        else:
            print(f"WARNING: {full_path} not found, skipping...")

    # 生成对比报告
    compare_checkpoints(results)

    # 保存 JSON 报告
    report_path = HW1_ROOT / "logs" / "residual_rl_v2" / "fingerprint_diagnosis.json"
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "checkpoints_analyzed": list(results.keys()),
        "results": results,
        "finding": "See fingerprint_*.csv and console output for detailed phase-level analysis",
        "recommendation": "If 350k shows sustained bias in specific phase pairs, that's the root cause of collapse",
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Report saved to {report_path}")
    print("\n" + "="*80)
    print("Diagnosis Complete! Check:")
    print("  1. fingerprint_*.csv - Step-by-step data")
    print("  2. fingerprint_diagnosis.json - Summary statistics")
    print("  3. Console output - Phase-level action delta comparison")
    print("="*80)


if __name__ == "__main__":
    main()

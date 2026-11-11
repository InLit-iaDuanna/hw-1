"""Residual sweep测试：扫描constant和phase-gated residual组合。

目标：
1. 测试constant residual: [-0.2, -0.1, 0, 0.1, 0.2] N·m
2. 测试phase-gated residual: 在特定相位施加residual
3. 找到至少1个+3%以上的组合

Phase-gated策略：
- stance_early: 仅在stance_early相位施加residual
- swing_thrust: 仅在swing_thrust相位施加residual
- alternating: left在stance, right在swing

验收标准：
- 至少找到1个组合使distance > baseline * 1.03
- 记录所有组合的performance
"""

from __future__ import annotations

import sys
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Tuple

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


@dataclass
class SweepResult:
    """Sweep测试结果"""

    strategy: str
    left_hip_residual: float
    right_hip_residual: float
    avg_distance: float
    std_distance: float
    success_rate: float
    improvement_pct: float


def get_phase_gated_action(
    env: ResidualRLEnvV2, strategy: str, residual: float
) -> np.ndarray:
    """根据策略生成phase-gated action。

    Args:
        env: 环境实例
        strategy: 策略名称
        residual: residual幅度

    Returns:
        2维action [left_hip, right_hip]
    """
    action = np.zeros(2, dtype=np.float32)

    left_phase = env._get_phase("left")
    right_phase = env._get_phase("right")

    if strategy == "constant":
        # 始终施加residual
        action[0] = residual  # left_hip
        action[1] = residual  # right_hip

    elif strategy == "stance_early_left":
        # 仅在left stance_early相位施加
        if left_phase == 0:
            action[0] = residual

    elif strategy == "stance_early_right":
        # 仅在right stance_early相位施加
        if right_phase == 0:
            action[1] = residual

    elif strategy == "swing_thrust_left":
        # 仅在left swing_thrust相位施加
        if left_phase == 2:
            action[0] = residual

    elif strategy == "swing_thrust_right":
        # 仅在right swing_thrust相位施加
        if right_phase == 2:
            action[1] = residual

    elif strategy == "alternating":
        # left在stance, right在swing
        if left_phase in [0, 1]:
            action[0] = residual
        if right_phase in [2, 3]:
            action[1] = residual

    return action


def test_residual_combination(
    strategy: str, left_residual: float, right_residual: float, num_episodes: int = 5
) -> SweepResult:
    """测试单个residual组合。

    Args:
        strategy: 策略名称
        left_residual: left_hip residual幅度
        right_residual: right_hip residual幅度
        num_episodes: 测试episode数

    Returns:
        SweepResult
    """
    env = ResidualRLEnvV2(
        residual_scale=1.0,  # 直接使用原始值
        inner_steps=5,
        max_steps=500,
    )

    distances = []
    successes = []

    for ep in range(num_episodes):
        obs, info = env.reset(seed=ep)

        terminated = False
        truncated = False

        while not (terminated or truncated):
            # 根据策略生成action
            if strategy == "constant":
                action = np.array([left_residual, right_residual], dtype=np.float32)
            else:
                # Phase-gated策略需要访问环境内部状态
                action = get_phase_gated_action(env, strategy, left_residual)

            obs, reward, terminated, truncated, info = env.step(action)

        distance = info["episode_distance"]
        success = truncated and not terminated

        distances.append(distance)
        successes.append(success)

    env.close()

    # 统计
    avg_distance = np.mean(distances)
    std_distance = np.std(distances)
    success_rate = sum(successes) / len(successes)

    # 计算改进百分比（相对baseline 4.63m）
    baseline_distance = 4.63
    improvement_pct = (avg_distance / baseline_distance - 1.0) * 100.0

    return SweepResult(
        strategy=strategy,
        left_hip_residual=left_residual,
        right_hip_residual=right_residual,
        avg_distance=avg_distance,
        std_distance=std_distance,
        success_rate=success_rate,
        improvement_pct=improvement_pct,
    )


def test_residual_sweep() -> dict:
    """运行完整的residual sweep测试。

    Returns:
        测试结果字典
    """
    print("=" * 80)
    print("Residual Sweep Test (V2)")
    print("=" * 80)
    print("Testing constant and phase-gated residual combinations")
    print("Goal: Find at least 1 combination with +3% improvement")
    print()

    results: List[SweepResult] = []

    # 1. Constant residual sweep
    print("Testing constant residual...")
    print("-" * 80)

    residual_values = [-0.2, -0.1, 0.0, 0.1, 0.2]

    for left_res in residual_values:
        for right_res in residual_values:
            print(
                f"  Testing: left={left_res:+.2f}, right={right_res:+.2f}...", end=" "
            )

            result = test_residual_combination(
                strategy="constant",
                left_residual=left_res,
                right_residual=right_res,
                num_episodes=5,
            )
            results.append(result)

            status = "[GOOD]" if result.improvement_pct > 3.0 else ""
            print(
                f"distance={result.avg_distance:.3f}m, "
                f"improvement={result.improvement_pct:+.1f}% {status}"
            )

    print()

    # 2. Phase-gated residual sweep
    print("Testing phase-gated residual...")
    print("-" * 80)

    strategies = [
        "stance_early_left",
        "stance_early_right",
        "swing_thrust_left",
        "swing_thrust_right",
        "alternating",
    ]

    phase_residual_values = [0.1, 0.2, 0.3]

    for strategy in strategies:
        for res in phase_residual_values:
            print(f"  Testing: {strategy}, residual={res:+.2f}...", end=" ")

            result = test_residual_combination(
                strategy=strategy, left_residual=res, right_residual=res, num_episodes=5
            )
            results.append(result)

            status = "[GOOD]" if result.improvement_pct > 3.0 else ""
            print(
                f"distance={result.avg_distance:.3f}m, "
                f"improvement={result.improvement_pct:+.1f}% {status}"
            )

    print()

    # 分析结果
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # 排序（按improvement降序）
    results_sorted = sorted(results, key=lambda x: x.improvement_pct, reverse=True)

    # Top 5
    print("Top 5 configurations:")
    print("-" * 80)
    for i, result in enumerate(results_sorted[:5]):
        print(
            f"{i + 1}. {result.strategy:20s} "
            f"left={result.left_hip_residual:+.2f}, right={result.right_hip_residual:+.2f} | "
            f"distance={result.avg_distance:.3f}m, "
            f"improvement={result.improvement_pct:+.1f}%, "
            f"success={result.success_rate * 100:.0f}%"
        )
    print()

    # 检查是否有+3%以上的组合
    best_result = results_sorted[0]
    good_results = [r for r in results if r.improvement_pct > 3.0]

    print("=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    if len(good_results) > 0:
        print(f"[PASS] Found {len(good_results)} configurations with +3% improvement!")
        print(
            f"  Best: {best_result.strategy} with {best_result.improvement_pct:+.1f}%"
        )
        print(f"  Distance: {best_result.avg_distance:.3f}m vs baseline 4.63m")
        print()
        print("Conclusion: Residual control shows clear potential for improvement.")
        print("Recommendation: Proceed with PPO training to learn adaptive residuals.")
        diagnosis = "PASS"
    else:
        print(f"[FAIL] No configuration achieved +3% improvement")
        print(
            f"  Best: {best_result.strategy} with {best_result.improvement_pct:+.1f}%"
        )
        print(f"  Distance: {best_result.avg_distance:.3f}m vs baseline 4.63m")
        print()
        print("Possible causes:")
        print("  1. residual_scale may be too small or too large")
        print("  2. Phase-gating logic may need refinement")
        print("  3. Baseline controller may already be near-optimal")
        diagnosis = "FAIL"

    print()

    # 保存结果
    summary = {
        "diagnosis": diagnosis,
        "baseline_distance": 4.63,
        "num_configurations": len(results),
        "num_good_configurations": len(good_results),
        "best_result": asdict(best_result),
        "all_results": [asdict(r) for r in results_sorted],
    }

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Sweep residual combinations for V2 environment"
    )
    parser.add_argument(
        "--save",
        type=str,
        default="test_residual_sweep_v2_report.json",
        help="Save path for results",
    )

    args = parser.parse_args()

    # 运行测试
    summary = test_residual_sweep()

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

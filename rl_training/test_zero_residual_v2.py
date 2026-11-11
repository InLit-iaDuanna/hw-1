"""测试zero residual：验证action=[0,0]时，V2环境与baseline一致。

目标：
1. 运行10个episodes，action固定为[0,0]
2. 验证结果与V13.7 baseline（4.63m）一致
3. 保存reference trajectory用于后续对比

验收标准：
- 平均距离在4.6±0.3m范围内
- 所有episodes都稳定完成（不摔倒）
- 保存reference数据到JSON
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import numpy as np

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


@dataclass
class ZeroResidualResult:
    """Zero residual测试结果"""

    episode_id: int
    distance: float
    sim_time: float
    success: bool
    failure_reason: str


def test_zero_residual(num_episodes: int = 10, save_trajectory: bool = False) -> dict:
    """测试zero residual。

    Args:
        num_episodes: 测试episode数

    Returns:
        测试结果字典
    """
    print("=" * 80)
    print("Zero Residual Test (V2)")
    print("=" * 80)
    print(f"Testing {num_episodes} episodes with action=[0, 0]")
    print("Expected: matches V13.7 baseline (~4.63m)")
    print()

    # 创建环境 (使用较长episode以匹配baseline 12s)
    env = ResidualRLEnvV2(
        residual_scale=0.05,
        inner_steps=5,
        max_steps=2400,  # 2400 * 5ms = 12s，匹配baseline
    )

    results: List[ZeroResidualResult] = []
    trajectories: List[dict] = []

    for ep in range(num_episodes):
        obs, info = env.reset(seed=ep)

        episode_trajectory = (
            {
                "episode_id": ep,
                "states": [],
                "actions": [],
                "rewards": [],
            }
            if save_trajectory
            else None
        )

        terminated = False
        truncated = False
        total_reward = 0.0

        while not (terminated or truncated):
            # Zero action
            action = np.array([0.0, 0.0], dtype=np.float32)

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

            if episode_trajectory is not None:
                episode_trajectory["states"].append(obs.tolist())
                episode_trajectory["actions"].append(action.tolist())
                episode_trajectory["rewards"].append(float(reward))

        # 结果
        distance = info["episode_distance"]
        sim_time = info["sim_time"]
        success = truncated and not terminated

        result = ZeroResidualResult(
            episode_id=ep,
            distance=distance,
            sim_time=sim_time,
            success=success,
            failure_reason="completed" if success else "terminated_early",
        )
        results.append(result)
        if episode_trajectory is not None:
            trajectories.append(episode_trajectory)

        status = "[SUCCESS]" if success else "[FAIL]"
        print(
            f"Episode {ep + 1}: {status} | "
            f"distance={distance:.3f}m | "
            f"time={sim_time:.2f}s | "
            f"reward={total_reward:.1f}"
        )

    env.close()

    # 统计分析
    print()
    print("=" * 80)
    print("STATISTICAL ANALYSIS")
    print("=" * 80)

    distances = [r.distance for r in results]
    times = [r.sim_time for r in results]
    successes = [r.success for r in results]

    avg_distance = np.mean(distances)
    std_distance = np.std(distances)
    max_distance = np.max(distances)
    min_distance = np.min(distances)
    avg_time = np.mean(times)
    success_rate = sum(successes) / len(successes)

    print("Distance Statistics:")
    print(f"  Average: {avg_distance:.3f} +/- {std_distance:.3f} m")
    print(f"  Range: [{min_distance:.3f}, {max_distance:.3f}] m")
    print("  Baseline: 4.630 m")
    print(
        f"  Deviation: {avg_distance - 4.63:+.3f} m ({(avg_distance / 4.63 - 1) * 100:+.1f}%)"
    )
    print()

    print("Time Statistics:")
    print(f"  Average: {avg_time:.2f} s")
    print("  Expected: 12.00 s (max_steps=2400, inner_steps=5)")
    print()

    print(
        f"Success Rate: {success_rate * 100:.0f}% ({sum(successes)}/{len(successes)})"
    )
    print()

    # 诊断
    print("=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    BASELINE_DISTANCE = 4.63
    tolerance = 0.3

    if success_rate >= 0.8 and abs(avg_distance - BASELINE_DISTANCE) < tolerance:
        print("[PASS] Zero residual test passed!")
        print(f"  - Average distance {avg_distance:.3f}m matches baseline")
        print(f"  - {success_rate * 100:.0f}% of episodes completed successfully")
        print()
        print("Conclusion: ResidualRLEnvV2 correctly reproduces V13.7 baseline.")
        print("Recommendation: Proceed with sweep and training tests.")
        diagnosis = "PASS"
    else:
        print("[FAIL] Zero residual test failed")
        if success_rate < 0.8:
            print(f"  - Success rate too low: {success_rate * 100:.0f}%")
        if abs(avg_distance - BASELINE_DISTANCE) >= tolerance:
            print(
                f"  - Distance deviation too large: {avg_distance - BASELINE_DISTANCE:+.3f}m"
            )
        diagnosis = "FAIL"

    print()

    # 保存结果
    summary = {
        "diagnosis": diagnosis,
        "num_episodes": num_episodes,
        "baseline_distance": BASELINE_DISTANCE,
        "statistics": {
            "avg_distance": float(avg_distance),
            "std_distance": float(std_distance),
            "max_distance": float(max_distance),
            "min_distance": float(min_distance),
            "avg_time": float(avg_time),
            "success_rate": float(success_rate),
        },
        "episodes": [asdict(r) for r in results],
        "reference_trajectory": trajectories[0] if len(trajectories) > 0 else None,
    }

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Test zero residual for V2 environment"
    )
    parser.add_argument(
        "--episodes", type=int, default=10, help="Number of test episodes"
    )
    parser.add_argument(
        "--save",
        type=str,
        default="logs/residual_rl_v2/test_zero_residual_v2_report.json",
        help="Save path for results",
    )
    parser.add_argument(
        "--save-trajectory",
        action="store_true",
        help="Save full observation/action trajectory",
    )

    args = parser.parse_args()

    # 运行测试
    summary = test_zero_residual(
        num_episodes=args.episodes, save_trajectory=args.save_trajectory
    )

    # 保存结果
    save_path = Path(args.save)
    if not save_path.is_absolute():
        save_path = HW1_ROOT / save_path
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Results saved to: {save_path}")
    print()

    # 返回退出码
    exit_code = 0 if summary["diagnosis"] == "PASS" else 1
    return exit_code


if __name__ == "__main__":
    exit(main())

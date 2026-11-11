"""Test zero residual with inner_steps=1 to isolate the issue"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


def test_inner_steps_impact():
    """测试inner_steps对结果的影响"""

    print("=" * 80)
    print("Inner Steps Impact Test")
    print("=" * 80)

    for inner_steps in [1, 5]:
        print(f"\n{'='*80}")
        print(f"Testing with inner_steps={inner_steps}")
        print(f"{'='*80}")

        # 创建环境
        max_steps = 12000 // inner_steps  # 12秒
        env = ResidualRLEnvV2(
            residual_scale=0.05,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )

        obs, info = env.reset(seed=0)

        terminated = False
        truncated = False

        while not (terminated or truncated):
            action = np.array([0.0, 0.0], dtype=np.float32)
            obs, reward, terminated, truncated, info = env.step(action)

        distance = info["episode_distance"]
        sim_time = info["sim_time"]
        success = truncated and not terminated

        status = "[SUCCESS]" if success else "[FAIL]"
        print(f"\nResult: {status}")
        print(f"  Distance: {distance:.3f}m (expected: ~4.63m)")
        print(f"  Time: {sim_time:.2f}s (expected: 12.00s)")
        print(f"  Terminated: {terminated}")
        print(f"  Truncated: {truncated}")

        env.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_inner_steps_impact()

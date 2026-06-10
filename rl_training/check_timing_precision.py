"""Check timing precision in sim_time accumulation"""

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2
import numpy as np

def check_timing_precision():
    """检查sim_time累积精度"""

    print("=" * 80)
    print("Timing Precision Check")
    print("=" * 80)

    # 测试inner_steps=1 vs inner_steps=5
    for inner_steps in [1, 5]:
        env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=inner_steps, max_steps=2000)
        obs, info = env.reset(seed=0)

        print(f"\ninner_steps={inner_steps}:")
        print(f"  Initial sim_time: {env.sim_time:.10f}")
        print(f"  dt: {env.dt:.10f}")

        # 运行100步
        for i in range(100):
            action = np.array([0.0, 0.0], dtype=np.float32)
            obs, reward, terminated, truncated, info = env.step(action)

            if i == 99:
                expected_time = 100 * inner_steps * 0.001
                actual_time = env.sim_time
                error = actual_time - expected_time
                print(f"  After 100 PPO steps:")
                print(f"    Expected sim_time: {expected_time:.10f}")
                print(f"    Actual sim_time: {actual_time:.10f}")
                print(f"    Error: {error:.10e}")

        env.close()

    print()

if __name__ == "__main__":
    check_timing_precision()

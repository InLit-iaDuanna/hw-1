"""检查sim_time在V2环境中是否正确累积。"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path("../v13_7_friction_compensation")))
sys.path.insert(0, str(Path("../v14_passive_arms")))
sys.path.insert(0, str(Path("..")))

from train_residual_rl_v2 import ResidualRLEnvV2

env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=100)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

print("Checking sim_time accumulation...")
print(f"{'PPO_step':<10} {'Expected_t':<12} {'Actual_t':<12} {'Diff':<10}")
print("-" * 50)

for step in range(20):
    expected_time = (step + 1) * 5 * 0.001  # PPO step * inner_steps * dt

    obs, reward, terminated, truncated, info = env.step(action)

    actual_time = env.sim_time
    diff = actual_time - expected_time

    print(f"{step+1:<10} {expected_time:<12.6f} {actual_time:<12.6f} {diff:<10.9f}")

    if abs(diff) > 0.0001:
        print(f"\n[WARNING] Time mismatch at step {step+1}!")
        print(f"  Expected: {expected_time:.6f}s")
        print(f"  Actual: {actual_time:.6f}s")
        break

env.close()

print(
    "\n[OK] sim_time accumulation is correct"
    if abs(diff) < 0.0001
    else "\n[PROBLEM] sim_time has errors"
)

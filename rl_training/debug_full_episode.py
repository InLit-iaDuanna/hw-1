"""Debug: 运行完整12秒episode查看是否能稳定。"""

from __future__ import annotations

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

import numpy as np

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2

# 创建环境
env = ResidualRLEnvV2(
    residual_scale=0.05,
    inner_steps=5,
    max_steps=2400,
)

print("=" * 80)
print("Debug: Full 12-second Episode")
print("=" * 80)

# Reset
obs, info = env.reset(seed=0)

# 运行完整episode
step_count = 0
for step in range(2400):
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    step_count = step + 1

    if step % 400 == 0:
        print(
            f"Step {step:4d} ({env.sim_time:.2f}s): "
            f"hip_x={info['hip_x']:.3f}, "
            f"distance={info['episode_distance']:.3f}, "
            f"hip_vx={info['hip_vel_x']:.3f}, "
            f"support={env.support_foot}"
        )

    if terminated or truncated:
        break

print()
print("Episode ended:")
print(f"  Steps: {step_count} / 2400")
print(f"  Time: {env.sim_time:.2f}s / 12.00s")
print(f"  Distance: {info['episode_distance']:.3f}m")
print(f"  Terminated: {terminated}")
print(f"  Truncated: {truncated}")
print(
    f"  Expected baseline distance in {env.sim_time:.2f}s: {4.63 * env.sim_time / 12.0:.3f}m"
)

env.close()

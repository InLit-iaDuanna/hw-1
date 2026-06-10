"""Debug: 更详细地检查episode_distance计算。"""

from __future__ import annotations

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2
import numpy as np

# 创建环境
env = ResidualRLEnvV2(
    residual_scale=0.05,
    inner_steps=5,
    max_steps=2400,
)

print("=" * 80)
print("Debug: Episode Distance Calculation")
print("=" * 80)

# Reset
obs, info = env.reset(seed=0)

print(f"After reset:")
print(f"  start_x: {env.start_x:.3f}")
print(f"  current hip_x: {env.data.qpos[0]:.3f}")
print(f"  episode_distance: {env.episode_distance:.3f}")
print()

# 运行800步 (4s)
print("Running 800 steps (4 seconds)...")
for step in range(800):
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 200 == 0:
        actual_distance = env.data.qpos[0] - env.start_x
        print(
            f"Step {step:4d}: "
            f"hip_x={env.data.qpos[0]:.3f}, "
            f"episode_distance={info['episode_distance']:.3f}, "
            f"actual_distance={actual_distance:.3f}, "
            f"diff={info['episode_distance'] - actual_distance:.6f}"
        )

    if terminated or truncated:
        break

print()
print(f"Final state:")
print(f"  start_x: {env.start_x:.3f}")
print(f"  final hip_x: {env.data.qpos[0]:.3f}")
print(f"  episode_distance: {info['episode_distance']:.3f}")
print(f"  actual distance: {env.data.qpos[0] - env.start_x:.3f}")
print(f"  terminated: {terminated}")
print(f"  truncated: {truncated}")
print(f"  sim_time: {env.sim_time:.2f}s")

env.close()

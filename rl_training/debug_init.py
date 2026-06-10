"""Debug: 检查初始化参数。"""

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
print("Debug: Initialization Parameters")
print("=" * 80)
print(f"Parameters:")
print(f"  initial_vx: {env.params.base.initial_vx}")
print(f"  swing_hip_vel: {env.params.base.swing_hip_vel}")
print(f"  swing_knee_vel: {env.params.base.swing_knee_vel}")
print(f"  gait_period: {env.params.base.gait_period}")
print()

# Reset and check initial state
obs, info = env.reset(seed=0)

print("After reset:")
print(f"  qpos[0] (hip_x): {env.data.qpos[0]:.6f}")
print(f"  qpos[1] (hip_z): {env.data.qpos[1]:.6f}")
print(f"  qvel[0] (hip_vx): {env.data.qvel[0]:.6f} (expected: {env.params.base.initial_vx:.6f})")
print(f"  qvel[1] (hip_vz): {env.data.qvel[1]:.6f}")
print(f"  qvel[2] (left_hip): {env.data.qvel[2]:.6f}")
print(f"  qvel[5] (right_hip): {env.data.qvel[5]:.6f}")
print()

# Run a few steps and check
for step in range(5):
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    print(f"Step {step}: hip_x={info['hip_x']:.4f}, hip_vx={info['hip_vel_x']:.4f}")

env.close()

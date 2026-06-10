"""Debug script: 检查V13.7控制器在ResidualRLEnvV2中是否正常工作。"""

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
print("Debug: Check V13.7 Controller in ResidualRLEnvV2")
print("=" * 80)
print(f"Parameters:")
print(f"  gait_period: {env.params.base.gait_period}")
print(f"  timestep: {env.params.base.timestep}")
print(f"  hip_motor: {env.params.hip_motor.name}")
print(f"  compensate_friction: {env.params.compensate_friction}")
print()

# Reset
obs, info = env.reset(seed=0)

print(f"Initial state:")
print(f"  hip_x: {env.data.qpos[0]:.3f}")
print(f"  hip_z: {env.data.qpos[1]:.3f}")
print(f"  support_foot: {env.support_foot}")
print(f"  burst_start_t: {env.burst_start_t:.3f}")
print()

# 运行前100步，打印状态
print("Running first 100 steps with zero action...")
print("-" * 80)

for step in range(100):
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 20 == 0:
        print(
            f"Step {step:3d}: "
            f"hip_x={info['hip_x']:.3f}, "
            f"hip_z={info['hip_height']:.3f}, "
            f"hip_vx={info['hip_vel_x']:.3f}, "
            f"support={env.support_foot}, "
            f"phase_t={env.sim_time - env.burst_start_t:.3f}"
        )

    if terminated:
        print(f"\n[TERMINATED] at step {step}, time {env.sim_time:.2f}s")
        print(f"  Failure detected, distance={info['episode_distance']:.3f}m")
        break

    if truncated:
        print(f"\n[TRUNCATED] at step {step}, time {env.sim_time:.2f}s")
        print(f"  Episode completed, distance={info['episode_distance']:.3f}m")
        break

env.close()
print()
print("Debug complete.")

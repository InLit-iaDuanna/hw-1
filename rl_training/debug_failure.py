"""Debug: 检查failure detection是否工作。"""

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
print("Debug: Failure Detection")
print("=" * 80)

# Reset
obs, info = env.reset(seed=0)

# 运行1000步并观察failure detection
for step in range(1000):
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 100 == 0:
        from simulate_passive_arms_v14 import classify_failure
        failure_reason = classify_failure(env.model, env.data, env.params.base, env.start_x, env.sim_time)

        print(
            f"Step {step:4d}: "
            f"hip_x={info['hip_x']:.3f}, "
            f"hip_z={info['hip_height']:.3f}, "
            f"hip_vx={info['hip_vel_x']:.3f}, "
            f"terminated={terminated}, "
            f"failure_reason='{failure_reason}'"
        )

    if terminated or truncated:
        print(f"\nEpisode ended at step {step}")
        print(f"  terminated={terminated}, truncated={truncated}")
        break

env.close()

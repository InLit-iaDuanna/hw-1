"""追踪classify_failure的返回值。"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path("../v13_7_friction_compensation")))
sys.path.insert(0, str(Path("../v14_passive_arms")))
sys.path.insert(0, str(Path("../v13_6_event_driven_fsm")))
sys.path.insert(0, str(Path("..")))

from train_residual_rl_v2 import ResidualRLEnvV2
from simulate_passive_arms_v14 import classify_failure

env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

print("Running until failure...")
print(f"{'Step':<6} {'Time':<8} {'hip_x':<10} {'hip_h':<8} {'Failure':<15}")
print("-" * 60)

for step in range(1000):
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 100 == 0:
        failure_reason = classify_failure(
            env.model, env.data, env.params.base, env.start_x, env.sim_time
        )
        print(
            f"{step:<6} {env.sim_time:<8.3f} {info['hip_x']:<10.3f} "
            f"{info['hip_height']:<8.3f} {failure_reason:<15}"
        )

    if terminated:
        failure_reason = classify_failure(
            env.model, env.data, env.params.base, env.start_x, env.sim_time
        )
        print(f"\n[TERMINATED] at step {step}, t={env.sim_time:.3f}s")
        print(f"Failure reason: '{failure_reason}'")
        print(f"hip_height: {info['hip_height']:.4f}")
        print(f"hip_x: {info['hip_x']:.4f}")
        break

env.close()

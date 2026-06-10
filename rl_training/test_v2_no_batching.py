"""测试V2环境使用inner_steps=1（无批处理）。"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path('../v13_7_friction_compensation')))
sys.path.insert(0, str(Path('../v14_passive_arms')))
sys.path.insert(0, str(Path('..')))

from train_residual_rl_v2 import ResidualRLEnvV2

print('Testing V2 with inner_steps=1 (no batching)...')
env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=1, max_steps=12000)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

for step in range(12000):
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 1000 == 0:
        print(f"Step {step}, t={env.sim_time:.3f}s, distance={info['episode_distance']:.3f}m")

    if terminated:
        print(f"\n[TERMINATED] at t={env.sim_time:.3f}s, distance={info['episode_distance']:.3f}m")
        break

    if truncated:
        print(f"\n[COMPLETED] t={env.sim_time:.3f}s, distance={info['episode_distance']:.3f}m")
        break

env.close()

print("\nExpected: 4.630m in 12.00s (like Identity Test)")

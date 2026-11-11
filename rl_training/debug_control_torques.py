"""Debug control torques at each timestep"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


def debug_control_torques():
    """对比V2环境在前100ms的控制力矩"""

    print("=" * 80)
    print("Control Torque Debug for train_residual_rl_v2.py")
    print("=" * 80)

    env = ResidualRLEnvV2(
        residual_scale=0.05,
        inner_steps=5,
        max_steps=2400,
    )

    obs, info = env.reset(seed=0)

    print("\nInitial state (t=0.000s):")
    print(f"  qpos[0:8]: {env.data.qpos[0:8]}")
    print(f"  qvel[0:7]: {env.data.qvel[0:7]}")
    print()

    print("Control torques for first 200ms (40 PPO steps):")
    print("-" * 80)

    terminated = False
    truncated = False
    step_count = 0

    while not (terminated or truncated) and step_count < 40:
        action = np.array([0.0, 0.0], dtype=np.float32)

        # 记录step前的状态
        t_before = env.sim_time

        obs, reward, terminated, truncated, info = env.step(action)

        if step_count % 10 == 0:  # 每10步打印一次
            print(f"Step {step_count} (t={t_before:.4f}s -> {env.sim_time:.4f}s):")
            print(f"  last_base_torques: {env.last_base_torques}")
            print(f"  ctrl applied: {env.data.ctrl[:]}")
            print(f"  hip_x: {env.data.qpos[0]:.4f}m")
            print(f"  support_foot: {env.support_foot}")
            print(f"  burst_start_t: {env.burst_start_t:.4f}s")
            print()

        step_count += 1

    print("-" * 80)
    print(f"Final state at t={env.sim_time:.3f}s:")
    print(f"  Distance: {info['episode_distance']:.4f}m")
    print(f"  Terminated: {terminated}")
    print()

    env.close()


if __name__ == "__main__":
    debug_control_torques()

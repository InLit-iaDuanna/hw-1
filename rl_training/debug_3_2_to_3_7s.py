"""Debug what happens between 3.2s and 3.7s in V2"""

import sys
import numpy as np
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2
from simulate_passive_arms_v14 import contact_flags


def debug_3_2s_to_3_7s():
    """调试3.2-3.7s之间发生了什么"""

    print("=" * 80)
    print("Debug V2: 3.2s - 3.7s (FSM transition delay period)")
    print("=" * 80)

    env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=1, max_steps=10000)
    obs, info = env.reset(seed=0)

    # Run to 3.2s
    for step in range(3200):
        action = np.array([0.0, 0.0], dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)

    print(f"\nAt t=3.200s:")
    print(f"  hip_x: {env.data.qpos[0]:.4f}m")
    print(f"  support_foot: {env.support_foot}")
    print(f"  burst_start_t: {env.burst_start_t:.4f}s")
    print(f"  accepted_contact: '{env.accepted_contact}'")
    print(f"  last_event_t: {env.last_event_t:.4f}s")
    print()

    print("Contact detection from 3.2s to 3.7s:")
    print("-" * 80)

    # Step through 3.2-3.7s with detailed logging
    for step in range(500):
        t = 3.200 + step * 0.001

        action = np.array([0.0, 0.0], dtype=np.float32)

        # Check contact before step
        left_c, right_c = contact_flags(env.model, env.data)
        old_support = env.support_foot
        old_burst = env.burst_start_t

        obs, reward, terminated, truncated, info = env.step(action)

        # Check if FSM switched
        if env.support_foot != old_support or env.burst_start_t != old_burst:
            print(
                f"[{t:.3f}s] FSM SWITCH: support={old_support}->{env.support_foot}, burst_t={old_burst:.4f}->{env.burst_start_t:.4f}"
            )

        # Print detailed state every 50ms
        if step % 50 == 0:
            left_c, right_c = contact_flags(env.model, env.data)
            print(
                f"t={t:.3f}s: L={int(left_c)} R={int(right_c)} | candidate_L={env.candidate_start_t['left']} | hip_x={env.data.qpos[0]:.4f}m | support={env.support_foot}"
            )

        if terminated:
            print(f"\n[TERMINATED at t={t:.3f}s]")
            break

    print("-" * 80)
    print(f"\nFinal state:")
    print(f"  hip_x: {env.data.qpos[0]:.4f}m")
    print(f"  support_foot: {env.support_foot}")
    print(f"  burst_start_t: {env.burst_start_t:.4f}s")
    print()

    env.close()


if __name__ == "__main__":
    debug_3_2s_to_3_7s()

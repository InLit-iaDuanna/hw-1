"""Debug FSM transitions in train_residual_rl_v2.py"""

import sys
import numpy as np
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


def debug_fsm_transitions():
    """运行一个episode并打印所有FSM状态转换"""

    print("=" * 80)
    print("FSM Transition Debug for train_residual_rl_v2.py")
    print("=" * 80)

    # 创建环境
    env = ResidualRLEnvV2(
        residual_scale=0.05,
        inner_steps=5,
        max_steps=2400,  # 12s
    )

    obs, info = env.reset(seed=0)

    print(f"\nInitial state:")
    print(f"  support_foot: {env.support_foot}")
    print(f"  burst_start_t: {env.burst_start_t:.4f}")
    print(f"  accepted_contact: '{env.accepted_contact}'")
    print(f"  last_event_t: {env.last_event_t:.4f}")
    print(f"  gait_period: {env.params.base.gait_period}")
    print(f"  stable_contact_time: {env.params.base.stable_contact_time}")
    print(f"  min_event_interval: {env.params.base.min_event_interval}")
    print()

    print("FSM Transitions:")
    print("-" * 80)

    last_accepted = env.accepted_contact
    last_support = env.support_foot

    terminated = False
    truncated = False
    step_count = 0

    while not (terminated or truncated) and step_count < 800:  # 800步 = 4秒
        action = np.array([0.0, 0.0], dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)

        # 检测状态变化
        if env.accepted_contact != last_accepted or env.support_foot != last_support:
            print(f"[{env.sim_time:.4f}s] FSM Event:")
            print(f"  accepted_contact: '{last_accepted}' -> '{env.accepted_contact}'")
            print(f"  support_foot: '{last_support}' -> '{env.support_foot}'")
            print(f"  burst_start_t: {env.burst_start_t:.4f}")
            print(f"  last_event_t: {env.last_event_t:.4f}")

            last_accepted = env.accepted_contact
            last_support = env.support_foot

        step_count += 1

    print("-" * 80)
    print(f"\nFinal Results:")
    print(f"  Steps completed: {step_count}")
    print(f"  Sim time: {env.sim_time:.2f}s")
    print(f"  Distance: {info['episode_distance']:.3f}m")
    print(f"  Terminated: {terminated}")
    print(f"  Truncated: {truncated}")
    print(f"  Final accepted_contact: '{env.accepted_contact}'")
    print(f"  Final support_foot: '{env.support_foot}'")
    print()

    env.close()


if __name__ == "__main__":
    debug_fsm_transitions()

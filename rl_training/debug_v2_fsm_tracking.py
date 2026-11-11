"""追踪FSM状态变化，找出在哪里出错。"""

import sys
from pathlib import Path
import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))
sys.path.insert(0, str(HW1_ROOT / "v13_7_friction_compensation"))
sys.path.insert(0, str(HW1_ROOT / "v13_6_event_driven_fsm"))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from train_residual_rl_v2 import ResidualRLEnvV2

print("=" * 80)
print("FSM State Tracking (first 3 seconds)")
print("=" * 80)

env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

print(
    f"\n{'Step':<6} {'Time':<8} {'hip_x':<10} {'hip_vx':<10} {'Support':<8} {'Burst_t':<10} {'Accepted':<10} {'E_curr':<10}"
)
print("-" * 90)

last_support = env.support_foot
last_burst = env.burst_start_t
fsm_events = []

for step in range(600):  # 前3秒
    obs, reward, terminated, truncated, info = env.step(action)

    # 检测FSM事件
    if env.support_foot != last_support or env.burst_start_t != last_burst:
        event = {
            "step": step,
            "time": env.sim_time,
            "support": env.support_foot,
            "burst_t": env.burst_start_t,
            "accepted": env.accepted_contact,
            "hip_x": info["hip_x"],
        }
        fsm_events.append(event)
        last_support = env.support_foot
        last_burst = env.burst_start_t

    # 打印前20步和每50步
    if step < 20 or step % 50 == 0:
        from simulate_v13_7 import _mechanical_energy

        E_current = _mechanical_energy(env.params.base, env.data)

        print(
            f"{step:<6} {env.sim_time:<8.3f} {info['hip_x']:<10.6f} "
            f"{info['hip_vel_x']:<10.6f} {env.support_foot:<8} "
            f"{env.burst_start_t:<10.3f} {env.accepted_contact:<10} {E_current:<10.3f}"
        )

    if terminated or truncated:
        break

print("\n" + "=" * 80)
print("FSM Events Summary")
print("=" * 80)
for i, event in enumerate(fsm_events):
    print(
        f"Event {i+1}: t={event['time']:.3f}s, support={event['support']}, "
        f"burst_t={event['burst_t']:.3f}s, hip_x={event['hip_x']:.6f}"
    )

print(f"\nTotal FSM events: {len(fsm_events)}")
print(f"Expected: ~2 events per second (left->right->left...)")
print(f"Expected total in 3s: ~6 events")

if len(fsm_events) < 4:
    print(f"\n[WARNING] Too few FSM events! FSM may not be switching properly.")
elif len(fsm_events) > 10:
    print(f"\n[WARNING] Too many FSM events! FSM may be oscillating.")
else:
    print(f"\n[OK] FSM event count looks reasonable.")

env.close()

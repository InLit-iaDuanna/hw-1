"""追踪接触状态，找出为什么FSM停止切换。"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))
sys.path.insert(0, str(HW1_ROOT / "v13_7_friction_compensation"))
sys.path.insert(0, str(HW1_ROOT / "v13_6_event_driven_fsm"))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from simulate_passive_arms_v14 import contact_flags
from train_residual_rl_v2 import ResidualRLEnvV2

print("=" * 80)
print("Contact State Tracking (1.0s - 2.5s)")
print("=" * 80)

env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)
obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

# 快进到1.0秒
for step in range(200):
    obs, reward, terminated, truncated, info = env.step(action)

print("\nStarting from t=1.0s (after Event 3)")
print(f"Current support: {env.support_foot}")
print(f"Last event: {env.last_event_t:.3f}s")
print(f"Accepted contact: '{env.accepted_contact}'")

print(
    f"\n{'Step':<6} {'Time':<8} {'Left_C':<8} {'Right_C':<8} {'Cand_L':<10} {'Cand_R':<10} {'Support':<8} {'Event':<6}"
)
print("-" * 80)

for step in range(200, 500):  # 1.0s到2.5s
    left_contact, right_contact = contact_flags(env.model, env.data)

    obs, reward, terminated, truncated, info = env.step(action)

    cand_l = (
        f"{env.candidate_start_t['left']:.3f}"
        if env.candidate_start_t["left"] is not None
        else "None"
    )
    cand_r = (
        f"{env.candidate_start_t['right']:.3f}"
        if env.candidate_start_t["right"] is not None
        else "None"
    )

    event_marker = ""
    if step == 200 or abs(env.last_event_t - env.sim_time) < 0.01:
        event_marker = "<<<" if abs(env.last_event_t - env.sim_time) < 0.01 else ""

    # 打印每10步
    if step % 10 == 0 or event_marker:
        print(
            f"{step:<6} {env.sim_time:<8.3f} {int(left_contact):<8} {int(right_contact):<8} "
            f"{cand_l:<10} {cand_r:<10} {env.support_foot:<8} {event_marker:<6}"
        )

    if terminated or truncated:
        break

print("\n" + "=" * 80)
print("Analysis:")
print("=" * 80)

print(f"Final support foot: {env.support_foot}")
print(f"Last FSM event: {env.last_event_t:.3f}s")
print("Expected next event: ~1.7s (left contact after 1.3s right burst)")

if env.last_event_t < 1.5:
    print("\n[PROBLEM] FSM stopped switching after 1.3s")
    print("Possible reasons:")
    print("  1. Left foot never established stable contact after 1.3s")
    print("  2. Contact detection (contact_flags) is failing")
    print("  3. candidate_start_t not being set correctly")
    print("  4. min_event_interval blocking new events")

env.close()

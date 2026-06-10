"""运行完整episode，找出在哪一步开始后退。"""

import sys
from pathlib import Path
import numpy as np

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "rl_training"))
sys.path.insert(0, str(HW1_ROOT / "v13_7_friction_compensation"))
sys.path.insert(0, str(HW1_ROOT / "v13_6_event_driven_fsm"))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from train_residual_rl_v2 import ResidualRLEnvV2

print("=" * 80)
print("Full Episode Test (12 seconds)")
print("=" * 80)

# 创建V2环境
env = ResidualRLEnvV2(
    residual_scale=0.05,
    inner_steps=5,
    max_steps=2400,  # 12秒
)

obs, info = env.reset()
action = np.array([0.0, 0.0], dtype=np.float32)

print(f"\nInitial state:")
print(f"  hip_x: {info['hip_x']:.6f}")
print(f"  hip_vx: {env.data.qvel[0]:.6f}")

print(f"\nRunning episode...")
print(f"{'Step':<8} {'Time(s)':<10} {'hip_x':<12} {'Distance':<12} {'hip_vx':<12} {'Status':<10}")
print("-" * 80)

max_distance = 0.0
step_at_max = 0
time_at_max = 0.0

for step in range(2400):
    obs, reward, terminated, truncated, info = env.step(action)

    current_distance = info['episode_distance']

    if current_distance > max_distance:
        max_distance = current_distance
        step_at_max = step
        time_at_max = env.sim_time

    # 每200步（1秒）打印一次
    if step % 200 == 0 or step < 20:
        status = "OK"
        if current_distance < max_distance - 0.01:
            status = "BACKWARD!"

        print(
            f"{step:<8} {env.sim_time:<10.3f} {info['hip_x']:<12.6f} "
            f"{current_distance:<12.6f} {info['hip_vel_x']:<12.6f} {status:<10}"
        )

    if terminated:
        print(f"\n[TERMINATED] at step {step}, time={env.sim_time:.3f}s")
        print(f"  Reason: hip_height={info['hip_height']:.4f} < threshold")
        break

    if truncated:
        print(f"\n[COMPLETED] Full episode")
        break

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print(f"Max forward distance: {max_distance:.6f}m at step {step_at_max} (t={time_at_max:.3f}s)")
print(f"Final distance: {info['episode_distance']:.6f}m at t={env.sim_time:.3f}s")
print(f"Distance change: {info['episode_distance'] - max_distance:+.6f}m")

if info['episode_distance'] < max_distance - 0.01:
    print(f"\n[PROBLEM DETECTED] Robot started moving backward after {time_at_max:.3f}s")
    print(f"  This suggests FSM or control issue after ~{time_at_max:.1f}s")
else:
    print(f"\n[OK] Robot continuously moved forward")

env.close()

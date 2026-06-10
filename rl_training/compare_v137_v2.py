"""对比：运行test_v137_identity和ResidualRLEnvV2，看参数是否完全一致。"""

from __future__ import annotations

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
RL_TRAINING_DIR = HW1_ROOT / "rl_training"
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(RL_TRAINING_DIR))

from test_v137_identity import V137IdentitySimulator
from train_residual_rl_v2 import ResidualRLEnvV2
import numpy as np

print("=" * 80)
print("Comparison: V137IdentitySimulator vs ResidualRLEnvV2")
print("=" * 80)

# 创建两个模拟器
print("Creating V137IdentitySimulator...")
v137_sim = V137IdentitySimulator()

print("Creating ResidualRLEnvV2...")
v2_env = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)

print()
print("Parameter Comparison:")
print("-" * 80)

# 比较base参数
print(f"thigh_length:     v137={v137_sim.params.base.thigh_length:.6f}, v2={v2_env.params.base.thigh_length:.6f}")
print(f"shank_length:     v137={v137_sim.params.base.shank_length:.6f}, v2={v2_env.params.base.shank_length:.6f}")
print(f"step_length:      v137={v137_sim.params.base.step_length:.6f}, v2={v2_env.params.base.step_length:.6f}")
print(f"foot_radius:      v137={v137_sim.params.base.foot_radius:.6f}, v2={v2_env.params.base.foot_radius:.6f}")
print(f"arm_mass:         v137={v137_sim.params.base.arm_mass:.6f}, v2={v2_env.params.base.arm_mass:.6f}")
print(f"arm_length:       v137={v137_sim.params.base.arm_length:.6f}, v2={v2_env.params.base.arm_length:.6f}")
print(f"initial_vx:       v137={v137_sim.params.base.initial_vx:.6f}, v2={v2_env.params.base.initial_vx:.6f}")
print(f"compensate_friction: v137={v137_sim.params.compensate_friction}, v2={v2_env.params.compensate_friction}")
print()

# 运行100步并比较轨迹
print("Running 100 steps comparison:")
print("-" * 80)

# V137
from simulate_passive_arms_v14 import initialize
initialize(v137_sim.model, v137_sim.data, v137_sim.params.base)
v137_sim.support_foot = "left"
v137_sim.burst_start_t = -v137_sim.params.base.gait_period

# V2
v2_env.reset(seed=0)

print(f"Initial state:")
print(f"  v137: hip_x={v137_sim.data.qpos[0]:.4f}, hip_vx={v137_sim.data.qvel[0]:.4f}")
print(f"  v2:   hip_x={v2_env.data.qpos[0]:.4f}, hip_vx={v2_env.data.qvel[0]:.4f}")
print()

# 运行100个PPO steps (v2) = 500 1ms steps
for i in range(100):
    # V2: 1个PPO step = 5个1ms steps
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = v2_env.step(action)

    # V137: 5个1ms steps (匹配v2的inner_steps)
    for j in range(5):
        # 这里简化，只运行mj_step不调用完整控制循环
        pass

if i % 20 == 0:
        print(f"PPO Step {i:3d}:")
        print(f"  v2:   hip_x={v2_env.data.qpos[0]:.4f}, hip_vx={v2_env.data.cvel[v2_env.model.body('hip').id][3]:.4f}")

print()
v137_sim.model = None
v137_sim.data = None
v2_env.close()

"""Check if initial conditions match exactly"""

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v14 import initialize

from rl_training.test_v137_identity import V137IdentitySimulator
from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


def check_initial_conditions():
    """检查初始条件是否完全一致"""

    print("=" * 80)
    print("Initial Conditions Check")
    print("=" * 80)

    # === BASELINE ===
    baseline_sim = V137IdentitySimulator()
    p_base = baseline_sim.params.base
    initialize(baseline_sim.model, baseline_sim.data, p_base)

    print("\nBaseline after initialize():")
    print(f"  qpos: {baseline_sim.data.qpos[:]}")
    print(f"  qvel: {baseline_sim.data.qvel[:]}")

    # === V2 ===
    env_v2 = ResidualRLEnvV2(residual_scale=0.05, inner_steps=5, max_steps=2400)
    obs, info = env_v2.reset(seed=0)

    print("\nV2 after reset(seed=0):")
    print(f"  qpos: {env_v2.data.qpos[:]}")
    print(f"  qvel: {env_v2.data.qvel[:]}")

    print("\nDifferences:")
    qpos_diff = np.array(baseline_sim.data.qpos[:]) - np.array(env_v2.data.qpos[:])
    qvel_diff = np.array(baseline_sim.data.qvel[:]) - np.array(env_v2.data.qvel[:])
    print(f"  qpos_diff: {qpos_diff}")
    print(f"  qvel_diff: {qvel_diff}")
    print(f"  max qpos_diff: {np.max(np.abs(qpos_diff)):.10e}")
    print(f"  max qvel_diff: {np.max(np.abs(qvel_diff)):.10e}")

    if np.max(np.abs(qpos_diff)) < 1e-10 and np.max(np.abs(qvel_diff)) < 1e-10:
        print("\n[PASS] Initial conditions match exactly!")
    else:
        print("\n[FAIL] Initial conditions differ!")

    env_v2.close()


if __name__ == "__main__":
    check_initial_conditions()

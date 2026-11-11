# -*- coding: utf-8 -*-
"""
Smoke test for CompassGaitEnv.

Verifies (without needing stable_baselines3):
  1. Model loads from the real V13.7 XML.
  2. Joint/actuator/site/body names resolve correctly.
  3. Observation indexing reads the intended joints (no off-by-N bug).
  4. reset() / step() run and shapes match the declared spaces.
  5. All four reward functions produce finite scalars.

Run:
  D:\\Dunna\\Documents\\hw-1\\.venv-mujoco\\Scripts\\python.exe rl_training\\smoke_test_env.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import mujoco
from environment import CompassGaitEnv


def check(cond, msg):
    print(("[OK]  " if cond else "[FAIL] ") + msg)
    return bool(cond)


def main():
    ok = True

    # 1. Build env (loads real V13.7 model by default)
    env = CompassGaitEnv(reward_type="forward")
    ok &= check(env.model is not None, "model loaded from V13.7 XML")

    # 2. Indexing self-consistency: qposadr derived from jnt_qposadr must match
    #    a direct name lookup for each leg joint.
    expected = {}
    for name in env.joint_names:
        jid = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        expected[name] = int(env.model.jnt_qposadr[jid])
    derived = {
        env.joint_names[i]: env.joint_qposadr[i] for i in range(len(env.joint_names))
    }
    ok &= check(expected == derived, f"joint qpos addresses correct: {derived}")

    # left_hip must NOT alias to left_ankle (the old +2 bug)
    lh = env.joint_qposadr[env.joint_names.index("left_hip")]
    la = env.joint_qposadr[env.joint_names.index("left_ankle")]
    ok &= check(
        lh != la, f"left_hip addr {lh} != left_ankle addr {la} (off-by-N bug gone)"
    )

    # 3. reset + obs shape
    obs, info = env.reset(seed=0)
    ok &= check(
        obs.shape == env.observation_space.shape,
        f"obs shape {obs.shape} == space {env.observation_space.shape}",
    )
    ok &= check(np.all(np.isfinite(obs)), "initial obs is finite")

    # 4. Targeted indexing check: set a known angle on left_hip in qpos, read it back in obs
    env.reset(seed=0)
    lh_idx = env.joint_qposadr[env.joint_names.index("left_hip")]
    env.data.qpos[lh_idx] = 0.321  # rad
    mujoco.mj_forward(env.model, env.data)
    obs2 = env._get_obs()
    # obs layout: joint_angles[0:6] in order of joint_names; left_hip is index 0
    ok &= check(
        abs(obs2[0] - 0.321) < 1e-6,
        f"obs[0] reads left_hip angle back: {obs2[0]:.4f} (expected 0.321)",
    )

    # 5. step runs, shapes/flags valid
    env.reset(seed=1)
    a = env.action_space.sample()
    o, r, term, trunc, i = env.step(a)
    ok &= check(o.shape == env.observation_space.shape, "step obs shape ok")
    ok &= check(
        isinstance(float(r), float) and np.isfinite(r), f"step reward finite: {r:.4f}"
    )
    ok &= check(
        isinstance(term, bool) and isinstance(trunc, bool), "term/trunc are bool"
    )

    # 6. all reward functions finite
    for rt in ["forward", "energy_efficient", "limit_cycle", "imitation"]:
        e = CompassGaitEnv(reward_type=rt)
        e.reset(seed=2)
        rr = e._compute_reward(e.action_space.sample())
        ok &= check(np.isfinite(rr), f"reward '{rt}' finite: {rr:.4f}")
        e.close()

    env.close()
    print("\n[SUCCESS] all checks passed" if ok else "\n[FAILURE] some checks failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

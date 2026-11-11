# -*- coding: utf-8 -*-
"""
Short PPO pipeline smoke-train.

Goal: prove the full training loop works end-to-end (env -> PPO -> GPU ->
checkpoint -> reload) on a small budget. NOT meant to produce a good gait.

Run:
  .venv-mujoco\\Scripts\\python.exe rl_training\\quick_train_ppo.py --steps 20000
"""

import sys
import time
import argparse
from pathlib import Path

RL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RL_DIR))

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from environment import CompassGaitEnv


def make_env(reward_type, seed):
    def _init():
        env = CompassGaitEnv(reward_type=reward_type)
        env = Monitor(env)
        env.reset(seed=seed)
        return env

    return _init


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--n-envs", type=int, default=4)
    ap.add_argument("--reward", type=str, default="energy_efficient")
    ap.add_argument("--device", type=str, default="auto")
    args = ap.parse_args()

    out_dir = RL_DIR / "smoke_run"
    out_dir.mkdir(exist_ok=True)

    print(
        f"torch {torch.__version__} | cuda={torch.cuda.is_available()} "
        f"({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'})"
    )

    env = DummyVecEnv([make_env(args.reward, 100 + i) for i in range(args.n_envs)])

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        n_epochs=5,
        gamma=0.99,
        gae_lambda=0.95,
        verbose=1,
        device=args.device,
        seed=0,
        tensorboard_log=str(out_dir / "tb"),
    )
    print(f"PPO device: {model.device}")

    t0 = time.time()
    model.learn(total_timesteps=args.steps, progress_bar=False)
    dt = time.time() - t0
    print(f"\n[timing] {args.steps} steps in {dt:.1f}s = {args.steps/dt:.0f} steps/s")

    # Save + reload to prove serialization works
    mp = out_dir / "ppo_smoke"
    model.save(str(mp))
    reloaded = PPO.load(str(mp))
    print(f"[save/load] model saved to {mp}.zip and reloaded OK")

    # Quick deterministic rollout with the reloaded model
    test_env = CompassGaitEnv(reward_type=args.reward)
    obs, _ = test_env.reset(seed=999)
    ep_ret, steps = 0.0, 0
    max_hip_x = 0.0
    for _ in range(test_env.max_steps):
        a, _ = reloaded.predict(obs, deterministic=True)
        obs, r, term, trunc, info = test_env.step(a)
        ep_ret += r
        steps += 1
        max_hip_x = max(max_hip_x, info.get("hip_x", 0.0))
        if term or trunc:
            break
    test_env.close()
    print(f"[rollout] steps={steps} return={ep_ret:.2f} max_hip_x={max_hip_x:.3f} m")
    print("\n[SUCCESS] PPO pipeline works end-to-end")


if __name__ == "__main__":
    main()

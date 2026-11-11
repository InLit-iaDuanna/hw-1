"""Corrected Gamma/GAE training for ResidualRLEnvV2.

Based on GPT5_ANALYSIS_RESPONSE.md Priority 2:
- Fix gamma: 0.99 -> 0.9990 (5s critic horizon instead of 0.5s)
- Fix gae_lambda: 0.95 -> 0.997 (1.5s advantage horizon)
- Add target_kl for early stopping per update
- Reduce clip_range to prevent large policy jumps
- Add entropy bonus for exploration

This should eliminate the 150k/350k-style collapse by giving PPO
sufficient temporal context to avoid actions that cause delayed falls.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


@dataclass
class EvalResult:
    timestep: int
    mean_distance_m: float
    std_distance_m: float
    mean_reward: float
    success_rate: float
    failure_rate: float
    distances_m: list[float]
    mean_actual_action: list[float] | None = None
    std_actual_action: list[float] | None = None
    min_actual_action: list[float] | None = None
    max_actual_action: list[float] | None = None


class ResidualPriorWrapper(gym.ActionWrapper):
    """Map PPO delta actions to residual actions near a known good prior."""

    def __init__(
        self,
        env: gym.Env,
        prior_action: np.ndarray,
        delta_scale: float,
    ):
        super().__init__(env)
        self.prior_action = np.asarray(prior_action, dtype=np.float32)
        self.delta_scale = float(delta_scale)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        self.last_actual_action = self.prior_action.copy()

    def action(self, action: np.ndarray) -> np.ndarray:
        delta = np.asarray(action, dtype=np.float32)
        actual = np.clip(self.prior_action + self.delta_scale * delta, -1.0, 1.0)
        self.last_actual_action = actual.astype(np.float32)
        return self.last_actual_action


def make_env(
    residual_scale: float,
    inner_steps: int,
    max_steps: int,
    prior_action: np.ndarray,
    delta_scale: float,
    seed_offset: int,
):
    def _init():
        env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )
        env = ResidualPriorWrapper(
            env, prior_action=prior_action, delta_scale=delta_scale
        )
        env = Monitor(env)
        env.reset(seed=seed_offset)
        return env

    return _init


def evaluate_model(
    model: PPO,
    residual_scale: float,
    inner_steps: int,
    max_steps: int,
    prior_action: np.ndarray,
    delta_scale: float,
    episodes: int,
    timestep: int,
) -> EvalResult:
    distances: list[float] = []
    rewards: list[float] = []
    successes: list[bool] = []
    actual_actions: list[np.ndarray] = []

    for seed in range(episodes):
        env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )
        env_wrapped = ResidualPriorWrapper(
            env, prior_action=prior_action, delta_scale=delta_scale
        )
        obs, _ = env_wrapped.reset(seed=seed)
        terminated = False
        truncated = False
        total_reward = 0.0

        while not (terminated or truncated):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env_wrapped.step(action)
            total_reward += float(reward)
            actual_actions.append(env_wrapped.last_actual_action.copy())

        distances.append(float(info["episode_distance"]))
        rewards.append(total_reward)
        successes.append(bool(truncated and not terminated))
        env.close()

    success_rate = float(np.mean(successes))
    actual_actions_arr = np.array(actual_actions)

    return EvalResult(
        timestep=timestep,
        mean_distance_m=float(np.mean(distances)),
        std_distance_m=float(np.std(distances)),
        mean_reward=float(np.mean(rewards)),
        success_rate=success_rate,
        failure_rate=float(1.0 - success_rate),
        distances_m=distances,
        mean_actual_action=actual_actions_arr.mean(axis=0).tolist(),
        std_actual_action=actual_actions_arr.std(axis=0).tolist(),
        min_actual_action=actual_actions_arr.min(axis=0).tolist(),
        max_actual_action=actual_actions_arr.max(axis=0).tolist(),
    )


class DistanceEvalCallback(BaseCallback):
    def __init__(
        self,
        eval_freq: int,
        eval_episodes: int,
        residual_scale: float,
        inner_steps: int,
        max_steps: int,
        prior_action: np.ndarray,
        delta_scale: float,
        model_dir: Path,
        abort_failure_rate: float,
        verbose: int = 1,
    ):
        super().__init__(verbose=verbose)
        self.eval_freq = int(eval_freq)
        self.eval_episodes = int(eval_episodes)
        self.residual_scale = float(residual_scale)
        self.inner_steps = int(inner_steps)
        self.max_steps = int(max_steps)
        self.prior_action = np.asarray(prior_action, dtype=np.float32)
        self.delta_scale = float(delta_scale)
        self.model_dir = model_dir
        self.abort_failure_rate = float(abort_failure_rate)
        self.eval_results: list[EvalResult] = []
        self.best_distance = -np.inf
        self._last_eval_bucket = -1
        self.stop_reason = "completed"

    def _on_step(self) -> bool:
        bucket = self.num_timesteps // self.eval_freq
        if bucket <= self._last_eval_bucket or self.num_timesteps < self.eval_freq:
            return True

        self._last_eval_bucket = bucket
        result = evaluate_model(
            self.model,
            self.residual_scale,
            self.inner_steps,
            self.max_steps,
            self.prior_action,
            self.delta_scale,
            self.eval_episodes,
            self.num_timesteps,
        )
        self.eval_results.append(result)

        if result.mean_distance_m > self.best_distance:
            self.best_distance = result.mean_distance_m
            self.model.save(str(self.model_dir / "ppo_best"))

        if self.verbose:
            print()
            print("=" * 80)
            print(f"Evaluation at {self.num_timesteps} timesteps")
            print("=" * 80)
            print(
                f"distance: {result.mean_distance_m:.3f} +/- {result.std_distance_m:.3f} m"
            )
            print(f"success: {result.success_rate * 100:.0f}%")
            print(f"reward: {result.mean_reward:.3f}")
            print(f"best so far: {self.best_distance:.3f} m")
            print("=" * 80)

        if result.failure_rate > self.abort_failure_rate:
            print()
            print(
                f"ABORT: failure rate {result.failure_rate * 100:.0f}% > threshold {self.abort_failure_rate * 100:.0f}%"
            )
            self.stop_reason = "high_failure_rate"
            return False

        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timesteps", type=int, default=200000, help="Total timesteps (default 200k)"
    )
    parser.add_argument("--n-envs", type=int, default=8, help="Parallel envs")
    parser.add_argument(
        "--eval-freq", type=int, default=25000, help="Eval every N steps"
    )
    parser.add_argument(
        "--eval-episodes", type=int, default=10, help="Episodes per eval"
    )
    parser.add_argument(
        "--model-dir", type=str, default="models/residual_rl_v2_corrected"
    )
    parser.add_argument("--checkpoint-prefix", type=str, default="ppo_corrected")
    args = parser.parse_args()

    start_time = datetime.now()
    print("=" * 80)
    print("Corrected Gamma/GAE Training for ResidualRLEnvV2")
    print("=" * 80)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Environment config
    residual_scale = 0.2
    inner_steps = 5  # 200Hz PPO control
    max_steps = 2400  # 12 seconds
    prior_action = np.array([0.5, 1.0], dtype=np.float32)
    delta_scale = 0.3

    # Corrected time scales
    dt_control = inner_steps * 0.001  # 0.005s per PPO step
    tau_return = 5.0  # Critic should see 5 seconds ahead
    tau_gae = 1.5  # Advantage should see 1.5 seconds ahead

    gamma = math.exp(-dt_control / tau_return)
    gae_lambda_raw = math.exp(-dt_control / tau_gae) / gamma
    gae_lambda = min(0.999, max(0.95, gae_lambda_raw))

    print("## Corrected Hyperparameters")
    print(f"dt_control: {dt_control:.6f}s (PPO acts every {dt_control*1000:.1f}ms)")
    print(f"tau_return: {tau_return:.1f}s (critic horizon)")
    print(f"tau_gae: {tau_gae:.1f}s (advantage horizon)")
    print(f"gamma: {gamma:.6f} (was 0.99)")
    print(f"gae_lambda: {gae_lambda:.6f} (was 0.95)")
    print()

    print("## Other Adjustments")
    print("learning_rate: 3e-5 (reduced from 1e-4)")
    print("n_epochs: 3 (reduced from 5)")
    print("clip_range: 0.05 (reduced from 0.2)")
    print("ent_coef: 0.001 (enabled, was 0.0)")
    print("target_kl: 0.003 (enabled, was None)")
    print()

    # Create environments
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    vec_env = DummyVecEnv(
        [
            make_env(
                residual_scale, inner_steps, max_steps, prior_action, delta_scale, i
            )
            for i in range(args.n_envs)
        ]
    )

    # Create PPO model with corrected hyperparameters
    model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=3e-5,
        n_steps=4096,
        batch_size=2048,
        n_epochs=3,
        gamma=gamma,  # Corrected
        gae_lambda=gae_lambda,  # Corrected
        clip_range=0.05,  # Reduced
        ent_coef=0.001,  # Enabled
        vf_coef=0.7,
        max_grad_norm=0.3,
        target_kl=0.003,  # Enabled
        verbose=1,
        device="auto",
    )

    print("## Training Setup")
    print(f"Total timesteps: {args.timesteps:,}")
    print(f"Parallel envs: {args.n_envs}")
    print(f"Eval frequency: {args.eval_freq:,} steps")
    print(f"Eval episodes: {args.eval_episodes}")
    print(f"Model dir: {model_dir}")
    print()

    # Callbacks
    eval_callback = DistanceEvalCallback(
        eval_freq=args.eval_freq,
        eval_episodes=args.eval_episodes,
        residual_scale=residual_scale,
        inner_steps=inner_steps,
        max_steps=max_steps,
        prior_action=prior_action,
        delta_scale=delta_scale,
        model_dir=model_dir,
        abort_failure_rate=0.3,
        verbose=1,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=args.eval_freq,
        save_path=str(model_dir / "checkpoints"),
        name_prefix=args.checkpoint_prefix,
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    # Train
    print("=" * 80)
    print("Starting training...")
    print("=" * 80)
    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=False,
    )

    # Save final model
    model.save(str(model_dir / "ppo_final"))
    print(f"\n[OK] Final model saved to {model_dir / 'ppo_final.zip'}")

    # Final evaluation
    print("\n" + "=" * 80)
    print("Final Evaluation")
    print("=" * 80)
    final_result = evaluate_model(
        model,
        residual_scale,
        inner_steps,
        max_steps,
        prior_action,
        delta_scale,
        args.eval_episodes,
        args.timesteps,
    )
    print(
        f"Distance: {final_result.mean_distance_m:.3f} +/- {final_result.std_distance_m:.3f} m"
    )
    print(f"Success rate: {final_result.success_rate * 100:.0f}%")
    print(f"Reward: {final_result.mean_reward:.3f}")

    # Save report
    end_time = datetime.now()
    duration = end_time - start_time

    report = {
        "timestamp": end_time.isoformat(),
        "duration_seconds": duration.total_seconds(),
        "config": {
            "timesteps": args.timesteps,
            "n_envs": args.n_envs,
            "residual_scale": residual_scale,
            "inner_steps": inner_steps,
            "max_steps": max_steps,
            "prior_action": prior_action.tolist(),
            "delta_scale": delta_scale,
        },
        "corrected_hyperparameters": {
            "dt_control": dt_control,
            "tau_return": tau_return,
            "tau_gae": tau_gae,
            "gamma": gamma,
            "gae_lambda": gae_lambda,
            "learning_rate": 3e-5,
            "n_epochs": 3,
            "clip_range": 0.05,
            "ent_coef": 0.001,
            "target_kl": 0.003,
        },
        "eval_history": [asdict(r) for r in eval_callback.eval_results],
        "final_eval": asdict(final_result),
        "best_distance": eval_callback.best_distance,
        "stop_reason": eval_callback.stop_reason,
        "baseline_comparison": {
            "100k_uncorrected": 4.779,
            "constant_best": 4.973,
            "final_corrected": final_result.mean_distance_m,
            "improvement_vs_100k": final_result.mean_distance_m - 4.779,
            "improvement_vs_constant": final_result.mean_distance_m - 4.973,
        },
    }

    report_path = (
        HW1_ROOT / "logs" / "residual_rl_v2" / "train_corrected_gamma_report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[OK] Report saved to {report_path}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Duration: {int(duration.total_seconds() // 60)} minutes")
    print(f"Best distance: {eval_callback.best_distance:.3f}m")
    print(f"Final distance: {final_result.mean_distance_m:.3f}m")
    print(f"Success rate: {final_result.success_rate * 100:.0f}%")
    print()
    print("Comparison:")
    print("  100k uncorrected: 4.779m")
    print("  Constant best:    4.973m")
    print(f"  Corrected final:  {final_result.mean_distance_m:.3f}m")
    print()
    if final_result.mean_distance_m > 4.973:
        print("[SUCCESS] Corrected training surpassed constant baseline!")
    elif final_result.mean_distance_m > 4.779:
        print("[IMPROVEMENT] Better than 100k, but not yet surpassing constant.")
    else:
        print("[FAILURE] Corrected training did not improve over 100k.")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""Prior-guided 100k PPO sanity run for ResidualRLEnvV2.

The environment itself remains identity-safe: action [0, 0] is zero residual.
This script trains PPO on a small delta around a sweep-discovered residual prior,
so exploration starts from a stable improvement direction instead of random
full-range hip torques.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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
        env = ResidualPriorWrapper(env, prior_action=prior_action, delta_scale=delta_scale)
        env = Monitor(env)
        env.reset(seed=seed_offset)
        return env

    return _init


def run_fixed_action(
    action: np.ndarray,
    residual_scale: float,
    inner_steps: int,
    max_steps: int,
    episodes: int,
) -> EvalResult:
    distances: list[float] = []
    rewards: list[float] = []
    successes: list[bool] = []

    for seed in range(episodes):
        env = ResidualRLEnvV2(
            residual_scale=residual_scale,
            inner_steps=inner_steps,
            max_steps=max_steps,
        )
        obs, _ = env.reset(seed=seed)
        terminated = False
        truncated = False
        total_reward = 0.0

        while not (terminated or truncated):
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += float(reward)

        distances.append(float(info["episode_distance"]))
        rewards.append(total_reward)
        successes.append(bool(truncated and not terminated))
        env.close()

    success_rate = float(np.mean(successes))
    return EvalResult(
        timestep=0,
        mean_distance_m=float(np.mean(distances)),
        std_distance_m=float(np.std(distances)),
        mean_reward=float(np.mean(rewards)),
        success_rate=success_rate,
        failure_rate=float(1.0 - success_rate),
        distances_m=distances,
    )


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
        env = ResidualPriorWrapper(
            ResidualRLEnvV2(
                residual_scale=residual_scale,
                inner_steps=inner_steps,
                max_steps=max_steps,
            ),
            prior_action=prior_action,
            delta_scale=delta_scale,
        )
        obs, _ = env.reset(seed=seed)
        terminated = False
        truncated = False
        total_reward = 0.0

        while not (terminated or truncated):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            actual_actions.append(env.last_actual_action.copy())
            total_reward += float(reward)

        distances.append(float(info["episode_distance"]))
        rewards.append(total_reward)
        successes.append(bool(truncated and not terminated))
        env.close()

    success_rate = float(np.mean(successes))
    action_array = np.asarray(actual_actions, dtype=np.float32)
    return EvalResult(
        timestep=int(timestep),
        mean_distance_m=float(np.mean(distances)),
        std_distance_m=float(np.std(distances)),
        mean_reward=float(np.mean(rewards)),
        success_rate=success_rate,
        failure_rate=float(1.0 - success_rate),
        distances_m=distances,
        mean_actual_action=action_array.mean(axis=0).tolist() if action_array.size else None,
        std_actual_action=action_array.std(axis=0).tolist() if action_array.size else None,
        min_actual_action=action_array.min(axis=0).tolist() if action_array.size else None,
        max_actual_action=action_array.max(axis=0).tolist() if action_array.size else None,
    )


def resolve_output_path(value: str | None, default: Path) -> Path:
    if value is None:
        return default

    path = Path(value)
    if not path.is_absolute():
        path = HW1_ROOT / path
    return path


def improvement_pct(distance_m: float, baseline_m: float) -> float:
    if baseline_m == 0.0:
        return 0.0
    return float((distance_m - baseline_m) / baseline_m * 100.0)


def format_improvement(value: float) -> str:
    return f"{value:+.2f}%"


def dedupe_eval_results(results: list[EvalResult]) -> list[EvalResult]:
    ordered: dict[int, EvalResult] = {}
    for result in results:
        ordered[int(result.timestep)] = result
    return [ordered[timestep] for timestep in sorted(ordered)]


def is_monotonic_after(results: list[EvalResult], timestep: int) -> bool:
    filtered = [item.mean_distance_m for item in results if item.timestep >= timestep]
    return all(curr >= prev for prev, curr in zip(filtered, filtered[1:]))


def build_diagnosis(
    final_eval: EvalResult,
    training_completed: bool,
    target_distance_m: float,
    nice_target_distance_m: float,
) -> str:
    must_have = (
        training_completed
        and final_eval.mean_distance_m > target_distance_m
        and final_eval.success_rate == 1.0
        and final_eval.failure_rate == 0.0
    )
    if not must_have:
        return "FAIL"

    if final_eval.mean_distance_m > nice_target_distance_m and final_eval.std_distance_m < 0.05:
        return "PASS"

    return "CONDITIONAL_PASS"


def format_checkpoint_line(result: dict[str, Any]) -> str:
    return (
        f"- {result['timestep'] // 1000}k: "
        f"mean={result['mean_distance_m']:.3f}m, "
        f"std={result['std_distance_m']:.3f}m, "
        f"success={result['success_rate'] * 100:.0f}%"
    )


def write_task_log(
    summary: dict[str, Any],
    path: Path,
    command_text: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    duration = end_time - start_time
    total_minutes = int(duration.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    final_eval = summary["final_eval"]
    final_label = (
        "Final 500k"
        if summary["training_completed"]
        else f"Final attempt ({final_eval['timestep'] // 1000}k)"
    )
    baseline = summary["baseline"]["mean_distance_m"]
    best_checkpoint = summary["best_checkpoint"]
    checks = {
        "Training completes without errors": summary["training_completed"],
        "Final distance > 5.0m": final_eval["mean_distance_m"] > summary["nice_target_distance_m"],
        "Final distance > sweep best (4.973m)": final_eval["mean_distance_m"] > summary["target_distance_m"],
        "Success rate = 100%": final_eval["success_rate"] == 1.0,
        "Convergence quality: monotonic after 300k, stable std": (
            summary["convergence_quality"]["monotonic_after_300k"]
            and summary["convergence_quality"]["final_std_m"] < 0.05
        ),
        "Model files saved": summary["artifacts"]["best_model_exists"]
        and summary["artifacts"]["final_model_exists"],
    }

    lines = [
        "# Task 4: 500K PPO Training",
        "",
        "## Command",
        command_text,
        "",
        "## Execution Start",
        f"Timestamp: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Progress Checkpoints",
        *[format_checkpoint_line(item) for item in summary["eval_history"]],
        "",
        "## Execution End",
        f"Timestamp: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Duration: {hours} hours {minutes} minutes",
        "",
        "## Key Metrics",
        f"- Baseline: {baseline:.3f}m",
        f"- Sweep best: {summary['sweep_best']['mean_distance_m']:.3f}m "
        f"({format_improvement(summary['sweep_best']['improvement_pct'])})",
        f"- Sanity 100k: {summary['sanity_100k']['mean_distance_m']:.3f}m "
        f"({format_improvement(summary['sanity_100k']['improvement_pct'])})",
        f"- {final_label}: {final_eval['mean_distance_m']:.3f}m "
        f"({format_improvement(improvement_pct(final_eval['mean_distance_m'], baseline))})",
        f"- Best checkpoint: {best_checkpoint['mean_distance_m']:.3f}m "
        f"at {best_checkpoint['timestep'] // 1000}k steps",
        "",
        "## Acceptance Check",
        *[f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items()],
        "",
        "## Diagnosis",
        summary["diagnosis"],
        "",
        "## Notes",
        f"- Stop reason: {summary['stop_reason']}",
        f"- Final action mean: {final_eval.get('mean_actual_action')}",
        f"- Final action range: min={final_eval.get('min_actual_action')}, "
        f"max={final_eval.get('max_actual_action')}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_analysis(summary: dict[str, Any], path: Path) -> None:
    eval_history = summary["eval_history"]
    target = summary["target_distance_m"]
    final_eval = summary["final_eval"]
    baseline = summary["baseline"]["mean_distance_m"]
    final_label = (
        "500k PPO"
        if summary["training_completed"]
        else f"aborted {final_eval['timestep'] // 1000}k PPO attempt"
    )
    surpass = next((item for item in eval_history if item["mean_distance_m"] > target), None)
    best = summary["best_checkpoint"]
    last_three = eval_history[-3:]
    oscillation = max((item["mean_distance_m"] for item in last_three), default=0.0) - min(
        (item["mean_distance_m"] for item in last_three), default=0.0
    )

    if surpass is None:
        surpass_text = "The policy did not surpass the sweep best during recorded checkpoints."
    else:
        surpass_text = (
            f"The policy first surpassed the sweep best at {surpass['timestep'] // 1000}k "
            f"steps with {surpass['mean_distance_m']:.3f}m."
        )

    action_mean = final_eval.get("mean_actual_action")
    action_std = final_eval.get("std_actual_action")
    action_min = final_eval.get("min_actual_action")
    action_max = final_eval.get("max_actual_action")

    lines = [
        "# Residual RL V2 500k Analysis",
        "",
        "## Learning Curve",
        *[format_checkpoint_line(item) for item in eval_history],
        "",
        "## Convergence Analysis",
        f"- {surpass_text}",
        f"- Best checkpoint: {best['mean_distance_m']:.3f}m at {best['timestep'] // 1000}k steps.",
        f"- Final checkpoint: {final_eval['mean_distance_m']:.3f}m "
        f"({format_improvement(improvement_pct(final_eval['mean_distance_m'], baseline))} vs baseline).",
        f"- Last-three-checkpoint oscillation: {oscillation:.3f}m.",
        f"- Monotonic after 300k: {summary['convergence_quality']['monotonic_after_300k']}.",
        "",
        "## Action Distribution Analysis",
        f"- Prior action: {summary['prior_action']}; delta scale: {summary['delta_scale']}.",
        f"- Final actual action mean: {action_mean}.",
        f"- Final actual action std: {action_std}.",
        f"- Final actual action range: min={action_min}, max={action_max}.",
        "",
        "## Comparison With 100k Run",
        f"- 100k PPO: {summary['sanity_100k']['mean_distance_m']:.3f}m "
        f"({format_improvement(summary['sanity_100k']['improvement_pct'])}).",
        f"- {final_label}: {final_eval['mean_distance_m']:.3f}m "
        f"({format_improvement(improvement_pct(final_eval['mean_distance_m'], baseline))}).",
        f"- Extra 400k-step gain: "
        f"{final_eval['mean_distance_m'] - summary['sanity_100k']['mean_distance_m']:.3f}m.",
        "",
        "## Diagnosis",
        summary["diagnosis"],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(summary: dict[str, Any], path: Path) -> None:
    final_eval = summary["final_eval"]
    baseline = summary["baseline"]["mean_distance_m"]
    final_improvement = improvement_pct(final_eval["mean_distance_m"], baseline)
    now = datetime.now().strftime("%Y-%m-%d %H:%M +08:00")
    phase = "500k training complete" if summary["training_completed"] else "500k training aborted"
    status_label = "COMPLETED" if summary["diagnosis"] in {"PASS", "CONDITIONAL_PASS"} else "FAILED"
    status = f"""# ResidualRLV2 Implementation Status

**Last Updated**: {now}
**Phase**: {phase}

## Current Status

{status_label}
- [x] Full `ResidualRLEnvV2` timing fixed.
- [x] 42-dim observation verified.
- [x] Hip-only 2-dim action mapping verified.
- [x] Baseline-relative reward verified.
- [x] Zero residual identity test passed: `4.630276m`, `100%` success over 10 episodes.
- [x] Residual sweep passed: best path `residual_scale=0.20`, action `[0.50, 1.00]`, distance `4.972583m`, `+7.39%`.
- [x] 100k prior-guided PPO sanity training passed: final distance `4.898271m`, `100%` success.
- [{'x' if summary['diagnosis'] in {'PASS', 'CONDITIONAL_PASS'} else ' '}] 500k full training {summary['diagnosis']}: `{final_eval['mean_distance_m']:.6f}m`, `{format_improvement(final_improvement)}`, stop reason `{summary['stop_reason']}`.

## Performance

| Metric | Baseline | Sweep Best | 100k PPO | 500k PPO |
|--------|----------|------------|----------|----------|
| Distance (12s) | {baseline:.6f}m | {summary['sweep_best']['mean_distance_m']:.6f}m | {summary['sanity_100k']['mean_distance_m']:.6f}m | {final_eval['mean_distance_m']:.6f}m |
| Improvement | +0.00% | {format_improvement(summary['sweep_best']['improvement_pct'])} | {format_improvement(summary['sanity_100k']['improvement_pct'])} | {format_improvement(final_improvement)} |
| Success Rate | 100% | 100% | 100% | {final_eval['success_rate'] * 100:.0f}% |

## Key Artifacts

- Environment: `rl_training/train_residual_rl_v2.py`
- Training script: `rl_training/train_sanity_100k.py`
- 500k model: `models/residual_rl_v2_500k/ppo_best.zip`
- 500k final model: `models/residual_rl_v2_500k/ppo_final.zip`
- 500k report: `logs/residual_rl_v2/train_500k_report.json`
- 500k task log: `logs/residual_rl_v2/task4_500k_training.log`
- 500k analysis: `logs/residual_rl_v2/500k_analysis.md`

---
*Updated by: Codex*
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status, encoding="utf-8")


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
            print(f"distance: {result.mean_distance_m:.3f} +/- {result.std_distance_m:.3f} m")
            print(f"reward:   {result.mean_reward:.2f}")
            print(f"success:  {result.success_rate * 100:.0f}%")
            print("=" * 80)

        if result.failure_rate > self.abort_failure_rate:
            self.stop_reason = (
                f"aborted: failure_rate {result.failure_rate:.3f} "
                f"exceeded {self.abort_failure_rate:.3f}"
            )
            return False

        return True


def train(args: argparse.Namespace) -> dict[str, Any]:
    start_time = datetime.now()
    log_dir = HW1_ROOT / "logs" / "residual_rl_v2"
    model_dir = resolve_output_path(
        args.model_dir,
        HW1_ROOT / "models" / "residual_rl_v2_sanity",
    )
    report_path = resolve_output_path(
        args.report_path,
        log_dir / "train_sanity_100k_report.json",
    )
    task_log_path = resolve_output_path(args.task_log_path, log_dir / "task4_500k_training.log")
    analysis_path = resolve_output_path(args.analysis_path, log_dir / "500k_analysis.md")
    status_path = resolve_output_path(args.status_path, log_dir / "STATUS.txt")
    checkpoint_dir = model_dir / "checkpoints"
    tensorboard_dir = log_dir / "tensorboard"
    for path in [log_dir, model_dir, checkpoint_dir, tensorboard_dir, report_path.parent]:
        path.mkdir(parents=True, exist_ok=True)

    prior_action = np.array([args.prior_left, args.prior_right], dtype=np.float32)
    zero_action = np.zeros(2, dtype=np.float32)

    print("=" * 80)
    print("Prior-guided ResidualRLEnvV2 PPO sanity training")
    print("=" * 80)
    print(f"timesteps: {args.timesteps}")
    print(f"n_envs: {args.n_envs}")
    print(f"residual_scale: {args.residual_scale}")
    print(f"prior_action: {prior_action.tolist()}")
    print(f"delta_scale: {args.delta_scale}")
    print(f"horizon: {args.max_steps * args.inner_steps * 0.001:.3f}s")
    print(f"model_dir: {model_dir}")
    print(f"report_path: {report_path}")

    baseline = run_fixed_action(
        zero_action,
        args.residual_scale,
        args.inner_steps,
        args.max_steps,
        args.eval_episodes,
    )
    prior_eval = run_fixed_action(
        prior_action,
        args.residual_scale,
        args.inner_steps,
        args.max_steps,
        args.eval_episodes,
    )
    threshold = baseline.mean_distance_m + args.pass_margin_m

    print()
    print(f"zero residual baseline: {baseline.mean_distance_m:.3f}m")
    print(f"sweep prior distance:   {prior_eval.mean_distance_m:.3f}m")
    print(f"pass threshold:         {threshold:.3f}m")
    print()

    env = DummyVecEnv(
        [
            make_env(
                args.residual_scale,
                args.inner_steps,
                args.max_steps,
                prior_action,
                args.delta_scale,
                args.seed + rank,
            )
            for rank in range(args.n_envs)
        ]
    )

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=args.ent_coef,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=str(tensorboard_dir),
        seed=args.seed,
        device=args.device,
    )

    eval_callback = DistanceEvalCallback(
        eval_freq=args.eval_freq,
        eval_episodes=args.eval_episodes,
        residual_scale=args.residual_scale,
        inner_steps=args.inner_steps,
        max_steps=args.max_steps,
        prior_action=prior_action,
        delta_scale=args.delta_scale,
        model_dir=model_dir,
        abort_failure_rate=args.abort_failure_rate,
        verbose=1,
    )
    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.eval_freq // args.n_envs, 1),
        save_path=str(checkpoint_dir),
        name_prefix=args.checkpoint_prefix,
    )

    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=False,
    )

    completed_timesteps = int(model.num_timesteps)
    training_completed = eval_callback.stop_reason == "completed" and completed_timesteps >= args.timesteps
    final_timestep = args.timesteps if training_completed else completed_timesteps
    final_eval = evaluate_model(
        model,
        args.residual_scale,
        args.inner_steps,
        args.max_steps,
        prior_action,
        args.delta_scale,
        args.eval_episodes,
        final_timestep,
    )
    eval_callback.eval_results.append(final_eval)
    eval_callback.eval_results = dedupe_eval_results(eval_callback.eval_results)

    if final_eval.mean_distance_m > eval_callback.best_distance:
        eval_callback.best_distance = final_eval.mean_distance_m
        model.save(str(model_dir / "ppo_best"))

    model.save(str(model_dir / "ppo_final"))
    env.close()

    eval_history = dedupe_eval_results(eval_callback.eval_results)
    best_eval = max(eval_history, key=lambda item: item.mean_distance_m)
    final_eval_dict = asdict(final_eval)
    diagnosis = build_diagnosis(
        final_eval,
        training_completed,
        args.target_distance_m,
        args.nice_target_distance_m,
    )
    best_model_path = model_dir / "ppo_best.zip"
    final_model_path = model_dir / "ppo_final.zip"
    checkpoint_files = sorted(checkpoint_dir.glob(f"{args.checkpoint_prefix}_*_steps.zip"))
    convergence_quality = {
        "monotonic_after_300k": is_monotonic_after(eval_history, 300000),
        "final_std_m": final_eval.std_distance_m,
        "catastrophic_forgetting": any(
            item.timestep >= 300000 and item.mean_distance_m < args.sanity_distance_m
            for item in eval_history
        ),
    }

    summary: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "diagnosis": diagnosis,
        "timesteps": args.timesteps,
        "completed_timesteps": completed_timesteps,
        "training_completed": training_completed,
        "stop_reason": eval_callback.stop_reason,
        "residual_scale": args.residual_scale,
        "prior_action": prior_action.tolist(),
        "delta_scale": args.delta_scale,
        "horizon_s": args.max_steps * args.inner_steps * 0.001,
        "baseline": asdict(baseline),
        "sweep_best": {
            "mean_distance_m": args.target_distance_m,
            "improvement_pct": improvement_pct(args.target_distance_m, baseline.mean_distance_m),
        },
        "sanity_100k": {
            "mean_distance_m": args.sanity_distance_m,
            "improvement_pct": improvement_pct(args.sanity_distance_m, baseline.mean_distance_m),
        },
        "prior_eval": asdict(prior_eval),
        "pass_threshold_m": threshold,
        "target_distance_m": args.target_distance_m,
        "nice_target_distance_m": args.nice_target_distance_m,
        "abort_failure_rate": args.abort_failure_rate,
        "final_eval": final_eval_dict,
        "eval_history": [asdict(item) for item in eval_history],
        "best_checkpoint": {
            "timestep": best_eval.timestep,
            "mean_distance_m": best_eval.mean_distance_m,
            "improvement_pct": improvement_pct(best_eval.mean_distance_m, baseline.mean_distance_m),
        },
        "convergence_quality": convergence_quality,
        "artifacts": {
            "best_model_exists": best_model_path.exists() and best_model_path.stat().st_size > 100_000,
            "final_model_exists": final_model_path.exists() and final_model_path.stat().st_size > 100_000,
            "checkpoint_count": len(checkpoint_files),
            "checkpoints": [str(path) for path in checkpoint_files],
        },
        "model_dir": str(model_dir),
        "tensorboard_dir": str(tensorboard_dir),
    }

    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    end_time = datetime.now()

    command_text = f"{sys.executable} {' '.join(sys.argv)}"
    if args.task_log_path is not None:
        write_task_log(summary, task_log_path, command_text, start_time, end_time)
    if args.analysis_path is not None:
        write_analysis(summary, analysis_path)
    if args.status_path is not None:
        write_status(summary, status_path)

    print()
    print("=" * 80)
    print("Final evaluation")
    print("=" * 80)
    print(f"diagnosis: {diagnosis}")
    print(f"distance:  {final_eval.mean_distance_m:.3f} +/- {final_eval.std_distance_m:.3f} m")
    print(f"success:   {final_eval.success_rate * 100:.0f}%")
    print(f"saved:     {report_path}")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, default=100000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--inner-steps", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=2400)
    parser.add_argument("--residual-scale", type=float, default=0.20)
    parser.add_argument("--prior-left", type=float, default=0.5)
    parser.add_argument("--prior-right", type=float, default=1.0)
    parser.add_argument("--delta-scale", type=float, default=0.02)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--n-steps", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--n-epochs", type=int, default=5)
    parser.add_argument("--ent-coef", type=float, default=0.0)
    parser.add_argument("--eval-freq", type=int, default=25000)
    parser.add_argument("--eval-episodes", type=int, default=5)
    parser.add_argument("--pass-margin-m", type=float, default=0.20)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--checkpoint-prefix", default="ppo_sanity")
    parser.add_argument("--target-distance-m", type=float, default=4.972583)
    parser.add_argument("--nice-target-distance-m", type=float, default=5.0)
    parser.add_argument("--sanity-distance-m", type=float, default=4.898271)
    parser.add_argument("--abort-failure-rate", type=float, default=0.05)
    parser.add_argument("--task-log-path", default=None)
    parser.add_argument("--analysis-path", default=None)
    parser.add_argument("--status-path", default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    summary = train(args)
    return 0 if summary["diagnosis"] in {"PASS", "CONDITIONAL_PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

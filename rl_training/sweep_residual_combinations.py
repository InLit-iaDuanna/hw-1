"""Sweep ResidualRLEnvV2 hip residual directions.

The action is normalized in [-1, 1]. The actual torque residual is
`residual_scale * action` for the two hip joints; knee residuals stay zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_residual_rl_v2 import ResidualRLEnvV2

BASELINE_DISTANCE_12S = 4.63027587315918


@dataclass
class SweepResult:
    strategy: str
    residual_scale: float
    left_action: float
    right_action: float
    left_residual_nm: float
    right_residual_nm: float
    mean_distance_m: float
    std_distance_m: float
    mean_reward: float
    success_rate: float
    failure_rate: float
    improvement_pct: float
    episodes: int


def run_policy(
    residual_scale: float,
    policy_fn: Callable[[ResidualRLEnvV2], np.ndarray],
    episodes: int,
    inner_steps: int,
    max_steps: int,
) -> tuple[list[float], list[float], list[bool]]:
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
            action = np.asarray(policy_fn(env), dtype=np.float32)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += float(reward)

        distances.append(float(info["episode_distance"]))
        rewards.append(total_reward)
        successes.append(bool(truncated and not terminated))
        env.close()

    return distances, rewards, successes


def run_policy_on_env(
    env: ResidualRLEnvV2,
    policy_fn: Callable[[ResidualRLEnvV2], np.ndarray],
    episodes: int,
) -> tuple[list[float], list[float], list[bool]]:
    distances: list[float] = []
    rewards: list[float] = []
    successes: list[bool] = []

    for seed in range(episodes):
        obs, _ = env.reset(seed=seed)
        terminated = False
        truncated = False
        total_reward = 0.0

        while not (terminated or truncated):
            action = np.asarray(policy_fn(env), dtype=np.float32)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += float(reward)

        distances.append(float(info["episode_distance"]))
        rewards.append(total_reward)
        successes.append(bool(truncated and not terminated))

    return distances, rewards, successes


def constant_policy(
    left_action: float, right_action: float
) -> Callable[[ResidualRLEnvV2], np.ndarray]:
    def _policy(env: ResidualRLEnvV2) -> np.ndarray:
        return np.array([left_action, right_action], dtype=np.float32)

    return _policy


def phase_policy(
    joint: str, phase: int, action_value: float
) -> Callable[[ResidualRLEnvV2], np.ndarray]:
    def _policy(env: ResidualRLEnvV2) -> np.ndarray:
        action = np.zeros(2, dtype=np.float32)
        phase_now = env._get_phase(joint)
        if phase_now == phase:
            action[0 if joint == "left" else 1] = action_value
        return action

    return _policy


def summarize(
    strategy: str,
    residual_scale: float,
    left_action: float,
    right_action: float,
    distances: list[float],
    rewards: list[float],
    successes: list[bool],
) -> SweepResult:
    mean_distance = float(np.mean(distances))
    success_rate = float(np.mean(successes))
    return SweepResult(
        strategy=strategy,
        residual_scale=float(residual_scale),
        left_action=float(left_action),
        right_action=float(right_action),
        left_residual_nm=float(residual_scale * left_action),
        right_residual_nm=float(residual_scale * right_action),
        mean_distance_m=mean_distance,
        std_distance_m=float(np.std(distances)),
        mean_reward=float(np.mean(rewards)),
        success_rate=success_rate,
        failure_rate=float(1.0 - success_rate),
        improvement_pct=float((mean_distance / BASELINE_DISTANCE_12S - 1.0) * 100.0),
        episodes=len(distances),
    )


def run_sweep(args: argparse.Namespace) -> dict:
    scales = [float(x) for x in args.scales.split(",")]
    action_values = [float(x) for x in args.actions.split(",")]

    results: list[SweepResult] = []

    print("=" * 80)
    print("ResidualRLEnvV2 sweep")
    print("=" * 80)
    print(f"episodes/config: {args.episodes}")
    print(f"horizon: {args.max_steps * args.inner_steps * 0.001:.3f}s")
    print(f"baseline: {BASELINE_DISTANCE_12S:.6f}m")
    print()

    for scale in scales:
        env = ResidualRLEnvV2(
            residual_scale=scale,
            inner_steps=args.inner_steps,
            max_steps=args.max_steps,
        )
        try:
            for left_action in action_values:
                for right_action in action_values:
                    distances, rewards, successes = run_policy_on_env(
                        env,
                        constant_policy(left_action, right_action),
                        args.episodes,
                    )
                    result = summarize(
                        "constant",
                        scale,
                        left_action,
                        right_action,
                        distances,
                        rewards,
                        successes,
                    )
                    results.append(result)
                    print(
                        f"scale={scale:.3f} action=[{left_action:+.2f},{right_action:+.2f}] "
                        f"distance={result.mean_distance_m:.3f}m "
                        f"improvement={result.improvement_pct:+.2f}% "
                        f"success={result.success_rate * 100:.0f}%"
                    )
        finally:
            env.close()

    if args.include_phase:
        for scale in scales:
            env = ResidualRLEnvV2(
                residual_scale=scale,
                inner_steps=args.inner_steps,
                max_steps=args.max_steps,
            )
            try:
                for action_value in [0.5, 1.0, -0.5, -1.0]:
                    for joint in ["left", "right"]:
                        for phase in range(4):
                            distances, rewards, successes = run_policy_on_env(
                                env,
                                phase_policy(joint, phase, action_value),
                                args.episodes,
                            )
                            left_action = action_value if joint == "left" else 0.0
                            right_action = action_value if joint == "right" else 0.0
                            result = summarize(
                                f"{joint}_phase_{phase}",
                                scale,
                                left_action,
                                right_action,
                                distances,
                                rewards,
                                successes,
                            )
                            results.append(result)
                            print(
                                f"scale={scale:.3f} {joint}@phase{phase}={action_value:+.2f} "
                                f"distance={result.mean_distance_m:.3f}m "
                                f"improvement={result.improvement_pct:+.2f}% "
                                f"success={result.success_rate * 100:.0f}%"
                            )
            finally:
                env.close()

    results_sorted = sorted(
        results, key=lambda item: item.mean_distance_m, reverse=True
    )
    good_results = [
        item
        for item in results_sorted
        if item.improvement_pct >= args.pass_improvement_pct
        and item.success_rate == 1.0
    ]

    print()
    print("Top configurations")
    print("-" * 80)
    for idx, item in enumerate(results_sorted[:10], 1):
        print(
            f"{idx:2d}. {item.strategy:<14} scale={item.residual_scale:.3f} "
            f"action=[{item.left_action:+.2f},{item.right_action:+.2f}] "
            f"torque=[{item.left_residual_nm:+.3f},{item.right_residual_nm:+.3f}]Nm "
            f"distance={item.mean_distance_m:.3f}m "
            f"improvement={item.improvement_pct:+.2f}%"
        )

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "baseline_distance_m": BASELINE_DISTANCE_12S,
        "pass_improvement_pct": args.pass_improvement_pct,
        "diagnosis": "PASS" if good_results else "PARTIAL",
        "best_result": asdict(results_sorted[0]),
        "num_results": len(results_sorted),
        "num_good_results": len(good_results),
        "all_results": [asdict(item) for item in results_sorted],
    }

    output_path = HW1_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print(f"Saved JSON results to: {output_path}")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--inner-steps", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=2400)
    parser.add_argument("--scales", default="0.05,0.10,0.15,0.20")
    parser.add_argument("--actions", default="-1.0,-0.5,0.0,0.5,1.0")
    parser.add_argument("--include-phase", action="store_true")
    parser.add_argument("--pass-improvement-pct", type=float, default=3.0)
    parser.add_argument(
        "--output",
        default="logs/residual_rl_v2/residual_sweep_results.json",
    )
    args = parser.parse_args()

    summary = run_sweep(args)
    return 0 if summary["diagnosis"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

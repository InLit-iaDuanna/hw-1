"""
Evaluation Script for RL-trained Gait Controller
Loads trained PPO model and compares against V13.7 FSM baseline
"""

import os
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import mujoco
from stable_baselines3 import PPO

# Add this directory to path for imports
RL_DIR = Path(__file__).resolve().parent
HW1_ROOT = RL_DIR.parent
sys.path.insert(0, str(RL_DIR))
sys.path.insert(0, str(HW1_ROOT))

from environment import CompassGaitEnv as GaitTrainingEnv


def load_trained_model(model_path: str) -> PPO:
    """Load trained PPO model from file"""
    if not os.path.exists(model_path):
        # Try with .zip extension
        if not model_path.endswith(".zip"):
            model_path = model_path + ".zip"

    print(f"Loading model from: {model_path}")
    model = PPO.load(model_path)
    return model


def run_episode(
    env: GaitTrainingEnv, model: PPO, deterministic: bool = True, render: bool = False
) -> dict:
    """
    Run a single episode and collect metrics

    Returns:
        dict with keys: distance, steps, duration, cot, stability, success,
                       trajectory (qpos, qvel, actions, rewards over time)
    """
    obs, _ = env.reset()

    trajectory = {"qpos": [], "qvel": [], "actions": [], "rewards": [], "times": []}

    total_reward = 0.0
    step_count = 0
    touchdown_count = 0
    prev_contact = [False, False]  # [left_foot, right_foot]

    done = False
    while not done and step_count < 12000:  # Max 12 seconds @ 1000Hz
        # Get action from model
        action, _states = model.predict(obs, deterministic=deterministic)

        # Store state before step
        trajectory["qpos"].append(env.data.qpos.copy())
        trajectory["qvel"].append(env.data.qvel.copy())
        trajectory["actions"].append(action.copy())
        trajectory["times"].append(env.data.time)

        # Step environment
        obs, reward, terminated, truncated, info = env.step(action)

        trajectory["rewards"].append(reward)
        total_reward += reward
        step_count += 1

        # Count touchdowns (heel strikes)
        # Check all foot contact geoms: heel, sole, toe
        left_foot_geoms = ["left_heel", "left_sole", "left_toe"]
        right_foot_geoms = ["right_heel", "right_sole", "right_toe"]

        left_foot_contact = any(
            env.data.contact[i].geom1 in [env.model.geom(g).id for g in left_foot_geoms]
            or env.data.contact[i].geom2
            in [env.model.geom(g).id for g in left_foot_geoms]
            for i in range(env.data.ncon)
        )
        right_foot_contact = any(
            env.data.contact[i].geom1
            in [env.model.geom(g).id for g in right_foot_geoms]
            or env.data.contact[i].geom2
            in [env.model.geom(g).id for g in right_foot_geoms]
            for i in range(env.data.ncon)
        )
        current_contact = [left_foot_contact, right_foot_contact]

        # Detect heel strike (contact goes from False to True)
        for foot_idx in range(2):
            if current_contact[foot_idx] and not prev_contact[foot_idx]:
                touchdown_count += 1

        prev_contact = current_contact

        if terminated or truncated:
            done = True

    # Compute final metrics
    final_distance = env.data.qpos[0]  # hip_x position
    duration = env.data.time
    hip_height = env.data.qpos[1]  # hip_y position

    # Compute Cost of Transport (CoT)
    # CoT = E_mech / (m * g * d)
    mass = env.model.body("hip").mass
    for body_id in range(env.model.nbody):
        if body_id != env.model.body("world").id:
            mass += env.model.body(body_id).mass

    # Mechanical energy change
    E_initial = trajectory["rewards"][0] if len(trajectory["rewards"]) > 0 else 0
    E_final = total_reward
    E_consumed = abs(E_final - E_initial)

    gravity = 9.81
    cot = (
        E_consumed / (mass * gravity * max(final_distance, 0.01))
        if final_distance > 0.01
        else float("inf")
    )

    # Stability metric: standard deviation of hip height
    hip_heights = [qpos[1] for qpos in trajectory["qpos"]]
    stability = np.std(hip_heights) if len(hip_heights) > 0 else 0.0

    # Success criteria (match V13.7 baseline)
    success = (
        final_distance >= 4.0  # Forward progress
        and touchdown_count >= 8  # Multiple steps
        and duration >= 10.0  # Sustained walking
        and hip_height > 0.3  # Not fallen
    )

    return {
        "distance": final_distance,
        "steps": touchdown_count,
        "duration": duration,
        "cot": cot,
        "stability": stability,
        "success": success,
        "total_reward": total_reward,
        "trajectory": trajectory,
        "hip_height": hip_height,
    }


def run_multiple_episodes(model: PPO, num_episodes: int = 10, seed: int = 42) -> list:
    """Run multiple test episodes with different initial conditions"""
    results = []

    for ep in range(num_episodes):
        print(f"\n{'='*60}")
        print(f"Episode {ep + 1}/{num_episodes}")
        print(f"{'='*60}")

        env = GaitTrainingEnv()
        env.reset(seed=seed + ep)

        result = run_episode(env, model, deterministic=True)

        print(f"  Distance: {float(result['distance']):.2f} m")
        print(f"  Steps: {result['steps']}")
        print(f"  Duration: {float(result['duration']):.2f} s")
        print(f"  CoT: {float(result['cot']):.4f}")
        print(f"  Stability (hip height std): {float(result['stability']):.4f} m")
        print(f"  Success: {'PASS' if result['success'] else 'FAIL'}")

        results.append(result)
        env.close()

    return results


def compute_statistics(results: list) -> dict:
    """Compute mean and std statistics across episodes"""
    metrics = ["distance", "steps", "duration", "cot", "stability", "total_reward"]

    stats = {}
    for metric in metrics:
        values = [
            r[metric]
            for r in results
            if not np.isnan(r[metric]) and not np.isinf(r[metric])
        ]
        if len(values) > 0:
            stats[metric] = {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values),
            }
        else:
            stats[metric] = {"mean": 0, "std": 0, "min": 0, "max": 0}

    success_rate = sum(r["success"] for r in results) / len(results)
    stats["success_rate"] = success_rate

    return stats


def compare_with_baseline(rl_stats: dict, baseline: dict = None) -> None:
    """
    Compare RL performance with V13.7 FSM baseline

    V13.7 baseline (from previous experiments):
        - Distance: 4.63 m
        - Steps: 10
        - Duration: 12.0 s
        - CoT: 0.066
        - Success rate: ~90%
    """
    if baseline is None:
        # Default V13.7 baseline values
        baseline = {
            "distance": {"mean": 4.63, "std": 0.15},
            "steps": {"mean": 10, "std": 1},
            "duration": {"mean": 12.0, "std": 0.5},
            "cot": {"mean": 0.066, "std": 0.008},
            "success_rate": 0.90,
        }

    print("\n" + "=" * 80)
    print("COMPARISON: RL (PPO) vs V13.7 FSM Baseline")
    print("=" * 80)
    print(f"{'Metric':<20} {'V13.7 Baseline':<25} {'RL (PPO)':<25} {'Change':<10}")
    print("-" * 80)

    metrics = [
        ("distance", "m", True),  # Higher is better
        ("steps", "", True),  # Higher is better
        ("duration", "s", True),  # Higher is better
        ("cot", "", False),  # Lower is better
        ("success_rate", "%", True),  # Higher is better
    ]

    for metric, unit, higher_better in metrics:
        if metric in rl_stats and metric in baseline:
            if metric == "success_rate":
                baseline_val = baseline[metric] * 100
                rl_val = rl_stats[metric] * 100
                print(
                    f"{metric:<20} {baseline_val:>6.1f}{unit:<18} {rl_val:>6.1f}{unit:<18}",
                    end="",
                )
            else:
                baseline_val = baseline[metric]["mean"]
                rl_val = rl_stats[metric]["mean"]
                rl_std = rl_stats[metric]["std"]
                print(
                    f"{metric:<20} {baseline_val:>6.2f}{unit:<18} {rl_val:>6.2f}±{rl_std:.2f}{unit:<10}",
                    end="",
                )

            # Compute percentage change
            if baseline_val != 0:
                change = (rl_val - baseline_val) / baseline_val * 100
                indicator = (
                    "↑"
                    if (change > 0 and higher_better)
                    or (change < 0 and not higher_better)
                    else "↓"
                )
                print(f"{change:>+6.1f}% {indicator}")
            else:
                print("N/A")

    print("=" * 80)


def plot_trajectory(result: dict, save_path: str = None) -> None:
    """Plot trajectory data from a single episode"""
    traj = result["trajectory"]
    times = np.array(traj["times"])
    qpos = np.array(traj["qpos"])
    qvel = np.array(traj["qvel"])
    actions = np.array(traj["actions"])
    rewards = np.array(traj["rewards"])

    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(4, 2, figure=fig)

    # 1. Hip trajectory (x-y plane)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(qpos[:, 0], qpos[:, 1], "b-", linewidth=1.5)
    ax1.set_xlabel("Hip X Position (m)")
    ax1.set_ylabel("Hip Y Position (m)")
    ax1.set_title("Hip Trajectory")
    ax1.grid(True, alpha=0.3)

    # 2. Joint angles over time
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(times, qpos[:, 2], label="Left Hip", linewidth=1.5)
    ax2.plot(times, qpos[:, 3], label="Right Hip", linewidth=1.5)
    ax2.plot(times, qpos[:, 4], label="Left Knee", linewidth=1.5)
    ax2.plot(times, qpos[:, 5], label="Right Knee", linewidth=1.5)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Joint Angle (rad)")
    ax2.set_title("Joint Angles")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Joint velocities
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(times, qvel[:, 2], label="Left Hip ω", linewidth=1.5)
    ax3.plot(times, qvel[:, 3], label="Right Hip ω", linewidth=1.5)
    ax3.plot(times, qvel[:, 4], label="Left Knee ω", linewidth=1.5)
    ax3.plot(times, qvel[:, 5], label="Right Knee ω", linewidth=1.5)
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Joint Velocity (rad/s)")
    ax3.set_title("Joint Velocities")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Control actions (torques)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(times, actions[:, 0], label="Left Hip τ", linewidth=1.5)
    ax4.plot(times, actions[:, 1], label="Right Hip τ", linewidth=1.5)
    ax4.plot(times, actions[:, 2], label="Left Knee τ", linewidth=1.5)
    ax4.plot(times, actions[:, 3], label="Right Knee τ", linewidth=1.5)
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Torque (N·m)")
    ax4.set_title("Control Actions")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Hip height over time
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.plot(times, qpos[:, 1], "g-", linewidth=1.5)
    ax5.axhline(y=0.3, color="r", linestyle="--", label="Fall threshold")
    ax5.set_xlabel("Time (s)")
    ax5.set_ylabel("Hip Height (m)")
    ax5.set_title("Hip Height (Stability)")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. Reward over time
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.plot(times, rewards, "purple", linewidth=1.5)
    ax6.set_xlabel("Time (s)")
    ax6.set_ylabel("Reward")
    ax6.set_title("Instantaneous Reward")
    ax6.grid(True, alpha=0.3)

    # 7. Phase portrait: hip angle vs velocity
    ax7 = fig.add_subplot(gs[3, 0])
    ax7.plot(qpos[:, 2], qvel[:, 2], "b-", alpha=0.7, linewidth=1)
    ax7.scatter(
        qpos[0, 2], qvel[0, 2], c="green", s=50, marker="o", label="Start", zorder=5
    )
    ax7.scatter(
        qpos[-1, 2], qvel[-1, 2], c="red", s=50, marker="x", label="End", zorder=5
    )
    ax7.set_xlabel("Left Hip Angle (rad)")
    ax7.set_ylabel("Left Hip Velocity (rad/s)")
    ax7.set_title("Phase Portrait (Left Hip)")
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # 8. Summary metrics
    ax8 = fig.add_subplot(gs[3, 1])
    ax8.axis("off")
    summary_text = f"""
    EPISODE SUMMARY
    {'='*30}
    Distance:     {result['distance']:.2f} m
    Steps:        {result['steps']}
    Duration:     {result['duration']:.2f} s
    CoT:          {result['cot']:.4f}
    Stability:    {result['stability']:.4f} m
    Total Reward: {result['total_reward']:.2f}
    Success:      {'✓ YES' if result['success'] else '✗ NO'}
    """
    ax8.text(
        0.1,
        0.5,
        summary_text,
        fontsize=11,
        family="monospace",
        verticalalignment="center",
    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\nTrajectory plot saved to: {save_path}")
    else:
        plt.show()

    plt.close()


def generate_comparison_plots(
    rl_stats: dict, baseline: dict = None, save_path: str = None
):
    """Generate comparison bar charts"""
    if baseline is None:
        baseline = {
            "distance": {"mean": 4.63, "std": 0.15},
            "steps": {"mean": 10, "std": 1},
            "cot": {"mean": 0.066, "std": 0.008},
            "success_rate": 0.90,
        }

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    metrics = [
        ("distance", "Forward Distance (m)", axes[0, 0]),
        ("steps", "Number of Steps", axes[0, 1]),
        ("cot", "Cost of Transport", axes[1, 0]),
        ("success_rate", "Success Rate", axes[1, 1]),
    ]

    for metric, label, ax in metrics:
        if metric == "success_rate":
            baseline_val = baseline[metric]
            baseline_err = 0
            rl_val = rl_stats[metric]
            rl_err = 0
        else:
            baseline_val = baseline[metric]["mean"]
            baseline_err = baseline[metric]["std"]
            rl_val = rl_stats[metric]["mean"]
            rl_err = rl_stats[metric]["std"]

        x = [0, 1]
        values = [baseline_val, rl_val]
        errors = [baseline_err, rl_err]
        colors = ["#3498db", "#e74c3c"]

        ax.bar(x, values, yerr=errors, color=colors, alpha=0.7, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(["V13.7 FSM", "RL (PPO)"])
        ax.set_ylabel(label)
        ax.set_title(label)
        ax.grid(True, alpha=0.3, axis="y")

        # Add value labels on bars
        for i, (val, err) in enumerate(zip(values, errors)):
            ax.text(
                i,
                val + err + 0.05 * max(values),
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Comparison plot saved to: {save_path}")
    else:
        plt.show()

    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained RL gait controller")
    parser.add_argument(
        "--model",
        type=str,
        default="./models/ppo_gait_final",
        help="Path to trained model (default: ./models/ppo_gait_final)",
    )
    parser.add_argument(
        "--episodes", type=int, default=10, help="Number of test episodes (default: 10)"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./evaluation_results",
        help="Directory to save results (default: ./evaluation_results)",
    )
    parser.add_argument(
        "--plot-trajectory",
        action="store_true",
        help="Plot trajectory for first episode",
    )
    parser.add_argument(
        "--baseline-file",
        type=str,
        default=None,
        help="JSON file with V13.7 baseline metrics",
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("RL GAIT CONTROLLER EVALUATION")
    print("=" * 80)
    print(f"Model: {args.model}")
    print(f"Episodes: {args.episodes}")
    print(f"Output directory: {args.output_dir}")

    # Load trained model
    try:
        model = load_trained_model(args.model)
    except Exception as e:
        print(f"\nERROR: Failed to load model from {args.model}")
        print(f"Error: {e}")
        print("\nMake sure the model has been trained first using train_ppo.py")
        return 1

    # Load baseline if provided
    baseline = None
    if args.baseline_file and os.path.exists(args.baseline_file):
        with open(args.baseline_file, "r") as f:
            baseline = json.load(f)
        print(f"Loaded baseline from: {args.baseline_file}")

    # Run multiple episodes
    print(f"\nRunning {args.episodes} test episodes...")
    results = run_multiple_episodes(model, num_episodes=args.episodes, seed=args.seed)

    # Compute statistics
    stats = compute_statistics(results)

    print("\n" + "=" * 80)
    print("AGGREGATE STATISTICS")
    print("=" * 80)
    for metric, values in stats.items():
        if metric == "success_rate":
            print(f"{metric:<20} {values*100:>6.1f}%")
        elif isinstance(values, dict):
            print(
                f"{metric:<20} {values['mean']:>6.2f} ± {values['std']:.2f}  "
                f"(min: {values['min']:.2f}, max: {values['max']:.2f})"
            )

    # Compare with baseline
    compare_with_baseline(stats, baseline)

    # Save results
    results_file = os.path.join(args.output_dir, "evaluation_results.json")
    with open(results_file, "w") as f:
        json.dump(
            {
                "statistics": stats,
                "episodes": results,
                "model_path": args.model,
                "num_episodes": args.episodes,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nResults saved to: {results_file}")

    # Plot trajectory for first successful episode
    if args.plot_trajectory:
        successful_results = [r for r in results if r["success"]]
        if successful_results:
            plot_path = os.path.join(args.output_dir, "trajectory_plot.png")
            plot_trajectory(successful_results[0], save_path=plot_path)
        else:
            print("\nWARNING: No successful episodes to plot")

    # Generate comparison plots
    comparison_path = os.path.join(args.output_dir, "comparison_plot.png")
    generate_comparison_plots(stats, baseline, save_path=comparison_path)

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {args.output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

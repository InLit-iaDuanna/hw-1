"""Sobol sensitivity analysis for hw-1 gait parameters.

Performs global sensitivity analysis using SALib to identify the most important
parameters affecting gait performance metrics (speed, stability, energy efficiency).

Usage:
    python sensitivity_analysis.py --metric speed --samples 1024
    python sensitivity_analysis.py --metric stability --second-order
    python sensitivity_analysis.py --visualize
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parameter_explorer.sensitivity_analyzer import (
    SensitivityAnalyzer,
    comprehensive_sensitivity_analysis,
)
from common.compass_gait import CompassGaitParams, CompassGait
from common.simulation_runner import run_simulation_safe


def create_objective_function(metric: str = "speed") -> Callable[[dict[str, float]], float]:
    """Create objective function for sensitivity analysis.

    Args:
        metric: Target metric - "speed", "stability", "energy", or "robustness"

    Returns:
        Function that takes parameter dict and returns scalar metric value
    """

    def objective(params: dict[str, float]) -> float:
        """Evaluate gait performance with given parameters.

        Args:
            params: Dictionary of parameter values

        Returns:
            Scalar performance metric (higher is better for optimization)
        """
        try:
            # Create parameter object
            gait_params = CompassGaitParams(
                slope_deg=params.get("slope_deg", 5.0),
                step_angle_deg=params.get("step_angle_deg", 10.0),
                stance_damping=params.get("stance_damping", 0.012),
                swing_damping=params.get("swing_damping", 0.035),
                passive_hip_stiffness=params.get("passive_hip_stiffness", 0.42),
                collision_retention=params.get("collision_retention", 0.82),
                energy_gain_scale=params.get("energy_gain_scale", 0.42),
                initial_speed=params.get("initial_speed", 0.24),
                steps=16,  # Reduced for faster evaluation
                dt=0.002,
            )

            # Run simulation
            model = CompassGait(gait_params)
            result = run_simulation_safe(model)

            if result is None or not result.get("success", False):
                return -1000.0  # Penalty for failed simulation

            # Extract metrics
            trajectory = result.get("trajectory", {})

            if metric == "speed":
                # Average forward velocity
                velocities = trajectory.get("stance_vel", [])
                if len(velocities) == 0:
                    return -1000.0
                return float(np.mean(velocities))

            elif metric == "stability":
                # Inverse of velocity variance (more stable = less variance)
                velocities = trajectory.get("stance_vel", [])
                if len(velocities) < 2:
                    return -1000.0
                variance = np.var(velocities)
                return -float(variance)  # Negative variance (minimize variance)

            elif metric == "energy":
                # Energy efficiency (distance per energy unit)
                energy = result.get("total_energy", 1e-6)
                distance = result.get("distance_traveled", 0.0)
                if energy <= 0:
                    return -1000.0
                return float(distance / energy)

            elif metric == "robustness":
                # Number of successful steps completed
                steps_completed = result.get("steps_completed", 0)
                return float(steps_completed)

            else:
                raise ValueError(f"Unknown metric: {metric}")

        except Exception as e:
            print(f"Simulation failed with params {params}: {e}")
            return -1000.0

    return objective


def define_parameter_space() -> tuple[list[str], list[tuple[float, float]]]:
    """Define parameter names and bounds for sensitivity analysis.

    Returns:
        (param_names, param_bounds) tuple
    """
    param_names = [
        "slope_deg",
        "step_angle_deg",
        "stance_damping",
        "swing_damping",
        "passive_hip_stiffness",
        "collision_retention",
        "energy_gain_scale",
        "initial_speed",
    ]

    param_bounds = [
        (3.0, 8.0),      # slope_deg: terrain steepness
        (5.0, 15.0),     # step_angle_deg: gait geometry
        (0.005, 0.025),  # stance_damping: energy dissipation
        (0.020, 0.050),  # swing_damping: leg swing control
        (0.20, 0.80),    # passive_hip_stiffness: hip compliance
        (0.70, 0.95),    # collision_retention: impact efficiency
        (0.20, 0.80),    # energy_gain_scale: active energy input
        (0.15, 0.35),    # initial_speed: starting condition
    ]

    return param_names, param_bounds


def visualize_sensitivity_results(
    results: dict[str, Any],
    output_path: Path | None = None,
    show: bool = True
) -> None:
    """Visualize Sobol sensitivity analysis results.

    Args:
        results: Results from comprehensive_sensitivity_analysis
        output_path: Path to save figure (optional)
        show: Whether to display figure
    """
    param_names = results["param_names"]
    S1 = results["S1"]
    ST = results["ST"]
    S1_conf = results["S1_conf"]
    ST_conf = results["ST_conf"]

    n_params = len(param_names)

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Sobol Sensitivity Analysis Results", fontsize=16, fontweight="bold")

    # 1. First-order and total-order indices
    ax1 = axes[0, 0]
    x = np.arange(n_params)
    width = 0.35

    ax1.bar(x - width/2, S1, width, label="S1 (First-order)",
            color="steelblue", yerr=S1_conf, capsize=5)
    ax1.bar(x + width/2, ST, width, label="ST (Total-order)",
            color="coral", yerr=ST_conf, capsize=5)

    ax1.set_xlabel("Parameter", fontweight="bold")
    ax1.set_ylabel("Sobol Index", fontweight="bold")
    ax1.set_title("First-order vs Total-order Sensitivity")
    ax1.set_xticks(x)
    ax1.set_xticklabels(param_names, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # 2. Interaction effects (ST - S1)
    ax2 = axes[0, 1]
    interaction = ST - S1
    colors = ["green" if i > 0 else "gray" for i in interaction]

    ax2.bar(x, interaction, color=colors, alpha=0.7)
    ax2.set_xlabel("Parameter", fontweight="bold")
    ax2.set_ylabel("Interaction Effect (ST - S1)", fontweight="bold")
    ax2.set_title("Parameter Interaction Strength")
    ax2.set_xticks(x)
    ax2.set_xticklabels(param_names, rotation=45, ha="right")
    ax2.axhline(y=0, color="black", linestyle="--", linewidth=0.8)
    ax2.grid(axis="y", alpha=0.3)

    # 3. Ranked sensitivity
    ax3 = axes[1, 0]
    ranked = sorted(zip(param_names, ST), key=lambda item: item[1], reverse=True)
    ranked_names, ranked_values = zip(*ranked)

    ax3.barh(range(len(ranked_names)), ranked_values, color="mediumseagreen")
    ax3.set_yticks(range(len(ranked_names)))
    ax3.set_yticklabels(ranked_names)
    ax3.set_xlabel("Total Sobol Index (ST)", fontweight="bold")
    ax3.set_title("Parameter Importance Ranking")
    ax3.grid(axis="x", alpha=0.3)

    # 4. Interaction matrix (if available)
    ax4 = axes[1, 1]
    if "interaction_matrix" in results and results["interaction_matrix"] is not None:
        interaction_matrix = results["interaction_matrix"]
        im = ax4.imshow(interaction_matrix, cmap="RdYlGn", aspect="auto",
                        vmin=-0.1, vmax=0.5)
        ax4.set_xticks(range(n_params))
        ax4.set_yticks(range(n_params))
        ax4.set_xticklabels(param_names, rotation=45, ha="right")
        ax4.set_yticklabels(param_names)
        ax4.set_title("Second-order Interaction Matrix (S2)")
        plt.colorbar(im, ax=ax4, label="Interaction Index")

        # Add values to cells
        for i in range(n_params):
            for j in range(n_params):
                if i != j:
                    value = interaction_matrix[i, j]
                    color = "white" if value > 0.25 else "black"
                    ax4.text(j, i, f"{value:.3f}", ha="center", va="center",
                            color=color, fontsize=8)
    else:
        ax4.text(0.5, 0.5, "Second-order indices\nnot computed",
                ha="center", va="center", transform=ax4.transAxes, fontsize=12)
        ax4.set_xticks([])
        ax4.set_yticks([])

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Figure saved to {output_path}")

    if show:
        plt.show()
    else:
        plt.close()


def print_sensitivity_report(results: dict[str, Any], metric: str) -> None:
    """Print formatted sensitivity analysis report.

    Args:
        results: Results from comprehensive_sensitivity_analysis
        metric: Target metric name
    """
    print("\n" + "="*80)
    print(f"SOBOL SENSITIVITY ANALYSIS REPORT - Metric: {metric.upper()}")
    print("="*80)

    param_names = results["param_names"]
    S1 = results["S1"]
    ST = results["ST"]
    ranked = results["ranked_params"]
    n_evals = results["n_evals"]

    print(f"\nTotal function evaluations: {n_evals}")
    print(f"Number of parameters: {len(param_names)}")

    print("\n" + "-"*80)
    print("PARAMETER IMPORTANCE RANKING (by Total Sobol Index)")
    print("-"*80)
    print(f"{'Rank':<6} {'Parameter':<25} {'ST':<10} {'S1':<10} {'Interaction':<12}")
    print("-"*80)

    for i, (name, st_value) in enumerate(ranked, 1):
        idx = param_names.index(name)
        s1_value = S1[idx]
        interaction = st_value - s1_value

        print(f"{i:<6} {name:<25} {st_value:>8.4f}  {s1_value:>8.4f}  {interaction:>10.4f}")

    print("\n" + "-"*80)
    print("INTERPRETATION GUIDE")
    print("-"*80)
    print("S1 (First-order):  Direct effect of parameter variation")
    print("ST (Total-order):  Direct + interaction effects")
    print("Interaction:       ST - S1 (effect through parameter interactions)")
    print("\nHigh ST:           Parameter significantly affects output")
    print("High Interaction:  Parameter has strong interactions with others")
    print("ST ≈ S1:          Parameter effects are mostly independent")

    # Identify key parameters
    print("\n" + "-"*80)
    print("KEY FINDINGS")
    print("-"*80)

    threshold_high = 0.1
    threshold_interaction = 0.05

    important_params = [name for name, val in ranked if val > threshold_high]
    if important_params:
        print(f"\nMost important parameters (ST > {threshold_high}):")
        for name in important_params:
            idx = param_names.index(name)
            print(f"  - {name}: ST={ST[idx]:.4f}")
    else:
        print(f"\nNo parameters with ST > {threshold_high}")

    interactive_params = [
        name for name in param_names
        if (ST[param_names.index(name)] - S1[param_names.index(name)]) > threshold_interaction
    ]
    if interactive_params:
        print(f"\nParameters with strong interactions (ST-S1 > {threshold_interaction}):")
        for name in interactive_params:
            idx = param_names.index(name)
            interaction = ST[idx] - S1[idx]
            print(f"  - {name}: Interaction={interaction:.4f}")

    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Sobol sensitivity analysis for hw-1 gait parameters"
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="speed",
        choices=["speed", "stability", "energy", "robustness"],
        help="Target metric for sensitivity analysis"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=512,
        help="Base sample size (actual evals = samples * (2*D + 2))"
    )
    parser.add_argument(
        "--second-order",
        action="store_true",
        help="Compute second-order interaction indices (increases computation)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualization plots"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="sensitivity_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Don't display plots (only save)"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Starting Sobol sensitivity analysis for metric: {args.metric}")
    print(f"Base samples: {args.samples}")
    print(f"Second-order: {args.second_order}")
    print(f"Random seed: {args.seed}")

    # Define parameter space
    param_names, param_bounds = define_parameter_space()
    print(f"\nAnalyzing {len(param_names)} parameters:")
    for name, bounds in zip(param_names, param_bounds):
        print(f"  {name}: [{bounds[0]}, {bounds[1]}]")

    # Create objective function
    objective_func = create_objective_function(args.metric)

    # Run comprehensive Sobol analysis
    print("\nRunning Sobol sensitivity analysis...")
    print("This may take several minutes depending on sample size...")

    results = comprehensive_sensitivity_analysis(
        param_names=param_names,
        param_bounds=param_bounds,
        objective_func=objective_func,
        n_sobol_samples=args.samples,
        calc_second_order=args.second_order,
        seed=args.seed,
    )

    # Print report
    print_sensitivity_report(results, args.metric)

    # Save results to file
    results_file = output_dir / f"sensitivity_{args.metric}_n{args.samples}.npz"
    np.savez(
        results_file,
        param_names=results["param_names"],
        S1=results["S1"],
        ST=results["ST"],
        S1_conf=results["S1_conf"],
        ST_conf=results["ST_conf"],
        samples=results["samples"],
        objectives=results["objectives"],
        n_evals=results["n_evals"],
        S2=results.get("S2", None),
        interaction_matrix=results.get("interaction_matrix", None),
    )
    print(f"Results saved to {results_file}")

    # Visualize if requested
    if args.visualize:
        print("\nGenerating visualization...")
        fig_path = output_dir / f"sensitivity_{args.metric}_n{args.samples}.png"
        visualize_sensitivity_results(
            results,
            output_path=fig_path,
            show=not args.no_show
        )

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()

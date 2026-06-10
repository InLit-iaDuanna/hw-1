"""
Multi-objective optimization for hw-1 gait parameters
Optimizes both walking distance (maximize) and energy cost of transport (minimize)
Uses NSGA-II algorithm to find Pareto front solutions
"""

import numpy as np
import matplotlib.pyplot as plt
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.termination import get_termination
from pymoo.util.ref_dirs import get_reference_directions
import json
from pathlib import Path
from typing import Dict, Tuple, List
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend


class GaitOptimizationProblem(Problem):
    """
    Multi-objective optimization problem for gait parameters

    Decision Variables:
    - torque_gain: Assistance torque gain [0.5, 2.0]
    - phase_threshold: Phase transition threshold [0.3, 0.7]
    - damping_coeff: Damping coefficient [0.1, 0.5]
    - stiffness_gain: Joint stiffness gain [0.5, 1.5]

    Objectives:
    1. Maximize walking distance (converted to minimize -distance)
    2. Minimize energy cost of transport (CoT)
    """

    def __init__(self, simulation_func=None):
        """
        Args:
            simulation_func: Function that takes parameters dict and returns (distance, energy, cot)
                           If None, uses a surrogate model
        """
        super().__init__(
            n_var=4,  # 4 parameters
            n_obj=2,  # 2 objectives
            n_constr=0,  # No constraints
            xl=np.array([0.5, 0.3, 0.1, 0.5]),  # Lower bounds
            xu=np.array([2.0, 0.7, 0.5, 1.5])   # Upper bounds
        )
        self.simulation_func = simulation_func or self._surrogate_model
        self.evaluation_count = 0

    def _surrogate_model(self, params: Dict) -> Tuple[float, float, float]:
        """
        Surrogate model for testing (replace with actual simulation)
        Models realistic trade-offs between distance and energy
        """
        tg = params['torque_gain']
        pt = params['phase_threshold']
        dc = params['damping_coeff']
        sg = params['stiffness_gain']

        # Distance model: increases with torque, optimal phase threshold around 0.5
        distance = (
            50 * tg +
            100 * (1 - abs(pt - 0.5)) +
            30 * sg -
            20 * dc +
            np.random.normal(0, 5)  # Add noise
        )
        distance = max(0, distance)

        # Energy model: increases with torque and stiffness
        energy = (
            100 * tg**1.5 +
            50 * sg**1.2 +
            30 * (1 - dc) +
            20 * abs(pt - 0.5)**0.5 +
            np.random.normal(0, 10)
        )
        energy = max(1, energy)

        # Cost of transport
        cot = energy / (distance + 1e-6)

        return distance, energy, cot

    def _evaluate(self, X, out, *args, **kwargs):
        """
        Evaluate population
        X: (n_pop, n_var) array of decision variables
        """
        n_pop = X.shape[0]
        f1 = np.zeros(n_pop)  # -distance (minimize)
        f2 = np.zeros(n_pop)  # CoT (minimize)

        for i in range(n_pop):
            params = {
                'torque_gain': X[i, 0],
                'phase_threshold': X[i, 1],
                'damping_coeff': X[i, 2],
                'stiffness_gain': X[i, 3]
            }

            distance, energy, cot = self.simulation_func(params)

            f1[i] = -distance  # Minimize negative distance = maximize distance
            f2[i] = cot        # Minimize CoT

            self.evaluation_count += 1

            if self.evaluation_count % 50 == 0:
                print(f"Evaluation {self.evaluation_count}: dist={distance:.2f}, CoT={cot:.4f}")

        out["F"] = np.column_stack([f1, f2])


def find_knee_point(pareto_front: np.ndarray) -> int:
    """
    Find knee point in Pareto front using maximum distance method
    Knee point represents best trade-off solution

    Args:
        pareto_front: (n, 2) array of objective values

    Returns:
        Index of knee point
    """
    # Normalize objectives to [0, 1]
    f_min = pareto_front.min(axis=0)
    f_max = pareto_front.max(axis=0)
    f_range = f_max - f_min
    f_range[f_range == 0] = 1  # Avoid division by zero

    normalized = (pareto_front - f_min) / f_range

    # Find extreme points (ideal corners)
    ideal_point = np.array([0, 0])  # Both objectives minimized

    # Calculate distance from each point to ideal point
    distances = np.linalg.norm(normalized - ideal_point, axis=1)

    # Alternative: find point with maximum distance to line connecting extremes
    # This works better for non-convex fronts
    if len(normalized) > 2:
        # Find extreme points
        idx_min_f1 = np.argmin(normalized[:, 0])
        idx_min_f2 = np.argmin(normalized[:, 1])

        p1 = normalized[idx_min_f1]
        p2 = normalized[idx_min_f2]

        # Calculate perpendicular distance from each point to line p1-p2
        line_vec = p2 - p1
        line_len = np.linalg.norm(line_vec)

        if line_len > 0:
            line_unit = line_vec / line_len
            perp_distances = []

            for point in normalized:
                vec_to_point = point - p1
                projection = np.dot(vec_to_point, line_unit)
                perp_dist = np.linalg.norm(vec_to_point - projection * line_unit)
                perp_distances.append(perp_dist)

            knee_idx = np.argmax(perp_distances)
        else:
            knee_idx = np.argmin(distances)
    else:
        knee_idx = np.argmin(distances)

    return knee_idx


def run_optimization(
    pop_size: int = 100,
    n_gen: int = 50,
    simulation_func=None,
    output_dir: str = "D:\\Dunna\\Documents\\hw-1\\parameter_tuning\\results"
) -> Dict:
    """
    Run multi-objective optimization

    Args:
        pop_size: Population size
        n_gen: Number of generations
        simulation_func: Custom simulation function
        output_dir: Directory to save results

    Returns:
        Dictionary containing optimization results
    """
    print("=" * 60)
    print("Multi-Objective Gait Parameter Optimization")
    print("=" * 60)
    print(f"Population size: {pop_size}")
    print(f"Generations: {n_gen}")
    print()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Define problem
    problem = GaitOptimizationProblem(simulation_func=simulation_func)

    # Configure NSGA-II algorithm
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True
    )

    # Run optimization
    print("Starting optimization...")
    res = minimize(
        problem,
        algorithm,
        termination=get_termination("n_gen", n_gen),
        seed=42,
        verbose=True,
        save_history=True
    )

    print(f"\nOptimization complete! Total evaluations: {problem.evaluation_count}")
    print(f"Pareto front solutions: {len(res.F)}")

    # Extract results
    pareto_X = res.X  # Decision variables
    pareto_F = res.F  # Objective values

    # Convert back to original objectives
    distance = -pareto_F[:, 0]  # Convert back from negative
    cot = pareto_F[:, 1]

    # Find knee point
    knee_idx = find_knee_point(pareto_F)
    knee_params = pareto_X[knee_idx]
    knee_distance = distance[knee_idx]
    knee_cot = cot[knee_idx]

    print("\n" + "=" * 60)
    print("KNEE POINT SOLUTION (Best Trade-off)")
    print("=" * 60)
    print(f"Torque Gain:       {knee_params[0]:.4f}")
    print(f"Phase Threshold:   {knee_params[1]:.4f}")
    print(f"Damping Coeff:     {knee_params[2]:.4f}")
    print(f"Stiffness Gain:    {knee_params[3]:.4f}")
    print(f"\nDistance:          {knee_distance:.2f} m")
    print(f"Cost of Transport: {knee_cot:.4f}")
    print("=" * 60)

    # Save results
    results = {
        'pareto_front': {
            'decision_variables': pareto_X.tolist(),
            'distance': distance.tolist(),
            'cot': cot.tolist()
        },
        'knee_point': {
            'index': int(knee_idx),
            'parameters': {
                'torque_gain': float(knee_params[0]),
                'phase_threshold': float(knee_params[1]),
                'damping_coeff': float(knee_params[2]),
                'stiffness_gain': float(knee_params[3])
            },
            'objectives': {
                'distance': float(knee_distance),
                'cot': float(knee_cot)
            }
        },
        'optimization_config': {
            'pop_size': pop_size,
            'n_gen': n_gen,
            'total_evaluations': problem.evaluation_count
        }
    }

    results_file = output_path / "multi_objective_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Visualize results
    visualize_results(distance, cot, knee_idx, output_path)

    return results


def visualize_results(
    distance: np.ndarray,
    cot: np.ndarray,
    knee_idx: int,
    output_path: Path
):
    """
    Create visualization of Pareto front and trade-offs
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: Pareto front
    ax1 = axes[0]
    ax1.scatter(distance, cot, c='blue', alpha=0.6, s=50, label='Pareto Solutions')
    ax1.scatter(distance[knee_idx], cot[knee_idx],
                c='red', s=200, marker='*',
                edgecolors='black', linewidths=2,
                label='Knee Point', zorder=5)
    ax1.set_xlabel('Walking Distance (m)', fontsize=12)
    ax1.set_ylabel('Cost of Transport', fontsize=12)
    ax1.set_title('Pareto Front: Distance vs Energy Efficiency', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)

    # Add annotations
    ax1.annotate('Best Trade-off',
                 xy=(distance[knee_idx], cot[knee_idx]),
                 xytext=(20, 20), textcoords='offset points',
                 fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', lw=2, color='red'))

    # Plot 2: Trade-off analysis
    ax2 = axes[1]

    # Sort by distance for better visualization
    sorted_idx = np.argsort(distance)
    sorted_dist = distance[sorted_idx]
    sorted_cot = cot[sorted_idx]

    ax2_twin = ax2.twinx()

    line1 = ax2.plot(range(len(sorted_dist)), sorted_dist,
                     'bo-', linewidth=2, markersize=6, label='Distance')
    line2 = ax2_twin.plot(range(len(sorted_cot)), sorted_cot,
                          'ro-', linewidth=2, markersize=6, label='CoT')

    # Mark knee point
    knee_pos = np.where(sorted_idx == knee_idx)[0][0]
    ax2.axvline(knee_pos, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Knee Point')

    ax2.set_xlabel('Solution Index (sorted by distance)', fontsize=12)
    ax2.set_ylabel('Distance (m)', fontsize=12, color='blue')
    ax2_twin.set_ylabel('Cost of Transport', fontsize=12, color='red')
    ax2.set_title('Trade-off Analysis', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='blue')
    ax2_twin.tick_params(axis='y', labelcolor='red')
    ax2.grid(True, alpha=0.3)

    # Combine legends
    lines = line1 + line2 + [ax2.get_lines()[-1]]
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, fontsize=10, loc='upper left')

    plt.tight_layout()

    plot_file = output_path / "pareto_front.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_file}")
    plt.close()

    # Create additional 3D visualization if more than 20 solutions
    if len(distance) > 20:
        create_3d_visualization(distance, cot, knee_idx, output_path)


def create_3d_visualization(
    distance: np.ndarray,
    cot: np.ndarray,
    knee_idx: int,
    output_path: Path
):
    """
    Create 3D scatter plot with solution quality metric
    """
    from mpl_toolkits.mplot3d import Axes3D

    # Calculate a combined quality metric (normalized)
    dist_norm = (distance - distance.min()) / (distance.max() - distance.min() + 1e-6)
    cot_norm = (cot - cot.min()) / (cot.max() - cot.min() + 1e-6)
    quality = dist_norm - cot_norm  # Higher distance, lower CoT = better

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    scatter = ax.scatter(distance, cot, quality,
                        c=quality, cmap='viridis',
                        s=50, alpha=0.6)
    ax.scatter(distance[knee_idx], cot[knee_idx], quality[knee_idx],
              c='red', s=300, marker='*',
              edgecolors='black', linewidths=2, zorder=5)

    ax.set_xlabel('Distance (m)', fontsize=11)
    ax.set_ylabel('Cost of Transport', fontsize=11)
    ax.set_zlabel('Quality Score', fontsize=11)
    ax.set_title('3D Solution Space', fontsize=14, fontweight='bold')

    plt.colorbar(scatter, ax=ax, label='Quality Score', pad=0.1)

    plot_file = output_path / "solution_space_3d.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"3D plot saved to: {plot_file}")
    plt.close()


def compare_solutions(results: Dict, baseline_params: Dict = None):
    """
    Compare knee point solution with baseline or extreme solutions
    """
    knee = results['knee_point']
    pareto = results['pareto_front']

    distance_arr = np.array(pareto['distance'])
    cot_arr = np.array(pareto['cot'])

    max_dist_idx = np.argmax(distance_arr)
    min_cot_idx = np.argmin(cot_arr)

    print("\n" + "=" * 60)
    print("SOLUTION COMPARISON")
    print("=" * 60)

    print("\n1. Maximum Distance Solution:")
    print(f"   Distance: {distance_arr[max_dist_idx]:.2f} m")
    print(f"   CoT: {cot_arr[max_dist_idx]:.4f}")

    print("\n2. Minimum CoT Solution:")
    print(f"   Distance: {distance_arr[min_cot_idx]:.2f} m")
    print(f"   CoT: {cot_arr[min_cot_idx]:.4f}")

    print("\n3. Knee Point (Recommended):")
    print(f"   Distance: {knee['objectives']['distance']:.2f} m")
    print(f"   CoT: {knee['objectives']['cot']:.4f}")

    if baseline_params:
        print("\n4. Baseline:")
        print(f"   Parameters: {baseline_params}")
        print("   (Run simulation with these parameters to compare)")

    print("=" * 60)


if __name__ == "__main__":
    # Run optimization with surrogate model
    results = run_optimization(
        pop_size=100,
        n_gen=50,
        simulation_func=None  # Uses surrogate model
    )

    # Compare solutions
    baseline = {
        'torque_gain': 1.0,
        'phase_threshold': 0.5,
        'damping_coeff': 0.3,
        'stiffness_gain': 1.0
    }
    compare_solutions(results, baseline)

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Replace surrogate model with actual hw-1 simulation")
    print("2. Validate knee point solution in real hardware")
    print("3. Test sensitivity of Pareto front to environmental factors")
    print("4. Consider adding constraints (safety, comfort, etc.)")
    print("=" * 60)

"""
Parameter Tuning Tool for hw-1 PD Controller Gains

Supports:
- Grid search over PD gain space
- Bayesian optimization using scikit-optimize
- Parallel evaluation of parameter sets
- Multi-objective ranking (tracking, stability, energy efficiency)
- Integration with parameter_explorer if available

Based on V13.7 architecture with phase-dependent gain scheduling.
"""

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from feedback import GaitPhase, PDController


@dataclass
class ParameterSet:
    """Container for PD controller parameters."""

    kp_stance: float
    kd_stance: float
    kp_swing: float
    kd_swing: float

    def __hash__(self):
        return hash((self.kp_stance, self.kd_stance, self.kp_swing, self.kd_swing))

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Performance evaluation metrics for controller parameter set."""

    # Tracking performance
    rms_position_error: float  # RMS position tracking error [rad]
    rms_velocity_error: float  # RMS velocity tracking error [rad/s]
    max_position_error: float  # Peak position error [rad]

    # Stability metrics
    torque_saturation_ratio: float  # Fraction of steps with saturated torque
    control_effort: float  # Mean absolute torque [Nm]
    control_smoothness: float  # RMS torque derivative [Nm/s]

    # Energy efficiency
    energy_total: float  # Total energy consumed [J]
    energy_per_step: float  # Energy per gait cycle [J/cycle]

    # Distance traveled
    distance_traveled: float  # Forward distance [m]

    # Composite score (lower is better)
    composite_score: float = 0.0

    def compute_composite_score(
        self,
        w_tracking: float = 1.0,
        w_stability: float = 0.5,
        w_energy: float = 0.3,
        w_distance: float = -2.0,  # Negative = reward distance
    ) -> float:
        """
        Compute weighted composite score for multi-objective optimization.

        Args:
            w_tracking: Weight for tracking error
            w_stability: Weight for control effort/smoothness
            w_energy: Weight for energy consumption
            w_distance: Weight for distance traveled (negative = maximize)

        Returns:
            Composite score (lower is better)
        """
        tracking_cost = self.rms_position_error + 0.1 * self.rms_velocity_error
        stability_cost = 0.5 * self.control_effort + 0.5 * self.control_smoothness
        energy_cost = self.energy_per_step
        distance_reward = self.distance_traveled

        self.composite_score = (
            w_tracking * tracking_cost
            + w_stability * stability_cost
            + w_energy * energy_cost
            + w_distance * distance_reward
        )

        return self.composite_score


class SimulationEvaluator:
    """
    Evaluates controller parameter sets through simulation.

    Can be replaced with actual hardware experiments or MuJoCo simulation.
    """

    def __init__(
        self,
        simulation_duration: float = 10.0,
        dt: float = 0.001,
        torque_limit: float = 6.0,
    ):
        """
        Initialize simulation evaluator.

        Args:
            simulation_duration: Simulation time [s]
            dt: Control timestep [s]
            torque_limit: Motor torque limit [Nm]
        """
        self.duration = simulation_duration
        self.dt = dt
        self.torque_limit = torque_limit
        self.n_steps = int(simulation_duration / dt)

    def evaluate(self, params: ParameterSet) -> PerformanceMetrics:
        """
        Evaluate parameter set through simulation.

        Args:
            params: PD controller parameters to evaluate

        Returns:
            Performance metrics for this parameter set
        """
        # Create controller with specified parameters
        controller = PDController(
            kp_stance=params.kp_stance,
            kd_stance=params.kd_stance,
            kp_swing=params.kp_swing,
            kd_swing=params.kd_swing,
            torque_limit=self.torque_limit,
            enable_logging=True,
        )

        # Simulate gait cycle with sinusoidal reference trajectory
        time_array = np.linspace(0, self.duration, self.n_steps)
        gait_frequency = 1.0  # 1 Hz gait cycle

        position_errors = []
        velocity_errors = []
        torques = []
        phases = []

        for t in time_array:
            # Generate reference trajectory (sinusoidal hip angle)
            theta_ref = 0.3 * np.sin(2 * np.pi * gait_frequency * t)  # ±17 deg
            omega_ref = (
                0.3
                * 2
                * np.pi
                * gait_frequency
                * np.cos(2 * np.pi * gait_frequency * t)
            )

            # Simulate actual state with some tracking error and dynamics
            theta_actual = theta_ref + 0.05 * np.sin(5 * t)  # Simulated disturbance
            omega_actual = omega_ref + 0.1 * np.cos(3 * t)

            # Determine phase based on hip angle
            phase = GaitPhase.STANCE if theta_actual > 0 else GaitPhase.SWING
            phases.append(phase)

            # Compute errors
            e_pos = theta_ref - theta_actual
            e_vel = omega_ref - omega_actual

            # Compute control torque
            tau = controller.compute_torque(e_pos, e_vel, phase)

            position_errors.append(e_pos)
            velocity_errors.append(e_vel)
            torques.append(tau)

        # Calculate performance metrics
        position_errors = np.array(position_errors)
        velocity_errors = np.array(velocity_errors)
        torques = np.array(torques)

        rms_pos_error = np.sqrt(np.mean(position_errors**2))
        rms_vel_error = np.sqrt(np.mean(velocity_errors**2))
        max_pos_error = np.max(np.abs(position_errors))

        saturation_ratio = controller.get_saturation_ratio()
        control_effort = np.mean(np.abs(torques))

        # Control smoothness (RMS of torque derivative)
        torque_derivative = np.diff(torques) / self.dt
        control_smoothness = np.sqrt(np.mean(torque_derivative**2))

        # Energy consumption (integral of |tau * omega|)
        # Approximate omega from position trajectory
        theta_trajectory = 0.3 * np.sin(2 * np.pi * gait_frequency * time_array)
        omega_trajectory = np.gradient(theta_trajectory, self.dt)
        power = np.abs(torques * omega_trajectory)
        energy_total = np.trapz(power, dx=self.dt)

        # Estimate gait cycles and energy per cycle
        n_cycles = gait_frequency * self.duration
        energy_per_step = energy_total / n_cycles if n_cycles > 0 else energy_total

        # Distance traveled (approximate from hip kinematics)
        # Assume stride length ~0.7 m per cycle
        distance_traveled = 0.7 * n_cycles

        metrics = PerformanceMetrics(
            rms_position_error=rms_pos_error,
            rms_velocity_error=rms_vel_error,
            max_position_error=max_pos_error,
            torque_saturation_ratio=saturation_ratio,
            control_effort=control_effort,
            control_smoothness=control_smoothness,
            energy_total=energy_total,
            energy_per_step=energy_per_step,
            distance_traveled=distance_traveled,
        )

        metrics.compute_composite_score()

        return metrics


class GridSearchTuner:
    """Grid search over PD controller parameter space."""

    def __init__(
        self,
        evaluator: SimulationEvaluator,
        kp_stance_range: Tuple[float, float, int] = (40.0, 120.0, 5),
        kd_stance_range: Tuple[float, float, int] = (4.0, 12.0, 5),
        kp_swing_range: Tuple[float, float, int] = (20.0, 60.0, 5),
        kd_swing_range: Tuple[float, float, int] = (2.0, 8.0, 5),
        parallel: bool = True,
        max_workers: int = 4,
    ):
        """
        Initialize grid search tuner.

        Args:
            evaluator: Simulation evaluator instance
            kp_stance_range: (min, max, n_points) for stance kp
            kd_stance_range: (min, max, n_points) for stance kd
            kp_swing_range: (min, max, n_points) for swing kp
            kd_swing_range: (min, max, n_points) for swing kd
            parallel: Enable parallel evaluation
            max_workers: Number of parallel workers
        """
        self.evaluator = evaluator
        self.parallel = parallel
        self.max_workers = max_workers

        # Generate parameter grid
        kp_stance_grid = np.linspace(*kp_stance_range)
        kd_stance_grid = np.linspace(*kd_stance_range)
        kp_swing_grid = np.linspace(*kp_swing_range)
        kd_swing_grid = np.linspace(*kd_swing_range)

        self.parameter_sets = []
        for kp_st in kp_stance_grid:
            for kd_st in kd_stance_grid:
                for kp_sw in kp_swing_grid:
                    for kd_sw in kd_swing_grid:
                        self.parameter_sets.append(
                            ParameterSet(kp_st, kd_st, kp_sw, kd_sw)
                        )

        print(f"Grid search initialized with {len(self.parameter_sets)} parameter sets")

    def run(self) -> List[Tuple[ParameterSet, PerformanceMetrics]]:
        """
        Execute grid search.

        Returns:
            List of (params, metrics) tuples sorted by performance
        """
        results = []

        if self.parallel:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.evaluator.evaluate, params): params
                    for params in self.parameter_sets
                }

                completed = 0
                for future in as_completed(futures):
                    params = futures[future]
                    try:
                        metrics = future.result()
                        results.append((params, metrics))
                        completed += 1
                        if completed % 10 == 0:
                            print(
                                f"Evaluated {completed}/{len(self.parameter_sets)} parameter sets"
                            )
                    except Exception as e:
                        print(f"Error evaluating {params}: {e}")
        else:
            for i, params in enumerate(self.parameter_sets):
                try:
                    metrics = self.evaluator.evaluate(params)
                    results.append((params, metrics))
                    if (i + 1) % 10 == 0:
                        print(
                            f"Evaluated {i+1}/{len(self.parameter_sets)} parameter sets"
                        )
                except Exception as e:
                    print(f"Error evaluating {params}: {e}")

        # Sort by composite score (lower is better)
        results.sort(key=lambda x: x[1].composite_score)

        return results


class BayesianOptimizationTuner:
    """Bayesian optimization for PD controller parameters using scikit-optimize."""

    def __init__(
        self,
        evaluator: SimulationEvaluator,
        kp_stance_bounds: Tuple[float, float] = (40.0, 120.0),
        kd_stance_bounds: Tuple[float, float] = (4.0, 12.0),
        kp_swing_bounds: Tuple[float, float] = (20.0, 60.0),
        kd_swing_bounds: Tuple[float, float] = (2.0, 8.0),
        n_calls: int = 50,
        n_initial_points: int = 10,
        random_state: int = 42,
    ):
        """
        Initialize Bayesian optimization tuner.

        Args:
            evaluator: Simulation evaluator instance
            kp_stance_bounds: (min, max) for stance kp
            kd_stance_bounds: (min, max) for stance kd
            kp_swing_bounds: (min, max) for swing kp
            kd_swing_bounds: (min, max) for swing kd
            n_calls: Number of optimization iterations
            n_initial_points: Number of random exploration points
            random_state: Random seed for reproducibility
        """
        self.evaluator = evaluator
        self.bounds = [
            kp_stance_bounds,
            kd_stance_bounds,
            kp_swing_bounds,
            kd_swing_bounds,
        ]
        self.n_calls = n_calls
        self.n_initial_points = n_initial_points
        self.random_state = random_state

        # Try to import scikit-optimize
        try:
            from skopt import gp_minimize
            from skopt.space import Real

            self.gp_minimize = gp_minimize
            self.Real = Real
            self.available = True
        except ImportError:
            print(
                "WARNING: scikit-optimize not available. Install with: pip install scikit-optimize"
            )
            self.available = False

    def _objective(self, x: List[float]) -> float:
        """
        Objective function for optimization.

        Args:
            x: [kp_stance, kd_stance, kp_swing, kd_swing]

        Returns:
            Composite performance score (to minimize)
        """
        params = ParameterSet(
            kp_stance=x[0], kd_stance=x[1], kp_swing=x[2], kd_swing=x[3]
        )

        metrics = self.evaluator.evaluate(params)
        return metrics.composite_score

    def run(self) -> List[Tuple[ParameterSet, PerformanceMetrics]]:
        """
        Execute Bayesian optimization.

        Returns:
            List of (params, metrics) tuples sorted by performance
        """
        if not self.available:
            raise RuntimeError("scikit-optimize not available")

        space = [
            self.Real(*bounds, name=name)
            for bounds, name in zip(
                self.bounds, ["kp_stance", "kd_stance", "kp_swing", "kd_swing"]
            )
        ]

        print(f"Starting Bayesian optimization with {self.n_calls} iterations...")

        result = self.gp_minimize(
            func=self._objective,
            dimensions=space,
            n_calls=self.n_calls,
            n_initial_points=self.n_initial_points,
            random_state=self.random_state,
            verbose=True,
        )

        # Extract all evaluated parameter sets
        results = []
        for x_eval, y_eval in zip(result.x_iters, result.func_vals):
            params = ParameterSet(
                kp_stance=x_eval[0],
                kd_stance=x_eval[1],
                kp_swing=x_eval[2],
                kd_swing=x_eval[3],
            )
            # Re-evaluate to get full metrics
            metrics = self.evaluator.evaluate(params)
            results.append((params, metrics))

        # Sort by composite score
        results.sort(key=lambda x: x[1].composite_score)

        return results


def save_results(
    results: List[Tuple[ParameterSet, PerformanceMetrics]],
    output_path: Path,
    top_n: int = 10,
):
    """
    Save tuning results to JSON file.

    Args:
        results: List of (params, metrics) tuples
        output_path: Output file path
        top_n: Number of top results to save
    """
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_evaluated": len(results),
        "top_results": [],
    }

    for rank, (params, metrics) in enumerate(results[:top_n], 1):
        output_data["top_results"].append(
            {"rank": rank, "parameters": params.to_dict(), "metrics": asdict(metrics)}
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_path}")


def print_results(
    results: List[Tuple[ParameterSet, PerformanceMetrics]], top_n: int = 5
):
    """
    Print top tuning results to console.

    Args:
        results: List of (params, metrics) tuples
        top_n: Number of top results to print
    """
    print(f"\n{'='*80}")
    print(f"TOP {top_n} PARAMETER SETS")
    print(f"{'='*80}\n")

    for rank, (params, metrics) in enumerate(results[:top_n], 1):
        print(f"Rank {rank}:")
        print("  Parameters:")
        print(f"    kp_stance={params.kp_stance:.2f}, kd_stance={params.kd_stance:.2f}")
        print(f"    kp_swing={params.kp_swing:.2f}, kd_swing={params.kd_swing:.2f}")
        print("  Performance:")
        print(f"    Composite Score: {metrics.composite_score:.4f}")
        print(f"    RMS Position Error: {metrics.rms_position_error:.4f} rad")
        print(f"    Control Effort: {metrics.control_effort:.3f} Nm")
        print(f"    Energy/Step: {metrics.energy_per_step:.3f} J")
        print(f"    Distance: {metrics.distance_traveled:.2f} m")
        print(f"    Saturation: {metrics.torque_saturation_ratio:.1%}")
        print()


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parameter tuning tool for hw-1 PD controller"
    )
    parser.add_argument(
        "--method",
        choices=["grid", "bayesian"],
        default="grid",
        help="Optimization method (default: grid)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Simulation duration in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel evaluation (grid search only)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--n-calls",
        type=int,
        default=50,
        help="Number of iterations for Bayesian optimization (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tuning_results.json",
        help="Output file path (default: tuning_results.json)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top results to save/display (default: 10)",
    )

    args = parser.parse_args()

    # Initialize evaluator
    evaluator = SimulationEvaluator(
        simulation_duration=args.duration, dt=0.001, torque_limit=6.0
    )

    # Run optimization
    if args.method == "grid":
        tuner = GridSearchTuner(
            evaluator=evaluator, parallel=args.parallel, max_workers=args.workers
        )
    else:  # bayesian
        tuner = BayesianOptimizationTuner(evaluator=evaluator, n_calls=args.n_calls)

    print(f"Starting {args.method} optimization...")
    start_time = time.time()

    results = tuner.run()

    elapsed_time = time.time() - start_time
    print(f"\nOptimization completed in {elapsed_time:.2f} seconds")

    # Display and save results
    print_results(results, top_n=args.top_n)

    output_path = Path(args.output)
    save_results(results, output_path, top_n=args.top_n)

    # Print best parameters for easy copy-paste
    best_params, best_metrics = results[0]
    print(f"\n{'='*80}")
    print("BEST PARAMETERS (copy-paste ready):")
    print(f"{'='*80}")
    print(f"kp_stance={best_params.kp_stance:.2f}")
    print(f"kd_stance={best_params.kd_stance:.2f}")
    print(f"kp_swing={best_params.kp_swing:.2f}")
    print(f"kd_swing={best_params.kd_swing:.2f}")
    print(f"# Composite score: {best_metrics.composite_score:.4f}")


if __name__ == "__main__":
    main()

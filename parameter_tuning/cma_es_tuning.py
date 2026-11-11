"""
CMA-ES (Covariance Matrix Adaptation Evolution Strategy) Parameter Tuning

CMA-ES is particularly effective for:
- High-dimensional continuous parameter spaces
- Non-convex, noisy objective functions
- Problems where gradient information is unavailable
- Robust optimization without extensive hyperparameter tuning

Usage:
    python cma_es_tuning.py --config config.yaml --generations 100
"""

import argparse
import json
import logging
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import cma
import numpy as np
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CMAESOptimizer:
    """
    CMA-ES optimizer for gait phase detection parameters

    Advantages over grid search:
    - Efficiently explores high-dimensional spaces
    - Adaptive step size control
    - Handles parameter correlations
    - Natural handling of noise in objective function
    """

    def __init__(
        self,
        param_bounds: Dict[str, Tuple[float, float]],
        population_size: Optional[int] = None,
        sigma0: float = 0.3,
        seed: Optional[int] = None,
    ):
        """
        Initialize CMA-ES optimizer

        Args:
            param_bounds: Dictionary mapping parameter names to (min, max) bounds
            population_size: Number of samples per generation (default: 4 + 3*log(n))
            sigma0: Initial standard deviation (relative to parameter range)
            seed: Random seed for reproducibility
        """
        self.param_names = list(param_bounds.keys())
        self.bounds = np.array([param_bounds[name] for name in self.param_names])
        self.n_params = len(self.param_names)

        # Normalize bounds to [0, 1]
        self.lb = self.bounds[:, 0]
        self.ub = self.bounds[:, 1]
        self.range = self.ub - self.lb

        # Initial guess (center of parameter space)
        self.x0 = np.full(self.n_params, 0.5)

        # CMA-ES options
        self.opts = {
            "bounds": [0, 1],
            "seed": seed,
            "verbose": -1,  # Suppress CMA-ES output
        }

        if population_size is not None:
            self.opts["popsize"] = population_size

        self.sigma0 = sigma0

        # Results storage
        self.history = []
        self.best_params = None
        self.best_score = float("inf")

    def denormalize_params(self, x_norm: np.ndarray) -> Dict[str, float]:
        """Convert normalized [0,1] parameters to actual values"""
        x_actual = self.lb + x_norm * self.range
        return {name: float(val) for name, val in zip(self.param_names, x_actual)}

    def normalize_params(self, params: Dict[str, float]) -> np.ndarray:
        """Convert actual parameter values to normalized [0,1]"""
        x_actual = np.array([params[name] for name in self.param_names])
        return (x_actual - self.lb) / self.range

    def optimize(
        self,
        objective_func: Callable,
        max_generations: int = 100,
        target_score: Optional[float] = None,
        callback: Optional[Callable] = None,
        parallel: bool = True,
        n_jobs: int = -1,
    ) -> Tuple[Dict[str, float], float]:
        """
        Run CMA-ES optimization

        Args:
            objective_func: Function that takes parameter dict and returns scalar cost
            max_generations: Maximum number of generations
            target_score: Stop if this score is reached
            callback: Optional function called after each generation
            parallel: Use parallel evaluation of population
            n_jobs: Number of parallel jobs (-1 for all cores)

        Returns:
            best_params: Best parameter configuration found
            best_score: Best score achieved
        """
        logger.info(f"Starting CMA-ES optimization with {self.n_params} parameters")
        logger.info(
            f"Population size: {self.opts.get('popsize', 4 + int(3 * np.log(self.n_params)))}"
        )

        # Initialize CMA-ES
        es = cma.CMAEvolutionStrategy(self.x0, self.sigma0, self.opts)

        generation = 0

        if parallel and n_jobs != 1:
            if n_jobs == -1:
                n_jobs = mp.cpu_count()
            pool = mp.Pool(processes=n_jobs)
            logger.info(f"Using {n_jobs} parallel workers")

        try:
            while not es.stop() and generation < max_generations:
                generation += 1

                # Generate new population
                solutions_norm = es.ask()

                # Evaluate population
                if parallel and n_jobs != 1:
                    # Parallel evaluation
                    params_list = [self.denormalize_params(x) for x in solutions_norm]
                    fitness_values = pool.map(objective_func, params_list)
                else:
                    # Sequential evaluation
                    fitness_values = []
                    for x_norm in solutions_norm:
                        params = self.denormalize_params(x_norm)
                        fitness_values.append(objective_func(params))

                # Update CMA-ES
                es.tell(solutions_norm, fitness_values)

                # Track best solution
                best_idx = np.argmin(fitness_values)
                gen_best_score = fitness_values[best_idx]
                gen_best_params = self.denormalize_params(solutions_norm[best_idx])

                if gen_best_score < self.best_score:
                    self.best_score = gen_best_score
                    self.best_params = gen_best_params

                # Record history
                self.history.append(
                    {
                        "generation": generation,
                        "best_score": self.best_score,
                        "gen_best_score": gen_best_score,
                        "mean_score": np.mean(fitness_values),
                        "std_score": np.std(fitness_values),
                        "sigma": es.sigma,
                        "params": gen_best_params,
                    }
                )

                # Logging
                logger.info(
                    f"Gen {generation:3d} | Best: {self.best_score:.6f} | "
                    f"Gen Best: {gen_best_score:.6f} | "
                    f"Mean: {np.mean(fitness_values):.6f} | "
                    f"Sigma: {es.sigma:.4f}"
                )

                # Callback
                if callback is not None:
                    callback(
                        generation, self.best_params, self.best_score, self.history
                    )

                # Early stopping
                if target_score is not None and self.best_score <= target_score:
                    logger.info(f"Target score {target_score} reached!")
                    break

        finally:
            if parallel and n_jobs != 1:
                pool.close()
                pool.join()

        # Final logging
        logger.info("=" * 60)
        logger.info("Optimization complete!")
        logger.info(f"Best score: {self.best_score:.6f}")
        logger.info("Best parameters:")
        for name, value in self.best_params.items():
            logger.info(f"  {name}: {value:.6f}")

        return self.best_params, self.best_score

    def save_results(self, output_path: str):
        """Save optimization results to file"""
        results = {
            "best_params": self.best_params,
            "best_score": float(self.best_score),
            "history": self.history,
            "n_generations": len(self.history),
            "timestamp": datetime.now().isoformat(),
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_path}")


def create_objective_function(
    config: Dict, test_data_path: str, metric: str = "f1_score"
) -> Callable:
    """
    Create objective function for CMA-ES

    This should be adapted to your specific evaluation pipeline
    """

    def objective(params: Dict[str, float]) -> float:
        """
        Objective function to minimize

        Args:
            params: Dictionary of parameters to evaluate

        Returns:
            cost: Scalar cost (lower is better)
        """
        try:
            # TODO: Replace with actual evaluation logic
            # Example structure:
            # 1. Load test data
            # 2. Initialize detector with params
            # 3. Run detection
            # 4. Compute metrics
            # 5. Return negative metric (since we minimize)

            # Placeholder: random evaluation
            # In practice, this should call your gait detection system
            cost = np.random.rand()  # Replace with actual evaluation

            # For maximizing metric (like F1), return negative
            return -cost  # or: return 1.0 - cost

        except Exception as e:
            logger.error(f"Error evaluating params: {e}")
            return float("inf")  # Penalize invalid configurations

    return objective


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="CMA-ES Parameter Tuning")
    parser.add_argument(
        "--config", type=str, required=True, help="Path to configuration YAML file"
    )
    parser.add_argument(
        "--test-data", type=str, required=True, help="Path to test data"
    )
    parser.add_argument(
        "--generations", type=int, default=100, help="Maximum number of generations"
    )
    parser.add_argument(
        "--population-size",
        type=int,
        default=None,
        help="Population size (default: auto)",
    )
    parser.add_argument("--sigma", type=float, default=0.3, help="Initial step size")
    parser.add_argument(
        "--metric",
        type=str,
        default="f1_score",
        choices=["f1_score", "accuracy", "precision", "recall"],
        help="Metric to optimize",
    )
    parser.add_argument(
        "--target-score",
        type=float,
        default=None,
        help="Target score for early stopping",
    )
    parser.add_argument(
        "--output", type=str, default="cma_results.json", help="Output file for results"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--no-parallel", action="store_true", help="Disable parallel evaluation"
    )
    parser.add_argument(
        "--n-jobs", type=int, default=-1, help="Number of parallel jobs (-1 for all)"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Define parameter bounds
    param_bounds = config.get(
        "parameter_bounds",
        {
            # Example bounds - customize for your parameters
            "swing_threshold": (0.1, 0.9),
            "stance_threshold": (0.1, 0.9),
            "min_phase_duration": (0.05, 0.5),
            "smoothing_window": (1, 20),
            "velocity_weight": (0.0, 1.0),
            "acceleration_weight": (0.0, 1.0),
        },
    )

    # Initialize optimizer
    optimizer = CMAESOptimizer(
        param_bounds=param_bounds,
        population_size=args.population_size,
        sigma0=args.sigma,
        seed=args.seed,
    )

    # Create objective function
    objective_func = create_objective_function(
        config=config, test_data_path=args.test_data, metric=args.metric
    )

    # Run optimization
    best_params, best_score = optimizer.optimize(
        objective_func=objective_func,
        max_generations=args.generations,
        target_score=args.target_score,
        parallel=not args.no_parallel,
        n_jobs=args.n_jobs,
    )

    # Save results
    optimizer.save_results(args.output)

    # Print summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(
        f"Best {args.metric}: {-best_score:.6f}"
    )  # Negate if minimizing negative metric
    print("\nBest Parameters:")
    for name, value in best_params.items():
        print(f"  {name:25s}: {value:.6f}")
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()

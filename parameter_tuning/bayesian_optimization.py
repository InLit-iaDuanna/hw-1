"""Bayesian optimization for V13.7 FSM PD gains using Optuna.

Optimizes 8 parameters (Kp/Kd per phase: stance_early, stance_late, swing_thrust, swing_retract)
to maximize forward distance traveled in simulation.

Usage:
    python bayesian_optimization.py --n_trials 100 --output results/bo_v137_gains.json
    python bayesian_optimization.py --resume results/bo_v137_gains.json --n_trials 50
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import optuna
from optuna.samplers import TPESampler

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14_DIR = HW1_ROOT / "v14_passive_arms"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))

from simulate_passive_arms_v14 import PassiveArmsParams  # noqa: E402
from simulate_v13_6 import PhaseParams, V136Params  # noqa: E402
from simulate_v13_7 import (  # noqa: E402
    V137Params,
    run_simulation_v137,
)

OUT_DIR = ROOT / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Search bounds for PD gains (based on V13.6 baseline ranges)
BOUNDS = {
    # Stance phases: strong tracking, high Kp/Kd
    "stance_early_kp": (10.0, 50.0),
    "stance_early_kd": (2.0, 12.0),
    "stance_late_kp": (10.0, 50.0),
    "stance_late_kd": (2.0, 12.0),
    # Swing thrust: moderate Kp (energy shaping dominates), moderate Kd
    "swing_thrust_kp": (5.0, 30.0),
    "swing_thrust_kd": (2.0, 12.0),
    # Swing retract: weak tracking, low Kp/Kd
    "swing_retract_kp": (5.0, 40.0),
    "swing_retract_kd": (2.0, 12.0),
}

# Fixed parameters (not optimized)
FIXED_PARAMS = {
    "stance_early": {"k_E": 0.0, "tau_max": 4.0, "E_target": 52.66},
    "stance_late": {"k_E": 0.0, "tau_max": 4.0, "E_target": 52.66},
    "swing_thrust": {"k_E": 7.5, "tau_max": 4.0, "E_target": 52.66},
    "swing_retract": {"k_E": 0.0, "tau_max": 2.0, "E_target": 52.66},
}

# Simulation settings
SIM_DURATION = 8.0  # seconds
SUCCESS_FORWARD = 1.5  # meters


def create_params_from_trial(trial: optuna.Trial) -> V137Params:
    """Build V137Params from Optuna trial suggestions."""

    # Suggest PD gains
    gains = {
        name: trial.suggest_float(name, *bounds) for name, bounds in BOUNDS.items()
    }

    # Build phase parameters
    stance_early = PhaseParams(
        k_E=FIXED_PARAMS["stance_early"]["k_E"],
        k_PD=gains["stance_early_kp"],
        tau_max=FIXED_PARAMS["stance_early"]["tau_max"],
        kd=gains["stance_early_kd"],
        E_target=FIXED_PARAMS["stance_early"]["E_target"],
    )

    stance_late = PhaseParams(
        k_E=FIXED_PARAMS["stance_late"]["k_E"],
        k_PD=gains["stance_late_kp"],
        tau_max=FIXED_PARAMS["stance_late"]["tau_max"],
        kd=gains["stance_late_kd"],
        E_target=FIXED_PARAMS["stance_late"]["E_target"],
    )

    swing_thrust = PhaseParams(
        k_E=FIXED_PARAMS["swing_thrust"]["k_E"],
        k_PD=gains["swing_thrust_kp"],
        tau_max=FIXED_PARAMS["swing_thrust"]["tau_max"],
        kd=gains["swing_thrust_kd"],
        E_target=FIXED_PARAMS["swing_thrust"]["E_target"],
    )

    swing_retract = PhaseParams(
        k_E=FIXED_PARAMS["swing_retract"]["k_E"],
        k_PD=gains["swing_retract_kp"],
        tau_max=FIXED_PARAMS["swing_retract"]["tau_max"],
        kd=gains["swing_retract_kd"],
        E_target=FIXED_PARAMS["swing_retract"]["E_target"],
    )

    # Build FSM params
    base_params = PassiveArmsParams()
    fsm_params = V136Params(
        base=base_params,
        stance_early=stance_early,
        stance_late=stance_late,
        swing_thrust=swing_thrust,
        swing_retract=swing_retract,
    )

    # Build V137 params with default motors and friction compensation
    v137_params = V137Params(
        base=base_params,
        fsm=fsm_params,
        compensate_friction=True,
    )

    return v137_params


def objective(trial: optuna.Trial) -> float:
    """Objective function: maximize forward distance traveled."""

    try:
        params = create_params_from_trial(trial)

        # Run simulation with reduced duration
        params_short = replace(params, base=replace(params.base, duration=SIM_DURATION))
        result = run_simulation_v137(params_short, save_prefix=None, sample_hz=50.0)

        forward_distance = result.get("forward_distance", 0.0)
        failure_mode = result.get("failure_mode", "unknown")

        # Store metadata for later analysis
        trial.set_user_attr("forward_distance", forward_distance)
        trial.set_user_attr("failure_mode", failure_mode)
        trial.set_user_attr("success", forward_distance >= SUCCESS_FORWARD)
        trial.set_user_attr("simulation_time", result.get("final_time", 0.0))
        trial.set_user_attr("touchdowns", result.get("contact_events", 0))

        # Return negative distance for minimization (Optuna minimizes by default)
        # We want to maximize distance, so return negative
        return -forward_distance

    except Exception as e:
        print(f"Trial {trial.number} failed with error: {e}")
        trial.set_user_attr("error", str(e))
        trial.set_user_attr("forward_distance", 0.0)
        trial.set_user_attr("failure_mode", "simulation_error")
        return 0.0  # Penalty for failed simulations


def save_results(study: optuna.Study, output_path: Path) -> None:
    """Save optimization history and best parameters to JSON."""

    trials_data = []
    for trial in study.trials:
        trial_dict = {
            "number": trial.number,
            "value": trial.value,
            "params": trial.params,
            "state": trial.state.name,
            "user_attrs": trial.user_attrs,
            "datetime_start": (
                trial.datetime_start.isoformat() if trial.datetime_start else None
            ),
            "datetime_complete": (
                trial.datetime_complete.isoformat() if trial.datetime_complete else None
            ),
            "duration": trial.duration.total_seconds() if trial.duration else None,
        }
        trials_data.append(trial_dict)

    best_trial = study.best_trial

    results = {
        "best_params": best_trial.params,
        "best_value": best_trial.value,
        "best_forward_distance": best_trial.user_attrs.get("forward_distance", 0.0),
        "best_trial_number": best_trial.number,
        "n_trials": len(study.trials),
        "study_name": study.study_name,
        "trials": trials_data,
        "optimization_bounds": BOUNDS,
        "fixed_params": FIXED_PARAMS,
    }

    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


def print_best_results(study: optuna.Study) -> None:
    """Print best trial results."""

    best_trial = study.best_trial

    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"\nBest trial number: {best_trial.number}")
    print(f"Best forward distance: {-best_trial.value:.3f} m")
    print(f"Success: {best_trial.user_attrs.get('success', False)}")
    print(f"Failure mode: {best_trial.user_attrs.get('failure_mode', 'N/A')}")
    print(f"Touchdowns: {best_trial.user_attrs.get('touchdowns', 0)}")

    print("\nBest parameters:")
    print("-" * 80)
    for phase in ["stance_early", "stance_late", "swing_thrust", "swing_retract"]:
        kp = best_trial.params[f"{phase}_kp"]
        kd = best_trial.params[f"{phase}_kd"]
        print(f"  {phase:15s}: k_PD={kp:6.2f}, kd={kd:5.2f}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Bayesian optimization of V13.7 FSM PD gains"
    )
    parser.add_argument(
        "--n_trials",
        type=int,
        default=100,
        help="Number of optimization trials (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bo_v137_gains.json",
        help="Output JSON file for results (default: bo_v137_gains.json)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from existing study JSON file",
    )
    parser.add_argument(
        "--study_name",
        type=str,
        default="v137_pd_gains_optimization",
        help="Optuna study name (default: v137_pd_gains_optimization)",
    )
    parser.add_argument(
        "--n_startup_trials",
        type=int,
        default=20,
        help="Number of random sampling trials before TPE (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    output_path = OUT_DIR / args.output

    # Create sampler (TPE with Gaussian Process-like behavior)
    sampler = TPESampler(
        n_startup_trials=args.n_startup_trials,
        seed=args.seed,
        multivariate=True,  # Consider parameter correlations
        group=True,  # Group correlated parameters
    )

    # Create or load study
    study = optuna.create_study(
        study_name=args.study_name,
        direction="minimize",  # Minimize negative distance = maximize distance
        sampler=sampler,
        load_if_exists=(args.resume is not None),
    )

    # Resume from checkpoint if specified
    if args.resume:
        resume_path = Path(args.resume)
        if resume_path.exists():
            print(f"Resuming from {resume_path}")
            # Note: Optuna uses SQLite or in-memory storage
            # For file-based resume, we'd need to implement custom logic
            # Here we just inform the user
            print("Note: Full state resume requires Optuna storage backend.")
            print("Starting fresh study with specified parameters.")

    print(f"Starting Bayesian optimization: {args.n_trials} trials")
    print(f"Study name: {args.study_name}")
    print(f"Sampler: TPE with {args.n_startup_trials} startup trials")
    print(f"Seed: {args.seed}")
    print(f"Output: {output_path}")
    print("\nOptimization bounds:")
    for name, (low, high) in BOUNDS.items():
        print(f"  {name:25s}: [{low:6.2f}, {high:6.2f}]")
    print("\n" + "=" * 80)

    # Run optimization
    study.optimize(
        objective,
        n_trials=args.n_trials,
        show_progress_bar=True,
        n_jobs=1,  # Sequential execution (MuJoCo not thread-safe by default)
    )

    # Save and print results
    save_results(study, output_path)
    print_best_results(study)

    # Print top 5 trials
    print("\nTop 5 trials:")
    print("-" * 80)
    top_trials = sorted(
        study.trials, key=lambda t: t.value if t.value is not None else float("inf")
    )[:5]
    for i, trial in enumerate(top_trials, 1):
        dist = -trial.value if trial.value is not None else 0.0
        success = trial.user_attrs.get("success", False)
        print(f"{i}. Trial {trial.number:3d}: {dist:6.3f} m, success={success}")


if __name__ == "__main__":
    main()

"""Phase-Gated Residual Search using CMA-ES.

Optimize 8D phase-gated residual torques (4 phases × 2 hip joints).
Goal: Surpass constant residual baseline (4.973m).

Phase-gated residual applies smooth transitions between phases:
- stance_early, stance_late, swing_thrust, swing_retract (per leg)
- Smooth interpolation using smoothstep during phase transitions
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14_DIR = HW1_ROOT / "v14_passive_arms"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))

import mujoco
from simulate_passive_arms_v14 import (
    PassiveArmsParams,
    classify_failure,
    contact_flags,
    initialize,
)
from simulate_v13_6 import control_v136
from simulate_v13_7 import (
    MODEL_PATH,
    V137Params,
    _compensate,
    _mechanical_energy,
    write_model_v137,
)
from simulate_v14c import make_v14c_params

from common.motor_dynamics import PRESETS as MOTOR_PRESETS
from common.motor_dynamics import L1MotorActuator


@dataclass
class PhaseGatedParams:
    """8D phase-gated residual parameters."""

    # Left hip torques per phase (N·m)
    left_stance_early: float
    left_stance_late: float
    left_swing_thrust: float
    left_swing_retract: float

    # Right hip torques per phase (N·m)
    right_stance_early: float
    right_stance_late: float
    right_swing_thrust: float
    right_swing_retract: float

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                self.left_stance_early,
                self.left_stance_late,
                self.left_swing_thrust,
                self.left_swing_retract,
                self.right_stance_early,
                self.right_stance_late,
                self.right_swing_thrust,
                self.right_swing_retract,
            ]
        )

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "PhaseGatedParams":
        return cls(
            left_stance_early=float(arr[0]),
            left_stance_late=float(arr[1]),
            left_swing_thrust=float(arr[2]),
            left_swing_retract=float(arr[3]),
            right_stance_early=float(arr[4]),
            right_stance_late=float(arr[5]),
            right_swing_thrust=float(arr[6]),
            right_swing_retract=float(arr[7]),
        )


def smoothstep(x: float, edge0: float = 0.0, edge1: float = 1.0) -> float:
    """Smooth Hermite interpolation between edge0 and edge1."""
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def get_phase_residual(
    phase_params: PhaseGatedParams,
    left_phase: str,
    right_phase: str,
    left_phase_progress: float,
    right_phase_progress: float,
) -> Tuple[float, float]:
    """Get interpolated residual torques for current phase state.

    Args:
        phase_params: 8D phase-gated parameters
        left_phase: Current left leg phase name
        right_phase: Current right leg phase name
        left_phase_progress: Progress in left phase [0, 1]
        right_phase_progress: Progress in right phase [0, 1]

    Returns:
        (left_hip_residual, right_hip_residual) in N·m
    """
    # Map phase names to parameter indices
    phase_map_left = {
        "stance_early": phase_params.left_stance_early,
        "stance_late": phase_params.left_stance_late,
        "swing_thrust": phase_params.left_swing_thrust,
        "swing_retract": phase_params.left_swing_retract,
    }
    phase_map_right = {
        "stance_early": phase_params.right_stance_early,
        "stance_late": phase_params.right_stance_late,
        "swing_thrust": phase_params.right_swing_thrust,
        "swing_retract": phase_params.right_swing_retract,
    }

    # Get current phase torques
    left_residual = phase_map_left.get(left_phase, 0.0)
    right_residual = phase_map_right.get(right_phase, 0.0)

    # Simple version: no inter-phase interpolation for now
    # (Could add smooth transitions later if needed)

    return left_residual, right_residual


def evaluate_phase_gated(
    params_8d: np.ndarray,
    episodes: int = 10,
    duration: float = 12.0,
    verbose: bool = False,
) -> Dict:
    """Evaluate 8D phase-gated residual.

    Args:
        params_8d: [left_early, left_late, left_thrust, left_retract,
                    right_early, right_late, right_thrust, right_retract]
        episodes: Number of episodes to average
        duration: Simulation duration in seconds
        verbose: Print per-episode results

    Returns:
        Dictionary with mean_distance, failure_rate, energy_cost
    """
    phase_params = PhaseGatedParams.from_array(params_8d)

    # Setup V13.7 params
    base_params = PassiveArmsParams()
    from dataclasses import replace

    base_params = replace(
        base_params,
        duration=duration,
        slope_deg=0.0,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        thigh_length=float(base_params.thigh_length * 1.02),
        shank_length=float(base_params.shank_length * 1.02),
        step_length=float(base_params.step_length * 1.02),
        foot_radius=0.042,
    )

    fsm_params = make_v14c_params(base_params)
    v137_params = V137Params(
        base=base_params,
        fsm=fsm_params,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
        compensate_friction=True,
    )

    # Write model
    write_model_v137(v137_params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    distances = []
    failures = []
    energy_costs = []

    for ep in range(episodes):
        data = mujoco.MjData(model)

        # Initialize
        initialize(model, data, base_params)

        # Setup FSM state
        support_foot = "left"
        burst_start_t = 0.0
        contact_data = {"left": 0, "right": 0}

        # Setup actuators
        actuators = {
            "left_hip": L1MotorActuator(v137_params.hip_motor),
            "left_knee": L1MotorActuator(v137_params.knee_motor),
            "right_hip": L1MotorActuator(v137_params.hip_motor),
            "right_knee": L1MotorActuator(v137_params.knee_motor),
        }

        # Joint address lookup
        qvel_addr = {
            "left_hip": mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_JOINT, "left_hip_joint"
            ),
            "left_knee": mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_JOINT, "left_knee_joint"
            ),
            "right_hip": mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_JOINT, "right_hip_joint"
            ),
            "right_knee": mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_JOINT, "right_knee_joint"
            ),
        }

        last_contact_t = -1.0
        candidate_start_t = {"left": None, "right": None}
        contact_reported = {"left": False, "right": False}

        micro_steps = 0
        dt = 0.001
        max_steps = int(duration / dt)
        total_energy = 0.0

        failed = False
        failure_type = "success"

        for step in range(max_steps):
            t = micro_steps * dt

            # FSM state update (contact detection)
            left_c, right_c = contact_flags(model, data)
            contacts = {"left": left_c, "right": right_c}

            for foot, has_contact in contacts.items():
                if has_contact:
                    if candidate_start_t[foot] is None:
                        candidate_start_t[foot] = t
                        contact_reported[foot] = False
                    elif (
                        t - candidate_start_t[foot]
                        >= base_params.contact_latch_duration
                    ):
                        if not contact_reported[foot]:
                            support_foot = foot
                            burst_start_t = t
                            last_contact_t = t
                            contact_reported[foot] = True
                            contact_data[foot] += 1
                else:
                    candidate_start_t[foot] = None
                    contact_reported[foot] = False

            # V13.6 FSM control
            E_current = _mechanical_energy(base_params, data)
            tau = control_v136(
                fsm_params, data, t, support_foot, burst_start_t, E_current
            )

            l_hip_des, l_knee_des = tau[0], tau[1]
            r_hip_des, r_knee_des = tau[2], tau[3]
            left_phase, right_phase = str(tau[5]), str(tau[6])

            # Friction compensation
            if v137_params.compensate_friction:
                l_hip_des = _compensate(
                    l_hip_des,
                    float(data.qvel[qvel_addr["left_hip"]]),
                    v137_params.hip_motor,
                )
                l_knee_des = _compensate(
                    l_knee_des,
                    float(data.qvel[qvel_addr["left_knee"]]),
                    v137_params.knee_motor,
                )
                r_hip_des = _compensate(
                    r_hip_des,
                    float(data.qvel[qvel_addr["right_hip"]]),
                    v137_params.hip_motor,
                )
                r_knee_des = _compensate(
                    r_knee_des,
                    float(data.qvel[qvel_addr["right_knee"]]),
                    v137_params.knee_motor,
                )

            # Add phase-gated residual (hip only)
            left_residual, right_residual = get_phase_residual(
                phase_params, left_phase, right_phase, 0.5, 0.5
            )
            l_hip_des += left_residual
            r_hip_des += right_residual

            # L1 motor model
            l_hip_out, _ = actuators["left_hip"].compute_actual_torque(
                l_hip_des, float(data.qvel[qvel_addr["left_hip"]])
            )
            l_knee_out, _ = actuators["left_knee"].compute_actual_torque(
                l_knee_des, float(data.qvel[qvel_addr["left_knee"]])
            )
            r_hip_out, _ = actuators["right_hip"].compute_actual_torque(
                r_hip_des, float(data.qvel[qvel_addr["right_hip"]])
            )
            r_knee_out, _ = actuators["right_knee"].compute_actual_torque(
                r_knee_des, float(data.qvel[qvel_addr["right_knee"]])
            )

            # Apply control
            data.ctrl[0] = l_hip_out
            data.ctrl[1] = l_knee_out
            data.ctrl[2] = r_hip_out
            data.ctrl[3] = r_knee_out

            # Step simulation
            mujoco.mj_step(model, data)
            micro_steps += 1

            # Energy cost (residual only)
            total_energy += abs(left_residual * data.qvel[qvel_addr["left_hip"]]) * dt
            total_energy += abs(right_residual * data.qvel[qvel_addr["right_hip"]]) * dt

            # Check failure
            failure_type = classify_failure(
                model,
                data,
                base_params,
                0.0,  # start_x
                t,
            )

            if failure_type != "success":
                failed = True
                break

        final_distance = float(data.qpos[0])
        distances.append(final_distance)
        failures.append(int(failed))
        energy_costs.append(total_energy)

        if verbose:
            status = "FAIL" if failed else "OK"
            print(f"  Episode {ep}: {final_distance:.3f}m [{status}] ({failure_type})")

    mean_distance = float(np.mean(distances))
    failure_rate = float(np.mean(failures))
    mean_energy = float(np.mean(energy_costs))

    return {
        "mean_distance": mean_distance,
        "std_distance": float(np.std(distances)),
        "failure_rate": failure_rate,
        "mean_energy": mean_energy,
        "distances": distances,
    }


def objective_function(params_8d: np.ndarray) -> float:
    """CMA-ES objective: minimize negative distance + penalties.

    Returns:
        Negative score (CMA-ES minimizes)
    """
    result = evaluate_phase_gated(params_8d, episodes=5, verbose=False)

    mean_distance = result["mean_distance"]
    failure_rate = result["failure_rate"]
    mean_energy = result["mean_energy"]

    # Penalties
    failure_penalty = 100.0 * failure_rate
    energy_penalty = 0.1 * mean_energy
    l1_penalty = 0.05 * np.sum(np.abs(params_8d))

    score = mean_distance - failure_penalty - energy_penalty - l1_penalty

    return -score  # Negative for minimization


def main():
    print("=" * 80)
    print("Phase-Gated Residual CMA-ES Search")
    print("=" * 80)
    print("Goal: Surpass constant baseline (4.973m)")
    print("Search space: 8D phase-gated hip residuals [-0.5, +0.5] N·m")
    print()

    # Try cma package
    try:
        import cma
    except ImportError:
        print("ERROR: cma package not found. Installing...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "cma"])
        import cma

    # Initial guess: start from constant best [0.5, 1.0]
    # But clip to bounds [-0.5, +0.5]
    initial_guess = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    sigma = 0.2  # Initial search step size

    print("Initial guess:", initial_guess)
    print("Initial sigma:", sigma)
    print()

    # CMA-ES options
    opts = {
        "bounds": [[-0.5] * 8, [0.5] * 8],
        "popsize": 12,
        "maxiter": 30,  # Reduced for faster iteration
        "verb_disp": 1,
        "verb_log": 0,
    }

    es = cma.CMAEvolutionStrategy(initial_guess, sigma, opts)

    best_score = float("inf")
    best_params = None
    iteration = 0

    print("Starting CMA-ES optimization...")
    print()

    while not es.stop():
        solutions = es.ask()
        scores = [objective_function(x) for x in solutions]
        es.tell(solutions, scores)

        current_best_idx = int(np.argmin(scores))
        if scores[current_best_idx] < best_score:
            best_score = scores[current_best_idx]
            best_params = solutions[current_best_idx]

            # Evaluate with more episodes
            result = evaluate_phase_gated(best_params, episodes=10, verbose=False)

            print(f"Iter {iteration}: New best score={-best_score:.3f}")
            print(
                f"  Distance: {result['mean_distance']:.3f} ± {result['std_distance']:.3f}m"
            )
            print(f"  Failure rate: {result['failure_rate']*100:.0f}%")
            print(f"  Params: {best_params}")
            print()

        iteration += 1

    # Final evaluation with more episodes
    print("=" * 80)
    print("Final Evaluation")
    print("=" * 80)

    final_result = evaluate_phase_gated(best_params, episodes=20, verbose=True)

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(
        f"Best distance: {final_result['mean_distance']:.3f} ± {final_result['std_distance']:.3f}m"
    )
    print(f"Failure rate: {final_result['failure_rate']*100:.0f}%")
    print(f"Energy cost: {final_result['mean_energy']:.3f} J")
    print()
    print("Best 8D parameters:")
    phase_params = PhaseGatedParams.from_array(best_params)
    print(
        f"  Left:  early={phase_params.left_stance_early:.3f}, late={phase_params.left_stance_late:.3f}, "
        f"thrust={phase_params.left_swing_thrust:.3f}, retract={phase_params.left_swing_retract:.3f}"
    )
    print(
        f"  Right: early={phase_params.right_stance_early:.3f}, late={phase_params.right_stance_late:.3f}, "
        f"thrust={phase_params.right_swing_thrust:.3f}, retract={phase_params.right_swing_retract:.3f}"
    )
    print()
    print("Comparison:")
    print("  Constant best:    4.973m")
    print("  100k RL:          4.779m")
    print(f"  Phase-gated 8D:   {final_result['mean_distance']:.3f}m")
    print()

    improvement_vs_constant = final_result["mean_distance"] - 4.973
    improvement_vs_rl = final_result["mean_distance"] - 4.779

    if final_result["mean_distance"] > 4.973:
        print("[SUCCESS] Phase-gated residual surpassed constant baseline!")
        print(
            f"  Improvement: +{improvement_vs_constant:.3f}m ({improvement_vs_constant/4.973*100:.1f}%)"
        )
    elif final_result["mean_distance"] > 4.779:
        print("[PARTIAL] Better than RL, but not yet surpassing constant.")
        print(f"  vs RL: +{improvement_vs_rl:.3f}m")
        print(f"  vs constant: {improvement_vs_constant:.3f}m")
    else:
        print("[FAILURE] Phase-gated did not improve over RL.")
        print("  Constant (4.973m) remains the best option.")

    # Save results
    report = {
        "best_params": best_params.tolist(),
        "best_distance": final_result["mean_distance"],
        "std_distance": final_result["std_distance"],
        "failure_rate": final_result["failure_rate"],
        "energy_cost": final_result["mean_energy"],
        "phase_params": {
            "left_stance_early": phase_params.left_stance_early,
            "left_stance_late": phase_params.left_stance_late,
            "left_swing_thrust": phase_params.left_swing_thrust,
            "left_swing_retract": phase_params.left_swing_retract,
            "right_stance_early": phase_params.right_stance_early,
            "right_stance_late": phase_params.right_stance_late,
            "right_swing_thrust": phase_params.right_swing_thrust,
            "right_swing_retract": phase_params.right_swing_retract,
        },
        "comparison": {
            "constant_best": 4.973,
            "rl_100k": 4.779,
            "phase_gated_8d": final_result["mean_distance"],
            "improvement_vs_constant": improvement_vs_constant,
            "improvement_vs_rl": improvement_vs_rl,
        },
        "cma_es_config": {
            "initial_guess": initial_guess.tolist(),
            "sigma": sigma,
            "iterations": iteration,
            "popsize": opts["popsize"],
        },
    }

    report_path = (
        HW1_ROOT / "logs" / "residual_rl_v2" / "phase_gated_search_result.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[OK] Report saved to {report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

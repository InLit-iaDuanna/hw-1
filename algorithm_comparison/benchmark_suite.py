"""
Unified Benchmark Suite for Algorithm Comparison
Compares V10 PD, V13.7 FSM, RL (PPO), RL (SAC), Trajectory Optimization, and Virtual Constraints
"""

import numpy as np
import mujoco
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import csv
from scipy import stats

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from stable_baselines3 import PPO, SAC

    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    print("Warning: stable_baselines3 not available, RL algorithms will be skipped")


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run"""

    algorithm: str
    scenario: str
    trial: int
    seed: int
    forward_distance: float
    num_steps: int
    cost_of_transport: float
    stability_metric: float
    robustness_score: float
    success: bool
    termination_reason: str
    execution_time: float


class V10PDController:
    """V10 PD Controller"""

    def __init__(self):
        self.kp = np.array([200.0, 200.0, 150.0, 150.0])
        self.kd = np.array([20.0, 20.0, 15.0, 15.0])
        self.target_angles = np.array([0.3, -0.6, 0.3, -0.6])  # hip, knee for both legs

    def get_action(self, qpos, qvel, phase):
        """Get control action based on current state"""
        joint_pos = qpos[7:11]
        joint_vel = qvel[6:10]

        # Simple phase-based target switching
        if phase < 0.5:
            targets = self.target_angles
        else:
            targets = self.target_angles[[2, 3, 0, 1]]  # Swap legs

        error = targets - joint_pos
        torque = self.kp * error - self.kd * joint_vel
        return np.clip(torque, -100, 100)


class V13FSMController:
    """V13.7 FSM Controller with Compass Gait Logic"""

    def __init__(self):
        self.kp = np.array([180.0, 180.0, 140.0, 140.0])
        self.kd = np.array([18.0, 18.0, 14.0, 14.0])
        self.state = "stance_L"
        self.phase = 0.0

        # Gait parameters
        self.hip_swing_amplitude = 0.4
        self.knee_swing_amplitude = 0.7
        self.stance_knee_target = -0.1

    def detect_phase(self, qpos, qvel, contact_force):
        """Detect gait phase from contact and kinematics"""
        left_contact = contact_force[0] > 10.0
        right_contact = contact_force[1] > 10.0

        # State machine transitions
        if self.state == "stance_L":
            if not left_contact and right_contact:
                self.state = "stance_R"
                self.phase = 0.0
        elif self.state == "stance_R":
            if left_contact and not right_contact:
                self.state = "stance_L"
                self.phase = 0.0

        self.phase = min(self.phase + 0.02, 1.0)
        return self.phase

    def get_action(self, qpos, qvel, contact_force):
        """Get control action based on FSM state"""
        phase = self.detect_phase(qpos, qvel, contact_force)
        joint_pos = qpos[7:11]
        joint_vel = qvel[6:10]

        # Generate targets based on state
        if self.state == "stance_L":
            # Left leg stance, right leg swing
            targets = np.array(
                [
                    -0.1,  # Left hip (slight backward)
                    self.stance_knee_target,  # Left knee
                    self.hip_swing_amplitude * np.sin(np.pi * phase),  # Right hip swing
                    -self.knee_swing_amplitude
                    * np.sin(np.pi * phase),  # Right knee swing
                ]
            )
        else:
            # Right leg stance, left leg swing
            targets = np.array(
                [
                    self.hip_swing_amplitude * np.sin(np.pi * phase),  # Left hip swing
                    -self.knee_swing_amplitude
                    * np.sin(np.pi * phase),  # Left knee swing
                    -0.1,  # Right hip
                    self.stance_knee_target,  # Right knee
                ]
            )

        error = targets - joint_pos
        torque = self.kp * error - self.kd * joint_vel
        return np.clip(torque, -100, 100)


class VirtualConstraintsController:
    """Virtual Constraints based on HZD principles"""

    def __init__(self):
        self.kp = 250.0
        self.kd = 25.0
        # Bezier polynomial coefficients for virtual constraints
        self.hip_coeffs = np.array([0.1, 0.4, 0.2, -0.1, -0.2])
        self.knee_coeffs = np.array([-0.1, -0.6, -0.8, -0.5, -0.2])

    def phase_variable(self, qpos):
        """Compute phase variable from configuration"""
        # Use stance leg angle as phase variable
        stance_hip = qpos[7]
        return np.clip((stance_hip + 0.3) / 0.6, 0, 1)

    def virtual_constraint(self, s, coeffs):
        """Evaluate Bezier polynomial"""
        n = len(coeffs) - 1
        result = 0
        for i, c in enumerate(coeffs):
            result += c * (np.math.comb(n, i) * (s**i) * ((1 - s) ** (n - i)))
        return result

    def get_action(self, qpos, qvel, contact_force):
        """Get control action based on virtual constraints"""
        s = self.phase_variable(qpos)
        joint_pos = qpos[7:11]
        joint_vel = qvel[6:10]

        # Desired trajectories from virtual constraints
        left_contact = contact_force[0] > 10.0

        if left_contact:
            targets = np.array(
                [
                    self.virtual_constraint(s, self.hip_coeffs),
                    self.virtual_constraint(s, self.knee_coeffs),
                    self.virtual_constraint(1 - s, self.hip_coeffs),
                    self.virtual_constraint(1 - s, self.knee_coeffs),
                ]
            )
        else:
            targets = np.array(
                [
                    self.virtual_constraint(1 - s, self.hip_coeffs),
                    self.virtual_constraint(1 - s, self.knee_coeffs),
                    self.virtual_constraint(s, self.hip_coeffs),
                    self.virtual_constraint(s, self.knee_coeffs),
                ]
            )

        error = targets - joint_pos
        torque = self.kp * error - self.kd * joint_vel
        return np.clip(torque, -100, 100)


class BenchmarkSuite:
    """Main benchmark suite for algorithm comparison"""

    def __init__(self, model_path: str):
        """Initialize benchmark suite with model path"""
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        # Benchmark parameters
        self.max_steps = 2000
        self.dt = self.model.opt.timestep
        self.num_trials = 10

        # Initialize controllers
        self.controllers = {
            "V10_PD": V10PDController(),
            "V13_FSM": V13FSMController(),
            "Virtual_Constraints": VirtualConstraintsController(),
        }

        # Try to load RL models if available
        if RL_AVAILABLE:
            self._load_rl_models()

    def _load_rl_models(self):
        """Load trained RL models if available"""
        base_dir = Path(self.model_path).parent / "algorithm_comparison"

        ppo_path = base_dir / "trained_models" / "ppo_biped_final.zip"
        sac_path = base_dir / "trained_models" / "sac_biped_final.zip"

        if ppo_path.exists():
            try:
                self.controllers["RL_PPO"] = PPO.load(str(ppo_path))
            except Exception as e:
                print(f"Warning: Could not load PPO model: {e}")

        if sac_path.exists():
            try:
                self.controllers["RL_SAC"] = SAC.load(str(sac_path))
            except Exception as e:
                print(f"Warning: Could not load SAC model: {e}")

    def reset_simulation(self, scenario: str, seed: int):
        """Reset simulation with scenario-specific initial conditions"""
        np.random.seed(seed)
        mujoco.mj_resetData(self.model, self.data)

        # Set initial position
        self.data.qpos[2] = 0.9  # Height
        self.data.qpos[7] = 0.1  # Left hip
        self.data.qpos[8] = -0.2  # Left knee
        self.data.qpos[9] = -0.1  # Right hip
        self.data.qpos[10] = -0.2  # Right knee

        # Add small random perturbations
        self.data.qpos[3:7] += np.random.randn(4) * 0.01  # Quaternion perturbation
        self.data.qvel[:] += np.random.randn(self.model.nv) * 0.05

        # Scenario-specific modifications
        if scenario == "small_slope":
            # Tilt the ground (if model supports it)
            pass
        elif scenario == "perturbations":
            # Will apply perturbations during simulation
            pass

    def apply_scenario_effects(self, scenario: str, step: int):
        """Apply scenario-specific effects during simulation"""
        if scenario == "perturbations":
            # Apply random push every 200 steps
            if step % 200 == 100:
                push_force = np.random.randn(3) * 50
                self.data.qvel[0:3] += push_force * self.dt

    def get_contact_forces(self) -> np.ndarray:
        """Extract contact forces for both feet"""
        left_contact = 0.0
        right_contact = 0.0

        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            # Identify which foot is in contact (simplified)
            if i < self.data.ncon // 2:
                left_contact += np.linalg.norm(self.data.contact[i].dist)
            else:
                right_contact += np.linalg.norm(self.data.contact[i].dist)

        return np.array([left_contact, right_contact])

    def compute_cost_of_transport(
        self, distance: float, energy: float, mass: float
    ) -> float:
        """Compute mechanical cost of transport"""
        if distance < 0.01:
            return float("inf")
        # CoT = Energy / (mass * gravity * distance)
        gravity = 9.81
        return energy / (mass * gravity * distance)

    def compute_stability_metric(self, trajectory: List[np.ndarray]) -> float:
        """Compute stability metric from trajectory"""
        if len(trajectory) < 10:
            return 0.0

        # Use variance of torso orientation as stability measure
        orientations = np.array([state[:4] for state in trajectory])  # Quaternions
        stability = 1.0 / (1.0 + np.var(orientations))
        return stability

    def compute_robustness_score(
        self, scenario: str, success: bool, distance: float
    ) -> float:
        """Compute robustness score based on scenario difficulty"""
        base_score = 1.0 if success else 0.0

        # Weight by scenario difficulty
        scenario_weights = {
            "flat_ground": 1.0,
            "small_slope": 1.5,
            "perturbations": 2.0,
        }

        weight = scenario_weights.get(scenario, 1.0)
        # Also consider distance traveled
        distance_bonus = min(distance / 5.0, 1.0)

        return base_score * weight * (0.5 + 0.5 * distance_bonus)

    def check_termination(self) -> Tuple[bool, str]:
        """Check if simulation should terminate"""
        # Fall detection
        torso_height = self.data.qpos[2]
        if torso_height < 0.3:
            return True, "fall"

        # Extreme tilt detection
        quat = self.data.qpos[3:7]
        # Convert to Euler angles (simplified check)
        if abs(quat[0]) < 0.5:  # Severe rotation
            return True, "excessive_tilt"

        # Check if moving backward
        if self.data.qpos[0] < -0.5:
            return True, "backward_motion"

        return False, "running"

    def run_trial(
        self, algorithm: str, scenario: str, trial: int, seed: int
    ) -> BenchmarkResult:
        """Run a single benchmark trial"""
        print(f"Running {algorithm} on {scenario}, trial {trial+1}/10, seed {seed}")

        start_time = time.time()
        self.reset_simulation(scenario, seed)

        controller = self.controllers.get(algorithm)
        if controller is None:
            print(f"Warning: Controller {algorithm} not available")
            return BenchmarkResult(
                algorithm=algorithm,
                scenario=scenario,
                trial=trial,
                seed=seed,
                forward_distance=0.0,
                num_steps=0,
                cost_of_transport=float("inf"),
                stability_metric=0.0,
                robustness_score=0.0,
                success=False,
                termination_reason="controller_not_available",
                execution_time=0.0,
            )

        # Track metrics
        initial_x = self.data.qpos[0]
        energy_consumed = 0.0
        trajectory = []
        success = True
        termination_reason = "completed"

        for step in range(self.max_steps):
            # Get contact forces
            contact_forces = self.get_contact_forces()

            # Get action from controller
            if algorithm in ["RL_PPO", "RL_SAC"]:
                # RL models expect observation vector
                obs = np.concatenate(
                    [self.data.qpos[:11], self.data.qvel[:10], contact_forces]
                )
                action, _ = controller.predict(obs, deterministic=True)
            elif algorithm == "Virtual_Constraints":
                action = controller.get_action(
                    self.data.qpos, self.data.qvel, contact_forces
                )
            elif algorithm == "V13_FSM":
                action = controller.get_action(
                    self.data.qpos, self.data.qvel, contact_forces
                )
            else:  # V10_PD
                phase = step / self.max_steps  # Simple phase estimate
                action = controller.get_action(self.data.qpos, self.data.qvel, phase)

            # Apply action
            self.data.ctrl[:] = action

            # Apply scenario effects
            self.apply_scenario_effects(scenario, step)

            # Step simulation
            mujoco.mj_step(self.model, self.data)

            # Track energy
            energy_consumed += np.sum(np.abs(action * self.data.qvel[6:10])) * self.dt

            # Store trajectory
            trajectory.append(self.data.qpos.copy())

            # Check termination
            terminated, reason = self.check_termination()
            if terminated:
                success = False
                termination_reason = reason
                break

        # Compute final metrics
        final_x = self.data.qpos[0]
        forward_distance = final_x - initial_x
        num_steps = step + 1

        mass = np.sum(self.model.body_mass)
        cot = self.compute_cost_of_transport(forward_distance, energy_consumed, mass)
        stability = self.compute_stability_metric(trajectory)
        robustness = self.compute_robustness_score(scenario, success, forward_distance)

        execution_time = time.time() - start_time

        return BenchmarkResult(
            algorithm=algorithm,
            scenario=scenario,
            trial=trial,
            seed=seed,
            forward_distance=forward_distance,
            num_steps=num_steps,
            cost_of_transport=cot,
            stability_metric=stability,
            robustness_score=robustness,
            success=success,
            termination_reason=termination_reason,
            execution_time=execution_time,
        )

    def run_benchmark(self, output_file: str = "benchmark_results.csv"):
        """Run full benchmark suite"""
        scenarios = ["flat_ground", "small_slope", "perturbations"]
        results = []

        print("=" * 80)
        print("Starting Benchmark Suite")
        print("=" * 80)
        print(f"Algorithms: {list(self.controllers.keys())}")
        print(f"Scenarios: {scenarios}")
        print(f"Trials per combination: {self.num_trials}")
        print("=" * 80)

        for algorithm in self.controllers.keys():
            for scenario in scenarios:
                for trial in range(self.num_trials):
                    seed = 1000 + trial
                    result = self.run_trial(algorithm, scenario, trial, seed)
                    results.append(result)

        # Save results to CSV
        self.save_results(results, output_file)

        # Print summary statistics
        self.print_summary(results)

        return results

    def save_results(self, results: List[BenchmarkResult], output_file: str):
        """Save results to CSV file"""
        output_path = (
            Path(self.model_path).parent / "algorithm_comparison" / output_file
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(
                [
                    "algorithm",
                    "scenario",
                    "trial",
                    "seed",
                    "forward_distance",
                    "num_steps",
                    "cost_of_transport",
                    "stability_metric",
                    "robustness_score",
                    "success",
                    "termination_reason",
                    "execution_time",
                ]
            )

            # Data
            for r in results:
                writer.writerow(
                    [
                        r.algorithm,
                        r.scenario,
                        r.trial,
                        r.seed,
                        f"{r.forward_distance:.4f}",
                        r.num_steps,
                        f"{r.cost_of_transport:.4f}",
                        f"{r.stability_metric:.4f}",
                        f"{r.robustness_score:.4f}",
                        r.success,
                        r.termination_reason,
                        f"{r.execution_time:.2f}",
                    ]
                )

        print(f"\nResults saved to: {output_path}")

    def print_summary(self, results: List[BenchmarkResult]):
        """Print summary statistics with significance tests"""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        algorithms = sorted(set(r.algorithm for r in results))
        scenarios = sorted(set(r.scenario for r in results))

        for scenario in scenarios:
            print(f"\n{scenario.upper().replace('_', ' ')}")
            print("-" * 80)
            print(
                f"{'Algorithm':<20} {'Distance':<15} {'CoT':<15} {'Stability':<15} {'Success Rate'}"
            )
            print("-" * 80)

            scenario_data = {}
            for algo in algorithms:
                algo_results = [
                    r for r in results if r.algorithm == algo and r.scenario == scenario
                ]

                if not algo_results:
                    continue

                distances = [r.forward_distance for r in algo_results]
                cots = [
                    r.cost_of_transport
                    for r in algo_results
                    if r.cost_of_transport != float("inf")
                ]
                stabilities = [r.stability_metric for r in algo_results]
                success_rate = sum(r.success for r in algo_results) / len(algo_results)

                scenario_data[algo] = {
                    "distances": distances,
                    "cots": cots,
                    "stabilities": stabilities,
                }

                dist_mean = np.mean(distances)
                dist_std = np.std(distances)
                cot_mean = np.mean(cots) if cots else float("inf")
                cot_std = np.std(cots) if cots else 0.0
                stab_mean = np.mean(stabilities)
                stab_std = np.std(stabilities)

                print(
                    f"{algo:<20} {dist_mean:>6.2f}±{dist_std:<5.2f} "
                    f"{cot_mean:>6.3f}±{cot_std:<5.3f} "
                    f"{stab_mean:>6.3f}±{stab_std:<5.3f} "
                    f"{success_rate:>6.1%}"
                )

            # Statistical significance tests (t-tests between pairs)
            if len(algorithms) >= 2:
                print("\nPairwise t-tests (forward distance):")
                for i, algo1 in enumerate(algorithms[:-1]):
                    for algo2 in algorithms[i + 1 :]:
                        if algo1 in scenario_data and algo2 in scenario_data:
                            data1 = scenario_data[algo1]["distances"]
                            data2 = scenario_data[algo2]["distances"]
                            t_stat, p_value = stats.ttest_ind(data1, data2)
                            sig = (
                                "***"
                                if p_value < 0.001
                                else (
                                    "**"
                                    if p_value < 0.01
                                    else "*" if p_value < 0.05 else "ns"
                                )
                            )
                            print(f"  {algo1} vs {algo2}: p={p_value:.4f} {sig}")

        print("\n" + "=" * 80)


def main():
    """Main entry point"""
    # Find model file
    base_dir = Path(__file__).parent.parent
    model_path = base_dir / "biped_model_V13.xml"

    if not model_path.exists():
        print(f"Error: Model file not found at {model_path}")
        print("Looking for alternative models...")
        alternatives = list(base_dir.glob("biped_model_V*.xml"))
        if alternatives:
            model_path = alternatives[-1]
            print(f"Using: {model_path}")
        else:
            print("No model files found!")
            return

    # Create and run benchmark
    benchmark = BenchmarkSuite(str(model_path))
    results = benchmark.run_benchmark("benchmark_results.csv")

    print("\nBenchmark completed successfully!")


if __name__ == "__main__":
    main()

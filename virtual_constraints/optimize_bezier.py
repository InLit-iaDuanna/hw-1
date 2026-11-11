"""
Bezier Curve Parameter Optimization for Virtual Constraints
Optimizes Bezier polynomial coefficients for hip trajectory control
Compares performance against V13.7 FSM baseline
"""

import numpy as np
import mujoco
import os
from pathlib import Path

try:
    import cma

    CMA_AVAILABLE = True
except ImportError:
    CMA_AVAILABLE = False
    print("Warning: CMA-ES not available. Install with: pip install cma")

# Configuration
XML_PATH = Path(__file__).parent.parent / "hw_scene.xml"
SIMULATION_TIME = 10.0  # seconds
DT = 0.002


class BezierVirtualConstraint:
    """Virtual constraint using cubic Bezier curve"""

    def __init__(self, a0, a1, a2, a3):
        """
        Cubic Bezier: q(s) = a0 + a1*s + a2*s^2 + a3*s^3
        where s ∈ [0, 1] is the phase variable (gait cycle progress)
        """
        self.a0 = a0
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3

    def compute_angle(self, phase):
        """Compute desired hip angle at given phase"""
        s = np.clip(phase, 0.0, 1.0)
        return self.a0 + self.a1 * s + self.a2 * s**2 + self.a3 * s**3

    def compute_velocity(self, phase, phase_dot):
        """Compute desired hip velocity"""
        s = np.clip(phase, 0.0, 1.0)
        dq_ds = self.a1 + 2 * self.a2 * s + 3 * self.a3 * s**2
        return dq_ds * phase_dot


class GaitSimulator:
    """Simulate biped gait with virtual constraints"""

    def __init__(self, xml_path):
        self.model = mujoco.MjModel.from_xml_path(str(xml_path))
        self.data = mujoco.MjData(self.model)

        # Find actuator indices
        self.hip_actuator_ids = []
        for i in range(self.model.nu):
            name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            if name and "hip" in name.lower():
                self.hip_actuator_ids.append(i)

        if not self.hip_actuator_ids:
            print("Warning: No hip actuators found. Using first 2 actuators.")
            self.hip_actuator_ids = [0, 1]

    def reset(self):
        """Reset simulation to initial state"""
        mujoco.mj_resetData(self.model, self.data)
        # Set initial standing pose
        if self.data.qpos.shape[0] > 2:
            self.data.qpos[2] = 0.9  # Torso height

    def step(self, ctrl):
        """Step simulation forward"""
        self.data.ctrl[:] = 0
        for i, act_id in enumerate(self.hip_actuator_ids[: len(ctrl)]):
            self.data.ctrl[act_id] = ctrl[i]
        mujoco.mj_step(self.model, self.data)

    def get_position(self):
        """Get forward position (x-coordinate of root)"""
        if self.data.qpos.shape[0] > 0:
            return self.data.qpos[0]
        return 0.0

    def get_energy(self):
        """Compute energy consumption (sum of actuator forces * velocities)"""
        energy = 0.0
        for act_id in self.hip_actuator_ids:
            force = self.data.actuator_force[act_id]
            vel = self.data.actuator_velocity[act_id]
            energy += abs(force * vel) * self.model.opt.timestep
        return energy


def simple_phase_estimator(t, stride_period=1.0):
    """Simple time-based phase estimator"""
    return (t % stride_period) / stride_period


def evaluate_bezier_params(params, xml_path, duration=SIMULATION_TIME, verbose=False):
    """
    Evaluate Bezier parameters performance

    Args:
        params: [a0, a1, a2, a3] - Bezier coefficients
        xml_path: Path to MuJoCo XML model
        duration: Simulation duration in seconds
        verbose: Print debug info

    Returns:
        cost: Lower is better (negative distance + energy penalty)
    """
    a0, a1, a2, a3 = params

    # Create virtual constraint
    vc = BezierVirtualConstraint(a0, a1, a2, a3)

    # Create simulator
    try:
        sim = GaitSimulator(xml_path)
    except Exception as e:
        if verbose:
            print(f"Simulation init failed: {e}")
        return 1e6  # High cost for invalid params

    sim.reset()

    # PD gains for tracking virtual constraint
    kp = 100.0
    kd = 10.0

    total_energy = 0.0
    stride_period = 1.0  # 1 second per stride

    steps = int(duration / sim.model.opt.timestep)

    for step in range(steps):
        t = step * sim.model.opt.timestep

        # Compute phase
        phase = simple_phase_estimator(t, stride_period)
        phase_dot = 1.0 / stride_period

        # Desired trajectory from virtual constraint
        q_des = vc.compute_angle(phase)
        qd_des = vc.compute_velocity(phase, phase_dot)

        # Simple bilateral control (both hips follow same trajectory with phase offset)
        ctrl = []
        for i, act_id in enumerate(sim.hip_actuator_ids):
            # Phase offset for left/right alternation
            phase_offset = 0.5 * i
            phase_shifted = (phase + phase_offset) % 1.0

            q_des_shifted = vc.compute_angle(phase_shifted)
            qd_des_shifted = vc.compute_velocity(phase_shifted, phase_dot)

            # Get current joint state (simplified - assumes actuator controls joint directly)
            q_actual = sim.data.qpos[min(i + 3, sim.data.qpos.shape[0] - 1)]
            qd_actual = sim.data.qvel[min(i + 3, sim.data.qvel.shape[0] - 1)]

            # PD control
            torque = kp * (q_des_shifted - q_actual) + kd * (qd_des_shifted - qd_actual)
            ctrl.append(np.clip(torque, -50, 50))

        sim.step(ctrl)
        total_energy += sim.get_energy()

        # Early termination if robot falls
        if sim.data.qpos.shape[0] > 2 and sim.data.qpos[2] < 0.3:
            if verbose:
                print(f"Robot fell at t={t:.2f}s")
            return 1e6

    # Compute metrics
    forward_distance = sim.get_position()
    avg_energy = total_energy / duration

    # Cost function: maximize distance, minimize energy
    # Negative distance (we want to maximize), plus energy penalty
    cost = -forward_distance + 0.1 * avg_energy

    if verbose:
        print(
            f"Distance: {forward_distance:.3f}m, Energy: {avg_energy:.3f}, Cost: {cost:.3f}"
        )

    return cost


def parameter_explorer(xml_path, n_samples=50, duration=5.0):
    """
    Simple grid search / random exploration

    Args:
        xml_path: Path to MuJoCo XML
        n_samples: Number of random samples to try
        duration: Simulation duration per sample

    Returns:
        best_params, best_cost, results
    """
    print("=== Parameter Explorer ===")
    print(f"Testing {n_samples} random parameter sets...")

    # Reasonable bounds for hip angle trajectory (radians)
    # a0: initial angle, a1: linear term, a2/a3: curvature
    bounds = [
        (-0.2, 0.2),  # a0: roughly straight
        (-1.0, 1.0),  # a1: swing amplitude
        (-0.5, 0.5),  # a2: curvature
        (-0.5, 0.5),  # a3: curvature
    ]

    best_params = None
    best_cost = float("inf")
    results = []

    for i in range(n_samples):
        # Random sample
        params = [np.random.uniform(low, high) for low, high in bounds]

        cost = evaluate_bezier_params(params, xml_path, duration, verbose=False)
        results.append((params, cost))

        if cost < best_cost:
            best_cost = cost
            best_params = params
            print(
                f"[{i+1}/{n_samples}] New best! Cost={cost:.3f}, params={[f'{p:.3f}' for p in params]}"
            )

        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{n_samples}] Progress... Current best cost: {best_cost:.3f}")

    return best_params, best_cost, results


def cma_es_optimize(xml_path, duration=5.0, max_evals=100):
    """
    CMA-ES optimization

    Args:
        xml_path: Path to MuJoCo XML
        duration: Simulation duration per evaluation
        max_evals: Maximum function evaluations

    Returns:
        best_params, best_cost
    """
    if not CMA_AVAILABLE:
        print("CMA-ES not available. Use parameter_explorer instead.")
        return None, None

    print("=== CMA-ES Optimization ===")

    # Initial guess (roughly neutral gait)
    x0 = [0.0, 0.5, 0.0, 0.0]

    # Initial standard deviation
    sigma0 = 0.3

    # Bounds
    bounds = [[-0.5, -2.0, -1.0, -1.0], [0.5, 2.0, 1.0, 1.0]]

    opts = {
        "bounds": bounds,
        "maxfevals": max_evals,
        "verb_disp": 1,
        "verb_log": 0,
        "tolfun": 1e-3,
    }

    es = cma.CMAEvolutionStrategy(x0, sigma0, opts)

    eval_count = 0

    while not es.stop():
        solutions = es.ask()
        fitness = []

        for params in solutions:
            cost = evaluate_bezier_params(params, xml_path, duration, verbose=False)
            fitness.append(cost)
            eval_count += 1

            if eval_count % 10 == 0:
                print(
                    f"Evaluations: {eval_count}/{max_evals}, Best so far: {es.result.fbest:.3f}"
                )

        es.tell(solutions, fitness)

    best_params = es.result.xbest
    best_cost = es.result.fbest

    print(f"\nOptimization complete!")
    print(f"Best cost: {best_cost:.3f}")
    print(f"Best params: {[f'{p:.3f}' for p in best_params]}")

    return best_params, best_cost


def compare_with_v13_fsm(xml_path, bezier_params, duration=10.0):
    """
    Compare optimized Bezier controller with V13.7 FSM baseline

    Args:
        xml_path: Path to MuJoCo XML
        bezier_params: Optimized [a0, a1, a2, a3]
        duration: Comparison duration
    """
    print("\n=== Comparison with V13.7 FSM Baseline ===")

    # Run Bezier controller
    print("\n[Bezier Controller]")
    bezier_cost = evaluate_bezier_params(
        bezier_params, xml_path, duration, verbose=True
    )

    print("\n[V13.7 FSM Baseline]")
    print("Note: FSM comparison requires V13.7 implementation.")
    print("If V13.7 code is available, integrate here for direct comparison.")
    print("Expected FSM metrics from previous runs should be documented.")

    # Placeholder for FSM comparison
    # TODO: Load and run V13.7 FSM controller if available
    fsm_cost_estimate = 0.5  # Placeholder - replace with actual run

    print(f"\nComparison:")
    print(f"  Bezier Cost: {bezier_cost:.3f}")
    print(f"  FSM Cost (est): {fsm_cost_estimate:.3f}")
    print(
        f"  Improvement: {((fsm_cost_estimate - bezier_cost) / abs(fsm_cost_estimate) * 100):.1f}%"
    )


def save_results(params, cost, output_path="best_bezier_params.txt"):
    """Save optimized parameters to file"""
    output_file = Path(__file__).parent / output_path

    with open(output_file, "w") as f:
        f.write("# Optimized Bezier Virtual Constraint Parameters\n")
        f.write("# Cubic Bezier: q(s) = a0 + a1*s + a2*s^2 + a3*s^3\n")
        f.write(f"# Cost: {cost:.6f}\n\n")
        f.write(f"a0 = {params[0]:.6f}\n")
        f.write(f"a1 = {params[1]:.6f}\n")
        f.write(f"a2 = {params[2]:.6f}\n")
        f.write(f"a3 = {params[3]:.6f}\n")

    print(f"\nParameters saved to: {output_file}")


def main():
    """Main optimization pipeline"""

    # Check if XML exists
    if not XML_PATH.exists():
        print(f"Error: MuJoCo XML not found at {XML_PATH}")
        print("Please ensure hw_scene.xml exists in parent directory")
        return

    print(f"Using model: {XML_PATH}\n")

    # Choose optimization method
    use_cma = CMA_AVAILABLE and True  # Set to False to force parameter explorer

    if use_cma:
        # CMA-ES optimization
        best_params, best_cost = cma_es_optimize(
            XML_PATH, duration=5.0, max_evals=100  # Shorter for faster optimization
        )
    else:
        # Parameter explorer (grid/random search)
        best_params, best_cost, _ = parameter_explorer(
            XML_PATH, n_samples=50, duration=5.0
        )

    if best_params is None:
        print("Optimization failed.")
        return

    # Validate with longer simulation
    print("\n=== Final Validation (10s simulation) ===")
    final_cost = evaluate_bezier_params(
        best_params, XML_PATH, duration=10.0, verbose=True
    )

    # Save results
    save_results(best_params, final_cost)

    # Compare with FSM
    compare_with_v13_fsm(XML_PATH, best_params, duration=10.0)

    print("\n=== Optimization Complete ===")
    print(
        f"Final parameters: a0={best_params[0]:.3f}, a1={best_params[1]:.3f}, "
        f"a2={best_params[2]:.3f}, a3={best_params[3]:.3f}"
    )


if __name__ == "__main__":
    main()

"""
Virtual Constraints Simulation Script
Simulates gait phases with virtual constraints and visualizes phase variable and constraint tracking.

This script demonstrates:
- Phase variable evolution during gait cycle
- Virtual constraint tracking
- Joint angle trajectories following Bézier curves
- Constraint error dynamics
"""

import argparse
import math
from dataclasses import dataclass
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


@dataclass
class GaitPhase:
    """Gait phase configuration"""

    name: str
    duration: float  # seconds
    start_phase: float  # 0-1
    end_phase: float  # 0-1


@dataclass
class VirtualConstraint:
    """Virtual constraint definition using Bézier curves"""

    joint_name: str
    bezier_coeffs: np.ndarray  # Bézier polynomial coefficients
    stiffness: float  # PD control stiffness
    damping: float  # PD control damping


class PhaseVariable:
    """Phase variable calculator for gait cycle"""

    def __init__(self, initial_phase: float = 0.0):
        self.phase = initial_phase
        self.phase_velocity = 0.0

    def update(self, dt: float, stride_freq: float = 1.0) -> float:
        """
        Update phase variable based on stride frequency

        Args:
            dt: Time step (seconds)
            stride_freq: Stride frequency (Hz)

        Returns:
            Current phase value (0-1)
        """
        self.phase_velocity = stride_freq
        self.phase += self.phase_velocity * dt
        self.phase = self.phase % 1.0  # Wrap around [0, 1]
        return self.phase

    def reset(self, phase: float = 0.0):
        """Reset phase variable"""
        self.phase = phase
        self.phase_velocity = 0.0


class BezierCurve:
    """Bézier curve for joint trajectory generation"""

    def __init__(self, control_points: np.ndarray):
        """
        Initialize Bézier curve

        Args:
            control_points: Control points array [n_points]
        """
        self.control_points = np.array(control_points)
        self.degree = len(control_points) - 1

    def evaluate(self, tau: float) -> float:
        """
        Evaluate Bézier curve at parameter tau

        Args:
            tau: Parameter value (0-1)

        Returns:
            Curve value at tau
        """
        tau = np.clip(tau, 0.0, 1.0)
        n = self.degree
        result = 0.0

        for i, cp in enumerate(self.control_points):
            # Bernstein polynomial
            binom = math.comb(n, i)
            bernstein = binom * (tau**i) * ((1 - tau) ** (n - i))
            result += cp * bernstein

        return result

    def derivative(self, tau: float) -> float:
        """
        Evaluate derivative of Bézier curve at parameter tau

        Args:
            tau: Parameter value (0-1)

        Returns:
            Derivative value at tau
        """
        if self.degree == 0:
            return 0.0

        tau = np.clip(tau, 0.0, 1.0)
        n = self.degree
        result = 0.0

        for i in range(n):
            diff = self.control_points[i + 1] - self.control_points[i]
            binom = math.comb(n - 1, i)
            bernstein = binom * (tau**i) * ((1 - tau) ** (n - 1 - i))
            result += n * diff * bernstein

        return result


class VirtualConstraintController:
    """Virtual constraint-based controller"""

    def __init__(self, constraints: List[VirtualConstraint]):
        """
        Initialize controller with virtual constraints

        Args:
            constraints: List of virtual constraints
        """
        self.constraints = constraints
        self.bezier_curves = {}

        for vc in constraints:
            self.bezier_curves[vc.joint_name] = BezierCurve(vc.bezier_coeffs)

    def compute_desired_position(self, joint_name: str, phase: float) -> float:
        """Compute desired joint position from phase variable"""
        return self.bezier_curves[joint_name].evaluate(phase)

    def compute_desired_velocity(
        self, joint_name: str, phase: float, phase_dot: float
    ) -> float:
        """Compute desired joint velocity"""
        curve_derivative = self.bezier_curves[joint_name].derivative(phase)
        return curve_derivative * phase_dot

    def compute_control_torque(
        self,
        joint_name: str,
        phase: float,
        phase_dot: float,
        actual_pos: float,
        actual_vel: float,
    ) -> Tuple[float, float]:
        """
        Compute control torque using PD control

        Returns:
            (torque, constraint_error)
        """
        # Find constraint for this joint
        constraint = None
        for vc in self.constraints:
            if vc.joint_name == joint_name:
                constraint = vc
                break

        if constraint is None:
            return 0.0, 0.0

        # Compute desired state
        q_des = self.compute_desired_position(joint_name, phase)
        qd_des = self.compute_desired_velocity(joint_name, phase, phase_dot)

        # Compute errors
        pos_error = q_des - actual_pos
        vel_error = qd_des - actual_vel

        # PD control
        torque = constraint.stiffness * pos_error + constraint.damping * vel_error

        return torque, pos_error


class GaitSimulator:
    """Simulate gait with virtual constraints"""

    def __init__(
        self,
        controller: VirtualConstraintController,
        stride_frequency: float = 1.0,
        dt: float = 0.001,
    ):
        """
        Initialize simulator

        Args:
            controller: Virtual constraint controller
            stride_frequency: Gait stride frequency (Hz)
            dt: Simulation time step (seconds)
        """
        self.controller = controller
        self.stride_freq = stride_frequency
        self.dt = dt
        self.phase_var = PhaseVariable()

        # Joint states (position, velocity)
        self.joint_states = {}
        for vc in controller.constraints:
            self.joint_states[vc.joint_name] = {"pos": 0.0, "vel": 0.0}

    def simulate(self, duration: float) -> dict:
        """
        Run simulation for specified duration

        Args:
            duration: Simulation duration (seconds)

        Returns:
            Dictionary with simulation results
        """
        n_steps = int(duration / self.dt)

        # Storage arrays
        time = np.zeros(n_steps)
        phase = np.zeros(n_steps)

        results = {
            "time": time,
            "phase": phase,
        }

        # Initialize storage for each joint
        for joint_name in self.joint_states.keys():
            results[joint_name] = {
                "pos": np.zeros(n_steps),
                "vel": np.zeros(n_steps),
                "des_pos": np.zeros(n_steps),
                "des_vel": np.zeros(n_steps),
                "torque": np.zeros(n_steps),
                "error": np.zeros(n_steps),
            }

        # Simulation loop
        for i in range(n_steps):
            t = i * self.dt
            time[i] = t

            # Update phase variable
            current_phase = self.phase_var.update(self.dt, self.stride_freq)
            phase[i] = current_phase
            phase_dot = self.phase_var.phase_velocity

            # Update each joint
            for joint_name, state in self.joint_states.items():
                # Compute control
                torque, error = self.controller.compute_control_torque(
                    joint_name, current_phase, phase_dot, state["pos"], state["vel"]
                )

                # Simple dynamics: unit inertia
                acceleration = torque

                # Integrate (Euler method)
                state["vel"] += acceleration * self.dt
                state["pos"] += state["vel"] * self.dt

                # Store results
                results[joint_name]["pos"][i] = state["pos"]
                results[joint_name]["vel"][i] = state["vel"]
                results[joint_name]["des_pos"][i] = (
                    self.controller.compute_desired_position(joint_name, current_phase)
                )
                results[joint_name]["des_vel"][i] = (
                    self.controller.compute_desired_velocity(
                        joint_name, current_phase, phase_dot
                    )
                )
                results[joint_name]["torque"][i] = torque
                results[joint_name]["error"][i] = error

        return results


def visualize_results(results: dict, joint_names: List[str]):
    """
    Visualize simulation results

    Args:
        results: Simulation results dictionary
        joint_names: List of joint names to plot
    """
    n_joints = len(joint_names)

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(n_joints + 1, 3, figure=fig, hspace=0.3, wspace=0.3)

    time = results["time"]
    phase = results["phase"]

    # Plot phase variable
    ax_phase = fig.add_subplot(gs[0, :])
    ax_phase.plot(time, phase, "k-", linewidth=2, label="Phase Variable")
    ax_phase.set_xlabel("Time (s)", fontsize=12)
    ax_phase.set_ylabel("Phase τ", fontsize=12)
    ax_phase.set_title("Phase Variable Evolution", fontsize=14, fontweight="bold")
    ax_phase.grid(True, alpha=0.3)
    ax_phase.set_ylim([0, 1])
    ax_phase.legend(fontsize=10)

    # Plot each joint
    for idx, joint_name in enumerate(joint_names):
        joint_data = results[joint_name]
        row = idx + 1

        # Position tracking
        ax_pos = fig.add_subplot(gs[row, 0])
        ax_pos.plot(
            time, joint_data["des_pos"], "b--", linewidth=2, label="Desired", alpha=0.7
        )
        ax_pos.plot(time, joint_data["pos"], "r-", linewidth=1.5, label="Actual")
        ax_pos.set_xlabel("Time (s)", fontsize=10)
        ax_pos.set_ylabel("Position (rad)", fontsize=10)
        ax_pos.set_title(
            f"{joint_name} - Position Tracking", fontsize=11, fontweight="bold"
        )
        ax_pos.grid(True, alpha=0.3)
        ax_pos.legend(fontsize=9)

        # Tracking error
        ax_err = fig.add_subplot(gs[row, 1])
        ax_err.plot(time, joint_data["error"], "g-", linewidth=1.5)
        ax_err.axhline(y=0, color="k", linestyle="--", alpha=0.3)
        ax_err.set_xlabel("Time (s)", fontsize=10)
        ax_err.set_ylabel("Error (rad)", fontsize=10)
        ax_err.set_title(
            f"{joint_name} - Constraint Error", fontsize=11, fontweight="bold"
        )
        ax_err.grid(True, alpha=0.3)

        # Control torque
        ax_torque = fig.add_subplot(gs[row, 2])
        ax_torque.plot(time, joint_data["torque"], "m-", linewidth=1.5)
        ax_torque.axhline(y=0, color="k", linestyle="--", alpha=0.3)
        ax_torque.set_xlabel("Time (s)", fontsize=10)
        ax_torque.set_ylabel("Torque (Nm)", fontsize=10)
        ax_torque.set_title(
            f"{joint_name} - Control Torque", fontsize=11, fontweight="bold"
        )
        ax_torque.grid(True, alpha=0.3)

    plt.suptitle(
        "Virtual Constraint Simulation Results", fontsize=16, fontweight="bold", y=0.995
    )

    return fig


def create_example_constraints() -> List[VirtualConstraint]:
    """Create example virtual constraints for hip and knee"""

    # Hip joint constraint (swing phase motion)
    # Control points for hip flexion/extension during stride
    hip_control_points = np.array(
        [
            -0.1,  # Initial extension
            0.3,  # Mid-swing flexion
            0.5,  # Peak flexion
            0.2,  # Pre-contact
            -0.1,  # Back to extension
        ]
    )

    hip_constraint = VirtualConstraint(
        joint_name="hip",
        bezier_coeffs=hip_control_points,
        stiffness=100.0,
        damping=20.0,
    )

    # Knee joint constraint
    # Control points for knee flexion during stride
    knee_control_points = np.array(
        [
            0.0,  # Extended at heel strike
            0.3,  # Early swing flexion
            0.8,  # Peak swing flexion
            0.4,  # Late swing
            0.0,  # Extended for next heel strike
        ]
    )

    knee_constraint = VirtualConstraint(
        joint_name="knee",
        bezier_coeffs=knee_control_points,
        stiffness=120.0,
        damping=25.0,
    )

    # Ankle joint constraint
    ankle_control_points = np.array(
        [
            -0.1,  # Plantarflexion
            0.0,  # Neutral
            0.1,  # Dorsiflexion
            0.05,  # Slight dorsiflex
            -0.1,  # Back to plantarflex
        ]
    )

    ankle_constraint = VirtualConstraint(
        joint_name="ankle",
        bezier_coeffs=ankle_control_points,
        stiffness=80.0,
        damping=15.0,
    )

    return [hip_constraint, knee_constraint, ankle_constraint]


def main():
    """Main simulation function"""
    parser = argparse.ArgumentParser(description="Run the virtual-constraints demo.")
    parser.add_argument("--show", action="store_true", help="Display the plot window.")
    args = parser.parse_args()

    print("=" * 70)
    print("Virtual Constraints Simulation for Gait Control")
    print("=" * 70)
    print()

    # Create virtual constraints
    constraints = create_example_constraints()

    print(f"Number of virtual constraints: {len(constraints)}")
    for vc in constraints:
        print(
            f"  - {vc.joint_name}: K={vc.stiffness}, D={vc.damping}, "
            f"Bézier degree={len(vc.bezier_coeffs)-1}"
        )
    print()

    # Create controller
    controller = VirtualConstraintController(constraints)

    # Create simulator
    stride_frequency = 1.0  # 1 Hz (slow walking)
    dt = 0.001  # 1 ms time step
    simulator = GaitSimulator(controller, stride_frequency, dt)

    print("Simulation parameters:")
    print(f"  - Stride frequency: {stride_frequency} Hz")
    print(f"  - Time step: {dt*1000} ms")
    print()

    # Run simulation
    duration = 3.0  # seconds
    print(f"Running simulation for {duration} seconds...")
    results = simulator.simulate(duration)
    print(f"Simulation complete. {len(results['time'])} time steps.")
    print()

    # Compute statistics
    print("Tracking Performance:")
    joint_names = ["hip", "knee", "ankle"]
    for joint_name in joint_names:
        error = results[joint_name]["error"]
        rmse = np.sqrt(np.mean(error**2))
        max_error = np.max(np.abs(error))
        print(f"  {joint_name:8s}: RMSE = {rmse:8.5f} rad, Max = {max_error:8.5f} rad")
    print()

    # Visualize results
    print("Generating visualization...")
    fig = visualize_results(results, joint_names)

    # Save figure
    output_path = (
        r"D:\Dunna\Documents\hw-1\virtual_constraints\vc_simulation_results.png"
    )
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Results saved to: {output_path}")
    print()

    if args.show:
        plt.show()
    else:
        plt.close(fig)

    print("=" * 70)
    print("Simulation complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

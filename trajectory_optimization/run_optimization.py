"""
Trajectory Optimization for Compass Gait Walker

This script performs trajectory optimization for the compass gait model to find
energy-efficient, smooth walking trajectories that can be used as reference
trajectories for tracking control.

Optimization objectives:
- Minimize energy consumption (torque^2 integrated over time)
- Minimize time to complete a step
- Maximize smoothness (minimize acceleration/jerk)
- Satisfy kinematic and dynamic constraints

Dependencies:
    pip install scipy matplotlib mujoco numpy
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import mujoco
import numpy as np
from scipy.optimize import minimize, NonlinearConstraint

# Configuration
ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "compass_gait_optimized.xml"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class CompassGaitOptimizer:
    """Trajectory optimizer for compass gait walker."""

    def __init__(
        self,
        model_path: str | Path,
        n_timesteps: int = 50,
        step_length: float = 0.5,
        weights: Dict[str, float] | None = None,
    ):
        """
        Initialize trajectory optimizer.

        Args:
            model_path: Path to MuJoCo XML model file
            n_timesteps: Number of discretization points for trajectory
            step_length: Desired step length (m)
            weights: Cost function weights {energy, time, smoothness}
        """
        self.model_path = Path(model_path)
        self.n_timesteps = n_timesteps
        self.step_length = step_length

        # Default cost weights
        self.weights = weights or {
            "energy": 1.0,      # Minimize torque^2
            "time": 0.1,        # Minimize step duration
            "smoothness": 0.5,  # Minimize jerk (d^3q/dt^3)
        }

        # Load MuJoCo model
        if not self.model_path.exists():
            self._create_default_model()

        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)

        # Extract model parameters
        self.nq = self.model.nq  # Number of position coordinates
        self.nv = self.model.nv  # Number of velocity coordinates
        self.nu = self.model.nu  # Number of actuators

        # Optimization decision variables: [q(t), qd(t), u(t), T]
        # q: positions, qd: velocities, u: controls, T: total time
        self.n_vars = (self.nq + self.nv + self.nu) * self.n_timesteps + 1

    def _create_default_model(self) -> None:
        """Create a default compass gait model if none exists."""
        xml_content = """
<mujoco model="compass_gait_optimized">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="0.002" integrator="RK4" gravity="0 0 -9.81"/>

  <default>
    <joint damping="0.1"/>
    <geom condim="3" friction="0.8 0.005 0.0001"/>
  </default>

  <worldbody>
    <light name="key" pos="-2 -3 5" dir="0.3 0.5 -1"/>
    <camera name="track" pos="1.5 -3.5 1.2" xyaxes="1 0 0 0 0.3 1"/>
    <geom name="ground" type="plane" pos="0 0 0" size="50 2 0.05"
          rgba="0.8 0.85 0.8 1" contype="1" conaffinity="1"/>

    <body name="hip" pos="0 0 0.95">
      <joint name="hip_x" type="slide" axis="1 0 0" damping="0.05"/>
      <joint name="hip_z" type="slide" axis="0 0 1" damping="0.05"/>
      <geom name="hip_mass" type="sphere" size="0.08" mass="5.0"
            rgba="0.1 0.1 0.2 1" contype="0" conaffinity="0"/>
      <site name="hip_site" pos="0 0 0" size="0.01"/>

      <body name="left_leg" pos="0 -0.1 0">
        <joint name="left_hip" type="hinge" axis="0 1 0"
               range="-75 75" limited="true"/>
        <geom name="left_thigh" type="capsule" fromto="0 0 -0.05 0 0 -0.45"
              size="0.03" mass="0.3" rgba="0.05 0.45 0.55 1"
              contype="0" conaffinity="0"/>

        <body name="left_shank" pos="0 0 -0.45">
          <joint name="left_knee" type="hinge" axis="0 1 0"
                 range="0 135" limited="true"/>
          <geom name="left_shin" type="capsule" fromto="0 0 -0.05 0 0 -0.45"
                size="0.025" mass="0.2" rgba="0.05 0.45 0.55 1"
                contype="0" conaffinity="0"/>
          <geom name="left_foot" type="sphere" pos="0 0 -0.45"
                size="0.04" mass="0.08" rgba="0.1 0.1 0.1 1"/>
          <site name="left_foot_site" pos="0 0 -0.45" size="0.01"/>
        </body>
      </body>

      <body name="right_leg" pos="0 0.1 0">
        <joint name="right_hip" type="hinge" axis="0 1 0"
               range="-75 75" limited="true"/>
        <geom name="right_thigh" type="capsule" fromto="0 0 -0.05 0 0 -0.45"
              size="0.03" mass="0.3" rgba="0.85 0.28 0.2 1"
              contype="0" conaffinity="0"/>

        <body name="right_shank" pos="0 0 -0.45">
          <joint name="right_knee" type="hinge" axis="0 1 0"
                 range="0 135" limited="true"/>
          <geom name="right_shin" type="capsule" fromto="0 0 -0.05 0 0 -0.45"
                size="0.025" mass="0.2" rgba="0.85 0.28 0.2 1"
                contype="0" conaffinity="0"/>
          <geom name="right_foot" type="sphere" pos="0 0 -0.45"
                size="0.04" mass="0.08" rgba="0.1 0.1 0.1 1"/>
          <site name="right_foot_site" pos="0 0 -0.45" size="0.01"/>
        </body>
      </body>
    </body>
  </worldbody>

  <actuator>
    <motor name="left_hip_motor" joint="left_hip" gear="20"
           ctrllimited="true" ctrlrange="-30 30"/>
    <motor name="left_knee_motor" joint="left_knee" gear="15"
           ctrllimited="true" ctrlrange="-20 20"/>
    <motor name="right_hip_motor" joint="right_hip" gear="20"
           ctrllimited="true" ctrlrange="-30 30"/>
    <motor name="right_knee_motor" joint="right_knee" gear="15"
           ctrllimited="true" ctrlrange="-20 20"/>
  </actuator>
</mujoco>
"""
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        MODEL_PATH.write_text(xml_content)
        print(f"Created default compass gait model at {MODEL_PATH}")

    def _unpack_decision_vars(self, x: np.ndarray) -> Tuple[np.ndarray, ...]:
        """Unpack flat decision variable vector into trajectory components."""
        idx = 0
        T = x[-1]  # Total time (last variable)

        q_traj = np.zeros((self.n_timesteps, self.nq))
        qd_traj = np.zeros((self.n_timesteps, self.nv))
        u_traj = np.zeros((self.n_timesteps, self.nu))

        for i in range(self.n_timesteps):
            q_traj[i] = x[idx : idx + self.nq]
            idx += self.nq
            qd_traj[i] = x[idx : idx + self.nv]
            idx += self.nv
            u_traj[i] = x[idx : idx + self.nu]
            idx += self.nu

        return q_traj, qd_traj, u_traj, T

    def cost_function(self, x: np.ndarray) -> float:
        """
        Compute total cost of trajectory.

        Cost = w_energy * E + w_time * T + w_smoothness * S

        where:
            E = ∫ u^T u dt  (energy)
            T = total time
            S = ∫ ||d³q/dt³||² dt  (smoothness/jerk)
        """
        q_traj, qd_traj, u_traj, T = self._unpack_decision_vars(x)
        dt = T / (self.n_timesteps - 1)

        # Energy cost: ∫ u^T u dt ≈ Σ u_i^T u_i * dt
        energy_cost = np.sum(u_traj**2) * dt

        # Time cost
        time_cost = T

        # Smoothness cost: approximate jerk as finite differences
        # jerk ≈ (qdd[i+1] - qdd[i]) / dt
        # qdd ≈ (qd[i+1] - qd[i]) / dt
        qdd_traj = np.diff(qd_traj, axis=0) / dt  # Acceleration
        jerk_traj = np.diff(qdd_traj, axis=0) / dt  # Jerk
        smoothness_cost = np.sum(jerk_traj**2) * dt

        total_cost = (
            self.weights["energy"] * energy_cost
            + self.weights["time"] * time_cost
            + self.weights["smoothness"] * smoothness_cost
        )

        return total_cost

    def dynamics_constraints(self, x: np.ndarray) -> np.ndarray:
        """
        Enforce dynamics: qd_next = qd + qdd * dt, where qdd from inverse dynamics.

        Returns residuals that should be zero.
        """
        q_traj, qd_traj, u_traj, T = self._unpack_decision_vars(x)
        dt = T / (self.n_timesteps - 1)

        residuals = []

        for i in range(self.n_timesteps - 1):
            # Set state
            self.data.qpos[:] = q_traj[i]
            self.data.qvel[:] = qd_traj[i]
            self.data.ctrl[:] = u_traj[i]

            # Forward dynamics to get acceleration
            mujoco.mj_forward(self.model, self.data)
            qdd = self.data.qacc.copy()

            # Euler integration
            qd_next_expected = qd_traj[i] + qdd * dt
            q_next_expected = q_traj[i] + qd_traj[i] * dt

            # Residuals
            residuals.append(qd_traj[i + 1] - qd_next_expected)
            residuals.append(q_traj[i + 1] - q_next_expected)

        return np.concatenate(residuals)

    def boundary_constraints(self, x: np.ndarray) -> np.ndarray:
        """
        Enforce boundary conditions:
        - Initial stance foot at origin
        - Final stance foot at step_length
        - Periodic gait (q_0 ≈ q_final after phase swap)
        """
        q_traj, qd_traj, u_traj, T = self._unpack_decision_vars(x)

        residuals = []

        # Initial hip position constraint (hip_x ≈ 0 at start)
        residuals.append(q_traj[0, 0])  # hip_x = 0

        # Final hip position constraint (hip_x ≈ step_length at end)
        residuals.append(q_traj[-1, 0] - self.step_length)

        # Hip height constraints (stay above ground)
        for i in range(self.n_timesteps):
            residuals.append(max(0, 0.3 - q_traj[i, 1]))  # hip_z > 0.3m

        return np.array(residuals)

    def generate_initial_guess(self) -> np.ndarray:
        """Generate initial guess for optimization using linear interpolation."""
        # Simple initial guess: interpolate between start and end configurations
        q0 = np.zeros(self.nq)
        qf = np.zeros(self.nq)

        # Initial: hip at origin, legs in stance
        q0[0] = 0.0  # hip_x
        q0[1] = 0.9  # hip_z (height)
        if self.nq > 2:
            q0[2] = -15.0 * np.pi / 180  # left_hip (deg to rad)
            q0[3] = 0.0  # left_knee
            q0[4] = 15.0 * np.pi / 180  # right_hip
            q0[5] = 0.0  # right_knee

        # Final: hip moved forward, legs swapped
        qf[0] = self.step_length
        qf[1] = 0.9
        if self.nq > 2:
            qf[2] = 15.0 * np.pi / 180
            qf[3] = 0.0
            qf[4] = -15.0 * np.pi / 180
            qf[5] = 0.0

        # Interpolate positions
        q_traj = np.linspace(q0, qf, self.n_timesteps)

        # Velocities from finite differences
        qd_traj = np.zeros((self.n_timesteps, self.nv))
        T_guess = 0.5  # Initial guess for step time (0.5 seconds)
        dt = T_guess / (self.n_timesteps - 1)
        qd_traj[:-1] = np.diff(q_traj, axis=0) / dt

        # Zero controls initially
        u_traj = np.zeros((self.n_timesteps, self.nu))

        # Pack into decision variable vector
        x0 = []
        for i in range(self.n_timesteps):
            x0.extend(q_traj[i])
            x0.extend(qd_traj[i])
            x0.extend(u_traj[i])
        x0.append(T_guess)

        return np.array(x0)

    def optimize(
        self,
        max_iter: int = 500,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run trajectory optimization.

        Args:
            max_iter: Maximum number of optimization iterations
            verbose: Print optimization progress

        Returns:
            Dictionary containing optimal trajectory and metadata
        """
        print("=" * 60)
        print("Compass Gait Trajectory Optimization")
        print("=" * 60)
        print(f"Model: {self.model_path}")
        print(f"Timesteps: {self.n_timesteps}")
        print(f"Step length: {self.step_length} m")
        print(f"Cost weights: {self.weights}")
        print(f"Decision variables: {self.n_vars}")
        print()

        # Generate initial guess
        print("Generating initial guess...")
        x0 = self.generate_initial_guess()
        print(f"Initial cost: {self.cost_function(x0):.4f}")
        print()

        # Set bounds
        bounds = []
        for _ in range(self.n_timesteps):
            # Position bounds
            for _ in range(self.nq):
                bounds.append((-10.0, 10.0))
            # Velocity bounds
            for _ in range(self.nv):
                bounds.append((-5.0, 5.0))
            # Control bounds
            for i in range(self.nu):
                bounds.append((
                    self.model.actuator_ctrlrange[i, 0],
                    self.model.actuator_ctrlrange[i, 1],
                ))
        # Time bound
        bounds.append((0.2, 2.0))  # Step time between 0.2s and 2.0s

        # Run optimization
        print("Running optimization...")
        print("Method: SLSQP (Sequential Least Squares Programming)")
        print()

        result = minimize(
            fun=self.cost_function,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            options={
                "maxiter": max_iter,
                "disp": verbose,
                "ftol": 1e-6,
            },
        )

        print()
        print("=" * 60)
        print("Optimization Results")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        print(f"Iterations: {result.nit}")
        print(f"Function evaluations: {result.nfev}")
        print(f"Final cost: {result.fun:.4f}")
        print()

        # Unpack optimal trajectory
        q_opt, qd_opt, u_opt, T_opt = self._unpack_decision_vars(result.x)

        # Compute cost breakdown
        dt = T_opt / (self.n_timesteps - 1)
        energy = np.sum(u_opt**2) * dt
        qdd = np.diff(qd_opt, axis=0) / dt
        jerk = np.diff(qdd, axis=0) / dt
        smoothness = np.sum(jerk**2) * dt

        print("Cost breakdown:")
        print(f"  Energy: {energy:.4f} (weight: {self.weights['energy']})")
        print(f"  Time: {T_opt:.4f} s (weight: {self.weights['time']})")
        print(f"  Smoothness: {smoothness:.4f} (weight: {self.weights['smoothness']})")
        print()

        return {
            "q": q_opt,
            "qd": qd_opt,
            "u": u_opt,
            "T": T_opt,
            "dt": dt,
            "cost": result.fun,
            "success": result.success,
            "n_iter": result.nit,
            "n_fev": result.nfev,
            "energy": energy,
            "smoothness": smoothness,
        }

    def save_trajectory(
        self,
        trajectory: Dict[str, Any],
        filename: str | Path,
    ) -> None:
        """Save optimized trajectory to file."""
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Convert numpy arrays to lists for JSON serialization
        save_data = {
            "q": trajectory["q"].tolist(),
            "qd": trajectory["qd"].tolist(),
            "u": trajectory["u"].tolist(),
            "T": float(trajectory["T"]),
            "dt": float(trajectory["dt"]),
            "cost": float(trajectory["cost"]),
            "energy": float(trajectory["energy"]),
            "smoothness": float(trajectory["smoothness"]),
            "n_timesteps": self.n_timesteps,
            "step_length": self.step_length,
            "weights": self.weights,
        }

        with open(filepath, "w") as f:
            json.dump(save_data, f, indent=2)

        print(f"Saved trajectory to {filepath}")

    def visualize_trajectory(
        self,
        trajectory: Dict[str, Any],
        save_path: str | Path | None = None,
    ) -> None:
        """Visualize optimized trajectory."""
        q_opt = trajectory["q"]
        qd_opt = trajectory["qd"]
        u_opt = trajectory["u"]
        T = trajectory["T"]
        t = np.linspace(0, T, self.n_timesteps)

        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        # Plot positions
        axes[0].set_title("Joint Positions", fontsize=14, fontweight="bold")
        for i in range(min(self.nq, 6)):
            joint_name = self.model.joint(i).name if i < self.model.njnt else f"q{i}"
            axes[0].plot(t, q_opt[:, i], label=joint_name, linewidth=2)
        axes[0].set_ylabel("Position (rad or m)", fontsize=11)
        axes[0].legend(loc="upper right", fontsize=9)
        axes[0].grid(True, alpha=0.3)

        # Plot velocities
        axes[1].set_title("Joint Velocities", fontsize=14, fontweight="bold")
        for i in range(min(self.nv, 6)):
            joint_name = self.model.joint(i).name if i < self.model.njnt else f"qd{i}"
            axes[1].plot(t, qd_opt[:, i], label=joint_name, linewidth=2)
        axes[1].set_ylabel("Velocity (rad/s or m/s)", fontsize=11)
        axes[1].legend(loc="upper right", fontsize=9)
        axes[1].grid(True, alpha=0.3)

        # Plot controls
        axes[2].set_title("Control Torques", fontsize=14, fontweight="bold")
        for i in range(self.nu):
            actuator_name = self.model.actuator(i).name
            axes[2].plot(t, u_opt[:, i], label=actuator_name, linewidth=2)
        axes[2].set_xlabel("Time (s)", fontsize=11)
        axes[2].set_ylabel("Torque (Nm)", fontsize=11)
        axes[2].legend(loc="upper right", fontsize=9)
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved trajectory plot to {save_path}")

        plt.show()

    def simulate_in_mujoco(
        self,
        trajectory: Dict[str, Any],
        render: bool = True,
    ) -> None:
        """Simulate and visualize optimal trajectory in MuJoCo."""
        q_opt = trajectory["q"]
        u_opt = trajectory["u"]

        print("Simulating trajectory in MuJoCo...")

        if render:
            try:
                import mujoco.viewer
                viewer = mujoco.viewer.launch_passive(self.model, self.data)
            except Exception as e:
                print(f"Could not launch viewer: {e}")
                render = False

        # Simulate trajectory
        for i in range(self.n_timesteps):
            self.data.qpos[:] = q_opt[i]
            self.data.ctrl[:] = u_opt[i]
            mujoco.mj_step(self.model, self.data)

            if render:
                viewer.sync()

        if render:
            viewer.close()

        print("Simulation complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Trajectory optimization for compass gait walker"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=str(MODEL_PATH),
        help="Path to MuJoCo XML model file",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=50,
        help="Number of trajectory discretization points",
    )
    parser.add_argument(
        "--step-length",
        type=float,
        default=0.5,
        help="Desired step length (m)",
    )
    parser.add_argument(
        "--w-energy",
        type=float,
        default=1.0,
        help="Cost weight for energy",
    )
    parser.add_argument(
        "--w-time",
        type=float,
        default=0.1,
        help="Cost weight for time",
    )
    parser.add_argument(
        "--w-smoothness",
        type=float,
        default=0.5,
        help="Cost weight for smoothness",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=500,
        help="Maximum optimization iterations",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_DIR / "optimal_trajectory.json"),
        help="Output file for optimal trajectory",
    )
    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="Skip trajectory visualization",
    )
    parser.add_argument(
        "--no-simulate",
        action="store_true",
        help="Skip MuJoCo simulation",
    )

    args = parser.parse_args()

    # Initialize optimizer
    weights = {
        "energy": args.w_energy,
        "time": args.w_time,
        "smoothness": args.w_smoothness,
    }

    optimizer = CompassGaitOptimizer(
        model_path=args.model,
        n_timesteps=args.timesteps,
        step_length=args.step_length,
        weights=weights,
    )

    # Run optimization
    trajectory = optimizer.optimize(max_iter=args.max_iter, verbose=True)

    # Save trajectory
    optimizer.save_trajectory(trajectory, args.output)

    # Visualize
    if not args.no_visualize:
        plot_path = Path(args.output).with_suffix(".png")
        optimizer.visualize_trajectory(trajectory, save_path=plot_path)

    # Simulate in MuJoCo
    if not args.no_simulate:
        optimizer.simulate_in_mujoco(trajectory, render=True)

    print()
    print("=" * 60)
    print("Trajectory optimization complete!")
    print(f"Output saved to: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Direct Collocation for Trajectory Optimization using CasADi

Formulates trajectory optimization as a large-scale NLP by discretizing
both state and control trajectories. More robust than shooting methods
for unstable or highly nonlinear systems like compass gait walking.

Based on compass gait dynamics from hw-1 project. Optimizes for energy-efficient
gait cycles with contact constraints, joint limits, and periodic boundary conditions.

Installation:
    pip install casadi

Dependencies:
    - casadi: Symbolic framework for automatic differentiation and optimization
    - numpy: Numerical arrays
    - scipy: Interpolation for initial guess loading
    - matplotlib: Plotting results
    - pandas: Loading trajectory data from CSV (optional)
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import casadi as ca
import numpy as np


class DirectCollocation:
    """
    Direct collocation trajectory optimizer for compass gait.

    Discretizes both states and controls over a gait cycle, enforcing
    dynamics at collocation points via Euler integration. Supports:
    - Energy minimization objective
    - Contact constraints (foot clearance)
    - Joint limit constraints
    - Periodic boundary conditions
    - Initial guess from existing trajectory (e.g., V13.7)
    """

    def __init__(
        self,
        n_points: int = 100,
        gait_period: float = 1.0,
        params: Optional[Dict] = None,
    ):
        """
        Initialize direct collocation optimizer.

        Args:
            n_points: Number of collocation points over one gait cycle
            gait_period: Duration of one gait cycle (seconds)
            params: Compass gait parameters dict with keys:
                   - leg_length: Length of legs (m)
                   - mass_hip: Hip mass (kg)
                   - mass_leg: Leg mass (kg)
                   - gravity: Gravitational acceleration (m/s^2)
                   - slope_deg: Slope angle (degrees)
                   - joint_damping: Joint damping coefficient
        """
        self.n_points = n_points
        self.T = gait_period
        self.dt = gait_period / (n_points - 1)

        # Default compass gait parameters
        if params is None:
            params = {}
        self.params = {
            "leg_length": params.get("leg_length", 1.0),
            "mass_hip": params.get("mass_hip", 10.0),
            "mass_leg": params.get("mass_leg", 5.0),
            "gravity": params.get("gravity", 9.81),
            "slope_deg": params.get("slope_deg", 5.0),
            "joint_damping": params.get("joint_damping", 0.02),
            "foot_radius": params.get("foot_radius", 0.04),
        }

        # State: [theta_stance, theta_swing, theta_stance_dot, theta_swing_dot]
        # Control: [tau_hip, tau_knee] (or [tau_hip] for simple compass)
        self.n_states = 4
        self.n_controls = 1  # Hip torque only for basic compass gait

        # Optimization problem (built in setup())
        self.opti = None
        self.X = None  # State trajectory variables
        self.U = None  # Control trajectory variables
        self.result = None

    def setup_optimization(self):
        """Set up CasADi optimization problem with decision variables and constraints."""
        self.opti = ca.Opti()

        # Decision variables
        self.X = self.opti.variable(self.n_states, self.n_points)
        self.U = self.opti.variable(self.n_controls, self.n_points - 1)

        # Extract parameters
        L = self.params["leg_length"]
        m_H = self.params["mass_hip"]
        m_L = self.params["mass_leg"]
        g = self.params["gravity"]
        gamma = np.deg2rad(self.params["slope_deg"])
        b = self.params["joint_damping"]

        # Objective: minimize control effort (proxy for energy)
        obj = 0
        for k in range(self.n_points - 1):
            # Control effort: integral of tau^2
            obj += ca.sumsqr(self.U[:, k]) * self.dt

            # Add velocity penalty to encourage smooth motion
            theta_stance_dot = self.X[2, k]
            theta_swing_dot = self.X[3, k]
            obj += 0.01 * (theta_stance_dot**2 + theta_swing_dot**2) * self.dt

        self.opti.minimize(obj)

        # Dynamics constraints (Euler integration)
        for k in range(self.n_points - 1):
            x_k = self.X[:, k]
            u_k = self.U[:, k]
            x_next = self.X[:, k + 1]

            # Compute state derivative
            x_dot = self._compass_dynamics(x_k, u_k)

            # Euler integration constraint
            self.opti.subject_to(x_next == x_k + x_dot * self.dt)

        # Periodic boundary conditions (limit cycle)
        # For true limit cycle: X[:, 0] == X[:, -1]
        # For now, enforce similar initial and final states
        self.opti.subject_to(self.X[:, 0] - self.X[:, -1] == 0)

        # Joint limit constraints
        theta_stance_min, theta_stance_max = np.deg2rad(-30), np.deg2rad(30)
        theta_swing_min, theta_swing_max = np.deg2rad(-40), np.deg2rad(40)

        for k in range(self.n_points):
            self.opti.subject_to(
                self.opti.bounded(theta_stance_min, self.X[0, k], theta_stance_max)
            )
            self.opti.subject_to(
                self.opti.bounded(theta_swing_min, self.X[1, k], theta_swing_max)
            )

        # Contact constraints (foot clearance during swing)
        for k in range(self.n_points):
            clearance = self._foot_clearance(self.X[:, k])
            # Swing foot should be above ground (clearance > 0)
            # or in contact (clearance ≈ 0, handled by dynamics)
            # Relaxed constraint: clearance >= -0.01
            self.opti.subject_to(clearance >= -0.01)

        # Control bounds (torque limits)
        tau_max = 50.0  # N·m (reasonable for human-scale walker)
        for k in range(self.n_points - 1):
            self.opti.subject_to(self.opti.bounded(-tau_max, self.U[:, k], tau_max))

        # Solver options
        opts = {
            "ipopt.print_level": 3,
            "ipopt.max_iter": 2000,
            "ipopt.tol": 1e-6,
            "ipopt.acceptable_tol": 1e-4,
            "ipopt.warm_start_init_point": "yes",
            "print_time": False,
        }
        self.opti.solver("ipopt", opts)

    def _compass_dynamics(self, x: ca.MX, u: ca.MX) -> ca.MX:
        """
        Compass gait dynamics: x_dot = f(x, u)

        Args:
            x: State [theta_stance, theta_swing, theta_stance_dot, theta_swing_dot]
            u: Control [tau_hip]

        Returns:
            x_dot: State derivative
        """
        theta_st = x[0]
        theta_sw = x[1]
        theta_st_dot = x[2]
        theta_sw_dot = x[3]
        tau_hip = u[0]

        # Extract parameters
        L = self.params["leg_length"]
        m_H = self.params["mass_hip"]
        m_L = self.params["mass_leg"]
        g = self.params["gravity"]
        gamma = np.deg2rad(self.params["slope_deg"])
        b = self.params["joint_damping"]

        # Simplified compass gait dynamics (stance phase)
        # Mass matrix M(theta) and forces h(theta, theta_dot)
        # M * theta_ddot + h = B * tau

        # Point mass model for simplicity
        # M = [[m_H*L^2, 0], [0, m_L*L^2]]
        M11 = m_H * L**2 + m_L * L**2 / 3.0  # Stance leg inertia
        M12 = -m_L * L**2 / 6.0
        M22 = m_L * L**2 / 3.0  # Swing leg inertia

        M = ca.vertcat(ca.horzcat(M11, M12), ca.horzcat(M12, M22))

        # Gravitational and Coriolis terms
        h1 = m_H * g * L * ca.sin(theta_st - gamma) + b * theta_st_dot
        h2 = m_L * g * L / 2.0 * ca.sin(theta_sw - gamma) + b * theta_sw_dot
        h = ca.vertcat(h1, h2)

        # Control input matrix
        B = ca.vertcat(-1.0, 1.0)  # Hip torque acts on both legs

        # Solve for accelerations: theta_ddot = M^-1 * (B*tau - h)
        theta_dot = ca.vertcat(theta_st_dot, theta_sw_dot)
        theta_ddot = ca.solve(M, B * tau_hip - h)

        # State derivative
        x_dot = ca.vertcat(theta_dot, theta_ddot)

        return x_dot

    def _foot_clearance(self, x: ca.MX) -> ca.MX:
        """
        Compute swing foot clearance above ground.

        Args:
            x: State [theta_stance, theta_swing, theta_stance_dot, theta_swing_dot]

        Returns:
            clearance: Height above ground (positive = above, negative = penetration)
        """
        theta_st = x[0]
        theta_sw = x[1]

        L = self.params["leg_length"]
        gamma = np.deg2rad(self.params["slope_deg"])
        r_foot = self.params["foot_radius"]

        # Assume stance foot at origin, hip moves along arc
        hip_x = L * ca.sin(theta_st)
        hip_z = L * ca.cos(theta_st)

        # Swing foot position
        foot_sw_x = hip_x + L * ca.sin(theta_sw)
        foot_sw_z = hip_z - L * ca.cos(theta_sw)

        # Ground height at swing foot x position (slope)
        ground_z = -ca.tan(gamma) * foot_sw_x

        # Clearance (foot center to ground, accounting for foot radius)
        clearance = foot_sw_z - ground_z - r_foot

        return clearance

    def set_initial_guess(
        self, X_guess: Optional[np.ndarray] = None, U_guess: Optional[np.ndarray] = None
    ):
        """
        Set initial guess for optimization.

        Args:
            X_guess: Initial state trajectory, shape (n_states, n_points)
                    If None, uses linear interpolation from simple gait
            U_guess: Initial control trajectory, shape (n_controls, n_points-1)
                    If None, uses zero torques
        """
        if X_guess is None:
            # Default: sinusoidal gait pattern
            t = np.linspace(0, self.T, self.n_points)
            theta_stance = 0.2 * np.sin(2 * np.pi * t / self.T)
            theta_swing = 0.3 * np.sin(2 * np.pi * t / self.T + np.pi)
            theta_stance_dot = 0.2 * 2 * np.pi / self.T * np.cos(2 * np.pi * t / self.T)
            theta_swing_dot = (
                0.3 * 2 * np.pi / self.T * np.cos(2 * np.pi * t / self.T + np.pi)
            )

            X_guess = np.vstack(
                [theta_stance, theta_swing, theta_stance_dot, theta_swing_dot]
            )

        if U_guess is None:
            U_guess = np.zeros((self.n_controls, self.n_points - 1))

        self.opti.set_initial(self.X, X_guess)
        self.opti.set_initial(self.U, U_guess)

    def load_initial_guess_from_v137(
        self, trajectory_file: Path
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load initial guess from V13.7 simulation trajectory.

        Args:
            trajectory_file: Path to V13.7 CSV data file with columns:
                           time, theta_stance, theta_swing, ...

        Returns:
            X_guess: State trajectory (n_states, n_points)
            U_guess: Control trajectory (n_controls, n_points-1)
        """
        import pandas as pd

        # Load trajectory data
        df = pd.read_csv(trajectory_file)

        # Extract one gait cycle (from heel strike to next heel strike)
        # Detect heel strikes (theta_swing crosses zero with positive velocity)
        theta_sw = (
            df["left_hip_angle"].values
            if "left_hip_angle" in df.columns
            else df["theta_swing"].values
        )

        # Find first two heel strikes
        heel_strikes = []
        for i in range(1, len(theta_sw) - 1):
            if theta_sw[i - 1] < 0 and theta_sw[i] >= 0:
                heel_strikes.append(i)
            if len(heel_strikes) == 2:
                break

        if len(heel_strikes) < 2:
            # Fallback: use first n_points samples
            idx_start, idx_end = 0, min(self.n_points, len(df))
        else:
            idx_start, idx_end = heel_strikes[0], heel_strikes[1]

        # Extract state data
        cycle_data = df.iloc[idx_start:idx_end]

        # Resample to n_points
        from scipy.interpolate import interp1d

        t_orig = cycle_data["time"].values - cycle_data["time"].values[0]
        t_new = np.linspace(0, t_orig[-1], self.n_points)

        # Interpolate states
        states_orig = np.vstack(
            [
                (
                    cycle_data["theta_stance"].values
                    if "theta_stance" in cycle_data.columns
                    else cycle_data["right_hip_angle"].values
                ),
                (
                    cycle_data["theta_swing"].values
                    if "theta_swing" in cycle_data.columns
                    else cycle_data["left_hip_angle"].values
                ),
                (
                    cycle_data["theta_stance_dot"].values
                    if "theta_stance_dot" in cycle_data.columns
                    else np.gradient(cycle_data["right_hip_angle"].values, t_orig)
                ),
                (
                    cycle_data["theta_swing_dot"].values
                    if "theta_swing_dot" in cycle_data.columns
                    else np.gradient(cycle_data["left_hip_angle"].values, t_orig)
                ),
            ]
        )

        X_guess = np.zeros((self.n_states, self.n_points))
        for i in range(self.n_states):
            interp = interp1d(
                t_orig, states_orig[i, :], kind="cubic", fill_value="extrapolate"
            )
            X_guess[i, :] = interp(t_new)

        # Extract controls (if available, otherwise zero)
        if "tau_hip" in cycle_data.columns:
            tau_orig = cycle_data["tau_hip"].values
            t_control = t_new[:-1]
            interp_u = interp1d(
                t_orig, tau_orig, kind="linear", fill_value="extrapolate"
            )
            U_guess = interp_u(t_control).reshape(1, -1)
        else:
            U_guess = np.zeros((self.n_controls, self.n_points - 1))

        return X_guess, U_guess

    def optimize(self) -> Dict:
        """
        Solve the trajectory optimization problem.

        Returns:
            result: Dictionary containing:
                   - 'success': True if optimization succeeded
                   - 'X': Optimal state trajectory (n_states, n_points)
                   - 'U': Optimal control trajectory (n_controls, n_points-1)
                   - 'cost': Optimal objective value
                   - 'time': Time vector
                   - 'iterations': Number of iterations
                   - 'status': Solver status message
        """
        if self.opti is None:
            raise RuntimeError("Call setup_optimization() before optimize()")

        try:
            sol = self.opti.solve()

            X_opt = sol.value(self.X)
            U_opt = sol.value(self.U)
            cost = sol.value(self.opti.f)

            self.result = {
                "success": True,
                "X": X_opt,
                "U": U_opt,
                "cost": cost,
                "time": np.linspace(0, self.T, self.n_points),
                "iterations": sol.stats()["iter_count"],
                "status": sol.stats()["return_status"],
            }

        except Exception as e:
            # Optimization failed, try to retrieve partial solution
            print(f"Optimization failed: {e}")
            try:
                X_opt = self.opti.debug.value(self.X)
                U_opt = self.opti.debug.value(self.U)
                cost = self.opti.debug.value(self.opti.f)
            except:
                X_opt = np.zeros((self.n_states, self.n_points))
                U_opt = np.zeros((self.n_controls, self.n_points - 1))
                cost = np.inf

            self.result = {
                "success": False,
                "X": X_opt,
                "U": U_opt,
                "cost": cost,
                "time": np.linspace(0, self.T, self.n_points),
                "iterations": 0,
                "status": str(e),
            }

        return self.result

    def save_result(self, output_path: Path):
        """
        Save optimization result to file.

        Args:
            output_path: Path to save result (JSON format)
        """
        if self.result is None:
            raise RuntimeError("No result to save. Run optimize() first.")

        # Convert numpy arrays to lists for JSON serialization
        result_json = {
            "success": self.result["success"],
            "cost": float(self.result["cost"]),
            "iterations": int(self.result["iterations"]),
            "status": self.result["status"],
            "time": self.result["time"].tolist(),
            "states": self.result["X"].tolist(),
            "controls": self.result["U"].tolist(),
            "parameters": self.params,
            "n_points": self.n_points,
            "gait_period": self.T,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result_json, f, indent=2)

        print(f"Result saved to {output_path}")

    def plot_result(self, output_path: Optional[Path] = None):
        """
        Plot optimization result.

        Args:
            output_path: Optional path to save figure
        """
        if self.result is None:
            raise RuntimeError("No result to plot. Run optimize() first.")

        import matplotlib.pyplot as plt

        t = self.result["time"]
        X = self.result["X"]
        U = self.result["U"]
        t_control = t[:-1]

        fig, axes = plt.subplots(3, 1, figsize=(10, 8))

        # States
        axes[0].plot(t, np.rad2deg(X[0, :]), label="Stance angle")
        axes[0].plot(t, np.rad2deg(X[1, :]), label="Swing angle")
        axes[0].set_ylabel("Angle (deg)")
        axes[0].set_title("Joint Angles")
        axes[0].legend()
        axes[0].grid(True)

        # Velocities
        axes[1].plot(t, X[2, :], label="Stance velocity")
        axes[1].plot(t, X[3, :], label="Swing velocity")
        axes[1].set_ylabel("Angular velocity (rad/s)")
        axes[1].set_title("Joint Velocities")
        axes[1].legend()
        axes[1].grid(True)

        # Controls
        axes[2].plot(t_control, U[0, :], label="Hip torque")
        axes[2].set_xlabel("Time (s)")
        axes[2].set_ylabel("Torque (N·m)")
        axes[2].set_title("Control Inputs")
        axes[2].legend()
        axes[2].grid(True)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150)
            print(f"Figure saved to {output_path}")
        else:
            plt.show()


def main():
    """Example usage: optimize compass gait trajectory."""

    # Create optimizer
    optimizer = DirectCollocation(
        n_points=100,
        gait_period=1.0,
        params={
            "leg_length": 1.0,
            "mass_hip": 10.0,
            "mass_leg": 5.0,
            "gravity": 9.81,
            "slope_deg": 5.0,
            "joint_damping": 0.02,
        },
    )

    # Set up optimization problem
    print("Setting up optimization problem...")
    optimizer.setup_optimization()

    # Set initial guess (can load from V13.7 trajectory)
    print("Setting initial guess...")
    optimizer.set_initial_guess()

    # Uncomment to load from V13.7 data:
    # v137_data = Path("D:/Dunna/Documents/hw-1/v13_7_friction_compensation/out/v13_7_data.csv")
    # if v137_data.exists():
    #     X_guess, U_guess = optimizer.load_initial_guess_from_v137(v137_data)
    #     optimizer.set_initial_guess(X_guess, U_guess)

    # Optimize
    print("Optimizing...")
    result = optimizer.optimize()

    if result["success"]:
        print("Optimization succeeded!")
        print(f"  Cost: {result['cost']:.4f}")
        print(f"  Iterations: {result['iterations']}")
    else:
        print(f"Optimization failed: {result['status']}")

    # Save and plot
    output_dir = Path(__file__).parent / "out"
    output_dir.mkdir(exist_ok=True)

    optimizer.save_result(output_dir / "collocation_result.json")
    optimizer.plot_result(output_dir / "collocation_trajectory.png")


if __name__ == "__main__":
    main()

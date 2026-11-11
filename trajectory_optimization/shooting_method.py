"""
Single Shooting Method for Trajectory Optimization

A simpler alternative to collocation methods. Good for:
- Comparison with collocation results
- Problems with stable dynamics
- Initial feasibility studies

Single shooting directly integrates the dynamics forward in time,
optimizing only the control trajectory. Simpler but less robust than
multiple shooting or collocation for unstable or highly nonlinear systems.
"""

from typing import Callable, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize


class SingleShootingOptimizer:
    """
    Single shooting trajectory optimization.

    Optimizes control inputs by forward-integrating dynamics from initial state.
    Simpler than collocation but can be sensitive to initial guess.
    """

    def __init__(
        self,
        dynamics: Callable,
        initial_state: np.ndarray,
        target_state: np.ndarray,
        n_steps: int,
        dt: float,
        control_bounds: Tuple[np.ndarray, np.ndarray],
    ):
        """
        Args:
            dynamics: Function f(t, x, u) returning state derivatives
            initial_state: Starting state x0
            target_state: Desired final state xf
            n_steps: Number of time steps
            dt: Time step duration
            control_bounds: (u_min, u_max) arrays
        """
        self.dynamics = dynamics
        self.x0 = np.array(initial_state)
        self.xf = np.array(target_state)
        self.n_steps = n_steps
        self.dt = dt
        self.u_min, self.u_max = control_bounds

        self.n_states = len(self.x0)
        self.n_controls = len(self.u_min)
        self.T = n_steps * dt

        # Storage for optimization results
        self.result = None
        self.optimal_controls = None
        self.optimal_trajectory = None

    def _integrate_trajectory(self, controls: np.ndarray) -> np.ndarray:
        """
        Forward integrate dynamics with given control sequence.

        Args:
            controls: Flat array of controls [u0, u1, ..., u_{N-1}]
                     Shape: (n_steps * n_controls,)

        Returns:
            trajectory: State trajectory, shape (n_steps+1, n_states)
        """
        U = controls.reshape(self.n_steps, self.n_controls)

        # Time points for integration
        t_span = (0, self.T)
        t_eval = np.linspace(0, self.T, self.n_steps + 1)

        def dynamics_interpolated(t, x):
            # Find which control to use at time t
            idx = int(np.clip(t / self.dt, 0, self.n_steps - 1))
            u = U[idx]
            return self.dynamics(t, x, u)

        # Integrate forward
        sol = solve_ivp(
            dynamics_interpolated,
            t_span,
            self.x0,
            t_eval=t_eval,
            method="RK45",
            rtol=1e-6,
            atol=1e-8,
        )

        return sol.y.T  # Shape: (n_steps+1, n_states)

    def _objective(self, controls: np.ndarray) -> float:
        """
        Objective function: terminal cost + control effort.

        Args:
            controls: Flat control array

        Returns:
            cost: Scalar cost value
        """
        # Integrate to get final state
        trajectory = self._integrate_trajectory(controls)
        x_final = trajectory[-1]

        # Terminal cost (tracking error)
        terminal_cost = 100.0 * np.sum((x_final - self.xf) ** 2)

        # Control effort cost
        U = controls.reshape(self.n_steps, self.n_controls)
        control_cost = 0.1 * np.sum(U**2) * self.dt

        # Control smoothness (penalize rapid changes)
        smoothness_cost = 1.0 * np.sum(np.diff(U, axis=0) ** 2)

        return terminal_cost + control_cost + smoothness_cost

    def _constraints(self, controls: np.ndarray) -> Dict:
        """
        Nonlinear constraints (if needed).

        For single shooting, usually only terminal constraints are needed
        since dynamics are automatically satisfied by integration.
        """
        trajectory = self._integrate_trajectory(controls)
        x_final = trajectory[-1]

        # Example: terminal constraint (could be equality or inequality)
        # Here we use soft constraint via objective instead
        return {}

    def optimize(
        self,
        initial_guess: Optional[np.ndarray] = None,
        method: str = "SLSQP",
        max_iter: int = 200,
        verbose: bool = True,
    ) -> Dict:
        """
        Run single shooting optimization.

        Args:
            initial_guess: Initial control sequence (if None, uses zeros)
            method: Optimization method ('SLSQP', 'trust-constr', etc.)
            max_iter: Maximum iterations
            verbose: Print progress

        Returns:
            result_dict: Dictionary with optimization results
        """
        # Initial guess
        if initial_guess is None:
            u_guess = np.zeros(self.n_steps * self.n_controls)
        else:
            u_guess = initial_guess.flatten()

        # Bounds on controls
        bounds = []
        for _ in range(self.n_steps):
            for i in range(self.n_controls):
                bounds.append((self.u_min[i], self.u_max[i]))

        # Optimization options
        options = {"maxiter": max_iter, "disp": verbose, "ftol": 1e-6}

        if verbose:
            print("Starting single shooting optimization...")
            print(f"  States: {self.n_states}, Controls: {self.n_controls}")
            print(f"  Time steps: {self.n_steps}, dt: {self.dt}")
            print(f"  Total time: {self.T:.2f}s")

        # Run optimization
        self.result = minimize(
            self._objective, u_guess, method=method, bounds=bounds, options=options
        )

        # Extract results
        self.optimal_controls = self.result.x.reshape(self.n_steps, self.n_controls)
        self.optimal_trajectory = self._integrate_trajectory(self.result.x)

        if verbose:
            print(f"\nOptimization {'succeeded' if self.result.success else 'failed'}")
            print(f"  Final cost: {self.result.fun:.6f}")
            print(f"  Iterations: {self.result.nit}")
            print(
                f"  Terminal error: {np.linalg.norm(self.optimal_trajectory[-1] - self.xf):.6f}"
            )

        return {
            "success": self.result.success,
            "cost": self.result.fun,
            "controls": self.optimal_controls,
            "trajectory": self.optimal_trajectory,
            "iterations": self.result.nit,
            "message": self.result.message,
        }

    def plot_results(self, save_path: Optional[str] = None):
        """Plot optimization results."""
        if self.optimal_trajectory is None:
            print("No results to plot. Run optimize() first.")
            return

        t = np.linspace(0, self.T, self.n_steps + 1)
        t_control = np.linspace(0, self.T - self.dt, self.n_steps)

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # Plot states
        ax = axes[0]
        for i in range(self.n_states):
            ax.plot(t, self.optimal_trajectory[:, i], label=f"State {i+1}")
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.3)
        ax.plot(t[-1], self.xf, "ro", markersize=8, label="Target")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("State")
        ax.set_title("Optimal State Trajectory (Single Shooting)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot controls
        ax = axes[1]
        for i in range(self.n_controls):
            ax.step(
                t_control,
                self.optimal_controls[:, i],
                where="post",
                label=f"Control {i+1}",
            )
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.3)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Control")
        ax.set_title("Optimal Control Inputs")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")
        else:
            plt.show()


# ============================================================================
# Example: Double Integrator
# ============================================================================


def double_integrator_dynamics(t, x, u):
    """
    Double integrator: position and velocity.
    x = [position, velocity]
    u = [acceleration]
    """
    return np.array([x[1], u[0]])


def example_double_integrator():
    """Example: Move from rest to target position."""
    print("=" * 60)
    print("Single Shooting Example: Double Integrator")
    print("=" * 60)

    # Problem setup
    x0 = np.array([0.0, 0.0])  # Start at rest at origin
    xf = np.array([1.0, 0.0])  # End at position 1.0 at rest

    n_steps = 50
    dt = 0.05

    u_min = np.array([-2.0])  # Acceleration limits
    u_max = np.array([2.0])

    # Create optimizer
    optimizer = SingleShootingOptimizer(
        dynamics=double_integrator_dynamics,
        initial_state=x0,
        target_state=xf,
        n_steps=n_steps,
        dt=dt,
        control_bounds=(u_min, u_max),
    )

    # Optimize
    result = optimizer.optimize(verbose=True)

    # Plot results
    optimizer.plot_results()

    return optimizer, result


# ============================================================================
# Example: Pendulum Swing-Up
# ============================================================================


def pendulum_dynamics(t, x, u):
    """
    Pendulum dynamics.
    x = [theta, theta_dot]
    u = [torque]

    theta = 0 is hanging down, theta = pi is upright
    """
    g = 9.81
    L = 1.0
    m = 1.0
    b = 0.1  # damping

    theta, theta_dot = x
    torque = u[0]

    theta_ddot = (torque - m * g * L * np.sin(theta) - b * theta_dot) / (m * L**2)

    return np.array([theta_dot, theta_ddot])


def example_pendulum_swingup():
    """Example: Swing pendulum from hanging to upright."""
    print("=" * 60)
    print("Single Shooting Example: Pendulum Swing-Up")
    print("=" * 60)

    # Problem setup
    x0 = np.array([0.0, 0.0])  # Hanging down at rest
    xf = np.array([np.pi, 0.0])  # Upright at rest

    n_steps = 80
    dt = 0.05

    u_min = np.array([-5.0])  # Torque limits
    u_max = np.array([5.0])

    # Create optimizer
    optimizer = SingleShootingOptimizer(
        dynamics=pendulum_dynamics,
        initial_state=x0,
        target_state=xf,
        n_steps=n_steps,
        dt=dt,
        control_bounds=(u_min, u_max),
    )

    # Initial guess: bang-bang control
    u_guess = np.zeros((n_steps, 1))
    u_guess[: n_steps // 2] = u_max
    u_guess[n_steps // 2 :] = u_min

    # Optimize
    result = optimizer.optimize(initial_guess=u_guess, verbose=True)

    # Plot results
    optimizer.plot_results()

    return optimizer, result


if __name__ == "__main__":
    # Run examples
    print("\n\n")
    opt1, res1 = example_double_integrator()

    print("\n\n")
    opt2, res2 = example_pendulum_swingup()

    print("\n" + "=" * 60)
    print("Comparison: Single Shooting vs Collocation")
    print("=" * 60)
    print("Single Shooting:")
    print("  + Simpler implementation")
    print("  + Fewer optimization variables (only controls)")
    print("  + Dynamics automatically satisfied")
    print("  - Less robust for unstable/nonlinear systems")
    print("  - Sensitive to initial guess")
    print("  - Can have numerical integration issues")
    print()
    print("Collocation (Direct Transcription):")
    print("  + More robust for complex dynamics")
    print("  + Better convergence from poor initial guesses")
    print("  + Can handle path constraints easily")
    print("  - More variables (states + controls)")
    print("  - Requires constraint handling")
    print("  - More complex implementation")

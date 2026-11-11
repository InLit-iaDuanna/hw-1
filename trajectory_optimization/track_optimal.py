"""
Trajectory Tracking Controller with PD Control
===============================================
Tracks optimized trajectory and compares performance vs free optimization.

Features:
- PD controller for trajectory tracking
- Multiple trajectory types (sinusoidal, polynomial, minimum jerk)
- Performance metrics (tracking error, control effort, energy)
- Comparative analysis with baseline (no tracking)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from dataclasses import dataclass
from typing import Tuple, Dict, Callable
import json


@dataclass
class SystemParams:
    """Physical parameters of the system."""

    m: float = 1.0  # Mass (kg)
    l: float = 1.0  # Length (m)
    g: float = 9.81  # Gravity (m/s^2)
    b: float = 0.1  # Damping coefficient
    I: float = None  # Moment of inertia (computed if None)

    def __post_init__(self):
        if self.I is None:
            self.I = self.m * self.l**2 / 3  # Uniform rod


@dataclass
class PDGains:
    """PD controller gains."""

    kp: float = 100.0  # Proportional gain
    kd: float = 20.0  # Derivative gain


class TrajectoryGenerator:
    """Generate reference trajectories."""

    @staticmethod
    def sinusoidal(
        t: np.ndarray,
        amplitude: float = 0.5,
        frequency: float = 1.0,
        offset: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate sinusoidal trajectory."""
        omega = 2 * np.pi * frequency
        q_ref = amplitude * np.sin(omega * t) + offset
        dq_ref = amplitude * omega * np.cos(omega * t)
        return q_ref, dq_ref

    @staticmethod
    def polynomial(
        t: np.ndarray, t_final: float, q0: float = 0.0, qf: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate smooth polynomial trajectory (5th order)."""
        s = t / t_final
        s = np.clip(s, 0, 1)

        # 5th order polynomial: ensures zero velocity/acceleration at endpoints
        h = 10 * s**3 - 15 * s**4 + 6 * s**5
        dh = (30 * s**2 - 60 * s**3 + 30 * s**4) / t_final

        q_ref = q0 + (qf - q0) * h
        dq_ref = (qf - q0) * dh
        return q_ref, dq_ref

    @staticmethod
    def minimum_jerk(
        t: np.ndarray, t_final: float, q0: float = 0.0, qf: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate minimum jerk trajectory."""
        tau = t / t_final
        tau = np.clip(tau, 0, 1)

        # Minimum jerk trajectory
        q_ref = q0 + (qf - q0) * (10 * tau**3 - 15 * tau**4 + 6 * tau**5)
        dq_ref = (qf - q0) * (30 * tau**2 - 60 * tau**3 + 30 * tau**4) / t_final
        return q_ref, dq_ref

    @staticmethod
    def step_response(
        t: np.ndarray, t_step: float = 1.0, q0: float = 0.0, qf: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate step input trajectory."""
        q_ref = np.where(t < t_step, q0, qf)
        dq_ref = np.zeros_like(t)
        return q_ref, dq_ref


class PDTrackingController:
    """PD controller for trajectory tracking."""

    def __init__(self, params: SystemParams, gains: PDGains):
        self.params = params
        self.gains = gains

    def compute_control(
        self, q: float, dq: float, q_ref: float, dq_ref: float
    ) -> float:
        """Compute PD control torque."""
        e = q_ref - q
        de = dq_ref - dq
        u = self.gains.kp * e + self.gains.kd * de
        return u

    def dynamics(
        self, t: float, state: np.ndarray, q_ref_func: Callable, dq_ref_func: Callable
    ) -> np.ndarray:
        """System dynamics with PD control."""
        q, dq = state

        # Reference trajectory at current time
        q_ref = q_ref_func(t)
        dq_ref = dq_ref_func(t)

        # PD control
        u = self.compute_control(q, dq, q_ref, dq_ref)

        # Pendulum dynamics: I*ddq + b*dq + m*g*l*sin(q) = u
        ddq = (
            u
            - self.params.b * dq
            - self.params.m * self.params.g * self.params.l * np.sin(q)
        ) / self.params.I

        return np.array([dq, ddq])


class FreeOptimizationController:
    """Baseline controller without tracking (free optimization)."""

    def __init__(self, params: SystemParams, control_type: str = "zero"):
        self.params = params
        self.control_type = control_type

    def compute_control(self, t: float, q: float, dq: float) -> float:
        """Compute control torque."""
        if self.control_type == "zero":
            return 0.0
        elif self.control_type == "gravity_compensation":
            return self.params.m * self.params.g * self.params.l * np.sin(q)
        elif self.control_type == "damping":
            return -5.0 * dq
        else:
            return 0.0

    def dynamics(self, t: float, state: np.ndarray) -> np.ndarray:
        """System dynamics with baseline control."""
        q, dq = state

        u = self.compute_control(t, q, dq)

        ddq = (
            u
            - self.params.b * dq
            - self.params.m * self.params.g * self.params.l * np.sin(q)
        ) / self.params.I

        return np.array([dq, ddq])


class PerformanceMetrics:
    """Compute and analyze tracking performance."""

    @staticmethod
    def tracking_error(q: np.ndarray, q_ref: np.ndarray) -> Dict[str, float]:
        """Compute tracking error metrics."""
        error = q - q_ref
        return {
            "mae": np.mean(np.abs(error)),
            "rmse": np.sqrt(np.mean(error**2)),
            "max_error": np.max(np.abs(error)),
            "std_error": np.std(error),
        }

    @staticmethod
    def control_effort(u: np.ndarray, dt: float) -> Dict[str, float]:
        """Compute control effort metrics."""
        return {
            "total_effort": np.sum(np.abs(u)) * dt,
            "rms_effort": np.sqrt(np.mean(u**2)),
            "peak_effort": np.max(np.abs(u)),
            "effort_variance": np.var(u),
        }

    @staticmethod
    def energy_consumption(
        u: np.ndarray, dq: np.ndarray, dt: float
    ) -> Dict[str, float]:
        """Compute energy consumption metrics."""
        power = u * dq
        energy = np.sum(np.abs(power)) * dt
        return {
            "total_energy": energy,
            "avg_power": np.mean(np.abs(power)),
            "peak_power": np.max(np.abs(power)),
        }

    @staticmethod
    def settling_metrics(
        t: np.ndarray, error: np.ndarray, threshold: float = 0.05
    ) -> Dict[str, float]:
        """Compute settling time and overshoot."""
        abs_error = np.abs(error)

        # Settling time (last time error exceeds threshold)
        settling_idx = np.where(abs_error > threshold)[0]
        settling_time = t[settling_idx[-1]] if len(settling_idx) > 0 else t[0]

        # Overshoot
        overshoot = np.max(error) if len(error) > 0 else 0.0

        return {
            "settling_time": settling_time,
            "overshoot": overshoot,
            "undershoot": np.min(error),
        }


def simulate_tracking(
    params: SystemParams,
    gains: PDGains,
    trajectory_type: str,
    t_span: Tuple[float, float],
    initial_state: np.ndarray,
    **traj_kwargs,
) -> Dict:
    """Simulate trajectory tracking with PD control."""

    # Generate reference trajectory
    t_eval = np.linspace(t_span[0], t_span[1], 1000)

    traj_gen = TrajectoryGenerator()
    if trajectory_type == "sinusoidal":
        q_ref, dq_ref = traj_gen.sinusoidal(t_eval, **traj_kwargs)
    elif trajectory_type == "polynomial":
        q_ref, dq_ref = traj_gen.polynomial(t_eval, t_span[1], **traj_kwargs)
    elif trajectory_type == "minimum_jerk":
        q_ref, dq_ref = traj_gen.minimum_jerk(t_eval, t_span[1], **traj_kwargs)
    elif trajectory_type == "step":
        q_ref, dq_ref = traj_gen.step_response(t_eval, **traj_kwargs)
    else:
        raise ValueError(f"Unknown trajectory type: {trajectory_type}")

    # Create interpolation functions
    q_ref_func = interp1d(t_eval, q_ref, kind="cubic", fill_value="extrapolate")
    dq_ref_func = interp1d(t_eval, dq_ref, kind="cubic", fill_value="extrapolate")

    # Simulate with PD control
    controller = PDTrackingController(params, gains)

    def dynamics_wrapper(t, state):
        return controller.dynamics(t, state, q_ref_func, dq_ref_func)

    sol = solve_ivp(
        dynamics_wrapper,
        t_span,
        initial_state,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-6,
        atol=1e-8,
    )

    # Compute control inputs
    u = np.array(
        [
            controller.compute_control(sol.y[0, i], sol.y[1, i], q_ref[i], dq_ref[i])
            for i in range(len(t_eval))
        ]
    )

    return {
        "t": sol.t,
        "q": sol.y[0],
        "dq": sol.y[1],
        "q_ref": q_ref,
        "dq_ref": dq_ref,
        "u": u,
        "success": sol.success,
    }


def simulate_free_optimization(
    params: SystemParams,
    control_type: str,
    t_span: Tuple[float, float],
    initial_state: np.ndarray,
) -> Dict:
    """Simulate free optimization (no trajectory tracking)."""

    t_eval = np.linspace(t_span[0], t_span[1], 1000)

    controller = FreeOptimizationController(params, control_type)

    sol = solve_ivp(
        lambda t, state: controller.dynamics(t, state),
        t_span,
        initial_state,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-6,
        atol=1e-8,
    )

    # Compute control inputs
    u = np.array(
        [
            controller.compute_control(sol.t[i], sol.y[0, i], sol.y[1, i])
            for i in range(len(t_eval))
        ]
    )

    return {"t": sol.t, "q": sol.y[0], "dq": sol.y[1], "u": u, "success": sol.success}


def compare_performance(tracking_result: Dict, free_result: Dict) -> Dict:
    """Compare tracking vs free optimization performance."""

    dt = tracking_result["t"][1] - tracking_result["t"][0]

    # Tracking metrics
    tracking_metrics = PerformanceMetrics.tracking_error(
        tracking_result["q"], tracking_result["q_ref"]
    )

    tracking_control = PerformanceMetrics.control_effort(tracking_result["u"], dt)

    tracking_energy = PerformanceMetrics.energy_consumption(
        tracking_result["u"], tracking_result["dq"], dt
    )

    error = tracking_result["q"] - tracking_result["q_ref"]
    tracking_settling = PerformanceMetrics.settling_metrics(tracking_result["t"], error)

    # Free optimization metrics
    free_control = PerformanceMetrics.control_effort(free_result["u"], dt)
    free_energy = PerformanceMetrics.energy_consumption(
        free_result["u"], free_result["dq"], dt
    )

    return {
        "tracking": {
            "error": tracking_metrics,
            "control": tracking_control,
            "energy": tracking_energy,
            "settling": tracking_settling,
        },
        "free_optimization": {
            "control": free_control,
            "energy": free_energy,
            "final_state": [free_result["q"][-1], free_result["dq"][-1]],
        },
        "comparison": {
            "energy_ratio": tracking_energy["total_energy"]
            / max(free_energy["total_energy"], 1e-6),
            "effort_ratio": tracking_control["total_effort"]
            / max(free_control["total_effort"], 1e-6),
            "tracking_efficiency": 1.0 / (1.0 + tracking_metrics["rmse"]),
        },
    }


def plot_comparison(
    tracking_result: Dict, free_result: Dict, metrics: Dict, save_path: str = None
):
    """Plot tracking vs free optimization comparison."""

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))

    # Position tracking
    axes[0, 0].plot(
        tracking_result["t"],
        tracking_result["q_ref"],
        "k--",
        linewidth=2,
        label="Reference",
    )
    axes[0, 0].plot(
        tracking_result["t"],
        tracking_result["q"],
        "b-",
        linewidth=1.5,
        label="PD Tracking",
    )
    axes[0, 0].plot(
        free_result["t"],
        free_result["q"],
        "r:",
        linewidth=1.5,
        label="Free Optimization",
    )
    axes[0, 0].set_ylabel("Position (rad)")
    axes[0, 0].set_xlabel("Time (s)")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].set_title("Position Comparison")

    # Velocity
    axes[0, 1].plot(
        tracking_result["t"],
        tracking_result["dq_ref"],
        "k--",
        linewidth=2,
        label="Reference",
    )
    axes[0, 1].plot(
        tracking_result["t"],
        tracking_result["dq"],
        "b-",
        linewidth=1.5,
        label="PD Tracking",
    )
    axes[0, 1].plot(
        free_result["t"],
        free_result["dq"],
        "r:",
        linewidth=1.5,
        label="Free Optimization",
    )
    axes[0, 1].set_ylabel("Velocity (rad/s)")
    axes[0, 1].set_xlabel("Time (s)")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_title("Velocity Comparison")

    # Tracking error
    error = tracking_result["q"] - tracking_result["q_ref"]
    axes[1, 0].plot(tracking_result["t"], error, "b-", linewidth=1.5)
    axes[1, 0].axhline(0, color="k", linestyle="--", linewidth=1)
    axes[1, 0].fill_between(tracking_result["t"], error, alpha=0.3)
    axes[1, 0].set_ylabel("Tracking Error (rad)")
    axes[1, 0].set_xlabel("Time (s)")
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_title(
        f'Tracking Error (RMSE: {metrics["tracking"]["error"]["rmse"]:.4f})'
    )

    # Control effort
    axes[1, 1].plot(
        tracking_result["t"],
        tracking_result["u"],
        "b-",
        linewidth=1.5,
        label="PD Tracking",
    )
    axes[1, 1].plot(
        free_result["t"],
        free_result["u"],
        "r:",
        linewidth=1.5,
        label="Free Optimization",
    )
    axes[1, 1].set_ylabel("Control Torque (Nm)")
    axes[1, 1].set_xlabel("Time (s)")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].set_title("Control Effort Comparison")

    # Phase portrait
    axes[2, 0].plot(
        tracking_result["q_ref"],
        tracking_result["dq_ref"],
        "k--",
        linewidth=2,
        label="Reference",
    )
    axes[2, 0].plot(
        tracking_result["q"],
        tracking_result["dq"],
        "b-",
        linewidth=1.5,
        label="PD Tracking",
    )
    axes[2, 0].plot(
        free_result["q"],
        free_result["dq"],
        "r:",
        linewidth=1.5,
        label="Free Optimization",
    )
    axes[2, 0].set_xlabel("Position (rad)")
    axes[2, 0].set_ylabel("Velocity (rad/s)")
    axes[2, 0].legend()
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].set_title("Phase Portrait")

    # Metrics comparison bar chart
    metrics_labels = ["Energy\nRatio", "Effort\nRatio", "Tracking\nEfficiency"]
    metrics_values = [
        metrics["comparison"]["energy_ratio"],
        metrics["comparison"]["effort_ratio"],
        metrics["comparison"]["tracking_efficiency"],
    ]

    bars = axes[2, 1].bar(
        metrics_labels,
        metrics_values,
        color=["#ff7f0e", "#2ca02c", "#1f77b4"],
        alpha=0.7,
    )
    axes[2, 1].axhline(1.0, color="k", linestyle="--", linewidth=1, alpha=0.5)
    axes[2, 1].set_ylabel("Ratio / Score")
    axes[2, 1].set_title("Performance Metrics")
    axes[2, 1].grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for bar, value in zip(bars, metrics_values):
        height = bar.get_height()
        axes[2, 1].text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Plot saved to {save_path}")

    plt.show()


def main():
    """Main execution function."""

    # System parameters
    params = SystemParams(m=1.0, l=1.0, g=9.81, b=0.1)

    # PD gains (tuned for good tracking)
    gains = PDGains(kp=50.0, kd=15.0)

    # Simulation settings
    t_span = (0, 10)
    initial_state = np.array([0.2, 0.0])  # Start slightly off from equilibrium

    print("=" * 70)
    print("Trajectory Tracking vs Free Optimization Comparison")
    print("=" * 70)

    # Test different trajectory types
    trajectories = [
        ("sinusoidal", {"amplitude": 0.5, "frequency": 0.5, "offset": 0.0}),
        ("polynomial", {"q0": 0.2, "qf": 1.0}),
        ("minimum_jerk", {"q0": 0.2, "qf": 1.0}),
        ("step", {"t_step": 1.0, "q0": 0.2, "qf": 0.8}),
    ]

    for traj_type, traj_kwargs in trajectories:
        print(f"\n{'-'*70}")
        print(f"Trajectory Type: {traj_type.upper()}")
        print(f"Parameters: {traj_kwargs}")
        print(f"{'-'*70}")

        # Simulate tracking
        tracking_result = simulate_tracking(
            params, gains, traj_type, t_span, initial_state, **traj_kwargs
        )

        # Simulate free optimization
        free_result = simulate_free_optimization(params, "zero", t_span, initial_state)

        # Compare performance
        metrics = compare_performance(tracking_result, free_result)

        # Print results
        print("\nTracking Performance:")
        print(f"  MAE: {metrics['tracking']['error']['mae']:.4f} rad")
        print(f"  RMSE: {metrics['tracking']['error']['rmse']:.4f} rad")
        print(f"  Max Error: {metrics['tracking']['error']['max_error']:.4f} rad")
        print(
            f"  Settling Time: {metrics['tracking']['settling']['settling_time']:.2f} s"
        )
        print(f"  Total Energy: {metrics['tracking']['energy']['total_energy']:.2f} J")
        print(f"  RMS Effort: {metrics['tracking']['control']['rms_effort']:.2f} Nm")

        print("\nFree Optimization Performance:")
        print(
            f"  Total Energy: {metrics['free_optimization']['energy']['total_energy']:.2f} J"
        )
        print(
            f"  RMS Effort: {metrics['free_optimization']['control']['rms_effort']:.2f} Nm"
        )
        print(
            f"  Final State: q={metrics['free_optimization']['final_state'][0]:.4f}, "
            f"dq={metrics['free_optimization']['final_state'][1]:.4f}"
        )

        print("\nComparative Metrics:")
        print(
            f"  Energy Ratio (tracking/free): {metrics['comparison']['energy_ratio']:.2f}"
        )
        print(
            f"  Effort Ratio (tracking/free): {metrics['comparison']['effort_ratio']:.2f}"
        )
        print(
            f"  Tracking Efficiency: {metrics['comparison']['tracking_efficiency']:.4f}"
        )

        # Plot comparison
        save_path = f"D:\\Dunna\\Documents\\hw-1\\trajectory_optimization\\tracking_comparison_{traj_type}.png"
        plot_comparison(tracking_result, free_result, metrics, save_path)

    # Save metrics to JSON
    print(f"\n{'='*70}")
    print("Simulation complete. All results plotted and saved.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

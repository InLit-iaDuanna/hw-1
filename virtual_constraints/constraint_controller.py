"""
Virtual Constraint Based Controller for Bipedal Walking
Based on RABBIT/ATRIAS walking literature (Westervelt et al., Ames et al.)

Key concepts:
- Output functions: y = h(q) define coordination between joints
- Desired outputs: y_d(s) parameterized by phase variable s
- Phase variable: s = θ_stance (stance leg angle)
- Virtual constraints enforce: h(q) → h_d(s) via feedback linearization
"""

import numpy as np
from typing import Callable, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BezierParameters:
    """Bezier polynomial parameters for desired output trajectory"""

    coefficients: np.ndarray  # [a0, a1, a2, ..., aM]

    def __call__(self, s: float) -> float:
        """Evaluate Bezier polynomial at phase s ∈ [0, 1]"""
        M = len(self.coefficients) - 1
        return sum(self.coefficients[i] * s**i for i in range(M + 1))

    def derivative(self, s: float) -> float:
        """Evaluate derivative of Bezier polynomial"""
        M = len(self.coefficients) - 1
        if M == 0:
            return 0.0
        return sum(i * self.coefficients[i] * s ** (i - 1) for i in range(1, M + 1))


class VirtualConstraintController:
    """
    Virtual constraint controller for underactuated bipedal robots.

    Based on hybrid zero dynamics (HZD) framework:
    1. Define output functions y = h(q) that encode desired joint coordination
    2. Parameterize desired outputs y_d(s) using Bezier curves
    3. Use phase variable s (e.g., stance leg angle) to synchronize gait
    4. Apply PD control to drive outputs to zero: y - y_d(s) → 0
    """

    def __init__(
        self,
        output_functions: list[Callable],
        bezier_params: list[BezierParameters],
        phase_variable_fn: Callable,
        kp: np.ndarray,
        kd: np.ndarray,
        epsilon: float = 1e-6,
    ):
        """
        Args:
            output_functions: List of output functions h_i(q)
            bezier_params: List of Bezier parameters for y_d,i(s)
            phase_variable_fn: Function to compute phase variable s(q)
            kp: Proportional gains [n_outputs]
            kd: Derivative gains [n_outputs]
            epsilon: Small value for numerical Jacobian computation
        """
        self.h_funcs = output_functions
        self.y_d_params = bezier_params
        self.phase_fn = phase_variable_fn
        self.kp = np.array(kp)
        self.kd = np.array(kd)
        self.epsilon = epsilon

        self.n_outputs = len(output_functions)
        assert len(bezier_params) == self.n_outputs
        assert len(kp) == self.n_outputs
        assert len(kd) == self.n_outputs

    def compute_output(self, q: np.ndarray) -> np.ndarray:
        """
        Compute actual output y = h(q)

        Args:
            q: Joint positions [n_joints]

        Returns:
            y: Output vector [n_outputs]
        """
        return np.array([h(q) for h in self.h_funcs])

    def compute_desired_output(self, s: float) -> np.ndarray:
        """
        Compute desired output y_d(s) from Bezier parameterization

        Args:
            s: Phase variable ∈ [0, 1]

        Returns:
            y_d: Desired output vector [n_outputs]
        """
        s_clamped = np.clip(s, 0.0, 1.0)
        return np.array([bezier(s_clamped) for bezier in self.y_d_params])

    def compute_desired_output_derivative(self, s: float, s_dot: float) -> np.ndarray:
        """
        Compute desired output derivative: dy_d/dt = (dy_d/ds) * (ds/dt)

        Args:
            s: Phase variable
            s_dot: Time derivative of phase variable

        Returns:
            dy_d_dt: Derivative of desired output [n_outputs]
        """
        s_clamped = np.clip(s, 0.0, 1.0)
        dy_d_ds = np.array([bezier.derivative(s_clamped) for bezier in self.y_d_params])
        return dy_d_ds * s_dot

    def compute_output_jacobian(self, q: np.ndarray) -> np.ndarray:
        """
        Compute Jacobian of output: J = ∂h/∂q using finite differences

        Args:
            q: Joint positions [n_joints]

        Returns:
            J: Jacobian matrix [n_outputs × n_joints]
        """
        n_joints = len(q)
        J = np.zeros((self.n_outputs, n_joints))

        y_nominal = self.compute_output(q)

        for i in range(n_joints):
            q_perturbed = q.copy()
            q_perturbed[i] += self.epsilon
            y_perturbed = self.compute_output(q_perturbed)
            J[:, i] = (y_perturbed - y_nominal) / self.epsilon

        return J

    def compute_phase_jacobian(self, q: np.ndarray) -> np.ndarray:
        """
        Compute Jacobian of phase variable: ∂s/∂q

        Args:
            q: Joint positions [n_joints]

        Returns:
            ds_dq: Phase Jacobian [n_joints]
        """
        n_joints = len(q)
        ds_dq = np.zeros(n_joints)

        s_nominal = self.phase_fn(q)

        for i in range(n_joints):
            q_perturbed = q.copy()
            q_perturbed[i] += self.epsilon
            s_perturbed = self.phase_fn(q_perturbed)
            ds_dq[i] = (s_perturbed - s_nominal) / self.epsilon

        return ds_dq

    def compute_output_derivative(self, q: np.ndarray, dq: np.ndarray) -> np.ndarray:
        """
        Compute output time derivative: dy/dt = J * dq/dt

        Args:
            q: Joint positions [n_joints]
            dq: Joint velocities [n_joints]

        Returns:
            dy_dt: Output derivative [n_outputs]
        """
        J = self.compute_output_jacobian(q)
        return J @ dq

    def compute_phase_derivative(self, q: np.ndarray, dq: np.ndarray) -> float:
        """
        Compute phase time derivative: ds/dt = (∂s/∂q) * dq/dt

        Args:
            q: Joint positions [n_joints]
            dq: Joint velocities [n_joints]

        Returns:
            s_dot: Phase derivative
        """
        ds_dq = self.compute_phase_jacobian(q)
        return ds_dq @ dq

    def compute_control(self, q: np.ndarray, dq: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Compute virtual constraint control torques using PD control

        Control law:
            τ = Kp * (y_d - y) + Kd * (dy_d/dt - dy/dt)

        Args:
            q: Joint positions [n_joints]
            dq: Joint velocities [n_joints]

        Returns:
            tau: Control torques [n_joints]
            info: Dictionary with debugging information
        """
        # Compute phase variable and its derivative
        s = self.phase_fn(q)
        s_dot = self.compute_phase_derivative(q, dq)

        # Compute actual outputs
        y = self.compute_output(q)
        dy_dt = self.compute_output_derivative(q, dq)

        # Compute desired outputs
        y_d = self.compute_desired_output(s)
        dy_d_dt = self.compute_desired_output_derivative(s, s_dot)

        # PD control in output space
        output_error = y_d - y
        output_error_dot = dy_d_dt - dy_dt

        # Virtual control: μ = Kp*e + Kd*ė
        mu = self.kp * output_error + self.kd * output_error_dot

        # Map to joint torques via Jacobian transpose
        # (For fully actuated systems; underactuated requires input-output linearization)
        J = self.compute_output_jacobian(q)
        tau = J.T @ mu

        # Debugging information
        info = {
            "phase": s,
            "phase_dot": s_dot,
            "output": y,
            "desired_output": y_d,
            "output_error": output_error,
            "output_derivative": dy_dt,
            "desired_output_derivative": dy_d_dt,
            "virtual_control": mu,
            "jacobian": J,
        }

        return tau, info

    def compute_control_feedback_linearization(
        self,
        q: np.ndarray,
        dq: np.ndarray,
        M: np.ndarray,
        C: np.ndarray,
        G: np.ndarray,
        B: np.ndarray,
    ) -> Tuple[np.ndarray, dict]:
        """
        Compute control using input-output feedback linearization (for underactuated systems)

        Control law:
            u = (L_g L_f h)^{-1} * [-L_f^2 h + Kp*(y_d - y) + Kd*(dy_d/dt - dy/dt)]

        Where:
            L_f h = J * dq (Lie derivative along drift dynamics)
            L_g L_f h = J * M^{-1} * B (relative degree 2 assumption)

        Args:
            q: Joint positions [n_joints]
            dq: Joint velocities [n_joints]
            M: Mass matrix [n_joints × n_joints]
            C: Coriolis/centrifugal vector [n_joints]
            G: Gravity vector [n_joints]
            B: Input selection matrix [n_joints × n_actuators]

        Returns:
            u: Control inputs [n_actuators]
            info: Dictionary with debugging information
        """
        # Compute phase variable
        s = self.phase_fn(q)
        s_dot = self.compute_phase_derivative(q, dq)

        # Compute outputs and Jacobian
        y = self.compute_output(q)
        J = self.compute_output_jacobian(q)

        # Lie derivative: L_f h = J * dq
        L_f_h = J @ dq

        # Second Lie derivative: L_f^2 h = J * M^{-1} * (C + G)
        # (assuming passive dynamics: ddq = -M^{-1}*(C + G) when u=0)
        M_inv = np.linalg.inv(M)
        L_f2_h = -J @ M_inv @ (C + G)

        # Decoupling matrix: L_g L_f h = J * M^{-1} * B
        L_g_L_f_h = J @ M_inv @ B

        # Check if decoupling matrix is invertible
        if np.linalg.matrix_rank(L_g_L_f_h) < min(L_g_L_f_h.shape):
            raise ValueError(
                "Decoupling matrix is singular - outputs may not have relative degree 2"
            )

        # Desired outputs
        y_d = self.compute_desired_output(s)
        dy_d_dt = self.compute_desired_output_derivative(s, s_dot)

        # PD control law in output space
        output_error = y_d - y
        output_error_dot = dy_d_dt - L_f_h

        # Virtual control: v = -L_f^2 h + Kp*e + Kd*ė
        v = -L_f2_h + self.kp * output_error + self.kd * output_error_dot

        # Solve for actual control: u = (L_g L_f h)^{-1} * v
        u = np.linalg.lstsq(L_g_L_f_h, v, rcond=None)[0]

        # Debugging information
        info = {
            "phase": s,
            "phase_dot": s_dot,
            "output": y,
            "desired_output": y_d,
            "output_error": output_error,
            "L_f_h": L_f_h,
            "L_f2_h": L_f2_h,
            "L_g_L_f_h": L_g_L_f_h,
            "virtual_control": v,
            "jacobian": J,
        }

        return u, info


# Example output functions for bipedal walking
def hip_angle_output(q: np.ndarray) -> float:
    """Output: hip angle relative to stance leg"""
    # Assumes q = [stance_hip, stance_knee, swing_hip, swing_knee]
    return q[2] - q[0]  # swing_hip - stance_hip


def swing_knee_output(q: np.ndarray) -> float:
    """Output: swing knee angle"""
    # Assumes q = [stance_hip, stance_knee, swing_hip, swing_knee]
    return q[3]


def stance_knee_output(q: np.ndarray) -> float:
    """Output: stance knee angle"""
    # Assumes q = [stance_hip, stance_knee, swing_hip, swing_knee]
    return q[1]


def phase_variable_stance_angle(q: np.ndarray) -> float:
    """
    Phase variable: normalized stance leg angle
    Maps stance angle from initial to final value into [0, 1]
    """
    # Assumes q[0] is stance hip angle
    # Typical gait: θ_stance goes from -20° to +20° (normalized to [0, 1])
    theta_initial = -20.0 * np.pi / 180.0
    theta_final = 20.0 * np.pi / 180.0

    theta_stance = q[0]
    s = (theta_stance - theta_initial) / (theta_final - theta_initial)
    return s


# Example usage
if __name__ == "__main__":
    # Define Bezier parameters for desired outputs (5th order polynomial)
    # y_d(s) = a0 + a1*s + a2*s^2 + a3*s^3 + a4*s^4 + a5*s^5

    # Hip angle trajectory: smooth curve from 0 to π/4
    hip_bezier = BezierParameters(coefficients=np.array([0.0, 0.2, 0.3, 0.2, 0.1, 0.0]))

    # Swing knee: lift and extend
    swing_knee_bezier = BezierParameters(
        coefficients=np.array([0.0, 1.5, -2.0, 1.2, -0.5, 0.0])
    )

    # Stance knee: slight compliance
    stance_knee_bezier = BezierParameters(
        coefficients=np.array([0.1, -0.2, 0.3, -0.2, 0.1, 0.0])
    )

    # Create controller
    controller = VirtualConstraintController(
        output_functions=[hip_angle_output, swing_knee_output, stance_knee_output],
        bezier_params=[hip_bezier, swing_knee_bezier, stance_knee_bezier],
        phase_variable_fn=phase_variable_stance_angle,
        kp=np.array([100.0, 80.0, 60.0]),
        kd=np.array([10.0, 8.0, 6.0]),
    )

    # Test with sample configuration
    q_test = np.array(
        [0.0, 0.1, 0.3, 0.5]
    )  # [stance_hip, stance_knee, swing_hip, swing_knee]
    dq_test = np.array([0.5, 0.2, 0.8, -0.3])

    # Compute control (simple Jacobian transpose method)
    tau, info = controller.compute_control(q_test, dq_test)

    print("Virtual Constraint Controller Test")
    print("=" * 50)
    print(f"Phase variable s: {info['phase']:.3f}")
    print(f"Phase derivative ṡ: {info['phase_dot']:.3f}")
    print(f"\nActual outputs y: {info['output']}")
    print(f"Desired outputs y_d: {info['desired_output']}")
    print(f"Output error: {info['output_error']}")
    print(f"\nControl torques τ: {tau}")
    print(f"Virtual control μ: {info['virtual_control']}")

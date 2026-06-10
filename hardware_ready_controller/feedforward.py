"""
Feedforward Compensation Module

Provides friction and gravity compensation for motor control.
Based on V13.7 successful implementation and V16 motor parameters.

Motor Parameters (MX-64AR):
- τ_C_eff: 0.20 Nm (effective Coulomb friction)
- J: 2.8e-3 kg·m² (rotor inertia)
- b: 0.05 Nm·s/rad (viscous damping)
"""

import numpy as np
from typing import Optional, Dict


def sign_smooth(value: float, epsilon: float = 0.01) -> float:
    """
    Smooth sign function to avoid discontinuity at zero.

    Uses tanh approximation for smooth transition:
    sign_smooth(x, ε) = tanh(x/ε)

    Args:
        value: Input value (typically angular velocity ω)
        epsilon: Smoothing parameter (smaller = sharper transition)
                Default 0.01 rad/s based on V13.7 testing

    Returns:
        Smooth sign value in range [-1, 1]
    """
    return np.tanh(value / epsilon)


class FrictionCompensator:
    """
    Feedforward friction compensation for robot joints.

    Implements Coulomb friction model:
        τ_comp = τ_C_eff * sign_smooth(ω, ε)

    Verified against V13.7 successful implementation.
    """

    # Default motor parameters (MX-64AR from V16)
    DEFAULT_PARAMS = {
        'tau_c_eff': 0.20,      # Nm - effective Coulomb friction
        'J': 2.8e-3,            # kg·m² - rotor inertia
        'b': 0.05,              # Nm·s/rad - viscous damping
        'epsilon': 0.01         # rad/s - sign smoothing parameter
    }

    def __init__(
        self,
        joint_names: list[str],
        tau_c_values: Optional[Dict[str, float]] = None,
        epsilon: float = 0.01,
        enable_gravity_comp: bool = False
    ):
        """
        Initialize friction compensator.

        Args:
            joint_names: List of joint names (e.g., ['hip', 'knee', 'ankle'])
            tau_c_values: Per-joint τ_C_eff values {joint_name: tau_c}
                         If None, uses DEFAULT_PARAMS['tau_c_eff'] for all
            epsilon: Smoothing parameter for sign function (default 0.01)
            enable_gravity_comp: Enable gravity compensation (default False)
        """
        self.joint_names = joint_names
        self.epsilon = epsilon
        self.enable_gravity_comp = enable_gravity_comp

        # Set per-joint friction parameters
        if tau_c_values is None:
            self.tau_c = {
                name: self.DEFAULT_PARAMS['tau_c_eff']
                for name in joint_names
            }
        else:
            self.tau_c = tau_c_values.copy()
            # Fill missing joints with default
            for name in joint_names:
                if name not in self.tau_c:
                    self.tau_c[name] = self.DEFAULT_PARAMS['tau_c_eff']

        # Store other motor parameters (may be used for future extensions)
        self.J = self.DEFAULT_PARAMS['J']
        self.b = self.DEFAULT_PARAMS['b']

    def compute_friction_compensation(
        self,
        joint_velocities: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute Coulomb friction compensation torques.

        Args:
            joint_velocities: Angular velocities {joint_name: ω} in rad/s

        Returns:
            Compensation torques {joint_name: τ_comp} in Nm
        """
        tau_comp = {}

        for joint_name in self.joint_names:
            omega = joint_velocities.get(joint_name, 0.0)
            tau_c = self.tau_c[joint_name]

            # Coulomb friction compensation with smooth sign
            tau_comp[joint_name] = tau_c * sign_smooth(omega, self.epsilon)

        return tau_comp

    def compute_gravity_compensation(
        self,
        joint_positions: Dict[str, float],
        mass: float = 1.0,
        link_lengths: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Compute gravity compensation torques (optional feature).

        Simple 2D sagittal plane gravity model:
            τ_g = m * g * L * cos(θ)

        Args:
            joint_positions: Joint angles {joint_name: θ} in rad
            mass: Link mass in kg (default 1.0)
            link_lengths: Link lengths {joint_name: L} in m
                         If None, returns zero compensation

        Returns:
            Gravity compensation torques {joint_name: τ_g} in Nm
        """
        if not self.enable_gravity_comp or link_lengths is None:
            return {name: 0.0 for name in self.joint_names}

        g = 9.81  # m/s²
        tau_g = {}

        for joint_name in self.joint_names:
            theta = joint_positions.get(joint_name, 0.0)
            L = link_lengths.get(joint_name, 0.0)

            # Simple gravity model (assumes link COM at L/2)
            tau_g[joint_name] = mass * g * (L / 2) * np.cos(theta)

        return tau_g

    def compute_total_compensation(
        self,
        joint_velocities: Dict[str, float],
        joint_positions: Optional[Dict[str, float]] = None,
        mass: Optional[float] = None,
        link_lengths: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Compute total feedforward compensation (friction + gravity).

        Args:
            joint_velocities: Angular velocities {joint_name: ω} in rad/s
            joint_positions: Joint angles {joint_name: θ} in rad (for gravity)
            mass: Link mass in kg (for gravity)
            link_lengths: Link lengths {joint_name: L} in m (for gravity)

        Returns:
            Total compensation torques {joint_name: τ_total} in Nm
        """
        # Friction compensation (always computed)
        tau_friction = self.compute_friction_compensation(joint_velocities)

        # Gravity compensation (if enabled and parameters provided)
        if self.enable_gravity_comp and joint_positions is not None:
            tau_gravity = self.compute_gravity_compensation(
                joint_positions,
                mass or 1.0,
                link_lengths
            )
        else:
            tau_gravity = {name: 0.0 for name in self.joint_names}

        # Sum compensations
        tau_total = {
            name: tau_friction[name] + tau_gravity[name]
            for name in self.joint_names
        }

        return tau_total

    def set_tau_c(self, joint_name: str, tau_c: float) -> None:
        """
        Update τ_C_eff for a specific joint.

        Args:
            joint_name: Name of joint to update
            tau_c: New τ_C_eff value in Nm
        """
        if joint_name in self.joint_names:
            self.tau_c[joint_name] = tau_c
        else:
            raise ValueError(f"Unknown joint: {joint_name}")

    def get_params(self) -> Dict:
        """
        Get current compensator parameters.

        Returns:
            Dictionary of all parameters
        """
        return {
            'joint_names': self.joint_names,
            'tau_c': self.tau_c.copy(),
            'epsilon': self.epsilon,
            'enable_gravity_comp': self.enable_gravity_comp,
            'J': self.J,
            'b': self.b
        }


# Example usage
if __name__ == '__main__':
    # Create compensator for 3-joint leg
    joints = ['hip', 'knee', 'ankle']

    # Option 1: Use default parameters for all joints
    compensator = FrictionCompensator(joints)

    # Option 2: Specify per-joint friction values
    custom_tau_c = {
        'hip': 0.25,    # Higher friction at hip
        'knee': 0.20,   # Default MX-64AR value
        'ankle': 0.15   # Lower friction at ankle
    }
    compensator_custom = FrictionCompensator(
        joints,
        tau_c_values=custom_tau_c,
        epsilon=0.01
    )

    # Test friction compensation
    velocities = {'hip': 1.5, 'knee': -0.8, 'ankle': 0.3}
    tau_comp = compensator_custom.compute_friction_compensation(velocities)

    print("Friction Compensation Test:")
    for joint, tau in tau_comp.items():
        print(f"  {joint}: ω={velocities[joint]:+.2f} rad/s → τ_comp={tau:+.3f} Nm")

    # Test with gravity compensation
    compensator_with_gravity = FrictionCompensator(
        joints,
        enable_gravity_comp=True
    )

    positions = {'hip': np.pi/6, 'knee': -np.pi/4, 'ankle': np.pi/12}
    link_lengths = {'hip': 0.4, 'knee': 0.4, 'ankle': 0.2}

    tau_total = compensator_with_gravity.compute_total_compensation(
        velocities,
        positions,
        mass=1.5,
        link_lengths=link_lengths
    )

    print("\nTotal Compensation (Friction + Gravity):")
    for joint, tau in tau_total.items():
        print(f"  {joint}: τ_total={tau:+.3f} Nm")

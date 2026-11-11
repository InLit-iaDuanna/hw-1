"""Example: V13.7 FSM controller with friction compensation.

Demonstrates the unified FSMController API with:
- 4-phase finite state machine (stance_early, stance_late, swing_thrust, swing_retract)
- Per-phase control gains (k_E, k_PD, tau_max, kd)
- Energy shaping during swing_thrust phase
- Friction compensation for motor dynamics
- Event-driven gait phase switching

This example shows how to:
1. Configure FSM parameters for a bipedal walker
2. Set up motor dynamics with friction compensation
3. Run a simulation loop with phase-based control
4. Track energy metrics and phase transitions

Based on V13.7 friction compensation implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np

# Add hw-1 common module to path
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from common.fsm_controller import BaseGaitParams, FSMController, FSMParams, PhaseParams
from common.motor_dynamics import (
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (
    L1MotorActuator,
    _sign_smooth,
)


def build_simple_walker_xml() -> str:
    """Build a minimal bipedal walker XML for demonstration.

    Returns:
        MuJoCo XML string for a planar bipedal walker.
    """
    return """
    <mujoco model="fsm_walker_demo">
        <compiler angle="degree" coordinate="local"/>
        <option timestep="0.0005" gravity="0 0 -9.81"/>

        <worldbody>
            <light pos="0 0 3" dir="0 0 -1"/>
            <geom name="floor" type="plane" size="10 10 0.1" rgba="0.8 0.8 0.8 1"/>

            <body name="hip" pos="0 0 0.6">
                <freejoint/>
                <geom type="sphere" size="0.05" rgba="0.2 0.2 0.8 1" mass="1.0"/>
                <geom name="torso" type="capsule" size="0.03" fromto="0 0 0 0 0 0.15"
                      rgba="0.3 0.3 0.9 1" mass="0.05"/>

                <!-- Left leg -->
                <body name="left_thigh" pos="0 0 0">
                    <joint name="left_hip" type="hinge" axis="0 1 0"
                           damping="0.5" armature="0.004"/>
                    <geom type="capsule" size="0.025" fromto="0 0 0 0 0 -0.25"
                          rgba="0.8 0.2 0.2 1" mass="0.2"/>

                    <body name="left_shank" pos="0 0 -0.25">
                        <joint name="left_knee" type="hinge" axis="0 1 0"
                               damping="0.5" armature="0.004"
                               limited="true" range="0 120"/>
                        <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -0.25"
                              rgba="0.6 0.2 0.2 1" mass="0.15"/>
                        <geom name="left_foot" type="sphere" pos="0 0 -0.25"
                              size="0.03" rgba="0.4 0.1 0.1 1" mass="0.05"/>
                    </body>
                </body>

                <!-- Right leg -->
                <body name="right_thigh" pos="0 0 0">
                    <joint name="right_hip" type="hinge" axis="0 1 0"
                           damping="0.5" armature="0.004"/>
                    <geom type="capsule" size="0.025" fromto="0 0 0 0 0 -0.25"
                          rgba="0.2 0.8 0.2 1" mass="0.2"/>

                    <body name="right_shank" pos="0 0 -0.25">
                        <joint name="right_knee" type="hinge" axis="0 1 0"
                               damping="0.5" armature="0.004"
                               limited="true" range="0 120"/>
                        <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -0.25"
                              rgba="0.2 0.6 0.2 1" mass="0.15"/>
                        <geom name="right_foot" type="sphere" pos="0 0 -0.25"
                              size="0.03" rgba="0.1 0.4 0.1 1" mass="0.05"/>
                    </body>
                </body>
            </body>
        </worldbody>

        <actuator>
            <motor name="left_hip_motor" joint="left_hip" gear="1"/>
            <motor name="left_knee_motor" joint="left_knee" gear="1"/>
            <motor name="right_hip_motor" joint="right_hip" gear="1"/>
            <motor name="right_knee_motor" joint="right_knee" gear="1"/>
        </actuator>
    </mujoco>
    """


def initialize_walker(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    """Initialize walker to standing pose.

    Args:
        model: MuJoCo model
        data: MuJoCo data
    """
    data.qpos[0] = 0.0  # x position
    data.qpos[1] = 0.6  # z position (hip height)
    data.qpos[2] = np.radians(10.0)  # left hip: forward
    data.qpos[3] = 0.0  # left knee: straight
    data.qpos[5] = np.radians(-10.0)  # right hip: back
    data.qpos[6] = 0.0  # right knee: straight
    mujoco.mj_forward(model, data)


def contact_flags(model: mujoco.MjModel, data: mujoco.MjData) -> tuple[bool, bool]:
    """Check which feet are in contact with ground.

    Args:
        model: MuJoCo model
        data: MuJoCo data

    Returns:
        (left_contact, right_contact) boolean tuple
    """
    left_contact = False
    right_contact = False

    for i in range(data.ncon):
        contact = data.contact[i]
        geom1_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom1)
        geom2_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom2)

        if "left_foot" in (geom1_name, geom2_name):
            left_contact = True
        if "right_foot" in (geom1_name, geom2_name):
            right_contact = True

    return left_contact, right_contact


def apply_friction_compensation(
    tau_fsm: float, omega_joint: float, motor_params
) -> float:
    """Apply feedforward friction compensation.

    Adds τ_C_eff·sign_smooth(ω) to cancel motor Coulomb friction.

    Args:
        tau_fsm: Torque command from FSM controller
        omega_joint: Joint angular velocity (rad/s)
        motor_params: Motor parameters with friction characteristics

    Returns:
        Compensated torque command
    """
    tau_C_eff = motor_params.joint_tau_C_eff()
    return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor_params.omega_eps)


def run_fsm_walker_demo(
    duration: float = 5.0,
    timestep: float = 0.0005,
    enable_friction_comp: bool = True,
    verbose: bool = True,
) -> dict:
    """Run FSM walker demonstration with friction compensation.

    Args:
        duration: Simulation duration (seconds)
        timestep: Integration timestep (seconds)
        enable_friction_comp: Enable feedforward friction compensation
        verbose: Print simulation progress

    Returns:
        Dictionary with simulation results and metrics
    """
    # Build model
    xml = build_simple_walker_xml()
    model = mujoco.MjModel.from_xml_string(xml)
    model.opt.timestep = timestep
    data = mujoco.MjData(model)
    initialize_walker(model, data)

    # Configure FSM parameters
    fsm_params = FSMParams(
        stance_early=PhaseParams(
            k_E=0.0,  # PD-only during early stance
            k_PD=30.0,  # Strong position tracking
            tau_max=4.0,
            kd=6.0,
        ),
        stance_late=PhaseParams(
            k_E=0.0,  # PD-only during late stance
            k_PD=30.0,
            tau_max=4.0,
            kd=6.0,
        ),
        swing_thrust=PhaseParams(
            k_E=7.5,  # Energy shaping active
            k_PD=10.0,  # Reduced PD gain
            tau_max=4.0,
            kd=6.0,
            E_target=52.66,  # Target mechanical energy (J)
        ),
        swing_retract=PhaseParams(
            k_E=0.0,  # PD-only during retraction
            k_PD=30.0,
            tau_max=2.0,  # Reduced torque limit
            kd=6.0,
        ),
    )

    # Configure base gait parameters
    base_params = BaseGaitParams(
        gait_period=0.80,
        gamma=0.0,
        stance_front_deg=15.0,
        stance_back_deg=-15.0,
        swing_back_deg=-20.0,
        swing_front_deg=25.0,
        recovery_clearance=0.38,
        slope_deg=0.0,
        hip_mass=1.0,
        torso_mass=0.05,
    )

    # Create FSM controller
    fsm = FSMController(
        fsm_params=fsm_params,
        base_params=base_params,
        knee_kp=16.0,
        knee_kd=2.0,
        knee_torque_limit=4.0,
        swing_knee_flex_deg=30.0,
        stance_knee_deg=0.0,
    )

    # Motor dynamics (MX-64AR with friction)
    motor = MOTOR_PRESETS["mx64ar"]
    actuators = {
        "left_hip": L1MotorActuator(motor),
        "left_knee": L1MotorActuator(motor),
        "right_hip": L1MotorActuator(motor),
        "right_knee": L1MotorActuator(motor),
    }

    # Joint velocity addresses in qvel
    qvel_addr = {"left_hip": 2, "left_knee": 3, "right_hip": 5, "right_knee": 6}

    # Simulation state
    support_foot = "left"
    burst_start_t = -base_params.gait_period
    last_event_t = -1.0
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    stable_contact_time = 0.02
    min_event_interval = 0.15

    # Metrics
    contact_events = []
    phase_transitions = []
    total_energy_input = 0.0
    coulomb_dissipation = 0.0
    last_phase = ("", "")

    if verbose:
        print("=" * 60)
        print("FSM Walker Demo with V13.7 Friction Compensation")
        print("=" * 60)
        print(f"Duration: {duration}s, Timestep: {timestep}s")
        print(
            f"Friction compensation: {'ENABLED' if enable_friction_comp else 'DISABLED'}"
        )
        print(f"Motor: {motor.name}")
        print(f"  - Coulomb friction: {motor.tau_C_motor:.4f} Nm")
        print(f"  - Joint-side effective: {motor.joint_tau_C_eff():.4f} Nm")
        print("-" * 60)

    # Main simulation loop
    n_steps = int(duration / timestep)
    for step in range(n_steps):
        t = step * timestep

        # Compute FSM control
        E_current = fsm.mechanical_energy(data)
        (
            l_hip_tau,
            l_knee_tau,
            r_hip_tau,
            r_knee_tau,
            mode_label,
            left_phase,
            right_phase,
            e_E_swing,
            A_swing,
        ) = fsm.compute_control(data, t, support_foot, burst_start_t, E_current)

        # Apply friction compensation if enabled
        if enable_friction_comp:
            l_hip_tau = apply_friction_compensation(
                l_hip_tau, float(data.qvel[qvel_addr["left_hip"]]), motor
            )
            l_knee_tau = apply_friction_compensation(
                l_knee_tau, float(data.qvel[qvel_addr["left_knee"]]), motor
            )
            r_hip_tau = apply_friction_compensation(
                r_hip_tau, float(data.qvel[qvel_addr["right_hip"]]), motor
            )
            r_knee_tau = apply_friction_compensation(
                r_knee_tau, float(data.qvel[qvel_addr["right_knee"]]), motor
            )

        # Apply motor dynamics (saturation + friction)
        tau_commands = [l_hip_tau, l_knee_tau, r_hip_tau, r_knee_tau]
        actuator_keys = ["left_hip", "left_knee", "right_hip", "right_knee"]
        tau_actual = []

        for key, tau_cmd in zip(actuator_keys, tau_commands):
            omega = float(data.qvel[qvel_addr[key]])
            tau_out, _ = actuators[key].compute_actual_torque(tau_cmd, omega)
            tau_actual.append(tau_out)

        data.ctrl[:] = tau_actual

        # Energy accounting
        for i, key in enumerate(actuator_keys):
            omega = float(data.qvel[qvel_addr[key]])
            power = tau_actual[i] * omega
            if power > 0:
                total_energy_input += power * timestep

            # Coulomb dissipation
            tau_C_eff = actuators[key]._tau_C_eff
            coulomb_dissipation += tau_C_eff * abs(omega) * timestep

        # Track phase transitions
        current_phase = (left_phase, right_phase)
        if current_phase != last_phase:
            phase_transitions.append((t, left_phase, right_phase))
            last_phase = current_phase

        # Step simulation
        mujoco.mj_step(model, data)

        # Contact detection and event-driven switching
        left_contact, right_contact = contact_flags(model, data)
        contacts = {"left": left_contact, "right": right_contact}

        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False

                # Stable contact threshold
                if t - candidate_start_t[foot] >= stable_contact_time:
                    if (
                        not contact_reported[foot]
                        and foot != support_foot
                        and t - last_event_t > min_event_interval
                    ):
                        # Contact event: switch support foot
                        old_support = support_foot
                        support_foot = foot
                        burst_start_t = t
                        last_event_t = t
                        contact_reported[foot] = True

                        contact_events.append(
                            {
                                "time": t,
                                "foot": foot,
                                "from": old_support,
                                "energy": E_current,
                            }
                        )

                        if verbose and len(contact_events) <= 10:
                            print(
                                f"t={t:.3f}s: Contact {foot} -> support={support_foot}, E={E_current:.2f}J"
                            )
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        # Progress indicator
        if verbose and step % 10000 == 0:
            progress = 100 * step / n_steps
            print(
                f"Progress: {progress:.1f}% | t={t:.2f}s | E={E_current:.2f}J | x={data.qpos[0]:.2f}m"
            )

    # Final results
    final_x = float(data.qpos[0])
    final_energy = fsm.mechanical_energy(data)
    avg_velocity = final_x / duration

    results = {
        "duration": duration,
        "timestep": timestep,
        "friction_comp_enabled": enable_friction_comp,
        "final_position": final_x,
        "final_energy": final_energy,
        "avg_velocity": avg_velocity,
        "contact_events": len(contact_events),
        "total_energy_input": total_energy_input,
        "coulomb_dissipation": coulomb_dissipation,
        "phase_transitions": len(phase_transitions),
        "motor": motor.name,
    }

    if verbose:
        print("-" * 60)
        print("Simulation Results:")
        print(f"  Final position: {final_x:.3f} m")
        print(f"  Average velocity: {avg_velocity:.3f} m/s")
        print(f"  Contact events: {len(contact_events)}")
        print(f"  Phase transitions: {len(phase_transitions)}")
        print(f"  Total energy input: {total_energy_input:.2f} J")
        print(f"  Coulomb dissipation: {coulomb_dissipation:.2f} J")
        print(f"  Final energy: {final_energy:.2f} J")
        print("=" * 60)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Demonstrate V13.7 FSM controller with friction compensation"
    )
    parser.add_argument(
        "--duration", type=float, default=5.0, help="Simulation duration (s)"
    )
    parser.add_argument(
        "--no-friction-comp",
        action="store_true",
        help="Disable friction compensation",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    results = run_fsm_walker_demo(
        duration=args.duration,
        enable_friction_comp=not args.no_friction_comp,
        verbose=not args.quiet,
    )

    print("\nDemo complete. Results summary:")
    for key, value in results.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

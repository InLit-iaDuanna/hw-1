"""Integration example: Using SEAActuator with V15.1 simulation.

This example demonstrates how to use the SEAActuator class to:
1. Configure SEA parameters
2. Track energy flow during simulation
3. Generate energy audit reports
4. Compare different stiffness configurations

Based on V15.1 series elastic actuator experiments.
"""

import math
import sys
from pathlib import Path

# Add paths
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "common"))

from sea_actuator import SEAActuator, SEAParams, PRESETS


def example_basic_usage():
    """Basic usage: single SEA actuator tracking."""
    print("=" * 70)
    print("Example 1: Basic SEA Actuator Usage")
    print("=" * 70)

    # Create SEA with soft spring (k=500, optimal for V15.1)
    sea_params = PRESETS["v151_soft"]
    left_hip_sea = SEAActuator("left_hip", sea_params)

    # Initialize before simulation
    left_hip_sea.initialize(q_link_initial=0.0)

    print(f"\nSEA Configuration:")
    print(f"  k_sea: {sea_params.k_sea} N·m/rad")
    print(f"  c_sea: {sea_params.damping_resolved():.4f} N·m·s/rad")
    print(f"  Natural frequency: {sea_params.spring_natural_frequency():.1f} rad/s")
    print(f"  Damping ratio: {sea_params.damping_ratio():.3f}")

    # Simulate 100 time steps
    dt = 0.001
    for i in range(100):
        t = i * dt

        # Example: FSM provides desired torque
        tau_motor_desired = 3.0 * math.sin(2 * math.pi * 2.0 * t)

        # In real V15.1: motor applies this directly (no inner loop)
        tau_motor_actual = tau_motor_desired

        # Motor velocity (from MuJoCo data.qvel)
        qd_motor = 1.5 * math.cos(2 * math.pi * 2.0 * t)

        # Spring deflection (from MuJoCo: q_link = q_motor - q_thigh)
        q_link = 0.03 * math.sin(2 * math.pi * 2.0 * t + 0.2)
        qd_link = 0.03 * 2 * math.pi * 2.0 * math.cos(2 * math.pi * 2.0 * t + 0.2)

        # Update energy tracking
        left_hip_sea.update_energy(tau_motor_actual, qd_motor, q_link, qd_link, dt)

    # Finalize and get report
    q_link_final = 0.0
    audit = left_hip_sea.finalize_energy_audit(q_link_final)

    print(f"\nEnergy Audit Report:")
    print(f"  Motor input work: {audit['W_motor_input_J']:.4f} J")
    print(f"  Link useful work: {audit['W_link_useful_J']:.4f} J")
    print(f"  Damper loss: {audit['W_damper_loss_J']:.4f} J")
    print(f"  Spring PE change: {audit['dPE_spring_J']:.4f} J")
    print(f"  Max deflection: {audit['q_link_max_deg']:.3f}°")
    print(f"  Energy balance error: {audit['energy_balance_error_pct']:.2f}%")


def example_stiffness_comparison():
    """Compare energy efficiency across different stiffness settings."""
    print("\n" + "=" * 70)
    print("Example 2: Stiffness Comparison")
    print("=" * 70)

    results = []

    for preset_name in ["v151_soft", "v151_medium", "v151_stiff", "v151_rigid"]:
        params = PRESETS[preset_name]
        sea = SEAActuator(preset_name, params)
        sea.initialize(q_link_initial=0.0)

        dt = 0.001
        # Simulate impact scenario
        for i in range(200):
            t = i * dt
            # Step torque input (impact)
            tau_motor = 4.0 if t < 0.05 else 1.0
            qd_motor = 2.0

            # Spring response depends on stiffness
            # Softer spring -> larger deflection
            deflection_scale = 1000.0 / params.k_sea
            q_link = (
                deflection_scale
                * 0.05
                * math.exp(-5 * t)
                * math.sin(params.spring_natural_frequency() * t)
            )
            qd_link = (
                deflection_scale
                * 0.05
                * (
                    -5
                    * math.exp(-5 * t)
                    * math.sin(params.spring_natural_frequency() * t)
                    + params.spring_natural_frequency()
                    * math.exp(-5 * t)
                    * math.cos(params.spring_natural_frequency() * t)
                )
            )

            sea.update_energy(tau_motor, qd_motor, q_link, qd_link, dt)

        audit = sea.finalize_energy_audit(q_link_final=0.0)
        results.append(
            {
                "name": preset_name,
                "k_sea": params.k_sea,
                "max_deflection_deg": audit["q_link_max_deg"],
                "damper_loss_J": audit["W_damper_loss_J"],
                "spring_pe_max_J": audit["spring_pe_max_J"],
            }
        )

    print(
        f"\n{'Preset':<15} {'k (N·m/rad)':<12} {'Max Deflection':<15} {'Damper Loss':<12} {'Max PE':<10}"
    )
    print("-" * 70)
    for r in results:
        print(
            f"{r['name']:<15} {r['k_sea']:<12.0f} "
            f"{r['max_deflection_deg']:<15.3f} "
            f"{r['damper_loss_J']:<12.4f} {r['spring_pe_max_J']:<10.4f}"
        )

    print("\nObservations:")
    print(
        "  - Softer springs (k=500) allow larger deflections → better impact absorption"
    )
    print(
        "  - Stiffer springs (k=10000) behave like rigid coupling → minimal compliance"
    )
    print(
        "  - V15.1 experiments showed k=500 achieved best performance (4.92m forward)"
    )


def example_v151_integration_pattern():
    """Show integration pattern with V15.1 simulation loop."""
    print("\n" + "=" * 70)
    print("Example 3: V15.1 Integration Pattern")
    print("=" * 70)

    print("""
Integration with V15.1 simulate_v151.py:

1. Initialize SEA actuators before simulation:
    ```python
    sea_left = SEAActuator("left_hip", SEAParams(k_sea=500.0))
    sea_right = SEAActuator("right_hip", SEAParams(k_sea=500.0))
    sea_left.initialize(q_link_initial=0.0)
    sea_right.initialize(q_link_initial=0.0)
    ```

2. In the simulation loop (after mujoco.mj_step):
    ```python
    # Get motor torques (FSM output, after clipping)
    tau_motor_l = float(np.clip(l_hip_des, -hip_lim, hip_lim))
    tau_motor_r = float(np.clip(r_hip_des, -hip_lim, hip_lim))

    # Get velocities from data.qvel
    qd_motor_l = float(data.qvel[d_l_motor])
    qd_motor_r = float(data.qvel[d_r_motor])
    qd_link_l = float(data.qvel[d_l_link])
    qd_link_r = float(data.qvel[d_r_link])

    # Get spring deflections from data.qpos
    q_link_l = float(data.qpos[q_l_link])
    q_link_r = float(data.qpos[q_r_link])

    # Update energy tracking
    sea_left.update_energy(tau_motor_l, qd_motor_l, q_link_l, qd_link_l, dt)
    sea_right.update_energy(tau_motor_r, qd_motor_r, q_link_r, qd_link_r, dt)
    ```

3. After simulation, generate reports:
    ```python
    audit_left = sea_left.finalize_energy_audit(float(data.qpos[q_l_link]))
    audit_right = sea_right.finalize_energy_audit(float(data.qpos[q_r_link]))

    summary['sea_energy_audit'] = {
        'left_hip': audit_left,
        'right_hip': audit_right,
    }
    ```

Key Benefits:
  - Decouples energy accounting from simulation loop
  - Provides detailed energy breakdown per actuator
  - Validates energy conservation (balance error should be <1%)
  - Enables comparative analysis across stiffness settings
    """)


def example_xml_generation():
    """Show XML generation for MuJoCo models."""
    print("\n" + "=" * 70)
    print("Example 4: XML Generation for MuJoCo")
    print("=" * 70)

    from sea_actuator import build_sea_xml_fragment

    sea_params = PRESETS["v151_soft"]

    print("\nGenerated XML for left hip SEA:")
    print("-" * 70)
    xml = build_sea_xml_fragment("left", sea_params, lateral_offset=-0.055)
    print(xml)

    print("\nThis XML fragment should be inserted into the hip body,")
    print("replacing the standard rigid hip joint structure.")


if __name__ == "__main__":
    example_basic_usage()
    example_stiffness_comparison()
    example_v151_integration_pattern()
    example_xml_generation()

    print("\n" + "=" * 70)
    print("Examples complete! See D:\\Dunna\\Documents\\hw-1\\common\\sea_actuator.py")
    print("for full API documentation.")
    print("=" * 70)

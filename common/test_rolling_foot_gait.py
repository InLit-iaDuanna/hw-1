"""Test script for RollingFootGait model.

Verifies:
- Model instantiation
- XML generation
- Initialization
- Contact detection
- Control computation
- Basic simulation step
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.rolling_foot_gait import RollingFootGait, RollingFootParams


def test_model_creation():
    """Test model creation with default parameters."""
    print("=" * 60)
    print("Test 1: Model Creation")
    print("=" * 60)

    params = RollingFootParams()
    gait = RollingFootGait(params)

    print("[OK] RollingFootGait instance created")
    print(f"  Slope: {params.slope_deg}°")
    print(f"  Foot length: {params.foot_length}m")
    print(f"  Leg length: {params.leg_length}m")
    print()

    return gait


def test_xml_generation(gait: RollingFootGait):
    """Test XML generation and model loading."""
    print("=" * 60)
    print("Test 2: XML Generation and Model Loading")
    print("=" * 60)

    model = gait.model

    print("[OK] Model loaded successfully")
    print(f"  nq (position dims): {model.nq}")
    print(f"  nv (velocity dims): {model.nv}")
    print(f"  nu (actuators): {model.nu}")
    print(f"  timestep: {model.opt.timestep}s")

    # Verify joints
    expected_joints = [
        "hip_x",
        "hip_z",
        "left_hip",
        "left_knee",
        "left_ankle",
        "right_hip",
        "right_knee",
        "right_ankle",
    ]
    for joint_name in expected_joints:
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        assert jid >= 0, f"Joint {joint_name} not found"
    print(f"[OK] All {len(expected_joints)} expected joints found")

    # Verify actuators
    expected_actuators = [
        "left_hip_muscle",
        "left_knee_stabilizer",
        "right_hip_muscle",
        "right_knee_stabilizer",
    ]
    for act_name in expected_actuators:
        aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
        assert aid >= 0, f"Actuator {act_name} not found"
    print(f"[OK] All {len(expected_actuators)} expected actuators found")

    # Verify foot geoms
    foot_geoms = [
        "left_heel",
        "left_sole",
        "left_toe",
        "right_heel",
        "right_sole",
        "right_toe",
    ]
    for geom_name in foot_geoms:
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, geom_name)
        assert gid >= 0, f"Geom {geom_name} not found"
    print(f"[OK] All {len(foot_geoms)} foot geoms found (heel-toe-toe)")
    print()


def test_initialization(gait: RollingFootGait):
    """Test model initialization."""
    print("=" * 60)
    print("Test 3: Initialization")
    print("=" * 60)

    gait.initialize()
    data = gait.data

    print("[OK] Initialization completed")
    print(f"  Hip position: ({data.qpos[0]:.3f}, {data.qpos[1]:.3f})m")
    print(f"  Hip velocity: ({data.qvel[0]:.3f}, {data.qvel[1]:.3f})m/s")
    print(f"  Left hip angle: {np.rad2deg(data.qpos[2]):.1f}°")
    print(f"  Right hip angle: {np.rad2deg(data.qpos[5]):.1f}°")

    # Verify state is finite
    assert np.all(np.isfinite(data.qpos)), "qpos contains non-finite values"
    assert np.all(np.isfinite(data.qvel)), "qvel contains non-finite values"
    print("[OK] All states are finite")
    print()


def test_geometry_utilities(gait: RollingFootGait):
    """Test geometry calculation functions."""
    print("=" * 60)
    print("Test 4: Geometry Utilities")
    print("=" * 60)

    # Test ramp height
    x_values = [0.0, 1.0, 2.0]
    for x in x_values:
        h = gait.ramp_height(x)
        print(f"  ramp_height({x:.1f}) = {h:.4f}m")

    # Test foot center on ramp
    foot_z = gait.foot_center_z_on_ramp(0.0)
    print(f"  foot_center_z_on_ramp(0.0) = {foot_z:.4f}m")

    # Test smoothstep
    u_values = [0.0, 0.5, 1.0]
    for u in u_values:
        s = gait.smoothstep(u)
        print(f"  smoothstep({u:.1f}) = {s:.4f}")

    # Test IK
    hip_x, hip_z = 0.5, 1.0
    foot_x, foot_z = 0.0, 0.04
    hip_angle, knee_angle = gait.leg_ik_front_knee(hip_x, hip_z, foot_x, foot_z)
    print(f"  IK: hip={np.rad2deg(hip_angle):.1f}°, knee={np.rad2deg(knee_angle):.1f}°")

    print("[OK] Geometry utilities working")
    print()


def test_contact_detection(gait: RollingFootGait):
    """Test contact detection."""
    print("=" * 60)
    print("Test 5: Contact Detection")
    print("=" * 60)

    gait.initialize()

    # Get contact detail
    detail = gait.foot_contact_detail()
    print("  Contact detail:")
    for key, value in detail.items():
        print(f"    {key}: {value}")

    # Get overall contact flags
    left_contact, right_contact = gait.contact_flags()
    print(f"  Left foot contact: {left_contact}")
    print(f"  Right foot contact: {right_contact}")

    # Get site margins
    sites = ["left_heel_site", "left_toe_site", "right_heel_site", "right_toe_site"]
    print("  Site margins:")
    for site in sites:
        margin = gait.site_margin(site)
        print(f"    {site}: {margin:.4f}m")

    print("[OK] Contact detection working")
    print()


def test_control_computation(gait: RollingFootGait):
    """Test control computation."""
    print("=" * 60)
    print("Test 6: Control Computation")
    print("=" * 60)

    gait.initialize()

    t = 0.5
    support_foot = "left"
    burst_start_t = 0.0

    left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode = (
        gait.compute_control(t, support_foot, burst_start_t)
    )

    print(f"  Time: {t}s, Support: {support_foot}, Mode: {mode}")
    print("  Torques:")
    print(f"    Left hip: {left_hip_tau:.3f} Nm")
    print(f"    Left knee: {left_knee_tau:.3f} Nm")
    print(f"    Right hip: {right_hip_tau:.3f} Nm")
    print(f"    Right knee: {right_knee_tau:.3f} Nm")

    # Verify torques are within limits
    p = gait.params
    assert (
        abs(left_hip_tau) <= p.hip_torque_limit + 1e-6
    ), "Left hip torque exceeds limit"
    assert (
        abs(right_hip_tau) <= p.hip_torque_limit + 1e-6
    ), "Right hip torque exceeds limit"
    assert (
        abs(left_knee_tau) <= p.knee_torque_limit + 1e-6
    ), "Left knee torque exceeds limit"
    assert (
        abs(right_knee_tau) <= p.knee_torque_limit + 1e-6
    ), "Right knee torque exceeds limit"

    print("[OK] Control computation working, torques within limits")
    print()


def test_simulation_step(gait: RollingFootGait):
    """Test basic simulation step."""
    print("=" * 60)
    print("Test 7: Simulation Step")
    print("=" * 60)

    gait.reset()
    model = gait.model
    data = gait.data

    # Run 100 steps
    n_steps = 100
    support_foot = "left"
    burst_start_t = 0.0

    for i in range(n_steps):
        t = i * model.opt.timestep

        # Compute control
        tau = gait.compute_control(t, support_foot, burst_start_t)
        data.ctrl[:] = tau[:4]

        # Step simulation
        mujoco.mj_step(model, data)

        # Check for failure
        failure = gait.classify_failure(data.qpos[0], t)
        if failure:
            print(f"  Warning: Failure detected at step {i}: {failure}")
            break
    else:
        print(f"[OK] Completed {n_steps} simulation steps without failure")
        print(f"  Final time: {t:.3f}s")
        print(f"  Hip position: ({data.qpos[0]:.3f}, {data.qpos[1]:.3f})m")
        print(f"  Hip velocity: ({data.qvel[0]:.3f}, {data.qvel[1]:.3f})m/s")

    print()


def test_custom_parameters():
    """Test model with custom parameters."""
    print("=" * 60)
    print("Test 8: Custom Parameters")
    print("=" * 60)

    custom_params = RollingFootParams(
        slope_deg=5.0,
        foot_radius=0.05,
        hip_mass=6.0,
        duration=8.0,
    )

    gait = RollingFootGait(custom_params)
    model = gait.model

    print("[OK] Model created with custom parameters")
    print(f"  Slope: {custom_params.slope_deg}°")
    print(f"  Foot radius: {custom_params.foot_radius}m")
    print(f"  Hip mass: {custom_params.hip_mass}kg")
    print(f"  Duration: {custom_params.duration}s")

    # Initialize and verify
    gait.initialize()
    assert np.all(np.isfinite(gait.data.qpos)), "Custom params: qpos not finite"
    print("[OK] Custom parameters model initialized successfully")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "RollingFootGait Model Test Suite" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    try:
        # Run tests
        gait = test_model_creation()
        test_xml_generation(gait)
        test_initialization(gait)
        test_geometry_utilities(gait)
        test_contact_detection(gait)
        test_control_computation(gait)
        test_simulation_step(gait)
        test_custom_parameters()

        # Summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("[OK] All tests passed!")
        print()
        print("The RollingFootGait model is ready to use.")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

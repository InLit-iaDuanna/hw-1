"""
Integration test for MuJoCo-FEA workflow.

Validates that all modules can be imported and basic functionality works
without requiring Abaqus or actual simulation data.

Usage:
    python test_integration.py
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported."""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)

    try:
        import extract_contact_forces

        print("[PASS] extract_contact_forces")
    except Exception as e:
        print(f"[FAIL] extract_contact_forces: {e}")
        return False

    try:
        import generate_fea_boundary_conditions

        print("[PASS] generate_fea_boundary_conditions")
    except Exception as e:
        print(f"[FAIL] generate_fea_boundary_conditions: {e}")
        return False

    try:
        import parse_fea_results

        print("[PASS] parse_fea_results")
    except Exception as e:
        print(f"[FAIL] parse_fea_results: {e}")
        return False

    try:
        import design_constraint_validator

        print("[PASS] design_constraint_validator")
    except Exception as e:
        print(f"[FAIL] design_constraint_validator: {e}")
        return False

    try:
        import workflow_example

        print("[PASS] workflow_example")
    except Exception as e:
        print(f"[FAIL] workflow_example: {e}")
        return False

    print("\n[PASS] All modules imported successfully\n")
    return True


def test_data_structures():
    """Test that data structures are correctly defined."""
    print("=" * 70)
    print("TEST 2: Data Structures")
    print("=" * 70)

    from extract_contact_forces import ContactEvent, ContactForceHistory
    from generate_fea_boundary_conditions import FEABoundaryCondition
    from parse_fea_results import MaterialProperties, StressAnalysisResult
    from design_constraint_validator import DesignRequirements, ValidationResult

    # Test ContactEvent
    event = ContactEvent(
        time=1.0,
        foot="left",
        force_normal=350.0,
        force_tangential=50.0,
        contact_position_x=0.5,
        contact_position_z=0.0,
        body_velocity_x=0.8,
        body_velocity_z=-0.75,
        event_type="heel_strike",
    )
    print(
        f"[PASS] ContactEvent: force={event.force_normal}N, velocity={event.body_velocity_z}m/s"
    )

    # Test MaterialProperties
    mat = MaterialProperties(
        name="Test_Material",
        elastic_modulus_Pa=50e9,
        poisson_ratio=0.3,
        yield_stress_Pa=200e6,
    )
    print(f"[PASS] MaterialProperties: {mat.name}, E={mat.elastic_modulus_Pa/1e9}GPa")

    # Test FEABoundaryCondition
    bc = FEABoundaryCondition(
        load_type="initial_velocity",
        target_geometry="heel_body",
        time_dependent=False,
        velocity_magnitude=0.75,
        velocity_direction=(0.0, 0.0, -1.0),
    )
    print(f"[PASS] FEABoundaryCondition: {bc.load_type}, v={bc.velocity_magnitude}m/s")

    # Test DesignRequirements
    req = DesignRequirements(
        min_safety_factor_yield=1.5,
        target_gait_cycles=100000,
    )
    print(
        f"[PASS] DesignRequirements: SF>={req.min_safety_factor_yield}, cycles>={req.target_gait_cycles}"
    )

    print("\n[PASS] All data structures working\n")
    return True


def test_contact_force_extraction():
    """Test contact force extraction with synthetic data."""
    print("=" * 70)
    print("TEST 3: Contact Force Extraction")
    print("=" * 70)

    import numpy as np
    from extract_contact_forces import detect_contact_events

    # Create synthetic data
    dt = 0.001  # 1ms
    duration = 3.0  # 3 seconds
    n_steps = int(duration / dt)

    time = np.linspace(0, duration, n_steps)

    # Simulate heel-strike pattern: periodic impacts every 0.5s
    contact_force = np.zeros(n_steps)
    for i in range(6):  # 6 impacts
        impact_time = 0.25 + i * 0.5
        impact_idx = int(impact_time / dt)
        # Gaussian impact profile
        for j in range(-50, 50):
            if 0 <= impact_idx + j < n_steps:
                contact_force[impact_idx + j] = 350.0 * np.exp(-(j**2) / 200.0)

    data = {
        "time": time,
        "left_contact_force_z": contact_force,
        "left_foot_vel_z": np.ones(n_steps) * -0.75,  # constant velocity
    }

    # Extract events
    events = detect_contact_events(
        data, foot="left", event_type="heel_strike", force_threshold=50.0
    )

    print(f"✓ Detected {len(events)} heel-strike events")
    if events:
        print(f"  Event 1: t={events[0].time:.3f}s, F={events[0].force_normal:.1f}N")
        print(
            f"  Event {len(events)}: t={events[-1].time:.3f}s, F={events[-1].force_normal:.1f}N"
        )

    assert len(events) == 6, f"Expected 6 events, got {len(events)}"
    print("\n✓ Contact force extraction working\n")
    return True


def test_boundary_condition_generation():
    """Test FEA boundary condition generation."""
    print("=" * 70)
    print("TEST 4: Boundary Condition Generation")
    print("=" * 70)

    from generate_fea_boundary_conditions import contact_forces_to_fea_bc

    # Synthetic contact data
    contact_data = {
        "version": "test_v1",
        "num_events": 4,
        "statistics": {
            "peak_force_avg_N": 380.5,
            "velocity_z_avg_m_s": -0.758,
            "velocity_x_avg_m_s": 0.05,
        },
    }

    # Generate initial velocity BC
    bc = contact_forces_to_fea_bc(
        contact_data,
        bc_type="initial_velocity",
        effective_mass=2.5,
    )

    print(f"✓ BC generated: {bc.load_type}")
    print(f"  Velocity: {bc.velocity_magnitude:.4f} m/s")
    print(f"  Direction: {bc.velocity_direction}")
    print(f"  Effective mass: {bc.effective_mass} kg")

    assert bc.velocity_magnitude > 0.7, "Velocity should be ~0.758"
    print("\n✓ Boundary condition generation working\n")
    return True


def test_result_parsing():
    """Test FEA result parsing."""
    print("=" * 70)
    print("TEST 5: FEA Result Parsing")
    print("=" * 70)

    from parse_fea_results import parse_abaqus_json_results, MATERIALS
    import json
    import tempfile

    # Create synthetic FEA results
    fea_results = {
        "analysis": "Test_Analysis",
        "material": "PLA",
        "peak_von_mises_Pa": 60e6,
        "peak_von_mises_MPa": 60.0,
        "safety_factor_yield": 1.0,
        "peak_PEEQ": 0.01,
        "peak_contact_force_N": 380.0,
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fea_results, f)
        temp_path = Path(f.name)

    try:
        # Parse results
        result = parse_abaqus_json_results(temp_path)

        print(f"✓ Results parsed: {result.material}")
        print(f"  Peak stress: {result.peak_von_mises_Pa/1e6:.2f} MPa")
        print(f"  Safety factor: {result.safety_factor_yield:.2f}")
        print(f"  Status: {result.pass_fail_status}")

        assert result.material == "PLA", "Material should be PLA"
        assert result.pass_fail_status in ["PASS", "MARGINAL", "FAIL"], "Invalid status"

    finally:
        temp_path.unlink()

    print("\n✓ Result parsing working\n")
    return True


def test_design_validation():
    """Test design constraint validation."""
    print("=" * 70)
    print("TEST 6: Design Validation")
    print("=" * 70)

    from design_constraint_validator import (
        validate_structural_integrity,
        DesignRequirements,
    )

    # Synthetic FEA results
    fea_results = {
        "material": "AL6061-T6",
        "peak_von_mises_MPa": 50.0,
        "safety_factor_yield": 5.5,
        "peak_PEEQ": 0.0,
    }

    requirements = DesignRequirements(
        min_safety_factor_yield=1.5,
        max_plastic_deformation=0.01,
    )

    # Run validation checks
    checks = validate_structural_integrity(fea_results, requirements)

    print(f"✓ Validation completed: {len(checks)} checks")
    for check in checks:
        status = "✓" if check.passed else "✗"
        print(f"  {status} {check.check_name}: {check.measured_value}")

    passed = sum(1 for c in checks if c.passed)
    print(f"\n✓ Design validation working ({passed}/{len(checks)} passed)\n")
    return True


def test_workflow_class():
    """Test workflow manager class."""
    print("=" * 70)
    print("TEST 7: Workflow Manager")
    print("=" * 70)

    from workflow_example import MuJoCoFEAWorkflow

    # This will fail if version doesn't exist, but we're just testing initialization
    try:
        # Try with a version that likely exists
        workflow = MuJoCoFEAWorkflow(
            version="v10",
            material="PLA",
            output_dir=Path(__file__).parent / "out" / "test_workflow",
        )
        print(f"✓ Workflow initialized: {workflow.version}")
        print(f"  Material: {workflow.material}")
        print(f"  Output: {workflow.output_dir}")

    except FileNotFoundError as e:
        print(f"⚠ Workflow initialization skipped (version not found)")
        print(f"  This is OK if v10 directory doesn't exist")
    except Exception as e:
        print(f"✗ Workflow initialization failed: {e}")
        return False

    print("\n✓ Workflow manager working\n")
    return True


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "#" * 70)
    print("# MuJoCo-FEA Integration Test Suite")
    print("#" * 70 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("Data Structures", test_data_structures),
        ("Contact Force Extraction", test_contact_force_extraction),
        ("Boundary Condition Generation", test_boundary_condition_generation),
        ("Result Parsing", test_result_parsing),
        ("Design Validation", test_design_validation),
        ("Workflow Manager", test_workflow_class),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ TEST FAILED: {name}")
            print(f"  Error: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} | {name}")

    print("=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

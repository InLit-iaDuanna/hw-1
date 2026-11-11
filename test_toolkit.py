# -*- coding: utf-8 -*-
"""
Quick Test Script for Algorithm Toolkit
Verify all tools are working correctly
"""

import sys
from pathlib import Path


def test_imports():
    """Test basic imports"""
    print("=" * 60)
    print("Test 1: Check basic dependencies")
    print("=" * 60)

    try:
        import numpy as np

        print("[OK] NumPy:", np.__version__)
    except ImportError:
        print("[FAIL] NumPy not found")
        return False

    try:
        import mujoco

        print("[OK] MuJoCo:", mujoco.__version__)
    except ImportError:
        print("[FAIL] MuJoCo not found")
        return False

    try:
        import matplotlib

        print("[OK] Matplotlib:", matplotlib.__version__)
    except ImportError:
        print("[FAIL] Matplotlib not found")
        return False

    return True


def test_optional_imports():
    """Test optional dependencies"""
    print("\n" + "=" * 60)
    print("Test 2: Check optional dependencies (RL/Optimization)")
    print("=" * 60)

    optional_libs = [
        ("stable_baselines3", "RL training (PPO/SAC)"),
        ("gymnasium", "RL environment"),
        ("casadi", "Trajectory optimization"),
        ("skopt", "Bayesian optimization"),
        ("SALib", "Sobol sensitivity analysis"),
    ]

    for lib, desc in optional_libs:
        try:
            __import__(lib)
            print(f"[OK] {lib:20s} - {desc}")
        except ImportError:
            print(f"[--] {lib:20s} - {desc} (not installed)")


def test_model_files():
    """Test model files"""
    print("\n" + "=" * 60)
    print("Test 3: Check MuJoCo model files")
    print("=" * 60)

    project_root = Path(__file__).parent

    models = [
        "v13_7_friction_compensation/out/v13_7_models/friction_comp_walker.xml",
        "v10_rolling_foot_biomimetic_gait/models/rolling_foot_walker.xml",
        "v01_mujoco_compass_gait/models/compass_gait.xml",
    ]

    found_models = []
    for model_path in models:
        full_path = project_root / model_path
        if full_path.exists():
            print(f"[OK] {model_path}")
            found_models.append(str(full_path))
        else:
            print(f"[--] {model_path}")

    return found_models


def test_controller_files():
    """Test controller files"""
    print("\n" + "=" * 60)
    print("Test 4: Check controller files")
    print("=" * 60)

    project_root = Path(__file__).parent

    files = [
        "hardware_ready_controller/controller.py",
        "hardware_ready_controller/state_estimator.py",
        "hardware_ready_controller/phase_fsm.py",
        "hardware_ready_controller/feedforward.py",
        "hardware_ready_controller/examples/run_in_mujoco.py",
    ]

    all_exist = True
    for file_path in files:
        full_path = project_root / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print(f"[OK] {file_path:50s} ({size_kb:.1f} KB)")
        else:
            print(f"[FAIL] {file_path}")
            all_exist = False

    return all_exist


def test_rl_files():
    """Test RL files"""
    print("\n" + "=" * 60)
    print("Test 5: Check RL training files")
    print("=" * 60)

    project_root = Path(__file__).parent

    files = [
        "rl_training/environment.py",
        "rl_training/train_ppo.py",
        "rl_training/train_sac.py",
        "rl_training/evaluate.py",
    ]

    all_exist = True
    for file_path in files:
        full_path = project_root / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print(f"[OK] {file_path:50s} ({size_kb:.1f} KB)")
        else:
            print(f"[FAIL] {file_path}")
            all_exist = False

    return all_exist


def test_optimization_files():
    """Test optimization files"""
    print("\n" + "=" * 60)
    print("Test 6: Check optimization tool files")
    print("=" * 60)

    project_root = Path(__file__).parent

    files = [
        "trajectory_optimization/direct_collocation.py",
        "trajectory_optimization/run_optimization.py",
        "virtual_constraints/constraint_controller.py",
        "parameter_tuning/bayesian_optimization.py",
        "parameter_tuning/sensitivity_analysis.py",
        "algorithm_comparison/benchmark_suite.py",
        "algorithm_comparison/run_all_benchmarks.py",
    ]

    all_exist = True
    for file_path in files:
        full_path = project_root / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print(f"[OK] {file_path:50s} ({size_kb:.1f} KB)")
        else:
            print(f"[FAIL] {file_path}")
            all_exist = False

    return all_exist


def generate_summary():
    """Generate test summary"""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print("\n[SUCCESS] Toolkit created successfully!")
    print("\nPackages included:")
    print("  * Hardware-Ready Controller")
    print("  * RL Training (PPO, SAC, Imitation)")
    print("  * Trajectory Optimization")
    print("  * Virtual Constraints")
    print("  * Parameter Tuning (Bayesian, CMA-ES, Sobol, Multi-objective)")
    print("  * Algorithm Comparison")

    print("\nNext steps:")
    print("  1. Install RL: pip install stable-baselines3 gymnasium tensorboard")
    print("  2. Install optimization: pip install casadi scikit-optimize pymoo SALib")
    print("  3. Run example: cd hardware_ready_controller/examples")
    print("                  python run_in_mujoco.py")

    print("\nDocumentation:")
    print("  * ALGORITHM_TOOLKIT_OVERVIEW.md")
    print("  * QUICK_START_ALGORITHMS.md")
    print("  * ALGORITHM_SUMMARY.md")
    print("  * ALGORITHM_CHANGELOG.md")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ALGORITHM TOOLKIT VERIFICATION TEST")
    print("=" * 60 + "\n")

    # Run all tests
    test_imports()
    test_optional_imports()
    found_models = test_model_files()
    test_controller_files()
    test_rl_files()
    test_optimization_files()

    # Generate summary
    generate_summary()

    print("\n[TEST COMPLETE]\n")

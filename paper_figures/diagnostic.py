#!/usr/bin/env python3
"""Quick diagnostic script to verify installation and data availability."""

from __future__ import annotations

import sys
from pathlib import Path


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    print("Checking dependencies...")

    try:
        import matplotlib

        print(f"  ✓ matplotlib {matplotlib.__version__}")
    except ImportError:
        print("  ✗ matplotlib not found")
        return False

    try:
        import numpy

        print(f"  ✓ numpy {numpy.__version__}")
    except ImportError:
        print("  ✗ numpy not found")
        return False

    return True


def check_file_structure() -> bool:
    """Check if directory structure is correct."""
    print("\nChecking file structure...")

    root = Path(__file__).resolve().parent
    required_dirs = [
        "generators",
        "styles",
        "templates",
        "output",
        "output/svg",
        "output/pdf",
        "output/png",
    ]

    all_exist = True
    for dir_name in required_dirs:
        dir_path = root / dir_name
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ missing")
            all_exist = False

    return all_exist


def check_generators() -> bool:
    """Check if generator scripts exist."""
    print("\nChecking generators...")

    root = Path(__file__).resolve().parent
    generators = [
        "fig_version_evolution.py",
        "fig_stability_domain.py",
        "fig_energy_analysis.py",
        "fig_phase_portrait.py",
        "fig_hardware_specs.py",
    ]

    all_exist = True
    for gen_file in generators:
        gen_path = root / "generators" / gen_file
        if gen_path.exists():
            print(f"  ✓ {gen_file}")
        else:
            print(f"  ✗ {gen_file} missing")
            all_exist = False

    return all_exist


def test_generation() -> bool:
    """Test generating a simple figure."""
    print("\nTesting figure generation...")

    try:
        import matplotlib

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.plot([1, 2, 3], [1, 4, 2])
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Test Figure")

        root = Path(__file__).resolve().parent
        test_file = root / "output" / "png" / "test.png"
        fig.savefig(test_file, dpi=150, bbox_inches="tight")
        plt.close(fig)

        if test_file.exists():
            file_size = test_file.stat().st_size
            print(f"  ✓ Test figure generated ({file_size} bytes)")
            test_file.unlink()  # Clean up
            return True
        else:
            print("  ✗ Test figure not created")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def check_data_availability() -> None:
    """Check if simulation data is available for real data loading."""
    print("\nChecking simulation data availability...")

    hw1_root = Path(__file__).resolve().parents[1]

    # Check for version directories
    version_dirs = [
        "v05_hybrid_compass_proof",
        "v10_rolling_foot_biomimetic_gait",
        "v11_rugged_terrain_robustness",
    ]

    found_count = 0
    for vdir in version_dirs:
        vpath = hw1_root / vdir
        if vpath.exists():
            # Check for output data
            out_dir = vpath / "out"
            if out_dir.exists():
                csv_files = list(out_dir.glob("*.csv"))
                if csv_files:
                    print(f"  ✓ {vdir}: {len(csv_files)} CSV files")
                    found_count += 1
                else:
                    print(f"  ○ {vdir}: no CSV data")
            else:
                print(f"  ○ {vdir}: no output folder")
        else:
            print(f"  ✗ {vdir}: not found")

    if found_count > 0:
        print(
            f"\n  Note: {found_count} versions have data available for real data integration"
        )
    else:
        print("\n  Note: Using synthetic data (no simulation data found)")


def main() -> None:
    print("=" * 70)
    print("Paper Figures System Diagnostic")
    print("=" * 70)
    print()

    results = []

    results.append(("Dependencies", check_dependencies()))
    results.append(("File Structure", check_file_structure()))
    results.append(("Generators", check_generators()))
    results.append(("Test Generation", test_generation()))

    check_data_availability()

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name:20s} [{status}]")

    all_passed = all(r[1] for r in results)

    print("=" * 70)
    if all_passed:
        print("All checks passed! System is ready.")
        print("\nRun: python generate_all.py")
    else:
        print("Some checks failed. Please fix issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

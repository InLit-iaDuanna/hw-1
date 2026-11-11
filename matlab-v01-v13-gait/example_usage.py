"""
Example: Using Python to MATLAB Exporter Programmatically
"""

from pathlib import Path
from python_to_matlab_exporter import export_version, export_all_versions

# Repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "python_exports"


def example_single_version():
    """Export a single version (e.g., v10)."""
    print("Example 1: Export single version (v10)")
    print("=" * 60)

    success = export_version(
        version_id="v10",
        version_dir=REPO_ROOT / "v10_rolling_foot_biomimetic_gait",
        output_dir=OUTPUT_DIR,
        version_title="V10 rolling-foot biomimetic gait",
    )

    if success:
        print("\n✓ Export successful!")
        print(f"Output: {OUTPUT_DIR / 'v10' / 'v10_python_export.mat'}")
    else:
        print("\n✗ Export failed")

    print()


def example_batch_export():
    """Export all available versions."""
    print("Example 2: Batch export all versions")
    print("=" * 60)

    export_all_versions(REPO_ROOT, OUTPUT_DIR)

    print("\n✓ Batch export completed!")
    print(f"Check outputs in: {OUTPUT_DIR}")
    print()


def example_custom_pipeline():
    """Custom pipeline: export specific versions for a report."""
    print("Example 3: Custom pipeline for thesis figures")
    print("=" * 60)

    # Versions needed for thesis Chapter 3
    thesis_versions = [
        ("v05", "v05_hybrid_compass_proof", "V5 hybrid passive proof"),
        ("v09", "v09_stable_biomimetic_gait", "V9 stable biomimetic contact gait"),
        ("v10", "v10_rolling_foot_biomimetic_gait", "V10 rolling-foot biomimetic gait"),
        ("v11", "v11_rugged_terrain_robustness", "V11 rugged terrain robustness"),
    ]

    for version_id, folder_name, title in thesis_versions:
        version_dir = REPO_ROOT / folder_name
        if version_dir.exists():
            print(f"\nExporting {version_id}...")
            export_version(version_id, version_dir, OUTPUT_DIR, title)

    print("\n✓ Thesis versions exported!")
    print("\nNext: Open MATLAB and run:")
    print("  cd('D:\\Dunna\\Documents\\hw-1\\matlab-v01-v13-gait')")
    print("  run_matlab_analysis_batch")
    print()


if __name__ == "__main__":
    # Run examples
    example_single_version()
    # example_batch_export()
    # example_custom_pipeline()

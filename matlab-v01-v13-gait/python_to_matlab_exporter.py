"""
Python to MATLAB Data Exporter
Automatically export Python simulation results to MATLAB .mat format.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import scipy.io
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("WARNING: scipy not installed. Install with: pip install scipy")


def load_csv_data(csv_path: Path) -> dict[str, np.ndarray]:
    """Load CSV file and convert to dictionary of numpy arrays."""
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file {csv_path} is empty")

    data: dict[str, np.ndarray] = {}
    for key in rows[0].keys():
        try:
            data[key] = np.array([float(row[key]) for row in rows])
        except ValueError:
            # Keep string columns as object arrays
            data[key] = np.array([row[key] for row in rows], dtype=object)

    return data


def load_json_params(json_path: Path) -> dict[str, Any]:
    """Load JSON parameters file."""
    if not json_path.exists():
        return {}
    return json.loads(json_path.read_text(encoding="utf-8"))


def export_to_mat(
    csv_path: Path,
    json_path: Path | None,
    output_mat_path: Path,
    version_id: str,
    version_title: str,
) -> None:
    """
    Export Python CSV/JSON data to MATLAB .mat format.

    Args:
        csv_path: Path to CSV data file
        json_path: Path to JSON parameters file (optional)
        output_mat_path: Output .mat file path
        version_id: Version identifier (e.g., "v10")
        version_title: Human-readable title
    """
    if not HAS_SCIPY:
        raise RuntimeError("scipy is required for .mat export. Install with: pip install scipy")

    print(f"[{version_id}] Loading data from {csv_path.name}")
    data = load_csv_data(csv_path)

    params = {}
    if json_path and json_path.exists():
        print(f"[{version_id}] Loading parameters from {json_path.name}")
        params = load_json_params(json_path)

    # Prepare MATLAB-compatible structure
    mat_data = {
        "version": version_id,
        "title": version_title,
        "data": data,
        "params": params,
        "column_names": list(data.keys()),
        "n_rows": len(next(iter(data.values()))),
        "n_cols": len(data),
    }

    # Add common derived metrics
    if "time" in data and len(data["time"]) > 0:
        mat_data["duration_s"] = float(data["time"][-1])
        mat_data["dt_s"] = float(data["time"][1] - data["time"][0]) if len(data["time"]) > 1 else 0.0

    if "hip_x" in data:
        mat_data["forward_distance_m"] = float(data["hip_x"][-1] - data["hip_x"][0])

    if "left_contact" in data and "right_contact" in data:
        left_rises = np.sum(np.diff(np.r_[0, data["left_contact"] > 0.5]) == 1)
        right_rises = np.sum(np.diff(np.r_[0, data["right_contact"] > 0.5]) == 1)
        mat_data["left_touchdowns"] = int(left_rises)
        mat_data["right_touchdowns"] = int(right_rises)

    # Save to .mat file (MATLAB v7 format for compatibility)
    output_mat_path.parent.mkdir(parents=True, exist_ok=True)
    scipy.io.savemat(str(output_mat_path), mat_data, format='5', do_compression=True)
    print(f"[{version_id}] Exported to {output_mat_path}")
    print(f"           {mat_data['n_rows']} rows × {mat_data['n_cols']} columns")


def export_version(version_id: str, version_dir: Path, output_dir: Path, version_title: str) -> bool:
    """
    Export a single version's data to MATLAB format.

    Args:
        version_id: Version identifier (e.g., "v10")
        version_dir: Directory containing the version's Python output
        output_dir: Directory for MATLAB output
        version_title: Human-readable title

    Returns:
        True if export succeeded, False otherwise
    """
    # Find the CSV file
    csv_candidates = list(version_dir.glob("out/*_data.csv"))
    if not csv_candidates:
        csv_candidates = list(version_dir.glob("out/*.csv"))

    if not csv_candidates:
        print(f"[{version_id}] WARNING: No CSV data found in {version_dir}/out/")
        return False

    csv_path = csv_candidates[0]  # Use first match

    # Find JSON parameters
    json_candidates = list(version_dir.glob("out/*_params.json")) + list(version_dir.glob("out/*_summary.json"))
    json_path = json_candidates[0] if json_candidates else None

    # Export to .mat
    mat_path = output_dir / version_id / f"{version_id}_python_export.mat"
    try:
        export_to_mat(csv_path, json_path, mat_path, version_id, version_title)
        return True
    except Exception as e:
        print(f"[{version_id}] ERROR: {e}")
        return False


def export_all_versions(repo_root: Path, output_dir: Path) -> None:
    """
    Export all available versions to MATLAB format.

    Args:
        repo_root: Root directory of hw-1 repository
        output_dir: Output directory for MATLAB files
    """
    # Version mapping (id -> title)
    versions = {
        "v01": ("v01_mujoco_compass_gait", "V1 MuJoCo compass gait"),
        "v02": ("v02_rugged_rimless_limit_cycle", "V2 rimless wheel limit cycle"),
        "v03": ("v03_compass_limit_cycle", "V3 compass limit cycle reference"),
        "v04": ("v04_kneed_limit_cycle", "V4 kneed limit cycle reference"),
        "v05": ("v05_hybrid_compass_proof", "V5 hybrid passive proof"),
        "v06": ("v06_mve_gait_homework", "V6 MVE homework expression"),
        "v07": ("v07_true_contact_exploration", "V7 true contact exploration"),
        "v08": ("v08_quasi_passive_assisted", "V8 quasi-passive assist exploration"),
        "v09": ("v09_stable_biomimetic_gait", "V9 stable biomimetic contact gait"),
        "v10": ("v10_rolling_foot_biomimetic_gait", "V10 rolling-foot biomimetic gait"),
        "v11": ("v11_rugged_terrain_robustness", "V11 rugged terrain robustness"),
        "v12": ("v12_energy_cot_analysis", "V12 energy and CoT analysis"),
        "v13": ("v13_parameter_sensitivity_atlas", "V13 parameter sensitivity atlas"),
    }

    success_count = 0
    total_count = 0

    print("=" * 70)
    print("Python → MATLAB Data Export")
    print("=" * 70)

    for version_id, (folder_name, title) in versions.items():
        version_dir = repo_root / folder_name
        if not version_dir.exists():
            print(f"[{version_id}] SKIP: Directory not found")
            continue

        total_count += 1
        if export_version(version_id, version_dir, output_dir, title):
            success_count += 1
        print()

    print("=" * 70)
    print(f"Export complete: {success_count}/{total_count} versions exported successfully")
    print(f"Output directory: {output_dir}")
    print("=" * 70)


def main() -> None:
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Export Python simulation data to MATLAB .mat format")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Root directory of hw-1 repository",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "python_exports",
        help="Output directory for .mat files",
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Export only specific version (e.g., v10)",
    )

    args = parser.parse_args()

    if not HAS_SCIPY:
        print("ERROR: scipy is required for .mat export")
        print("Install with: pip install scipy")
        return

    if args.version:
        # Export single version
        versions = {
            "v01": ("v01_mujoco_compass_gait", "V1 MuJoCo compass gait"),
            "v02": ("v02_rugged_rimless_limit_cycle", "V2 rimless wheel limit cycle"),
            "v03": ("v03_compass_limit_cycle", "V3 compass limit cycle reference"),
            "v04": ("v04_kneed_limit_cycle", "V4 kneed limit cycle reference"),
            "v05": ("v05_hybrid_compass_proof", "V5 hybrid passive proof"),
            "v06": ("v06_mve_gait_homework", "V6 MVE homework expression"),
            "v07": ("v07_true_contact_exploration", "V7 true contact exploration"),
            "v08": ("v08_quasi_passive_assisted", "V8 quasi-passive assist exploration"),
            "v09": ("v09_stable_biomimetic_gait", "V9 stable biomimetic contact gait"),
            "v10": ("v10_rolling_foot_biomimetic_gait", "V10 rolling-foot biomimetic gait"),
            "v11": ("v11_rugged_terrain_robustness", "V11 rugged terrain robustness"),
            "v12": ("v12_energy_cot_analysis", "V12 energy and CoT analysis"),
            "v13": ("v13_parameter_sensitivity_atlas", "V13 parameter sensitivity atlas"),
        }

        if args.version not in versions:
            print(f"ERROR: Unknown version {args.version}")
            print(f"Available versions: {', '.join(versions.keys())}")
            return

        folder_name, title = versions[args.version]
        version_dir = args.repo_root / folder_name

        if not version_dir.exists():
            print(f"ERROR: Directory not found: {version_dir}")
            return

        export_version(args.version, version_dir, args.output_dir, title)
    else:
        # Export all versions
        export_all_versions(args.repo_root, args.output_dir)


if __name__ == "__main__":
    main()

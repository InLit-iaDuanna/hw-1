"""
Design constraint validator: checks if mechanical design meets all requirements.

Integrates MuJoCo simulation data, FEA stress analysis, and design specifications
to validate that the hw-1 device will survive operational loads.

Usage:
    python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json
    python design_constraint_validator.py --config design_requirements.json --full-validation
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np


@dataclass
class DesignRequirements:
    """Design requirements for hw-1 rehab device."""

    # Structural
    min_safety_factor_yield: float = 1.5
    min_safety_factor_ultimate: float = 2.0
    max_plastic_deformation: float = 0.01  # PEEQ limit
    max_deflection_mm: float = 5.0

    # Operational
    target_gait_cycles: int = 100000  # ~100 km walking distance
    max_contact_force_N: float = 500.0  # maximum expected ground reaction
    operating_temperature_range: tuple[float, float] = (-10, 50)  # Celsius

    # Performance
    min_walking_speed_m_s: float = 0.3
    max_walking_speed_m_s: float = 1.2
    max_device_mass_kg: float = 3.0  # per leg
    max_actuator_power_W: float = 50.0

    # Manufacturing
    max_manufacturing_cost_usd: float = 500.0
    manufacturability: Literal["3D_print", "CNC", "injection_mold"] = "3D_print"
    assembly_complexity: Literal["low", "medium", "high"] = "medium"


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    check_name: str
    requirement: str
    measured_value: float | str | None
    required_value: float | str
    passed: bool
    severity: Literal["critical", "warning", "info"] = "critical"
    notes: str = ""


@dataclass
class FullValidationReport:
    """Complete validation report."""

    version: str
    material: str
    timestamp: str
    overall_pass: bool
    checks: list[ValidationResult]
    summary: dict
    recommendations: list[str]


def load_mujoco_performance(version_dir: Path) -> dict:
    """Load MuJoCo simulation performance metrics."""
    # Try to load from cross_version_analysis or version-specific output
    out_dir = version_dir / "out"
    csv_files = list(out_dir.glob("*.csv"))

    if not csv_files:
        return {
            "walking_speed": 0.0,
            "stability": "unknown",
            "distance_traveled": 0.0,
        }

    # Parse CSV to get performance (simplified - could use data_io.py)
    import csv

    with open(csv_files[0]) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return {"walking_speed": 0.0}

    # Calculate average forward velocity
    try:
        times = [float(r["time"]) for r in rows]
        positions = [float(r["hip_x"]) for r in rows]
        duration = times[-1] - times[0]
        distance = positions[-1] - positions[0]
        avg_speed = distance / duration if duration > 0 else 0.0
    except (KeyError, ValueError):
        avg_speed = 0.0

    return {
        "walking_speed": avg_speed,
        "stability": "stable" if avg_speed > 0.3 else "unstable",
        "distance_traveled": distance if "distance" in locals() else 0.0,
        "simulation_duration": duration if "duration" in locals() else 0.0,
    }


def load_fea_results(fea_results_path: Path) -> dict:
    """Load FEA stress analysis results."""
    with open(fea_results_path) as f:
        return json.load(f)


def validate_structural_integrity(
    fea_results: dict, requirements: DesignRequirements
) -> list[ValidationResult]:
    """Validate structural safety factors and stress limits."""
    checks = []

    # Safety factor - yield
    sf_yield = fea_results.get("safety_factor_yield", 0.0)
    checks.append(
        ValidationResult(
            check_name="Safety Factor (Yield)",
            requirement=f"SF >= {requirements.min_safety_factor_yield}",
            measured_value=sf_yield,
            required_value=requirements.min_safety_factor_yield,
            passed=sf_yield >= requirements.min_safety_factor_yield,
            severity="critical",
            notes="Ensures no permanent deformation under normal loads",
        )
    )

    # Plastic deformation
    peak_peeq = fea_results.get("peak_PEEQ", 0.0)
    checks.append(
        ValidationResult(
            check_name="Plastic Deformation",
            requirement=f"PEEQ < {requirements.max_plastic_deformation}",
            measured_value=peak_peeq,
            required_value=requirements.max_plastic_deformation,
            passed=peak_peeq < requirements.max_plastic_deformation,
            severity="critical" if peak_peeq > 0.05 else "warning",
            notes="Plastic strain indicates permanent shape change",
        )
    )

    # Peak stress check
    peak_stress_MPa = fea_results.get("peak_von_mises_MPa", 0.0)
    material = fea_results.get("material", "UNKNOWN")

    # Material-specific limits
    yield_limits = {
        "PLA": 60.0,
        "AL6061-T6": 276.0,
        "TPU-95A": 8.6,
        "PETG": 53.0,
    }

    if material in yield_limits:
        checks.append(
            ValidationResult(
                check_name="Peak Stress vs Yield",
                requirement=f"σ_max < σ_yield ({yield_limits[material]} MPa)",
                measured_value=peak_stress_MPa,
                required_value=yield_limits[material],
                passed=peak_stress_MPa < yield_limits[material],
                severity="critical",
                notes=f"Peak von Mises stress in {material}",
            )
        )

    return checks


def validate_operational_performance(
    mujoco_data: dict, requirements: DesignRequirements
) -> list[ValidationResult]:
    """Validate walking performance and operational metrics."""
    checks = []

    # Walking speed
    speed = mujoco_data.get("walking_speed", 0.0)
    checks.append(
        ValidationResult(
            check_name="Walking Speed",
            requirement=f"{requirements.min_walking_speed_m_s} - {requirements.max_walking_speed_m_s} m/s",
            measured_value=speed,
            required_value=f"{requirements.min_walking_speed_m_s}-{requirements.max_walking_speed_m_s}",
            passed=requirements.min_walking_speed_m_s
            <= speed
            <= requirements.max_walking_speed_m_s,
            severity=(
                "critical"
                if speed < requirements.min_walking_speed_m_s * 0.8
                else "warning"
            ),
            notes="Average forward walking velocity",
        )
    )

    # Stability
    stability = mujoco_data.get("stability", "unknown")
    checks.append(
        ValidationResult(
            check_name="Gait Stability",
            requirement="Stable walking without falls",
            measured_value=stability,
            required_value="stable",
            passed=stability == "stable",
            severity="critical",
            notes="Must complete target distance without falling",
        )
    )

    return checks


def validate_fatigue_life(
    fea_results: dict, requirements: DesignRequirements
) -> list[ValidationResult]:
    """Estimate and validate fatigue life."""
    checks = []

    # Get stress amplitude (simplified: use half of peak stress for fully reversed)
    peak_stress_Pa = fea_results.get("peak_von_mises_Pa", 0.0)
    stress_amplitude = peak_stress_Pa / 2  # Conservative: fully reversed loading

    material = fea_results.get("material", "UNKNOWN")

    # Endurance limits (rough estimates)
    endurance_limits_MPa = {
        "PLA": 24.0,  # ~0.4 * S_ut
        "AL6061-T6": 96.0,  # ~0.35 * S_ut for aluminum
        "TPU-95A": 4.0,
        "PETG": 21.0,
    }

    if material in endurance_limits_MPa:
        S_e_Pa = endurance_limits_MPa[material] * 1e6
        stress_amp_MPa = stress_amplitude / 1e6

        # Check if below endurance limit (infinite life)
        infinite_life = stress_amplitude < S_e_Pa

        if infinite_life:
            estimated_cycles = requirements.target_gait_cycles * 10  # >> target
            passed = True
            notes = f"Stress below endurance limit ({endurance_limits_MPa[material]:.1f} MPa) - infinite life"
        else:
            # Basquin equation estimate: N = (S_f / S_a)^(1/b)
            b = -0.1
            S_f = endurance_limits_MPa[material] * 1e6 * 2  # rough S_f estimate
            estimated_cycles = int((S_f / stress_amplitude) ** (1 / b))
            passed = estimated_cycles >= requirements.target_gait_cycles
            notes = f"Finite life: {estimated_cycles} cycles estimated (needs validation testing)"

        checks.append(
            ValidationResult(
                check_name="Fatigue Life",
                requirement=f">= {requirements.target_gait_cycles} cycles",
                measured_value=estimated_cycles if not infinite_life else "infinite",
                required_value=requirements.target_gait_cycles,
                passed=passed,
                severity="warning",  # Estimates are uncertain
                notes=notes,
            )
        )

    return checks


def validate_manufacturing_feasibility(
    material: str, requirements: DesignRequirements
) -> list[ValidationResult]:
    """Validate manufacturing and cost constraints."""
    checks = []

    # Manufacturing method compatibility
    compatible_materials = {
        "3D_print": ["PLA", "PETG", "TPU-95A"],
        "CNC": ["AL6061-T6", "PLA", "PETG"],
        "injection_mold": ["PLA", "PETG", "TPU-95A"],
    }

    method = requirements.manufacturability
    can_manufacture = material in compatible_materials.get(method, [])

    checks.append(
        ValidationResult(
            check_name="Manufacturing Compatibility",
            requirement=f"Material suitable for {method}",
            measured_value=material,
            required_value=", ".join(compatible_materials.get(method, [])),
            passed=can_manufacture,
            severity="info",
            notes=f"{material} {'is' if can_manufacture else 'is NOT'} compatible with {method}",
        )
    )

    # Cost estimate (very rough)
    material_costs_per_kg = {
        "PLA": 25.0,
        "PETG": 30.0,
        "TPU-95A": 45.0,
        "AL6061-T6": 15.0,  # raw material, machining adds significant cost
    }

    material_densities = {
        "PLA": 1240,
        "PETG": 1270,
        "TPU-95A": 1120,
        "AL6061-T6": 2700,
    }

    if material in material_costs_per_kg:
        # Estimate mass: rough hemisphere r=0.04m + shank ~0.5m × 0.02m dia cylinder
        volume_heel = (2 / 3) * np.pi * (0.04) ** 3
        volume_shank = np.pi * (0.01) ** 2 * 0.5
        total_volume_m3 = volume_heel + volume_shank
        mass_kg = total_volume_m3 * material_densities[material]
        material_cost = mass_kg * material_costs_per_kg[material]

        # Add manufacturing overhead
        mfg_overhead = {
            "3D_print": 1.5,
            "CNC": 5.0,
            "injection_mold": 2.0,
        }
        total_cost = material_cost * mfg_overhead.get(method, 2.0)

        checks.append(
            ValidationResult(
                check_name="Manufacturing Cost",
                requirement=f"< ${requirements.max_manufacturing_cost_usd}",
                measured_value=round(total_cost, 2),
                required_value=requirements.max_manufacturing_cost_usd,
                passed=total_cost < requirements.max_manufacturing_cost_usd,
                severity="info",
                notes=f"Rough estimate: {mass_kg:.2f} kg × ${material_costs_per_kg[material]:.0f}/kg × {mfg_overhead.get(method, 2.0):.1f}× overhead",
            )
        )

    return checks


def generate_recommendations(
    checks: list[ValidationResult], material: str
) -> list[str]:
    """Generate design recommendations based on validation results."""
    recommendations = []

    # Check for failures
    critical_failures = [c for c in checks if not c.passed and c.severity == "critical"]
    warnings = [c for c in checks if not c.passed and c.severity == "warning"]

    if critical_failures:
        recommendations.append(
            "⚠ CRITICAL ISSUES DETECTED - Design requires modification:"
        )
        for check in critical_failures:
            recommendations.append(f"  • {check.check_name}: {check.notes}")

    # Material-specific recommendations
    sf_checks = [c for c in checks if "Safety Factor" in c.check_name and not c.passed]
    if sf_checks:
        if material == "PLA":
            recommendations.append(
                "Consider upgrading to AL6061-T6 for higher strength"
            )
        recommendations.append(
            "Alternative: Add TPU damping layer to reduce peak stress"
        )
        recommendations.append(
            "Alternative: Increase heel radius to distribute contact load"
        )

    # Fatigue recommendations
    fatigue_checks = [c for c in checks if "Fatigue" in c.check_name and not c.passed]
    if fatigue_checks:
        recommendations.append("Fatigue life may be insufficient - consider:")
        recommendations.append("  • Periodic inspection/replacement schedule")
        recommendations.append("  • Stress-relief heat treatment (if applicable)")
        recommendations.append("  • Surface polishing to remove stress concentrations")

    # Performance recommendations
    perf_checks = [
        c for c in checks if "Walking" in c.check_name or "Stability" in c.check_name
    ]
    perf_failures = [c for c in perf_checks if not c.passed]
    if perf_failures:
        recommendations.append(
            "Walking performance below target - tune FSM control parameters"
        )

    if not critical_failures and not warnings:
        recommendations.append("✓ All design constraints satisfied")
        recommendations.append(
            f"✓ {material} is suitable for V22 hardware implementation"
        )

    return recommendations


def run_full_validation(
    version: str,
    fea_results_path: Path,
    requirements: DesignRequirements | None = None,
    output_path: Path | None = None,
) -> FullValidationReport:
    """
    Run complete design validation workflow.

    Args:
        version: Version name (e.g., "v10")
        fea_results_path: Path to FEA results JSON
        requirements: Design requirements (uses defaults if None)
        output_path: Output report path

    Returns:
        FullValidationReport with all checks
    """
    if requirements is None:
        requirements = DesignRequirements()

    # Load data
    hw1_root = Path(__file__).parent.parent
    version_dir = hw1_root / version
    if not version_dir.exists():
        matches = list(hw1_root.glob(f"{version}*"))
        if matches:
            version_dir = matches[0]

    fea_results = load_fea_results(fea_results_path)
    mujoco_data = load_mujoco_performance(version_dir) if version_dir.exists() else {}

    material = fea_results.get("material", "UNKNOWN")

    # Run all validation checks
    all_checks = []
    all_checks.extend(validate_structural_integrity(fea_results, requirements))
    all_checks.extend(validate_operational_performance(mujoco_data, requirements))
    all_checks.extend(validate_fatigue_life(fea_results, requirements))
    all_checks.extend(validate_manufacturing_feasibility(material, requirements))

    # Overall pass/fail
    critical_failures = [
        c for c in all_checks if not c.passed and c.severity == "critical"
    ]
    overall_pass = len(critical_failures) == 0

    # Summary statistics
    total_checks = len(all_checks)
    passed_checks = sum(1 for c in all_checks if c.passed)
    failed_checks = total_checks - passed_checks

    summary = {
        "total_checks": total_checks,
        "passed": passed_checks,
        "failed": failed_checks,
        "pass_rate": (
            round(passed_checks / total_checks * 100, 1) if total_checks > 0 else 0.0
        ),
        "critical_failures": len(critical_failures),
    }

    # Generate recommendations
    recommendations = generate_recommendations(all_checks, material)

    # Create report
    from datetime import datetime

    report = FullValidationReport(
        version=version,
        material=material,
        timestamp=datetime.now().isoformat(),
        overall_pass=overall_pass,
        checks=all_checks,
        summary=summary,
        recommendations=recommendations,
    )

    # Save to file
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_dict = asdict(report)
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        print(f"Validation report saved to: {output_path}")

    return report


def print_validation_report(report: FullValidationReport):
    """Print formatted validation report to console."""
    print("\n" + "=" * 70)
    print(f"  DESIGN VALIDATION REPORT: {report.version} ({report.material})")
    print("=" * 70)

    print(f"\nOVERALL STATUS: {'✓ PASS' if report.overall_pass else '✗ FAIL'}")
    print(
        f"  Checks passed: {report.summary['passed']}/{report.summary['total_checks']} ({report.summary['pass_rate']:.1f}%)"
    )

    print("\n" + "-" * 70)
    print("VALIDATION CHECKS:")
    print("-" * 70)

    for check in report.checks:
        status = "✓" if check.passed else "✗"
        severity_marker = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }.get(check.severity, "")

        print(f"\n{status} {severity_marker} {check.check_name}")
        print(f"   Requirement: {check.requirement}")
        print(f"   Measured: {check.measured_value}")
        if not check.passed:
            print(f"   ⚠ {check.notes}")

    print("\n" + "-" * 70)
    print("RECOMMENDATIONS:")
    print("-" * 70)
    for rec in report.recommendations:
        print(rec)

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate hw-1 mechanical design against requirements"
    )
    parser.add_argument(
        "--version", type=str, required=True, help="Version name (e.g., v10)"
    )
    parser.add_argument(
        "--fea-results", type=Path, required=True, help="Path to FEA results JSON"
    )
    parser.add_argument(
        "--config", type=Path, help="Design requirements JSON (optional)"
    )
    parser.add_argument("--output", type=Path, help="Output validation report path")
    parser.add_argument(
        "--full-validation", action="store_true", help="Run complete validation suite"
    )
    parser.add_argument(
        "--min-sf", type=float, default=1.5, help="Minimum safety factor"
    )

    args = parser.parse_args()

    # Load requirements
    if args.config:
        with open(args.config) as f:
            req_dict = json.load(f)
        requirements = DesignRequirements(**req_dict)
    else:
        requirements = DesignRequirements(min_safety_factor_yield=args.min_sf)

    # Output path
    if args.output:
        output_path = args.output
    else:
        output_path = (
            Path(__file__).parent / "out" / f"{args.version}_validation_report.json"
        )

    # Run validation
    report = run_full_validation(
        args.version, args.fea_results, requirements, output_path
    )

    # Print report
    print_validation_report(report)

    # Exit code
    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    exit(main())

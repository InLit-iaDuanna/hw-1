"""
Parse FEA results (Abaqus ODB or JSON output) and extract design-relevant metrics.

Extracts:
- Peak von Mises stress and location
- Stress concentrations (stress gradients)
- Safety factors for different materials
- Plastic deformation extent
- Contact pressure distribution
- Energy dissipation

Usage:
    python parse_fea_results.py --odb out/Job_HeelStrike.odb --output results_summary.json
    python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class MaterialProperties:
    """Material properties for safety factor calculations."""

    name: str
    elastic_modulus_Pa: float
    poisson_ratio: float
    yield_stress_Pa: float
    ultimate_stress_Pa: float | None = None
    density_kg_m3: float = 1000.0
    fracture_toughness_MPa_m05: float | None = None  # K_IC


# Material database for hw-1 design options
MATERIALS = {
    "PLA": MaterialProperties(
        name="PLA",
        elastic_modulus_Pa=3500e6,
        poisson_ratio=0.36,
        yield_stress_Pa=60e6,
        ultimate_stress_Pa=70e6,
        density_kg_m3=1240,
    ),
    "AL6061-T6": MaterialProperties(
        name="AL6061-T6",
        elastic_modulus_Pa=69e9,
        poisson_ratio=0.33,
        yield_stress_Pa=276e6,
        ultimate_stress_Pa=310e6,
        density_kg_m3=2700,
    ),
    "TPU-95A": MaterialProperties(
        name="TPU-95A",
        elastic_modulus_Pa=26e6,
        poisson_ratio=0.48,
        yield_stress_Pa=8.6e6,
        ultimate_stress_Pa=12e6,
        density_kg_m3=1120,
    ),
    "PETG": MaterialProperties(
        name="PETG",
        elastic_modulus_Pa=2200e6,
        poisson_ratio=0.38,
        yield_stress_Pa=53e6,
        ultimate_stress_Pa=60e6,
        density_kg_m3=1270,
    ),
}


@dataclass
class StressAnalysisResult:
    """Results from stress analysis."""

    analysis_name: str
    material: str
    peak_von_mises_Pa: float
    peak_location: str | None = None
    peak_principal_stress_Pa: float | None = None
    peak_shear_stress_Pa: float | None = None
    peak_plastic_strain: float = 0.0
    plastic_volume_fraction: float = 0.0

    # Safety factors
    safety_factor_yield: float = 999.0
    safety_factor_ultimate: float = 999.0

    # Contact results
    peak_contact_pressure_Pa: float | None = None
    contact_area_m2: float | None = None
    peak_contact_force_N: float | None = None

    # Energy
    total_strain_energy_J: float | None = None
    plastic_dissipation_J: float | None = None
    kinetic_energy_J: float | None = None

    # Design verdict
    pass_fail_status: Literal["PASS", "MARGINAL", "FAIL"] = "PASS"
    failure_mode: str | None = None
    design_recommendation: str = ""


def parse_abaqus_json_results(json_path: Path) -> StressAnalysisResult:
    """
    Parse Abaqus postprocessing JSON output.

    Args:
        json_path: Path to *_results.json from postprocess_odb.py

    Returns:
        StressAnalysisResult with extracted metrics
    """
    with open(json_path) as f:
        data = json.load(f)

    material_name = data.get("material", "UNKNOWN")
    material = MATERIALS.get(material_name)

    peak_mises_Pa = data.get("peak_von_mises_Pa", 0.0)
    peak_mises_MPa = data.get("peak_von_mises_MPa", peak_mises_Pa / 1e6)
    if peak_mises_Pa == 0:
        peak_mises_Pa = peak_mises_MPa * 1e6

    sf_yield = data.get("safety_factor_yield", 999.0)

    # Determine pass/fail
    if sf_yield >= 1.5:
        status = "PASS"
        failure_mode = None
    elif sf_yield >= 1.0:
        status = "MARGINAL"
        failure_mode = "Low safety factor"
    else:
        status = "FAIL"
        failure_mode = "Yield stress exceeded"

    result = StressAnalysisResult(
        analysis_name=data.get("analysis", "UNKNOWN"),
        material=material_name,
        peak_von_mises_Pa=peak_mises_Pa,
        peak_plastic_strain=data.get("peak_PEEQ", 0.0),
        safety_factor_yield=sf_yield,
        peak_contact_force_N=data.get("peak_contact_force_N"),
        total_strain_energy_J=data.get("energy_balance", {}).get("ALLIE"),
        plastic_dissipation_J=data.get("energy_balance", {}).get("ALLPD"),
        kinetic_energy_J=data.get("energy_balance", {}).get("ALLKE"),
        pass_fail_status=status,
        failure_mode=failure_mode,
        design_recommendation=data.get("v22_design_verdict", ""),
    )

    # Calculate SF_ultimate if material known
    if material and material.ultimate_stress_Pa:
        result.safety_factor_ultimate = (
            material.ultimate_stress_Pa / peak_mises_Pa if peak_mises_Pa > 0 else 999.0
        )

    # Check for plastic deformation
    if result.peak_plastic_strain > 0.001:
        result.plastic_volume_fraction = min(
            1.0, result.peak_plastic_strain / 0.1
        )  # rough estimate
        if result.failure_mode is None:
            result.failure_mode = "Plastic deformation detected"

    return result


def compare_materials(
    base_results_path: Path, material_variants: list[str] | None = None
) -> dict[str, StressAnalysisResult]:
    """
    Compare FEA results across different materials.

    Args:
        base_results_path: Path to base results JSON
        material_variants: List of material names to compare (default: all in MATERIALS)

    Returns:
        Dictionary mapping material name to analysis results
    """
    if material_variants is None:
        material_variants = list(MATERIALS.keys())

    # Load base results
    base_result = parse_abaqus_json_results(base_results_path)

    # For actual comparison, we'd need to re-run FEA with different materials
    # Here we estimate based on elastic scaling (rough approximation)
    results = {base_result.material: base_result}

    base_material = MATERIALS.get(base_result.material)
    if base_material is None:
        print(f"Warning: Material {base_result.material} not in database")
        return results

    # Estimate stress in other materials (elastic scaling)
    # σ_new ≈ σ_base * (E_new / E_base) for same geometry and load
    # This is ROUGH - real comparison needs actual FEA runs

    for mat_name in material_variants:
        if mat_name == base_result.material:
            continue

        mat = MATERIALS[mat_name]

        # Elastic stress scaling
        stress_scale = mat.elastic_modulus_Pa / base_material.elastic_modulus_Pa
        peak_stress_est = base_result.peak_von_mises_Pa * stress_scale

        sf_yield = (
            mat.yield_stress_Pa / peak_stress_est if peak_stress_est > 0 else 999.0
        )
        sf_ult = (
            mat.ultimate_stress_Pa / peak_stress_est
            if mat.ultimate_stress_Pa and peak_stress_est > 0
            else 999.0
        )

        if sf_yield >= 1.5:
            status = "PASS"
            failure = None
        elif sf_yield >= 1.0:
            status = "MARGINAL"
            failure = "Low safety factor"
        else:
            status = "FAIL"
            failure = "Yield exceeded (estimated)"

        # Create estimated result
        est_result = StressAnalysisResult(
            analysis_name=f"{base_result.analysis_name}_{mat_name}_ESTIMATE",
            material=mat_name,
            peak_von_mises_Pa=peak_stress_est,
            safety_factor_yield=sf_yield,
            safety_factor_ultimate=sf_ult,
            peak_contact_force_N=base_result.peak_contact_force_N,
            pass_fail_status=status,
            failure_mode=failure,
            design_recommendation=f"Estimated from {base_result.material} results (needs actual FEA validation)",
        )

        results[mat_name] = est_result

    return results


def calculate_stress_concentration_factor(
    peak_stress: float, nominal_stress: float
) -> float:
    """
    Calculate stress concentration factor K_t = σ_peak / σ_nominal.

    Args:
        peak_stress: Peak stress at concentration site
        nominal_stress: Nominal stress in uniform section

    Returns:
        Stress concentration factor
    """
    if nominal_stress == 0:
        return float("inf")
    return peak_stress / nominal_stress


def estimate_fatigue_life(
    stress_amplitude_Pa: float,
    material: MaterialProperties,
    stress_ratio: float = 0.0,
    surface_finish: Literal["polished", "machined", "as_cast"] = "machined",
) -> int:
    """
    Estimate fatigue life using simplified S-N curve approach.

    Args:
        stress_amplitude_Pa: Cyclic stress amplitude
        material: Material properties
        stress_ratio: R = σ_min / σ_max (default 0 = fully reversed)
        surface_finish: Surface condition

    Returns:
        Estimated cycles to failure (0 if infinite life)
    """
    # Endurance limit (rough estimate: 0.5 * S_ut for steel, 0.4 for others)
    S_e = 0.4 * (material.ultimate_stress_Pa or material.yield_stress_Pa)

    # Surface finish factor
    k_surface = {
        "polished": 1.0,
        "machined": 0.9,
        "as_cast": 0.6,
    }[surface_finish]

    S_e_corrected = S_e * k_surface

    # If stress below endurance limit: infinite life
    if stress_amplitude_Pa < S_e_corrected:
        return 0  # infinite life

    # Basquin equation: N = (S_f / σ_a)^(1/b)
    # Assuming b ≈ -0.1 (typical for many materials)
    b = -0.1
    S_f = material.ultimate_stress_Pa or material.yield_stress_Pa

    N = (S_f / stress_amplitude_Pa) ** (1 / b)

    return int(N)


def generate_design_report(
    results: dict[str, StressAnalysisResult],
    output_path: Path,
    design_constraints: dict | None = None,
):
    """
    Generate comprehensive design validation report.

    Args:
        results: Material comparison results
        output_path: Output JSON file path
        design_constraints: Design requirements (e.g., min SF, max weight)
    """
    if design_constraints is None:
        design_constraints = {
            "min_safety_factor_yield": 1.5,
            "min_safety_factor_ultimate": 2.0,
            "max_plastic_strain": 0.01,
            "target_cycles": 100000,
        }

    # Rank materials by safety factor
    ranked = sorted(
        results.items(), key=lambda x: x[1].safety_factor_yield, reverse=True
    )

    report = {
        "design_validation_report": {
            "timestamp": Path(__file__).stat().st_mtime,
            "design_constraints": design_constraints,
            "materials_evaluated": list(results.keys()),
            "analysis_summary": {
                mat_name: {
                    "peak_stress_MPa": round(res.peak_von_mises_Pa / 1e6, 2),
                    "SF_yield": round(res.safety_factor_yield, 2),
                    "SF_ultimate": round(res.safety_factor_ultimate, 2),
                    "status": res.pass_fail_status,
                    "failure_mode": res.failure_mode,
                    "recommendation": res.design_recommendation,
                }
                for mat_name, res in results.items()
            },
            "material_ranking": [
                {
                    "rank": i + 1,
                    "material": mat_name,
                    "SF_yield": round(res.safety_factor_yield, 2),
                    "status": res.pass_fail_status,
                }
                for i, (mat_name, res) in enumerate(ranked)
            ],
            "design_recommendations": _generate_recommendations(
                results, design_constraints
            ),
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Design report written to: {output_path}")


def _generate_recommendations(
    results: dict[str, StressAnalysisResult], constraints: dict
) -> list[str]:
    """Generate design recommendations based on results."""
    recommendations = []

    min_sf = constraints.get("min_safety_factor_yield", 1.5)

    # Find materials that pass
    passing = [
        name for name, res in results.items() if res.safety_factor_yield >= min_sf
    ]
    failing = [
        name for name, res in results.items() if res.safety_factor_yield < min_sf
    ]

    if not passing:
        recommendations.append("CRITICAL: No materials meet safety factor requirement")
        recommendations.append(
            "Consider: (1) Increase material thickness, (2) Add reinforcement, (3) Use composite structure"
        )
    else:
        # Recommend lightest passing material
        passing_with_density = [
            (name, MATERIALS[name].density_kg_m3)
            for name in passing
            if name in MATERIALS
        ]
        if passing_with_density:
            lightest = min(passing_with_density, key=lambda x: x[1])
            recommendations.append(
                f"Recommended material: {lightest[0]} (lightest that meets SF={min_sf})"
            )

    # Check for plastic deformation
    plasticity_detected = [
        name for name, res in results.items() if res.peak_plastic_strain > 0.001
    ]
    if plasticity_detected:
        recommendations.append(
            f"Plastic deformation detected in: {', '.join(plasticity_detected)}"
        )
        recommendations.append(
            "Consider: (1) Add damping layer (TPU), (2) Reduce impact velocity, (3) Increase contact area"
        )

    # Cost-performance tradeoff
    if "PLA" in results and results["PLA"].pass_fail_status == "PASS":
        recommendations.append(
            "PLA is adequate and most cost-effective for prototyping"
        )
    elif "AL6061-T6" in passing:
        recommendations.append(
            "Aluminum recommended for production (high strength, moderate weight)"
        )

    return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="Parse FEA results and generate design report"
    )
    parser.add_argument(
        "--json-results", type=Path, help="Path to Abaqus JSON results file"
    )
    parser.add_argument(
        "--odb", type=Path, help="Path to Abaqus ODB file (requires Abaqus Python)"
    )
    parser.add_argument(
        "--compare-materials",
        action="store_true",
        help="Compare across different materials",
    )
    parser.add_argument(
        "--materials", type=str, nargs="+", help="Materials to compare (default: all)"
    )
    parser.add_argument("--output", type=Path, help="Output design report path")
    parser.add_argument(
        "--min-sf", type=float, default=1.5, help="Minimum required safety factor"
    )

    args = parser.parse_args()

    if args.odb:
        print("Error: Direct ODB parsing requires Abaqus Python environment")
        print("Please use postprocess_odb.py first to generate JSON results")
        return 1

    if not args.json_results:
        parser.error("Must specify --json-results")
        return 1

    # Parse base results
    print(f"Parsing results from: {args.json_results}")
    base_result = parse_abaqus_json_results(args.json_results)

    print("\n=== FEA Results Summary ===")
    print(f"  Material: {base_result.material}")
    print(f"  Peak stress: {base_result.peak_von_mises_Pa / 1e6:.2f} MPa")
    print(f"  Safety factor (yield): {base_result.safety_factor_yield:.2f}")
    print(f"  Status: {base_result.pass_fail_status}")
    if base_result.failure_mode:
        print(f"  Failure mode: {base_result.failure_mode}")

    # Material comparison
    if args.compare_materials:
        print("\nComparing materials...")
        results = compare_materials(args.json_results, args.materials)

        print("\n=== Material Comparison ===")
        for mat_name, result in sorted(
            results.items(), key=lambda x: x[1].safety_factor_yield, reverse=True
        ):
            print(
                f"  {mat_name:15s}: SF={result.safety_factor_yield:5.2f}  Status={result.pass_fail_status}"
            )
    else:
        results = {base_result.material: base_result}

    # Generate design report
    output_path = (
        args.output or Path(__file__).parent / "out" / "design_validation_report.json"
    )

    constraints = {
        "min_safety_factor_yield": args.min_sf,
        "min_safety_factor_ultimate": 2.0,
        "max_plastic_strain": 0.01,
    }

    generate_design_report(results, output_path, constraints)

    print("\n=== Design Recommendations ===")
    with open(output_path) as f:
        report = json.load(f)
    for rec in report["design_validation_report"]["design_recommendations"]:
        print(f"  • {rec}")

    return 0


if __name__ == "__main__":
    exit(main())

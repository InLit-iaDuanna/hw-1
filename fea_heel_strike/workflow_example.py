"""
Complete workflow example: MuJoCo simulation → FEA analysis → Design validation.

This script demonstrates the full integration pipeline for hw-1 design iterations.

Workflow:
1. Extract contact forces from MuJoCo simulation (any version)
2. Generate FEA boundary conditions
3. Run FEA analysis (Abaqus)
4. Parse FEA results
5. Validate against design constraints
6. Generate design recommendations

Usage:
    python workflow_example.py --version v10 --material PLA --run-all
    python workflow_example.py --version v14 --material AL6061-T6 --skip-fea
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Import local modules
sys.path.insert(0, str(Path(__file__).parent))

from design_constraint_validator import (
    DesignRequirements,
    print_validation_report,
    run_full_validation,
)
from extract_contact_forces import extract_from_version
from generate_fea_boundary_conditions import (
    contact_forces_to_fea_bc,
    write_abaqus_initial_velocity,
)
from parse_fea_results import compare_materials, parse_abaqus_json_results


class MuJoCoFEAWorkflow:
    """Complete MuJoCo-FEA integration workflow manager."""

    def __init__(
        self, version: str, material: str = "PLA", output_dir: Path | None = None
    ):
        self.version = version
        self.material = material

        self.hw1_root = Path(__file__).parent.parent
        self.version_dir = self._find_version_dir(version)
        self.fea_dir = Path(__file__).parent

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = self.fea_dir / "out" / f"workflow_{version}"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Workflow state
        self.contact_data = None
        self.bc_data = None
        self.fea_results = None
        self.validation_report = None

    def _find_version_dir(self, version: str) -> Path:
        """Find version directory with pattern matching."""
        version_dir = self.hw1_root / version
        if version_dir.exists():
            return version_dir

        matches = list(self.hw1_root.glob(f"{version}*"))
        if matches:
            return matches[0]

        raise FileNotFoundError(f"Version directory not found: {version}")

    def step1_extract_contact_forces(
        self, foot: str = "left", num_events: int = 4
    ) -> dict:
        """
        Step 1: Extract contact forces from MuJoCo simulation.

        Args:
            foot: Which foot to analyze
            num_events: Number of steady-state events to extract

        Returns:
            Contact force data dictionary
        """
        print("\n" + "=" * 70)
        print("STEP 1: Extract Contact Forces from MuJoCo Simulation")
        print("=" * 70)

        print(f"Version: {self.version_dir.name}")
        print(f"Foot: {foot}")

        self.contact_data = extract_from_version(
            self.version_dir,
            event_type="heel_strike",
            foot=foot,
            num_events=num_events,
        )

        # Save to file
        contact_path = self.output_dir / "contact_forces.json"
        with open(contact_path, "w") as f:
            json.dump(self.contact_data, f, indent=2)

        print("✓ Contact forces extracted")
        print(f"  Events: {self.contact_data['num_events']}")
        print(
            f"  Avg peak force: {self.contact_data['statistics']['peak_force_avg_N']:.1f} N"
        )
        print(
            f"  Avg impact velocity: {self.contact_data['statistics']['velocity_z_avg_m_s']:.4f} m/s"
        )
        print(f"  Saved to: {contact_path}")

        return self.contact_data

    def step2_generate_boundary_conditions(
        self,
        bc_type: str = "initial_velocity",
        effective_mass: float = 2.5,
    ) -> dict:
        """
        Step 2: Generate FEA boundary conditions from contact data.

        Args:
            bc_type: Type of BC ("initial_velocity", "force_history", "quasi_static")
            effective_mass: Effective mass for impact (kg)

        Returns:
            Boundary condition specification
        """
        print("\n" + "=" * 70)
        print("STEP 2: Generate FEA Boundary Conditions")
        print("=" * 70)

        if self.contact_data is None:
            raise ValueError("Must run step1_extract_contact_forces first")

        print(f"BC type: {bc_type}")
        print(f"Effective mass: {effective_mass} kg")

        self.bc_data = contact_forces_to_fea_bc(
            self.contact_data,
            bc_type=bc_type,
            effective_mass=effective_mass,
        )

        # Save BC specification
        bc_path = self.output_dir / "boundary_conditions.json"
        bc_dict = {
            "load_type": self.bc_data.load_type,
            "target_geometry": self.bc_data.target_geometry,
            "velocity_magnitude_m_s": self.bc_data.velocity_magnitude,
            "velocity_direction": self.bc_data.velocity_direction,
            "effective_mass_kg": self.bc_data.effective_mass,
            "contact_radius_m": self.bc_data.contact_radius,
            "friction_coefficient": self.bc_data.friction_coefficient,
        }
        with open(bc_path, "w") as f:
            json.dump(bc_dict, f, indent=2)

        # Write Abaqus input fragment
        if self.bc_data.load_type == "initial_velocity":
            abaqus_bc_path = self.output_dir / "abaqus_initial_conditions.inp"
            write_abaqus_initial_velocity(self.bc_data, abaqus_bc_path)

        print("✓ Boundary conditions generated")
        print(f"  Velocity: {self.bc_data.velocity_magnitude:.4f} m/s")
        print(f"  Saved to: {bc_path}")

        return bc_dict

    def step3_run_fea_analysis(self, abaqus_available: bool = True) -> dict:
        """
        Step 3: Run FEA analysis with Abaqus.

        Args:
            abaqus_available: Whether Abaqus is installed and available

        Returns:
            FEA job information
        """
        print("\n" + "=" * 70)
        print("STEP 3: Run FEA Analysis")
        print("=" * 70)

        if not abaqus_available:
            print("⚠ Abaqus not available - using existing results")
            # Try to find existing results
            existing_results = list(self.fea_dir.glob("out/*_results.json"))
            if existing_results:
                print(f"  Using existing: {existing_results[0].name}")
                return {"status": "skipped", "results_file": existing_results[0]}
            else:
                print("  No existing results found")
                return {"status": "skipped"}

        print(f"Material: {self.material}")
        print("Generating FEA model...")

        # Generate model based on material
        if self.material == "TPU-95A" or "TPU" in self.material:
            model_script = self.fea_dir / "build_tpu_model.py"
            job_name = "Job_HeelStrike_TPU"
        else:
            model_script = self.fea_dir / "build_heel_strike_model.py"
            job_name = "Job_HeelStrike"

        # Run model generation
        try:
            subprocess.run(
                [sys.executable, str(model_script)], check=True, cwd=self.fea_dir
            )
            print(f"✓ Model generated: {job_name}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Model generation failed: {e}")
            return {"status": "failed", "error": str(e)}

        # Submit Abaqus job
        print(f"Submitting Abaqus job: {job_name}")
        fea_out_dir = self.fea_dir / "out"

        try:
            # Run Abaqus solver
            result = subprocess.run(
                ["abaqus", "job=" + job_name, "cpus=4", "interactive"],
                cwd=fea_out_dir,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                print("✗ Abaqus job failed")
                print(result.stderr)
                return {"status": "failed", "error": "Abaqus solver error"}

            print("✓ Abaqus job completed")

            # Run post-processing
            odb_path = fea_out_dir / f"{job_name}.odb"
            postprocess_script = self.fea_dir / "postprocess_odb.py"

            subprocess.run(
                ["abaqus", "python", str(postprocess_script), str(odb_path)],
                cwd=fea_out_dir,
                check=True,
            )

            results_file = fea_out_dir / f"{job_name}_results.json"
            print("✓ Post-processing completed")
            print(f"  Results: {results_file}")

            return {
                "status": "completed",
                "job_name": job_name,
                "results_file": results_file,
            }

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            print(f"✗ FEA execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    def step4_parse_fea_results(
        self, fea_results_path: Path | None = None, compare_materials_flag: bool = False
    ) -> dict:
        """
        Step 4: Parse FEA results and extract design metrics.

        Args:
            fea_results_path: Path to FEA results JSON (auto-detect if None)
            compare_materials_flag: Compare across different materials

        Returns:
            Parsed FEA results
        """
        print("\n" + "=" * 70)
        print("STEP 4: Parse FEA Results")
        print("=" * 70)

        if fea_results_path is None:
            # Auto-detect from fea output directory
            fea_out_dir = self.fea_dir / "out"
            candidates = list(fea_out_dir.glob("*_results.json"))
            if not candidates:
                raise FileNotFoundError("No FEA results found in out/")
            fea_results_path = candidates[0]

        print(f"Results file: {fea_results_path.name}")

        self.fea_results = parse_abaqus_json_results(fea_results_path)

        print("✓ Results parsed")
        print(f"  Material: {self.fea_results.material}")
        print(f"  Peak stress: {self.fea_results.peak_von_mises_Pa / 1e6:.2f} MPa")
        print(f"  Safety factor: {self.fea_results.safety_factor_yield:.2f}")
        print(f"  Status: {self.fea_results.pass_fail_status}")

        if compare_materials_flag:
            print("\nComparing materials...")
            material_results = compare_materials(fea_results_path)

            comparison_path = self.output_dir / "material_comparison.json"
            comparison_dict = {
                name: {
                    "peak_stress_MPa": result.peak_von_mises_Pa / 1e6,
                    "SF_yield": result.safety_factor_yield,
                    "status": result.pass_fail_status,
                }
                for name, result in material_results.items()
            }
            with open(comparison_path, "w") as f:
                json.dump(comparison_dict, f, indent=2)

            print(f"✓ Material comparison saved to: {comparison_path}")

        return self.fea_results

    def step5_validate_design(
        self, requirements: DesignRequirements | None = None
    ) -> dict:
        """
        Step 5: Validate design against requirements.

        Args:
            requirements: Design requirements (uses defaults if None)

        Returns:
            Validation report
        """
        print("\n" + "=" * 70)
        print("STEP 5: Validate Design Constraints")
        print("=" * 70)

        if self.fea_results is None:
            raise ValueError("Must run step4_parse_fea_results first")

        # Find FEA results file
        fea_results_path = self.fea_dir / "out" / "heel_strike_results.json"
        if not fea_results_path.exists():
            fea_results_path = list(self.fea_dir.glob("out/*_results.json"))[0]

        validation_path = self.output_dir / "validation_report.json"

        self.validation_report = run_full_validation(
            self.version,
            fea_results_path,
            requirements,
            validation_path,
        )

        print_validation_report(self.validation_report)

        return self.validation_report

    def run_full_workflow(
        self, skip_fea: bool = False, compare_materials_flag: bool = False
    ):
        """
        Run complete workflow from MuJoCo to design validation.

        Args:
            skip_fea: Skip FEA execution (use existing results)
            compare_materials_flag: Compare materials in step 4
        """
        print("\n" + "#" * 70)
        print(
            f"# MuJoCo-FEA Design Validation Workflow: {self.version} ({self.material})"
        )
        print("#" * 70)

        try:
            # Step 1: Extract contact forces
            self.step1_extract_contact_forces()

            # Step 2: Generate boundary conditions
            self.step2_generate_boundary_conditions()

            # Step 3: Run FEA (optional)
            if not skip_fea:
                self.step3_run_fea_analysis(abaqus_available=True)
            else:
                print("\n⚠ Skipping FEA execution (using existing results)")

            # Step 4: Parse results
            self.step4_parse_fea_results(compare_materials_flag=compare_materials_flag)

            # Step 5: Validate design
            self.step5_validate_design()

            print("\n" + "#" * 70)
            print("# WORKFLOW COMPLETE")
            print("#" * 70)
            print(f"✓ All outputs saved to: {self.output_dir}")

            # Print summary
            if self.validation_report:
                status = "✓ PASS" if self.validation_report.overall_pass else "✗ FAIL"
                print(f"\n📊 Final Design Status: {status}")
                print(
                    f"   Checks passed: {self.validation_report.summary['passed']}/{self.validation_report.summary['total_checks']}"
                )

        except Exception as e:
            print(f"\n✗ Workflow failed: {e}")
            import traceback

            traceback.print_exc()
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Complete MuJoCo-FEA design validation workflow"
    )
    parser.add_argument(
        "--version", type=str, required=True, help="Version name (e.g., v10, v14)"
    )
    parser.add_argument(
        "--material",
        type=str,
        default="PLA",
        choices=["PLA", "AL6061-T6", "TPU-95A", "PETG"],
        help="Material for FEA analysis",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Output directory for workflow results"
    )
    parser.add_argument(
        "--run-all", action="store_true", help="Run complete workflow including FEA"
    )
    parser.add_argument(
        "--skip-fea",
        action="store_true",
        help="Skip FEA execution (use existing results)",
    )
    parser.add_argument(
        "--compare-materials", action="store_true", help="Compare materials in step 4"
    )
    parser.add_argument(
        "--step", type=int, choices=[1, 2, 3, 4, 5], help="Run specific step only"
    )

    args = parser.parse_args()

    # Create workflow manager
    workflow = MuJoCoFEAWorkflow(
        version=args.version,
        material=args.material,
        output_dir=args.output_dir,
    )

    # Run workflow
    if args.run_all:
        workflow.run_full_workflow(
            skip_fea=args.skip_fea,
            compare_materials_flag=args.compare_materials,
        )
    elif args.step:
        # Run specific step
        if args.step == 1:
            workflow.step1_extract_contact_forces()
        elif args.step == 2:
            workflow.step1_extract_contact_forces()
            workflow.step2_generate_boundary_conditions()
        elif args.step == 3:
            workflow.step3_run_fea_analysis()
        elif args.step == 4:
            workflow.step4_parse_fea_results(
                compare_materials_flag=args.compare_materials
            )
        elif args.step == 5:
            workflow.step4_parse_fea_results()
            workflow.step5_validate_design()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

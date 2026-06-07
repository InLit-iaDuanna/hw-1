"""
Generate FEA boundary condition files from MuJoCo contact force data.

Converts extracted contact forces into formats suitable for:
1. Abaqus .inp amplitude definitions
2. JSON boundary condition files for parametric studies
3. Python scripts for programmatic FEA model generation

Usage:
    python generate_fea_boundary_conditions.py --contact-data v10_contact_forces.json --output-format abaqus
    python generate_fea_boundary_conditions.py --version v10 --auto-generate
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np


@dataclass
class FEABoundaryCondition:
    """FEA boundary condition specification."""

    load_type: Literal[
        "point_load", "distributed_load", "initial_velocity", "displacement"
    ]
    target_geometry: str  # e.g., "heel_surface", "ground_contact_point"
    time_dependent: bool

    # For point loads / distributed loads
    force_magnitude: float | None = None  # N
    force_direction: tuple[float, float, float] | None = None  # unit vector

    # For time-dependent loads
    time_amplitude: list[tuple[float, float]] | None = None  # (time, amplitude) pairs

    # For initial velocity
    velocity_magnitude: float | None = None  # m/s
    velocity_direction: tuple[float, float, float] | None = None

    # Geometric parameters
    contact_radius: float | None = None  # m
    contact_area: float | None = None  # m²

    # Material/analysis parameters
    effective_mass: float | None = None  # kg (for initial velocity BC)
    friction_coefficient: float | None = None


def contact_forces_to_fea_bc(
    contact_data: dict,
    bc_type: Literal[
        "initial_velocity", "force_history", "quasi_static"
    ] = "initial_velocity",
    effective_mass: float = 2.5,
    contact_radius: float = 0.04,
    friction_coef: float = 1.35,
) -> FEABoundaryCondition:
    """
    Convert MuJoCo contact force data to FEA boundary conditions.

    Args:
        contact_data: Output from extract_contact_forces.py
        bc_type: Type of FEA analysis to set up
        effective_mass: Mass participating in impact (kg)
        contact_radius: Contact geometry radius (m)
        friction_coef: Coulomb friction coefficient

    Returns:
        FEABoundaryCondition specification
    """

    if bc_type == "initial_velocity":
        # For explicit dynamics: apply initial velocity to impacting body
        # Extract average impact velocity from contact events

        if "statistics" in contact_data:
            v_impact = abs(contact_data["statistics"]["velocity_z_avg_m_s"])
            v_tangent = contact_data["statistics"].get("velocity_x_avg_m_s", 0.0)
        elif "events" in contact_data and contact_data["events"]:
            velocities_z = [e["velocity_z_m_s"] for e in contact_data["events"]]
            velocities_x = [
                e.get("velocity_x_m_s", 0.0) for e in contact_data["events"]
            ]
            v_impact = abs(np.mean(velocities_z))
            v_tangent = np.mean(velocities_x)
        else:
            raise ValueError("No velocity data in contact_data")

        # Direction: downward (negative z in most conventions)
        v_magnitude = math.sqrt(v_impact**2 + v_tangent**2)
        v_dir_z = -v_impact / v_magnitude if v_magnitude > 0 else -1.0
        v_dir_x = v_tangent / v_magnitude if v_magnitude > 0 else 0.0

        return FEABoundaryCondition(
            load_type="initial_velocity",
            target_geometry="heel_body",
            time_dependent=False,
            velocity_magnitude=v_impact,  # just vertical component for explicit impact
            velocity_direction=(v_dir_x, 0.0, v_dir_z),  # (x, y, z) in 3D
            effective_mass=effective_mass,
            contact_radius=contact_radius,
            friction_coefficient=friction_coef,
        )

    elif bc_type == "force_history":
        # For implicit dynamics: apply time-varying force history

        if "time_history" not in contact_data:
            raise ValueError("force_history BC requires time_history data")

        times = contact_data["time_history"]["times"]
        forces_normal = contact_data["time_history"]["forces_normal_N"]
        forces_tangent = contact_data["time_history"].get(
            "forces_tangential_N", [0.0] * len(times)
        )

        # Normalize time to start at 0
        t0 = times[0]
        time_amplitude = [(t - t0, f) for t, f in zip(times, forces_normal)]

        peak_force = max(forces_normal)

        return FEABoundaryCondition(
            load_type="point_load",
            target_geometry="ground_reaction_point",
            time_dependent=True,
            force_magnitude=peak_force,
            force_direction=(0.0, 0.0, 1.0),  # upward ground reaction
            time_amplitude=time_amplitude,
            contact_radius=contact_radius,
            friction_coefficient=friction_coef,
        )

    elif bc_type == "quasi_static":
        # For static analysis: apply peak force as static load

        if "statistics" in contact_data:
            peak_force = contact_data["statistics"]["peak_force_avg_N"]
        elif "peak_force_N" in contact_data:
            peak_force = contact_data["peak_force_N"]
        else:
            raise ValueError("No peak force data in contact_data")

        return FEABoundaryCondition(
            load_type="distributed_load",
            target_geometry="heel_contact_surface",
            time_dependent=False,
            force_magnitude=peak_force,
            force_direction=(0.0, 0.0, 1.0),
            contact_radius=contact_radius,
            contact_area=math.pi * contact_radius**2,
            friction_coefficient=friction_coef,
        )

    else:
        raise ValueError(f"Unknown BC type: {bc_type}")


def write_abaqus_amplitude(
    bc: FEABoundaryCondition,
    output_path: Path,
    amplitude_name: str = "CONTACT_FORCE_AMP",
):
    """
    Write Abaqus *AMPLITUDE keyword for time-dependent loads.

    Args:
        bc: Boundary condition with time_amplitude data
        output_path: Output .inp file path
        amplitude_name: Name for the amplitude definition
    """
    if not bc.time_dependent or bc.time_amplitude is None:
        raise ValueError("BC must be time_dependent with time_amplitude data")

    with open(output_path, "w") as f:
        f.write("**\n")
        f.write("** Amplitude definition from MuJoCo contact force history\n")
        f.write(f"*AMPLITUDE, NAME={amplitude_name}, DEFINITION=TABULAR\n")

        # Write time-amplitude pairs (8 pairs per line in Abaqus format)
        for i, (t, amp) in enumerate(bc.time_amplitude):
            if i > 0 and i % 4 == 0:
                f.write("\n")
            f.write(f"{t:.6e}, {amp:.6e}")
            if (i + 1) % 4 != 0 and i < len(bc.time_amplitude) - 1:
                f.write(", ")
        f.write("\n")

        f.write("**\n")
        f.write("** Apply to load:\n")
        f.write("** *CLOAD, AMPLITUDE=%s\n" % amplitude_name)
        f.write("** node_or_nset, dof, magnitude\n")
        f.write("**\n")

    print(f"Abaqus amplitude written to: {output_path}")


def write_abaqus_initial_velocity(
    bc: FEABoundaryCondition,
    output_path: Path,
    node_set_name: str = "HEEL_NODES",
):
    """
    Write Abaqus *INITIAL CONDITIONS for impact analysis.

    Args:
        bc: Boundary condition with velocity data
        output_path: Output .inp fragment file
        node_set_name: Name of node set to apply velocity to
    """
    if bc.load_type != "initial_velocity" or bc.velocity_magnitude is None:
        raise ValueError("BC must be initial_velocity type")

    v_mag = bc.velocity_magnitude
    v_dir = bc.velocity_direction or (0.0, 0.0, -1.0)

    with open(output_path, "w") as f:
        f.write("**\n")
        f.write("** Initial velocity from MuJoCo heel-strike data\n")
        f.write("** V_impact = %.4f m/s (vertical)\n" % v_mag)
        f.write("**\n")
        f.write("*INITIAL CONDITIONS, TYPE=VELOCITY\n")

        # Abaqus IC format: node_set, dof, value
        # DOF 1=x, 2=y(or z in 2D), 3=z (in 3D)
        if abs(v_dir[0]) > 1e-6:
            f.write(f"{node_set_name}, 1, {v_dir[0] * v_mag:.6f}\n")
        if abs(v_dir[1]) > 1e-6:
            f.write(f"{node_set_name}, 2, {v_dir[1] * v_mag:.6f}\n")
        if abs(v_dir[2]) > 1e-6:
            # For 2D axisymmetric: DOF 2 is axial (z)
            # For 3D: DOF 3 is z
            dof = 2  # assuming 2D axisymmetric like current models
            f.write(f"{node_set_name}, {dof}, {v_dir[2] * v_mag:.6f}\n")

        f.write("**\n")
        f.write(
            "** Effective mass (non-structural): %.2f kg\n" % (bc.effective_mass or 0)
        )
        f.write("** Apply via *NONSTRUCTURAL MASS or *MASS element\n")
        f.write("**\n")

    print(f"Abaqus initial conditions written to: {output_path}")


def write_json_bc(
    bc: FEABoundaryCondition,
    output_path: Path,
    include_metadata: bool = True,
):
    """
    Write boundary condition as JSON for generic FEA tools.

    Args:
        bc: Boundary condition specification
        output_path: Output JSON file path
        include_metadata: Include analysis recommendations
    """
    data = {
        "load_type": bc.load_type,
        "target_geometry": bc.target_geometry,
        "time_dependent": bc.time_dependent,
    }

    if bc.force_magnitude is not None:
        data["force_magnitude_N"] = round(bc.force_magnitude, 2)
    if bc.force_direction is not None:
        data["force_direction"] = list(bc.force_direction)
    if bc.velocity_magnitude is not None:
        data["velocity_magnitude_m_s"] = round(bc.velocity_magnitude, 6)
    if bc.velocity_direction is not None:
        data["velocity_direction"] = list(bc.velocity_direction)
    if bc.effective_mass is not None:
        data["effective_mass_kg"] = bc.effective_mass
    if bc.contact_radius is not None:
        data["contact_radius_m"] = bc.contact_radius
    if bc.contact_area is not None:
        data["contact_area_m2"] = round(bc.contact_area, 6)
    if bc.friction_coefficient is not None:
        data["friction_coefficient"] = bc.friction_coefficient

    if bc.time_amplitude is not None:
        data["time_amplitude"] = [
            {"time_s": round(t, 6), "amplitude": round(a, 2)}
            for t, a in bc.time_amplitude
        ]

    if include_metadata:
        data["metadata"] = {
            "description": f"{bc.load_type} boundary condition for FEA",
            "analysis_type_recommendation": _recommend_analysis_type(bc),
            "mesh_refinement": "Refine mesh near contact region (element size < %.1f mm)"
            % (bc.contact_radius * 1000 / 5),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"JSON boundary conditions written to: {output_path}")


def _recommend_analysis_type(bc: FEABoundaryCondition) -> str:
    """Recommend FEA analysis type based on BC."""
    if bc.load_type == "initial_velocity":
        return "Explicit dynamics (Abaqus/Explicit, LS-DYNA)"
    elif bc.time_dependent:
        return "Implicit dynamics (Abaqus/Standard with *DYNAMIC) or Explicit"
    else:
        return "Static (Abaqus/Standard with *STATIC)"


def write_python_script(
    bc: FEABoundaryCondition,
    output_path: Path,
    template: str = "abaqus",
):
    """
    Generate Python script to apply BC in FEA model builder.

    Args:
        bc: Boundary condition specification
        output_path: Output .py file path
        template: FEA software template ("abaqus", "generic")
    """
    lines = [
        '"""',
        "Auto-generated FEA boundary condition application script.",
        "Generated from MuJoCo contact force data.",
        '"""',
        "",
        "import numpy as np",
        "",
    ]

    if template == "abaqus":
        lines.extend(
            [
                "# Apply to Abaqus model",
                'def apply_boundary_conditions(model, step_name="Impact"):',
                '    """Apply boundary conditions to Abaqus model."""',
                "",
            ]
        )

        if bc.load_type == "initial_velocity":
            lines.extend(
                [
                    f"    # Initial velocity: {bc.velocity_magnitude:.4f} m/s",
                    f"    v_magnitude = {bc.velocity_magnitude:.6f}",
                    f"    v_direction = {bc.velocity_direction}",
                    "",
                    "    # Apply to heel body node set",
                    '    region = model.rootAssembly.sets["HEEL_NODES"]',
                    '    model.predefinedFields["IC_Velocity"].setValues(',
                    "        region=region,",
                    "        velocity1=v_direction[0] * v_magnitude,",
                    "        velocity2=v_direction[2] * v_magnitude,  # axisymmetric: 2=axial",
                    "    )",
                    "",
                ]
            )

        elif bc.time_dependent and bc.time_amplitude:
            lines.extend(
                [
                    f"    # Time-dependent force: peak {bc.force_magnitude:.1f} N",
                    "",
                    "    # Create amplitude",
                    "    time_amplitude = [",
                ]
            )
            for t, a in bc.time_amplitude[:5]:  # show first 5 points
                lines.append(f"        ({t:.6f}, {a:.2f}),")
            lines.extend(
                [
                    "        # ... (see full data in JSON)",
                    "    ]",
                    "",
                    "    model.TabularAmplitude(",
                    '        name="ContactForce",',
                    "        data=time_amplitude,",
                    "    )",
                    "",
                ]
            )

    else:  # generic
        lines.extend(
            [
                "# Generic boundary condition data",
                f'load_type = "{bc.load_type}"',
                f'target_geometry = "{bc.target_geometry}"',
                "",
            ]
        )

        if bc.velocity_magnitude:
            lines.append(f"initial_velocity = {bc.velocity_magnitude:.6f}  # m/s")
        if bc.force_magnitude:
            lines.append(f"peak_force = {bc.force_magnitude:.2f}  # N")

    lines.extend(
        [
            "",
            'if __name__ == "__main__":',
            '    print("Boundary condition script ready for integration")',
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Python script written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate FEA boundary conditions from MuJoCo contact data"
    )
    parser.add_argument(
        "--contact-data", type=Path, help="Input JSON from extract_contact_forces.py"
    )
    parser.add_argument(
        "--version", type=str, help="Version name to auto-extract contact data"
    )
    parser.add_argument(
        "--bc-type",
        type=str,
        default="initial_velocity",
        choices=["initial_velocity", "force_history", "quasi_static"],
        help="Type of boundary condition to generate",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="all",
        choices=["abaqus", "json", "python", "all"],
        help="Output format(s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: fea_heel_strike/out/bc)",
    )
    parser.add_argument(
        "--effective-mass",
        type=float,
        default=2.5,
        help="Effective mass for impact (kg)",
    )
    parser.add_argument(
        "--contact-radius", type=float, default=0.04, help="Contact radius (m)"
    )
    parser.add_argument(
        "--friction", type=float, default=1.35, help="Friction coefficient"
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir:
        out_dir = args.output_dir
    else:
        out_dir = Path(__file__).parent / "out" / "bc"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load contact data
    if args.contact_data:
        contact_data_path = args.contact_data
    elif args.version:
        # Auto-extract contact data first
        from extract_contact_forces import extract_from_version

        hw1_root = Path(__file__).parent.parent
        version_dir = hw1_root / args.version
        if not version_dir.exists():
            matches = list(hw1_root.glob(f"{args.version}*"))
            if matches:
                version_dir = matches[0]
            else:
                raise FileNotFoundError(f"Version not found: {args.version}")

        print(f"Auto-extracting contact forces from {version_dir.name}...")
        contact_data = extract_from_version(version_dir)

        # Save extracted data
        contact_data_path = out_dir / f"{version_dir.name}_contact_forces.json"
        with open(contact_data_path, "w") as f:
            json.dump(contact_data, f, indent=2)
        print(f"  Saved contact data to: {contact_data_path}")
    else:
        parser.error("Must specify --contact-data or --version")
        return

    # Load contact data if from file
    if isinstance(contact_data_path, Path):
        with open(contact_data_path) as f:
            contact_data = json.load(f)

    # Generate boundary condition
    print(f"\nGenerating {args.bc_type} boundary conditions...")
    bc = contact_forces_to_fea_bc(
        contact_data,
        bc_type=args.bc_type,
        effective_mass=args.effective_mass,
        contact_radius=args.contact_radius,
        friction_coef=args.friction,
    )

    # Write output files
    base_name = f"{args.bc_type}_bc"

    if args.output_format in ["abaqus", "all"]:
        if bc.time_dependent and bc.time_amplitude:
            write_abaqus_amplitude(bc, out_dir / f"{base_name}_amplitude.inp")
        if bc.load_type == "initial_velocity":
            write_abaqus_initial_velocity(bc, out_dir / f"{base_name}_initial.inp")

    if args.output_format in ["json", "all"]:
        write_json_bc(bc, out_dir / f"{base_name}.json")

    if args.output_format in ["python", "all"]:
        write_python_script(bc, out_dir / f"{base_name}.py", template="abaqus")

    print("\n=== Boundary Condition Generation Complete ===")
    print(f"  Type: {bc.load_type}")
    if bc.velocity_magnitude:
        print(f"  Impact velocity: {bc.velocity_magnitude:.4f} m/s")
    if bc.force_magnitude:
        print(f"  Peak force: {bc.force_magnitude:.1f} N")
    print(f"  Output directory: {out_dir}")


if __name__ == "__main__":
    main()

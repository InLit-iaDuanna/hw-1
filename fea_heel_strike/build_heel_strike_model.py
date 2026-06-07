"""
Generate Abaqus .inp file directly for heel-strike impact analysis.
Bypasses CAE entirely - generates mesh and all keywords via numpy.

2D Axisymmetric Explicit: hemisphere (r=40mm) on rigid ground.
Elements: CAX4R (reduced integration axisymmetric quad).

Run after generation:
    cd out && abaqus job=Job_HeelStrike cpus=4 interactive
"""

import json
import os

import numpy as np

# === PARAMETERS ===
V_IMPACT = 0.759  # m/s downward
EFFECTIVE_MASS = 2.5  # kg
R = 0.04  # heel radius (m)
FRICTION = 1.35
T_ANALYSIS = 0.010  # 10 ms

MAT_NAME = "PLA"
DENSITY = 1240.0
YOUNGS = 3500.0e6
POISSON = 0.36
YIELD_STRESS = 60.0e6

# Mesh parameters
NR = 20  # elements in radial direction
NZ = 40  # elements in axial direction (through hemisphere height)


def generate_mesh():
    """Generate structured quad mesh for a semicircle (hemisphere cross-section)."""
    # Use polar-like structured mesh
    # r_local from 0 to R, theta from 0 to pi (bottom to top)
    # Map to (x, y) = (r_local*sin(theta), -r_local*cos(theta))
    # This gives semicircle with bottom at (0, -R) and top at (0, R)

    # Bias radial: finer near surface (where contact happens)
    r_frac = np.linspace(0, 1, NR + 1) ** 0.7  # power < 1 = finer at surface
    r_vals = r_frac * R

    # Uniform theta from 0 (bottom pole) to pi (top pole)
    theta_vals = np.linspace(0, np.pi, NZ + 1)

    nodes = {}
    node_id = 1

    for j in range(NZ + 1):
        theta = theta_vals[j]
        for i in range(NR + 1):
            r_local = r_vals[i]
            if i == 0:
                # On the axis: all converge to center
                x = 0.0
                y = 0.0
            else:
                x = r_local * np.sin(theta)  # radial coordinate (must be >= 0)
                y = -r_local * np.cos(theta)  # axial coordinate
            nodes[node_id] = (x, y)
            node_id += 1

    # Elements: structured quads
    elements = []
    elem_id = 1
    for j in range(NZ):
        for i in range(NR):
            n1 = j * (NR + 1) + i + 1
            n2 = n1 + 1
            n3 = n2 + (NR + 1)
            n4 = n1 + (NR + 1)
            # Skip degenerate elements at axis (i==0 means both n1,n4 are at center)
            if i == 0:
                # Collapse to triangle: n1==n4 (both at axis center for this ring)
                # Use CAX3 for axis elements
                elements.append((elem_id, "TRI", n1, n2, n3))
            else:
                elements.append((elem_id, "QUAD", n1, n2, n3, n4))
            elem_id += 1

    return nodes, elements


def generate_mesh_v2():
    """Better mesh: structured quads, no degenerate axis elements.

    Use a mapped mesh approach: rectangular grid mapped to semicircle.
    xi in [0,1] = fraction from axis to surface
    eta in [0,1] = fraction from bottom to top of semicircle
    """
    # Number of elements
    n_radial = NR  # from axis to surface
    n_circum = NZ  # around the semicircle (bottom to top)

    # Create node grid
    # xi: 0=axis, 1=surface. Bias toward surface for contact refinement
    xi_vals = np.linspace(0, 1, n_radial + 1) ** 1.3  # bias toward surface
    # eta: 0=bottom pole, 1=top pole
    eta_vals = np.linspace(0, 1, n_circum + 1)

    nodes = {}
    node_id = 1

    for j in range(n_circum + 1):
        eta = eta_vals[j]
        theta = eta * np.pi  # 0 to pi
        for i in range(n_radial + 1):
            xi = xi_vals[i]
            r_local = xi * R
            # Map to Cartesian (x=radial, y=axial)
            x = r_local * np.sin(theta)
            y = -r_local * np.cos(theta)  # bottom of sphere at y=-R
            nodes[node_id] = (float(x), float(y))
            node_id += 1

    # Offset: place sphere center at y = R + gap so bottom is at y=gap
    gap = 0.0001  # 0.1 mm initial gap
    for nid in nodes:
        x, y = nodes[nid]
        nodes[nid] = (x, y + R + gap)

    # Generate elements
    elements_quad = []
    elements_tri = []
    elem_id = 1

    for j in range(n_circum):
        for i in range(n_radial):
            n1 = j * (n_radial + 1) + i + 1
            n2 = n1 + 1
            n3 = n2 + (n_radial + 1)
            n4 = n1 + (n_radial + 1)

            if i == 0:
                # First column: n1 and n4 are on the axis
                # These degenerate to triangles (n1==n4 in position but different node IDs)
                # Use collapsed quad (repeat one node)
                elements_tri.append((elem_id, n1, n2, n3))
                elem_id += 1
            else:
                elements_quad.append((elem_id, n1, n2, n3, n4))
                elem_id += 1

    return nodes, elements_quad, elements_tri


def find_surface_nodes(nodes, n_radial, n_circum):
    """Find nodes on the outer surface (last column, xi=1)."""
    surface_nodes = []
    for j in range(n_circum + 1):
        nid = j * (n_radial + 1) + (n_radial + 1)  # last node in each row
        surface_nodes.append(nid)
    return surface_nodes


def find_bottom_surface_elements(elements_quad, elements_tri, n_radial, n_circum):
    """Find elements near the bottom pole (contact zone)."""
    # Bottom pole = first few rows (j=0..2)
    # Elements in first 5 circumferential rows, outer radial columns
    contact_elems = []
    for j in range(min(5, n_circum)):
        for i in range(n_radial):
            elem_idx = j * n_radial + i
            if i == 0:
                if elem_idx < len(elements_tri):
                    contact_elems.append(elements_tri[elem_idx][0])
            else:
                # Find in quad list
                quad_idx = elem_idx - (j + 1)  # subtract triangle count
                if quad_idx < len(elements_quad):
                    contact_elems.append(elements_quad[quad_idx][0])
    return contact_elems


def write_inp(filepath, nodes, elements_quad, elements_tri):
    """Write complete Abaqus .inp file."""
    n_radial = NR
    n_circum = NZ

    with open(filepath, "w") as f:
        f.write("*HEADING\n")
        f.write("Heel-Strike Impact: 2D Axisymmetric, PLA hemisphere R=40mm\n")
        f.write("V_impact=0.759 m/s, M_eff=2.5 kg, Explicit 10ms\n")
        f.write("**\n")

        # --- NODES ---
        f.write("*NODE, NSET=ALLNODES\n")
        for nid in sorted(nodes.keys()):
            x, y = nodes[nid]
            f.write("%d, %.8e, %.8e\n" % (nid, x, y))

        # --- ELEMENTS ---
        f.write("*ELEMENT, TYPE=CAX4R, ELSET=QUADS\n")
        for eid, n1, n2, n3, n4 in elements_quad:
            f.write("%d, %d, %d, %d, %d\n" % (eid, n1, n2, n3, n4))

        if elements_tri:
            f.write("*ELEMENT, TYPE=CAX3, ELSET=TRIS\n")
            for eid, n1, n2, n3 in elements_tri:
                f.write("%d, %d, %d, %d\n" % (eid, n1, n2, n3))

        f.write("*ELSET, ELSET=ALLELS\n")
        f.write("QUADS,\n")
        if elements_tri:
            f.write("TRIS,\n")

        # --- Node sets ---
        axis_nodes = [j * (n_radial + 1) + 1 for j in range(n_circum + 1)]
        f.write("*NSET, NSET=AXIS\n")
        _write_set(f, axis_nodes)

        surf_nodes = [j * (n_radial + 1) + (n_radial + 1) for j in range(n_circum + 1)]
        f.write("*NSET, NSET=SURFACE_NODES\n")
        _write_set(f, surf_nodes)

        # --- Contact surface (not needed for General Contact, but kept for post-proc) ---
        f.write("** Node-based surface kept for reference\n")
        f.write("*NSET, NSET=CONTACT_NODES\n")
        # Bottom quarter of surface nodes (near contact zone)
        n_contact = max(3, n_circum // 4)
        contact_nodes = surf_nodes[: n_contact + 1]
        _write_set(f, contact_nodes)

        # --- RIGID SURFACE (ground at y=0) ---
        rigid_node_id = max(nodes.keys()) + 1
        f.write("*NODE, NSET=GROUND_RP\n")
        f.write("%d, 0.0, -0.001\n" % rigid_node_id)
        f.write("*SURFACE, TYPE=SEGMENTS, NAME=GROUND_SURF\n")
        f.write("START, 0.0, 0.0\n")
        f.write("LINE, 0.15, 0.0\n")
        f.write(
            "*RIGID BODY, REF NODE=%d, ANALYTICAL SURFACE=GROUND_SURF\n" % rigid_node_id
        )

        # --- MATERIAL & SECTION ---
        f.write("*SOLID SECTION, ELSET=ALLELS, MATERIAL=%s\n" % MAT_NAME)
        f.write(",\n")
        f.write("*MATERIAL, NAME=%s\n" % MAT_NAME)
        f.write("*DENSITY\n")
        f.write("%.1f,\n" % DENSITY)
        f.write("*ELASTIC\n")
        f.write("%.6e, %.4f\n" % (YOUNGS, POISSON))
        f.write("*PLASTIC\n")
        f.write("%.6e, 0.0\n" % YIELD_STRESS)
        f.write("%.6e, 0.5\n" % (YIELD_STRESS * 1.2))

        # --- NON-STRUCTURAL MASS ---
        f.write("*NONSTRUCTURAL MASS, ELSET=ALLELS, UNITS=TOTAL MASS\n")
        f.write("%.4f,\n" % EFFECTIVE_MASS)

        # --- CONTACT PROPERTIES (model data) ---
        f.write("*SURFACE INTERACTION, NAME=FRIC\n")
        f.write("*FRICTION\n")
        f.write("%.2f,\n" % FRICTION)
        f.write("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD\n")

        # --- INITIAL CONDITIONS ---
        f.write("*INITIAL CONDITIONS, TYPE=VELOCITY\n")
        f.write("ALLNODES, 1, 0.0\n")
        f.write("ALLNODES, 2, %.6f\n" % (-V_IMPACT))

        # --- BOUNDARY CONDITIONS ---
        f.write("*BOUNDARY\n")
        f.write("GROUND_RP, 1, 2, 0.0\n")
        f.write("GROUND_RP, 6, 6, 0.0\n")
        f.write("AXIS, 1, 1, 0.0\n")

        # --- STEP ---
        f.write("*STEP, NAME=Impact, NLGEOM=YES\n")
        f.write("*DYNAMIC, EXPLICIT\n")
        f.write(", %.6f\n" % T_ANALYSIS)

        # --- GENERAL CONTACT (Explicit) ---
        f.write("*CONTACT\n")
        f.write("*CONTACT INCLUSIONS, ALL EXTERIOR\n")
        f.write("*CONTACT PROPERTY ASSIGNMENT\n")
        f.write(", , FRIC\n")

        # --- OUTPUT ---
        f.write("*OUTPUT, FIELD, NUMBER INTERVAL=200\n")
        f.write("*NODE OUTPUT\n")
        f.write("U, V, A, RF\n")
        f.write("*ELEMENT OUTPUT\n")
        f.write("S, LE, PEEQ, STATUS\n")
        f.write("**\n")
        f.write("*OUTPUT, HISTORY, TIME INTERVAL=%.6e\n" % (T_ANALYSIS / 2000))
        f.write("*NODE OUTPUT, NSET=GROUND_RP\n")
        f.write("RF1, RF2\n")
        f.write("*ENERGY OUTPUT\n")
        f.write("ALLKE, ALLIE, ALLPD, ALLSE, ETOTAL\n")
        f.write("**\n")
        f.write("*END STEP\n")


def _write_set(f, ids):
    """Write node/element IDs in 16-per-line format."""
    for i, nid in enumerate(ids):
        if i > 0 and i % 16 == 0:
            f.write("\n")
        if i == len(ids) - 1:
            f.write("%d\n" % nid)
        else:
            f.write("%d, " % nid)
    if not ids:
        f.write("\n")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    print("Generating axisymmetric mesh: NR=%d, NZ=%d" % (NR, NZ))
    nodes, quads, tris = generate_mesh_v2()
    print("  Nodes: %d" % len(nodes))
    print("  Quads (CAX4R): %d" % len(quads))
    print("  Tris (CAX3): %d" % len(tris))

    inp_path = os.path.join(out_dir, "Job_HeelStrike.inp")
    write_inp(inp_path, nodes, quads, tris)
    print("  Written: %s" % inp_path)
    print("")
    print("Next: cd out && abaqus job=Job_HeelStrike cpus=4 interactive")

    # Save mesh info
    info = {
        "model": "HeelStrike_V10_Axisymmetric",
        "elements": {"CAX4R": len(quads), "CAX3": len(tris)},
        "nodes": len(nodes),
        "parameters": {
            "R_heel_m": R,
            "V_impact_m_s": V_IMPACT,
            "M_eff_kg": EFFECTIVE_MASS,
            "material": MAT_NAME,
            "E_Pa": YOUNGS,
            "nu": POISSON,
            "yield_Pa": YIELD_STRESS,
            "density_kg_m3": DENSITY,
            "friction": FRICTION,
            "t_analysis_s": T_ANALYSIS,
        },
    }
    with open(os.path.join(out_dir, "mesh_info.json"), "w") as f:
        json.dump(info, f, indent=2)


if __name__ == "__main__":
    main()

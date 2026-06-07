"""
TPU-buffered heel: 2mm TPU-95A shell over PLA core.
Same mesh framework as PLA-only model, adds a layer partition.

Run: python build_tpu_model.py
     cd out && abaqus job=Job_HeelStrike_TPU cpus=4 interactive
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_heel_strike_model import _write_set

V_IMPACT = 0.759
EFFECTIVE_MASS = 2.5
R_OUTER = 0.04  # heel outer radius (m)
TPU_THICKNESS = 0.002  # 2 mm TPU layer
R_INNER = R_OUTER - TPU_THICKNESS  # PLA core radius
FRICTION = 1.35
T_ANALYSIS = 0.010
NR_CORE = 16  # radial elements in PLA core
NR_TPU = 4  # radial elements in TPU layer
NZ = 40  # circumferential elements


def generate_bilayer_mesh():
    """Structured mesh: PLA core (r=0..R_inner) + TPU shell (r=R_inner..R_outer)."""
    # Radial: core uses power bias toward interface; TPU uniform fine
    xi_core = np.linspace(0, 1, NR_CORE + 1) ** 1.3
    xi_tpu = np.linspace(0, 1, NR_TPU + 1)
    eta_vals = np.linspace(0, 1, NZ + 1)
    gap = 0.0001

    nodes = {}
    nid = 1
    # Core nodes: r = 0 .. R_inner
    for j in range(NZ + 1):
        theta = eta_vals[j] * np.pi
        for i in range(NR_CORE + 1):
            r = xi_core[i] * R_INNER
            x = float(r * np.sin(theta))
            y = float(-r * np.cos(theta) + R_OUTER + gap)
            nodes[nid] = (x, y)
            nid += 1
    core_node_count = NR_CORE + 1

    # TPU nodes: r = R_inner .. R_outer (share interface with core)
    # Interface nodes are the last column of core (i==NR_CORE)
    # We generate NEW nodes for TPU, but interface is shared => re-use core's last col
    # Store mapping: (j, i_tpu) -> node_id
    tpu_nodes_start = nid  # first new TPU node
    for j in range(NZ + 1):
        theta = eta_vals[j] * np.pi
        for i in range(1, NR_TPU + 1):  # skip i=0 (interface, already in core)
            r = R_INNER + xi_tpu[i] * (R_OUTER - R_INNER)
            x = float(r * np.sin(theta))
            y = float(-r * np.cos(theta) + R_OUTER + gap)
            nodes[nid] = (x, y)
            nid += 1

    # --- Elements ---
    quads_core, tris_core = [], []
    quads_tpu = []
    eid = 1

    # Core elements
    for j in range(NZ):
        for i in range(NR_CORE):
            n1 = j * core_node_count + i + 1
            n2 = n1 + 1
            n3 = n2 + core_node_count
            n4 = n1 + core_node_count
            if i == 0:
                tris_core.append((eid, n1, n2, n3))
            else:
                quads_core.append((eid, n1, n2, n3, n4))
            eid += 1

    # TPU elements — need to map (j, i_tpu) to node IDs
    def tpu_node(j, i_tpu):
        if i_tpu == 0:
            # interface node: last column of core
            return j * core_node_count + NR_CORE + 1
        else:
            return tpu_nodes_start + j * NR_TPU + (i_tpu - 1)

    for j in range(NZ):
        for i in range(NR_TPU):
            n1 = tpu_node(j, i)
            n2 = tpu_node(j, i + 1)
            n3 = tpu_node(j + 1, i + 1)
            n4 = tpu_node(j + 1, i)
            quads_tpu.append((eid, n1, n2, n3, n4))
            eid += 1

    # Node sets
    axis_nodes = [j * core_node_count + 1 for j in range(NZ + 1)]
    surf_nodes = [tpu_node(j, NR_TPU) for j in range(NZ + 1)]
    core_elsets = list(range(1, len(quads_core) + len(tris_core) + 1))
    tpu_elsets = [q[0] for q in quads_tpu]

    return (
        nodes,
        quads_core,
        tris_core,
        quads_tpu,
        axis_nodes,
        surf_nodes,
        core_elsets,
        tpu_elsets,
    )


def write_inp(
    filepath,
    nodes,
    quads_core,
    tris_core,
    quads_tpu,
    axis_nodes,
    surf_nodes,
    core_elsets,
    tpu_elsets,
):
    rigid_nid = max(nodes.keys()) + 1

    with open(filepath, "w") as f:
        f.write("*HEADING\n")
        f.write("Heel-Strike TPU-buffered: PLA core r=38mm + 2mm TPU-95A shell\n")
        f.write("V=0.759 m/s, M=2.5 kg, Explicit 10ms\n**\n")

        f.write("*NODE, NSET=ALLNODES\n")
        for nid in sorted(nodes):
            f.write("%d, %.8e, %.8e\n" % (nid, nodes[nid][0], nodes[nid][1]))

        f.write("*ELEMENT, TYPE=CAX4R, ELSET=CORE_QUADS\n")
        for e in quads_core:
            f.write("%d,%d,%d,%d,%d\n" % e)
        if tris_core:
            f.write("*ELEMENT, TYPE=CAX3, ELSET=CORE_TRIS\n")
            for e in tris_core:
                f.write("%d,%d,%d,%d\n" % e)
        f.write("*ELEMENT, TYPE=CAX4R, ELSET=TPU_QUADS\n")
        for e in quads_tpu:
            f.write("%d,%d,%d,%d,%d\n" % e)

        f.write("*ELSET, ELSET=CORE_ELS\nCORE_QUADS,\n")
        if tris_core:
            f.write("CORE_TRIS,\n")
        f.write("*ELSET, ELSET=ALL_HEEL\nCORE_ELS,\nTPU_QUADS,\n")

        f.write("*NSET, NSET=AXIS\n")
        _write_set(f, axis_nodes)
        f.write("*NSET, NSET=SURFACE_NODES\n")
        _write_set(f, surf_nodes)

        # Ground
        f.write("*NODE, NSET=GROUND_RP\n%d, 0.0, -0.001\n" % rigid_nid)
        f.write(
            "*SURFACE, TYPE=SEGMENTS, NAME=GROUND_SURF\nSTART,0.0,0.0\nLINE,0.15,0.0\n"
        )
        f.write(
            "*RIGID BODY, REF NODE=%d, ANALYTICAL SURFACE=GROUND_SURF\n" % rigid_nid
        )

        # PLA material
        f.write("*SOLID SECTION, ELSET=CORE_ELS, MATERIAL=PLA\n,\n")
        f.write("*MATERIAL, NAME=PLA\n*DENSITY\n1240.0,\n")
        f.write("*ELASTIC\n3500.0E6, 0.36\n")
        f.write("*PLASTIC\n60.0E6, 0.0\n72.0E6, 0.5\n")

        # TPU material
        f.write("*SOLID SECTION, ELSET=TPU_QUADS, MATERIAL=TPU\n,\n")
        f.write("*MATERIAL, NAME=TPU\n*DENSITY\n1120.0,\n")
        f.write("*ELASTIC\n26.0E6, 0.48\n")
        f.write("*PLASTIC\n8.6E6, 0.0\n10.3E6, 0.5\n")

        # Non-structural mass
        f.write(
            "*NONSTRUCTURAL MASS, ELSET=ALL_HEEL, UNITS=TOTAL MASS\n%.4f,\n"
            % EFFECTIVE_MASS
        )

        # Contact
        f.write("*SURFACE INTERACTION, NAME=FRIC\n*FRICTION\n%.2f,\n" % FRICTION)
        f.write("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD\n")

        # ICs & BCs
        f.write(
            "*INITIAL CONDITIONS, TYPE=VELOCITY\nALLNODES,1,0.0\nALLNODES,2,%.6f\n"
            % (-V_IMPACT)
        )
        f.write("*BOUNDARY\nGROUND_RP,1,2,0.0\nGROUND_RP,6,6,0.0\nAXIS,1,1,0.0\n")

        # Step
        f.write(
            "*STEP, NAME=Impact, NLGEOM=YES\n*DYNAMIC, EXPLICIT\n,%.6f\n" % T_ANALYSIS
        )
        f.write("*CONTACT\n*CONTACT INCLUSIONS, ALL EXTERIOR\n")
        f.write("*CONTACT PROPERTY ASSIGNMENT\n,,FRIC\n")
        f.write("*OUTPUT, FIELD, NUMBER INTERVAL=200\n*NODE OUTPUT\nU,V,A,RF\n")
        f.write("*ELEMENT OUTPUT\nS,LE,PEEQ,STATUS\n**\n")
        f.write("*OUTPUT, HISTORY, TIME INTERVAL=%.6e\n" % (T_ANALYSIS / 2000))
        f.write("*NODE OUTPUT, NSET=GROUND_RP\nRF1,RF2\n")
        f.write("*ENERGY OUTPUT\nALLKE,ALLIE,ALLPD,ALLSE,ETOTAL\n**\n*END STEP\n")


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    nodes, qc, tc, qt, ax, sf, ce, te = generate_bilayer_mesh()
    print(
        "TPU model: %d nodes, %d core quads, %d tris, %d TPU quads"
        % (len(nodes), len(qc), len(tc), len(qt))
    )
    inp = os.path.join(out_dir, "Job_HeelStrike_TPU.inp")
    write_inp(inp, nodes, qc, tc, qt, ax, sf, ce, te)
    print("Written: %s" % inp)
    print("Next: cd out && abaqus job=Job_HeelStrike_TPU cpus=4 interactive")


if __name__ == "__main__":
    main()

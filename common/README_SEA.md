# SEAActuator - Series Elastic Actuator Module

**Based on V15.1 SEA Direct-Drive Implementation**

## Overview

`SEAActuator` provides a reusable Python class for modeling Series Elastic Actuators (SEA) with configurable spring stiffness. It handles spring torque calculation, energy accounting, and MuJoCo XML generation.

## Features

- **Configurable stiffness**: k_sea from 500 (soft) to 10000 (rigid) N·m/rad
- **Automatic damping**: Subcritical damping (ζ=0.1) calculated automatically
- **Energy audit**: Tracks motor input, link output, damper loss, and spring PE
- **XML generation**: Creates MuJoCo model fragments for SEA topology
- **V15.1 validated**: Parameters match successful V15.1 experiments

## Files

```
hw-1/common/
├── sea_actuator.py              # Main module (SEAActuator, SEAParams)
├── sea_actuator_examples.py     # Usage examples and integration patterns
└── motor_dynamics.py            # L1 motor model (complementary)

hw-1/tests/unit/
└── test_sea_actuator.py         # Unit tests (23 tests, all passing)
```

## Quick Start

### Basic Usage

```python
from sea_actuator import SEAActuator, SEAParams, PRESETS

# Create SEA with soft spring (V15.1 optimal)
sea_params = PRESETS["v151_soft"]  # k=500 N·m/rad
left_hip = SEAActuator("left_hip", sea_params)

# Initialize before simulation
left_hip.initialize(q_link_initial=0.0)

# In simulation loop
for step in range(n_steps):
    # Get data from MuJoCo
    tau_motor = ...  # FSM output torque
    qd_motor = data.qvel[motor_dof]
    q_link = data.qpos[link_joint]
    qd_link = data.qvel[link_dof]
    
    # Update energy tracking
    left_hip.update_energy(tau_motor, qd_motor, q_link, qd_link, dt)

# After simulation
audit = left_hip.finalize_energy_audit(q_link_final)
print(f"Max deflection: {audit['q_link_max_deg']:.2f}°")
print(f"Motor input: {audit['W_motor_input_J']:.3f} J")
```

### Preset Configurations

| Preset | k_sea (N·m/rad) | Natural Freq | Use Case |
|--------|-----------------|--------------|----------|
| `v151_soft` | 500 | 56 Hz | Optimal compliance (V15.1: 4.92m forward) |
| `v151_medium` | 1000 | 80 Hz | Balanced performance |
| `v151_stiff` | 5000 | 178 Hz | High bandwidth control |
| `v151_rigid` | 10000 | 252 Hz | Rigid coupling (V14c degenerate test) |

## API Reference

### SEAParams

Configuration dataclass for SEA parameters.

**Attributes:**
- `k_sea`: Spring stiffness (N·m/rad), default 1000.0
- `c_sea`: Spring damping (N·m·s/rad), -1 = auto subcritical
- `motor_rotor_mass`: Rotor mass (kg), default 0.01
- `motor_rotor_iyy`: Rotor inertia (kg·m²), default 0.004
- `motor_rotor_ixy`: Rotor off-axis inertia (kg·m²), default 0.002
- `motor_bearing_damping`: Bearing damping (N·m·s/rad), default 0.001

**Methods:**
- `damping_resolved(I_rotor)`: Get resolved damping coefficient
- `spring_natural_frequency(I_rotor)`: Calculate ω_n (rad/s)
- `damping_ratio(I_rotor)`: Calculate ζ (dimensionless)
- `recommended_timestep()`: Get recommended MuJoCo timestep (s)

### SEAActuator

Main actuator class for simulation integration.

**Constructor:**
```python
SEAActuator(name: str, params: SEAParams)
```

**Key Methods:**

#### `initialize(q_link_initial: float)`
Must be called before simulation. Sets initial spring PE for energy balance.

#### `compute_spring_torque(q_link: float, qd_link: float) -> float`
Calculate spring torque: `τ = -k*q - c*qd`

#### `update_energy(tau_motor, qd_motor, q_link, qd_link, dt)`
Update energy statistics (call every timestep).

#### `finalize_energy_audit(q_link_final: float) -> dict`
Generate final energy report after simulation.

**Energy Audit Fields:**
- `W_motor_input_J`: Total motor input work
- `W_link_useful_J`: Work transmitted to link (stiffness term only)
- `W_damper_loss_J`: Energy dissipated in damper
- `dPE_spring_J`: Change in spring potential energy
- `q_link_max_deg`: Maximum spring deflection
- `energy_balance_error_pct`: Energy conservation check

## Physics Model

### SEA Topology

```
hip_body
└─ motor_rotor (actuated, mass=0.01 kg, I_yy=0.004 kg·m²)
   ├─ joint: hip_motor (controlled by FSM, ±4 N·m)
   └─ thigh_link
      ├─ joint: hip_link (series spring: k_sea, c_sea)
      └─ shank → foot
```

### Spring Dynamics

**Torque:**
```
τ_spring = -k_sea * q_link - c_sea * qd_link
```

**Potential Energy:**
```
PE_spring = 0.5 * k_sea * q_link²
```

**Automatic Damping (c_sea < 0):**
```
c_sea = 0.1 × 2 × √(k_sea × I_rotor)
ζ = 0.1 (underdamped, fast response with damping)
```

### Energy Balance

```
W_motor_input ≈ W_link_useful + W_damper_loss + ΔPE_spring
```

Where:
- `W_motor_input = ∫ τ_motor · ω_motor dt`
- `W_link_useful = ∫ (-k*q) · ω_link dt` (conservative)
- `W_damper_loss = ∫ c · ω_link² dt` (dissipative)
- `ΔPE_spring = PE_final - PE_initial`

## V15.1 Integration

### Differences from V14c (Rigid)

| Aspect | V14c Rigid | V15.1 SEA |
|--------|------------|-----------|
| Hip DOF | 1 (hip joint) | 2 (motor + link) |
| nq | 7 | 12 |
| Spring | N/A | k=500-10000 N·m/rad |
| Deflection | 0° | 0.02-1.6° (k-dependent) |
| FSM Input | Direct hip angle | Absolute (motor+link) |

### Key V15.1 Findings

1. **Degeneration Test** (k=10000 N·m/rad):
   - Forward: 4.87m (V14c: 4.62m, +5.6%)
   - Success: ✓ (validates implementation)

2. **Optimal Configuration** (k=500 N·m/rad):
   - Forward: 4.92m (best in slice C)
   - Deflection: ~1.6° (visible in videos)
   - Success rate: 8.3% (3/36, slice C)

3. **Resonance Band** (k=1000 N·m/rad):
   - Non-monotonic failures (similar to V16 τ_C)
   - Highlights FSM-spring coupling dynamics

## MuJoCo XML Generation

```python
from sea_actuator import build_sea_xml_fragment, PRESETS

xml_left = build_sea_xml_fragment(
    side="left",
    params=PRESETS["v151_soft"],
    lateral_offset=-0.055,
    hip_torque_limit=4.0
)

# Insert into hip body in model XML
```

**Generated Structure:**
```xml
<body name="left_motor_rotor" pos="0 -0.055 0">
  <inertial pos="0 0 0" mass="0.01" diaginertia="0.002 0.004 0.002"/>
  <joint name="left_hip_motor" type="hinge" axis="0 1 0" 
         range="-95 95" limited="true" armature="0" damping="0.001"/>
  <body name="left_thigh" pos="0 0 0">
    <joint name="left_hip_link" type="hinge" axis="0 1 0" 
           range="-95 95" limited="true" armature="0" 
           damping="0.2828" stiffness="500.0" springref="0"/>
    <!-- thigh content -->
  </body>
</body>
```

## Testing

Run unit tests:
```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m pytest .\tests\unit\test_sea_actuator.py -v
```

**Test Coverage:**
- Parameter resolution (damping, frequency, timestep)
- Spring torque calculation
- Energy accounting
- Preset configurations
- V15.1 integration validation
- XML generation

**Result:** 23/23 tests passing

## Examples

Run examples:
```powershell
.\.venv-mujoco\Scripts\python.exe .\common\sea_actuator_examples.py
```

Examples include:
1. Basic usage with energy audit
2. Stiffness comparison (k=500 to k=10000)
3. V15.1 simulation integration pattern
4. MuJoCo XML generation

## Design Decisions

### Why separate stiffness and damping terms in energy accounting?

The spring torque τ = -k*q - c*qd has two components:
- `-k*q`: Conservative (stores/releases energy in spring)
- `-c*qd`: Dissipative (converts to heat)

To avoid double-counting, `W_link_useful` only includes the stiffness term, while `W_damper_loss` tracks dissipation separately.

### Why ζ=0.1 (10% damping)?

Underdamped (ζ<1) provides fast response while suppressing high-frequency oscillations. V15.1 experiments validated this value across all stiffness settings.

### Why auto-damping by default?

Ensures subcritical damping scales with stiffness. As k↑, natural frequency ω_n↑, so c must also ↑ to maintain ζ=0.1.

## Related Modules

- **`motor_dynamics.py`**: L1 motor model (V16+), handles Coulomb friction and current saturation
- **`simulate_v151.py`**: Reference implementation showing SEA integration with MuJoCo

## References

- V15.1 README: `D:\Dunna\Documents\hw-1\v15_1_sea_direct\README.md`
- V15.1 Simulation: `D:\Dunna\Documents\hw-1\v15_1_sea_direct\simulate_v151.py`
- MuJoCo XML: `<joint stiffness>` and `<joint damping>` documentation

## Version History

- **2026-06-08**: Initial implementation based on V15.1
  - SEAParams with auto-damping
  - SEAActuator with energy audit
  - 4 preset configurations
  - 23 unit tests (all passing)
  - Integration examples

## License

Part of hw-1 gait rehabilitation device project.

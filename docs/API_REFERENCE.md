# API Reference

Complete API documentation for the hw-1 gait rehabilitation device project.

## Table of Contents

- [Core Classes](#core-classes)
  - [FSMController](#fsmcontroller)
  - [CompassGait](#compassgait)
  - [SEAActuator](#seaactuator)
  - [Controller (Abstract)](#controller-abstract)
- [Data Classes](#data-classes)
  - [PhaseParams](#phaseparams)
  - [FSMParams](#fsmparams)
  - [BaseGaitParams](#basegaitparams)
  - [CompassGaitParams](#compassgaitparams)
  - [SEAParams](#seaparams)
  - [ContactState](#contactstate)
  - [EnergyStats](#energystats)
  - [PhaseTracker](#phasetracker)
- [Terrain Generation](#terrain-generation)
- [Simulation Framework](#simulation-framework)

---

## Core Classes

### FSMController

Finite state machine gait controller implementing 4-phase FSM control with per-phase gains and energy shaping.

**Location:** `common/fsm_controller.py`

#### Constructor

```python
FSMController(
    fsm_params: FSMParams,
    base_params: BaseGaitParams,
    knee_kp: float = 16.0,
    knee_kd: float = 2.0,
    knee_torque_limit: float = 4.0,
    swing_knee_flex_deg: float = 30.0,
    stance_knee_deg: float = 0.0
)
```

**Parameters:**
- `fsm_params`: Per-phase FSM control parameters
- `base_params`: Base gait parameters (timing, targets, terrain)
- `knee_kp`: Knee PD proportional gain (default: 16.0)
- `knee_kd`: Knee PD derivative gain (default: 2.0)
- `knee_torque_limit`: Knee torque saturation limit in N·m (default: 4.0)
- `swing_knee_flex_deg`: Peak knee flexion during swing in degrees (default: 30.0)
- `stance_knee_deg`: Knee angle during stance in degrees (default: 0.0)

#### Class Methods

##### `from_v136(cls, v136_params, v10_base_params) -> FSMController`

Factory method to create FSMController from V13.6 parameters.

**Parameters:**
- `v136_params`: V136Params object from simulate_v13_6.py
- `v10_base_params`: RollingFootParams (V10Params) base configuration

**Returns:** FSMController instance

##### `from_v137(cls, v137_params) -> FSMController`

Factory method to create FSMController from V13.7 parameters.

**Parameters:**
- `v137_params`: V137Params object from simulate_v13_7.py

**Returns:** FSMController instance

#### Instance Methods

##### `mechanical_energy(data: mujoco.MjData) -> float`

Calculate total mechanical energy (kinetic + potential).

**Parameters:**
- `data`: MuJoCo data structure

**Returns:** Total mechanical energy in Joules

##### `compute_control(data, t, support_foot, burst_start_t, E_current=None) -> tuple`

Compute FSM control outputs for all joints.

**Parameters:**
- `data`: MuJoCo data structure
- `t`: Current simulation time
- `support_foot`: "left" or "right"
- `burst_start_t`: Time of last contact event
- `E_current`: Current mechanical energy (computed if None)

**Returns:** Tuple of:
- `l_hip_tau`: Left hip torque (N·m)
- `l_knee_tau`: Left knee torque (N·m)
- `r_hip_tau`: Right hip torque (N·m)
- `r_knee_tau`: Right knee torque (N·m)
- `mode_label`: Control mode string
- `left_phase`: Left leg phase name
- `right_phase`: Right leg phase name
- `e_E_swing`: Energy error from swing thrust phase (J)
- `A_swing`: Energy drive amplitude (N·m)

---

### CompassGait

Compass gait model with MuJoCo integration, supporting both kinematic playback and hybrid dynamics simulation.

**Location:** `common/compass_gait.py`

#### Constructor

```python
CompassGait(params: CompassGaitParams)
```

**Parameters:**
- `params`: Model parameters

#### Class Methods

##### `from_template(cls, template: str) -> CompassGait`

Create from template configuration.

**Parameters:**
- `template`: Template name - "kinematic", "hybrid", "steep", "gentle", "fast", "slow"

**Returns:** CompassGait instance

#### Instance Methods

##### `load_mujoco_model(xml_path: Path | str) -> None`

Load MuJoCo model from XML file.

**Parameters:**
- `xml_path`: Path to MuJoCo XML model file

##### `ramp_height(x: float) -> float`

Compute ramp height at position x.

**Parameters:**
- `x`: Position along ramp (m)

**Returns:** Height (m)

##### `foot_position(hip_x: float, hip_z: float, theta: float) -> tuple[float, float]`

Compute foot position given hip position and leg angle.

**Parameters:**
- `hip_x`: Hip x position (m)
- `hip_z`: Hip z position (m)
- `theta`: Leg angle in radians (positive = forward)

**Returns:** Tuple of (foot_x, foot_z) in meters

##### `foot_clearance(hip_x: float, hip_z: float, theta: float) -> float`

Compute foot clearance above ramp.

**Parameters:**
- `hip_x`: Hip x position (m)
- `hip_z`: Hip z position (m)
- `theta`: Leg angle in radians

**Returns:** Clearance in meters (negative if penetrating)

##### `simulate_kinematic() -> tuple[list[dict], list[dict]]`

Run kinematic limit-cycle simulation (v03-style).

**Returns:** Tuple of:
- `trajectory_rows`: List of state dictionaries
- `poincare_points`: List of Poincaré section points

##### `simulate_hybrid() -> tuple[list[dict], list[dict]]`

Run hybrid dynamics simulation (v05-style).

**Returns:** Tuple of:
- `trajectory_rows`: List of state dictionaries
- `poincare_points`: List of Poincaré section points

##### `set_mujoco_state(state: dict[str, float]) -> None`

Set MuJoCo model state from trajectory row.

**Parameters:**
- `state`: State dictionary from simulate_kinematic or simulate_hybrid

---

### SEAActuator

Series Elastic Actuator (SEA) class managing single joint state, torque calculation, and energy auditing.

**Location:** `common/sea_actuator.py`

#### Constructor

```python
SEAActuator(name: str, params: SEAParams)
```

**Parameters:**
- `name`: Joint name (e.g., "left_hip", "right_hip")
- `params`: SEA parameter configuration

#### Instance Methods

##### `initialize(q_link_initial: float) -> None`

Initialize energy audit with initial spring potential energy.

**Parameters:**
- `q_link_initial`: Initial spring deflection angle in radians (usually 0)

##### `compute_spring_torque(q_link: float, qd_link: float) -> float`

Calculate spring torque acting on the link.

**Formula:** τ_spring = -k_sea × q_link - c_sea × qd_link

**Parameters:**
- `q_link`: Spring deflection angle (rad)
- `qd_link`: Spring deflection angular velocity (rad/s)

**Returns:** Spring torque in N·m

##### `compute_spring_pe(q_link: float) -> float`

Calculate spring elastic potential energy.

**Formula:** PE = 0.5 × k_sea × q_link²

**Parameters:**
- `q_link`: Spring deflection angle (rad)

**Returns:** Potential energy in Joules

##### `update_energy(tau_motor, qd_motor, q_link, qd_link, dt) -> None`

Update energy audit statistics (call each timestep).

**Parameters:**
- `tau_motor`: Motor actual output torque (N·m)
- `qd_motor`: Motor angular velocity (rad/s)
- `q_link`: Spring deflection angle (rad)
- `qd_link`: Spring deflection angular velocity (rad/s)
- `dt`: Timestep (s)

##### `get_energy_audit() -> dict`

Get energy audit report.

**Returns:** Dictionary with keys:
- `W_motor_input_J`: Motor input work (J)
- `W_link_useful_J`: Link received work (J)
- `W_damper_loss_J`: Damping dissipation (J)
- `dPE_spring_J`: Spring potential energy change (J)
- `PE_spring_initial_J`: Initial spring PE (J)
- `PE_spring_final_J`: Final spring PE (J)
- `spring_pe_max_J`: Maximum spring PE (J)
- `spring_pe_mean_J`: Average spring PE (J)
- `q_link_max_deg`: Maximum deflection angle (degrees)
- `energy_balance_error_J`: Energy balance error (J)
- `energy_balance_error_pct`: Energy balance error (%)

##### `finalize_energy_audit(q_link_final: float) -> dict`

Complete energy audit with accurate final PE.

**Parameters:**
- `q_link_final`: Final spring deflection angle (rad)

**Returns:** Energy audit report dictionary (same as get_energy_audit)

##### `reset() -> None`

Reset energy audit statistics.

---

### Controller (Abstract)

Abstract base class for controllers.

**Location:** `common/controllers.py`

#### Abstract Methods

##### `compute_torque(q, qd, target=None, **kwargs) -> float`

Calculate control torque.

**Parameters:**
- `q`: Current joint position (rad)
- `qd`: Current joint velocity (rad/s)
- `target`: Target joint position (rad), optional for passive controllers
- `**kwargs`: Additional control parameters (e.g., kp, kd)

**Returns:** Control torque in N·m

#### Instance Methods

##### `reset() -> None`

Reset controller state (optional implementation for stateful controllers).

---

### PassiveController

Passive controller (zero torque output).

**Location:** `common/controllers.py`

**Inherits:** Controller

#### Constructor

```python
PassiveController()
```

#### Instance Methods

##### `compute_torque(q, qd, target=None, **kwargs) -> float`

Always returns 0.0.

---

### PDController

Standard PD (Proportional-Derivative) controller.

**Location:** `common/controllers.py`

**Inherits:** Controller

**Formula:** τ = Kp × (target - q) - Kd × qd

#### Constructor

```python
PDController(kp: float = 100.0, kd: float = 10.0, torque_limit: float | None = None)
```

**Parameters:**
- `kp`: Proportional gain (N·m/rad), default 100.0
- `kd`: Derivative gain (N·m·s/rad), default 10.0
- `torque_limit`: Torque limit magnitude (N·m), None for unlimited

#### Instance Methods

##### `compute_torque(q, qd, target=None, **kwargs) -> float`

Compute PD control torque.

**Parameters:**
- `q`: Current joint position (rad)
- `qd`: Current joint velocity (rad/s)
- `target`: Target joint position (rad), required
- `**kwargs`: Optional temporary parameter overrides (kp, kd, torque_limit)

**Returns:** Control torque in N·m (clipped if torque_limit set)

##### `set_gains(kp: float | None = None, kd: float | None = None) -> None`

Update control gains.

**Parameters:**
- `kp`: New proportional gain (None to keep unchanged)
- `kd`: New derivative gain (None to keep unchanged)

---

## Data Classes

### PhaseParams

Per-phase control parameters for FSM gait controller.

**Location:** `common/fsm_controller.py`

**Attributes:**
- `k_E` (float): Energy shaping gain (0 = PD-only, >0 = energy-based)
- `k_PD` (float): Proportional gain for position tracking
- `tau_max` (float): Torque saturation limit (N·m)
- `kd` (float): Derivative (damping) gain, default 6.0
- `E_target` (float): Target mechanical energy (J), default 52.66

---

### FSMParams

Complete FSM controller parameters for 4-phase gait control.

**Location:** `common/fsm_controller.py`

**Phases:**
- `stance_early`: 0-50% of support phase (strong PD tracking)
- `stance_late`: 50-100% of support phase (push-off preparation)
- `swing_thrust`: 0-50% of swing phase (energy injection)
- `swing_retract`: 50-100% of swing phase (passive return)

**Attributes:**
- `stance_early` (PhaseParams): Default: k_E=0.0, k_PD=30.0, tau_max=4.0
- `stance_late` (PhaseParams): Default: k_E=0.0, k_PD=30.0, tau_max=4.0
- `swing_thrust` (PhaseParams): Default: k_E=7.5, k_PD=10.0, tau_max=4.0
- `swing_retract` (PhaseParams): Default: k_E=0.0, k_PD=30.0, tau_max=2.0

---

### BaseGaitParams

Base gait parameters needed for FSM controller.

**Location:** `common/fsm_controller.py`

**Attributes:**
- `gait_period` (float): Gait period (s), default 0.80
- `gamma` (float): Hip angle offset (rad), default 0.0
- `stance_front_deg` (float): Front stance angle (deg), default 0.0
- `stance_back_deg` (float): Back stance angle (deg), default 0.0
- `swing_back_deg` (float): Back swing angle (deg), default 0.0
- `swing_front_deg` (float): Front swing angle (deg), default 0.0
- `recovery_clearance` (float): Hip height recovery threshold (m), default 0.38
- `slope_deg` (float): Terrain slope (deg), default 0.0
- `hip_mass` (float): Hip mass (kg), default 1.0
- `torso_mass` (float): Torso mass (kg), default 0.05

---

### CompassGaitParams

Compass gait model parameters supporting both kinematic and hybrid dynamics modes.

**Location:** `common/compass_gait.py`

**Attributes:**
- `slope_deg` (float): Slope angle (deg), default 5.0
- `leg_length` (float): Leg length (m), default 1.0
- `foot_radius` (float): Foot radius (m), default 0.04
- `step_length` (float): Step length for kinematic mode (m), default 0.34
- `step_angle_deg` (float): Step angle for hybrid mode (deg), default 10.0
- `gravity` (float): Gravity (m/s²), default 9.81
- `stance_damping` (float): Stance damping, default 0.012
- `swing_damping` (float): Swing damping, default 0.035
- `passive_hip_stiffness` (float): Passive hip stiffness, default 0.42
- `collision_retention` (float): Collision retention coefficient, default 0.82
- `energy_gain_scale` (float): Energy gain scale, default 0.42
- `initial_speed` (float): Initial speed (m/s), default 0.24
- `fixed_speed` (float | None): Fixed-point speed (auto-computed if None)
- `convergence` (float): Convergence rate for kinematic mode, default 0.58
- `steps` (int): Number of steps, default 32
- `dt` (float): Timestep (s), default 0.002
- `samples_per_step` (int): Samples per step, default 120

**Properties:**
- `alpha`: Half step angle (rad)
- `alpha_hybrid`: Half step angle for hybrid mode (rad)
- `gamma`: Slope angle (rad)
- `computed_fixed_speed`: Fixed-point speed for hybrid mode (m/s)

**Methods:**
- `to_dict() -> dict`: Convert to dictionary with computed properties
- `from_template(cls, template: str) -> CompassGaitParams`: Factory for common configurations

---

### SEAParams

Series Elastic Actuator parameter configuration.

**Location:** `common/sea_actuator.py`

**Attributes:**
- `k_sea` (float): Spring stiffness (N·m/rad), default 1000.0
  - 500: Soft (max deflection ~1.6°)
  - 1000-5000: Medium stiffness
  - 10000: Near-rigid (degrades to direct drive)
- `c_sea` (float): Spring damping (N·m·s/rad), default -1.0
  - If <0: auto-compute subcritical damping = 0.1 × 2√(k_sea × I_rotor)
  - If ≥0: use specified value
- `motor_rotor_mass` (float): Motor rotor mass (kg), default 0.01
- `motor_rotor_iyy` (float): Motor rotor y-axis inertia (kg·m²), default 0.004
- `motor_rotor_ixy` (float): Motor rotor x/z-axis inertia (kg·m²), default 0.002
- `motor_bearing_damping` (float): Motor bearing damping (N·m·s/rad), default 0.001

**Methods:**
- `damping_resolved(I_rotor: float | None = None) -> float`: Resolve damping coefficient
- `spring_natural_frequency(I_rotor: float | None = None) -> float`: Calculate natural frequency (rad/s)
- `damping_ratio(I_rotor: float | None = None) -> float`: Calculate damping ratio ζ
- `recommended_timestep() -> float`: Recommend simulation timestep (s)

---

### ContactState

Contact state tracker for debouncing and event detection.

**Location:** `common/simulation_framework.py`

**Attributes:**
- `stable_contact_time` (float): Stable contact duration threshold (s), default 0.035
- `min_event_interval` (float): Minimum event interval for debouncing (s), default 0.22
- `candidate_start_t` (dict): Contact candidate start times
- `contact_reported` (dict): Contact reported flags
- `last_event_t` (float): Last event time
- `accepted_contact` (str): Currently accepted contact foot
- `support_foot` (str): Current support foot
- `alternations` (int): Contact alternation count
- `contact_events` (list): Contact event history

---

### EnergyStats

Energy and power statistics container.

**Location:** `common/simulation_framework.py`

**Attributes:**
- `positive_input_energy` (float): Positive work accumulation (J), default 0.0
- `net_work` (float): Net work (J), default 0.0
- `positive_input_energy_elec` (float): Electrical power accumulation (J), default 0.0
- `coulomb_dissipation` (float): Coulomb friction dissipation (J), default 0.0

**Methods:**
- `update(input_power, timestep, *, resistive_power=0.0, coulomb_power=0.0) -> None`

---

### PhaseTracker

Phase timeline tracker for FSM control.

**Location:** `common/simulation_framework.py`

**Attributes:**
- `phase_names` (tuple): Phase name tuple
- `phase_timeline` (list): Phase timeline records
- `last_left_phase` (str): Last left leg phase
- `last_right_phase` (str): Last right leg phase
- `phase_durations` (dict): Phase duration statistics
- `phase_torque_int` (dict): Phase torque integrals
- `phase_saturation_steps` (dict): Phase saturation step counts
- `phase_total_steps` (dict): Phase total step counts

**Methods:**
- `update(t, left_phase, right_phase, timestep, *, left_hip_tau=0.0, right_hip_tau=0.0, hip_saturated=False) -> None`

---

## Terrain Generation

Functions for generating rugged terrain using MuJoCo hfield.

**Location:** `common/terrain.py`

### `build_rugged_assets_xml(amplitude_m: float, length_m: float = 90.0, width_m: float = 3.6) -> str`

Generate hfield asset declaration for insertion into `<asset>` block.

**Parameters:**
- `amplitude_m`: Terrain amplitude (m), returns empty string if 0
- `length_m`: Terrain length (m), default 90.0
- `width_m`: Terrain width (m), default 3.6

**Returns:** XML string for hfield declaration

### `build_rugged_geom_xml(amplitude_m: float, slope_deg: float = 0.0) -> str`

Generate ramp geom XML. Returns plane if amplitude=0, hfield otherwise.

**Parameters:**
- `amplitude_m`: Terrain amplitude (m)
- `slope_deg`: Slope angle (deg), default 0.0

**Returns:** XML string for geom element (always named "ramp")

### `generate_profile(amplitude_m: float, wavelength_m: float, length_m: float, seed: int) -> np.ndarray`

Generate normalized height array for hfield.

**Parameters:**
- `amplitude_m`: Terrain amplitude (m)
- `wavelength_m`: Base wavelength (m)
- `length_m`: Terrain length (m)
- `seed`: Random seed

**Returns:** (HFIELD_NROW, HFIELD_NCOL) array with values in [0, 1]

### `fill_hfield_data(model, profile: np.ndarray) -> None`

Write generated profile into model.hfield_data.

**Parameters:**
- `model`: MuJoCo model
- `profile`: Height array (nrow, ncol) with values in [0, 1]

---

## Simulation Framework

Enhanced simulation framework with contact detection, energy statistics, and FSM support.

**Location:** `common/simulation_framework.py`

### `update_contact_state(state, t, left_contact, right_contact, extra_data=None) -> list[str]`

Update contact state and return newly stable contact feet.

**Parameters:**
- `state`: ContactState object (modified in-place)
- `t`: Current time (s)
- `left_contact`: Left foot contact boolean
- `right_contact`: Right foot contact boolean
- `extra_data`: Extra data to record in contact_events

**Returns:** List of newly stable contact feet

### DictRowRecorder

Dictionary row recorder callback for simulation data collection.

**Constructor:**
```python
DictRowRecorder(
    *,
    row_builder: Callable,
    sample_hz: float = 160.0,
    context: dict[str, Any] | None = None
)
```

**Parameters:**
- `row_builder`: Function (model, data, t, context) -> dict
- `sample_hz`: Sampling frequency (Hz), default 160.0
- `context`: Context dictionary passed to row_builder

**Methods:**
- `get_rows() -> list[dict]`: Return recorded rows

### IntegratedSimulationCallback

Integrated callback for control, contact detection, and energy statistics.

**Constructor:**
```python
IntegratedSimulationCallback(
    controller: Controller,
    contact_detector: Callable,
    *,
    contact_state: ContactState | None = None,
    energy_stats: EnergyStats | None = None,
    phase_tracker: PhaseTracker | None = None,
    context: dict[str, Any] | None = None
)
```

**Parameters:**
- `controller`: Controller instance
- `contact_detector`: Function (model, data) -> (left_contact, right_contact)
- `contact_state`: ContactState tracker
- `energy_stats`: EnergyStats container
- `phase_tracker`: PhaseTracker (optional for FSM)
- `context`: Shared context dictionary

### FailureClassifier

Generic failure classifier for early stopping.

**Constructor:**
```python
FailureClassifier(
    classify_fn: Callable,
    context: dict[str, Any]
)
```

**Parameters:**
- `classify_fn`: Function (model, data, t, context) -> failure_reason
- `context`: Context dictionary with start_x, etc.

---

## Utility Functions

### `smoothstep(u: float) -> float`

Smooth interpolation function with C1 continuity.

**Formula:** s(u) = 3u² - 2u³

**Parameters:**
- `u`: Input value (clamped to [0, 1])

**Returns:** Smoothly interpolated value in [0, 1]

### `ramp_height(x: float, params: BaseGaitParams) -> float`

Calculate ground height at position x for sloped terrain.

**Parameters:**
- `x`: Position along ground (m)
- `params`: BaseGaitParams with slope_deg

**Returns:** Height (m)

---

## Presets

### SEA Presets

**Location:** `common/sea_actuator.py`

Available presets in `PRESETS` dict:
- `"v151_soft"`: k_sea=500, soft configuration
- `"v151_medium"`: k_sea=1000, medium stiffness
- `"v151_stiff"`: k_sea=5000, stiff configuration
- `"v151_rigid"`: k_sea=10000, near-rigid (degrades to direct drive)

---

## Constants

### Terrain Constants

**Location:** `common/terrain.py`

- `HFIELD_NAME` = "rugged_terrain"
- `HFIELD_NROW` = 8 (y direction, kept flat)
- `HFIELD_NCOL` = 256 (x direction, densely sampled)

### Physics Constants

**Location:** `common/fsm_controller.py`

- `G` = 9.81 (m/s², gravitational acceleration)

---

## Version History

Based on hw-1 project versions V01-V19:
- V01-V05: Compass gait foundations
- V10: Rolling foot biomimetic gait
- V13.6: Event-driven FSM
- V13.7: Friction compensation
- V14: State machine hip control
- V15: SEA (Series Elastic Actuator)
- V16: Motor dynamics
- V17: State estimation

---

## Related Files

- `common/simulation_runner.py`: Base simulation runner
- `common/energy_metrics.py`: Energy metrics and CoT calculation
- `common/poincare_analyzer.py`: Poincaré analysis tools
- `common/motor_dynamics.py`: Motor dynamics models
- `common/model_loader.py`: MuJoCo model loading utilities

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-08  
**Project:** hw-1 Gait Rehabilitation Device

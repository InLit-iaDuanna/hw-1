# RollingFootGait Model Documentation

## Overview

The `RollingFootGait` model is a reusable implementation of a biped walker with heel-toe rolling capability, based on the v10 implementation. It provides a clean, object-oriented interface for creating, simulating, and analyzing biomimetic walking gaits with passive foot rolling mechanics.

## Features

- **Heel-toe-toe geometry**: Separate contact points for heel, sole, and toe enable natural rolling motion
- **Passive ankle joint**: Spring-damper ankle joint allows compliant foot-ground interaction
- **Quasi-passive control**: Minimal actuation with PD controllers on hip and knee joints
- **Event-driven phase transitions**: Automatic detection of contact events with anti-bounce filtering
- **Comprehensive contact detection**: Track individual heel, sole, and toe contacts
- **Failure classification**: Automatic detection of common failure modes
- **Configurable parameters**: Easy customization of geometry, dynamics, and control

## Installation

The model is located in `common/rolling_foot_gait.py` and requires:
- Python 3.8+
- MuJoCo (mujoco package)
- NumPy

## Quick Start

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams

# Create model with default parameters
params = RollingFootParams()
gait = RollingFootGait(params)

# Initialize the model
gait.initialize()

# Access MuJoCo model and data
model = gait.model
data = gait.data

# Run simulation step
t = 0.0
support_foot = "left"
burst_start_t = 0.0

# Compute control
tau = gait.compute_control(t, support_foot, burst_start_t)
data.ctrl[:] = tau[:4]

# Step forward
import mujoco
mujoco.mj_step(model, data)

# Check contacts
left_contact, right_contact = gait.contact_flags()
detail = gait.foot_contact_detail()

# Check for failure
failure = gait.classify_failure(start_x=0.0, t=t)
```

## Class Reference

### RollingFootParams

Parameter dataclass for configuring the model.

#### Terrain Parameters
- `slope_deg` (float, default=0.0): Ramp slope in degrees
- `friction` (float, default=1.35): Ground friction coefficient

#### Foot Geometry
- `foot_radius` (float, default=0.04): Heel radius in meters
- `foot_length` (float, default=0.16): Total foot length in meters
- `toe_radius` (float, default=0.028): Toe radius in meters (smaller for natural roll-off)

#### Leg Dimensions
- `thigh_length` (float, default=0.48): Thigh length in meters
- `shank_length` (float, default=0.52): Shank length in meters
- `leg_length` (property): Total leg length = thigh + shank

#### Masses
- `hip_mass` (float, default=5.0): Hip mass in kg
- `torso_mass` (float, default=0.2): Torso mass in kg
- `torso_height` (float, default=0.30): Torso height in meters

#### Joint Limits and Passive Dynamics
- `ankle_limit_deg` (float, default=25.0): Ankle joint limit in degrees
- `ankle_damping` (float, default=0.08): Ankle damping coefficient
- `ankle_stiffness` (float, default=0.55): Ankle spring stiffness
- `knee_limit_deg` (float, default=70.0): Knee joint limit in degrees
- `knee_damping` (float, default=0.08): Knee damping coefficient
- `knee_stiffness` (float, default=0.8): Knee spring stiffness
- `hip_joint_damping` (float, default=0.02): Hip joint damping
- `joint_damping` (float, default=0.01): Default joint damping

#### Control Parameters
- `hip_kp` (float, default=18.0): Hip PD proportional gain
- `hip_kd` (float, default=4.0): Hip PD derivative gain
- `knee_kp` (float, default=10.0): Knee PD proportional gain
- `knee_kd` (float, default=1.2): Knee PD derivative gain
- `hip_torque_limit` (float, default=8.0): Maximum hip torque in Nm
- `knee_torque_limit` (float, default=2.0): Maximum knee torque in Nm

#### Gait Timing and Targets
- `gait_period` (float, default=1.00): Gait cycle period in seconds
- `swing_back_deg` (float, default=20.0): Swing leg starting angle
- `swing_front_deg` (float, default=-22.0): Swing leg ending angle
- `stance_front_deg` (float, default=-14.0): Stance leg starting angle
- `stance_back_deg` (float, default=22.0): Stance leg ending angle
- `swing_knee_flex_deg` (float, default=28.0): Maximum swing knee flexion
- `stance_knee_deg` (float, default=2.0): Stance knee angle

#### Initialization
- `initial_vx` (float, default=0.04): Initial forward velocity
- `step_length` (float, default=0.34): Target step length
- `release_phase` (float, default=0.08): Initial release phase (0-1)
- `swing_foot_x` (float, default=0.38): Swing foot x position
- `swing_foot_clearance` (float, default=0.12): Swing foot clearance
- `swing_hip_vel` (float, default=0.10): Initial swing hip velocity
- `swing_knee_vel` (float, default=-0.04): Initial swing knee velocity

#### Contact Detection
- `min_event_interval` (float, default=0.22): Minimum time between contact events
- `stable_contact_time` (float, default=0.035): Required stable contact duration
- `recovery_clearance` (float, default=0.38): Hip clearance threshold for recovery mode

#### Simulation
- `timestep` (float, default=0.001): Simulation timestep in seconds
- `duration` (float, default=12.0): Default simulation duration in seconds

### RollingFootGait

Main model class encapsulating the biped walker.

#### Properties

- `model` (mujoco.MjModel): MuJoCo model (built on first access)
- `data` (mujoco.MjData): MuJoCo data structure (created on first access)
- `params` (RollingFootParams): Model parameters

#### Methods

##### `__init__(params: RollingFootParams)`
Initialize the RollingFootGait model with given parameters.

##### `initialize() -> None`
Initialize the model state using inverse kinematics. Sets initial positions and velocities based on parameters.

##### `reset() -> None`
Reset the simulation state and reinitialize.

##### Geometry Utilities

###### `ramp_height(x: float) -> float`
Calculate ramp height at position x.

###### `foot_center_z_on_ramp(x: float) -> float`
Calculate foot center z-coordinate on ramp at position x.

###### `smoothstep(u: float) -> float`
Smoothstep interpolation function (0 <= u <= 1).

###### `leg_ik_front_knee(hip_x, hip_z, foot_x, foot_z) -> tuple[float, float]`
Inverse kinematics for front-knee leg configuration.
Returns: (hip_angle, knee_angle) in radians

##### Contact Detection

###### `foot_contact_detail() -> dict[str, bool]`
Get detailed contact information for each foot segment.
Returns dict with keys: `left_heel`, `left_sole`, `left_toe`, `right_heel`, `right_sole`, `right_toe`

###### `contact_flags() -> tuple[bool, bool]`
Get overall contact flags for left and right feet.
Returns: (left_contact, right_contact)

###### `site_margin(site_name: str) -> float`
Calculate margin (clearance) for a site above the ramp.

##### Control

###### `compute_control(t, support_foot, burst_start_t) -> tuple[float, float, float, float, str]`
Compute control torques based on current state.

**Args:**
- `t` (float): Current time
- `support_foot` (str): Which foot is currently supporting ("left" or "right")
- `burst_start_t` (float): Time when current gait cycle started

**Returns:**
- Tuple of (left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode)

##### Failure Detection

###### `classify_failure(start_x: float, t: float) -> str`
Classify failure mode based on current state.

**Returns:**
- Empty string if no failure
- "nan_or_unstable": Non-finite states or excessive velocity
- "fall_down": Hip too low
- "fly_away": Hip too high
- "penetration": Foot penetrating ground
- "stuck": Not making forward progress

## Usage Examples

### Example 1: Basic Simulation

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams
import mujoco

# Create and initialize model
params = RollingFootParams(duration=10.0)
gait = RollingFootGait(params)
gait.initialize()

# Simulation loop
support_foot = "left"
burst_start_t = 0.0
start_x = float(gait.data.qpos[0])

for step in range(int(params.duration / params.timestep)):
    t = step * params.timestep
    
    # Compute and apply control
    tau = gait.compute_control(t, support_foot, burst_start_t)
    gait.data.ctrl[:] = tau[:4]
    
    # Step simulation
    mujoco.mj_step(gait.model, gait.data)
    
    # Check for failure
    failure = gait.classify_failure(start_x, t)
    if failure:
        print(f"Failure at t={t:.3f}s: {failure}")
        break
```

### Example 2: Contact Event Detection

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams
import mujoco

params = RollingFootParams()
gait = RollingFootGait(params)
gait.initialize()

# Contact state tracking
support_foot = "left"
burst_start_t = 0.0
alternations = 0
candidate_start_t = {"left": None, "right": None}
contact_reported = {"left": False, "right": False}
accepted_contact = ""
last_event_t = -1.0

for step in range(10000):
    t = step * params.timestep
    
    # Control and step
    tau = gait.compute_control(t, support_foot, burst_start_t)
    gait.data.ctrl[:] = tau[:4]
    mujoco.mj_step(gait.model, gait.data)
    
    # Detect stable contacts
    left_contact, right_contact = gait.contact_flags()
    contacts = {"left": left_contact, "right": right_contact}
    
    stable_feet = []
    for foot, has_contact in contacts.items():
        if has_contact:
            if candidate_start_t[foot] is None:
                candidate_start_t[foot] = t
                contact_reported[foot] = False
            if t - candidate_start_t[foot] >= params.stable_contact_time:
                stable_feet.append(foot)
        else:
            candidate_start_t[foot] = None
            contact_reported[foot] = False
    
    # Process contact events
    for foot in stable_feet:
        if (not contact_reported[foot] and 
            foot != accepted_contact and 
            t - last_event_t > params.min_event_interval):
            
            if accepted_contact in {"left", "right"}:
                alternations += 1
            
            accepted_contact = foot
            support_foot = foot
            burst_start_t = t
            last_event_t = t
            contact_reported[foot] = True
            
            print(f"t={t:.3f}s: {foot} foot touchdown (alternation #{alternations})")
            break
```

### Example 3: Walking on a Slope

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams

# Create model for 5-degree downhill slope
params = RollingFootParams(
    slope_deg=5.0,
    duration=10.0,
    hip_mass=6.0,  # Heavier walker for more momentum
)

gait = RollingFootGait(params)
gait.initialize()

# The ramp height function accounts for slope
x_positions = [0.0, 1.0, 2.0, 3.0]
for x in x_positions:
    height = gait.ramp_height(x)
    print(f"Ramp height at x={x:.1f}m: {height:.4f}m")
```

### Example 4: Custom Parameters

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams

# Create a custom walker
custom_params = RollingFootParams(
    # Larger foot for more stability
    foot_radius=0.05,
    foot_length=0.18,
    
    # Stronger control
    hip_kp=22.0,
    hip_kd=5.0,
    hip_torque_limit=10.0,
    
    # Slower gait
    gait_period=1.2,
    
    # Custom geometry
    thigh_length=0.50,
    shank_length=0.50,
)

gait = RollingFootGait(custom_params)
print(f"Leg length: {custom_params.leg_length}m")
print(f"Slope angle: {custom_params.gamma:.4f} rad")
```

## Integration with Existing Code

The RollingFootGait model is designed to integrate with existing hw-1 project components:

### With simulation_framework.py

```python
from common.rolling_foot_gait import RollingFootGait, RollingFootParams
from common.simulation_framework import ContactState, update_contact_state

params = RollingFootParams()
gait = RollingFootGait(params)
gait.initialize()

contact_state = ContactState(
    stable_contact_time=params.stable_contact_time,
    min_event_interval=params.min_event_interval,
)

for step in range(10000):
    t = step * params.timestep
    
    # Get contacts
    left_contact, right_contact = gait.contact_flags()
    
    # Update contact state
    new_events = update_contact_state(contact_state, t, left_contact, right_contact)
    
    if new_events:
        support_foot = contact_state.support_foot
```

### With data_loader.py

The CSV output format from simulations using RollingFootGait is compatible with the existing `DataLoader` class.

## File Locations

- Model implementation: `D:\Dunna\Documents\hw-1\common\rolling_foot_gait.py`
- Test suite: `D:\Dunna\Documents\hw-1\common\test_rolling_foot_gait.py`
- Usage example: `D:\Dunna\Documents\hw-1\common\example_rolling_foot_gait.py`
- Documentation: `D:\Dunna\Documents\hw-1\common\rolling_foot_gait_docs.md`

## Testing

Run the test suite:
```bash
cd D:\Dunna\Documents\hw-1
.venv-mujoco\Scripts\python.exe common\test_rolling_foot_gait.py
```

Run the usage examples:
```bash
cd D:\Dunna\Documents\hw-1
.venv-mujoco\Scripts\python.exe common\example_rolling_foot_gait.py
```

## Implementation Notes

### Model Structure

The model uses a 2D planar biped with:
- 2 DOF hip (slide joints in x and z)
- 2 hip joints (left and right, revolute)
- 2 knee joints (left and right, revolute)
- 2 ankle joints (left and right, revolute with passive spring-damper)

Total: 8 DOF (qpos), 4 actuators (left/right hip and knee)

### Foot Geometry

Each foot consists of three contact geoms:
- **Heel**: Sphere at rear (larger radius for stability)
- **Sole**: Capsule connecting heel and toe (smaller radius)
- **Toe**: Sphere at front (smallest radius for natural roll-off)

This geometry enables natural heel-strike, mid-stance, and toe-off phases.

### Control Strategy

The control is quasi-passive with minimal actuation:
1. Hip joints use PD control to track time-varying targets
2. Knee joints use weak PD control for stabilization
3. Ankle joints are passive (spring-damper only)
4. Control targets switch based on support foot (stance vs swing)
5. Smoothstep interpolation provides smooth transitions

### Contact Detection

The model includes robust contact detection with anti-bounce filtering:
1. Raw contact is detected via MuJoCo collision detection
2. Contacts must persist for `stable_contact_time` to be considered stable
3. Contact events must be separated by at least `min_event_interval`
4. This prevents false triggering from foot bouncing

## Comparison with v10 Implementation

The RollingFootGait model is based on v10 but provides:

| Feature | v10 | RollingFootGait |
|---------|-----|-----------------|
| Structure | Script-based | Object-oriented class |
| Model generation | Function | Method with lazy loading |
| State management | Separate variables | Encapsulated properties |
| Reusability | Copy-paste | Import and instantiate |
| Testing | Manual | Comprehensive test suite |
| Documentation | Comments | Full API docs |
| Integration | Direct | Compatible with common/ modules |

## Future Extensions

Possible enhancements:
- Add sensor model integration (IMU, force sensors)
- Support for terrain variations beyond ramps
- Energy optimization utilities
- Visualization helpers
- Parameter optimization interface
- Multi-objective scoring functions

## License

Part of the hw-1 project. Follows the same license as the parent project.

## References

Based on:
- V10 rolling foot biomimetic gait implementation
- Passive dynamic walking principles
- Quasi-passive control strategies
- Event-driven state machine design

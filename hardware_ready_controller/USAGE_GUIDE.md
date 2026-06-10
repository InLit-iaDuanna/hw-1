# Hardware-Ready Controller Usage Guide

> Comprehensive guide for the hw-1 rehabilitation gait controller - from installation to deployment

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [MuJoCo Simulation Tutorial](#mujoco-simulation-tutorial)
4. [Hardware Deployment Guide](#hardware-deployment-guide)
5. [Parameter Tuning Guide](#parameter-tuning-guide)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) Virtual environment tool

### Development Environment Setup

```bash
# Clone or navigate to the project directory
cd D:\Dunna\Documents\hw-1\hardware_ready_controller

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install core dependencies
pip install numpy scipy matplotlib

# Install MuJoCo for simulation
pip install mujoco>=3.0.0

# Verify installation
python -c "import mujoco; print(f'MuJoCo {mujoco.__version__} installed')"
```

**Expected Output:**
```
MuJoCo 3.1.0 installed
```

### Hardware Deployment Dependencies

For Raspberry Pi deployment:

```bash
# Install hardware interface libraries
pip install spidev RPi.GPIO

# Install Dynamixel SDK
pip install dynamixel-sdk

# Verify hardware libraries
python -c "import spidev, RPi.GPIO, dynamixel_sdk; print('Hardware libraries ready')"
```

---

## Quick Start (5 Minutes)

### Minimal Working Example

Create a file `test_controller.py`:

```python
from controller import HardwareReadyController, MotorSpec, FSMConfig, PhaseConfig

# Create controller with default parameters
hip_motor = MotorSpec()  # Dynamixel MX-64AR defaults
knee_motor = MotorSpec()

fsm_config = FSMConfig(
    stance_early=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66),
    stance_late=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66),
    swing_thrust=PhaseConfig(k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0, E_target=52.66),
    swing_retract=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=3.0, kd=6.0, E_target=52.66),
)

controller = HardwareReadyController(
    hip_motor=hip_motor,
    knee_motor=knee_motor,
    fsm_config=fsm_config,
    total_mass_kg=6.08,
    compensate_friction=True
)

print("Controller initialized successfully!")
print(f"Friction compensation: {controller.compensate_friction}")
print(f"Hip motor peak torque: {controller.hip_motor.joint_tau_sat_peak:.2f} Nm")
```

**Run:**
```bash
python test_controller.py
```

**Expected Output:**
```
Controller initialized successfully!
Friction compensation: True
Hip motor peak torque: 5.99 Nm
```

---

## MuJoCo Simulation Tutorial

### Step 1: Verify MuJoCo Model

Ensure you have a MuJoCo XML model file. The controller expects a model with:
- Joints: `left_hip`, `left_knee`, `right_hip`, `right_knee`, `hip_x`, `hip_z`
- Geoms: `left_sole`, `right_sole` (for contact detection)

### Step 2: Run Example Simulation

```python
from examples.run_in_mujoco import MuJoCoControllerDemo, create_default_controller
from pathlib import Path

# Create controller
controller = create_default_controller()

# Path to your MuJoCo model
model_path = "path/to/your/model.xml"

# Create demo
demo = MuJoCoControllerDemo(model_path, controller)

# Run 10-second simulation with visualization
demo.run_simulation(duration_sec=10.0, visualize=True)

# Save results
demo.save_results("simulation_results")
```

**Run:**
```bash
python examples/run_in_mujoco.py
```

**Expected Behavior:**
1. MuJoCo viewer window opens
2. Robot starts walking with 4-phase gait pattern
3. Console shows live status updates:
   ```
   t=1.0s | Phase: stance_late      | Steps:  2 | Velocity: 0.312 m/s
   t=2.0s | Phase: swing_thrust     | Steps:  4 | Velocity: 0.298 m/s
   ```
4. After completion, generates performance plots and metrics

### Step 3: Interpret Results

Check the output directory for:

**`performance_metrics.json`:**
```json
{
  "avg_velocity_m_s": 0.305,
  "total_distance_m": 3.12,
  "total_steps": 10,
  "step_frequency_hz": 1.25,
  "avg_mechanical_energy_j": 52.34,
  "rms_torque_nm": 2.14,
  "peak_torque_nm": 5.87,
  "saturation_events": {
    "left_hip": 0,
    "left_knee": 0,
    "right_hip": 0,
    "right_knee": 0
  }
}
```

**Key Metrics to Monitor:**
- **avg_velocity_m_s**: Should be 0.25-0.35 m/s for stable walking
- **saturation_events**: Should be zero or minimal (indicates torque limits hit)
- **step_frequency_hz**: Typical human cadence is 1.0-1.5 Hz

---

## Hardware Deployment Guide

### Hardware Setup Checklist

**Components:**
- [ ] Raspberry Pi 4 (recommended) with Raspbian OS
- [ ] 4x Dynamixel MX-64AR motors
- [ ] U2D2 or USB2Dynamixel adapter
- [ ] 2x Contact sensors (force-sensitive resistors)
- [ ] 4x AS5048 magnetic encoders (optional, if not using Dynamixel encoders)
- [ ] 12V power supply (5A minimum)

**Wiring:**
- Motors connected via Dynamixel daisy chain to `/dev/ttyUSB0`
- Contact sensors connected to GPIO pins 17, 27
- (Optional) SPI encoders on SPI bus 0, devices 0-3

### Step 1: Configure Hardware Interface

Create `hardware_config.json`:

```json
{
  "device_name": "/dev/ttyUSB0",
  "baudrate": 57600,
  "motor_ids": [1, 2, 3, 4],
  "contact_pins": [17, 27],
  "encoder_channels": [0, 1, 2, 3]
}
```

### Step 2: Test Hardware Connections

```python
from deployment.raspberry_pi_interface import RaspberryPiInterface
from hardware_interface import HardwareConfig

# Load config
config = HardwareConfig(
    device_name="/dev/ttyUSB0",
    baudrate=57600,
    motor_ids=[1, 2, 3, 4],
    contact_pins=[17, 27]
)

# Initialize hardware
hw = RaspberryPiInterface(config)
success = hw.initialize()

if success:
    print("Hardware initialized successfully!")
    
    # Test sensor reads
    positions = hw.read_joint_positions()
    velocities = hw.read_joint_velocities()
    contacts = hw.read_contact_states()
    
    print(f"Joint positions: {positions}")
    print(f"Joint velocities: {velocities}")
    print(f"Contact states: {contacts}")
    
    # Test motor write (small torque)
    import numpy as np
    test_torques = np.array([0.1, 0.1, 0.1, 0.1])
    hw.write_motor_torques(test_torques)
    print("Motor command sent successfully!")
    
    # Emergency stop
    hw.emergency_stop()
    hw.shutdown()
else:
    print("Hardware initialization failed!")
```

**Expected Output:**
```
Dynamixel motors initialized: [1, 2, 3, 4]
GPIO contact sensors initialized: [17, 27]
Hardware initialized successfully!
Joint positions: [ 0.023 -0.012  0.018 -0.015]
Joint velocities: [0.0 0.0 0.0 0.0]
Contact states: [True False]
Motor command sent successfully!
```

### Step 3: Deploy Controller

Create `deploy_controller.py`:

```python
import time
import signal
import sys
from controller import HardwareReadyController, SensorData
from deployment.raspberry_pi_interface import RaspberryPiInterface
from hardware_interface import HardwareConfig

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    global running
    print("\nShutdown signal received...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# Initialize hardware
config = HardwareConfig(
    device_name="/dev/ttyUSB0",
    baudrate=57600,
    motor_ids=[1, 2, 3, 4],
    contact_pins=[17, 27]
)
hw = RaspberryPiInterface(config)

if not hw.initialize():
    print("Hardware initialization failed!")
    sys.exit(1)

# Create controller (same code as simulation!)
from examples.run_in_mujoco import create_default_controller
controller = create_default_controller()

print("Starting control loop at 1kHz...")
print("Press Ctrl+C to stop")

# Control loop
dt = 0.001  # 1kHz
loop_count = 0

try:
    while running:
        t_start = time.perf_counter()
        
        # Read sensors
        positions = hw.read_joint_positions()
        velocities = hw.read_joint_velocities()
        contacts = hw.read_contact_states()
        
        # Package sensor data
        sensors = SensorData(
            time=loop_count * dt,
            left_hip_pos=positions[0],
            left_hip_vel=velocities[0],
            left_knee_pos=positions[1],
            left_knee_vel=velocities[1],
            right_hip_pos=positions[2],
            right_hip_vel=velocities[2],
            right_knee_pos=positions[3],
            right_knee_vel=velocities[3],
            left_foot_contact=contacts[0],
            right_foot_contact=contacts[1],
            hip_height=0.9,  # From IMU or kinematics
            hip_velocity_x=0.3  # From IMU or differentiation
        )
        
        # Compute control
        control = controller.compute_control(sensors)
        
        # Apply torques
        torques = [
            control.left_hip_torque,
            control.left_knee_torque,
            control.right_hip_torque,
            control.right_knee_torque
        ]
        hw.write_motor_torques(torques)
        
        # Status logging (every second)
        if loop_count % 1000 == 0:
            print(f"t={sensors.time:.1f}s | Phase: {control.phase:15s} | "
                  f"Steps: {control.diagnostics['step_count']:2d}")
        
        loop_count += 1
        
        # Maintain 1kHz timing
        elapsed = time.perf_counter() - t_start
        if elapsed < dt:
            time.sleep(dt - elapsed)
        elif elapsed > dt * 1.5:
            print(f"Warning: Loop time {elapsed*1000:.2f}ms exceeds target {dt*1000:.0f}ms")

except Exception as e:
    print(f"Error in control loop: {e}")

finally:
    print("\nStopping controller...")
    hw.emergency_stop()
    hw.shutdown()
    
    # Print diagnostics
    diag = controller.get_diagnostics()
    print(f"\nSession summary:")
    print(f"  Total steps: {diag['step_count']}")
    print(f"  Phase transitions: {diag['phase_transitions']}")
    print(f"  Runtime: {diag['total_time_s']:.1f}s")
    print(f"  Saturation events: {diag['saturation_count']}")
```

**Run on Raspberry Pi:**
```bash
sudo python deploy_controller.py
```

> **Note:** `sudo` is required for GPIO access and real-time scheduling priority.

---

## Parameter Tuning Guide

### Understanding Key Parameters

#### 1. FSM Phase Configuration

Each phase has control parameters:

```python
PhaseConfig(
    k_E=7.5,        # Energy feedback gain [unitless]
    k_PD=30.0,      # Position proportional gain [Nm/rad]
    tau_max=4.0,    # Torque limit for this phase [Nm]
    kd=6.0,         # Velocity derivative gain [Nm·s/rad]
    E_target=52.66  # Target mechanical energy [J]
)
```

**Tuning Guidelines:**

| Parameter | Effect | Increase if... | Decrease if... |
|-----------|--------|----------------|----------------|
| `k_PD` | Position tracking stiffness | Robot doesn't follow trajectory | Robot is too rigid, oscillates |
| `kd` | Damping | Robot oscillates | Robot is sluggish |
| `k_E` | Energy injection (swing phase) | Robot slows down over time | Robot accelerates uncontrollably |
| `tau_max` | Safety limit | Torque saturation occurs | Motors get too hot |

#### 2. Motor Friction Compensation

```python
MotorSpec(
    joint_tau_C_eff=0.201,  # Coulomb friction [Nm]
    joint_b_eff=0.05        # Viscous damping [Nm·s/rad]
)
```

**Calibration Procedure:**

1. **Measure Coulomb friction:**
   ```python
   # Apply slowly increasing torque until joint moves
   # Record torque at breakaway point
   tau_C = torque_at_breakaway
   ```

2. **Measure viscous damping:**
   ```python
   # Command constant velocity, measure steady-state torque
   # b = tau_steady_state / velocity
   b_eff = measured_torque / commanded_velocity
   ```

#### 3. FSM Transition Thresholds

```python
FSMConfig(
    min_event_interval=0.22,       # Min time between steps [s]
    stable_contact_time=0.035,     # Contact stabilization [s]
    recovery_clearance=0.38        # Foot clearance threshold [m]
)
```

**Adjustment Tips:**
- Increase `min_event_interval` if steps are too fast (stumbling)
- Decrease `stable_contact_time` for more responsive transitions
- Adjust `recovery_clearance` based on terrain

### Automated Parameter Tuning

Use the included tuning script:

```python
from examples.tune_parameters import ParameterTuner

tuner = ParameterTuner(
    model_path="model.xml",
    base_config=fsm_config
)

# Grid search over PD gains
results = tuner.tune_gains(
    k_PD_range=[20, 30, 40, 50],
    kd_range=[3, 6, 9, 12],
    metric="avg_velocity"  # or "stability", "energy_efficiency"
)

# Get best parameters
best_params = results['best_params']
print(f"Optimal k_PD: {best_params['k_PD']}")
print(f"Optimal kd: {best_params['kd']}")
```

---

## Troubleshooting

### Issue 1: Robot Falls Immediately

**Symptoms:**
- Robot collapses at start
- All torques saturated

**Diagnosis:**
```python
diag = controller.get_diagnostics()
print(diag['saturation_count'])
# Output: {'left_hip': 1203, ...}  <- High counts
```

**Solutions:**
1. Check initial pose - knees should be slightly flexed (5-10°)
2. Reduce `k_PD` gains (try 50% reduction)
3. Verify friction compensation is enabled
4. Check motor power supply voltage

### Issue 2: Robot Doesn't Walk Forward

**Symptoms:**
- Robot maintains balance but no forward progress
- `avg_velocity < 0.1 m/s`

**Diagnosis:**
```python
# Check energy injection in swing phase
print(controller.fsm_config.swing_thrust.k_E)
# Should be non-zero (e.g., 7.5)
```

**Solutions:**
1. Increase `k_E` in `swing_thrust` phase (try 10.0-15.0)
2. Verify hip angle targets are asymmetric:
   ```python
   print(fsm_config.swing_front_deg)   # Should be negative (e.g., -22)
   print(fsm_config.swing_back_deg)    # Should be positive (e.g., 20)
   ```
3. Check ground friction in MuJoCo model

### Issue 3: Oscillations / Vibrations

**Symptoms:**
- High-frequency joint oscillations
- Chattering sounds from motors

**Diagnosis:**
```python
import numpy as np
torque_signal = np.array(demo.metrics.left_hip_torque)
torque_derivative = np.diff(torque_signal)
print(f"Torque change rate: {np.std(torque_derivative):.2f} Nm/step")
# High value (>5) indicates oscillation
```

**Solutions:**
1. Increase damping gains `kd` (try 2x current value)
2. Enable state estimation filtering (Kalman filter)
3. Reduce control frequency (e.g., 500Hz instead of 1kHz)
4. Check for mechanical backlash in joints

### Issue 4: Phase Transitions Don't Occur

**Symptoms:**
- FSM stuck in one phase
- No contact events detected

**Diagnosis:**
```python
diag = controller.get_diagnostics()
print(diag['contact_events'])
# Output: []  <- No contacts detected
```

**Solutions:**
1. Verify contact sensor connections and polarity
2. Lower contact force threshold in `_check_contact()`
3. Check foot geom names match model:
   ```python
   print(demo.left_foot_geom, demo.right_foot_geom)
   ```
4. Inspect `self.contact_events` in controller diagnostics

### Issue 5: Hardware Read Errors

**Symptoms:**
```
Encoder read error (channel 0): [Errno 121] Remote I/O error
Dynamixel read error: Communication timeout
```

**Solutions:**
1. **SPI errors:**
   ```bash
   # Enable SPI in Raspberry Pi config
   sudo raspi-config
   # Interface Options -> SPI -> Enable
   ```

2. **Dynamixel errors:**
   ```bash
   # Check USB permissions
   sudo chmod 666 /dev/ttyUSB0
   
   # Verify baudrate matches motors
   # Use Dynamixel Wizard to check
   ```

3. **GPIO errors:**
   ```bash
   # Run with sudo for GPIO access
   sudo python deploy_controller.py
   ```

### Issue 6: Real-Time Performance Degradation

**Symptoms:**
```
Warning: Loop time 2.14ms exceeds target 1ms
```

**Solutions:**
1. **Set CPU governor to performance:**
   ```bash
   sudo cpufreq-set -g performance
   ```

2. **Disable unnecessary services:**
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable wifi
   ```

3. **Use real-time kernel:**
   ```bash
   sudo apt install linux-image-rt-arm64
   ```

4. **Optimize Python code:**
   - Use NumPy vectorization
   - Minimize allocations in control loop
   - Profile with `cProfile`

---

## API Reference

### Controller Class

#### `HardwareReadyController`

**Constructor:**
```python
HardwareReadyController(
    hip_motor: MotorSpec,
    knee_motor: MotorSpec,
    fsm_config: FSMConfig,
    total_mass_kg: float = 6.08,
    compensate_friction: bool = True,
    log_level: int = logging.INFO
)
```

**Methods:**

##### `compute_control(sensors: SensorData) -> ControlOutput`
Main control computation method.

**Parameters:**
- `sensors`: Current sensor readings

**Returns:**
- `ControlOutput` with torque commands and diagnostics

**Example:**
```python
sensors = SensorData(
    time=0.1,
    left_hip_pos=0.0,
    left_hip_vel=0.0,
    # ... other fields
)
control = controller.compute_control(sensors)
print(f"Left hip torque: {control.left_hip_torque:.3f} Nm")
```

##### `get_diagnostics() -> Dict`
Get accumulated diagnostic information.

**Returns:**
```python
{
    'step_count': int,
    'contact_events': int,
    'phase_durations_s': dict,
    'phase_transitions': int,
    'saturation_count': dict,
    'total_time_s': float,
    'recent_contacts': list
}
```

##### `reset()`
Reset controller state for new trial.

**Example:**
```python
controller.reset()
# All counters and FSM state cleared
```

### Data Structures

#### `SensorData`
```python
@dataclass
class SensorData:
    time: float                         # Current time [s]
    left_hip_pos: float                 # [rad]
    left_hip_vel: float                 # [rad/s]
    left_knee_pos: float                # [rad]
    left_knee_vel: float                # [rad/s]
    right_hip_pos: float                # [rad]
    right_hip_vel: float                # [rad/s]
    right_knee_pos: float               # [rad]
    right_knee_vel: float               # [rad/s]
    left_foot_contact: bool             # Contact sensor
    right_foot_contact: bool            # Contact sensor
    hip_height: Optional[float] = None  # CoM height [m]
    hip_velocity_x: Optional[float] = None  # Forward velocity [m/s]
```

#### `ControlOutput`
```python
@dataclass
class ControlOutput:
    left_hip_torque: float              # [Nm]
    left_knee_torque: float             # [Nm]
    right_hip_torque: float             # [Nm]
    right_knee_torque: float            # [Nm]
    phase: str                          # Current FSM phase
    diagnostics: Dict                   # Additional info
```

#### `MotorSpec`
```python
@dataclass
class MotorSpec:
    name: str = "Dynamixel MX-64AR @12V"
    Kt: float = 0.0109                  # Torque constant [Nm/A]
    N: float = 200.0                    # Gear ratio
    eta: float = 0.67                   # Efficiency
    joint_tau_C_eff: float = 0.201      # Coulomb friction [Nm]
    joint_b_eff: float = 0.05           # Viscous damping [Nm·s/rad]
    joint_tau_sat_peak: float = 5.988   # Peak torque [Nm]
    joint_tau_sat_cont: float = 1.753   # Continuous torque [Nm]
```

#### `PhaseConfig`
```python
@dataclass
class PhaseConfig:
    k_E: float          # Energy feedback gain
    k_PD: float         # PD position gain [Nm/rad]
    tau_max: float      # Torque limit [Nm]
    kd: float           # Derivative gain [Nm·s/rad]
    E_target: float     # Target energy [J]
```

#### `FSMConfig`
```python
@dataclass
class FSMConfig:
    stance_early: PhaseConfig
    stance_late: PhaseConfig
    swing_thrust: PhaseConfig
    swing_retract: PhaseConfig
    
    # Transition parameters
    min_event_interval: float = 0.22
    stable_contact_time: float = 0.035
    recovery_clearance: float = 0.38
    
    # Trajectory targets (degrees)
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0
```

### Hardware Interface

#### `RaspberryPiInterface`

**Constructor:**
```python
RaspberryPiInterface(config: HardwareConfig)
```

**Methods:**

##### `initialize() -> bool`
Initialize all hardware interfaces.

##### `read_joint_positions() -> np.ndarray`
Read joint positions [rad] from encoders.

##### `read_joint_velocities() -> np.ndarray`
Read joint velocities [rad/s] from motors.

##### `read_contact_states() -> np.ndarray`
Read contact sensor states (bool array).

##### `write_motor_torques(torques: np.ndarray) -> bool`
Write torque commands [Nm] to motors.

##### `emergency_stop() -> bool`
Immediately disable all motor torques.

##### `shutdown()`
Clean shutdown of all hardware interfaces.

---

## Performance Benchmarks

### V13.7 Verified Performance

From simulation validation:

| Metric | Value | Tolerance |
|--------|-------|-----------|
| Forward velocity | 0.30 ± 0.05 m/s | Stable walking range |
| Step frequency | 1.2 ± 0.2 Hz | Human-like cadence |
| Hip height variation | < 0.05 m | Smooth gait |
| Torque saturation rate | < 1% | Motor capacity utilization |
| Phase transition success | > 95% | FSM reliability |

### Hardware Timing Requirements

| Operation | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Control loop | 1.0 ms (1kHz) | 1.5 ms | 2.0 ms |
| Sensor read | 0.2 ms | 0.5 ms | 1.0 ms |
| Control compute | 0.3 ms | 0.5 ms | 0.8 ms |
| Motor write | 0.2 ms | 0.4 ms | 0.7 ms |

---

## Additional Resources

- **V13.7 Technical Report**: `../v13_7_friction_compensation/README.md`
- **FSM Design Document**: `../v13_6_event_driven_fsm/README.md`
- **Motor Specifications**: `controller.py` - `MotorSpec` class
- **Example Configurations**: `examples/` directory
- **Test Suite**: `tests/` directory

---

## Support and Contributing

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review diagnostic output from `controller.get_diagnostics()`
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. Consult V13.7 simulation validation results

**Version:** 1.0.0  
**Last Updated:** 2026-06-08  
**Based on:** V13.7 friction compensation + V17 state estimation

"""
HardwareReadyController - Main orchestration class for hw-1 gait control system

Based on V13.7 architecture with friction compensation and event-driven FSM.
Coordinates: state estimation -> FSM phase logic -> trajectory generation ->
feedforward compensation -> feedback control -> torque output

References:
- V13.7: friction_compensation with MX-64AR motor model
- V13.6: event-driven FSM with 4-phase gait (stance_early, stance_late, swing_thrust, swing_retract)
- V16: MX-64AR actuator parameters (Kt, N, eta, tau_C, b_visc)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np


@dataclass
class MotorSpec:
    """Dynamixel MX-64AR motor specifications from V13.7"""
    name: str = "Dynamixel MX-64AR @12V"
    Kt: float = 0.0109              # Motor torque constant [Nm/A]
    J_rotor: float = 7e-08          # Rotor inertia [kg·m²]
    N: float = 200.0                # Gear ratio
    eta: float = 0.67               # Gearbox efficiency
    I_max: float = 4.1              # Peak current [A]
    I_cont: float = 1.2             # Continuous current [A]
    R_arm: float = 1.0              # Armature resistance [Ω]
    tau_C_motor: float = 0.0015     # Motor Coulomb friction [Nm]
    b_visc_motor: float = 1.25e-06  # Motor viscous damping [Nm·s/rad]

    # Joint-level effective parameters (reflected through gearbox)
    joint_J_eff: float = 0.0028     # Effective joint inertia [kg·m²]
    joint_b_eff: float = 0.05       # Effective joint damping [Nm·s/rad]
    joint_tau_C_eff: float = 0.201  # Effective Coulomb friction at joint [Nm]
    joint_tau_sat_peak: float = 5.988  # Peak torque limit [Nm]
    joint_tau_sat_cont: float = 1.753  # Continuous torque limit [Nm]


@dataclass
class PhaseConfig:
    """FSM phase control parameters from V13.6/V13.7"""
    k_E: float          # Energy feedback gain
    k_PD: float         # PD position gain (kp)
    tau_max: float      # Torque limit for this phase [Nm]
    kd: float           # Derivative gain
    E_target: float     # Target mechanical energy [J]


@dataclass
class FSMConfig:
    """V13.6 event-driven FSM configuration"""
    stance_early: PhaseConfig
    stance_late: PhaseConfig
    swing_thrust: PhaseConfig
    swing_retract: PhaseConfig

    # Phase transition parameters
    min_event_interval: float = 0.22        # Minimum time between events [s]
    stable_contact_time: float = 0.035      # Contact stabilization time [s]
    recovery_clearance: float = 0.38        # Recovery foot clearance threshold [m]

    # Trajectory targets
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0

    @classmethod
    def from_v137_params(cls, v136_phase_params: Dict, gait_params: Dict) -> 'FSMConfig':
        """Load FSM config from V13.7 parameter dictionary"""
        return cls(
            stance_early=PhaseConfig(**v136_phase_params['stance_early']),
            stance_late=PhaseConfig(**v136_phase_params['stance_late']),
            swing_thrust=PhaseConfig(**v136_phase_params['swing_thrust']),
            swing_retract=PhaseConfig(**v136_phase_params['swing_retract']),
            min_event_interval=gait_params.get('min_event_interval', 0.22),
            stable_contact_time=gait_params.get('stable_contact_time', 0.035),
            recovery_clearance=gait_params.get('recovery_clearance', 0.38),
            swing_back_deg=gait_params.get('swing_back_deg', 20.0),
            swing_front_deg=gait_params.get('swing_front_deg', -22.0),
            stance_front_deg=gait_params.get('stance_front_deg', -14.0),
            stance_back_deg=gait_params.get('stance_back_deg', 22.0),
            swing_knee_flex_deg=gait_params.get('swing_knee_flex_deg', 28.0),
            stance_knee_deg=gait_params.get('stance_knee_deg', 2.0),
        )


@dataclass
class SensorData:
    """Raw sensor readings from hardware"""
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
    hip_height: Optional[float] = None  # CoM height from IMU/kinematics [m]
    hip_velocity_x: Optional[float] = None  # Forward velocity [m/s]


@dataclass
class StateEstimate:
    """Processed state estimate"""
    time: float
    stance_leg: str                     # 'left' or 'right'
    swing_leg: str                      # 'left' or 'right'
    mechanical_energy: float            # Total mechanical energy [J]
    contact_height: float               # Estimated stance foot height [m]
    swing_foot_clearance: float         # Swing foot height above ground [m]
    phase_time: float                   # Time since last phase transition [s]


@dataclass
class ControlOutput:
    """Computed control torques"""
    left_hip_torque: float              # [Nm]
    left_knee_torque: float             # [Nm]
    right_hip_torque: float             # [Nm]
    right_knee_torque: float            # [Nm]
    phase: str                          # Current FSM phase
    diagnostics: Dict = field(default_factory=dict)


class HardwareReadyController:
    """
    Main controller orchestrator for hw-1 rehabilitation gait device.

    Architecture (V13.7):
    1. State Estimator: sensor fusion -> mechanical energy, contact state
    2. FSM: event-driven 4-phase gait state machine
    3. Trajectory Generator: phase-dependent joint angle targets
    4. Feedforward Compensator: friction + viscous damping compensation
    5. Feedback Controller: PD + energy-based torque computation

    Usage:
        controller = HardwareReadyController.from_v137_config(config_path)

        while running:
            sensors = read_sensors()
            torques = controller.compute_control(sensors)
            send_torques(torques)
    """

    def __init__(
        self,
        hip_motor: MotorSpec,
        knee_motor: MotorSpec,
        fsm_config: FSMConfig,
        total_mass_kg: float = 6.08,
        compensate_friction: bool = True,
        log_level: int = logging.INFO
    ):
        self.hip_motor = hip_motor
        self.knee_motor = knee_motor
        self.fsm_config = fsm_config
        self.total_mass_kg = total_mass_kg
        self.compensate_friction = compensate_friction

        # FSM state
        self.current_phase = "stance_early"
        self.phase_start_time = 0.0
        self.last_event_time = 0.0
        self.step_count = 0

        # State memory
        self.last_contact = {"left": False, "right": False}
        self.stance_leg = "right"  # Initial stance leg

        # Logging
        self.logger = logging.getLogger("HardwareReadyController")
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

        # Diagnostics
        self.phase_durations = {
            "stance_early": [],
            "stance_late": [],
            "swing_thrust": [],
            "swing_retract": []
        }
        self.contact_events = []
        self.saturation_count = {
            "left_hip": 0,
            "left_knee": 0,
            "right_hip": 0,
            "right_knee": 0
        }

        self.logger.info(f"Controller initialized with friction compensation: {compensate_friction}")
        self.logger.info(f"Hip motor: {hip_motor.name}, Peak torque: {hip_motor.joint_tau_sat_peak:.2f} Nm")
        self.logger.info(f"FSM phases: {list(self.phase_durations.keys())}")

    @classmethod
    def from_v137_config(cls, config_path: str) -> 'HardwareReadyController':
        """Load controller from V13.7 JSON configuration file"""
        with open(config_path, 'r') as f:
            cfg = json.load(f)

        hip_spec = MotorSpec(**cfg['v13_7_motor']['hip'])
        knee_spec = MotorSpec(**cfg['v13_7_motor']['knee'])
        fsm_config = FSMConfig.from_v137_params(
            cfg['v136_phase_params'],
            cfg['params']
        )

        return cls(
            hip_motor=hip_spec,
            knee_motor=knee_spec,
            fsm_config=fsm_config,
            total_mass_kg=cfg.get('total_mass_kg', 6.08),
            compensate_friction=cfg.get('compensate_friction', True)
        )

    def read_sensors(self, sensor_data: SensorData) -> StateEstimate:
        """
        State estimation: fuse sensor data into control-relevant state estimate.

        Computes:
        - Stance/swing leg identification
        - Mechanical energy (kinetic + potential)
        - Foot clearance for phase transitions
        """
        # Contact-based stance detection
        if sensor_data.left_foot_contact and not sensor_data.right_foot_contact:
            stance_leg = "left"
            swing_leg = "right"
        elif sensor_data.right_foot_contact and not sensor_data.left_foot_contact:
            stance_leg = "right"
            swing_leg = "left"
        else:
            # Both or neither in contact - maintain previous stance
            stance_leg = self.stance_leg
            swing_leg = "left" if stance_leg == "right" else "right"

        # Update stance leg memory
        self.stance_leg = stance_leg

        # Compute mechanical energy (simplified)
        # E = 0.5 * m * v^2 + m * g * h
        g = 9.81
        v_x = sensor_data.hip_velocity_x if sensor_data.hip_velocity_x is not None else 0.3
        h = sensor_data.hip_height if sensor_data.hip_height is not None else 0.9

        E_kinetic = 0.5 * self.total_mass_kg * v_x**2
        E_potential = self.total_mass_kg * g * h
        E_total = E_kinetic + E_potential

        # Swing foot clearance estimation (simplified - requires kinematics)
        swing_foot_clearance = 0.1  # Placeholder - needs forward kinematics

        phase_time = sensor_data.time - self.phase_start_time

        return StateEstimate(
            time=sensor_data.time,
            stance_leg=stance_leg,
            swing_leg=swing_leg,
            mechanical_energy=E_total,
            contact_height=0.0,
            swing_foot_clearance=swing_foot_clearance,
            phase_time=phase_time
        )

    def _update_fsm(self, state: StateEstimate, sensors: SensorData) -> str:
        """
        Event-driven FSM logic from V13.6.

        Phases:
        - stance_early: Double support -> weight acceptance
        - stance_late: Single support -> push-off preparation
        - swing_thrust: Swing leg forward extension
        - swing_retract: Swing leg retraction before contact

        Transitions triggered by contact events and clearance thresholds.
        """
        current_phase = self.current_phase
        time_in_phase = state.phase_time
        time_since_event = state.time - self.last_event_time

        new_phase = current_phase

        # Detect contact events
        left_contact = sensors.left_foot_contact
        right_contact = sensors.right_foot_contact
        left_touchdown = left_contact and not self.last_contact["left"]
        right_touchdown = right_contact and not self.last_contact["right"]

        # Update contact memory
        self.last_contact["left"] = left_contact
        self.last_contact["right"] = right_contact

        # Phase transition logic
        if current_phase == "stance_early":
            # Transition to stance_late after stable contact
            if time_in_phase > self.fsm_config.stable_contact_time:
                new_phase = "stance_late"

        elif current_phase == "stance_late":
            # Transition to swing_thrust on opposite leg liftoff
            # (approximated by single support detection)
            if time_in_phase > 0.1 and not (left_contact and right_contact):
                new_phase = "swing_thrust"

        elif current_phase == "swing_thrust":
            # Transition to swing_retract when swing foot reaches forward target
            if time_in_phase > 0.2:  # Time-based for now
                new_phase = "swing_retract"

        elif current_phase == "swing_retract":
            # Transition to stance_early on touchdown
            if (left_touchdown or right_touchdown) and time_since_event > self.fsm_config.min_event_interval:
                new_phase = "stance_early"
                self.last_event_time = state.time
                self.step_count += 1

                # Log contact event
                self.contact_events.append({
                    "time": state.time,
                    "foot": "left" if left_touchdown else "right",
                    "E": state.mechanical_energy
                })

        # Update phase if transition occurred
        if new_phase != current_phase:
            duration = time_in_phase
            self.phase_durations[current_phase].append(duration)
            self.current_phase = new_phase
            self.phase_start_time = state.time
            self.logger.debug(f"Phase transition: {current_phase} -> {new_phase} after {duration:.3f}s")

        return new_phase

    def _generate_trajectory(self, phase: str, state: StateEstimate) -> Dict[str, float]:
        """
        Generate joint angle targets based on current FSM phase.

        Returns target angles [rad] for each joint.
        """
        deg2rad = np.pi / 180.0

        stance_leg = state.stance_leg
        swing_leg = state.swing_leg

        targets = {}

        if phase == "stance_early":
            # Weight acceptance - knees slightly flexed, neutral hip
            targets[f"{stance_leg}_hip"] = self.fsm_config.stance_front_deg * deg2rad
            targets[f"{stance_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad
            targets[f"{swing_leg}_hip"] = self.fsm_config.stance_back_deg * deg2rad
            targets[f"{swing_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad

        elif phase == "stance_late":
            # Push-off preparation - stance leg extends, swing begins
            targets[f"{stance_leg}_hip"] = self.fsm_config.stance_back_deg * deg2rad
            targets[f"{stance_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad
            targets[f"{swing_leg}_hip"] = self.fsm_config.swing_back_deg * deg2rad
            targets[f"{swing_leg}_knee"] = self.fsm_config.swing_knee_flex_deg * deg2rad

        elif phase == "swing_thrust":
            # Swing forward - flex knee, extend hip forward
            targets[f"{stance_leg}_hip"] = self.fsm_config.stance_back_deg * deg2rad
            targets[f"{stance_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad
            targets[f"{swing_leg}_hip"] = self.fsm_config.swing_front_deg * deg2rad
            targets[f"{swing_leg}_knee"] = self.fsm_config.swing_knee_flex_deg * deg2rad

        elif phase == "swing_retract":
            # Prepare for contact - extend swing leg knee
            targets[f"{stance_leg}_hip"] = self.fsm_config.stance_back_deg * deg2rad
            targets[f"{stance_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad
            targets[f"{swing_leg}_hip"] = self.fsm_config.swing_front_deg * deg2rad
            targets[f"{swing_leg}_knee"] = self.fsm_config.stance_knee_deg * deg2rad

        return targets

    def _compute_feedforward(self, joint: str, velocity: float, motor: MotorSpec) -> float:
        """
        Feedforward friction compensation from V13.7.

        Compensates for:
        - Coulomb friction (sign(velocity) * tau_C)
        - Viscous damping (b * velocity)
        """
        if not self.compensate_friction:
            return 0.0

        tau_coulomb = motor.joint_tau_C_eff * np.sign(velocity) if abs(velocity) > 1e-3 else 0.0
        tau_viscous = motor.joint_b_eff * velocity

        return tau_coulomb + tau_viscous

    def _compute_feedback(
        self,
        phase: str,
        target: float,
        actual_pos: float,
        actual_vel: float,
        mechanical_energy: float
    ) -> float:
        """
        Feedback control: PD + energy-based control from V13.6/V13.7.

        tau_fb = k_PD * (target - pos) - kd * vel + k_E * (E_target - E)
        """
        phase_cfg = getattr(self.fsm_config, phase)

        position_error = target - actual_pos
        tau_pd = phase_cfg.k_PD * position_error - phase_cfg.kd * actual_vel

        energy_error = phase_cfg.E_target - mechanical_energy
        tau_energy = phase_cfg.k_E * energy_error

        return tau_pd + tau_energy

    def _saturate_torque(
        self,
        torque: float,
        joint: str,
        motor: MotorSpec,
        phase_limit: float | None = None,
    ) -> float:
        """Apply motor torque limits and track saturation events"""
        limit = motor.joint_tau_sat_peak
        if phase_limit is not None:
            limit = min(limit, phase_limit)

        if abs(torque) > limit:
            self.saturation_count[joint] += 1
            return np.clip(torque, -limit, limit)
        return torque

    def compute_control(self, sensors: SensorData) -> ControlOutput:
        """
        Main control loop: orchestrate all components.

        Pipeline:
        1. State estimation
        2. FSM update
        3. Trajectory generation
        4. Feedforward compensation
        5. Feedback control
        6. Torque saturation
        """
        # Step 1: State estimation
        state = self.read_sensors(sensors)

        # Step 2: FSM update
        phase = self._update_fsm(state, sensors)

        # Step 3: Trajectory generation
        targets = self._generate_trajectory(phase, state)

        # Step 4 & 5: Compute torques (feedforward + feedback)
        left_hip_ff = self._compute_feedforward("left_hip", sensors.left_hip_vel, self.hip_motor)
        left_hip_fb = self._compute_feedback(
            phase, targets["left_hip"], sensors.left_hip_pos, sensors.left_hip_vel, state.mechanical_energy
        )
        left_hip_torque = left_hip_ff + left_hip_fb

        left_knee_ff = self._compute_feedforward("left_knee", sensors.left_knee_vel, self.knee_motor)
        left_knee_fb = self._compute_feedback(
            phase, targets["left_knee"], sensors.left_knee_pos, sensors.left_knee_vel, state.mechanical_energy
        )
        left_knee_torque = left_knee_ff + left_knee_fb

        right_hip_ff = self._compute_feedforward("right_hip", sensors.right_hip_vel, self.hip_motor)
        right_hip_fb = self._compute_feedback(
            phase, targets["right_hip"], sensors.right_hip_pos, sensors.right_hip_vel, state.mechanical_energy
        )
        right_hip_torque = right_hip_ff + right_hip_fb

        right_knee_ff = self._compute_feedforward("right_knee", sensors.right_knee_vel, self.knee_motor)
        right_knee_fb = self._compute_feedback(
            phase, targets["right_knee"], sensors.right_knee_pos, sensors.right_knee_vel, state.mechanical_energy
        )
        right_knee_torque = right_knee_ff + right_knee_fb

        # Step 6: Saturation
        phase_limit = getattr(self.fsm_config, phase).tau_max
        left_hip_torque = self._saturate_torque(
            left_hip_torque, "left_hip", self.hip_motor, phase_limit
        )
        left_knee_torque = self._saturate_torque(
            left_knee_torque, "left_knee", self.knee_motor, phase_limit
        )
        right_hip_torque = self._saturate_torque(
            right_hip_torque, "right_hip", self.hip_motor, phase_limit
        )
        right_knee_torque = self._saturate_torque(
            right_knee_torque, "right_knee", self.knee_motor, phase_limit
        )

        # Diagnostics
        diagnostics = {
            "mechanical_energy": state.mechanical_energy,
            "stance_leg": state.stance_leg,
            "phase_time": state.phase_time,
            "step_count": self.step_count,
            "left_hip_target": targets["left_hip"],
            "right_hip_target": targets["right_hip"],
        }

        return ControlOutput(
            left_hip_torque=left_hip_torque,
            left_knee_torque=left_knee_torque,
            right_hip_torque=right_hip_torque,
            right_knee_torque=right_knee_torque,
            phase=phase,
            diagnostics=diagnostics
        )

    def get_diagnostics(self) -> Dict:
        """Return accumulated diagnostics for logging/analysis"""
        total_phase_time = sum(sum(durations) for durations in self.phase_durations.values())

        return {
            "step_count": self.step_count,
            "contact_events": len(self.contact_events),
            "phase_durations_s": {
                phase: sum(durations) for phase, durations in self.phase_durations.items()
            },
            "phase_transitions": sum(len(durations) for durations in self.phase_durations.values()),
            "saturation_count": self.saturation_count.copy(),
            "total_time_s": total_phase_time,
            "recent_contacts": self.contact_events[-5:] if self.contact_events else []
        }

    def reset(self):
        """Reset controller state for new trial"""
        self.current_phase = "stance_early"
        self.phase_start_time = 0.0
        self.last_event_time = 0.0
        self.step_count = 0
        self.last_contact = {"left": False, "right": False}
        self.stance_leg = "right"

        self.phase_durations = {phase: [] for phase in self.phase_durations}
        self.contact_events.clear()
        self.saturation_count = {joint: 0 for joint in self.saturation_count}

        self.logger.info("Controller state reset")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Load from V13.7 config
    config_path = Path(__file__).parent.parent / "v13_7_friction_compensation" / "out" / "v13_7_mx64ar_comp_summary.json"

    if config_path.exists():
        controller = HardwareReadyController.from_v137_config(str(config_path))
        print(f"\nController loaded successfully")
        print(f"FSM phases: {list(controller.phase_durations.keys())}")
        print(f"Friction compensation: {controller.compensate_friction}")
        print(f"Hip motor peak torque: {controller.hip_motor.joint_tau_sat_peak:.3f} Nm")
    else:
        print(f"Config file not found: {config_path}")
        print("Creating controller with default V13.7 parameters...")

        hip_motor = MotorSpec()
        knee_motor = MotorSpec()
        fsm_config = FSMConfig(
            stance_early=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66),
            stance_late=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66),
            swing_thrust=PhaseConfig(k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0, E_target=52.66),
            swing_retract=PhaseConfig(k_E=0.0, k_PD=30.0, tau_max=3.0, kd=6.0, E_target=52.66),
        )

        controller = HardwareReadyController(hip_motor, knee_motor, fsm_config)
        print("Controller initialized with defaults")

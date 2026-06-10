"""CompassGait model class with MuJoCo integration.

Unified compass gait model supporting both kinematic playback (v03-style) and
hybrid dynamics simulation (v05-style). Provides factory methods for common
configurations and clean integration with MuJoCo.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal

import mujoco
import numpy as np


@dataclass(frozen=True)
class CompassGaitParams:
    """Compass gait model parameters.

    Supports both kinematic limit-cycle playback and hybrid dynamics simulation.
    """
    # Geometry
    slope_deg: float = 5.0
    leg_length: float = 1.0
    foot_radius: float = 0.04

    # Gait parameters
    step_length: float = 0.34  # For kinematic mode
    step_angle_deg: float = 10.0  # For hybrid mode

    # Dynamics (hybrid mode only)
    gravity: float = 9.81
    stance_damping: float = 0.012
    swing_damping: float = 0.035
    passive_hip_stiffness: float = 0.42
    collision_retention: float = 0.82
    energy_gain_scale: float = 0.42

    # Simulation parameters
    initial_speed: float = 0.24
    fixed_speed: float | None = None  # Auto-computed if None
    convergence: float = 0.58  # For kinematic mode
    steps: int = 32
    dt: float = 0.002
    samples_per_step: int = 120

    @property
    def alpha(self) -> float:
        """Half step angle (rad)."""
        return math.asin(self.step_length / (2.0 * self.leg_length))

    @property
    def alpha_hybrid(self) -> float:
        """Half step angle for hybrid mode (rad)."""
        return math.radians(self.step_angle_deg)

    @property
    def gamma(self) -> float:
        """Slope angle (rad)."""
        return math.radians(self.slope_deg)

    @property
    def computed_fixed_speed(self) -> float:
        """Fixed-point speed for hybrid mode."""
        if self.fixed_speed is not None:
            return self.fixed_speed
        drop = math.sin(self.gamma) * 2.0 * self.leg_length * math.sin(self.alpha_hybrid)
        gain = (
            self.energy_gain_scale
            * 2.0
            * self.gravity
            * max(drop, 1e-8)
            / self.leg_length
        )
        rho = self.collision_retention
        return rho * math.sqrt(max(gain / max(1e-8, 1.0 - rho * rho), 0.0))

    def to_dict(self) -> dict:
        """Convert to dictionary with computed properties."""
        d = asdict(self)
        d["alpha_deg"] = math.degrees(self.alpha)
        d["alpha_hybrid_deg"] = self.step_angle_deg
        d["gamma_rad"] = self.gamma
        d["computed_fixed_speed"] = self.computed_fixed_speed
        return d

    @classmethod
    def from_template(
        cls, template: Literal["kinematic", "hybrid", "steep", "gentle", "fast", "slow"]
    ) -> CompassGaitParams:
        """Factory method for common configurations.

        Args:
            template: Configuration template name
                - "kinematic": v03-style limit cycle playback
                - "hybrid": v05-style hybrid dynamics
                - "steep": Steeper slope (7 deg)
                - "gentle": Gentler slope (3 deg)
                - "fast": Higher speed walking
                - "slow": Lower speed walking

        Returns:
            CompassGaitParams instance
        """
        if template == "kinematic":
            return cls(
                slope_deg=5.0,
                leg_length=1.0,
                foot_radius=0.04,
                step_length=0.34,
                initial_speed=0.24,
                fixed_speed=0.47,
                convergence=0.58,
                steps=32,
                samples_per_step=120,
            )
        elif template == "hybrid":
            return cls(
                slope_deg=5.0,
                leg_length=1.0,
                foot_radius=0.035,
                step_angle_deg=10.0,
                gravity=9.81,
                stance_damping=0.012,
                swing_damping=0.035,
                passive_hip_stiffness=0.42,
                collision_retention=0.82,
                energy_gain_scale=0.42,
                initial_speed=0.28,
                steps=18,
                dt=0.002,
                samples_per_step=80,
            )
        elif template == "steep":
            base = cls.from_template("hybrid")
            return cls(**{**asdict(base), "slope_deg": 7.0})
        elif template == "gentle":
            base = cls.from_template("hybrid")
            return cls(**{**asdict(base), "slope_deg": 3.0})
        elif template == "fast":
            base = cls.from_template("hybrid")
            return cls(**{**asdict(base), "initial_speed": 0.40, "energy_gain_scale": 0.52})
        elif template == "slow":
            base = cls.from_template("hybrid")
            return cls(**{**asdict(base), "initial_speed": 0.18, "energy_gain_scale": 0.32})
        else:
            raise ValueError(f"Unknown template: {template}")


class CompassGait:
    """Compass gait model with MuJoCo integration.

    Provides kinematic and hybrid dynamics simulation modes with clean
    MuJoCo integration for visualization and playback.
    """

    def __init__(self, params: CompassGaitParams):
        """Initialize compass gait model.

        Args:
            params: Model parameters
        """
        self.params = params
        self._model: mujoco.MjModel | None = None
        self._data: mujoco.MjData | None = None

    @classmethod
    def from_template(cls, template: str) -> CompassGait:
        """Create from template configuration.

        Args:
            template: Template name (see CompassGaitParams.from_template)

        Returns:
            CompassGait instance
        """
        params = CompassGaitParams.from_template(template)
        return cls(params)

    def load_mujoco_model(self, xml_path: Path | str) -> None:
        """Load MuJoCo model from XML file.

        Args:
            xml_path: Path to MuJoCo XML model file
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Model file not found: {xml_path}")
        self._model = mujoco.MjModel.from_xml_path(str(xml_path))
        self._data = mujoco.MjData(self._model)

    @property
    def model(self) -> mujoco.MjModel:
        """MuJoCo model (must call load_mujoco_model first)."""
        if self._model is None:
            raise RuntimeError("MuJoCo model not loaded. Call load_mujoco_model() first.")
        return self._model

    @property
    def data(self) -> mujoco.MjData:
        """MuJoCo data (must call load_mujoco_model first)."""
        if self._data is None:
            raise RuntimeError("MuJoCo model not loaded. Call load_mujoco_model() first.")
        return self._data

    def ramp_height(self, x: float) -> float:
        """Compute ramp height at position x."""
        return -math.tan(self.params.gamma) * x

    def sphere_center_clearance(self) -> float:
        """Foot sphere center clearance above ramp."""
        return self.params.foot_radius / math.cos(self.params.gamma)

    def foot_position(
        self, hip_x: float, hip_z: float, theta: float
    ) -> tuple[float, float]:
        """Compute foot position given hip position and leg angle.

        Args:
            hip_x: Hip x position
            hip_z: Hip z position
            theta: Leg angle (rad, positive = forward)

        Returns:
            (foot_x, foot_z)
        """
        return (
            hip_x - self.params.leg_length * math.sin(theta),
            hip_z - self.params.leg_length * math.cos(theta),
        )

    def foot_clearance(
        self, hip_x: float, hip_z: float, theta: float
    ) -> float:
        """Compute foot clearance above ramp.

        Args:
            hip_x: Hip x position
            hip_z: Hip z position
            theta: Leg angle (rad)

        Returns:
            Clearance (m), negative if penetrating
        """
        foot_x, foot_z = self.foot_position(hip_x, hip_z, theta)
        return foot_z - (self.ramp_height(foot_x) + self.sphere_center_clearance())

    def simulate_kinematic(
        self,
    ) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
        """Run kinematic limit-cycle simulation (v03-style).

        Returns:
            (trajectory_rows, poincare_points)
        """
        rows: list[dict[str, float | int | str]] = []
        poincare: list[dict[str, float]] = []
        speed = self.params.initial_speed
        t = 0.0

        for step in range(self.params.steps):
            error = abs(speed - (self.params.fixed_speed or self.params.computed_fixed_speed))
            step_time = self.params.step_length / max(speed, 0.12)
            step_time = float(np.clip(step_time, 0.68, 1.25))

            poincare.append({
                "step": float(step),
                "speed": speed,
                "fixed_speed": self.params.fixed_speed or self.params.computed_fixed_speed,
                "error": error,
                "step_time": step_time,
            })

            for i in range(self.params.samples_per_step):
                phase = i / self.params.samples_per_step
                rows.append(
                    self._kinematic_state(step, phase, t + phase * step_time, speed, error)
                )

            t += step_time
            speed = (self.params.fixed_speed or self.params.computed_fixed_speed) + \
                    self.params.convergence * (speed - (self.params.fixed_speed or self.params.computed_fixed_speed))

        # Final state
        rows.append(
            self._kinematic_state(
                self.params.steps,
                0.0,
                t,
                speed,
                abs(speed - (self.params.fixed_speed or self.params.computed_fixed_speed)),
            )
        )

        return rows, poincare

    def _kinematic_state(
        self, step: int, phase: float, t: float, speed: float, error: float
    ) -> dict[str, float | int | str]:
        """Generate kinematic state for a given step and phase."""
        alpha = self.params.alpha
        stance_x = step * self.params.step_length
        stance_q = -alpha + 2.0 * alpha * phase
        hip_x = stance_x + self.params.leg_length * math.sin(stance_q)
        hip_z = (
            self.ramp_height(stance_x)
            + self.sphere_center_clearance()
            + self.params.leg_length * math.cos(stance_q)
        )

        # Swing leg with clearance
        swing_s = phase * phase * (3.0 - 2.0 * phase)  # smoothstep
        swing_q = alpha - 2.0 * alpha * swing_s
        swing_q -= 0.10 * math.sin(math.pi * phase)

        # Adjust hip height to avoid penetration
        required_hip_z = []
        for q in (stance_q, swing_q):
            foot_x = hip_x - self.params.leg_length * math.sin(q)
            required_hip_z.append(
                self.ramp_height(foot_x)
                + self.sphere_center_clearance()
                + self.params.leg_length * math.cos(q)
            )
        hip_z = max(required_hip_z)

        support = "left" if step % 2 == 0 else "right"
        contact = support if phase < 0.985 else "both"

        if support == "left":
            left_q, right_q = stance_q, swing_q
        else:
            left_q, right_q = swing_q, stance_q

        left_x, left_z = self.foot_position(hip_x, hip_z, left_q)
        right_x, right_z = self.foot_position(hip_x, hip_z, right_q)
        stance_omega = 2.0 * alpha / max(self.params.step_length / speed, 1e-6)
        swing_omega = -stance_omega * (0.4 + 1.2 * math.sin(math.pi * phase) ** 2)

        return {
            "time": t,
            "step": step,
            "phase": phase,
            "support": support,
            "contact": contact,
            "hip_x": hip_x,
            "hip_z": hip_z,
            "left_angle": left_q,
            "right_angle": right_q,
            "left_foot_x": left_x,
            "left_foot_z": left_z,
            "right_foot_x": right_x,
            "right_foot_z": right_z,
            "stance_omega": stance_omega,
            "swing_omega": swing_omega,
            "step_speed": speed,
            "poincare_error": error,
        }

    def simulate_hybrid(
        self,
    ) -> tuple[list[dict[str, float | int | str]], list[dict[str, float]]]:
        """Run hybrid dynamics simulation (v05-style).

        Returns:
            (trajectory_rows, poincare_points)
        """
        rows: list[dict[str, float | int | str]] = []
        poincare: list[dict[str, float]] = []

        alpha = self.params.alpha_hybrid
        y = np.array(
            [
                -alpha,
                alpha,
                self.params.initial_speed,
                -0.35 * self.params.initial_speed,
            ],
            dtype=float,
        )
        t = 0.0
        v_star = self.params.computed_fixed_speed

        for step in range(self.params.steps):
            step_start_t = t
            step_rows: list[dict[str, float | int | str]] = []
            max_step_time = 1.6
            sample_stride = max(
                1, int((max_step_time / self.params.dt) / self.params.samples_per_step)
            )
            event_hit = False

            for i in range(int(max_step_time / self.params.dt)):
                if i % sample_stride == 0:
                    phase = min(1.0, (t - step_start_t) / max_step_time)
                    step_rows.append(self._hybrid_state(t, step, y, phase))

                y_next = self._rk4_step(y, self.params.dt, t)
                if not np.all(np.isfinite(y_next)) or np.max(np.abs(y_next)) > 50:
                    break

                if i > 30 and self._event_value(step, y_next) <= 0:
                    event_t, event_y = self._bisect_event(y, y_next, t, t + self.params.dt, step)
                    t, y = event_t, event_y
                    step_rows.append(self._hybrid_state(t, step, y, 1.0, "touchdown"))
                    event_hit = True
                    break

                y = y_next
                t += self.params.dt

            pre = y.copy()
            rows.extend(step_rows)
            post = self._impact_map(pre)
            speed_error = abs(float(post[2]) - v_star)

            poincare.append({
                "step": float(step),
                "time": t,
                "theta_stance": float(post[0]),
                "theta_swing": float(post[1]),
                "omega_stance": float(post[2]),
                "omega_swing": float(post[3]),
                "fixed_speed": v_star,
                "speed_error": speed_error,
                "event_hit": 1.0 if event_hit else 0.0,
                "step_duration": t - step_start_t,
            })

            y = post
            rows.append(self._hybrid_state(t, step + 1, y, 0.0, "impact_map"))

        return rows, poincare

    def _hybrid_state(
        self,
        t: float,
        step: int,
        y: np.ndarray,
        phase: float,
        event: str = "",
    ) -> dict[str, float | int | str]:
        """Generate hybrid dynamics state."""
        theta_stance, theta_swing, omega_stance, omega_swing = [float(v) for v in y]
        stance_x = step * 2.0 * self.params.leg_length * math.sin(self.params.alpha_hybrid)
        stance_z = self.ramp_height(stance_x) + self.sphere_center_clearance()
        hip_x = stance_x + self.params.leg_length * math.sin(theta_stance)
        hip_z = stance_z + self.params.leg_length * math.cos(theta_stance)
        swing_x, swing_z = self.foot_position(hip_x, hip_z, theta_swing)

        support = "left" if step % 2 == 0 else "right"
        if support == "left":
            left_angle, right_angle = theta_stance, theta_swing
            left_foot_x, left_foot_z = stance_x, stance_z
            right_foot_x, right_foot_z = swing_x, swing_z
        else:
            left_angle, right_angle = theta_swing, theta_stance
            left_foot_x, left_foot_z = swing_x, swing_z
            right_foot_x, right_foot_z = stance_x, stance_z

        return {
            "time": t,
            "step": step,
            "phase": phase,
            "support": support,
            "event": event,
            "theta_stance": theta_stance,
            "theta_swing": theta_swing,
            "omega_stance": omega_stance,
            "omega_swing": omega_swing,
            "left_angle": left_angle,
            "right_angle": right_angle,
            "hip_x": hip_x,
            "hip_z": hip_z,
            "left_foot_x": left_foot_x,
            "left_foot_z": left_foot_z,
            "right_foot_x": right_foot_x,
            "right_foot_z": right_foot_z,
            "swing_clearance": self.foot_clearance(hip_x, hip_z, theta_swing),
        }

    def _dynamics(self, _t: float, y: np.ndarray) -> np.ndarray:
        """Hybrid dynamics equations."""
        theta_stance, theta_swing, omega_stance, omega_swing = y
        drop = math.sin(self.params.gamma) * 2.0 * self.params.leg_length * math.sin(self.params.alpha_hybrid)
        gain = (
            self.params.energy_gain_scale
            * 2.0
            * self.params.gravity
            * max(drop, 1e-8)
            / self.params.leg_length
        )
        d_omega_stance = gain / max(4.0 * self.params.alpha_hybrid, 1e-8)
        target_swing = -theta_stance
        d_omega_swing = (
            -self.params.passive_hip_stiffness * (theta_swing - target_swing)
            - self.params.swing_damping * omega_swing
            - 0.10 * self.params.gravity / self.params.leg_length * math.sin(theta_swing)
        )
        return np.array([omega_stance, omega_swing, d_omega_stance, d_omega_swing], dtype=float)

    def _rk4_step(self, y: np.ndarray, dt: float, t: float) -> np.ndarray:
        """RK4 integration step."""
        k1 = self._dynamics(t, y)
        k2 = self._dynamics(t + 0.5 * dt, y + 0.5 * dt * k1)
        k3 = self._dynamics(t + 0.5 * dt, y + 0.5 * dt * k2)
        k4 = self._dynamics(t + dt, y + dt * k3)
        return y + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0

    def _event_value(self, step: int, y: np.ndarray) -> float:
        """Event detection: stance leg reaches target angle."""
        return self.params.alpha_hybrid - float(y[0])

    def _bisect_event(
        self,
        y0: np.ndarray,
        y1: np.ndarray,
        t0: float,
        t1: float,
        step: int,
    ) -> tuple[float, np.ndarray]:
        """Bisection search for event time."""
        lo_t, hi_t = t0, t1
        lo_y, hi_y = y0.copy(), y1.copy()
        for _ in range(20):
            mid_t = 0.5 * (lo_t + hi_t)
            mid_y = self._rk4_step(lo_y, mid_t - lo_t, lo_t)
            if self._event_value(step, mid_y) <= 0:
                hi_t, hi_y = mid_t, mid_y
            else:
                lo_t, lo_y = mid_t, mid_y
        return hi_t, hi_y

    def _impact_map(self, pre: np.ndarray) -> np.ndarray:
        """Impact map: instantaneous collision at heel strike."""
        omega_stance = float(pre[2])
        pre_speed = max(0.02, abs(omega_stance))
        post_speed = self.params.collision_retention * pre_speed
        post_speed = max(0.06, post_speed)
        alpha = self.params.alpha_hybrid
        return np.array(
            [-alpha, alpha, post_speed, -0.35 * post_speed], dtype=float
        )

    def set_mujoco_state(self, state: dict[str, float]) -> None:
        """Set MuJoCo model state from trajectory row.

        Args:
            state: State dictionary (from simulate_kinematic or simulate_hybrid)
        """
        if self._model is None or self._data is None:
            raise RuntimeError("MuJoCo model not loaded")

        # Set joint positions
        try:
            hip_x_idx = self._model.joint("hip_x").qposadr[0]
            hip_z_idx = self._model.joint("hip_z").qposadr[0]
            left_hip_idx = self._model.joint("left_hip").qposadr[0]
            right_hip_idx = self._model.joint("right_hip").qposadr[0]

            self._data.qpos[hip_x_idx] = state["hip_x"]
            self._data.qpos[hip_z_idx] = state["hip_z"]
            self._data.qpos[left_hip_idx] = state["left_angle"]
            self._data.qpos[right_hip_idx] = state["right_angle"]

            mujoco.mj_forward(self._model, self._data)
        except KeyError as e:
            raise ValueError(f"Joint not found in model: {e}")


def smoothstep(u: float) -> float:
    """Smooth interpolation function (C1 continuous)."""
    return u * u * (3.0 - 2.0 * u)

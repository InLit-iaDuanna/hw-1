"""V17 状态估计器：带噪声测量 → 控制器可用的估计状态。

核心组件：
- JointKalmanFilter: 2-state [θ, ω] Kalman 滤波器，平滑编码器量化噪声
- HipFK: 从支撑脚 + 关节角度正运动学计算 hip 位置/速度
- StateEstimator: 统一接口
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from sensor_model import SensorReading


@dataclass
class EstimatedState:
    hip_x: float
    hip_z: float
    hip_vx: float
    hip_vz: float
    joint_angles: np.ndarray
    joint_velocities: np.ndarray
    left_contact: bool
    right_contact: bool


class JointKalmanFilter:
    """2-state Kalman filter: state = [angle, velocity]."""

    def __init__(
        self,
        dt: float,
        process_accel_std: float = 60.0,
        measurement_std: float = 0.77e-3,
    ):
        self.dt = dt
        self._x = np.zeros(2)
        self._P = np.diag([measurement_std**2, (process_accel_std * dt) ** 2])
        q_a = process_accel_std**2
        self._Q = np.array(
            [
                [dt**4 / 4 * q_a, dt**3 / 2 * q_a],
                [dt**3 / 2 * q_a, dt**2 * q_a],
            ]
        )
        self._R = measurement_std**2
        self._F = np.array([[1.0, dt], [0.0, 1.0]])
        self._H = np.array([[1.0, 0.0]])
        self._initialized = False

    def update(self, z_angle: float) -> tuple[float, float]:
        if not self._initialized:
            self._x[0] = z_angle
            self._x[1] = 0.0
            self._initialized = True
            return float(self._x[0]), float(self._x[1])

        x_pred = self._F @ self._x
        P_pred = self._F @ self._P @ self._F.T + self._Q

        y = z_angle - self._H @ x_pred
        S = (self._H @ P_pred @ self._H.T)[0, 0] + self._R
        K = (P_pred @ self._H.T) / S

        self._x = x_pred + K.flatten() * float(y)
        self._P = (np.eye(2) - K @ self._H) @ P_pred
        return float(self._x[0]), float(self._x[1])


class HipFK:
    """从支撑脚位置 + 关节角度正运动学估计 hip 位置/速度。"""

    def __init__(
        self,
        thigh_length: float,
        shank_length: float,
        foot_radius: float,
        slope_rad: float,
        dt: float,
    ):
        self.thigh_length = thigh_length
        self.shank_length = shank_length
        self.foot_radius = foot_radius
        self.slope_rad = slope_rad
        self.dt = dt
        self._support_foot_x: float = 0.0
        self._support_foot_z: float = 0.0
        self._last_hip_x: float | None = None
        self._last_hip_z: float | None = None
        self._vx_filter = _ScalarLPF(alpha=0.15)
        self._vz_filter = _ScalarLPF(alpha=0.15)

    def set_support_foot(
        self, hip_x_est: float, hip_z_est: float, hip_angle: float, knee_angle: float
    ):
        """在足切换时，用当前 hip 估计 + FK 向下算出支撑脚位置。"""
        shank_angle = hip_angle + knee_angle
        knee_x = hip_x_est - self.thigh_length * math.sin(hip_angle)
        knee_z = hip_z_est - self.thigh_length * math.cos(hip_angle)
        foot_x = knee_x - self.shank_length * math.sin(shank_angle)
        foot_z = knee_z - self.shank_length * math.cos(shank_angle)
        self._support_foot_x = foot_x
        self._support_foot_z = foot_z

    def estimate(
        self, hip_angle: float, knee_angle: float
    ) -> tuple[float, float, float, float]:
        """FK 向上：foot → knee → hip。返回 (hip_x, hip_z, hip_vx, hip_vz)。"""
        shank_angle = hip_angle + knee_angle
        knee_x = self._support_foot_x + self.shank_length * math.sin(shank_angle)
        knee_z = self._support_foot_z + self.shank_length * math.cos(shank_angle)
        hip_x = knee_x + self.thigh_length * math.sin(hip_angle)
        hip_z = knee_z + self.thigh_length * math.cos(hip_angle)

        if self._last_hip_x is not None:
            raw_vx = (hip_x - self._last_hip_x) / self.dt
            raw_vz = (hip_z - self._last_hip_z) / self.dt
            vx = self._vx_filter.update(raw_vx)
            vz = self._vz_filter.update(raw_vz)
        else:
            vx, vz = 0.0, 0.0

        self._last_hip_x = hip_x
        self._last_hip_z = hip_z
        return hip_x, hip_z, vx, vz

    def init_from_ground_truth(
        self, hip_x: float, hip_z: float, hip_angle: float, knee_angle: float
    ):
        """初始化：用 ground truth hip 位置设置初始支撑脚。"""
        self.set_support_foot(hip_x, hip_z, hip_angle, knee_angle)
        self._last_hip_x = hip_x
        self._last_hip_z = hip_z


class _ScalarLPF:
    """一阶低通滤波器。"""

    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self._y: float | None = None

    def update(self, x: float) -> float:
        if self._y is None:
            self._y = x
        else:
            self._y = self.alpha * x + (1.0 - self.alpha) * self._y
        return self._y


class StateEstimator:
    """V17 状态估计器统一接口。"""

    def __init__(
        self,
        thigh_length: float,
        shank_length: float,
        foot_radius: float,
        slope_rad: float,
        dt: float,
    ):
        self.dt = dt
        self._joint_filters = [JointKalmanFilter(dt) for _ in range(4)]
        self._hip_fk = HipFK(thigh_length, shank_length, foot_radius, slope_rad, dt)
        self._state = EstimatedState(
            hip_x=0.0,
            hip_z=0.0,
            hip_vx=0.0,
            hip_vz=0.0,
            joint_angles=np.zeros(4),
            joint_velocities=np.zeros(4),
            left_contact=False,
            right_contact=False,
        )
        self._support_foot = "left"
        self._initialized = False

    def init_from_ground_truth(self, data, support_foot: str):
        """用 ground truth 初始化（仿真开始时调用一次）。"""
        hip_x = float(data.qpos[0])
        hip_z = float(data.qpos[1])
        support_hip_idx = 2 if support_foot == "left" else 5
        support_knee_idx = 3 if support_foot == "left" else 6
        hip_angle = float(data.qpos[support_hip_idx])
        knee_angle = float(data.qpos[support_knee_idx])
        self._hip_fk.init_from_ground_truth(hip_x, hip_z, hip_angle, knee_angle)
        self._support_foot = support_foot
        self._initialized = True

    def update(self, reading: SensorReading, support_foot: str):
        """每步更新估计状态。"""
        angles = np.zeros(4)
        velocities = np.zeros(4)
        for i in range(4):
            a, v = self._joint_filters[i].update(float(reading.joint_angles[i]))
            angles[i] = a
            velocities[i] = v

        if support_foot != self._support_foot:
            sup_idx = 0 if support_foot == "left" else 2
            self._hip_fk.set_support_foot(
                self._state.hip_x,
                self._state.hip_z,
                angles[sup_idx],
                angles[sup_idx + 1],
            )
            self._support_foot = support_foot

        sup_idx = 0 if support_foot == "left" else 2
        hip_x, hip_z, hip_vx, hip_vz = self._hip_fk.estimate(
            angles[sup_idx], angles[sup_idx + 1]
        )

        self._state = EstimatedState(
            hip_x=hip_x,
            hip_z=hip_z,
            hip_vx=hip_vx,
            hip_vz=hip_vz,
            joint_angles=angles,
            joint_velocities=velocities,
            left_contact=reading.left_contact_raw,
            right_contact=reading.right_contact_raw,
        )

    def get_state(self) -> EstimatedState:
        return self._state

"""V17 状态估计器回归测试。

验证传感器模型和状态估计器的数值稳定性。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HW1_ROOT = Path(__file__).resolve().parents[2]
V17_DIR = HW1_ROOT / "v17_state_estimation"
sys.path.insert(0, str(V17_DIR))

from state_estimator import EstimatedState, HipFK, JointKalmanFilter


class TestJointKalmanFilter:
    """测试关节 Kalman 滤波器。"""

    def test_filter_initialization(self):
        """滤波器应正确初始化。"""
        dt = 0.001
        kf = JointKalmanFilter(dt=dt, process_accel_std=60.0, measurement_std=0.77e-3)
        assert kf.dt == dt
        assert not kf._initialized

    def test_first_update_initializes(self):
        """第一次更新应初始化滤波器。"""
        kf = JointKalmanFilter(dt=0.001)
        angle, velocity = kf.update(z_angle=0.5)

        assert kf._initialized
        assert angle == 0.5
        assert velocity == 0.0  # 首次速度为 0

    def test_filter_smooths_noise(self):
        """滤波器应平滑测量噪声。"""
        kf = JointKalmanFilter(dt=0.001, measurement_std=0.01)

        # 真实信号：恒定角度 0.5
        true_angle = 0.5
        rng = np.random.default_rng(42)

        # 加噪声测量
        noisy_measurements = [true_angle + rng.normal(0, 0.01) for _ in range(100)]

        estimates = [kf.update(z)[0] for z in noisy_measurements]

        # 后半段估计应更接近真值（滤波器收敛）
        late_estimates = estimates[50:]
        late_error = np.std(late_estimates)

        # 估计的标准差应小于测量噪声
        assert late_error < 0.01

    def test_filter_tracks_constant_velocity(self):
        """滤波器应跟踪匀速运动。"""
        dt = 0.001
        kf = JointKalmanFilter(dt=dt, process_accel_std=10.0, measurement_std=1e-6)

        # 匀速运动：角度 = 初值 + 速度 * 时间
        initial_angle = 0.0
        angular_velocity = 1.0  # rad/s

        angles = []
        velocities = []

        for i in range(500):
            true_angle = initial_angle + angular_velocity * i * dt
            angle_est, vel_est = kf.update(true_angle)
            angles.append(angle_est)
            velocities.append(vel_est)

        # 速度估计应收敛到真实速度
        final_velocity_estimates = velocities[-50:]
        avg_vel = np.mean(final_velocity_estimates)
        assert abs(avg_vel - angular_velocity) < 0.1

    def test_filter_deterministic(self):
        """相同输入应产生相同输出。"""

        def run_filter():
            kf = JointKalmanFilter(dt=0.001)
            measurements = [0.1, 0.2, 0.3, 0.4, 0.5]
            return [kf.update(z) for z in measurements]

        results1 = run_filter()
        results2 = run_filter()

        for (a1, v1), (a2, v2) in zip(results1, results2):
            assert a1 == a2
            assert v1 == v2


class TestHipFK:
    """测试 hip 正运动学估计。"""

    def test_fk_initialization(self):
        """FK 应正确初始化。"""
        fk = HipFK(
            thigh_length=0.48,
            shank_length=0.52,
            foot_radius=0.04,
            slope_rad=0.0,
            dt=0.001,
        )
        assert fk.thigh_length == 0.48
        assert fk.shank_length == 0.52

    def test_fk_straight_leg(self):
        """直腿（零关节角）应垂直站立。"""
        fk = HipFK(
            thigh_length=0.5,
            shank_length=0.5,
            foot_radius=0.0,
            slope_rad=0.0,
            dt=0.001,
        )

        # 设置支撑脚在原点
        fk._support_foot_x = 0.0
        fk._support_foot_z = 0.0

        # 直腿：hip 和 knee 角度都为 0
        hip_x, hip_z, _, _ = fk.estimate(hip_angle=0.0, knee_angle=0.0)

        # hip 应正好在脚正上方，高度 = 腿长
        assert abs(hip_x - 0.0) < 1e-6
        assert abs(hip_z - 1.0) < 1e-6

    def test_fk_hip_flexion(self):
        """hip 屈曲应使 hip x 坐标前移。"""
        fk = HipFK(
            thigh_length=0.5,
            shank_length=0.5,
            foot_radius=0.0,
            slope_rad=0.0,
            dt=0.001,
        )

        fk._support_foot_x = 0.0
        fk._support_foot_z = 0.0

        # hip 前屈 30°（0.524 rad），knee 直
        import math

        hip_angle = math.radians(30)
        hip_x, hip_z, _, _ = fk.estimate(hip_angle=hip_angle, knee_angle=0.0)

        # hip x 应为正（前移）
        assert hip_x > 0.2
        # hip z 应低于直立
        assert hip_z < 1.0

    def test_fk_velocity_estimation(self):
        """FK 应估计 hip 速度。"""
        dt = 0.01
        fk = HipFK(
            thigh_length=0.5,
            shank_length=0.5,
            foot_radius=0.0,
            slope_rad=0.0,
            dt=dt,
        )

        fk._support_foot_x = 0.0
        fk._support_foot_z = 0.0

        # 匀速改变 hip 角度
        import math

        results = []
        for i in range(10):
            hip_angle = math.radians(i * 2)  # 逐渐增大角度
            hip_x, hip_z, vx, vz = fk.estimate(hip_angle=hip_angle, knee_angle=0.0)
            results.append((hip_x, hip_z, vx, vz))

        # 速度应非零（角度在变化）
        velocities_x = [r[2] for r in results[2:]]  # 跳过初始化
        assert any(abs(v) > 0.01 for v in velocities_x)


class TestEstimatedState:
    """测试估计状态数据类。"""

    def test_state_creation(self):
        """应能创建估计状态。"""
        state = EstimatedState(
            hip_x=1.0,
            hip_z=0.9,
            hip_vx=0.5,
            hip_vz=0.0,
            joint_angles=np.array([0.1, 0.2, 0.3, 0.4]),
            joint_velocities=np.array([0.01, 0.02, 0.03, 0.04]),
            left_contact=True,
            right_contact=False,
        )

        assert state.hip_x == 1.0
        assert state.hip_z == 0.9
        assert state.left_contact is True
        assert state.right_contact is False

    def test_state_arrays(self):
        """状态应包含数组数据。"""
        angles = np.array([0.1, 0.2, 0.3, 0.4])
        velocities = np.array([0.01, 0.02, 0.03, 0.04])

        state = EstimatedState(
            hip_x=1.0,
            hip_z=0.9,
            hip_vx=0.5,
            hip_vz=0.0,
            joint_angles=angles,
            joint_velocities=velocities,
            left_contact=True,
            right_contact=False,
        )

        np.testing.assert_array_equal(state.joint_angles, angles)
        np.testing.assert_array_equal(state.joint_velocities, velocities)


class TestV17Integration:
    """V17 组件集成测试。"""

    def test_kalman_filter_with_realistic_noise(self):
        """用真实编码器噪声测试滤波器。"""
        dt = 0.001
        encoder_resolution = 0.77e-3  # rad，真实 AS5048A 分辨率
        kf = JointKalmanFilter(dt=dt, measurement_std=encoder_resolution)

        # 模拟摆动关节
        import math

        rng = np.random.default_rng(42)
        true_trajectory = [
            0.3 * math.sin(2 * math.pi * 2.0 * i * dt) for i in range(1000)
        ]

        # 加量化噪声
        noisy_measurements = [
            angle + rng.normal(0, encoder_resolution) for angle in true_trajectory
        ]

        estimates = [kf.update(z)[0] for z in noisy_measurements]

        # 后期估计误差应小于测量噪声
        late_errors = [
            abs(est - true) for est, true in zip(estimates[500:], true_trajectory[500:])
        ]
        assert np.mean(late_errors) < encoder_resolution

    def test_fk_chain_consistency(self):
        """FK 链式计算应保持一致性。"""
        fk = HipFK(
            thigh_length=0.48,
            shank_length=0.52,
            foot_radius=0.04,
            slope_rad=0.0,
            dt=0.001,
        )

        # 设置初始支撑脚
        fk._support_foot_x = 0.0
        fk._support_foot_z = 0.0

        import math

        hip_angle = math.radians(20)
        knee_angle = math.radians(10)

        # 多次估计应保持一致（无状态更新）
        result1 = fk.estimate(hip_angle, knee_angle)
        result2 = fk.estimate(hip_angle, knee_angle)

        # 位置应一致（速度可能因滤波略有不同）
        assert abs(result1[0] - result2[0]) < 1e-6
        assert abs(result1[1] - result2[1]) < 1e-6

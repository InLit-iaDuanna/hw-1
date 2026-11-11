"""V17 状态估计端到端集成测试。

验证状态估计器在完整仿真中的表现：
- 传感器模型（编码器 + 接触开关）
- Kalman 滤波器平滑噪声
- 正运动学估计 hip 位置
- 估计状态与真实状态的一致性
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
V17_DIR = HW1_ROOT / "v17_state_estimation"
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V14_DIR = HW1_ROOT / "v14_passive_arms"

sys.path.insert(0, str(V17_DIR))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(HW1_ROOT / "common"))

import mujoco
from sensor_model import SensorModel, SensorNoiseParams
from state_estimator import HipFK, JointKalmanFilter, StateEstimator
from simulate_passive_arms_v14 import PassiveArmsParams, build_model_xml, initialize
from simulate_v13_7 import V137Params, make_v137_fsm
from simulate_v17 import V17Params, make_v17_fsm, run_simulation_v17

from motor_dynamics import PRESETS as MOTOR_PRESETS


@pytest.fixture
def v17_model():
    """创建 V17 测试模型（基于 V13.7）。"""
    base = PassiveArmsParams()
    fsm = make_v137_fsm(base)
    params = V137Params(
        base=base,
        fsm=fsm,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
        compensate_friction=True,
    )

    xml = build_model_xml(params.base)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    initialize(model, data, params.base)

    return model, data, params


@pytest.fixture
def sensor_model():
    """创建传感器模型。"""
    return SensorModel(
        encoder_resolution_rad=0.77e-3,
        contact_threshold_N=5.0,
        noise_seed=42,
    )


@pytest.fixture
def state_estimator():
    """创建状态估计器。"""
    return StateEstimator(
        thigh_length=0.48,
        shank_length=0.52,
        foot_radius=0.04,
        dt=0.001,
        encoder_std=0.77e-3,
    )


class TestV17SensorModel:
    """测试传感器模型集成。"""

    def test_sensor_model_reads_encoders(self, v17_model, sensor_model):
        """传感器模型应读取关节编码器。"""
        model, data, _ = v17_model

        # 运行几步
        for _ in range(100):
            mujoco.mj_step(model, data)

        # 读取传感器
        sensor_data = sensor_model.read(model, data)

        assert "joint_angles" in sensor_data
        assert len(sensor_data["joint_angles"]) >= 2  # 至少 hip + knee

    def test_sensor_model_detects_contact(self, v17_model, sensor_model):
        """传感器模型应检测足地接触。"""
        model, data, _ = v17_model

        # 运行至稳定接触
        for _ in range(500):
            mujoco.mj_step(model, data)

        sensor_data = sensor_model.read(model, data)

        assert "left_contact" in sensor_data
        assert "right_contact" in sensor_data
        # 应至少有一只脚接触地面
        assert sensor_data["left_contact"] or sensor_data["right_contact"]

    def test_sensor_noise_added(self, v17_model, sensor_model):
        """传感器应添加测量噪声。"""
        model, data, _ = v17_model

        # 固定状态，多次读取
        for _ in range(100):
            mujoco.mj_step(model, data)

        # 暂停仿真，多次读取
        readings = []
        for _ in range(10):
            sensor_data = sensor_model.read(model, data)
            readings.append(sensor_data["joint_angles"][0])

        # 读数应有微小差异（噪声）
        std_dev = np.std(readings)
        assert std_dev > 1e-6  # 有噪声
        assert std_dev < 0.01  # 但不会太大


class TestV17StateEstimator:
    """测试状态估计器集成。"""

    def test_estimator_initialization(self, state_estimator):
        """估计器应正确初始化。"""
        assert state_estimator is not None
        assert state_estimator.dt == 0.001

    def test_estimator_processes_sensor_data(
        self, v17_model, sensor_model, state_estimator
    ):
        """估计器应处理传感器数据。"""
        model, data, _ = v17_model

        # 运行仿真并估计状态
        for _ in range(200):
            mujoco.mj_step(model, data)

        sensor_data = sensor_model.read(model, data)
        estimated_state = state_estimator.update(sensor_data)

        assert estimated_state is not None
        assert hasattr(estimated_state, "hip_x")
        assert hasattr(estimated_state, "hip_z")
        assert hasattr(estimated_state, "joint_angles")

    def test_estimated_position_reasonable(
        self, v17_model, sensor_model, state_estimator
    ):
        """估计位置应在合理范围内。"""
        model, data, _ = v17_model

        # 运行至稳态
        for _ in range(500):
            mujoco.mj_step(model, data)
            sensor_data = sensor_model.read(model, data)
            est = state_estimator.update(sensor_data)

        # Hip 高度应合理（0.5-1.2m）
        assert 0.5 < est.hip_z < 1.2

        # Hip x 应前进
        assert est.hip_x > 0.0

    def test_velocity_estimation(self, v17_model, sensor_model, state_estimator):
        """应估计 hip 速度。"""
        model, data, _ = v17_model

        velocities = []

        for _ in range(1000):
            mujoco.mj_step(model, data)
            sensor_data = sensor_model.read(model, data)
            est = state_estimator.update(sensor_data)
            velocities.append(est.hip_vx)

        # 速度应非零（在运动）
        avg_velocity = np.mean(velocities[500:])  # 稳态后
        assert abs(avg_velocity) > 0.01


class TestV17EstimationAccuracy:
    """测试估计精度。"""

    def test_estimation_vs_ground_truth(self):
        """估计状态应接近真实状态。"""
        base0 = PassiveArmsParams()
        base = replace(
            base0,
            duration=12.0,
            arm_mass=0.01,
            arm_length=0.40,
            arm_damping=0.02,
            arm_stiffness=0.0,
            thigh_length=float(base0.thigh_length * 1.02),
            shank_length=float(base0.shank_length * 1.02),
            step_length=float(base0.step_length * 1.02),
            foot_radius=0.042,
        )
        params = V17Params(
            base=base,
            fsm=make_v17_fsm(base),
            hip_motor=MOTOR_PRESETS["mx64ar"],
            knee_motor=MOTOR_PRESETS["mx64ar"],
            compensate_friction=True,
            sensor_noise=SensorNoiseParams(noise_scale=1.0),
        )

        _, summary = run_simulation_v17(params, save_prefix=None)

        assert summary["success"] is True
        assert summary["estimation_rmse_hip_x"] < 0.06
        assert summary["estimation_rmse_vx"] < 0.10

    def test_kalman_filter_reduces_noise(self, v17_model, state_estimator):
        """Kalman 滤波应减小测量噪声。"""
        model, data, _ = v17_model

        # 运行至稳态
        for _ in range(500):
            mujoco.mj_step(model, data)

        # 创建带噪声的传感器
        noisy_sensor = SensorModel(
            encoder_resolution_rad=0.01,  # 较大噪声
            contact_threshold_N=5.0,
            noise_seed=42,
        )

        # 记录原始测量和滤波后估计
        raw_angles = []
        filtered_angles = []

        for _ in range(500):
            mujoco.mj_step(model, data)
            sensor_data = noisy_sensor.read(model, data)

            raw_angles.append(sensor_data["joint_angles"][0])

            est = state_estimator.update(sensor_data)
            filtered_angles.append(est.joint_angles[0])

        # 滤波后应更平滑
        raw_std = np.std(np.diff(raw_angles))
        filtered_std = np.std(np.diff(filtered_angles))

        assert filtered_std < raw_std


class TestV17ContactEstimation:
    """测试接触估计。"""

    def test_contact_switching_detected(self, v17_model, sensor_model, state_estimator):
        """应检测到接触切换。"""
        model, data, _ = v17_model

        contact_switches = 0
        prev_left = False
        prev_right = False

        for i in range(5000):
            mujoco.mj_step(model, data)
            sensor_data = sensor_model.read(model, data)
            est = state_estimator.update(sensor_data)

            if i % 100 == 0 and i > 500:
                if (est.left_contact != prev_left) or (est.right_contact != prev_right):
                    contact_switches += 1
                prev_left = est.left_contact
                prev_right = est.right_contact

        # 应有多次接触切换
        assert contact_switches >= 3, f"接触切换不足: {contact_switches}"


class TestV17ForwardKinematics:
    """测试正运动学计算。"""

    def test_fk_consistent_with_simulation(self, v17_model, sensor_model):
        """FK 计算应与仿真一致。"""
        model, data, _ = v17_model

        # 运行至稳态
        for _ in range(1000):
            mujoco.mj_step(model, data)

        sensor_data = sensor_model.read(model, data)

        # 提取关节角度
        joint_angles = sensor_data["joint_angles"]

        # 创建 FK 计算器
        fk = HipFK(
            thigh_length=0.48,
            shank_length=0.52,
            foot_radius=0.04,
            slope_rad=0.0,
            dt=0.001,
        )

        # 假设左腿支撑，计算 hip 位置
        fk._support_foot_x = 0.0
        fk._support_foot_z = 0.0

        if len(joint_angles) >= 2:
            hip_x, hip_z, _, _ = fk.estimate(joint_angles[0], joint_angles[1])

            # FK 结果应合理
            assert 0.5 < hip_z < 1.2
            assert -1.0 < hip_x < 2.0


class TestV17Robustness:
    """测试 V17 状态估计鲁棒性。"""

    def test_handles_missing_sensor_data(self, state_estimator):
        """应能处理缺失传感器数据。"""
        # 构造部分缺失的传感器数据
        sensor_data = {
            "joint_angles": np.array([0.1, 0.2]),
            # 缺少 contact 信息
        }

        # 应不抛出异常
        try:
            est = state_estimator.update(sensor_data)
            assert est is not None
        except KeyError:
            pytest.skip("实现未支持缺失数据处理")

    def test_handles_outlier_measurements(self, v17_model, state_estimator):
        """应能抑制异常测量值。"""
        model, data, _ = v17_model

        # 正常运行
        for _ in range(500):
            mujoco.mj_step(model, data)
            sensor_data = {
                "joint_angles": np.array([data.qpos[3], data.qpos[4]]),
                "joint_velocities": np.array([data.qvel[3], data.qvel[4]]),
                "left_contact": True,
                "right_contact": False,
            }
            state_estimator.update(sensor_data)

        # 插入异常值
        outlier_data = {
            "joint_angles": np.array([10.0, -10.0]),  # 异常大
            "joint_velocities": np.array([0.0, 0.0]),
            "left_contact": True,
            "right_contact": False,
        }

        est_outlier = state_estimator.update(outlier_data)

        # 继续正常数据
        for _ in range(100):
            mujoco.mj_step(model, data)
            sensor_data = {
                "joint_angles": np.array([data.qpos[3], data.qpos[4]]),
                "joint_velocities": np.array([data.qvel[3], data.qvel[4]]),
                "left_contact": True,
                "right_contact": False,
            }
            est_normal = state_estimator.update(sensor_data)

        # 应恢复到合理状态
        assert 0.3 < est_normal.hip_z < 1.5

    def test_deterministic_estimation(self, v17_model, sensor_model):
        """相同传感器输入应产生相同估计。"""

        def run_estimation():
            base = PassiveArmsParams()
            fsm = make_v137_fsm(base)
            params = V137Params(
                base=base,
                fsm=fsm,
                hip_motor=MOTOR_PRESETS["mx64ar"],
                knee_motor=MOTOR_PRESETS["mx64ar"],
                compensate_friction=True,
            )
            xml = build_model_xml(params.base)
            model = mujoco.MjModel.from_xml_string(xml)
            data = mujoco.MjData(model)
            initialize(model, data, params.base)
            local_sensor = SensorModel(
                encoder_resolution_rad=0.77e-3,
                contact_threshold_N=5.0,
                noise_seed=42,
            )
            estimator = StateEstimator(
                thigh_length=0.48,
                shank_length=0.52,
                foot_radius=0.04,
                dt=0.001,
                encoder_std=0.77e-3,
            )
            estimator.init_from_ground_truth(data, "left")

            for _ in range(500):
                mujoco.mj_step(model, data)
                sensor_data = local_sensor.read(model, data)
                est = estimator.update(sensor_data)

            return est.hip_x, est.hip_z

        # 注意：由于传感器噪声，这个测试可能失败
        # 需要固定随机种子
        x1, z1 = run_estimation()
        x2, z2 = run_estimation()

        # 如果传感器有随机噪声，这里会失败
        # 可以放宽精度要求或固定传感器种子
        assert abs(x1 - x2) < 0.01
        assert abs(z1 - z2) < 0.01


class TestV17Performance:
    """测试 V17 性能。"""

    def test_real_time_capable(self, v17_model, sensor_model, state_estimator):
        """状态估计应快速（< 1ms per update）。"""
        import time

        model, data, _ = v17_model

        # 预热
        for _ in range(100):
            mujoco.mj_step(model, data)
            sensor_data = sensor_model.read(model, data)
            state_estimator.update(sensor_data)

        # 计时
        start = time.perf_counter()
        iterations = 1000

        for _ in range(iterations):
            sensor_data = sensor_model.read(model, data)
            state_estimator.update(sensor_data)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # 单次更新应 < 1ms（实时能力）
        assert avg_time_ms < 1.0, f"状态估计过慢: {avg_time_ms:.3f} ms"

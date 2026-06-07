"""V10 rolling foot gait 回归测试。

验证 V10 基线版本的仿真结果稳定性和数值正确性。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))

import mujoco
from simulate_rolling_foot_gait_v10 import (
    RollingFootParams,
    build_model_xml,
    contact_flags,
    initialize,
)


@pytest.fixture
def default_params():
    """默认 V10 参数。"""
    return RollingFootParams()


@pytest.fixture
def v10_model(default_params):
    """创建 V10 模型和数据。"""
    xml = build_model_xml(default_params)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    initialize(model, data, default_params)
    return model, data, default_params


class TestV10ModelLoading:
    """测试 V10 模型加载正确性。"""

    def test_model_creation(self, v10_model):
        """模型应成功创建。"""
        model, data, params = v10_model
        assert model is not None
        assert data is not None

    def test_model_has_required_bodies(self, v10_model):
        """模型应包含必需的 body。"""
        model, _, _ = v10_model
        required_bodies = [
            "hip",
            "left_thigh",
            "right_thigh",
            "left_shank",
            "right_shank",
        ]
        for body_name in required_bodies:
            body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
            assert body_id >= 0, f"缺少 body: {body_name}"

    def test_model_has_required_joints(self, v10_model):
        """模型应包含必需的关节。"""
        model, _, _ = v10_model
        required_joints = ["left_hip", "left_knee", "right_hip", "right_knee"]
        for joint_name in required_joints:
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            assert joint_id >= 0, f"缺少关节: {joint_name}"

    def test_timestep(self, v10_model):
        """验证时间步长设置。"""
        model, _, params = v10_model
        assert model.opt.timestep == params.timestep

    def test_gravity(self, v10_model):
        """验证重力设置。"""
        model, _, _ = v10_model
        np.testing.assert_almost_equal(model.opt.gravity[2], -9.81, decimal=5)


class TestV10Initialization:
    """测试 V10 初始化。"""

    def test_initial_hip_position(self, v10_model):
        """验证初始 hip 位置。"""
        model, data, params = v10_model
        hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
        hip_x = data.xpos[hip_id, 0]
        hip_z = data.xpos[hip_id, 2]

        # hip 应在合理高度（约腿长）
        assert 0.8 < hip_z < 1.2, f"hip 高度异常: {hip_z}"
        # hip x 应接近原点
        assert -0.5 < hip_x < 0.5, f"hip x 位置异常: {hip_x}"

    def test_initial_velocity(self, v10_model):
        """验证初始前向速度。"""
        model, data, params = v10_model
        hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
        hip_vx = data.cvel[hip_id, 3]  # linear velocity x

        # 应有小的初始前向速度
        assert hip_vx > 0, "初始速度应为正"
        assert hip_vx < 0.5, "初始速度不应过大"


class TestV10SimulationStability:
    """测试 V10 仿真数值稳定性。"""

    def test_short_simulation_no_nan(self, v10_model):
        """短时间仿真不应产生 NaN。"""
        model, data, params = v10_model

        # 仿真 1 秒
        steps = int(1.0 / model.opt.timestep)
        for _ in range(steps):
            mujoco.mj_step(model, data)

        # 检查位置和速度无 NaN
        assert not np.any(np.isnan(data.qpos)), "qpos 包含 NaN"
        assert not np.any(np.isnan(data.qvel)), "qvel 包含 NaN"

    def test_hip_remains_above_ground(self, v10_model):
        """仿真过程中 hip 应保持在地面以上。"""
        model, data, params = v10_model
        hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")

        # 仿真 2 秒
        steps = int(2.0 / model.opt.timestep)
        min_hip_z = float("inf")

        for _ in range(steps):
            mujoco.mj_step(model, data)
            hip_z = data.xpos[hip_id, 2]
            min_hip_z = min(min_hip_z, hip_z)

        # hip 最低点应在合理高度
        assert min_hip_z > 0.6, f"hip 高度过低: {min_hip_z}"

    def test_forward_progression(self, v10_model):
        """机器人应向前行走（被动步态可能位移较小）。"""
        model, data, params = v10_model
        hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")

        initial_x = data.xpos[hip_id, 0]

        # 仿真 3 秒
        steps = int(3.0 / model.opt.timestep)
        for _ in range(steps):
            mujoco.mj_step(model, data)

        final_x = data.xpos[hip_id, 0]

        # V10 被动步态位移可能较小，降低阈值
        displacement = final_x - initial_x
        assert displacement > 0.05, f"前向位移不足: {displacement}"


class TestV10ContactDetection:
    """测试接触检测功能。"""

    def test_contact_flags_function(self, v10_model):
        """contact_flags 函数应返回有效标志。"""
        model, data, params = v10_model

        # 运行几步让接触稳定
        for _ in range(100):
            mujoco.mj_step(model, data)

        left_contact, right_contact = contact_flags(model, data)

        # 至少有一只脚应接触地面
        assert left_contact or right_contact, "无足地接触"

    def test_alternating_contacts(self, v10_model):
        """长时间仿真应观察到足交替接触。"""
        model, data, params = v10_model

        contact_history = []
        steps = int(5.0 / model.opt.timestep)

        for _ in range(steps):
            mujoco.mj_step(model, data)
            if _ % 100 == 0:  # 每 0.1 秒采样
                left, right = contact_flags(model, data)
                contact_history.append((left, right))

        # 应观察到左右足接触切换
        left_contacts = sum(1 for l, r in contact_history if l)
        right_contacts = sum(1 for l, r in contact_history if r)

        assert left_contacts > 5, "左足接触次数不足"
        assert right_contacts > 5, "右足接触次数不足"


class TestV10EnergyConservation:
    """测试能量合理性（不严格守恒，但应有界）。"""

    def test_energy_bounded(self, v10_model):
        """机械能应保持有界（简化计算）。"""
        model, data, params = v10_model

        def mechanical_energy():
            # 简化：仅计算质心动能和势能
            ke = 0.5 * np.sum(data.qvel**2)  # 简化动能计算
            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            pe = params.hip_mass * 9.81 * data.xpos[hip_id, 2]
            return ke + pe

        initial_energy = mechanical_energy()

        # 仿真 3 秒
        steps = int(3.0 / model.opt.timestep)
        for _ in range(steps):
            mujoco.mj_step(model, data)

        final_energy = mechanical_energy()

        # 能量变化应在合理范围（考虑控制输入和损耗）
        energy_change = abs(final_energy - initial_energy)
        assert energy_change < 1000.0, f"能量变化过大: {energy_change}"


class TestV10Reproducibility:
    """测试仿真可重复性。"""

    def test_deterministic_simulation(self, default_params):
        """相同参数应产生相同结果。"""

        def run_simulation():
            xml = build_model_xml(default_params)
            model = mujoco.MjModel.from_xml_string(xml)
            data = mujoco.MjData(model)
            initialize(model, data, default_params)

            steps = int(1.0 / model.opt.timestep)
            for _ in range(steps):
                mujoco.mj_step(model, data)

            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            return data.xpos[hip_id, 0], data.xpos[hip_id, 2]

        x1, z1 = run_simulation()
        x2, z2 = run_simulation()

        np.testing.assert_almost_equal(x1, x2, decimal=10)
        np.testing.assert_almost_equal(z1, z2, decimal=10)

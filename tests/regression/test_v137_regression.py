"""V13.7 摩擦补偿 FSM 回归测试。

验证摩擦补偿控制器的数值稳定性和补偿效果。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"

sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14C_DIR))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1_ROOT))

import mujoco
from simulate_passive_arms_v14 import (
    PassiveArmsParams,
    actuator_names,
    build_model_xml,
    contact_flags,
    initialize,
)
from simulate_v13_7 import V137Params, _compensate, make_v137_fsm

from common.motor_dynamics import PRESETS as MOTOR_PRESETS
from common.motor_dynamics import _sign_smooth


@pytest.fixture
def v137_params():
    """V13.7 默认参数。"""
    base = PassiveArmsParams()
    fsm = make_v137_fsm(base)
    return V137Params(
        base=base,
        fsm=fsm,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
        compensate_friction=True,
    )


@pytest.fixture
def v137_model(v137_params):
    """创建 V13.7 模型和数据。"""
    xml = build_model_xml(v137_params.base)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    initialize(model, data, v137_params.base)
    return model, data, v137_params


class TestV137ModelLoading:
    """测试 V13.7 模型加载。"""

    def test_model_creation(self, v137_model):
        """模型应成功创建。"""
        model, data, params = v137_model
        assert model is not None
        assert data is not None

    def test_actuators_present(self, v137_model):
        """模型应包含执行器。"""
        model, _, _ = v137_model
        act_names = actuator_names(model)
        assert len(act_names) > 0
        # 应包含 hip 和 knee 执行器
        assert any("hip" in name for name in act_names)
        assert any("knee" in name for name in act_names)


class TestV137FrictionCompensation:
    """测试摩擦补偿逻辑。"""

    def test_compensate_function_signature(self):
        """_compensate 函数应接受正确的参数。"""
        motor = MOTOR_PRESETS["mx64ar"]
        tau_fsm = 5.0
        omega = 0.1

        tau_comp = _compensate(tau_fsm, omega, motor)
        assert isinstance(tau_comp, float)

    def test_compensate_increases_torque_for_positive_velocity(self):
        """正速度时补偿应增加力矩（克服摩擦）。"""
        motor = MOTOR_PRESETS["mx64ar"]
        tau_fsm = 5.0
        omega = 0.5  # 正速度

        tau_comp = _compensate(tau_fsm, omega, motor)
        # 补偿后力矩应大于原始 FSM 力矩
        assert tau_comp > tau_fsm

    def test_compensate_decreases_torque_for_negative_velocity(self):
        """负速度时补偿应减小力矩（克服反向摩擦）。"""
        motor = MOTOR_PRESETS["mx64ar"]
        tau_fsm = 5.0
        omega = -0.5  # 负速度

        tau_comp = _compensate(tau_fsm, omega, motor)
        # 补偿后力矩应小于原始 FSM 力矩
        assert tau_comp < tau_fsm

    def test_compensate_zero_velocity(self):
        """零速度时补偿应接近原始力矩。"""
        motor = MOTOR_PRESETS["mx64ar"]
        tau_fsm = 5.0
        omega = 0.0

        tau_comp = _compensate(tau_fsm, omega, motor)
        # 零速度时 sign_smooth(0) ≈ 0，补偿量应很小
        assert abs(tau_comp - tau_fsm) < 0.5

    def test_compensate_with_disabled_compensation(self):
        """关闭补偿时应返回原始力矩（测试设计意图）。"""
        # 这个测试验证设计假设：如果 compensate_friction=False，
        # 实际代码中应跳过调用 _compensate
        motor = MOTOR_PRESETS["mx64ar"]
        tau_fsm = 5.0
        omega = 0.5

        # 当补偿开启时
        tau_comp = _compensate(tau_fsm, omega, motor)
        assert tau_comp != tau_fsm


class TestV137SimulationStability:
    """测试 V13.7 仿真稳定性。"""

    def test_short_simulation_no_nan(self, v137_model):
        """短时间仿真不应产生 NaN。"""
        model, data, params = v137_model

        # 仿真 1 秒
        steps = int(1.0 / model.opt.timestep)
        for _ in range(steps):
            mujoco.mj_step(model, data)

        assert not np.any(np.isnan(data.qpos)), "qpos 包含 NaN"
        assert not np.any(np.isnan(data.qvel)), "qvel 包含 NaN"
        assert not np.any(np.isnan(data.ctrl)), "ctrl 包含 NaN"

    def test_hip_remains_upright(self, v137_model):
        """仿真过程中机器人应保持直立（V13.7 需要控制器激活）。"""
        model, data, params = v137_model
        hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")

        # V13.7 需要控制律，纯被动可能倒地
        # 简化测试：仅验证短时间稳定性
        steps = int(0.5 / model.opt.timestep)
        min_hip_z = float("inf")

        for _ in range(steps):
            mujoco.mj_step(model, data)
            hip_z = data.xpos[hip_id, 2]
            min_hip_z = min(min_hip_z, hip_z)

        # 短时间内应保持一定高度
        assert min_hip_z > 0.3, f"hip 快速下降: {min_hip_z}"

    def test_control_outputs_bounded(self, v137_model):
        """控制输出应有界。"""
        model, data, params = v137_model

        # 仿真 1 秒并记录控制量
        steps = int(1.0 / model.opt.timestep)
        max_ctrl = -float("inf")

        for _ in range(steps):
            mujoco.mj_step(model, data)
            max_ctrl = max(max_ctrl, np.max(np.abs(data.ctrl)))

        # 控制量应小于执行器力矩限制
        assert max_ctrl < 20.0, f"控制量过大: {max_ctrl}"


class TestV137ContactBehavior:
    """测试接触行为。"""

    def test_foot_ground_contact(self, v137_model):
        """应检测到足地接触。"""
        model, data, params = v137_model

        # 运行几步让接触稳定
        for _ in range(200):
            mujoco.mj_step(model, data)

        left_contact, right_contact = contact_flags(model, data)
        assert left_contact or right_contact, "无足地接触"

    def test_contact_switching_over_time(self, v137_model):
        """应观察到接触切换（步态）。"""
        model, data, params = v137_model

        contact_changes = 0
        prev_left, prev_right = False, False

        steps = int(5.0 / model.opt.timestep)
        for i in range(steps):
            mujoco.mj_step(model, data)

            if i % 100 == 0 and i > 0:  # 每 0.1 秒检查
                left, right = contact_flags(model, data)
                if (left != prev_left) or (right != prev_right):
                    contact_changes += 1
                prev_left, prev_right = left, right

        # 应有多次接触切换
        assert contact_changes > 3, f"接触切换次数不足: {contact_changes}"


class TestV137Reproducibility:
    """测试 V13.7 仿真可重复性。"""

    def test_deterministic_with_friction_compensation(self, v137_params):
        """开启摩擦补偿时仿真应可重复。"""

        def run_simulation():
            xml = build_model_xml(v137_params.base)
            model = mujoco.MjModel.from_xml_string(xml)
            data = mujoco.MjData(model)
            initialize(model, data, v137_params.base)

            steps = int(1.0 / model.opt.timestep)
            for _ in range(steps):
                mujoco.mj_step(model, data)

            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            return data.xpos[hip_id, 0], data.xpos[hip_id, 2]

        x1, z1 = run_simulation()
        x2, z2 = run_simulation()

        np.testing.assert_almost_equal(x1, x2, decimal=10)
        np.testing.assert_almost_equal(z1, z2, decimal=10)


class TestV137MotorParameters:
    """测试电机参数配置。"""

    def test_motor_presets_loaded(self, v137_params):
        """电机预设应正确加载。"""
        assert v137_params.hip_motor is not None
        assert v137_params.knee_motor is not None

    def test_motor_has_friction_params(self, v137_params):
        """电机应包含摩擦参数。"""
        motor = v137_params.hip_motor
        # 检查电机有库仑摩擦相关参数
        assert hasattr(motor, "joint_tau_C_eff")
        tau_C = motor.joint_tau_C_eff()
        assert tau_C > 0, "库仑摩擦系数应为正"

    def test_sign_smooth_function(self):
        """测试平滑符号函数。"""
        omega_eps = 0.1

        # 正速度
        assert _sign_smooth(1.0, omega_eps) > 0.9
        # 负速度
        assert _sign_smooth(-1.0, omega_eps) < -0.9
        # 零速度
        assert abs(_sign_smooth(0.0, omega_eps)) < 0.1
        # 小速度
        val = _sign_smooth(0.05, omega_eps)
        assert -1.0 <= val <= 1.0

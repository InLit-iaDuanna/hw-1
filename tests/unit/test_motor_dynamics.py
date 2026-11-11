"""motor_dynamics.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from motor_dynamics import (
    PRESETS,
    L1MotorActuator,
    MotorParams,
    _sign_smooth,
    joint_armature_with_motor,
    joint_damping_with_motor,
)


class TestMotorParams:
    """测试电机参数数据类。"""

    def test_default_creation(self):
        """应能创建默认电机参数。"""
        motor = MotorParams()
        assert motor.name == "MX-64AR"
        assert motor.Kt > 0
        assert motor.N > 0

    def test_custom_parameters(self):
        """应能创建自定义参数。"""
        motor = MotorParams(
            name="Custom",
            Kt=0.02,
            J_rotor=1e-7,
            N=100.0,
            eta=0.8,
            I_max=5.0,
        )
        assert motor.name == "Custom"
        assert motor.Kt == 0.02
        assert motor.N == 100.0

    def test_immutability(self):
        """电机参数应为不可变（frozen=True）。"""
        motor = MotorParams()
        with pytest.raises(AttributeError):
            motor.Kt = 0.05


class TestJointConversions:
    """测试电机参数到关节侧的转换。"""

    def test_joint_J_eff(self):
        """关节侧惯量应为转子惯量乘以减速比平方。"""
        motor = MotorParams(J_rotor=1e-7, N=100.0)
        J_joint = motor.joint_J_eff()
        assert J_joint == pytest.approx(1e-7 * 100.0 * 100.0)

    def test_joint_b_eff(self):
        """关节侧粘滞阻尼应正确折算。"""
        motor = MotorParams(b_visc_motor=1e-6, N=100.0)
        b_joint = motor.joint_b_eff()
        assert b_joint == pytest.approx(1e-6 * 100.0 * 100.0)

    def test_joint_tau_C_eff(self):
        """关节侧库仑摩擦应包含减速比和效率。"""
        motor = MotorParams(tau_C_motor=1e-3, N=200.0, eta=0.67)
        tau_C_joint = motor.joint_tau_C_eff()
        assert tau_C_joint == pytest.approx(1e-3 * 200.0 * 0.67)

    def test_joint_tau_sat_peak(self):
        """峰值饱和扭矩应正确计算。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0)
        tau_sat = motor.joint_tau_sat_peak()
        assert tau_sat == pytest.approx(200.0 * 0.67 * 0.01 * 4.0)

    def test_joint_tau_sat_cont(self):
        """连续额定扭矩应正确计算。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_cont=1.2)
        tau_cont = motor.joint_tau_sat_cont()
        assert tau_cont == pytest.approx(200.0 * 0.67 * 0.01 * 1.2)


class TestMotorPresets:
    """测试预定义电机参数库。"""

    def test_presets_is_dict(self):
        """PRESETS 应为字典。"""
        assert isinstance(PRESETS, dict)

    def test_presets_nonempty(self):
        """应包含预定义电机型号。"""
        assert len(PRESETS) > 0

    def test_mx64ar_exists(self):
        """应包含 MX-64AR 电机。"""
        assert "mx64ar" in PRESETS
        motor = PRESETS["mx64ar"]
        assert isinstance(motor, MotorParams)
        assert "MX-64" in motor.name or "mx64" in motor.name.lower()

    def test_all_presets_valid(self):
        """所有预设应为有效的 MotorParams 实例。"""
        for key, motor in PRESETS.items():
            assert isinstance(motor, MotorParams)
            assert motor.Kt > 0
            assert motor.N > 0
            assert motor.I_max > 0


class TestSignSmooth:
    """测试平滑符号函数。"""

    def test_positive_velocity(self):
        """正速度应返回接近 +1。"""
        result = _sign_smooth(1.0, 0.1)
        assert result > 0.9
        assert result <= 1.0

    def test_negative_velocity(self):
        """负速度应返回接近 -1。"""
        result = _sign_smooth(-1.0, 0.1)
        assert result < -0.9
        assert result >= -1.0

    def test_zero_velocity(self):
        """零速度应返回接近 0。"""
        result = _sign_smooth(0.0, 0.1)
        assert abs(result) < 0.1

    def test_small_velocity(self):
        """小速度应在 [-1, 1] 范围内平滑过渡。"""
        result = _sign_smooth(0.05, 0.1)
        assert -1.0 <= result <= 1.0

    def test_continuity(self):
        """函数应连续（无跳变）。"""
        omega_eps = 0.1
        velocities = [-0.2, -0.1, 0.0, 0.1, 0.2]
        results = [_sign_smooth(v, omega_eps) for v in velocities]

        # 相邻值差异应较小
        for i in range(len(results) - 1):
            diff = abs(results[i + 1] - results[i])
            assert diff < 0.7  # 允许一定变化率


class TestL1MotorActuator:
    """测试 L1 电机执行器类。"""

    def test_actuator_initialization(self):
        """执行器应正确初始化。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0)
        actuator = L1MotorActuator(motor)
        assert actuator.motor == motor
        assert actuator.saturation_count == 0

    def test_within_limit(self):
        """限制范围内的力矩应保持不变（忽略库仑摩擦）。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0, tau_C_motor=0.0)
        actuator = L1MotorActuator(motor)
        tau_desired = 2.0
        tau_out, i_motor = actuator.compute_actual_torque(tau_desired, omega_joint=0.0)
        assert tau_out == pytest.approx(tau_desired, abs=0.01)

    def test_positive_saturation(self):
        """超过峰值的正力矩应饱和。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0, tau_C_motor=0.0)
        actuator = L1MotorActuator(motor)
        tau_sat = motor.joint_tau_sat_peak()
        tau_desired = tau_sat + 5.0
        tau_out, _ = actuator.compute_actual_torque(tau_desired, omega_joint=0.0)
        assert tau_out == pytest.approx(tau_sat, abs=0.01)
        assert actuator.saturation_count > 0

    def test_negative_saturation(self):
        """超过峰值的负力矩应饱和。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0, tau_C_motor=0.0)
        actuator = L1MotorActuator(motor)
        tau_sat = motor.joint_tau_sat_peak()
        tau_desired = -tau_sat - 5.0
        tau_out, _ = actuator.compute_actual_torque(tau_desired, omega_joint=0.0)
        assert tau_out == pytest.approx(-tau_sat, abs=0.01)

    def test_coulomb_friction_positive_velocity(self):
        """正速度时库仑摩擦应减小输出力矩。"""
        motor = MotorParams(tau_C_motor=1e-3, N=200.0, eta=0.67, omega_eps=0.1)
        actuator = L1MotorActuator(motor)
        tau_desired = 5.0
        omega = 0.5

        tau_out, _ = actuator.compute_actual_torque(tau_desired, omega)
        # 输出力矩应小于期望（摩擦消耗）
        assert tau_out < tau_desired

    def test_coulomb_friction_negative_velocity(self):
        """负速度时库仑摩擦方向相反。"""
        motor = MotorParams(tau_C_motor=1e-3, N=200.0, eta=0.67, omega_eps=0.1)
        actuator = L1MotorActuator(motor)
        tau_desired = 5.0
        omega = -0.5

        tau_out, _ = actuator.compute_actual_torque(tau_desired, omega)
        # 负速度时摩擦为正，应增加输出
        assert tau_out > tau_desired

    def test_current_estimation(self):
        """应正确估计电机电流。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0, tau_C_motor=0.0)
        actuator = L1MotorActuator(motor)
        tau_desired = 2.0

        _, i_motor = actuator.compute_actual_torque(tau_desired, omega_joint=0.0)
        # I = tau / (N * eta * Kt)
        expected_current = tau_desired / (200.0 * 0.67 * 0.01)
        assert i_motor == pytest.approx(expected_current)

    def test_electrical_power(self):
        """应计算电功率。"""
        motor = MotorParams(Kt=0.01, N=200.0, eta=0.67, I_max=4.0, R_arm=1.0)
        actuator = L1MotorActuator(motor)
        tau = 2.0
        omega = 1.0

        power = actuator.electrical_power(tau, omega)
        assert power > 0


class TestJointConversionFunctions:
    """测试关节参数转换函数。"""

    def test_joint_armature_with_motor(self):
        """应正确计算关节惯量。"""
        motor = MotorParams(J_rotor=1e-7, N=100.0)
        base = 0.001
        total = joint_armature_with_motor(base, motor)
        expected = base + 1e-7 * 100.0 * 100.0
        assert total == pytest.approx(expected)

    def test_joint_damping_with_motor(self):
        """应正确计算关节阻尼。"""
        motor = MotorParams(b_visc_motor=1e-6, N=100.0)
        base = 0.01
        total = joint_damping_with_motor(base, motor)
        expected = base + 1e-6 * 100.0 * 100.0
        assert total == pytest.approx(expected)


class TestIntegration:
    """集成测试：电机动力学完整流程。"""

    def test_motor_control_pipeline(self):
        """测试完整的电机控制管道：期望力矩 → 实际力矩。"""
        motor = PRESETS["mx64ar"]
        actuator = L1MotorActuator(motor)
        tau_desired = 3.0
        omega = 0.3

        tau_out, i_motor = actuator.compute_actual_torque(tau_desired, omega)

        # 输出应考虑摩擦
        assert tau_out != tau_desired
        # 电流应合理
        assert 0 < i_motor < motor.I_max

    def test_realistic_motor_limits(self):
        """用真实电机参数验证力矩限制。"""
        motor = PRESETS["mx64ar"]

        # MX-64AR 参数：N=200, η=0.67, Kt=0.0109, I_max=4.1
        tau_sat = motor.joint_tau_sat_peak()

        # 峰值扭矩应在合理范围 (5-6 N·m)
        assert 5.0 < tau_sat < 7.0

        # 连续扭矩应显著小于峰值
        tau_cont = motor.joint_tau_sat_cont()
        assert tau_cont < tau_sat * 0.5

    def test_motor_dynamics_deterministic(self):
        """电机动力学计算应确定性。"""
        motor = PRESETS["mx64ar"]
        actuator = L1MotorActuator(motor)
        tau_desired = 4.0
        omega = 0.5

        result1 = actuator.compute_actual_torque(tau_desired, omega)

        # 重新创建执行器
        actuator2 = L1MotorActuator(motor)
        result2 = actuator2.compute_actual_torque(tau_desired, omega)

        assert result1[0] == result2[0]
        assert result1[1] == result2[1]

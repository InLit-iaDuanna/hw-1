"""单元测试：控制器基类与具体实现。

测试 PassiveController 和 PDController 的基本功能。
"""

import pytest

from common.controllers import Controller, PassiveController, PDController


class TestPassiveController:
    """测试 PassiveController 类。"""

    def test_always_returns_zero(self):
        """被动控制器始终返回零力矩。"""
        controller = PassiveController()

        assert controller.compute_torque(0.0, 0.0) == 0.0
        assert controller.compute_torque(0.5, 0.0) == 0.0
        assert controller.compute_torque(0.0, 1.0) == 0.0
        assert controller.compute_torque(1.0, -0.5) == 0.0

    def test_ignores_target(self):
        """被动控制器忽略目标位置。"""
        controller = PassiveController()

        assert controller.compute_torque(0.0, 0.0, target=1.0) == 0.0
        assert controller.compute_torque(0.5, 0.5, target=0.0) == 0.0

    def test_reset_does_nothing(self):
        """被动控制器的 reset 方法不抛出异常。"""
        controller = PassiveController()
        controller.reset()  # 应该不报错


class TestPDController:
    """测试 PDController 类。"""

    def test_proportional_only(self):
        """测试纯比例控制（kd=0）。"""
        controller = PDController(kp=100.0, kd=0.0)

        # 误差为 -0.1，力矩应为 -10.0
        torque = controller.compute_torque(q=0.1, qd=0.0, target=0.0)
        assert abs(torque - (-10.0)) < 1e-6

    def test_derivative_only(self):
        """测试纯微分控制（kp=0）。"""
        controller = PDController(kp=0.0, kd=10.0)

        # 速度为 1.0，力矩应为 -10.0
        torque = controller.compute_torque(q=0.0, qd=1.0, target=0.0)
        assert abs(torque - (-10.0)) < 1e-6

    def test_pd_combined(self):
        """测试 PD 联合控制。"""
        controller = PDController(kp=100.0, kd=10.0)

        # 误差 -0.1，速度 0.5 → 力矩 = 100*(-0.1) - 10*0.5 = -15.0
        torque = controller.compute_torque(q=0.1, qd=0.5, target=0.0)
        assert abs(torque - (-15.0)) < 1e-6

    def test_torque_limit(self):
        """测试力矩限幅。"""
        controller = PDController(kp=100.0, kd=0.0, torque_limit=50.0)

        # 未饱和
        torque1 = controller.compute_torque(q=0.3, qd=0.0, target=0.0)
        assert abs(torque1 - (-30.0)) < 1e-6

        # 饱和到 -50.0
        torque2 = controller.compute_torque(q=1.0, qd=0.0, target=0.0)
        assert abs(torque2 - (-50.0)) < 1e-6

        # 饱和到 +50.0
        torque3 = controller.compute_torque(q=-1.0, qd=0.0, target=0.0)
        assert abs(torque3 - 50.0) < 1e-6

    def test_no_torque_limit(self):
        """测试无限幅控制器。"""
        controller = PDController(kp=100.0, kd=0.0, torque_limit=None)

        # 大误差不应被限制
        torque = controller.compute_torque(q=2.0, qd=0.0, target=0.0)
        assert abs(torque - (-200.0)) < 1e-6

    def test_requires_target(self):
        """PD 控制器必须提供目标位置。"""
        controller = PDController(kp=100.0, kd=10.0)

        with pytest.raises(ValueError, match="requires a target"):
            controller.compute_torque(q=0.1, qd=0.0)

    def test_kwargs_override(self):
        """测试临时参数覆盖。"""
        controller = PDController(kp=100.0, kd=10.0, torque_limit=50.0)

        # 临时使用不同的增益
        torque = controller.compute_torque(
            q=0.1, qd=0.0, target=0.0, kp=200.0, kd=20.0
        )
        assert abs(torque - (-20.0)) < 1e-6

        # 原始增益不变
        torque_orig = controller.compute_torque(q=0.1, qd=0.0, target=0.0)
        assert abs(torque_orig - (-10.0)) < 1e-6

    def test_set_gains(self):
        """测试增益更新方法。"""
        controller = PDController(kp=100.0, kd=10.0)

        # 更新 kp
        controller.set_gains(kp=200.0)
        assert controller.kp == 200.0
        assert controller.kd == 10.0

        # 更新 kd
        controller.set_gains(kd=20.0)
        assert controller.kp == 200.0
        assert controller.kd == 20.0

        # 同时更新
        controller.set_gains(kp=50.0, kd=5.0)
        assert controller.kp == 50.0
        assert controller.kd == 5.0

    def test_repr(self):
        """测试字符串表示。"""
        controller1 = PDController(kp=100.0, kd=10.0)
        repr1 = repr(controller1)
        assert "100.0" in repr1
        assert "10.0" in repr1
        assert "None" in repr1

        controller2 = PDController(kp=100.0, kd=10.0, torque_limit=50.0)
        repr2 = repr(controller2)
        assert "50.0" in repr2


class TestControllerInterface:
    """测试控制器抽象基类接口。"""

    def test_is_abstract(self):
        """Controller 是抽象类，不能直接实例化。"""
        with pytest.raises(TypeError):
            Controller()  # type: ignore

    def test_passive_is_controller(self):
        """PassiveController 是 Controller 的子类。"""
        controller = PassiveController()
        assert isinstance(controller, Controller)

    def test_pd_is_controller(self):
        """PDController 是 Controller 的子类。"""
        controller = PDController()
        assert isinstance(controller, Controller)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

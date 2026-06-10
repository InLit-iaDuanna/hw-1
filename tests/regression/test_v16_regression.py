"""V16 电机动力学回归测试。

验证 V16 电机动力学模型的数值稳定性和力矩限制。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
V16_DIR = HW1_ROOT / "v16_motor_dynamics"
V14_DIR = HW1_ROOT / "v14_passive_arms"

# 尝试加载 V16 或 V16_refactored
try:
    sys.path.insert(0, str(V14_DIR))
    sys.path.insert(0, str(V16_DIR))
    from simulate_passive_arms_v14 import PassiveArmsParams
    from simulate_v16 import V16Params, build_model_xml_v16, initialize, make_v16_fsm

    V16_AVAILABLE = True
except ImportError:
    V16_AVAILABLE = False


@pytest.fixture
def v16_params():
    """V16 默认参数。"""
    if not V16_AVAILABLE:
        pytest.skip("V16 模块不可用")
    base = PassiveArmsParams(duration=1.0)
    return V16Params(base=base, fsm=make_v16_fsm(base))


@pytest.fixture
def v16_model(v16_params):
    """创建 V16 模型和数据。"""
    if not V16_AVAILABLE:
        pytest.skip("V16 模块不可用")

    import mujoco

    xml = build_model_xml_v16(v16_params)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    initialize(model, data, v16_params.base)
    return model, data, v16_params


@pytest.mark.skipif(not V16_AVAILABLE, reason="V16 not available")
class TestV16ModelLoading:
    """测试 V16 模型加载。"""

    def test_model_creation(self, v16_model):
        """模型应成功创建。"""
        model, data, params = v16_model
        assert model is not None
        assert data is not None

    def test_motor_parameters_configured(self, v16_params):
        """电机参数应正确配置。"""
        assert v16_params.hip_motor is not None
        assert v16_params.knee_motor is not None
        assert v16_params.hip_motor.name != ""


@pytest.mark.skipif(not V16_AVAILABLE, reason="V16 not available")
class TestV16SimulationStability:
    """测试 V16 仿真稳定性。"""

    def test_short_simulation_no_nan(self, v16_model):
        """短时间仿真不应产生 NaN。"""
        import mujoco

        model, data, params = v16_model

        steps = int(1.0 / model.opt.timestep)
        for _ in range(steps):
            mujoco.mj_step(model, data)

        assert not np.any(np.isnan(data.qpos)), "qpos 包含 NaN"
        assert not np.any(np.isnan(data.qvel)), "qvel 包含 NaN"
        assert not np.any(np.isnan(data.ctrl)), "ctrl 包含 NaN"

    def test_control_outputs_bounded(self, v16_model):
        """控制输出应受电机力矩限制约束。"""
        import mujoco

        model, data, params = v16_model

        steps = int(1.0 / model.opt.timestep)
        max_ctrl = -float("inf")

        for _ in range(steps):
            mujoco.mj_step(model, data)
            max_ctrl = max(max_ctrl, np.max(np.abs(data.ctrl)))

        # 控制量应小于电机峰值扭矩
        tau_sat = params.hip_motor.joint_tau_sat_peak()
        assert max_ctrl < tau_sat * 1.1, f"控制量超限: {max_ctrl} > {tau_sat}"


@pytest.mark.skipif(not V16_AVAILABLE, reason="V16 not available")
class TestV16Reproducibility:
    """测试 V16 仿真可重复性。"""

    def test_deterministic_simulation(self, v16_params):
        """相同参数应产生相同结果。"""
        import mujoco

        def run_simulation():
            xml = build_model_xml_v16(v16_params)
            model = mujoco.MjModel.from_xml_string(xml)
            data = mujoco.MjData(model)
            initialize(model, data, v16_params.base)

            steps = int(1.0 / model.opt.timestep)
            for _ in range(steps):
                mujoco.mj_step(model, data)

            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            return data.xpos[hip_id, 0], data.xpos[hip_id, 2]

        x1, z1 = run_simulation()
        x2, z2 = run_simulation()

        np.testing.assert_almost_equal(x1, x2, decimal=10)
        np.testing.assert_almost_equal(z1, z2, decimal=10)

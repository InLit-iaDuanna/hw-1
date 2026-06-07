"""disturbance.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from disturbance import ContactPhaseNoise, ImpulseSpec, apply_impulse


class TestImpulseSpec:
    """测试脉冲规范数据类。"""

    def test_impulse_spec_creation(self):
        """测试基本创建。"""
        spec = ImpulseSpec(
            body_name="hip",
            force_xyz=(10.0, 0.0, 0.0),
            t_start_s=2.0,
            duration_s=0.1,
        )
        assert spec.body_name == "hip"
        assert spec.force_xyz == (10.0, 0.0, 0.0)
        assert spec.t_start_s == 2.0
        assert spec.duration_s == 0.1

    def test_t_end_property(self):
        """测试 t_end 计算属性。"""
        spec = ImpulseSpec("hip", (10.0, 0.0, 0.0), 2.0, 0.1)
        assert spec.t_end_s == 2.1

    def test_zero_duration(self):
        """零持续时长脉冲（边界情况）。"""
        spec = ImpulseSpec("hip", (5.0, 0.0, 0.0), 1.0, 0.0)
        assert spec.t_end_s == 1.0


class TestApplyImpulse:
    """测试脉冲施力函数。"""

    @pytest.fixture
    def simple_model(self):
        """创建包含 hip body 的最小测试模型。"""
        import mujoco

        xml = """
        <mujoco>
          <worldbody>
            <body name="hip" pos="0 0 1">
              <geom type="sphere" size="0.1"/>
              <freejoint/>
            </body>
          </worldbody>
        </mujoco>
        """
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        return model, data

    def test_force_applied_in_window(self, simple_model):
        """时间窗口内应施加外力。"""
        model, data = simple_model
        spec = ImpulseSpec("hip", (10.0, 5.0, -3.0), 1.0, 0.5)

        # 时间在窗口内
        active = apply_impulse(model, data, spec, t=1.2)
        assert active is True
        assert data.xfrc_applied[1, 0] == 10.0
        assert data.xfrc_applied[1, 1] == 5.0
        assert data.xfrc_applied[1, 2] == -3.0

    def test_force_not_applied_before_window(self, simple_model):
        """时间窗口前不应施力。"""
        model, data = simple_model
        spec = ImpulseSpec("hip", (10.0, 0.0, 0.0), 2.0, 0.1)

        active = apply_impulse(model, data, spec, t=1.5)
        assert active is False
        assert data.xfrc_applied[1, 0] == 0.0

    def test_force_not_applied_after_window(self, simple_model):
        """时间窗口后应清零。"""
        model, data = simple_model
        spec = ImpulseSpec("hip", (10.0, 0.0, 0.0), 2.0, 0.1)

        # 先在窗口内施力
        apply_impulse(model, data, spec, t=2.05)
        assert data.xfrc_applied[1, 0] == 10.0

        # 窗口外应清零
        active = apply_impulse(model, data, spec, t=2.5)
        assert active is False
        assert data.xfrc_applied[1, 0] == 0.0

    def test_invalid_body_name(self, simple_model):
        """不存在的 body 应返回 False 且不报错。"""
        model, data = simple_model
        spec = ImpulseSpec("nonexistent_body", (10.0, 0.0, 0.0), 1.0, 0.1)

        active = apply_impulse(model, data, spec, t=1.05)
        assert active is False

    def test_window_boundary_start(self, simple_model):
        """窗口起点（包含）应施力。"""
        model, data = simple_model
        spec = ImpulseSpec("hip", (8.0, 0.0, 0.0), 3.0, 0.2)

        active = apply_impulse(model, data, spec, t=3.0)
        assert active is True
        assert data.xfrc_applied[1, 0] == 8.0

    def test_window_boundary_end(self, simple_model):
        """窗口终点（不包含）不应施力。"""
        model, data = simple_model
        spec = ImpulseSpec("hip", (8.0, 0.0, 0.0), 3.0, 0.2)

        active = apply_impulse(model, data, spec, t=3.2)
        assert active is False
        assert data.xfrc_applied[1, 0] == 0.0


class TestContactPhaseNoise:
    """测试接触相位噪声。"""

    def test_zero_noise(self):
        """sigma=0 时应返回原始阈值。"""
        noise = ContactPhaseNoise(sigma_s=0.0, seed=42)
        base = 0.035
        perturbed = noise.perturbed_threshold(base)
        assert perturbed == base

    def test_positive_noise_variability(self):
        """sigma>0 时应产生随机扰动。"""
        noise = ContactPhaseNoise(sigma_s=0.01, seed=42)
        base = 0.035
        results = [noise.perturbed_threshold(base) for _ in range(100)]

        # 应有变化
        assert len(set(results)) > 10
        # 均值应接近 base
        assert abs(np.mean(results) - base) < 0.005

    def test_minimum_threshold(self):
        """扰动后阈值不应小于 1 ms。"""
        noise = ContactPhaseNoise(sigma_s=1.0, seed=42)  # 大噪声
        base = 0.005
        results = [noise.perturbed_threshold(base) for _ in range(100)]
        assert all(r >= 0.001 for r in results)

    def test_reproducibility_with_seed(self):
        """相同 seed 应产生相同序列。"""
        noise1 = ContactPhaseNoise(sigma_s=0.01, seed=123)
        noise2 = ContactPhaseNoise(sigma_s=0.01, seed=123)
        base = 0.035

        seq1 = [noise1.perturbed_threshold(base) for _ in range(10)]
        seq2 = [noise2.perturbed_threshold(base) for _ in range(10)]

        np.testing.assert_array_almost_equal(seq1, seq2)

    def test_different_seeds_different_sequences(self):
        """不同 seed 应产生不同序列。"""
        noise1 = ContactPhaseNoise(sigma_s=0.01, seed=1)
        noise2 = ContactPhaseNoise(sigma_s=0.01, seed=2)
        base = 0.035

        seq1 = [noise1.perturbed_threshold(base) for _ in range(10)]
        seq2 = [noise2.perturbed_threshold(base) for _ in range(10)]

        assert not np.allclose(seq1, seq2)

    def test_large_base_threshold(self):
        """大基准阈值应正常扰动。"""
        noise = ContactPhaseNoise(sigma_s=0.05, seed=42)
        base = 1.0
        results = [noise.perturbed_threshold(base) for _ in range(50)]

        # 均值应接近 base
        assert abs(np.mean(results) - base) < 0.02
        # 应有显著分布
        assert np.std(results) > 0.02

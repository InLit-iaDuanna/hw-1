"""control_utils.py 单元测试。"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from control_utils import limited_pd, ramp_height, smoothstep


class TestSmoothstep:
    """测试 Smoothstep 插值函数。"""

    def test_boundary_zero(self):
        """输入 0 应返回 0。"""
        assert smoothstep(0.0) == 0.0

    def test_boundary_one(self):
        """输入 1 应返回 1。"""
        assert smoothstep(1.0) == 1.0

    def test_midpoint(self):
        """输入 0.5 应返回 0.5。"""
        assert smoothstep(0.5) == pytest.approx(0.5)

    def test_clipping_negative(self):
        """负值应裁剪到 0。"""
        assert smoothstep(-0.5) == 0.0

    def test_clipping_above_one(self):
        """超过 1 的值应裁剪到 1。"""
        assert smoothstep(1.5) == 1.0

    def test_monotonic_increasing(self):
        """函数应单调递增。"""
        values = [smoothstep(x) for x in [0.0, 0.25, 0.5, 0.75, 1.0]]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]

    def test_smooth_at_boundaries(self):
        """边界处应平滑（导数为 0）。"""
        # 数值验证：边界附近变化率应较小
        delta = 0.01
        slope_at_zero = (smoothstep(delta) - smoothstep(0.0)) / delta
        slope_at_one = (smoothstep(1.0) - smoothstep(1.0 - delta)) / delta

        # 边界处斜率应接近 0（smoothstep 性质）
        assert abs(slope_at_zero) < 0.2
        assert abs(slope_at_one) < 0.2


class TestLimitedPD:
    """测试有限幅 PD 控制器。"""

    def test_basic_proportional_control(self):
        """比例控制应产生正确的力矩。"""
        q = 0.1
        qd = 0.0
        target = 0.0
        kp = 100.0
        kd = 10.0
        limit = 50.0

        tau = limited_pd(q, qd, target, kp, kd, limit)
        expected = kp * (target - q)  # -10.0
        assert tau == pytest.approx(expected)

    def test_derivative_control(self):
        """微分控制应抑制速度。"""
        q = 0.0
        qd = 1.0
        target = 0.0
        kp = 100.0
        kd = 10.0
        limit = 50.0

        tau = limited_pd(q, qd, target, kp, kd, limit)
        expected = -kd * qd  # -10.0
        assert tau == pytest.approx(expected)

    def test_positive_saturation(self):
        """正向力矩应饱和到限制值。"""
        q = -1.0
        qd = 0.0
        target = 0.0
        kp = 100.0
        kd = 10.0
        limit = 50.0

        tau = limited_pd(q, qd, target, kp, kd, limit)
        # kp * (0 - (-1)) = 100，应饱和到 50
        assert tau == pytest.approx(limit)

    def test_negative_saturation(self):
        """负向力矩应饱和到负限制值。"""
        q = 1.0
        qd = 0.0
        target = 0.0
        kp = 100.0
        kd = 10.0
        limit = 50.0

        tau = limited_pd(q, qd, target, kp, kd, limit)
        # kp * (0 - 1) = -100，应饱和到 -50
        assert tau == pytest.approx(-limit)

    def test_zero_gains(self):
        """零增益应产生零力矩。"""
        tau = limited_pd(0.5, 0.5, 0.0, kp=0.0, kd=0.0, limit=50.0)
        assert tau == 0.0

    def test_zero_error(self):
        """零误差和零速度应产生零力矩。"""
        tau = limited_pd(0.5, 0.0, 0.5, kp=100.0, kd=10.0, limit=50.0)
        assert tau == 0.0

    def test_combined_control(self):
        """比例和微分项应正确组合。"""
        q = 0.1
        qd = 0.2
        target = 0.0
        kp = 100.0
        kd = 10.0
        limit = 50.0

        tau = limited_pd(q, qd, target, kp, kd, limit)
        expected = kp * (target - q) - kd * qd
        # 100 * (-0.1) - 10 * 0.2 = -10 - 2 = -12
        assert tau == pytest.approx(expected)


class TestRampHeight:
    """测试斜坡高度计算。"""

    def test_zero_x_zero_height(self):
        """原点处高度应为 0。"""
        h = ramp_height(0.0, gamma=0.05)
        assert h == 0.0

    def test_positive_x_downhill(self):
        """正坡度（下坡）正 x 应产生负高度。"""
        h = ramp_height(1.0, gamma=0.05)
        expected = -math.tan(0.05) * 1.0
        assert h == pytest.approx(expected)
        assert h < 0

    def test_negative_x_downhill(self):
        """正坡度负 x 应产生正高度。"""
        h = ramp_height(-1.0, gamma=0.05)
        expected = -math.tan(0.05) * (-1.0)
        assert h == pytest.approx(expected)
        assert h > 0

    def test_negative_gamma_uphill(self):
        """负坡度（上坡）正 x 应产生正高度。"""
        h = ramp_height(1.0, gamma=-0.05)
        expected = -math.tan(-0.05) * 1.0
        assert h == pytest.approx(expected)
        assert h > 0

    def test_zero_gamma_flat(self):
        """零坡度应产生零高度（平地）。"""
        h = ramp_height(10.0, gamma=0.0)
        assert h == pytest.approx(0.0)

    def test_linearity(self):
        """高度应与 x 线性相关。"""
        gamma = 0.1
        h1 = ramp_height(1.0, gamma)
        h2 = ramp_height(2.0, gamma)

        # h2 应约为 h1 的两倍
        assert h2 == pytest.approx(2.0 * h1)

    def test_steep_slope(self):
        """大坡度应产生大高度变化。"""
        gamma_small = 0.01
        gamma_large = 0.2
        x = 1.0

        h_small = abs(ramp_height(x, gamma_small))
        h_large = abs(ramp_height(x, gamma_large))

        assert h_large > h_small


class TestIntegration:
    """集成测试：控制工具组合使用。"""

    def test_smoothstep_in_pd_gain_scheduling(self):
        """Smoothstep 可用于 PD 增益调度。"""
        # 模拟相位插值：0 → 1 过程中增益从低到高
        phase = 0.3
        alpha = smoothstep(phase)

        kp_low = 50.0
        kp_high = 150.0
        kp = kp_low + alpha * (kp_high - kp_low)

        tau = limited_pd(0.1, 0.0, 0.0, kp, 10.0, 50.0)
        assert tau != 0.0

    def test_ramp_height_with_pd_tracking(self):
        """斜坡高度可用于 PD 控制器跟踪目标。"""
        x_robot = 1.0
        gamma = 0.05
        target_height = ramp_height(x_robot, gamma)

        current_height = 0.9
        height_error = target_height - current_height

        # 用 PD 控制器跟踪斜坡高度
        tau = limited_pd(current_height, 0.0, target_height, 100.0, 10.0, 50.0)
        assert tau != 0.0  # 应产生控制力矩

    def test_control_pipeline_deterministic(self):
        """控制管道应确定性。"""
        q, qd, target = 0.1, 0.2, 0.0
        kp, kd, limit = 100.0, 10.0, 50.0

        result1 = limited_pd(q, qd, target, kp, kd, limit)
        result2 = limited_pd(q, qd, target, kp, kd, limit)

        assert result1 == result2

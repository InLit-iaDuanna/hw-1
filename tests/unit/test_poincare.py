"""poincare.py 单元测试。

测试 Poincaré 截面采集和 Floquet 乘子估计。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from poincare import collect_section, floquet_multipliers, plot_section


class TestCollectSection:
    """测试 Poincaré 截面采集。"""

    def test_empty_input(self):
        """空输入应返回空数组。"""
        result = collect_section([], state_keys=("q1", "q2"))
        assert result.shape == (0, 2)

    def test_single_row_no_switching(self):
        """单行数据无法检测切换。"""
        rows = [{"support_foot": "left", "q1": 0.1, "q2": 0.2}]
        result = collect_section(rows, state_keys=("q1", "q2"))
        assert result.shape == (0, 2)

    def test_no_support_switching(self):
        """无支撑足切换应返回空数组。"""
        rows = [
            {"support_foot": "left", "q1": 0.1, "q2": 0.2},
            {"support_foot": "left", "q1": 0.15, "q2": 0.25},
            {"support_foot": "left", "q1": 0.2, "q2": 0.3},
        ]
        result = collect_section(rows, state_keys=("q1", "q2"))
        assert result.shape == (0, 2)

    def test_single_support_switch(self):
        """单次支撑足切换应捕获一个截面点。"""
        rows = [
            {"support_foot": "left", "q1": 0.1, "q2": 0.2},
            {"support_foot": "left", "q1": 0.15, "q2": 0.25},
            {"support_foot": "right", "q1": 0.2, "q2": 0.3},
            {"support_foot": "right", "q1": 0.25, "q2": 0.35},
        ]
        result = collect_section(rows, state_keys=("q1", "q2"))
        assert result.shape == (1, 2)
        np.testing.assert_array_almost_equal(result[0], [0.2, 0.3])

    def test_multiple_support_switches(self):
        """多次切换应捕获多个截面点。"""
        rows = [
            {"support_foot": "left", "q1": 0.1, "q2": 0.2},
            {"support_foot": "right", "q1": 0.2, "q2": 0.3},
            {"support_foot": "left", "q1": 0.3, "q2": 0.4},
            {"support_foot": "right", "q1": 0.4, "q2": 0.5},
        ]
        result = collect_section(rows, state_keys=("q1", "q2"))
        assert result.shape == (3, 2)
        np.testing.assert_array_almost_equal(result[0], [0.2, 0.3])
        np.testing.assert_array_almost_equal(result[1], [0.3, 0.4])
        np.testing.assert_array_almost_equal(result[2], [0.4, 0.5])

    def test_invalid_support_values_ignored(self):
        """无效的支撑足值应被忽略。"""
        rows = [
            {"support_foot": "left", "q1": 0.1, "q2": 0.2},
            {"support_foot": "both", "q1": 0.15, "q2": 0.25},
            {"support_foot": "right", "q1": 0.2, "q2": 0.3},
        ]
        result = collect_section(rows, state_keys=("q1", "q2"))
        # "both" 不是有效值，不应触发切换
        assert result.shape == (1, 2)

    def test_missing_support_foot_key(self):
        """缺少 support_foot 键应安全处理。"""
        rows = [
            {"q1": 0.1, "q2": 0.2},
            {"q1": 0.15, "q2": 0.25},
        ]
        result = collect_section(rows, state_keys=("q1", "q2"))
        # 默认为空字符串，无有效切换
        assert result.shape == (0, 2)

    def test_state_keys_extraction(self):
        """应正确提取指定的状态键。"""
        rows = [
            {"support_foot": "left", "q1": 0.1, "q2": 0.2, "q3": 0.3},
            {"support_foot": "right", "q1": 0.4, "q2": 0.5, "q3": 0.6},
        ]
        result = collect_section(rows, state_keys=("q1", "q3"))
        assert result.shape == (1, 2)
        np.testing.assert_array_almost_equal(result[0], [0.4, 0.6])

    def test_single_state_key(self):
        """应支持单个状态键。"""
        rows = [
            {"support_foot": "left", "theta": 0.1},
            {"support_foot": "right", "theta": 0.2},
        ]
        result = collect_section(rows, state_keys=("theta",))
        assert result.shape == (1, 1)
        assert result[0, 0] == pytest.approx(0.2)


class TestFloquetMultipliers:
    """测试 Floquet 乘子估计。"""

    def test_empty_input(self):
        """空输入应返回带 NaN 的结果。"""
        result = floquet_multipliers(np.empty((0, 2)))
        assert result["n_pairs"] == 0
        assert np.all(np.isnan(result["jacobian"]))
        assert np.all(np.isnan(result["eigvals"]))
        assert np.all(np.isnan(result["fixed_point"]))

    def test_single_point(self):
        """单点无法估计 Jacobian。"""
        pts = np.array([[0.1, 0.2]])
        result = floquet_multipliers(pts)
        assert result["n_pairs"] == 0
        assert np.all(np.isnan(result["jacobian"]))

    def test_two_points_are_underdetermined_in_two_dimensions(self):
        """二维系统的一对样本不足以估计 Jacobian，必须返回 NaN。"""
        pts = np.array([[0.1, 0.2], [0.15, 0.25]])
        result = floquet_multipliers(pts)
        assert result["n_pairs"] == 1
        assert result["jacobian"].shape == (2, 2)
        assert np.all(np.isnan(result["jacobian"]))
        assert np.all(np.isnan(result["eigvals"]))
        np.testing.assert_allclose(result["fixed_point"], pts.mean(axis=0))

    def test_stable_fixed_point(self):
        """稳定不动点：所有特征值模小于 1。"""
        # 构造收敛序列：x_{k+1} = 0.8 * x_k
        x0 = np.array([1.0, 0.5])
        pts = np.array([0.8**i * x0 for i in range(20)])

        result = floquet_multipliers(pts, skip_head=5)
        eigvals = result["eigvals"]

        # 特征值模应接近 0.8
        max_magnitude = np.max(np.abs(eigvals))
        assert max_magnitude < 1.0

    def test_unstable_fixed_point(self):
        """不稳定不动点：至少一个特征值模大于 1。"""
        # 构造发散序列：x_{k+1} = 1.2 * x_k
        x0 = np.array([0.1, 0.05])
        pts = np.array([1.2**i * x0 for i in range(15)])

        result = floquet_multipliers(pts, skip_head=3, fixed_point=np.array([0.0, 0.0]))
        eigvals = result["eigvals"]

        # 特征值模应大于 1
        max_magnitude = np.max(np.abs(eigvals))
        assert max_magnitude > 1.0

    def test_limit_cycle(self):
        """极限环：特征值模接近 1。"""
        # 构造周期序列（近似极限环）
        theta = np.linspace(0, 8 * np.pi, 40)
        radius = 1.0 + 0.01 * np.sin(theta)  # 小扰动
        pts = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])

        result = floquet_multipliers(pts, skip_head=10, tail_frac=0.5)
        eigvals = result["eigvals"]

        # 至少一个特征值模接近 1
        magnitudes = np.abs(eigvals)
        assert np.any(magnitudes > 0.8)

    def test_fixed_point_auto_estimation(self):
        """不动点应自动从尾部平均估计。"""
        # 收敛到 (1.0, 2.0)
        target = np.array([1.0, 2.0])
        pts = np.array([target + 0.5**i * np.array([0.5, -0.3]) for i in range(20)])

        result = floquet_multipliers(pts, tail_frac=0.3)
        fp = result["fixed_point"]

        # 不动点应接近目标
        np.testing.assert_array_almost_equal(fp, target, decimal=1)

    def test_custom_fixed_point(self):
        """应支持自定义不动点。"""
        pts = np.array([[0.1, 0.2], [0.15, 0.25], [0.2, 0.3]])
        custom_fp = np.array([0.5, 0.5])

        result = floquet_multipliers(pts, fixed_point=custom_fp)

        np.testing.assert_array_equal(result["fixed_point"], custom_fp)

    def test_skip_head_transient(self):
        """skip_head 应跳过暂态点。"""
        # 前几个点有大扰动
        pts = np.array(
            [
                [10.0, 5.0],  # 暂态
                [8.0, 4.0],  # 暂态
                [1.1, 0.5],
                [1.0, 0.5],
                [0.9, 0.5],
            ]
        )

        result_full = floquet_multipliers(pts, skip_head=0)
        result_skip = floquet_multipliers(pts, skip_head=2)

        # 跳过暂态后结果应不同
        assert result_full["n_pairs"] == 4
        assert result_skip["n_pairs"] == 2

    def test_tail_frac_parameter(self):
        """tail_frac 应控制不动点估计的样本数。"""
        pts = np.array([[i * 0.1, i * 0.05] for i in range(20)])

        result_small = floquet_multipliers(pts, tail_frac=0.2)
        result_large = floquet_multipliers(pts, tail_frac=0.8)

        # 不同尾部比例应产生不同的不动点估计
        assert not np.allclose(result_small["fixed_point"], result_large["fixed_point"])

    def test_jacobian_shape(self):
        """Jacobian 形状应与状态维度一致。"""
        # 2D 状态
        pts_2d = np.array([[0.1, 0.2], [0.15, 0.25], [0.2, 0.3]])
        result_2d = floquet_multipliers(pts_2d)
        assert result_2d["jacobian"].shape == (2, 2)
        assert result_2d["eigvals"].shape == (2,)

        # 3D 状态
        pts_3d = np.array([[0.1, 0.2, 0.3], [0.15, 0.25, 0.35], [0.2, 0.3, 0.4]])
        result_3d = floquet_multipliers(pts_3d)
        assert result_3d["jacobian"].shape == (3, 3)
        assert result_3d["eigvals"].shape == (3,)


class TestPlotSection:
    """测试 Poincaré 截面绘图函数。"""

    def test_plot_with_empty_data(self):
        """空数据应显示提示信息。"""
        import matplotlib

        matplotlib.use("Agg")  # 使用非交互式后端
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        pts = np.empty((0, 2))

        # 应不抛出异常
        plot_section(ax, pts, "x", "y", "Test")

        plt.close(fig)

    def test_plot_with_data(self):
        """有数据时应正常绘图。"""
        import matplotlib

        matplotlib.use("Agg")  # 使用非交互式后端
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        pts = np.array([[0.1, 0.2], [0.15, 0.25], [0.2, 0.3]])

        plot_section(ax, pts, "q1", "q2", "Phase Portrait")

        # 检查是否设置了标签和网格
        assert ax.get_xlabel() == "q1"
        assert ax.get_ylabel() == "q2"
        assert ax.get_title() == "Phase Portrait"

        plt.close(fig)

    def test_plot_without_title(self):
        """无标题时应正常绘图。"""
        import matplotlib

        matplotlib.use("Agg")  # 使用非交互式后端
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        pts = np.array([[0.1, 0.2], [0.15, 0.25]])

        plot_section(ax, pts, "x", "y")

        assert ax.get_xlabel() == "x"
        assert ax.get_ylabel() == "y"

        plt.close(fig)


class TestIntegration:
    """集成测试：完整 Poincaré 分析流程。"""

    def test_complete_analysis_pipeline(self):
        """测试从数据采集到 Floquet 分析的完整流程。"""
        # 模拟步态数据：周期性步行
        rows = []
        t = 0.0
        dt = 0.001

        for i in range(3000):
            support = "left" if (i // 500) % 2 == 0 else "right"
            theta1 = 0.3 * np.sin(2 * np.pi * t / 0.5)
            theta2 = 0.2 * np.cos(2 * np.pi * t / 0.5)

            rows.append(
                {
                    "time": t,
                    "support_foot": support,
                    "hip_angle": theta1,
                    "knee_angle": theta2,
                }
            )
            t += dt

        # 采集截面
        pts = collect_section(rows, state_keys=("hip_angle", "knee_angle"))

        # 应捕获多个步态周期
        assert pts.shape[0] > 2

        # 估计 Floquet 乘子
        result = floquet_multipliers(pts, skip_head=1)

        assert result["n_pairs"] >= pts.shape[1]
        assert result["jacobian"].shape == (2, 2)
        assert not np.any(np.isnan(result["eigvals"]))

    def test_deterministic_floquet_estimation(self):
        """Floquet 估计应确定性。"""
        pts = np.array([[0.1, 0.2], [0.15, 0.25], [0.2, 0.3], [0.25, 0.35]])

        result1 = floquet_multipliers(pts)
        result2 = floquet_multipliers(pts)

        np.testing.assert_array_almost_equal(result1["jacobian"], result2["jacobian"])
        np.testing.assert_array_almost_equal(result1["eigvals"], result2["eigvals"])
        np.testing.assert_array_almost_equal(
            result1["fixed_point"], result2["fixed_point"]
        )

    def test_goswami_method_consistency(self):
        """验证 Goswami 方法的一致性（线性系统）。"""
        # 线性系统 x_{k+1} = A @ x_k，A 的特征值应与估计的 Floquet 乘子一致
        A = np.array([[0.9, 0.1], [-0.1, 0.85]])

        x0 = np.array([1.0, 0.5])
        pts = [x0]
        for _ in range(15):
            pts.append(A @ pts[-1])
        pts = np.array(pts)

        result = floquet_multipliers(pts, fixed_point=np.array([0.0, 0.0]), skip_head=5)

        # 估计的 Jacobian 应接近 A
        np.testing.assert_array_almost_equal(result["jacobian"], A, decimal=2)

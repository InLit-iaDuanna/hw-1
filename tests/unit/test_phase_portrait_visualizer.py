"""单元测试：PhasePortraitVisualizer。

测试相空间可视化器的核心功能。
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for testing
import matplotlib.pyplot as plt

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.phase_portrait_visualizer import (
    PhasePortraitVisualizer,
    StateVariable,
    TrajectoryAnnotation,
    quick_phase_portrait,
)


class TestPhasePortraitVisualizer:
    """测试 PhasePortraitVisualizer 类。"""

    def test_initialization(self):
        """测试初始化。"""
        vis = PhasePortraitVisualizer()
        assert len(vis.trajectories) == 0
        assert len(vis.annotations) == 0
        assert vis.vector_field is None
        assert len(vis.nullclines) == 0

    def test_add_trajectory_2d(self):
        """测试添加 2D 轨迹。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        vis.add_trajectory(x, y, label="Test trajectory")

        assert len(vis.trajectories) == 1
        assert vis.trajectories[0]["label"] == "Test trajectory"
        assert np.allclose(vis.trajectories[0]["x"], x)
        assert np.allclose(vis.trajectories[0]["y"], y)
        assert vis.trajectories[0]["z"] is None

    def test_add_trajectory_3d(self):
        """测试添加 3D 轨迹。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        z = np.cos(x)

        vis.add_trajectory(x, y, z, label="3D trajectory")

        assert len(vis.trajectories) == 1
        assert vis.trajectories[0]["z"] is not None
        assert np.allclose(vis.trajectories[0]["z"], z)

    def test_add_trajectory_with_time(self):
        """测试添加带时间编码的轨迹。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        t = np.linspace(0, 1, 100)

        vis.add_trajectory(x, y, time=t, colormap="viridis")

        assert vis.trajectories[0]["time"] is not None
        assert np.allclose(vis.trajectories[0]["time"], t)
        assert vis.trajectories[0]["colormap"] == "viridis"

    def test_add_multiple_trajectories(self):
        """测试添加多条轨迹。"""
        vis = PhasePortraitVisualizer()

        for i in range(3):
            x = np.linspace(0, 10, 100) + i
            y = np.sin(x)
            vis.add_trajectory(x, y, label=f"Traj {i}")

        assert len(vis.trajectories) == 3

    def test_add_annotation(self):
        """测试添加标注。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        vis.add_trajectory(x, y)

        vis.add_annotation(0, "Start", color="green", marker="*")
        vis.add_annotation(-1, "End", color="red", marker="s")

        assert len(vis.annotations) == 2
        assert vis.annotations[0].label == "Start"
        assert vis.annotations[0].index == 0
        assert vis.annotations[1].label == "End"
        assert vis.annotations[1].index == -1

    def test_add_vector_field(self):
        """测试添加矢量场。"""
        vis = PhasePortraitVisualizer()

        def dx_dt(x, y):
            return y

        def dy_dt(x, y):
            return -x

        vis.add_vector_field(
            dx_dt,
            dy_dt,
            x_range=(-2, 2),
            y_range=(-2, 2),
            density=10,
        )

        assert vis.vector_field is not None
        assert vis.vector_field["X"].shape == (10, 10)
        assert vis.vector_field["Y"].shape == (10, 10)
        assert vis.vector_field["U"].shape == (10, 10)
        assert vis.vector_field["V"].shape == (10, 10)

    def test_add_nullcline(self):
        """测试添加零斜线。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(-2, 2, 100)
        y = np.zeros_like(x)

        vis.add_nullcline(x, y, label="dx/dt=0", color="blue")

        assert len(vis.nullclines) == 1
        assert vis.nullclines[0]["label"] == "dx/dt=0"
        assert np.allclose(vis.nullclines[0]["x"], x)

    def test_plot_2d_basic(self):
        """测试基本 2D 绘图。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)

        vis.add_trajectory(x, y, label="Sine wave")

        fig, ax = plt.subplots()
        result_ax = vis.plot(
            ax=ax,
            xlabel="x",
            ylabel="y",
            title="Test Plot",
        )

        assert result_ax is ax
        assert ax.get_xlabel() == "x"
        assert ax.get_ylabel() == "y"
        assert ax.get_title() == "Test Plot"
        plt.close(fig)

    def test_plot_2d_with_annotations(self):
        """测试带标注的 2D 绘图。"""
        vis = PhasePortraitVisualizer()
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)

        vis.add_trajectory(x, y, label="Sine wave")
        vis.add_annotation(0, "Start", color="green")
        vis.add_annotation(50, "Middle", color="yellow")
        vis.add_annotation(-1, "End", color="red")

        fig, ax = plt.subplots()
        vis.plot(ax=ax, xlabel="x", ylabel="y")

        # 检查标注是否被添加（通过检查 scatter 集合）
        collections = [c for c in ax.collections if hasattr(c, "get_sizes")]
        assert len(collections) >= 3  # 至少有 3 个标注点

        plt.close(fig)

    def test_plot_3d_basic(self):
        """测试基本 3D 绘图。"""
        vis = PhasePortraitVisualizer()

        t = np.linspace(0, 4 * np.pi, 500)
        x = np.cos(t)
        y = np.sin(t)
        z = t

        vis.add_trajectory(x, y, z, label="Helix")

        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
        result_ax = vis.plot(
            ax=ax,
            xlabel="x",
            ylabel="y",
            zlabel="z",
            title="3D Test",
        )

        assert result_ax is ax
        assert ax.get_xlabel() == "x"
        assert ax.get_ylabel() == "y"
        assert ax.get_zlabel() == "z"
        plt.close(fig)

    def test_clear(self):
        """测试清空功能。"""
        vis = PhasePortraitVisualizer()

        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        vis.add_trajectory(x, y)
        vis.add_annotation(0, "Start")
        vis.add_vector_field(lambda x, y: y, lambda x, y: -x, (-1, 1), (-1, 1))
        vis.add_nullcline(x, y)

        assert len(vis.trajectories) > 0
        assert len(vis.annotations) > 0
        assert vis.vector_field is not None
        assert len(vis.nullclines) > 0

        vis.clear()

        assert len(vis.trajectories) == 0
        assert len(vis.annotations) == 0
        assert vis.vector_field is None
        assert len(vis.nullclines) == 0

    def test_create_multi_view(self):
        """测试多视图投影。"""
        vis = PhasePortraitVisualizer()

        # 创建简单 3D 螺旋
        t = np.linspace(0, 4 * np.pi, 500)
        x = np.cos(t)
        y = np.sin(t)
        z = t

        x_var = StateVariable("x", "x", "m")
        y_var = StateVariable("y", "y", "m")
        z_var = StateVariable("z", "z", "m")

        fig = vis.create_multi_view(x, y, z, x_var, y_var, z_var)

        assert fig is not None
        assert len(fig.axes) == 3  # 3D + XY + XZ

        plt.close(fig)


class TestStateVariable:
    """测试 StateVariable 类。"""

    def test_basic_label(self):
        """测试基本标签生成。"""
        var = StateVariable("position", "x", "m")
        assert var.get_label() == "x [m]"

    def test_label_without_unit(self):
        """测试无单位标签。"""
        var = StateVariable("position", "x", "m")
        assert var.get_label(include_unit=False) == "x"

    def test_label_with_latex(self):
        """测试 LaTeX 标签。"""
        var = StateVariable("position", "x", "m", latex=r"$\theta$")
        assert var.get_label() == r"$\theta$ [m]"

    def test_label_no_unit(self):
        """测试无单位变量。"""
        var = StateVariable("position", "x", "")
        assert var.get_label() == "x"


class TestTrajectoryAnnotation:
    """测试 TrajectoryAnnotation 类。"""

    def test_initialization(self):
        """测试初始化。"""
        annot = TrajectoryAnnotation(
            index=10,
            label="Test point",
            color="blue",
            marker="x",
            size=100,
        )

        assert annot.index == 10
        assert annot.label == "Test point"
        assert annot.color == "blue"
        assert annot.marker == "x"
        assert annot.size == 100

    def test_defaults(self):
        """测试默认值。"""
        annot = TrajectoryAnnotation(index=5, label="Point")

        assert annot.color == "red"
        assert annot.marker == "o"
        assert annot.size == 50
        assert annot.zorder == 5


class TestQuickPhasePortrait:
    """测试快速绘图函数。"""

    def test_quick_plot(self):
        """测试快速绘图。"""
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)

        fig, ax = quick_phase_portrait(
            x,
            y,
            xlabel="Position",
            ylabel="Velocity",
            title="Quick Plot Test",
        )

        assert fig is not None
        assert ax is not None
        assert ax.get_xlabel() == "Position"
        assert ax.get_ylabel() == "Velocity"
        assert ax.get_title() == "Quick Plot Test"

        plt.close(fig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

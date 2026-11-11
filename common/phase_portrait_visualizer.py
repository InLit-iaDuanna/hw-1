"""Phase Portrait Visualizer: State space trajectory plotting with annotations.

提供灵活的相空间可视化工具，支持：
- 2D/3D 相轨迹绘制
- 自动轴标签和单位处理
- 关键点标注（起点、终点、事件点）
- 等倾线/零斜线叠加
- 矢量场可视化
- 多轨迹对比
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from typing import Optional, Literal, Callable, Any
from dataclasses import dataclass

from .plot_styles import PALETTE, create_figure, save_figure


@dataclass
class StateVariable:
    """状态变量配置。"""

    name: str
    symbol: str
    unit: str = ""
    latex: Optional[str] = None

    def get_label(self, include_unit: bool = True) -> str:
        """生成轴标签。"""
        label = self.latex if self.latex else self.symbol
        if include_unit and self.unit:
            return f"{label} [{self.unit}]"
        return label


@dataclass
class TrajectoryAnnotation:
    """轨迹标注配置。"""

    index: int
    label: str
    color: str = "red"
    marker: str = "o"
    size: int = 50
    zorder: int = 5


class PhasePortraitVisualizer:
    """相空间轨迹可视化器。

    支持 2D 和 3D 相空间轨迹绘制，提供丰富的标注和分析功能。

    Example:
        >>> vis = PhasePortraitVisualizer()
        >>> vis.add_trajectory(theta, theta_dot, label="Main trajectory")
        >>> vis.add_annotation(0, "Initial", color="green", marker="*")
        >>> vis.add_annotation(-1, "Final", color="red", marker="s")
        >>> vis.plot(xlabel="θ [rad]", ylabel="dθ/dt [rad/s]")
    """

    def __init__(self):
        """初始化可视化器。"""
        self.trajectories: list[dict[str, Any]] = []
        self.annotations: list[TrajectoryAnnotation] = []
        self.vector_field: Optional[dict] = None
        self.nullclines: list[dict] = []

    def add_trajectory(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: Optional[np.ndarray] = None,
        label: str = "",
        color: Optional[str] = None,
        linewidth: float = 1.5,
        alpha: float = 0.8,
        linestyle: str = "-",
        time: Optional[np.ndarray] = None,
        colormap: str = "viridis",
    ) -> None:
        """添加轨迹。

        Args:
            x, y: 状态空间坐标
            z: 第三维坐标（可选，用于 3D 相空间）
            label: 轨迹标签
            color: 线条颜色（None 则自动分配）
            linewidth: 线宽
            alpha: 透明度
            linestyle: 线型
            time: 时间数组（用于颜色编码）
            colormap: 颜色映射（当 time 非空时使用）
        """
        if color is None:
            # 自动分配颜色
            color_cycle = [
                PALETTE["ok"],
                PALETTE["left"],
                PALETTE["right"],
                PALETTE["warn"],
                PALETTE["neutral"],
            ]
            color = color_cycle[len(self.trajectories) % len(color_cycle)]

        self.trajectories.append(
            {
                "x": np.asarray(x),
                "y": np.asarray(y),
                "z": np.asarray(z) if z is not None else None,
                "label": label,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "linestyle": linestyle,
                "time": np.asarray(time) if time is not None else None,
                "colormap": colormap,
            }
        )

    def add_annotation(
        self,
        index: int,
        label: str,
        color: str = "red",
        marker: str = "o",
        size: int = 50,
        zorder: int = 5,
        trajectory_index: int = 0,
    ) -> None:
        """添加轨迹标注点。

        Args:
            index: 轨迹点索引（支持负数索引）
            label: 标注文本
            color: 标注颜色
            marker: 标记符号
            size: 标记大小
            zorder: 绘制层级
            trajectory_index: 要标注的轨迹索引（默认第一条）
        """
        self.annotations.append(
            TrajectoryAnnotation(
                index=index,
                label=label,
                color=color,
                marker=marker,
                size=size,
                zorder=zorder,
            )
        )

    def add_vector_field(
        self,
        dx_dt: Callable[[np.ndarray, np.ndarray], np.ndarray],
        dy_dt: Callable[[np.ndarray, np.ndarray], np.ndarray],
        x_range: tuple[float, float],
        y_range: tuple[float, float],
        density: int = 20,
        color: str = "gray",
        alpha: float = 0.4,
        scale: Optional[float] = None,
    ) -> None:
        """添加矢量场。

        Args:
            dx_dt: x 方向的导数函数 f(x, y) -> dx/dt
            dy_dt: y 方向的导数函数 f(x, y) -> dy/dt
            x_range: x 坐标范围 (min, max)
            y_range: y 坐标范围 (min, max)
            density: 网格密度
            color: 矢量颜色
            alpha: 透明度
            scale: 矢量缩放因子（None 则自动）
        """
        x_grid = np.linspace(x_range[0], x_range[1], density)
        y_grid = np.linspace(y_range[0], y_range[1], density)
        X, Y = np.meshgrid(x_grid, y_grid)

        U = dx_dt(X, Y)
        V = dy_dt(X, Y)

        self.vector_field = {
            "X": X,
            "Y": Y,
            "U": U,
            "V": V,
            "color": color,
            "alpha": alpha,
            "scale": scale,
        }

    def add_nullcline(
        self,
        x: np.ndarray,
        y: np.ndarray,
        label: str = "",
        color: str = "black",
        linestyle: str = "--",
        linewidth: float = 1.0,
        alpha: float = 0.6,
    ) -> None:
        """添加零斜线（nullcline）或等倾线（isocline）。

        Args:
            x, y: 曲线坐标
            label: 曲线标签
            color: 线条颜色
            linestyle: 线型
            linewidth: 线宽
            alpha: 透明度
        """
        self.nullclines.append(
            {
                "x": np.asarray(x),
                "y": np.asarray(y),
                "label": label,
                "color": color,
                "linestyle": linestyle,
                "linewidth": linewidth,
                "alpha": alpha,
            }
        )

    def plot(
        self,
        ax: Optional[Axes] = None,
        xlabel: str = "State x",
        ylabel: str = "State y",
        zlabel: str = "State z",
        title: str = "",
        show_legend: bool = True,
        show_grid: bool = True,
        show_start_end: bool = True,
        equal_aspect: bool = False,
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
        zlim: Optional[tuple[float, float]] = None,
    ) -> Axes:
        """绘制相空间轨迹。

        Args:
            ax: matplotlib Axes 对象（None 则创建新图）
            xlabel, ylabel, zlabel: 坐标轴标签
            title: 图表标题
            show_legend: 是否显示图例
            show_grid: 是否显示网格
            show_start_end: 是否自动标注起点和终点
            equal_aspect: 是否使用等比例坐标轴
            xlim, ylim, zlim: 坐标轴范围

        Returns:
            Axes 对象
        """
        # 判断是否为 3D 图
        is_3d = any(traj["z"] is not None for traj in self.trajectories)

        if ax is None:
            if is_3d:
                fig = plt.figure(figsize=(10, 8))
                ax = fig.add_subplot(111, projection="3d")
            else:
                fig, ax = create_figure("medium")

        # 绘制矢量场（仅 2D）
        if not is_3d and self.vector_field is not None:
            vf = self.vector_field
            ax.quiver(
                vf["X"],
                vf["Y"],
                vf["U"],
                vf["V"],
                color=vf["color"],
                alpha=vf["alpha"],
                scale=vf["scale"],
                scale_units="xy" if vf["scale"] else None,
                zorder=0,
            )

        # 绘制零斜线（仅 2D）
        if not is_3d:
            for nc in self.nullclines:
                ax.plot(
                    nc["x"],
                    nc["y"],
                    color=nc["color"],
                    linestyle=nc["linestyle"],
                    linewidth=nc["linewidth"],
                    alpha=nc["alpha"],
                    label=nc["label"],
                    zorder=1,
                )

        # 绘制轨迹
        for traj in self.trajectories:
            x, y, z = traj["x"], traj["y"], traj["z"]

            if traj["time"] is not None and not is_3d:
                # 时间颜色编码（仅 2D）
                points = np.array([x, y]).T.reshape(-1, 1, 2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)

                from matplotlib.collections import LineCollection

                lc = LineCollection(
                    segments,
                    cmap=traj["colormap"],
                    linewidths=traj["linewidth"],
                    alpha=traj["alpha"],
                )
                lc.set_array(traj["time"])
                ax.add_collection(lc)

                # 添加颜色条
                cbar = plt.colorbar(lc, ax=ax)
                cbar.set_label("Time")

            elif is_3d and z is not None:
                # 3D 绘制
                if traj["time"] is not None:
                    # 3D 时间颜色编码
                    points = np.array([x, y, z]).T.reshape(-1, 1, 3)
                    segments = np.concatenate([points[:-1], points[1:]], axis=1)

                    lc = Line3DCollection(
                        segments,
                        cmap=traj["colormap"],
                        linewidths=traj["linewidth"],
                        alpha=traj["alpha"],
                    )
                    lc.set_array(traj["time"])
                    ax.add_collection(lc)
                else:
                    ax.plot(
                        x,
                        y,
                        z,
                        color=traj["color"],
                        linewidth=traj["linewidth"],
                        alpha=traj["alpha"],
                        linestyle=traj["linestyle"],
                        label=traj["label"],
                    )
            else:
                # 2D 绘制
                ax.plot(
                    x,
                    y,
                    color=traj["color"],
                    linewidth=traj["linewidth"],
                    alpha=traj["alpha"],
                    linestyle=traj["linestyle"],
                    label=traj["label"],
                )

            # 自动标注起点和终点
            if show_start_end and len(x) > 0:
                if is_3d and z is not None:
                    ax.scatter(
                        [x[0]],
                        [y[0]],
                        [z[0]],
                        s=80,
                        c="green",
                        marker="*",
                        edgecolors="black",
                        linewidths=1.0,
                        zorder=10,
                        label=f"{traj['label']} start" if traj["label"] else "Start",
                    )
                    ax.scatter(
                        [x[-1]],
                        [y[-1]],
                        [z[-1]],
                        s=60,
                        c="red",
                        marker="s",
                        edgecolors="black",
                        linewidths=1.0,
                        zorder=10,
                        label=f"{traj['label']} end" if traj["label"] else "End",
                    )
                else:
                    ax.scatter(
                        x[0],
                        y[0],
                        s=80,
                        c="green",
                        marker="*",
                        edgecolors="black",
                        linewidths=1.0,
                        zorder=10,
                        label=f"{traj['label']} start" if traj["label"] else "Start",
                    )
                    ax.scatter(
                        x[-1],
                        y[-1],
                        s=60,
                        c="red",
                        marker="s",
                        edgecolors="black",
                        linewidths=1.0,
                        zorder=10,
                        label=f"{traj['label']} end" if traj["label"] else "End",
                    )

        # 绘制自定义标注
        for annot in self.annotations:
            if len(self.trajectories) == 0:
                continue

            traj = self.trajectories[0]  # 默认标注第一条轨迹
            x, y, z = traj["x"], traj["y"], traj["z"]
            idx = annot.index

            if is_3d and z is not None:
                ax.scatter(
                    [x[idx]],
                    [y[idx]],
                    [z[idx]],
                    s=annot.size,
                    c=annot.color,
                    marker=annot.marker,
                    edgecolors="white",
                    linewidths=1.5,
                    zorder=annot.zorder,
                    label=annot.label,
                )
            else:
                ax.scatter(
                    x[idx],
                    y[idx],
                    s=annot.size,
                    c=annot.color,
                    marker=annot.marker,
                    edgecolors="white",
                    linewidths=1.5,
                    zorder=annot.zorder,
                    label=annot.label,
                )

        # 设置标签和标题
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        if is_3d:
            ax.set_zlabel(zlabel, fontsize=11)

        if title:
            ax.set_title(title, fontsize=13, fontweight="bold")

        # 设置坐标范围
        if xlim is not None:
            ax.set_xlim(xlim)
        if ylim is not None:
            ax.set_ylim(ylim)
        if is_3d and zlim is not None:
            ax.set_zlim(zlim)

        # 等比例坐标轴
        if equal_aspect and not is_3d:
            ax.set_aspect("equal", adjustable="box")

        # 网格和图例
        if show_grid:
            ax.grid(True, alpha=0.3)

        if show_legend:
            ax.legend(loc="best", fontsize=9)

        return ax

    def create_multi_view(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        x_var: StateVariable,
        y_var: StateVariable,
        z_var: StateVariable,
        title: str = "3D State Space Multi-View",
        figsize: tuple[float, float] = (14, 10),
    ) -> Figure:
        """创建 3D 状态空间的多视图投影。

        Args:
            x, y, z: 三维状态坐标
            x_var, y_var, z_var: 状态变量配置
            title: 总标题
            figsize: 图形尺寸

        Returns:
            Figure 对象
        """
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 3D 主视图
        ax_3d = fig.add_subplot(gs[:, 0], projection="3d")
        self.add_trajectory(x, y, z, label="3D trajectory")
        self.plot(
            ax=ax_3d,
            xlabel=x_var.get_label(),
            ylabel=y_var.get_label(),
            zlabel=z_var.get_label(),
            title="3D Phase Space",
            show_start_end=True,
        )

        # XY 平面投影
        ax_xy = fig.add_subplot(gs[0, 1])
        ax_xy.plot(x, y, color=PALETTE["ok"], linewidth=1.5, alpha=0.8)
        ax_xy.scatter(
            x[0],
            y[0],
            s=80,
            c="green",
            marker="*",
            edgecolors="black",
            linewidths=1.0,
            zorder=10,
        )
        ax_xy.scatter(
            x[-1],
            y[-1],
            s=60,
            c="red",
            marker="s",
            edgecolors="black",
            linewidths=1.0,
            zorder=10,
        )
        ax_xy.set_xlabel(x_var.get_label())
        ax_xy.set_ylabel(y_var.get_label())
        ax_xy.set_title("XY Projection")
        ax_xy.grid(True, alpha=0.3)

        # XZ 平面投影
        ax_xz = fig.add_subplot(gs[1, 1])
        ax_xz.plot(x, z, color=PALETTE["left"], linewidth=1.5, alpha=0.8)
        ax_xz.scatter(
            x[0],
            z[0],
            s=80,
            c="green",
            marker="*",
            edgecolors="black",
            linewidths=1.0,
            zorder=10,
        )
        ax_xz.scatter(
            x[-1],
            z[-1],
            s=60,
            c="red",
            marker="s",
            edgecolors="black",
            linewidths=1.0,
            zorder=10,
        )
        ax_xz.set_xlabel(x_var.get_label())
        ax_xz.set_ylabel(z_var.get_label())
        ax_xz.set_title("XZ Projection")
        ax_xz.grid(True, alpha=0.3)

        fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

        return fig

    def clear(self) -> None:
        """清空所有轨迹和标注。"""
        self.trajectories.clear()
        self.annotations.clear()
        self.vector_field = None
        self.nullclines.clear()


def quick_phase_portrait(
    x: np.ndarray,
    y: np.ndarray,
    xlabel: str = "Position",
    ylabel: str = "Velocity",
    title: str = "Phase Portrait",
    output_path: Optional[str] = None,
    **kwargs,
) -> tuple[Figure, Axes]:
    """快速绘制相位图的便捷函数。

    Args:
        x, y: 状态坐标
        xlabel, ylabel: 坐标轴标签
        title: 图表标题
        output_path: 保存路径（None 则不保存）
        **kwargs: 传递给 PhasePortraitVisualizer.plot() 的其他参数

    Returns:
        fig, ax
    """
    vis = PhasePortraitVisualizer()
    vis.add_trajectory(x, y, label="Trajectory")

    fig, ax = create_figure("medium")
    vis.plot(ax=ax, xlabel=xlabel, ylabel=ylabel, title=title, **kwargs)

    if output_path:
        save_figure(fig, output_path)

    return fig, ax


__all__ = [
    "PhasePortraitVisualizer",
    "StateVariable",
    "TrajectoryAnnotation",
    "quick_phase_portrait",
]

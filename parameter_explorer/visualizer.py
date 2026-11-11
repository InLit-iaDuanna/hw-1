"""可视化工具。

生成参数空间探索的各类可视化：
- 2D 切片图（固定其他参数）
- 3D 响应曲面
- 等高线图
- Pareto 前沿
- 灵敏度排行
- 交互热图
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D


class ParameterVisualizer:
    """参数空间可视化器。"""

    def __init__(
        self, output_dir: Path | str | None = None, style: str = "seaborn-v0_8-darkgrid"
    ):
        """
        Args:
            output_dir: 输出目录（None 则不保存）
            style: matplotlib 样式
        """
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        plt.style.use(style)
        sns.set_palette("husl")

    def plot_2d_slice(
        self,
        param_name: str,
        param_values: np.ndarray,
        objective_values: np.ndarray,
        samples_x: np.ndarray | None = None,
        samples_y: np.ndarray | None = None,
        xlabel: str | None = None,
        ylabel: str = "Objective",
        title: str | None = None,
        filename: str | None = None,
    ) -> None:
        """绘制 2D 参数切片图。

        Args:
            param_name: 参数名称
            param_values: 参数值数组
            objective_values: 目标函数值数组
            samples_x: 实际采样点 x 坐标（可选）
            samples_y: 实际采样点 y 坐标（可选）
            xlabel: x 轴标签
            ylabel: y 轴标签
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制响应曲线
        ax.plot(
            param_values, objective_values, "b-", linewidth=2, label="Response Surface"
        )

        # 绘制采样点
        if samples_x is not None and samples_y is not None:
            ax.scatter(
                samples_x,
                samples_y,
                c="red",
                s=50,
                alpha=0.6,
                label="Samples",
                zorder=5,
            )

        ax.set_xlabel(xlabel or param_name, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title or f"{param_name} Slice", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_3d_surface(
        self,
        param1_name: str,
        param2_name: str,
        param1_values: np.ndarray,
        param2_values: np.ndarray,
        objective_grid: np.ndarray,
        samples_x: np.ndarray | None = None,
        samples_y: np.ndarray | None = None,
        samples_z: np.ndarray | None = None,
        title: str | None = None,
        filename: str | None = None,
    ) -> None:
        """绘制 3D 响应曲面。

        Args:
            param1_name: 第一个参数名称
            param2_name: 第二个参数名称
            param1_values: 第一个参数值数组（网格）
            param2_values: 第二个参数值数组（网格）
            objective_grid: 目标函数值网格 (len(p1), len(p2))
            samples_x: 采样点 x 坐标（可选）
            samples_y: 采样点 y 坐标（可选）
            samples_z: 采样点 z 坐标（可选）
            title: 图标题
            filename: 保存文件名
        """
        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection="3d")

        # 创建网格
        X, Y = np.meshgrid(param1_values, param2_values, indexing="ij")

        # 绘制曲面
        surf = ax.plot_surface(
            X,
            Y,
            objective_grid,
            cmap=cm.viridis,
            alpha=0.8,
            edgecolor="none",
            antialiased=True,
        )

        # 绘制采样点
        if samples_x is not None and samples_y is not None and samples_z is not None:
            ax.scatter(
                samples_x,
                samples_y,
                samples_z,
                c="red",
                s=30,
                alpha=0.8,
                label="Samples",
            )

        ax.set_xlabel(param1_name, fontsize=11)
        ax.set_ylabel(param2_name, fontsize=11)
        ax.set_zlabel("Objective", fontsize=11)
        ax.set_title(
            title or f"Response Surface: {param1_name} vs {param2_name}",
            fontsize=13,
            fontweight="bold",
        )

        # 添加颜色条
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_contour(
        self,
        param1_name: str,
        param2_name: str,
        param1_values: np.ndarray,
        param2_values: np.ndarray,
        objective_grid: np.ndarray,
        samples_x: np.ndarray | None = None,
        samples_y: np.ndarray | None = None,
        n_levels: int = 20,
        title: str | None = None,
        filename: str | None = None,
    ) -> None:
        """绘制等高线图。

        Args:
            param1_name: 第一个参数名称
            param2_name: 第二个参数名称
            param1_values: 第一个参数值数组
            param2_values: 第二个参数值数组
            objective_grid: 目标函数值网格
            samples_x: 采样点 x 坐标（可选）
            samples_y: 采样点 y 坐标（可选）
            n_levels: 等高线级数
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # 创建网格
        X, Y = np.meshgrid(param1_values, param2_values, indexing="ij")

        # 绘制填充等高线
        contourf = ax.contourf(
            X, Y, objective_grid, levels=n_levels, cmap="viridis", alpha=0.8
        )
        # 绘制等高线
        contour = ax.contour(
            X,
            Y,
            objective_grid,
            levels=n_levels,
            colors="black",
            alpha=0.3,
            linewidths=0.5,
        )
        ax.clabel(contour, inline=True, fontsize=8, fmt="%.2f")

        # 绘制采样点
        if samples_x is not None and samples_y is not None:
            ax.scatter(
                samples_x,
                samples_y,
                c="red",
                s=40,
                alpha=0.7,
                edgecolors="white",
                linewidths=0.5,
                label="Samples",
                zorder=5,
            )

        ax.set_xlabel(param1_name, fontsize=12)
        ax.set_ylabel(param2_name, fontsize=12)
        ax.set_title(
            title or f"Contour Plot: {param1_name} vs {param2_name}",
            fontsize=14,
            fontweight="bold",
        )

        # 颜色条
        cbar = fig.colorbar(contourf, ax=ax)
        cbar.set_label("Objective", fontsize=11)

        if samples_x is not None and samples_y is not None:
            ax.legend()

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_pareto_front(
        self,
        objectives: np.ndarray,
        obj1_name: str = "Objective 1",
        obj2_name: str = "Objective 2",
        highlight_indices: list[int] | None = None,
        title: str = "Pareto Front",
        filename: str | None = None,
    ) -> None:
        """绘制 Pareto 前沿（2D）。

        Args:
            objectives: (n_solutions, 2) 目标值数组
            obj1_name: 第一个目标名称
            obj2_name: 第二个目标名称
            highlight_indices: 要高亮的解的索引
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # 绘制所有解
        ax.scatter(
            objectives[:, 0],
            objectives[:, 1],
            c="blue",
            s=60,
            alpha=0.6,
            label="Pareto Solutions",
        )

        # 高亮特定解
        if highlight_indices:
            highlight_objs = objectives[highlight_indices]
            ax.scatter(
                highlight_objs[:, 0],
                highlight_objs[:, 1],
                c="red",
                s=120,
                marker="*",
                edgecolors="black",
                linewidths=1.5,
                label="Highlighted",
                zorder=5,
            )

        # 连接 Pareto 前沿
        sorted_indices = np.argsort(objectives[:, 0])
        sorted_objs = objectives[sorted_indices]
        ax.plot(sorted_objs[:, 0], sorted_objs[:, 1], "k--", alpha=0.3, linewidth=1)

        ax.set_xlabel(obj1_name, fontsize=12)
        ax.set_ylabel(obj2_name, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_sensitivity_bar(
        self,
        param_names: list[str],
        sensitivity_scores: np.ndarray,
        errors: np.ndarray | None = None,
        ylabel: str = "Sensitivity",
        title: str = "Parameter Sensitivity",
        filename: str | None = None,
    ) -> None:
        """绘制灵敏度条形图。

        Args:
            param_names: 参数名称列表
            sensitivity_scores: 灵敏度分数
            errors: 误差条（可选）
            ylabel: y 轴标签
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # 排序
        sorted_indices = np.argsort(sensitivity_scores)[::-1]
        sorted_names = [param_names[i] for i in sorted_indices]
        sorted_scores = sensitivity_scores[sorted_indices]
        sorted_errors = errors[sorted_indices] if errors is not None else None

        # 颜色映射
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(sorted_names)))

        # 绘制条形图
        bars = ax.barh(
            sorted_names,
            sorted_scores,
            xerr=sorted_errors,
            color=colors,
            alpha=0.8,
            capsize=5,
        )

        ax.set_xlabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.grid(True, axis="x", alpha=0.3)

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_interaction_heatmap(
        self,
        interaction_matrix: np.ndarray,
        param_names: list[str],
        title: str = "Parameter Interaction Matrix",
        filename: str | None = None,
    ) -> None:
        """绘制参数交互热图。

        Args:
            interaction_matrix: (n_params, n_params) 交互矩阵
            param_names: 参数名称列表
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # 绘制热图
        sns.heatmap(
            interaction_matrix,
            annot=True,
            fmt=".3f",
            cmap="coolwarm",
            center=0,
            square=True,
            xticklabels=param_names,
            yticklabels=param_names,
            cbar_kws={"label": "Interaction Strength"},
            ax=ax,
        )

        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        plt.tight_layout()

        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_optimization_history(
        self,
        iterations: np.ndarray,
        best_values: np.ndarray,
        all_values: np.ndarray | None = None,
        ylabel: str = "Objective Value",
        title: str = "Optimization History",
        filename: str | None = None,
    ) -> None:
        """绘制优化历史。

        Args:
            iterations: 迭代次数数组
            best_values: 历史最优值数组
            all_values: 所有评估值数组（可选）
            ylabel: y 轴标签
            title: 图标题
            filename: 保存文件名
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制所有评估点
        if all_values is not None:
            ax.scatter(
                iterations,
                all_values,
                c="lightblue",
                s=20,
                alpha=0.5,
                label="All Evaluations",
            )

        # 绘制历史最优
        ax.plot(
            iterations,
            best_values,
            "r-",
            linewidth=2.5,
            marker="o",
            markersize=5,
            label="Best So Far",
        )

        ax.set_xlabel("Iteration", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

    def plot_parameter_distribution(
        self,
        samples: np.ndarray,
        param_names: list[str],
        title: str = "Parameter Sample Distribution",
        filename: str | None = None,
    ) -> None:
        """绘制参数分布直方图（多子图）。

        Args:
            samples: (n_samples, n_params) 样本矩阵
            param_names: 参数名称列表
            title: 图标题
            filename: 保存文件名
        """
        n_params = len(param_names)
        n_cols = min(3, n_params)
        n_rows = (n_params + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        axes = np.array(axes).flatten() if n_params > 1 else [axes]

        for i, (ax, name) in enumerate(zip(axes, param_names)):
            ax.hist(
                samples[:, i], bins=30, color="steelblue", alpha=0.7, edgecolor="black"
            )
            ax.set_xlabel(name, fontsize=11)
            ax.set_ylabel("Frequency", fontsize=11)
            ax.set_title(f"Distribution: {name}", fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3, axis="y")

        # 隐藏多余子图
        for j in range(n_params, len(axes)):
            axes[j].axis("off")

        fig.suptitle(title, fontsize=15, fontweight="bold", y=1.02)
        plt.tight_layout()

        if filename and self.output_dir:
            plt.savefig(self.output_dir / filename, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()

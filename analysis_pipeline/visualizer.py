"""
可视化模块
生成标准图表、对比图、统计图等
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from data_loader import GaitData
from feature_extractor import GaitFeatures


class Visualizer:
    """可视化器"""

    def __init__(self, config: dict):
        """
        初始化可视化器

        Args:
            config: visualization 配置字典
        """
        self.config = config
        self.figure_format = config.get("figure_format", "png")
        self.figure_dpi = config.get("figure_dpi", 300)
        self.figure_size = tuple(config.get("figure_size", [10, 6]))
        self.color_scheme = config.get("color_scheme", {})

        # 设置中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

    def get_version_color(self, version: str) -> str:
        """获取版本颜色"""
        return self.color_scheme.get(version, f"C{hash(version) % 10}")

    def plot_time_series(
        self,
        gait_data: GaitData,
        signals: list[str],
        output_path: str | Path,
        title: str | None = None,
    ):
        """
        绘制时间序列图

        Args:
            gait_data: 步态数据
            signals: 信号名称列表
            output_path: 输出路径
            title: 图表标题
        """
        n_signals = len(signals)
        fig, axes = plt.subplots(
            n_signals, 1, figsize=(self.figure_size[0], 3 * n_signals), sharex=True
        )

        if n_signals == 1:
            axes = [axes]

        for ax, signal_name in zip(axes, signals):
            data = gait_data.get_column(signal_name)
            if data is not None:
                ax.plot(
                    gait_data.time,
                    data,
                    linewidth=1.5,
                    color=self.get_version_color(gait_data.version),
                )
                ax.set_ylabel(signal_name.replace("_", " ").title())
                ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Time (s)")

        if title:
            fig.suptitle(title, fontsize=14, fontweight="bold")
        else:
            fig.suptitle(
                f"{gait_data.label} - Time Series", fontsize=14, fontweight="bold"
            )

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved time series plot: {output_path}")

    def plot_phase_diagram(
        self,
        gait_data: GaitData,
        x_signal: str,
        y_signal: str,
        output_path: str | Path,
        title: str | None = None,
    ):
        """
        绘制相位图

        Args:
            gait_data: 步态数据
            x_signal: X轴信号
            y_signal: Y轴信号
            output_path: 输出路径
            title: 图表标题
        """
        x_data = gait_data.get_column(x_signal)
        y_data = gait_data.get_column(y_signal)

        if x_data is None or y_data is None:
            print("  Warning: Could not plot phase diagram, signals not found")
            return

        fig, ax = plt.subplots(figsize=self.figure_size)

        # 绘制轨迹，颜色随时间变化
        scatter = ax.scatter(
            x_data, y_data, c=gait_data.time, cmap="viridis", s=10, alpha=0.6
        )
        ax.plot(x_data[0], y_data[0], "go", markersize=10, label="Start", zorder=5)
        ax.plot(x_data[-1], y_data[-1], "r^", markersize=10, label="End", zorder=5)

        ax.set_xlabel(x_signal.replace("_", " ").title())
        ax.set_ylabel(y_signal.replace("_", " ").title())
        ax.grid(True, alpha=0.3)
        ax.legend()

        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Time (s)")

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold")
        else:
            ax.set_title(
                f"{gait_data.label} - Phase Diagram", fontsize=14, fontweight="bold"
            )

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved phase diagram: {output_path}")

    def plot_comparison_bars(
        self,
        features_dict: dict[str, GaitFeatures],
        metrics: list[str],
        output_path: str | Path,
        title: str | None = None,
    ):
        """
        绘制对比柱状图

        Args:
            features_dict: 版本到特征的字典
            metrics: 指标列表
            output_path: 输出路径
            title: 图表标题
        """
        n_metrics = len(metrics)
        n_versions = len(features_dict)

        fig, axes = plt.subplots(
            (n_metrics + 1) // 2, 2, figsize=(12, 4 * ((n_metrics + 1) // 2))
        )
        axes = axes.flatten() if n_metrics > 1 else [axes]

        versions = list(features_dict.keys())
        labels = [features_dict[v].label for v in versions]
        colors = [self.get_version_color(v) for v in versions]

        for idx, metric in enumerate(metrics):
            if idx >= len(axes):
                break

            ax = axes[idx]
            values = []

            for version in versions:
                value = getattr(features_dict[version], metric, None)
                values.append(value if value is not None else 0.0)

            x = np.arange(n_versions)
            bars = ax.bar(x, values, color=colors, alpha=0.7, edgecolor="black")

            # 添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{value:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_ylabel(metric.replace("_", " ").title())
            ax.grid(True, alpha=0.3, axis="y")

        # 隐藏多余的子图
        for idx in range(n_metrics, len(axes)):
            axes[idx].set_visible(False)

        if title:
            fig.suptitle(title, fontsize=14, fontweight="bold")
        else:
            fig.suptitle("Feature Comparison", fontsize=14, fontweight="bold")

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved comparison bars: {output_path}")

    def plot_box_comparison(
        self,
        data_dict: dict[str, np.ndarray],
        output_path: str | Path,
        ylabel: str = "Value",
        title: str | None = None,
    ):
        """
        绘制箱线图对比

        Args:
            data_dict: 版本到数据数组的字典
            output_path: 输出路径
            ylabel: Y轴标签
            title: 图表标题
        """
        fig, ax = plt.subplots(figsize=self.figure_size)

        versions = list(data_dict.keys())
        data = [data_dict[v] for v in versions]
        colors = [self.get_version_color(v) for v in versions]

        bp = ax.boxplot(
            data,
            labels=versions,
            patch_artist=True,
            notch=True,
            showmeans=True,
        )

        # 设置颜色
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3, axis="y")

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold")

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved box plot: {output_path}")

    def plot_correlation_heatmap(
        self,
        features_dict: dict[str, GaitFeatures],
        metrics: list[str],
        output_path: str | Path,
        title: str | None = None,
    ):
        """
        绘制相关性热图

        Args:
            features_dict: 版本到特征的字典
            metrics: 指标列表
            output_path: 输出路径
            title: 图表标题
        """
        # 构建特征矩阵
        data_matrix = []
        valid_metrics = []

        for metric in metrics:
            values = []
            for version in features_dict:
                value = getattr(features_dict[version], metric, None)
                if value is not None and not np.isnan(value):
                    values.append(value)
                else:
                    values.append(0.0)

            # 只保留有变化的指标
            if np.std(values) > 1e-6:
                data_matrix.append(values)
                valid_metrics.append(metric)

        if len(data_matrix) < 2:
            print("  Warning: Not enough valid metrics for correlation heatmap")
            return

        data_matrix = np.array(data_matrix)

        # 计算相关矩阵
        corr_matrix = np.corrcoef(data_matrix)

        # 绘制热图
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")

        # 设置刻度
        ax.set_xticks(np.arange(len(valid_metrics)))
        ax.set_yticks(np.arange(len(valid_metrics)))
        ax.set_xticklabels([m.replace("_", " ") for m in valid_metrics], rotation=90)
        ax.set_yticklabels([m.replace("_", " ") for m in valid_metrics])

        # 添加数值标签
        for i in range(len(valid_metrics)):
            for j in range(len(valid_metrics)):
                text = ax.text(
                    j,
                    i,
                    f"{corr_matrix[i, j]:.2f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=8,
                )

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Correlation Coefficient")

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold")
        else:
            ax.set_title("Feature Correlation Matrix", fontsize=14, fontweight="bold")

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved correlation heatmap: {output_path}")

    def plot_gait_cycle(
        self,
        gait_data: GaitData,
        output_path: str | Path,
        title: str | None = None,
    ):
        """
        绘制步态周期综合图

        Args:
            gait_data: 步态数据
            output_path: 输出路径
            title: 图表标题
        """
        fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

        # 1. 髋关节角度
        if (
            "left_hip" in gait_data.joint_angles
            and "right_hip" in gait_data.joint_angles
        ):
            axes[0].plot(
                gait_data.time,
                np.rad2deg(gait_data.joint_angles["left_hip"]),
                label="Left Hip",
                linewidth=1.5,
            )
            axes[0].plot(
                gait_data.time,
                np.rad2deg(gait_data.joint_angles["right_hip"]),
                label="Right Hip",
                linewidth=1.5,
            )
            axes[0].set_ylabel("Hip Angle (deg)")
            axes[0].legend(loc="upper right")
            axes[0].grid(True, alpha=0.3)

        # 2. 膝关节角度
        if (
            "left_knee" in gait_data.joint_angles
            and "right_knee" in gait_data.joint_angles
        ):
            axes[1].plot(
                gait_data.time,
                np.rad2deg(gait_data.joint_angles["left_knee"]),
                label="Left Knee",
                linewidth=1.5,
            )
            axes[1].plot(
                gait_data.time,
                np.rad2deg(gait_data.joint_angles["right_knee"]),
                label="Right Knee",
                linewidth=1.5,
            )
            axes[1].set_ylabel("Knee Angle (deg)")
            axes[1].legend(loc="upper right")
            axes[1].grid(True, alpha=0.3)

        # 3. 接触状态
        if (
            "left_contact" in gait_data.contact_states
            and "right_contact" in gait_data.contact_states
        ):
            axes[2].fill_between(
                gait_data.time,
                0,
                gait_data.contact_states["left_contact"],
                alpha=0.5,
                label="Left Contact",
            )
            axes[2].fill_between(
                gait_data.time,
                0,
                -gait_data.contact_states["right_contact"],
                alpha=0.5,
                label="Right Contact",
            )
            axes[2].set_ylabel("Contact State")
            axes[2].legend(loc="upper right")
            axes[2].grid(True, alpha=0.3)

        # 4. 功率
        if gait_data.power is not None:
            axes[3].plot(gait_data.time, gait_data.power, linewidth=1.5, color="red")
            axes[3].axhline(y=0, color="black", linestyle="--", linewidth=0.5)
            axes[3].set_ylabel("Power (W)")
            axes[3].grid(True, alpha=0.3)

        axes[-1].set_xlabel("Time (s)")

        if title:
            fig.suptitle(title, fontsize=14, fontweight="bold")
        else:
            fig.suptitle(
                f"{gait_data.label} - Gait Cycle", fontsize=14, fontweight="bold"
            )

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches="tight")
        plt.close()

        print(f"  Saved gait cycle plot: {output_path}")


def main():
    """测试可视化"""
    from pathlib import Path

    import yaml
    from data_loader import DataLoader
    from feature_extractor import FeatureExtractor
    from preprocessor import DataPreprocessor

    config_path = Path(__file__).parent / "pipeline_config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    loader = DataLoader(config_path)
    preprocessor = DataPreprocessor(config["preprocessing"])
    extractor = FeatureExtractor(config["feature_extraction"])
    visualizer = Visualizer(config["visualization"])

    print("=" * 60)
    print("Visualizer Test")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path(__file__).parent / "test_plots"
    output_dir.mkdir(exist_ok=True)

    # 加载数据
    gait_data = loader.load_version("v09_stable")
    processed = preprocessor.preprocess_gait_data(gait_data)

    # 生成各种图表
    print("\nGenerating plots...")

    visualizer.plot_gait_cycle(
        processed,
        output_dir / "gait_cycle.png",
    )

    visualizer.plot_phase_diagram(
        processed,
        "left_hip",
        "left_hip_vel",
        output_dir / "phase_diagram.png",
    )

    print(f"\nPlots saved to {output_dir}")


if __name__ == "__main__":
    main()

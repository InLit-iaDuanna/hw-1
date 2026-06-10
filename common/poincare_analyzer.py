"""Poincaré 分析器：自动截面检测与返回映射生成。

基于 common/poincare.py 实现的高级分析器，提供：
- 自动截面点检测（支持多种触发条件）
- 返回映射可视化
- Floquet 乘子计算
- 稳定性分析
"""

from __future__ import annotations

import numpy as np
from typing import Literal, Callable
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from .poincare import collect_section, plot_section, floquet_multipliers


class PoincareAnalyzer:
    """Poincaré 截面分析器。

    自动检测截面点、生成返回映射、计算 Floquet 乘子。
    """

    def __init__(
        self,
        rows: list[dict],
        state_keys: tuple[str, ...] | list[str],
        section_mode: Literal["support_change", "heel_strike", "custom"] = "support_change",
        custom_detector: Callable[[dict, dict], bool] | None = None,
    ):
        """初始化 Poincaré 分析器。

        Args:
            rows: simulate 输出的轨迹数据列表
            state_keys: 要分析的状态变量键名（如 ("q1", "q1_dot")）
            section_mode: 截面检测模式
                - "support_change": 支撑足切换时刻（默认）
                - "heel_strike": 脚跟触地时刻
                - "custom": 自定义检测器
            custom_detector: 当 section_mode="custom" 时使用的检测函数
                接收 (prev_row, curr_row) 返回 bool
        """
        self.rows = rows
        self.state_keys = tuple(state_keys)
        self.section_mode = section_mode
        self.custom_detector = custom_detector

        # 截面点数据
        self._section_pts: np.ndarray | None = None
        self._section_indices: list[int] | None = None

        # Floquet 分析结果
        self._floquet_result: dict | None = None

    def detect_section(self) -> np.ndarray:
        """检测并提取截面点。

        Returns:
            shape (N, d) 的截面点数组
        """
        if self._section_pts is not None:
            return self._section_pts

        if not self.rows:
            self._section_pts = np.empty((0, len(self.state_keys)))
            self._section_indices = []
            return self._section_pts

        if self.section_mode == "support_change":
            self._section_pts, self._section_indices = self._detect_support_change()
        elif self.section_mode == "heel_strike":
            self._section_pts, self._section_indices = self._detect_heel_strike()
        elif self.section_mode == "custom":
            if self.custom_detector is None:
                raise ValueError("custom_detector must be provided when section_mode='custom'")
            self._section_pts, self._section_indices = self._detect_custom()
        else:
            raise ValueError(f"Unknown section_mode: {self.section_mode}")

        return self._section_pts

    def _detect_support_change(self) -> tuple[np.ndarray, list[int]]:
        """检测支撑足切换时刻。"""
        pts: list[list[float]] = []
        indices: list[int] = []

        last_support = self.rows[0].get("support_foot", "")
        for i, r in enumerate(self.rows[1:], start=1):
            cur = r.get("support_foot", "")
            if cur != last_support and cur in {"left", "right"}:
                pts.append([float(r[k]) for k in self.state_keys])
                indices.append(i)
                last_support = cur

        arr = np.array(pts) if pts else np.empty((0, len(self.state_keys)))
        return arr, indices

    def _detect_heel_strike(self) -> tuple[np.ndarray, list[int]]:
        """检测脚跟触地时刻（mode 切换到 'left' 或 'right'）。"""
        pts: list[list[float]] = []
        indices: list[int] = []

        last_mode = self.rows[0].get("mode", "")
        for i, r in enumerate(self.rows[1:], start=1):
            cur_mode = r.get("mode", "")
            # 检测是否从 'flight' 或其他状态切换到 'left'/'right'
            if cur_mode in {"left", "right"} and cur_mode != last_mode:
                pts.append([float(r[k]) for k in self.state_keys])
                indices.append(i)
            last_mode = cur_mode

        arr = np.array(pts) if pts else np.empty((0, len(self.state_keys)))
        return arr, indices

    def _detect_custom(self) -> tuple[np.ndarray, list[int]]:
        """使用自定义检测器。"""
        pts: list[list[float]] = []
        indices: list[int] = []

        for i in range(1, len(self.rows)):
            if self.custom_detector(self.rows[i-1], self.rows[i]):
                pts.append([float(self.rows[i][k]) for k in self.state_keys])
                indices.append(i)

        arr = np.array(pts) if pts else np.empty((0, len(self.state_keys)))
        return arr, indices

    def compute_floquet(
        self,
        fixed_point: np.ndarray | None = None,
        tail_frac: float = 0.4,
        skip_head: int = 0,
    ) -> dict:
        """计算 Floquet 乘子。

        Args:
            fixed_point: 不动点位置，None 则自动取后段均值
            tail_frac: 用于计算不动点的后段比例
            skip_head: 跳过前若干个暂态点

        Returns:
            包含 jacobian, eigvals, fixed_point, n_pairs 的字典
        """
        pts = self.detect_section()
        self._floquet_result = floquet_multipliers(
            pts, fixed_point=fixed_point, tail_frac=tail_frac, skip_head=skip_head
        )
        return self._floquet_result

    def plot_return_map(
        self,
        ax: Axes | None = None,
        title: str = "",
        show_fixed_point: bool = True,
        show_identity: bool = True,
    ) -> Axes:
        """绘制返回映射图。

        Args:
            ax: matplotlib Axes，None 则创建新图
            title: 图表标题
            show_fixed_point: 是否标注不动点
            show_identity: 是否显示 y=x 参考线

        Returns:
            Axes 对象
        """
        pts = self.detect_section()

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))

        if pts.size == 0:
            ax.text(0.5, 0.5, "No section points detected",
                   ha="center", va="center", transform=ax.transAxes)
            ax.set_xlabel(f"{self.state_keys[0]} [k]")
            ax.set_ylabel(f"{self.state_keys[0]} [k+1]")
            if title:
                ax.set_title(title)
            return ax

        # 绘制返回映射 (x_k, x_{k+1})
        x_k = pts[:-1, 0]
        x_k1 = pts[1:, 0]

        ax.scatter(x_k, x_k1, s=30, alpha=0.7, label="Return map")

        # 参考线 y=x
        if show_identity and len(x_k) > 0:
            x_range = [min(x_k.min(), x_k1.min()), max(x_k.max(), x_k1.max())]
            ax.plot(x_range, x_range, 'k--', lw=1, alpha=0.3, label="y=x")

        # 不动点标注
        if show_fixed_point and self._floquet_result is not None:
            fp = self._floquet_result["fixed_point"]
            if len(fp) > 0 and not np.isnan(fp[0]):
                ax.plot(fp[0], fp[0], 'r*', markersize=12, label="Fixed point")

        ax.set_xlabel(f"{self.state_keys[0]} [k]")
        ax.set_ylabel(f"{self.state_keys[0]} [k+1]")
        if title:
            ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_phase_portrait(
        self,
        ax: Axes | None = None,
        title: str = "",
        show_trajectory: bool = True,
    ) -> Axes:
        """绘制相平面轨迹（Poincaré 截面点）。

        Args:
            ax: matplotlib Axes，None 则创建新图
            title: 图表标题
            show_trajectory: 是否连线显示轨迹

        Returns:
            Axes 对象
        """
        pts = self.detect_section()

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))

        if len(self.state_keys) < 2:
            ax.text(0.5, 0.5, "Need at least 2 state variables",
                   ha="center", va="center", transform=ax.transAxes)
            return ax

        plot_section(
            ax, pts,
            x_label=self.state_keys[0],
            y_label=self.state_keys[1],
            title=title,
        )

        return ax

    def stability_report(self) -> str:
        """生成稳定性分析报告。

        Returns:
            包含 Floquet 乘子和稳定性判据的文本报告
        """
        if self._floquet_result is None:
            self.compute_floquet()

        result = self._floquet_result
        if result["n_pairs"] < 1:
            return "Insufficient section points for stability analysis."

        eigvals = result["eigvals"]
        jacobian = result["jacobian"]
        fp = result["fixed_point"]

        lines = []
        lines.append("=== Poincaré Stability Analysis ===")
        lines.append(f"Section points: {result['n_pairs'] + 1}")
        lines.append(f"Fixed point: {fp}")
        lines.append(f"\nJacobian (return map):")
        lines.append(str(jacobian))
        lines.append(f"\nFloquet multipliers (eigenvalues):")

        max_mag = 0.0
        for i, lam in enumerate(eigvals):
            mag = abs(lam)
            max_mag = max(max_mag, mag)
            lines.append(f"  λ_{i+1} = {lam:.6f}  |λ| = {mag:.6f}")

        lines.append(f"\nMaximum magnitude: {max_mag:.6f}")

        # 稳定性判据
        if max_mag < 1.0:
            stability = "STABLE (all |λ| < 1)"
        elif max_mag > 1.0:
            stability = "UNSTABLE (exists |λ| > 1)"
        else:
            stability = "MARGINALLY STABLE (|λ| ≈ 1)"

        lines.append(f"Stability: {stability}")

        return "\n".join(lines)

    def create_full_analysis_figure(self, figsize=(14, 10)) -> Figure:
        """创建包含完整分析的多子图。

        Returns:
            包含返回映射、相平面、稳定性信息的 Figure 对象
        """
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 左上：相平面轨迹
        ax1 = fig.add_subplot(gs[0, 0])
        self.plot_phase_portrait(ax1, title="Phase Portrait (Poincaré Section)")

        # 右上：返回映射
        ax2 = fig.add_subplot(gs[0, 1])
        self.plot_return_map(ax2, title="Return Map")

        # 下半部分：稳定性报告
        ax3 = fig.add_subplot(gs[1, :])
        ax3.axis('off')

        report = self.stability_report()
        ax3.text(0.05, 0.95, report,
                transform=ax3.transAxes,
                fontfamily='monospace',
                fontsize=9,
                verticalalignment='top')

        return fig

    @property
    def section_points(self) -> np.ndarray:
        """获取截面点数据。"""
        return self.detect_section()

    @property
    def section_indices(self) -> list[int]:
        """获取截面点在原始轨迹中的索引。"""
        if self._section_indices is None:
            self.detect_section()
        return self._section_indices or []

    @property
    def n_sections(self) -> int:
        """截面点数量。"""
        return len(self.detect_section())

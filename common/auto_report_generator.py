"""AutoReportGenerator - 自动生成 PDF 报告，包含所有证据、分析结果和格式化表格

此模块为 Limit Cycle Toolkit 提供完整的报告生成功能，支持：
- 自动收集所有分析结果和可视化图表
- 格式化表格（Floquet 乘子、能量指标、步态参数等）
- 多页 PDF 布局，包含目录、摘要、详细分析
- 支持中英文双语输出
- 可自定义报告模板和样式

依赖：matplotlib (PdfPages), numpy
不依赖外部 PDF 库（reportlab/fpdf），使用 matplotlib 内置 PDF 后端
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec


class AutoReportGenerator:
    """自动报告生成器 - 将分析结果、图表、表格整合为 PDF 报告"""

    def __init__(
        self,
        title: str = "Limit Cycle Gait Analysis Report",
        author: str = "",
        language: str = "en",
        include_watermark: bool = False,
        dpi: int = 150,
    ):
        """初始化报告生成器

        Args:
            title: 报告标题
            author: 作者名称
            language: 语言代码 ('en' 或 'zh')
            include_watermark: 是否添加水印
            dpi: PDF 图像 DPI
        """
        self.title = title
        self.author = author
        self.language = language
        self.include_watermark = include_watermark
        self.dpi = dpi

        # 内容收集
        self.sections: list[dict[str, Any]] = []
        self.figures: list[tuple[str, str | Path]] = []  # (caption, path)
        self.tables: list[tuple[str, list[list[str]]]] = []  # (caption, data)
        self.metadata: dict[str, Any] = {}

        # 本地化文本
        self._setup_i18n()

    def _setup_i18n(self):
        """设置国际化文本"""
        if self.language == "zh":
            self.i18n = {
                "toc": "目录",
                "summary": "摘要",
                "analysis": "分析结果",
                "figures": "图表",
                "tables": "数据表",
                "page": "第 {} 页",
                "generated": "生成时间",
                "floquet": "Floquet 乘子",
                "energy": "能量分析",
                "gait_params": "步态参数",
                "stability": "稳定性",
                "convergence": "收敛性",
            }
        else:
            self.i18n = {
                "toc": "Table of Contents",
                "summary": "Summary",
                "analysis": "Analysis Results",
                "figures": "Figures",
                "tables": "Data Tables",
                "page": "Page {}",
                "generated": "Generated",
                "floquet": "Floquet Multipliers",
                "energy": "Energy Analysis",
                "gait_params": "Gait Parameters",
                "stability": "Stability",
                "convergence": "Convergence",
            }

    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value

    def add_section(
        self,
        section_title: str,
        content: str | dict | None = None,
        level: int = 1,
    ) -> None:
        """添加章节

        Args:
            section_title: 章节标题
            content: 文本内容或结构化数据字典
            level: 标题级别 (1-3)
        """
        self.sections.append(
            {
                "title": section_title,
                "content": content,
                "level": level,
            }
        )

    def add_figure(self, caption: str, figure_path: str | Path) -> None:
        """添加图表引用

        Args:
            caption: 图表说明
            figure_path: 图表文件路径
        """
        self.figures.append((caption, Path(figure_path)))

    def add_table(
        self,
        caption: str,
        data: list[list[str]] | np.ndarray,
        headers: list[str] | None = None,
    ) -> None:
        """添加数据表

        Args:
            caption: 表格说明
            data: 表格数据（二维列表或数组）
            headers: 列标题（可选）
        """
        if isinstance(data, np.ndarray):
            data = data.tolist()

        if headers:
            table_data = [headers] + data
        else:
            table_data = data

        self.tables.append((caption, table_data))

    def add_floquet_analysis(
        self,
        floquet_result: dict,
        section_title: str | None = None,
    ) -> None:
        """添加 Floquet 分析结果

        Args:
            floquet_result: poincare.floquet_multipliers() 返回的字典
            section_title: 自定义章节标题
        """
        title = section_title or self.i18n["floquet"]

        eigvals = floquet_result.get("eigvals", np.array([]))
        n_pairs = floquet_result.get("n_pairs", 0)
        fixed_point = floquet_result.get("fixed_point", np.array([]))

        # 格式化表格数据
        table_data = [["Index", "Real", "Imaginary", "Magnitude"]]
        for i, ev in enumerate(eigvals):
            table_data.append(
                [
                    str(i + 1),
                    f"{ev.real:.6f}",
                    f"{ev.imag:.6f}",
                    f"{abs(ev):.6f}",
                ]
            )

        # 稳定性判断
        max_mag = max(abs(ev) for ev in eigvals) if len(eigvals) > 0 else 0.0
        stability = "Stable" if max_mag < 1.0 else "Unstable"

        content = {
            "n_pairs": n_pairs,
            "stability": stability,
            "max_magnitude": max_mag,
            "fixed_point": fixed_point.tolist() if len(fixed_point) > 0 else [],
        }

        self.add_section(title, content, level=2)
        self.add_table(f"{title} - Eigenvalues", table_data)

    def add_energy_analysis(
        self,
        energy_series: dict,
        cot: float | None = None,
        collision_losses: list[dict] | None = None,
        section_title: str | None = None,
    ) -> None:
        """添加能量分析结果

        Args:
            energy_series: energy_metrics.mechanical_energy_series() 返回的字典
            cot: 无量纲 CoT 值
            collision_losses: collision_loss_per_step() 返回的列表
            section_title: 自定义章节标题
        """
        title = section_title or self.i18n["energy"]

        time = energy_series.get("time", np.array([]))
        ke = energy_series.get("ke", np.array([]))
        pe = energy_series.get("pe", np.array([]))
        total = energy_series.get("total", np.array([]))

        content = {
            "duration_s": float(time[-1] - time[0]) if len(time) > 1 else 0.0,
            "avg_ke_J": float(np.mean(ke)) if len(ke) > 0 else 0.0,
            "avg_pe_J": float(np.mean(pe)) if len(pe) > 0 else 0.0,
            "total_range_J": (
                float(np.max(total) - np.min(total)) if len(total) > 0 else 0.0
            ),
        }

        if cot is not None:
            content["cost_of_transport"] = cot

        if collision_losses:
            avg_loss = np.mean([c["dE_J"] for c in collision_losses])
            content["avg_collision_loss_J"] = float(avg_loss)
            content["n_steps"] = len(collision_losses)

        self.add_section(title, content, level=2)

        # 添加碰撞损耗表
        if collision_losses:
            table_data = [["Step", "Time (s)", "From→To", "Loss (J)"]]
            for loss in collision_losses:
                table_data.append(
                    [
                        str(loss.get("step", "")),
                        f"{loss.get('time', 0.0):.3f}",
                        f"{loss.get('support_from', '')}→{loss.get('support_to', '')}",
                        f"{loss.get('dE_J', 0.0):.4f}",
                    ]
                )
            self.add_table(f"{title} - Collision Losses", table_data)

    def add_gait_metrics(
        self,
        metrics: dict[str, float],
        section_title: str | None = None,
    ) -> None:
        """添加步态指标

        Args:
            metrics: 指标字典（如步长、步频、速度等）
            section_title: 自定义章节标题
        """
        title = section_title or self.i18n["gait_params"]

        table_data = [["Metric", "Value", "Unit"]]

        # 常见指标及其单位
        units = {
            "stride_length": "m",
            "step_length": "m",
            "cadence": "steps/min",
            "velocity": "m/s",
            "step_width": "m",
            "step_time": "s",
            "stance_time": "s",
            "swing_time": "s",
            "double_support_time": "s",
        }

        for key, value in metrics.items():
            unit = units.get(key, "")
            formatted_key = key.replace("_", " ").title()
            table_data.append([formatted_key, f"{value:.4f}", unit])

        self.add_section(title, None, level=2)
        self.add_table(title, table_data)

    def generate(self, output_path: str | Path) -> Path:
        """生成 PDF 报告

        Args:
            output_path: 输出文件路径

        Returns:
            生成的 PDF 文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with PdfPages(output_path) as pdf:
            # 第 1 页：封面
            self._create_cover_page(pdf)

            # 第 2 页：目录
            if len(self.sections) > 0:
                self._create_toc_page(pdf)

            # 主体内容页
            self._create_content_pages(pdf)

            # 图表页
            if len(self.figures) > 0:
                self._create_figure_pages(pdf)

            # 表格页
            if len(self.tables) > 0:
                self._create_table_pages(pdf)

            # 设置 PDF 元数据
            d = pdf.infodict()
            d["Title"] = self.title
            d["Author"] = self.author
            d["Subject"] = "Limit Cycle Gait Analysis"
            d["Keywords"] = "Gait, Limit Cycle, Floquet, Energy"
            d["Creator"] = "AutoReportGenerator"

        return output_path

    def _create_cover_page(self, pdf: PdfPages) -> None:
        """创建封面页"""
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_subplot(111)
        ax.axis("off")

        # 标题
        ax.text(
            0.5,
            0.7,
            self.title,
            ha="center",
            va="center",
            fontsize=24,
            fontweight="bold",
            transform=ax.transAxes,
        )

        # 作者
        if self.author:
            ax.text(
                0.5,
                0.6,
                self.author,
                ha="center",
                va="center",
                fontsize=16,
                transform=ax.transAxes,
            )

        # 日期
        from datetime import datetime

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        ax.text(
            0.5,
            0.3,
            f"{self.i18n['generated']}: {date_str}",
            ha="center",
            va="center",
            fontsize=12,
            style="italic",
            transform=ax.transAxes,
        )

        # 水印
        if self.include_watermark:
            ax.text(
                0.5,
                0.1,
                "Generated by AutoReportGenerator",
                ha="center",
                va="center",
                fontsize=10,
                alpha=0.5,
                transform=ax.transAxes,
            )

        pdf.savefig(fig, dpi=self.dpi)
        plt.close(fig)

    def _create_toc_page(self, pdf: PdfPages) -> None:
        """创建目录页"""
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_subplot(111)
        ax.axis("off")

        # 标题
        ax.text(
            0.5,
            0.95,
            self.i18n["toc"],
            ha="center",
            va="top",
            fontsize=20,
            fontweight="bold",
            transform=ax.transAxes,
        )

        # 目录条目
        y_pos = 0.88
        for i, section in enumerate(self.sections):
            indent = "  " * (section["level"] - 1)
            toc_text = f"{indent}{i + 1}. {section['title']}"
            ax.text(
                0.1,
                y_pos,
                toc_text,
                ha="left",
                va="top",
                fontsize=12 if section["level"] == 1 else 10,
                transform=ax.transAxes,
            )
            y_pos -= 0.04

            if y_pos < 0.1:
                break

        pdf.savefig(fig, dpi=self.dpi)
        plt.close(fig)

    def _create_content_pages(self, pdf: PdfPages) -> None:
        """创建内容页"""
        for section in self.sections:
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis("off")

            y_pos = 0.95

            # 章节标题
            fontsize = (
                18 if section["level"] == 1 else (14 if section["level"] == 2 else 12)
            )
            ax.text(
                0.1,
                y_pos,
                section["title"],
                ha="left",
                va="top",
                fontsize=fontsize,
                fontweight="bold",
                transform=ax.transAxes,
            )
            y_pos -= 0.08

            # 内容
            content = section.get("content")
            if content:
                if isinstance(content, str):
                    # 文本内容
                    ax.text(
                        0.1,
                        y_pos,
                        content,
                        ha="left",
                        va="top",
                        fontsize=11,
                        wrap=True,
                        transform=ax.transAxes,
                    )
                elif isinstance(content, dict):
                    # 结构化数据
                    for key, value in content.items():
                        formatted_key = key.replace("_", " ").title()
                        if isinstance(value, (list, np.ndarray)):
                            value_str = str(value)
                        elif isinstance(value, float):
                            value_str = f"{value:.6f}"
                        else:
                            value_str = str(value)

                        ax.text(
                            0.15,
                            y_pos,
                            f"{formatted_key}: {value_str}",
                            ha="left",
                            va="top",
                            fontsize=10,
                            family="monospace",
                            transform=ax.transAxes,
                        )
                        y_pos -= 0.04

                        if y_pos < 0.1:
                            break

            pdf.savefig(fig, dpi=self.dpi)
            plt.close(fig)

    def _create_figure_pages(self, pdf: PdfPages) -> None:
        """创建图表页"""
        for caption, fig_path in self.figures:
            if not fig_path.exists():
                warnings.warn(f"Figure not found: {fig_path}")
                continue

            fig = plt.figure(figsize=(8.5, 11))
            gs = GridSpec(2, 1, height_ratios=[1, 9], hspace=0.05)

            # 标题栏
            ax_title = fig.add_subplot(gs[0])
            ax_title.axis("off")
            ax_title.text(
                0.5,
                0.5,
                caption,
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                transform=ax_title.transAxes,
            )

            # 图像
            ax_img = fig.add_subplot(gs[1])
            ax_img.axis("off")

            try:
                img = plt.imread(fig_path)
                ax_img.imshow(img, aspect="auto")
            except Exception as e:
                ax_img.text(
                    0.5,
                    0.5,
                    f"Error loading image:\n{e}",
                    ha="center",
                    va="center",
                    transform=ax_img.transAxes,
                )

            pdf.savefig(fig, dpi=self.dpi)
            plt.close(fig)

    def _create_table_pages(self, pdf: PdfPages) -> None:
        """创建表格页"""
        for caption, table_data in self.tables:
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis("off")

            # 标题
            ax.text(
                0.5,
                0.95,
                caption,
                ha="center",
                va="top",
                fontsize=14,
                fontweight="bold",
                transform=ax.transAxes,
            )

            # 表格
            if len(table_data) > 0:
                n_rows = len(table_data)
                n_cols = len(table_data[0]) if n_rows > 0 else 0

                # 计算表格位置
                table_height = min(0.8, 0.05 * n_rows)
                table_top = 0.85

                # 绘制表格
                col_widths = [1.0 / n_cols] * n_cols if n_cols > 0 else []

                table = ax.table(
                    cellText=table_data,
                    cellLoc="center",
                    loc="upper center",
                    bbox=[0.1, table_top - table_height, 0.8, table_height],
                    colWidths=col_widths,
                )

                table.auto_set_font_size(False)
                table.set_fontsize(9)
                table.scale(1, 1.5)

                # 表头样式
                for i in range(n_cols):
                    cell = table[(0, i)]
                    cell.set_facecolor("#4472C4")
                    cell.set_text_props(weight="bold", color="white")

                # 交替行颜色
                for i in range(1, n_rows):
                    for j in range(n_cols):
                        cell = table[(i, j)]
                        if i % 2 == 0:
                            cell.set_facecolor("#F0F0F0")

            pdf.savefig(fig, dpi=self.dpi)
            plt.close(fig)

    def generate_quick_report(
        self,
        output_path: str | Path,
        floquet_result: dict | None = None,
        energy_series: dict | None = None,
        gait_metrics: dict | None = None,
        figures: list[tuple[str, str | Path]] | None = None,
    ) -> Path:
        """快速生成报告（便捷方法）

        Args:
            output_path: 输出文件路径
            floquet_result: Floquet 分析结果
            energy_series: 能量序列数据
            gait_metrics: 步态指标
            figures: 图表列表 [(caption, path), ...]

        Returns:
            生成的 PDF 文件路径
        """
        self.add_section(self.i18n["summary"], level=1)

        if floquet_result:
            self.add_floquet_analysis(floquet_result)

        if energy_series:
            self.add_energy_analysis(energy_series)

        if gait_metrics:
            self.add_gait_metrics(gait_metrics)

        if figures:
            for caption, path in figures:
                self.add_figure(caption, path)

        return self.generate(output_path)


# 便捷函数
def generate_report(
    output_path: str | Path,
    title: str = "Gait Analysis Report",
    floquet_result: dict | None = None,
    energy_series: dict | None = None,
    gait_metrics: dict | None = None,
    figures: list[tuple[str, str | Path]] | None = None,
    language: str = "en",
    **kwargs,
) -> Path:
    """一键生成报告（便捷函数）

    Args:
        output_path: 输出文件路径
        title: 报告标题
        floquet_result: Floquet 分析结果
        energy_series: 能量序列数据
        gait_metrics: 步态指标
        figures: 图表列表
        language: 语言 ('en' 或 'zh')
        **kwargs: 传递给 AutoReportGenerator 的其他参数

    Returns:
        生成的 PDF 文件路径
    """
    generator = AutoReportGenerator(title=title, language=language, **kwargs)
    return generator.generate_quick_report(
        output_path=output_path,
        floquet_result=floquet_result,
        energy_series=energy_series,
        gait_metrics=gait_metrics,
        figures=figures,
    )

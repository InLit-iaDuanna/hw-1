"""
报告生成模块
生成 Markdown、HTML、LaTeX 格式的分析报告
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from data_loader import GaitData
from feature_extractor import GaitFeatures
from statistical_analyzer import ComparisonResult


class ReportGenerator:
    """报告生成器"""

    def __init__(self, config: dict, output_dir: str | Path):
        """
        初始化报告生成器

        Args:
            config: report 配置字典
            output_dir: 输出目录
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.output_formats = config.get("output_formats", ["markdown"])
        self.sections = config.get("sections", [])
        self.embed_figures = config.get("embed_figures", True)

    def generate_markdown_header(self, title: str, level: int = 1) -> str:
        """生成 Markdown 标题"""
        return f"{'#' * level} {title}\n\n"

    def generate_markdown_table(self, headers: list[str], rows: list[list[Any]]) -> str:
        """生成 Markdown 表格"""
        md = "| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        for row in rows:
            md += "| " + " | ".join(str(cell) for cell in row) + " |\n"

        return md + "\n"

    def generate_latex_table(
        self, headers: list[str], rows: list[list[Any]], caption: str = ""
    ) -> str:
        """生成 LaTeX 表格"""
        n_cols = len(headers)
        latex = "\\begin{table}[htbp]\n"
        latex += "\\centering\n"
        latex += f"\\begin{{tabular}}{{{'|'.join(['c'] * n_cols)}}}\n"
        latex += "\\hline\n"
        latex += " & ".join(headers) + " \\\\\n"
        latex += "\\hline\n"

        for row in rows:
            latex += " & ".join(str(cell) for cell in row) + " \\\\\n"

        latex += "\\hline\n"
        latex += "\\end{tabular}\n"

        if caption:
            latex += f"\\caption{{{caption}}}\n"

        latex += "\\end{table}\n\n"

        return latex

    def generate_data_summary(self, data_dict: dict[str, GaitData]) -> str:
        """生成数据概览部分"""
        md = self.generate_markdown_header("数据概览", 2)

        md += f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += f"**数据版本数**: {len(data_dict)}\n\n"

        # 数据表格
        headers = ["版本", "标签", "时长 (s)", "采样数", "采样率 (Hz)"]
        rows = []

        for version_key, gait_data in data_dict.items():
            rows.append(
                [
                    gait_data.version,
                    gait_data.label,
                    f"{gait_data.duration:.2f}",
                    gait_data.num_samples,
                    f"{gait_data.sampling_rate:.1f}",
                ]
            )

        md += self.generate_markdown_table(headers, rows)

        return md

    def generate_features_summary(self, features_dict: dict[str, GaitFeatures]) -> str:
        """生成特征汇总表"""
        md = self.generate_markdown_header("特征汇总", 2)

        # 选择关键特征
        key_metrics = [
            ("period_length", "步态周期 (s)"),
            ("stride_length", "步长 (m)"),
            ("stride_frequency", "步频 (Hz)"),
            ("cost_of_transport", "CoT"),
            ("duty_factor", "接触比例"),
            ("left_right_symmetry", "左右对称性"),
            ("convergence_rate", "收敛率"),
            ("power_mean", "平均功率 (W)"),
        ]

        headers = ["指标"] + [f.label for f in features_dict.values()]
        rows = []

        for metric, metric_label in key_metrics:
            row = [metric_label]
            for features in features_dict.values():
                value = getattr(features, metric, None)
                if value is not None and not np.isnan(value):
                    row.append(f"{value:.4f}")
                else:
                    row.append("N/A")
            rows.append(row)

        md += self.generate_markdown_table(headers, rows)

        return md

    def generate_comparison_section(self, comparisons: list[ComparisonResult]) -> str:
        """生成版本对比部分"""
        md = self.generate_markdown_header("版本对比", 2)

        if not comparisons:
            md += "*无对比数据*\n\n"
            return md

        # 按指标分组
        comp_by_metric: dict[str, list[ComparisonResult]] = {}
        for comp in comparisons:
            if comp.metric not in comp_by_metric:
                comp_by_metric[comp.metric] = []
            comp_by_metric[comp.metric].append(comp)

        # 生成对比表格
        headers = ["指标", "版本1", "值1", "版本2", "值2", "差异", "变化率 (%)"]
        rows = []

        for metric, comps in comp_by_metric.items():
            for comp in comps[:1]:  # 每个指标只显示一次
                rows.append(
                    [
                        metric.replace("_", " ").title(),
                        comp.version1,
                        f"{comp.value1:.4f}",
                        comp.version2,
                        f"{comp.value2:.4f}",
                        f"{comp.difference:+.4f}",
                        f"{comp.percent_change:+.2f}",
                    ]
                )

        md += self.generate_markdown_table(headers, rows)

        return md

    def generate_sensitivity_section(
        self, sensitivity_results: dict[str, dict[str, Any]]
    ) -> str:
        """生成敏感性分析部分"""
        md = self.generate_markdown_header("参数敏感性", 2)

        if not sensitivity_results:
            md += "*无敏感性数据*\n\n"
            return md

        headers = ["指标", "均值", "标准差", "范围", "变异系数"]
        rows = []

        for metric, stats in sensitivity_results.items():
            rows.append(
                [
                    metric.replace("_", " ").title(),
                    f"{stats['mean']:.4f}",
                    f"{stats['std']:.4f}",
                    f"[{stats['min']:.4f}, {stats['max']:.4f}]",
                    f"{stats['cv']:.2%}",
                ]
            )

        md += self.generate_markdown_table(headers, rows)

        return md

    def embed_figure(self, figure_path: Path, caption: str = "") -> str:
        """嵌入图片到 Markdown"""
        if self.embed_figures and figure_path.exists():
            rel_path = figure_path.name  # 使用相对路径
            md = f"![{caption}]({rel_path})\n\n"
            if caption:
                md += f"*{caption}*\n\n"
            return md
        return ""

    def generate_markdown_report(
        self,
        data_dict: dict[str, GaitData],
        features_dict: dict[str, GaitFeatures],
        comparisons: list[ComparisonResult] | None = None,
        sensitivity: dict[str, dict[str, Any]] | None = None,
        figure_paths: dict[str, Path] | None = None,
    ) -> str:
        """
        生成完整 Markdown 报告

        Args:
            data_dict: 数据字典
            features_dict: 特征字典
            comparisons: 对比结果
            sensitivity: 敏感性分析结果
            figure_paths: 图表路径字典

        Returns:
            Markdown 文本
        """
        md = self.generate_markdown_header("步态分析报告", 1)

        # 数据概览
        md += self.generate_data_summary(data_dict)

        # 特征汇总
        md += self.generate_features_summary(features_dict)

        # 步态周期分析
        md += self.generate_markdown_header("步态周期分析", 2)
        if figure_paths and "gait_cycle" in figure_paths:
            md += self.embed_figure(figure_paths["gait_cycle"], "步态周期时间序列")

        # 能量效率
        md += self.generate_markdown_header("能量效率分析", 2)
        md += "### Cost of Transport (CoT)\n\n"

        cot_data = []
        for version_key, features in features_dict.items():
            if features.cost_of_transport is not None:
                cot_data.append((features.label, features.cost_of_transport))

        if cot_data:
            headers = ["版本", "CoT"]
            rows = [[label, f"{cot:.4f}"] for label, cot in cot_data]
            md += self.generate_markdown_table(headers, rows)

        if figure_paths and "energy_comparison" in figure_paths:
            md += self.embed_figure(figure_paths["energy_comparison"], "能量对比")

        # 版本对比
        if comparisons:
            md += self.generate_comparison_section(comparisons)

        # 敏感性分析
        if sensitivity:
            md += self.generate_sensitivity_section(sensitivity)

        if figure_paths and "correlation_heatmap" in figure_paths:
            md += self.embed_figure(
                figure_paths["correlation_heatmap"], "特征相关性热图"
            )

        # 结论
        md += self.generate_markdown_header("结论", 2)
        md += self.generate_conclusions(features_dict)

        return md

    def generate_conclusions(self, features_dict: dict[str, GaitFeatures]) -> str:
        """生成自动结论"""
        md = ""

        # 找到最优版本（基于 CoT）
        best_cot = None
        best_version = None

        for version_key, features in features_dict.items():
            if features.cost_of_transport is not None:
                if best_cot is None or features.cost_of_transport < best_cot:
                    best_cot = features.cost_of_transport
                    best_version = features.label

        if best_version:
            md += f"- **能量效率最优版本**: {best_version} (CoT = {best_cot:.4f})\n"

        # 稳定性分析
        most_stable = None
        best_convergence = None

        for version_key, features in features_dict.items():
            if features.convergence_rate is not None:
                if (
                    best_convergence is None
                    or features.convergence_rate > best_convergence
                ):
                    best_convergence = features.convergence_rate
                    most_stable = features.label

        if most_stable:
            md += f"- **稳定性最优版本**: {most_stable} (收敛率 = {best_convergence:.4f})\n"

        # 对称性分析
        most_symmetric = None
        best_symmetry = None

        for version_key, features in features_dict.items():
            if features.left_right_symmetry is not None:
                if (
                    best_symmetry is None
                    or features.left_right_symmetry > best_symmetry
                ):
                    best_symmetry = features.left_right_symmetry
                    most_symmetric = features.label

        if most_symmetric:
            md += f"- **对称性最优版本**: {most_symmetric} (对称性 = {best_symmetry:.3f})\n"

        md += "\n"

        return md

    def save_report(
        self,
        content: str,
        filename: str,
        format: str = "markdown",
    ):
        """
        保存报告

        Args:
            content: 报告内容
            filename: 文件名（不含扩展名）
            format: 格式 (markdown, html, latex)
        """
        if format == "markdown":
            filepath = self.output_dir / f"{filename}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Saved Markdown report: {filepath}")

        elif format == "html":
            # 简单的 Markdown 到 HTML 转换
            html_content = self.markdown_to_html(content)
            filepath = self.output_dir / f"{filename}.html"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  Saved HTML report: {filepath}")

        elif format == "latex":
            filepath = self.output_dir / f"{filename}.tex"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Saved LaTeX report: {filepath}")

    def markdown_to_html(self, markdown: str) -> str:
        """简单的 Markdown 到 HTML 转换"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>步态分析报告</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        img { max-width: 100%; height: auto; }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; }
        h2 { color: #666; border-bottom: 1px solid #ddd; }
    </style>
</head>
<body>
"""

        # 简单替换（实际应用中应使用专业的 Markdown 解析器）
        lines = markdown.split("\n")
        for line in lines:
            if line.startswith("# "):
                html += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith("## "):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith("### "):
                html += f"<h3>{line[4:]}</h3>\n"
            elif line.startswith("| "):
                # 表格行（简化处理）
                html += (
                    "<tr><td>" + line[2:-2].replace(" | ", "</td><td>") + "</td></tr>\n"
                )
            elif line.startswith("!["):
                # 图片（简化处理）
                html += f"<img src='{line}' />\n"
            else:
                html += f"<p>{line}</p>\n"

        html += """
</body>
</html>
"""
        return html


def main():
    """测试报告生成"""
    from pathlib import Path
    import yaml
    from data_loader import DataLoader
    from preprocessor import DataPreprocessor
    from feature_extractor import FeatureExtractor

    config_path = Path(__file__).parent / "pipeline_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    loader = DataLoader(config_path)
    preprocessor = DataPreprocessor(config["preprocessing"])
    extractor = FeatureExtractor(config["feature_extraction"])

    output_dir = Path(__file__).parent / "test_reports"
    generator = ReportGenerator(config["report"], output_dir)

    print("=" * 60)
    print("Report Generator Test")
    print("=" * 60)

    # 加载数据
    data_dict = {}
    features_dict = {}

    for version_key in ["v09_stable", "v10_rolling"]:
        try:
            gait_data = loader.load_version(version_key)
            processed = preprocessor.preprocess_gait_data(gait_data)
            features = extractor.extract_all_features(processed)

            data_dict[version_key] = processed
            features_dict[version_key] = features
        except Exception as e:
            print(f"Warning: Failed to process {version_key}: {e}")

    # 生成报告
    print("\nGenerating report...")
    report_md = generator.generate_markdown_report(data_dict, features_dict)

    generator.save_report(report_md, "analysis_report", "markdown")

    print(f"\nReport saved to {output_dir}")


if __name__ == "__main__":
    main()

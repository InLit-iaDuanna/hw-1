"""
主管道运行脚本
完整的数据分析流程：加载 -> 预处理 -> 特征提取 -> 统计分析 -> 可视化 -> 报告生成
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from data_loader import DataLoader
from feature_extractor import FeatureExtractor
from preprocessor import DataPreprocessor
from report_generator import ReportGenerator
from statistical_analyzer import StatisticalAnalyzer
from visualizer import Visualizer


class AnalysisPipeline:
    """分析管道"""

    def __init__(self, config_path: str | Path):
        """
        初始化分析管道

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        with open(self.config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # 初始化各个模块
        self.loader = DataLoader(self.config_path)
        self.preprocessor = DataPreprocessor(self.config["preprocessing"])
        self.extractor = FeatureExtractor(self.config["feature_extraction"])
        self.analyzer = StatisticalAnalyzer(self.config["statistical_analysis"])
        self.visualizer = Visualizer(self.config["visualization"])

        # 输出目录
        report_config = self.config.get("report", {})
        self.output_dir = Path(report_config.get("output_directory", "./reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.figures_dir = self.output_dir / "figures"
        self.figures_dir.mkdir(exist_ok=True)

        self.generator = ReportGenerator(report_config, self.output_dir)

        # 缓存
        self.cache_enabled = self.config.get("execution", {}).get(
            "cache_intermediate", True
        )
        self.cache_dir = Path(
            self.config.get("execution", {}).get("cache_directory", "./.cache")
        )
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def run_full_pipeline(self, version_keys: list[str] | None = None) -> dict:
        """
        运行完整管道

        Args:
            version_keys: 要分析的版本列表，None 表示所有版本

        Returns:
            结果字典
        """
        print("=" * 80)
        print("Running Analysis Pipeline")
        print("=" * 80)

        # 1. 加载数据
        print("\n[1/6] Loading data...")
        if version_keys is None:
            data_dict = self.loader.load_all()
        else:
            data_dict = self.loader.load_batch(version_keys)

        if not data_dict:
            print("Error: No data loaded!")
            return {}

        print(f"Loaded {len(data_dict)} versions")

        # 2. 预处理
        print("\n[2/6] Preprocessing...")
        processed_dict = {}
        for version_key, gait_data in data_dict.items():
            try:
                processed = self.preprocessor.preprocess_gait_data(gait_data)
                processed_dict[version_key] = processed
            except Exception as e:
                print(f"Warning: Failed to preprocess {version_key}: {e}")
                continue

        # 3. 特征提取
        print("\n[3/6] Extracting features...")
        features_dict = {}
        for version_key, gait_data in processed_dict.items():
            try:
                features = self.extractor.extract_all_features(gait_data)
                features_dict[version_key] = features
            except Exception as e:
                print(f"Warning: Failed to extract features from {version_key}: {e}")
                continue

        # 4. 统计分析
        print("\n[4/6] Statistical analysis...")
        comparisons = []
        comparison_groups = self.config.get("statistical_analysis", {}).get(
            "comparison_groups", []
        )

        for group in comparison_groups:
            if len(group) >= 2:
                v1_key, v2_key = group[0], group[1]
                if v1_key in features_dict and v2_key in features_dict:
                    print(f"  Comparing {v1_key} vs {v2_key}")
                    comps = self.analyzer.compare_features(
                        features_dict[v1_key],
                        features_dict[v2_key],
                    )
                    comparisons.extend(comps)

        # 敏感性分析
        print("  Sensitivity analysis...")
        sensitivity = self.analyzer.sensitivity_analysis(features_dict)

        # 5. 可视化
        print("\n[5/6] Generating visualizations...")
        figure_paths = {}

        # 步态周期图（每个版本）
        for version_key, gait_data in processed_dict.items():
            try:
                fig_path = self.figures_dir / f"{version_key}_gait_cycle.png"
                self.visualizer.plot_gait_cycle(gait_data, fig_path)
                figure_paths[f"{version_key}_gait_cycle"] = fig_path
            except Exception as e:
                print(f"  Warning: Failed to plot gait cycle for {version_key}: {e}")

        # 相位图
        for version_key, gait_data in processed_dict.items():
            try:
                fig_path = self.figures_dir / f"{version_key}_phase.png"
                self.visualizer.plot_phase_diagram(
                    gait_data, "left_hip", "left_hip_vel", fig_path
                )
                figure_paths[f"{version_key}_phase"] = fig_path
            except Exception as e:
                print(f"  Warning: Failed to plot phase diagram for {version_key}: {e}")

        # 特征对比柱状图
        try:
            key_metrics = [
                "period_length",
                "stride_length",
                "cost_of_transport",
                "duty_factor",
                "left_right_symmetry",
                "convergence_rate",
            ]
            fig_path = self.figures_dir / "feature_comparison.png"
            self.visualizer.plot_comparison_bars(features_dict, key_metrics, fig_path)
            figure_paths["feature_comparison"] = fig_path
        except Exception as e:
            print(f"  Warning: Failed to plot feature comparison: {e}")

        # 相关性热图
        try:
            fig_path = self.figures_dir / "correlation_heatmap.png"
            self.visualizer.plot_correlation_heatmap(
                features_dict,
                list(sensitivity.keys())[:15],  # 前15个指标
                fig_path,
            )
            figure_paths["correlation_heatmap"] = fig_path
        except Exception as e:
            print(f"  Warning: Failed to plot correlation heatmap: {e}")

        # 6. 生成报告
        print("\n[6/6] Generating report...")
        report_md = self.generator.generate_markdown_report(
            processed_dict,
            features_dict,
            comparisons,
            sensitivity,
            figure_paths,
        )

        # 保存报告
        output_formats = self.config.get("report", {}).get(
            "output_formats", ["markdown"]
        )
        for fmt in output_formats:
            try:
                self.generator.save_report(report_md, "analysis_report", fmt)
            except Exception as e:
                print(f"  Warning: Failed to save {fmt} report: {e}")

        # 保存 LaTeX 表格
        if self.config.get("report", {}).get("generate_latex_tables", False):
            self.save_latex_tables(features_dict)

        print("\n" + "=" * 80)
        print("Pipeline Complete!")
        print("=" * 80)
        print(f"\nResults saved to: {self.output_dir}")
        print(f"Figures saved to: {self.figures_dir}")

        return {
            "data": processed_dict,
            "features": features_dict,
            "comparisons": comparisons,
            "sensitivity": sensitivity,
            "figures": figure_paths,
        }

    def save_latex_tables(self, features_dict: dict):
        """保存 LaTeX 表格"""
        print("  Generating LaTeX tables...")

        # 特征汇总表
        key_metrics = [
            ("version", "版本"),
            ("period_length", "步态周期 (s)"),
            ("stride_length", "步长 (m)"),
            ("stride_frequency", "步频 (Hz)"),
            ("cost_of_transport", "CoT"),
            ("duty_factor", "接触比例"),
            ("left_right_symmetry", "左右对称性"),
        ]

        headers = [label for _, label in key_metrics]
        rows = []

        for version_key, features in features_dict.items():
            row = []
            for metric, _ in key_metrics:
                if metric == "version":
                    row.append(features.label)
                else:
                    value = getattr(features, metric, None)
                    if value is not None:
                        row.append(f"{value:.4f}")
                    else:
                        row.append("N/A")
            rows.append(row)

        latex_table = self.generator.generate_latex_table(
            headers, rows, "步态特征汇总表"
        )

        latex_path = self.output_dir / "features_table.tex"
        with open(latex_path, "w", encoding="utf-8") as f:
            f.write(latex_table)

        print(f"    Saved LaTeX table: {latex_path}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Run gait analysis pipeline")
    parser.add_argument(
        "--config",
        type=str,
        default="pipeline_config.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--versions",
        type=str,
        nargs="+",
        help="Versions to analyze (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (overrides config)",
    )

    args = parser.parse_args()

    # 配置文件路径
    if Path(args.config).is_absolute():
        config_path = Path(args.config)
    else:
        config_path = Path(__file__).parent / args.config

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return

    # 运行管道
    pipeline = AnalysisPipeline(config_path)

    # 覆盖输出目录
    if args.output:
        pipeline.output_dir = Path(args.output)
        pipeline.output_dir.mkdir(parents=True, exist_ok=True)
        pipeline.figures_dir = pipeline.output_dir / "figures"
        pipeline.figures_dir.mkdir(exist_ok=True)
        pipeline.generator.output_dir = pipeline.output_dir

    # 运行
    results = pipeline.run_full_pipeline(args.versions)


if __name__ == "__main__":
    main()

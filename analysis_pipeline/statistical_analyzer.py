"""
统计分析模块
包括显著性检验、置信区间、敏感性分析等
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats

from feature_extractor import GaitFeatures


@dataclass
class StatisticalTest:
    """统计检验结果"""

    test_name: str
    groups: list[str]
    statistic: float
    p_value: float
    significant: bool
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None


@dataclass
class ComparisonResult:
    """版本对比结果"""

    version1: str
    version2: str
    metric: str
    value1: float
    value2: float
    difference: float
    percent_change: float
    test: StatisticalTest


class StatisticalAnalyzer:
    """统计分析器"""

    def __init__(self, config: dict):
        """
        初始化统计分析器

        Args:
            config: statistical_analysis 配置字典
        """
        self.config = config
        self.confidence_level = config.get("confidence_level", 0.95)
        self.alpha = 1.0 - self.confidence_level

    def t_test_independent(
        self, group1: np.ndarray, group2: np.ndarray, labels: tuple[str, str]
    ) -> StatisticalTest:
        """
        独立样本 t 检验

        Args:
            group1: 第一组数据
            group2: 第二组数据
            labels: 组标签

        Returns:
            StatisticalTest 对象
        """
        statistic, p_value = stats.ttest_ind(group1, group2, nan_policy="omit")

        # Cohen's d 效应量
        mean1 = np.nanmean(group1)
        mean2 = np.nanmean(group2)
        std1 = np.nanstd(group1, ddof=1)
        std2 = np.nanstd(group2, ddof=1)
        pooled_std = np.sqrt(
            ((len(group1) - 1) * std1**2 + (len(group2) - 1) * std2**2)
            / (len(group1) + len(group2) - 2)
        )
        cohens_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0

        # 置信区间
        diff = mean1 - mean2
        se = pooled_std * np.sqrt(1.0 / len(group1) + 1.0 / len(group2))
        df = len(group1) + len(group2) - 2
        t_critical = stats.t.ppf(1 - self.alpha / 2, df)
        ci = (diff - t_critical * se, diff + t_critical * se)

        return StatisticalTest(
            test_name="t-test (independent)",
            groups=list(labels),
            statistic=float(statistic),
            p_value=float(p_value),
            significant=p_value < self.alpha,
            effect_size=float(cohens_d),
            confidence_interval=ci,
        )

    def mann_whitney_test(
        self, group1: np.ndarray, group2: np.ndarray, labels: tuple[str, str]
    ) -> StatisticalTest:
        """
        Mann-Whitney U 检验（非参数）

        Args:
            group1: 第一组数据
            group2: 第二组数据
            labels: 组标签

        Returns:
            StatisticalTest 对象
        """
        # 移除 NaN
        g1 = group1[~np.isnan(group1)]
        g2 = group2[~np.isnan(group2)]

        if len(g1) < 2 or len(g2) < 2:
            return StatisticalTest(
                test_name="Mann-Whitney U",
                groups=list(labels),
                statistic=np.nan,
                p_value=np.nan,
                significant=False,
            )

        statistic, p_value = stats.mannwhitneyu(g1, g2, alternative="two-sided")

        # Rank-biserial correlation 效应量
        n1, n2 = len(g1), len(g2)
        r = 1 - (2 * statistic) / (n1 * n2)

        return StatisticalTest(
            test_name="Mann-Whitney U",
            groups=list(labels),
            statistic=float(statistic),
            p_value=float(p_value),
            significant=p_value < self.alpha,
            effect_size=float(r),
        )

    def anova_oneway(
        self, *groups: np.ndarray, labels: list[str] | None = None
    ) -> StatisticalTest:
        """
        单因素方差分析

        Args:
            *groups: 多组数据
            labels: 组标签

        Returns:
            StatisticalTest 对象
        """
        if labels is None:
            labels = [f"Group{i+1}" for i in range(len(groups))]

        # 移除 NaN
        clean_groups = [g[~np.isnan(g)] for g in groups]

        if any(len(g) < 2 for g in clean_groups):
            return StatisticalTest(
                test_name="One-way ANOVA",
                groups=labels,
                statistic=np.nan,
                p_value=np.nan,
                significant=False,
            )

        statistic, p_value = stats.f_oneway(*clean_groups)

        # Eta-squared 效应量
        grand_mean = np.mean(np.concatenate(clean_groups))
        ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in clean_groups)
        ss_total = sum(np.sum((g - grand_mean) ** 2) for g in clean_groups)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

        return StatisticalTest(
            test_name="One-way ANOVA",
            groups=labels,
            statistic=float(statistic),
            p_value=float(p_value),
            significant=p_value < self.alpha,
            effect_size=float(eta_squared),
        )

    def compare_features(
        self,
        features1: GaitFeatures,
        features2: GaitFeatures,
        metrics: list[str] | None = None,
    ) -> list[ComparisonResult]:
        """
        比较两个版本的特征

        Args:
            features1: 第一个版本的特征
            features2: 第二个版本的特征
            metrics: 要比较的指标列表，None 表示所有

        Returns:
            ComparisonResult 列表
        """
        results = []

        if metrics is None:
            # 获取所有数值型特征
            metrics = [
                k
                for k, v in features1.__dataclass_fields__.items()
                if k not in ["version", "label", "metadata"]
            ]

        for metric in metrics:
            value1 = getattr(features1, metric, None)
            value2 = getattr(features2, metric, None)

            if value1 is None or value2 is None:
                continue

            if not isinstance(value1, (int, float)) or not isinstance(
                value2, (int, float)
            ):
                continue

            # 计算差异
            difference = value2 - value1
            percent_change = 100 * difference / value1 if value1 != 0 else 0.0

            # 注意：单点比较无法进行统计检验，这里创建虚拟分布
            # 实际应用中应该有多次实验数据
            g1 = np.array([value1])
            g2 = np.array([value2])

            # 使用 t-test（虽然样本量不足，但提供框架）
            test = StatisticalTest(
                test_name="single-point",
                groups=[features1.version, features2.version],
                statistic=0.0,
                p_value=1.0,
                significant=False,
                effect_size=difference,
            )

            result = ComparisonResult(
                version1=features1.version,
                version2=features2.version,
                metric=metric,
                value1=value1,
                value2=value2,
                difference=difference,
                percent_change=percent_change,
                test=test,
            )

            results.append(result)

        return results

    def compute_confidence_interval(
        self, data: np.ndarray, confidence: float | None = None
    ) -> tuple[float, float, float]:
        """
        计算置信区间

        Args:
            data: 数据数组
            confidence: 置信水平，None 使用配置值

        Returns:
            (均值, 下界, 上界)
        """
        if confidence is None:
            confidence = self.confidence_level

        data_clean = data[~np.isnan(data)]
        if len(data_clean) < 2:
            mean = np.nanmean(data)
            return mean, mean, mean

        mean = np.mean(data_clean)
        se = stats.sem(data_clean)
        margin = se * stats.t.ppf((1 + confidence) / 2, len(data_clean) - 1)

        return mean, mean - margin, mean + margin

    def correlation_analysis(
        self, features_list: list[GaitFeatures], param_values: list[float], metric: str
    ) -> dict[str, Any]:
        """
        参数敏感性分析（相关性）

        Args:
            features_list: 特征列表
            param_values: 参数值列表
            metric: 要分析的指标

        Returns:
            相关性分析结果字典
        """
        # 提取指标值
        metric_values = []
        valid_params = []

        for features, param in zip(features_list, param_values):
            value = getattr(features, metric, None)
            if value is not None and not np.isnan(value):
                metric_values.append(value)
                valid_params.append(param)

        if len(metric_values) < 3:
            return {
                "metric": metric,
                "n_samples": len(metric_values),
                "correlation": np.nan,
                "p_value": np.nan,
                "significant": False,
            }

        # Pearson 相关
        r, p = stats.pearsonr(valid_params, metric_values)

        # Spearman 相关（非参数）
        rho, p_spearman = stats.spearmanr(valid_params, metric_values)

        return {
            "metric": metric,
            "n_samples": len(metric_values),
            "pearson_r": float(r),
            "pearson_p": float(p),
            "spearman_rho": float(rho),
            "spearman_p": float(p_spearman),
            "significant": p < self.alpha,
            "param_values": valid_params,
            "metric_values": metric_values,
        }

    def sensitivity_analysis(
        self, features_dict: dict[str, GaitFeatures], metrics: list[str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        多版本敏感性分析

        Args:
            features_dict: 版本到特征的字典
            metrics: 要分析的指标列表

        Returns:
            指标到统计结果的字典
        """
        if not features_dict:
            return {}

        if metrics is None:
            # 获取所有数值型特征
            first_features = next(iter(features_dict.values()))
            metrics = [
                k
                for k, v in first_features.__dataclass_fields__.items()
                if k not in ["version", "label", "metadata"]
            ]

        results = {}

        for metric in metrics:
            # 收集所有版本的该指标值
            values = []
            versions = []

            for version, features in features_dict.items():
                value = getattr(features, metric, None)
                if value is not None and not np.isnan(value):
                    values.append(value)
                    versions.append(version)

            if len(values) < 2:
                continue

            # 计算统计量
            results[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "range": float(np.max(values) - np.min(values)),
                "cv": (
                    float(np.std(values) / np.mean(values))
                    if np.mean(values) != 0
                    else 0.0
                ),
                "n_versions": len(values),
                "versions": versions,
                "values": values,
            }

        return results


def main():
    """测试统计分析"""
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
    analyzer = StatisticalAnalyzer(config["statistical_analysis"])

    print("=" * 60)
    print("Statistical Analyzer Test")
    print("=" * 60)

    # 加载两个版本进行对比
    versions = ["v09_stable", "v10_rolling"]
    features_dict = {}

    for version_key in versions:
        try:
            gait_data = loader.load_version(version_key)
            processed = preprocessor.preprocess_gait_data(gait_data)
            features = extractor.extract_all_features(processed)
            features_dict[version_key] = features
        except Exception as e:
            print(f"Warning: Failed to process {version_key}: {e}")

    if len(features_dict) >= 2:
        v1, v2 = list(features_dict.values())[:2]

        # 比较特征
        print(f"\nComparing {v1.version} vs {v2.version}:")
        comparisons = analyzer.compare_features(v1, v2)

        for comp in comparisons[:10]:  # 显示前10个
            print(f"\n  {comp.metric}:")
            print(f"    {v1.version}: {comp.value1:.4f}")
            print(f"    {v2.version}: {comp.value2:.4f}")
            print(
                f"    Difference: {comp.difference:+.4f} ({comp.percent_change:+.2f}%)"
            )

    # 敏感性分析
    print("\n\nSensitivity Analysis:")
    sensitivity = analyzer.sensitivity_analysis(features_dict)

    for metric, stats in list(sensitivity.items())[:5]:
        print(f"\n  {metric}:")
        print(f"    Mean: {stats['mean']:.4f}")
        print(f"    Std: {stats['std']:.4f}")
        print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
        print(f"    CV: {stats['cv']:.2%}")


if __name__ == "__main__":
    main()

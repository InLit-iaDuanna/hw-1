"""ComparisonTool for side-by-side controller/model comparison.

Provides comprehensive comparison capabilities for multiple controllers/models:
- Side-by-side metrics tables with statistical summaries
- Comparison plots (convergence, performance bars, radar charts)
- Export to multiple formats (CSV, JSON, HTML)
- Support for custom metrics and aggregation functions

Example:
    from common.comparison_tool import ComparisonTool, ControllerResult

    # Create comparison tool
    tool = ComparisonTool(name="FSM Controller Comparison")

    # Add results from different controllers
    tool.add_result(ControllerResult(
        name="V13.6 FSM",
        metrics={
            "forward_distance": 5.2,
            "cot": 0.082,
            "success_rate": 0.95,
            "alternations": 8
        },
        time_series={"energy": energy_history}
    ))

    tool.add_result(ControllerResult(
        name="V13.7 FSM + Friction",
        metrics={...}
    ))

    # Generate comparison
    tool.generate_comparison_table()
    tool.plot_metrics_comparison()
    tool.export_to_html("comparison_report.html")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


@dataclass
class ControllerResult:
    """Container for single controller/model evaluation result.

    Attributes:
        name: Controller/model identifier
        metrics: Dictionary of scalar metrics (e.g., CoT, distance, success_rate)
        time_series: Dictionary of time-indexed arrays (e.g., energy history)
        metadata: Additional information (parameters, configuration, etc.)
        convergence_curve: Optimization convergence history (if applicable)
    """
    name: str
    metrics: dict[str, float] = field(default_factory=dict)
    time_series: dict[str, np.ndarray] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    convergence_curve: list[float] | None = None


@dataclass
class MetricSpec:
    """Specification for how to display and aggregate a metric.

    Attributes:
        name: Metric display name
        unit: Unit string (e.g., "m", "J", "%")
        format_str: Format string for display (e.g., ".3f", ".1f")
        higher_is_better: True if higher values are preferred
        threshold_good: Value above/below which metric is considered good
        threshold_warn: Value above/below which metric is considered warning
    """
    name: str
    unit: str = ""
    format_str: str = ".3f"
    higher_is_better: bool = True
    threshold_good: float | None = None
    threshold_warn: float | None = None


class ComparisonTool:
    """Tool for comparing multiple controllers/models side-by-side.

    Supports:
    - Metric comparison tables with color-coding
    - Multiple plot types (bar charts, radar charts, time series)
    - Statistical analysis (mean, std, rankings)
    - Export to CSV, JSON, HTML

    Example:
        tool = ComparisonTool(name="Controller Comparison")
        tool.add_result(result1)
        tool.add_result(result2)
        tool.generate_comparison_table()
        tool.plot_all()
    """

    def __init__(
        self,
        name: str = "Controller Comparison",
        output_dir: Path | str | None = None,
    ):
        """Initialize comparison tool.

        Args:
            name: Name for this comparison study
            output_dir: Directory for saving outputs (default: ./comparison_out)
        """
        self.name = name
        self.results: list[ControllerResult] = []
        self.metric_specs: dict[str, MetricSpec] = {}

        if output_dir is None:
            self.output_dir = Path("comparison_out")
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Default metric specifications
        self._register_default_metrics()

    def _register_default_metrics(self) -> None:
        """Register common metric specifications."""
        self.register_metric("forward_distance", MetricSpec(
            name="Forward Distance",
            unit="m",
            format_str=".2f",
            higher_is_better=True,
            threshold_good=5.0,
            threshold_warn=3.0
        ))

        self.register_metric("cot", MetricSpec(
            name="Cost of Transport",
            unit="",
            format_str=".4f",
            higher_is_better=False,
            threshold_good=0.10,
            threshold_warn=0.15
        ))

        self.register_metric("success_rate", MetricSpec(
            name="Success Rate",
            unit="%",
            format_str=".1f",
            higher_is_better=True,
            threshold_good=80.0,
            threshold_warn=50.0
        ))

        self.register_metric("alternations", MetricSpec(
            name="Alternations",
            unit="steps",
            format_str=".0f",
            higher_is_better=True,
            threshold_good=8.0,
            threshold_warn=5.0
        ))

        self.register_metric("simulated_time", MetricSpec(
            name="Simulation Time",
            unit="s",
            format_str=".2f",
            higher_is_better=True,
        ))

        self.register_metric("energy_efficiency", MetricSpec(
            name="Energy Efficiency",
            unit="J/m",
            format_str=".2f",
            higher_is_better=False,
            threshold_good=10.0,
            threshold_warn=20.0
        ))

    def register_metric(self, key: str, spec: MetricSpec) -> None:
        """Register a metric specification.

        Args:
            key: Metric key in results dictionary
            spec: Metric specification
        """
        self.metric_specs[key] = spec

    def add_result(self, result: ControllerResult) -> None:
        """Add a controller/model result to comparison.

        Args:
            result: Controller evaluation result
        """
        self.results.append(result)

    def add_results(self, results: list[ControllerResult]) -> None:
        """Add multiple results at once.

        Args:
            results: List of controller results
        """
        self.results.extend(results)

    def generate_comparison_table(
        self,
        save_csv: bool = True,
        show_ranking: bool = True
    ) -> pd.DataFrame:
        """Generate comparison table with all metrics.

        Args:
            save_csv: Whether to save table as CSV
            show_ranking: Whether to include ranking column for each metric

        Returns:
            DataFrame with comparison data
        """
        if not self.results:
            raise ValueError("No results added to comparison tool")

        rows = []
        for result in self.results:
            row = {"Controller": result.name}

            # Add all metrics
            for key, value in result.metrics.items():
                spec = self.metric_specs.get(key, MetricSpec(name=key))

                # Format value
                if isinstance(value, (int, float)) and not np.isnan(value):
                    if spec.unit == "%":
                        formatted = f"{value * 100:{spec.format_str}}"
                    else:
                        formatted = f"{value:{spec.format_str}}"

                    # Add unit
                    if spec.unit and spec.unit != "%":
                        formatted += f" {spec.unit}"
                    elif spec.unit == "%":
                        formatted += " %"

                    row[spec.name] = formatted
                else:
                    row[spec.name] = "-"

            rows.append(row)

        df = pd.DataFrame(rows)

        # Add rankings if requested
        if show_ranking:
            for key, spec in self.metric_specs.items():
                col_name = spec.name
                if col_name not in df.columns:
                    continue

                # Extract numeric values for ranking
                values = []
                for result in self.results:
                    val = result.metrics.get(key)
                    if val is not None and not (isinstance(val, float) and np.isnan(val)):
                        values.append(val)
                    else:
                        values.append(None)

                # Compute rankings
                rankings = self._compute_rankings(values, spec.higher_is_better)
                df[f"{col_name} Rank"] = [
                    f"#{r}" if r is not None else "-" for r in rankings
                ]

        # Print to console
        print("\n" + "=" * 100)
        print(f"{self.name} - Metrics Comparison")
        print("=" * 100)
        print(df.to_string(index=False))
        print("=" * 100 + "\n")

        # Save to CSV
        if save_csv:
            csv_path = self.output_dir / "comparison_table.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"[OK] Saved comparison table: {csv_path}")

        return df

    def _compute_rankings(
        self,
        values: list[float | None],
        higher_is_better: bool
    ) -> list[int | None]:
        """Compute rankings for a list of values.

        Args:
            values: List of metric values
            higher_is_better: Whether higher values rank better

        Returns:
            List of rankings (1 = best, None for missing values)
        """
        valid_indices = [i for i, v in enumerate(values) if v is not None]
        if not valid_indices:
            return [None] * len(values)

        valid_values = [values[i] for i in valid_indices]

        # Sort and get rankings
        if higher_is_better:
            sorted_indices = sorted(
                range(len(valid_values)),
                key=lambda i: valid_values[i],
                reverse=True
            )
        else:
            sorted_indices = sorted(
                range(len(valid_values)),
                key=lambda i: valid_values[i]
            )

        # Create ranking map
        rank_map = {valid_indices[sorted_indices[i]]: i + 1 for i in range(len(sorted_indices))}

        return [rank_map.get(i) for i in range(len(values))]

    def plot_metrics_comparison(
        self,
        metrics: list[str] | None = None,
        figsize: tuple[int, int] = (14, 6)
    ) -> None:
        """Plot bar chart comparison of metrics.

        Args:
            metrics: List of metric keys to plot (None = all available)
            figsize: Figure size
        """
        if not self.results:
            print("[WARN] No results to plot")
            return

        # Determine which metrics to plot
        if metrics is None:
            all_keys = set()
            for result in self.results:
                all_keys.update(result.metrics.keys())
            metrics = sorted(all_keys)

        # Filter to metrics that have specs and data
        metrics = [
            m for m in metrics
            if m in self.metric_specs and any(
                m in r.metrics and r.metrics[m] is not None
                for r in self.results
            )
        ]

        if not metrics:
            print("[WARN] No valid metrics to plot")
            return

        n_metrics = len(metrics)
        n_cols = min(3, n_metrics)
        n_rows = (n_metrics + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        if n_metrics == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if n_rows * n_cols > 1 else [axes]

        controller_names = [r.name for r in self.results]
        colors = plt.cm.Set3(np.linspace(0, 1, len(self.results)))

        for idx, metric_key in enumerate(metrics):
            ax = axes[idx]
            spec = self.metric_specs[metric_key]

            # Extract values
            values = []
            for result in self.results:
                val = result.metrics.get(metric_key)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    if spec.unit == "%":
                        values.append(val * 100)
                    else:
                        values.append(val)
                else:
                    values.append(0)

            # Plot bars
            bars = ax.bar(range(len(values)), values, color=colors, alpha=0.8, edgecolor='black')

            # Color code based on thresholds
            if spec.threshold_good is not None and spec.threshold_warn is not None:
                for i, (bar, val) in enumerate(zip(bars, values)):
                    if spec.higher_is_better:
                        if val >= spec.threshold_good:
                            bar.set_color('#2ecc71')  # Green
                        elif val >= spec.threshold_warn:
                            bar.set_color('#f39c12')  # Orange
                        else:
                            bar.set_color('#e74c3c')  # Red
                    else:
                        if val <= spec.threshold_good:
                            bar.set_color('#2ecc71')  # Green
                        elif val <= spec.threshold_warn:
                            bar.set_color('#f39c12')  # Orange
                        else:
                            bar.set_color('#e74c3c')  # Red

            # Add value labels on bars
            for i, (bar, val) in enumerate(zip(bars, values)):
                height = bar.get_height()
                if val != 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{val:{spec.format_str}}",
                        ha='center',
                        va='bottom',
                        fontsize=9
                    )

            # Styling
            ax.set_xticks(range(len(controller_names)))
            ax.set_xticklabels(controller_names, rotation=45, ha='right', fontsize=9)

            unit_str = f" ({spec.unit})" if spec.unit else ""
            ax.set_ylabel(f"{spec.name}{unit_str}", fontsize=10)
            ax.set_title(spec.name, fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()
        out_path = self.output_dir / "metrics_comparison.png"
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved metrics comparison plot: {out_path}")
        plt.close()

    def plot_radar_chart(
        self,
        metrics: list[str] | None = None,
        normalize: bool = True,
        figsize: tuple[int, int] = (10, 10)
    ) -> None:
        """Plot radar chart for multi-dimensional comparison.

        Args:
            metrics: List of metrics to include (None = use all)
            normalize: Whether to normalize metrics to [0, 1] scale
            figsize: Figure size
        """
        if not self.results:
            print("[WARN] No results to plot")
            return

        # Determine metrics
        if metrics is None:
            all_keys = set()
            for result in self.results:
                all_keys.update(result.metrics.keys())
            metrics = sorted(all_keys)

        # Filter valid metrics
        metrics = [
            m for m in metrics
            if m in self.metric_specs and all(
                m in r.metrics and r.metrics[m] is not None
                for r in self.results
            )
        ]

        if len(metrics) < 3:
            print("[WARN] Need at least 3 metrics for radar chart")
            return

        # Extract values
        data = []
        for result in self.results:
            values = [result.metrics[m] for m in metrics]
            data.append(values)

        data = np.array(data)

        # Normalize if requested
        if normalize:
            for i, metric_key in enumerate(metrics):
                spec = self.metric_specs[metric_key]
                col = data[:, i]
                min_val, max_val = col.min(), col.max()

                if max_val - min_val > 1e-6:
                    if spec.higher_is_better:
                        data[:, i] = (col - min_val) / (max_val - min_val)
                    else:
                        # Invert for "lower is better" metrics
                        data[:, i] = (max_val - col) / (max_val - min_val)

        # Create radar chart
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Close the circle

        fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(projection='polar'))

        colors = plt.cm.Set2(np.linspace(0, 1, len(self.results)))

        for i, result in enumerate(self.results):
            values = data[i].tolist()
            values += values[:1]  # Close the circle
            ax.plot(angles, values, 'o-', linewidth=2, label=result.name, color=colors[i])
            ax.fill(angles, values, alpha=0.15, color=colors[i])

        # Set labels
        metric_labels = [self.metric_specs[m].name for m in metrics]
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metric_labels, fontsize=10)

        ax.set_ylim(0, 1 if normalize else None)
        ax.set_title(
            f"{self.name} - Radar Chart" + (" (Normalized)" if normalize else ""),
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        out_path = self.output_dir / "radar_chart.png"
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved radar chart: {out_path}")
        plt.close()

    def plot_convergence_curves(
        self,
        figsize: tuple[int, int] = (12, 6)
    ) -> None:
        """Plot optimization convergence curves (if available).

        Args:
            figsize: Figure size
        """
        results_with_convergence = [
            r for r in self.results if r.convergence_curve is not None
        ]

        if not results_with_convergence:
            print("[WARN] No convergence curves available")
            return

        fig, ax = plt.subplots(figsize=figsize)

        colors = plt.cm.tab10(np.linspace(0, 1, len(results_with_convergence)))

        for i, result in enumerate(results_with_convergence):
            curve = result.convergence_curve
            ax.plot(
                range(1, len(curve) + 1),
                curve,
                marker='o',
                markersize=3,
                linewidth=2,
                label=result.name,
                color=colors[i]
            )

        ax.set_xlabel("Evaluation Number", fontsize=12)
        ax.set_ylabel("Best Objective Value", fontsize=12)
        ax.set_title("Convergence Curves Comparison", fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3)

        plt.tight_layout()
        out_path = self.output_dir / "convergence_curves.png"
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved convergence curves: {out_path}")
        plt.close()

    def plot_time_series_comparison(
        self,
        series_key: str,
        ylabel: str | None = None,
        figsize: tuple[int, int] = (12, 6)
    ) -> None:
        """Plot time series comparison for a specific metric.

        Args:
            series_key: Key for time series data in results
            ylabel: Y-axis label (default: series_key)
            figsize: Figure size
        """
        results_with_series = [
            r for r in self.results
            if series_key in r.time_series and r.time_series[series_key] is not None
        ]

        if not results_with_series:
            print(f"[WARN] No time series data for '{series_key}'")
            return

        fig, ax = plt.subplots(figsize=figsize)

        colors = plt.cm.tab10(np.linspace(0, 1, len(results_with_series)))

        for i, result in enumerate(results_with_series):
            series = result.time_series[series_key]
            time = np.arange(len(series)) * 0.001  # Assuming 1ms timestep
            ax.plot(time, series, linewidth=1.5, label=result.name, color=colors[i], alpha=0.8)

        ax.set_xlabel("Time (s)", fontsize=12)
        ax.set_ylabel(ylabel or series_key, fontsize=12)
        ax.set_title(f"{series_key} Comparison", fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3)

        plt.tight_layout()
        out_path = self.output_dir / f"timeseries_{series_key}.png"
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved time series comparison: {out_path}")
        plt.close()

    def plot_all(self) -> None:
        """Generate all available comparison plots."""
        print("\n" + "=" * 80)
        print("Generating all comparison plots...")
        print("=" * 80 + "\n")

        self.plot_metrics_comparison()
        self.plot_radar_chart()
        self.plot_convergence_curves()

        # Plot common time series if available
        common_series = set(self.results[0].time_series.keys()) if self.results else set()
        for result in self.results[1:]:
            common_series &= set(result.time_series.keys())

        for series_key in common_series:
            self.plot_time_series_comparison(series_key)

    def export_to_json(self, filepath: Path | str | None = None) -> None:
        """Export comparison data to JSON.

        Args:
            filepath: Output path (default: output_dir/comparison.json)
        """
        if filepath is None:
            filepath = self.output_dir / "comparison.json"
        else:
            filepath = Path(filepath)

        data = {
            "name": self.name,
            "results": [
                {
                    "name": r.name,
                    "metrics": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in r.metrics.items()},
                    "metadata": r.metadata,
                }
                for r in self.results
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Exported to JSON: {filepath}")

    def export_to_html(self, filepath: Path | str | None = None) -> None:
        """Export comparison as interactive HTML report.

        Args:
            filepath: Output path (default: output_dir/comparison_report.html)
        """
        if filepath is None:
            filepath = self.output_dir / "comparison_report.html"
        else:
            filepath = Path(filepath)

        # Generate table
        df = self.generate_comparison_table(save_csv=False, show_ranking=True)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #ecf0f1;
        }}
        .metric-name {{
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <h1>{self.name}</h1>

    <h2>Metrics Comparison Table</h2>
    {df.to_html(index=False, escape=False)}

    <h2>Visual Comparisons</h2>
"""

        # Add images if they exist
        image_files = [
            ("Metrics Comparison", "metrics_comparison.png"),
            ("Radar Chart", "radar_chart.png"),
            ("Convergence Curves", "convergence_curves.png"),
        ]

        for title, filename in image_files:
            img_path = self.output_dir / filename
            if img_path.exists():
                html_content += f"""
    <h3>{title}</h3>
    <img src="{filename}" alt="{title}">
"""

        html_content += """
    <div class="footer">
        <p>Generated by ComparisonTool | HW-1 Project</p>
    </div>
</body>
</html>
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"[OK] Exported HTML report: {filepath}")

    def get_summary_statistics(self) -> dict[str, dict[str, float]]:
        """Compute summary statistics across all results.

        Returns:
            Dictionary mapping metric keys to stats (mean, std, min, max)
        """
        stats = {}

        all_metric_keys = set()
        for result in self.results:
            all_metric_keys.update(result.metrics.keys())

        for key in all_metric_keys:
            values = [
                r.metrics[key] for r in self.results
                if key in r.metrics and r.metrics[key] is not None
                and not (isinstance(r.metrics[key], float) and np.isnan(r.metrics[key]))
            ]

            if values:
                stats[key] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "count": len(values)
                }

        return stats

    def print_summary(self) -> None:
        """Print summary statistics to console."""
        stats = self.get_summary_statistics()

        print("\n" + "=" * 100)
        print(f"{self.name} - Summary Statistics")
        print("=" * 100)

        for key, stat in stats.items():
            spec = self.metric_specs.get(key, MetricSpec(name=key))
            print(f"\n{spec.name}:")
            print(f"  Mean: {stat['mean']:{spec.format_str}} {spec.unit}")
            print(f"  Std:  {stat['std']:{spec.format_str}} {spec.unit}")
            print(f"  Min:  {stat['min']:{spec.format_str}} {spec.unit}")
            print(f"  Max:  {stat['max']:{spec.format_str}} {spec.unit}")
            print(f"  N:    {stat['count']}")

        print("=" * 100 + "\n")

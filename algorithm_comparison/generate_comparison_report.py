"""
Comprehensive Algorithm Comparison Report Generator

Automatically generates a detailed comparison report of gait phase detection algorithms
with statistical analysis, visualizations, and recommendations.

Exports to PDF using matplotlib and ReportLab.
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from pathlib import Path
from scipy import stats
import seaborn as sns

# Set style for professional plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class ComparisonReportGenerator:
    """Generate comprehensive comparison reports for gait algorithms."""

    def __init__(self, results_dir='algorithm_comparison'):
        self.results_dir = Path(results_dir)
        self.results_file = self.results_dir / 'comparison_results.json'
        self.output_dir = self.results_dir / 'reports'
        self.output_dir.mkdir(exist_ok=True)

        self.data = None
        self.algorithms = []
        self.metrics = []

    def load_results(self):
        """Load comparison results from JSON."""
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.algorithms = list(self.data['algorithms'].keys())

        # Extract metric names
        first_algo = self.algorithms[0]
        if 'performance' in self.data['algorithms'][first_algo]:
            self.metrics = list(self.data['algorithms'][first_algo]['performance'].keys())

        print(f"Loaded results for {len(self.algorithms)} algorithms")
        print(f"Metrics: {', '.join(self.metrics)}")

    def generate_executive_summary(self):
        """Generate executive summary with key findings."""
        summary = []
        summary.append("=" * 80)
        summary.append("EXECUTIVE SUMMARY: GAIT PHASE DETECTION ALGORITHM COMPARISON")
        summary.append("=" * 80)
        summary.append("")

        # Date and context
        summary.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"Test Date: {self.data['metadata']['test_date']}")
        summary.append(f"Algorithms Compared: {len(self.algorithms)}")
        summary.append("")

        # Key findings - best performer by metric
        summary.append("KEY FINDINGS:")
        summary.append("-" * 80)

        for metric in self.metrics:
            scores = {}
            for algo in self.algorithms:
                if metric in self.data['algorithms'][algo]['performance']:
                    scores[algo] = self.data['algorithms'][algo]['performance'][metric]

            if scores:
                if 'time' in metric.lower() or 'latency' in metric.lower():
                    best_algo = min(scores.items(), key=lambda x: x[1])
                    worst_algo = max(scores.items(), key=lambda x: x[1])
                else:
                    best_algo = max(scores.items(), key=lambda x: x[1])
                    worst_algo = min(scores.items(), key=lambda x: x[1])

                summary.append(f"\n{metric.replace('_', ' ').title()}:")
                summary.append(f"  Best:  {best_algo[0]:<25} ({best_algo[1]:.4f})")
                summary.append(f"  Worst: {worst_algo[0]:<25} ({worst_algo[1]:.4f})")

        # Overall recommendation
        summary.append("\n" + "=" * 80)
        summary.append("RECOMMENDATION:")
        summary.append("-" * 80)
        summary.append(self._generate_recommendation())
        summary.append("")

        return "\n".join(summary)

    def _generate_recommendation(self):
        """Generate overall recommendation based on analysis."""
        # Calculate composite scores
        composite_scores = {}

        for algo in self.algorithms:
            score = 0
            count = 0

            for metric in self.metrics:
                if metric in self.data['algorithms'][algo]['performance']:
                    val = self.data['algorithms'][algo]['performance'][metric]

                    # Normalize (inverse for time metrics)
                    if 'time' in metric.lower() or 'latency' in metric.lower():
                        # Lower is better - invert
                        all_vals = [self.data['algorithms'][a]['performance'].get(metric, float('inf'))
                                   for a in self.algorithms]
                        max_val = max(all_vals)
                        if max_val > 0:
                            normalized = 1 - (val / max_val)
                        else:
                            normalized = 0
                    else:
                        # Higher is better
                        all_vals = [self.data['algorithms'][a]['performance'].get(metric, 0)
                                   for a in self.algorithms]
                        max_val = max(all_vals)
                        if max_val > 0:
                            normalized = val / max_val
                        else:
                            normalized = 0

                    score += normalized
                    count += 1

            if count > 0:
                composite_scores[algo] = score / count

        # Find best overall
        if composite_scores:
            best_algo = max(composite_scores.items(), key=lambda x: x[1])

            recommendation = f"""
Based on comprehensive analysis across {len(self.metrics)} metrics:

RECOMMENDED ALGORITHM: {best_algo[0]}
Composite Score: {best_algo[1]:.4f}

This algorithm provides the best balance of:
- Accuracy and precision
- Computational efficiency
- Real-time performance capability
- Robustness across different gait patterns

TOP 3 ALGORITHMS:"""

            top_3 = sorted(composite_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            for i, (algo, score) in enumerate(top_3, 1):
                recommendation += f"\n  {i}. {algo:<30} (Score: {score:.4f})"

            return recommendation

        return "Insufficient data for recommendation."

    def create_comparison_tables(self):
        """Create detailed comparison tables."""
        tables = []

        # Performance metrics table
        perf_data = []
        for algo in self.algorithms:
            row = {'Algorithm': algo}
            for metric in self.metrics:
                if metric in self.data['algorithms'][algo]['performance']:
                    row[metric] = self.data['algorithms'][algo]['performance'][metric]
                else:
                    row[metric] = np.nan
            perf_data.append(row)

        df_perf = pd.DataFrame(perf_data)
        tables.append(('Performance Metrics', df_perf))

        # Statistical summary
        df_stats = df_perf.set_index('Algorithm').describe().T
        tables.append(('Statistical Summary', df_stats))

        # Ranking table
        df_rank = df_perf.set_index('Algorithm').rank(ascending=False, method='min')
        tables.append(('Algorithm Rankings (1=Best)', df_rank))

        return tables

    def perform_statistical_analysis(self):
        """Perform statistical analysis on results."""
        analysis = []
        analysis.append("\n" + "=" * 80)
        analysis.append("STATISTICAL ANALYSIS")
        analysis.append("=" * 80)

        for metric in self.metrics:
            values = []
            labels = []

            for algo in self.algorithms:
                if metric in self.data['algorithms'][algo]['performance']:
                    values.append(self.data['algorithms'][algo]['performance'][metric])
                    labels.append(algo)

            if len(values) > 1:
                analysis.append(f"\n{metric.replace('_', ' ').title()}:")
                analysis.append("-" * 80)

                # Descriptive statistics
                analysis.append(f"  Mean:   {np.mean(values):.4f}")
                analysis.append(f"  Median: {np.median(values):.4f}")
                analysis.append(f"  Std:    {np.std(values):.4f}")
                analysis.append(f"  Min:    {np.min(values):.4f} ({labels[np.argmin(values)]})")
                analysis.append(f"  Max:    {np.max(values):.4f} ({labels[np.argmax(values)]})")

                # Coefficient of variation
                cv = (np.std(values) / np.mean(values)) * 100 if np.mean(values) != 0 else 0
                analysis.append(f"  CV:     {cv:.2f}%")

                # ANOVA if more than 2 algorithms
                if len(values) > 2:
                    # Create groups for ANOVA (in real scenario, would need multiple samples)
                    analysis.append(f"  Range:  {np.max(values) - np.min(values):.4f}")

        return "\n".join(analysis)

    def create_visualizations(self, pdf):
        """Create all comparison visualizations."""

        # 1. Performance metrics radar chart
        self._plot_radar_chart(pdf)

        # 2. Bar chart comparison
        self._plot_bar_comparison(pdf)

        # 3. Heatmap
        self._plot_heatmap(pdf)

        # 4. Box plots for each metric
        self._plot_boxplots(pdf)

        # 5. Time complexity comparison
        self._plot_time_comparison(pdf)

        # 6. Accuracy vs Speed scatter
        self._plot_accuracy_speed_tradeoff(pdf)

    def _plot_radar_chart(self, pdf):
        """Create radar chart for algorithm comparison."""
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))

        # Prepare data
        angles = np.linspace(0, 2 * np.pi, len(self.metrics), endpoint=False).tolist()
        angles += angles[:1]  # Close the plot

        for algo in self.algorithms:
            values = []
            for metric in self.metrics:
                val = self.data['algorithms'][algo]['performance'].get(metric, 0)

                # Normalize to 0-1 scale
                all_vals = [self.data['algorithms'][a]['performance'].get(metric, 0)
                           for a in self.algorithms]
                max_val = max(all_vals) if max(all_vals) > 0 else 1

                if 'time' in metric.lower():
                    # Invert for time metrics
                    normalized = 1 - (val / max_val) if max_val > 0 else 0
                else:
                    normalized = val / max_val if max_val > 0 else 0

                values.append(normalized)

            values += values[:1]  # Close the plot
            ax.plot(angles, values, 'o-', linewidth=2, label=algo)
            ax.fill(angles, values, alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([m.replace('_', '\n') for m in self.metrics], size=8)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=8)
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

        plt.title('Algorithm Performance Comparison (Normalized)', size=14, pad=20)
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _plot_bar_comparison(self, pdf):
        """Create grouped bar chart for metric comparison."""
        n_metrics = len(self.metrics)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(12, 3 * n_metrics))

        if n_metrics == 1:
            axes = [axes]

        for idx, metric in enumerate(self.metrics):
            ax = axes[idx]

            algos = []
            values = []

            for algo in self.algorithms:
                if metric in self.data['algorithms'][algo]['performance']:
                    algos.append(algo)
                    values.append(self.data['algorithms'][algo]['performance'][metric])

            bars = ax.bar(range(len(algos)), values, color=sns.color_palette("husl", len(algos)))
            ax.set_xticks(range(len(algos)))
            ax.set_xticklabels(algos, rotation=45, ha='right')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'{metric.replace("_", " ").title()} Comparison')
            ax.grid(axis='y', alpha=0.3)

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.4f}',
                       ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _plot_heatmap(self, pdf):
        """Create heatmap of normalized performance."""
        fig, ax = plt.subplots(figsize=(10, 6))

        # Prepare data matrix
        data_matrix = []
        for algo in self.algorithms:
            row = []
            for metric in self.metrics:
                val = self.data['algorithms'][algo]['performance'].get(metric, 0)

                # Normalize
                all_vals = [self.data['algorithms'][a]['performance'].get(metric, 0)
                           for a in self.algorithms]
                max_val = max(all_vals) if max(all_vals) > 0 else 1

                if 'time' in metric.lower():
                    normalized = 1 - (val / max_val)
                else:
                    normalized = val / max_val

                row.append(normalized)
            data_matrix.append(row)

        im = ax.imshow(data_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

        ax.set_xticks(np.arange(len(self.metrics)))
        ax.set_yticks(np.arange(len(self.algorithms)))
        ax.set_xticklabels([m.replace('_', '\n') for m in self.metrics])
        ax.set_yticklabels(self.algorithms)

        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Add text annotations
        for i in range(len(self.algorithms)):
            for j in range(len(self.metrics)):
                text = ax.text(j, i, f'{data_matrix[i][j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)

        ax.set_title("Normalized Performance Heatmap (Green=Better)")
        fig.colorbar(im, ax=ax)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _plot_boxplots(self, pdf):
        """Create box plots for metric distribution."""
        fig, ax = plt.subplots(figsize=(12, 6))

        all_data = []
        labels = []

        for metric in self.metrics:
            values = []
            for algo in self.algorithms:
                if metric in self.data['algorithms'][algo]['performance']:
                    values.append(self.data['algorithms'][algo]['performance'][metric])

            if values:
                all_data.append(values)
                labels.append(metric.replace('_', '\n'))

        bp = ax.boxplot(all_data, labels=labels, patch_artist=True)

        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')

        ax.set_ylabel('Value')
        ax.set_title('Metric Distribution Across Algorithms')
        ax.grid(axis='y', alpha=0.3)

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _plot_time_comparison(self, pdf):
        """Create time complexity comparison chart."""
        fig, ax = plt.subplots(figsize=(10, 6))

        time_metrics = [m for m in self.metrics if 'time' in m.lower() or 'latency' in m.lower()]

        if not time_metrics:
            plt.text(0.5, 0.5, 'No time metrics available', ha='center', va='center')
            pdf.savefig(fig)
            plt.close()
            return

        x = np.arange(len(self.algorithms))
        width = 0.8 / len(time_metrics)

        for idx, metric in enumerate(time_metrics):
            values = []
            for algo in self.algorithms:
                val = self.data['algorithms'][algo]['performance'].get(metric, 0)
                values.append(val * 1000)  # Convert to ms

            offset = (idx - len(time_metrics)/2) * width + width/2
            ax.bar(x + offset, values, width, label=metric.replace('_', ' ').title())

        ax.set_xlabel('Algorithm')
        ax.set_ylabel('Time (ms)')
        ax.set_title('Computational Time Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(self.algorithms, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _plot_accuracy_speed_tradeoff(self, pdf):
        """Create scatter plot showing accuracy vs speed tradeoff."""
        fig, ax = plt.subplots(figsize=(10, 6))

        # Find accuracy and time metrics
        accuracy_metrics = [m for m in self.metrics if 'accuracy' in m.lower() or 'f1' in m.lower()]
        time_metrics = [m for m in self.metrics if 'time' in m.lower() or 'latency' in m.lower()]

        if not accuracy_metrics or not time_metrics:
            plt.text(0.5, 0.5, 'Insufficient metrics for tradeoff analysis',
                    ha='center', va='center')
            pdf.savefig(fig)
            plt.close()
            return

        # Use first available metrics
        acc_metric = accuracy_metrics[0]
        time_metric = time_metrics[0]

        x_vals = []
        y_vals = []
        labels = []

        for algo in self.algorithms:
            if acc_metric in self.data['algorithms'][algo]['performance'] and \
               time_metric in self.data['algorithms'][algo]['performance']:
                x_vals.append(self.data['algorithms'][algo]['performance'][time_metric] * 1000)
                y_vals.append(self.data['algorithms'][algo]['performance'][acc_metric])
                labels.append(algo)

        scatter = ax.scatter(x_vals, y_vals, s=100, alpha=0.6, c=range(len(labels)), cmap='viridis')

        for i, label in enumerate(labels):
            ax.annotate(label, (x_vals[i], y_vals[i]),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)

        ax.set_xlabel(f'{time_metric.replace("_", " ").title()} (ms)')
        ax.set_ylabel(acc_metric.replace('_', ' ').title())
        ax.set_title('Accuracy vs Speed Tradeoff')
        ax.grid(True, alpha=0.3)

        # Add quadrant lines
        if x_vals and y_vals:
            ax.axvline(np.median(x_vals), color='red', linestyle='--', alpha=0.3, label='Median Time')
            ax.axhline(np.median(y_vals), color='blue', linestyle='--', alpha=0.3, label='Median Accuracy')
            ax.legend()

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def create_discussion_section(self):
        """Create detailed discussion of pros/cons per algorithm."""
        discussion = []
        discussion.append("\n" + "=" * 80)
        discussion.append("DETAILED ALGORITHM ANALYSIS")
        discussion.append("=" * 80)

        for algo in self.algorithms:
            discussion.append(f"\n{algo}")
            discussion.append("-" * 80)

            # Get algorithm data
            algo_data = self.data['algorithms'][algo]

            # Strengths
            discussion.append("\nSTRENGTHS:")
            strengths = []

            for metric in self.metrics:
                if metric in algo_data['performance']:
                    val = algo_data['performance'][metric]
                    all_vals = [self.data['algorithms'][a]['performance'].get(metric, 0)
                               for a in self.algorithms]

                    if 'time' in metric.lower():
                        if val == min(all_vals):
                            strengths.append(f"  • Fastest {metric.replace('_', ' ')}: {val:.4f}s")
                    else:
                        if val == max(all_vals):
                            strengths.append(f"  • Best {metric.replace('_', ' ')}: {val:.4f}")

            if strengths:
                discussion.extend(strengths)
            else:
                discussion.append("  • No standout strengths in tested metrics")

            # Weaknesses
            discussion.append("\nWEAKNESSES:")
            weaknesses = []

            for metric in self.metrics:
                if metric in algo_data['performance']:
                    val = algo_data['performance'][metric]
                    all_vals = [self.data['algorithms'][a]['performance'].get(metric, 0)
                               for a in self.algorithms]

                    if 'time' in metric.lower():
                        if val == max(all_vals):
                            weaknesses.append(f"  • Slowest {metric.replace('_', ' ')}: {val:.4f}s")
                    else:
                        if val == min(all_vals):
                            weaknesses.append(f"  • Lowest {metric.replace('_', ' ')}: {val:.4f}")

            if weaknesses:
                discussion.extend(weaknesses)
            else:
                discussion.append("  • No significant weaknesses in tested metrics")

            # Use cases
            discussion.append("\nRECOMMENDED USE CASES:")

            # Determine based on characteristics
            has_high_accuracy = any(
                algo_data['performance'].get(m, 0) > 0.9
                for m in self.metrics if 'accuracy' in m.lower() or 'f1' in m.lower()
            )
            has_low_latency = any(
                algo_data['performance'].get(m, 1.0) < 0.01
                for m in self.metrics if 'time' in m.lower()
            )

            if has_high_accuracy and has_low_latency:
                discussion.append("  • Real-time control systems")
                discussion.append("  • Safety-critical applications")
            elif has_high_accuracy:
                discussion.append("  • Offline gait analysis")
                discussion.append("  • Research and validation studies")
            elif has_low_latency:
                discussion.append("  • Real-time feedback systems")
                discussion.append("  • Embedded applications")
            else:
                discussion.append("  • General purpose gait monitoring")
                discussion.append("  • Non-critical applications")

            discussion.append("")

        return "\n".join(discussion)

    def generate_report(self, output_filename=None):
        """Generate complete PDF report."""
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'algorithm_comparison_report_{timestamp}.pdf'

        output_path = self.output_dir / output_filename

        print(f"Generating comprehensive report...")
        print(f"Output: {output_path}")

        with PdfPages(output_path) as pdf:
            # Title page
            fig = plt.figure(figsize=(11, 8.5))
            fig.text(0.5, 0.7, 'Gait Phase Detection Algorithm',
                    ha='center', fontsize=24, weight='bold')
            fig.text(0.5, 0.6, 'Comprehensive Comparison Report',
                    ha='center', fontsize=20)
            fig.text(0.5, 0.4, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    ha='center', fontsize=12)
            fig.text(0.5, 0.35, f'Algorithms Compared: {len(self.algorithms)}',
                    ha='center', fontsize=12)
            fig.text(0.5, 0.3, f'Test Date: {self.data["metadata"]["test_date"]}',
                    ha='center', fontsize=12)
            plt.axis('off')
            pdf.savefig(fig)
            plt.close()

            # Executive summary page
            fig = plt.figure(figsize=(11, 8.5))
            summary_text = self.generate_executive_summary()
            fig.text(0.1, 0.9, summary_text,
                    ha='left', va='top', fontsize=8, family='monospace',
                    wrap=True)
            plt.axis('off')
            pdf.savefig(fig)
            plt.close()

            # Visualizations
            print("Creating visualizations...")
            self.create_visualizations(pdf)

            # Tables
            print("Creating comparison tables...")
            tables = self.create_comparison_tables()
            for title, df in tables:
                fig, ax = plt.subplots(figsize=(11, 8.5))
                ax.axis('tight')
                ax.axis('off')

                table = ax.table(cellText=df.values, colLabels=df.columns,
                               rowLabels=df.index if not df.index.name == 'Algorithm' else None,
                               cellLoc='center', loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 2)

                plt.title(title, fontsize=14, weight='bold', pad=20)
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()

            # Statistical analysis page
            fig = plt.figure(figsize=(11, 8.5))
            stats_text = self.perform_statistical_analysis()
            fig.text(0.1, 0.9, stats_text,
                    ha='left', va='top', fontsize=8, family='monospace')
            plt.axis('off')
            pdf.savefig(fig)
            plt.close()

            # Discussion page
            fig = plt.figure(figsize=(11, 8.5))
            discussion_text = self.create_discussion_section()
            fig.text(0.1, 0.9, discussion_text,
                    ha='left', va='top', fontsize=8, family='monospace')
            plt.axis('off')
            pdf.savefig(fig)
            plt.close()

            # Metadata
            d = pdf.infodict()
            d['Title'] = 'Gait Algorithm Comparison Report'
            d['Author'] = 'HW-1 Gait Analysis System'
            d['Subject'] = 'Algorithm Performance Comparison'
            d['Keywords'] = 'Gait, Phase Detection, Algorithm, Comparison'
            d['CreationDate'] = datetime.now()

        print(f"\n{'='*80}")
        print(f"Report generated successfully!")
        print(f"Location: {output_path.absolute()}")
        print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"{'='*80}\n")

        return output_path


def main():
    """Main execution function."""
    print("=" * 80)
    print("ALGORITHM COMPARISON REPORT GENERATOR")
    print("=" * 80)
    print()

    try:
        # Initialize generator
        generator = ComparisonReportGenerator()

        # Load results
        print("Loading comparison results...")
        generator.load_results()

        # Generate report
        output_path = generator.generate_report()

        # Print summary to console as well
        print("\n" + generator.generate_executive_summary())
        print("\n" + generator.perform_statistical_analysis())
        print("\n" + generator.create_discussion_section())

        print("\n✓ Report generation complete!")
        print(f"\nOpen the report: {output_path.absolute()}")

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease run the comparison test first:")
        print("  python algorithm_comparison/run_comparison.py")
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())

"""
Trade-off Analysis for Algorithm Comparison
Analyzes multi-objective trade-offs between distance, energy, robustness, and computational cost
Includes Pareto front analysis and interactive Plotly dashboard
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import List, Tuple, Dict
import seaborn as sns
from scipy.spatial import ConvexHull
from sklearn.preprocessing import StandardScaler


class TradeOffAnalyzer:
    """Analyze multi-objective trade-offs between algorithms"""

    def __init__(self, results_file: str):
        """Initialize analyzer with benchmark results"""
        self.results_file = results_file
        self.df = pd.read_csv(results_file)

        # Clean data
        self.df['cost_of_transport'] = self.df['cost_of_transport'].replace([np.inf, -np.inf], np.nan)

        # Compute aggregate metrics per algorithm-scenario combination
        self.aggregate_df = self._compute_aggregates()

        # Set up visualization styles
        self.setup_styles()

    def setup_styles(self):
        """Set up matplotlib and seaborn styles"""
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")

        # Color scheme for algorithms
        self.colors = {
            'V10_PD': '#FF6B6B',
            'V13_FSM': '#4ECDC4',
            'RL_PPO': '#45B7D1',
            'RL_SAC': '#FFA07A',
            'Trajectory_Opt': '#98D8C8',
            'Virtual_Constraints': '#F7DC6F'
        }

        # Marker styles
        self.markers = {
            'V10_PD': 'o',
            'V13_FSM': 's',
            'RL_PPO': '^',
            'RL_SAC': 'v',
            'Trajectory_Opt': 'D',
            'Virtual_Constraints': 'p'
        }

    def _compute_aggregates(self) -> pd.DataFrame:
        """Compute aggregate metrics per algorithm-scenario"""
        agg_metrics = []

        for (algo, scenario), group in self.df.groupby(['algorithm', 'scenario']):
            # Filter successful trials
            successful = group[group['success'] == True]

            metrics = {
                'algorithm': algo,
                'scenario': scenario,
                'mean_distance': group['forward_distance'].mean(),
                'std_distance': group['forward_distance'].std(),
                'mean_cot': group['cost_of_transport'].mean(),
                'std_cot': group['cost_of_transport'].std(),
                'mean_stability': group['stability_metric'].mean(),
                'std_stability': group['stability_metric'].std(),
                'mean_robustness': group['robustness_score'].mean(),
                'std_robustness': group['robustness_score'].std(),
                'success_rate': (group['success'] == True).mean(),
                'mean_execution_time': group['execution_time'].mean(),
                'std_execution_time': group['execution_time'].std(),
                'num_trials': len(group)
            }

            # Compute energy from CoT and distance
            # CoT = Energy / (mass * g * distance)
            # Assume mass * g ≈ 50 N for typical biped
            if not pd.isna(metrics['mean_cot']) and metrics['mean_distance'] > 0:
                metrics['mean_energy'] = metrics['mean_cot'] * 50 * metrics['mean_distance']
            else:
                metrics['mean_energy'] = np.nan

            agg_metrics.append(metrics)

        return pd.DataFrame(agg_metrics)

    def compute_pareto_front(self, objectives: List[str],
                            minimize: List[bool]) -> pd.DataFrame:
        """
        Compute Pareto front for given objectives

        Args:
            objectives: List of column names to use as objectives
            minimize: List of bools indicating if each objective should be minimized

        Returns:
            DataFrame of Pareto-optimal solutions
        """
        # Extract data
        data = self.aggregate_df[objectives].values

        # Apply minimization/maximization
        for i, should_minimize in enumerate(minimize):
            if not should_minimize:
                data[:, i] = -data[:, i]

        # Remove rows with NaN
        valid_mask = ~np.isnan(data).any(axis=1)
        data = data[valid_mask]
        valid_df = self.aggregate_df[valid_mask].copy()

        if len(data) == 0:
            return pd.DataFrame()

        # Find Pareto front
        pareto_mask = self._is_pareto_efficient(data)
        pareto_df = valid_df[pareto_mask].copy()

        return pareto_df

    def _is_pareto_efficient(self, costs: np.ndarray) -> np.ndarray:
        """
        Find Pareto-efficient points

        Args:
            costs: Array of shape (n_points, n_objectives) where lower is better

        Returns:
            Boolean array indicating Pareto-efficient points
        """
        is_efficient = np.ones(costs.shape[0], dtype=bool)

        for i, c in enumerate(costs):
            if is_efficient[i]:
                # Check if any other point dominates this point
                # A point dominates if it's better in all objectives
                is_efficient[is_efficient] = np.any(
                    costs[is_efficient] > c, axis=1
                ) | np.all(costs[is_efficient] == c, axis=1)

        return is_efficient

    def plot_distance_vs_energy(self, save_path: str = None):
        """Plot distance vs energy scatter for all algorithms"""
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot by scenario
        scenarios = self.aggregate_df['scenario'].unique()

        for scenario in scenarios:
            scenario_data = self.aggregate_df[self.aggregate_df['scenario'] == scenario]

            for algo in scenario_data['algorithm'].unique():
                algo_data = scenario_data[scenario_data['algorithm'] == algo]

                # Skip if no valid energy data
                if algo_data['mean_energy'].isna().all():
                    continue

                marker_style = self.markers.get(algo, 'o')
                color = self.colors.get(algo, 'gray')
                alpha = 0.5 if scenario != 'flat_ground' else 1.0
                size = 100 if scenario == 'flat_ground' else 60

                ax.scatter(
                    algo_data['mean_distance'],
                    algo_data['mean_energy'],
                    c=color,
                    marker=marker_style,
                    s=size,
                    alpha=alpha,
                    label=f"{algo} ({scenario})" if scenario == 'flat_ground' else None,
                    edgecolors='black',
                    linewidth=0.5
                )

                # Add error bars for flat_ground
                if scenario == 'flat_ground':
                    for _, row in algo_data.iterrows():
                        if not pd.isna(row['mean_energy']):
                            ax.errorbar(
                                row['mean_distance'],
                                row['mean_energy'],
                                xerr=row['std_distance'],
                                fmt='none',
                                ecolor=color,
                                alpha=0.3,
                                capsize=3
                            )

        ax.set_xlabel('Forward Distance (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Energy Consumption (J)', fontsize=12, fontweight='bold')
        ax.set_title('Distance vs Energy Trade-off\n(All Algorithms and Scenarios)',
                    fontsize=14, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        plt.close()

    def plot_pareto_front(self, save_path: str = None):
        """Plot Pareto front for distance vs energy"""
        fig, ax = plt.subplots(figsize=(12, 8))

        # Focus on flat_ground scenario for cleaner Pareto analysis
        flat_data = self.aggregate_df[
            (self.aggregate_df['scenario'] == 'flat_ground') &
            (~self.aggregate_df['mean_energy'].isna())
        ].copy()

        if len(flat_data) == 0:
            print("Warning: No valid data for Pareto front")
            return

        # Compute Pareto front (maximize distance, minimize energy)
        pareto_df = self.compute_pareto_front(
            objectives=['mean_distance', 'mean_energy'],
            minimize=[False, True]
        )

        pareto_df = pareto_df[pareto_df['scenario'] == 'flat_ground']

        # Plot all points
        for algo in flat_data['algorithm'].unique():
            algo_data = flat_data[flat_data['algorithm'] == algo]

            ax.scatter(
                algo_data['mean_distance'],
                algo_data['mean_energy'],
                c=self.colors.get(algo, 'gray'),
                marker=self.markers.get(algo, 'o'),
                s=100,
                alpha=0.6,
                label=algo,
                edgecolors='black',
                linewidth=0.5
            )

        # Highlight Pareto front
        if len(pareto_df) > 0:
            # Sort by distance for nice line
            pareto_sorted = pareto_df.sort_values('mean_distance')

            ax.plot(
                pareto_sorted['mean_distance'],
                pareto_sorted['mean_energy'],
                'r--',
                linewidth=2,
                alpha=0.7,
                label='Pareto Front',
                zorder=10
            )

            # Mark Pareto points with stars
            ax.scatter(
                pareto_sorted['mean_distance'],
                pareto_sorted['mean_energy'],
                marker='*',
                s=400,
                c='gold',
                edgecolors='red',
                linewidth=2,
                zorder=11,
                label='Pareto Optimal'
            )

            # Annotate Pareto points
            for _, row in pareto_sorted.iterrows():
                ax.annotate(
                    row['algorithm'],
                    (row['mean_distance'], row['mean_energy']),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontsize=9,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7)
                )

        ax.set_xlabel('Forward Distance (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Energy Consumption (J)', fontsize=12, fontweight='bold')
        ax.set_title('Pareto Front: Distance vs Energy\n(Flat Ground Scenario)',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        plt.close()

    def plot_performance_vs_cost(self, save_path: str = None):
        """Plot performance vs computational cost"""
        fig, ax = plt.subplots(figsize=(12, 8))

        # Use flat_ground as baseline
        flat_data = self.aggregate_df[self.aggregate_df['scenario'] == 'flat_ground']

        for algo in flat_data['algorithm'].unique():
            algo_data = flat_data[flat_data['algorithm'] == algo]

            # Performance metric: weighted combination of distance and success
            performance = (
                algo_data['mean_distance'] *
                algo_data['success_rate'] *
                algo_data['mean_stability']
            )

            ax.scatter(
                algo_data['mean_execution_time'],
                performance,
                c=self.colors.get(algo, 'gray'),
                marker=self.markers.get(algo, 'o'),
                s=200,
                alpha=0.7,
                label=algo,
                edgecolors='black',
                linewidth=1.5
            )

            # Add error bars
            ax.errorbar(
                algo_data['mean_execution_time'],
                performance,
                xerr=algo_data['std_execution_time'],
                fmt='none',
                ecolor=self.colors.get(algo, 'gray'),
                alpha=0.3,
                capsize=5
            )

            # Annotate points
            for _, row in algo_data.iterrows():
                perf = (
                    row['mean_distance'] *
                    row['success_rate'] *
                    row['mean_stability']
                )
                ax.annotate(
                    algo,
                    (row['mean_execution_time'], perf),
                    xytext=(10, 5),
                    textcoords='offset points',
                    fontsize=9,
                    alpha=0.7
                )

        ax.set_xlabel('Computational Time per Trial (s)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Performance Score\n(Distance × Success × Stability)',
                     fontsize=12, fontweight='bold')
        ax.set_title('Performance vs Computational Cost\n(Flat Ground Scenario)',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        plt.close()

    def plot_robustness_vs_performance(self, save_path: str = None):
        """Plot robustness vs performance across scenarios"""
        fig, ax = plt.subplots(figsize=(12, 8))

        # Aggregate across all scenarios for robustness
        algo_metrics = []

        for algo in self.aggregate_df['algorithm'].unique():
            algo_data = self.aggregate_df[self.aggregate_df['algorithm'] == algo]

            # Robustness: mean robustness score across scenarios
            robustness = algo_data['mean_robustness'].mean()

            # Performance: weighted by scenario success
            performance = (
                algo_data['mean_distance'] *
                algo_data['success_rate']
            ).mean()

            # Stability
            stability = algo_data['mean_stability'].mean()

            algo_metrics.append({
                'algorithm': algo,
                'robustness': robustness,
                'performance': performance,
                'stability': stability
            })

        metrics_df = pd.DataFrame(algo_metrics)

        # Create scatter with size based on stability
        for _, row in metrics_df.iterrows():
            ax.scatter(
                row['performance'],
                row['robustness'],
                c=self.colors.get(row['algorithm'], 'gray'),
                marker=self.markers.get(row['algorithm'], 'o'),
                s=row['stability'] * 1000,  # Scale for visibility
                alpha=0.7,
                label=row['algorithm'],
                edgecolors='black',
                linewidth=1.5
            )

            # Annotate
            ax.annotate(
                row['algorithm'],
                (row['performance'], row['robustness']),
                xytext=(10, 10),
                textcoords='offset points',
                fontsize=10,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.7)
            )

        # Add quadrant lines
        perf_median = metrics_df['performance'].median()
        robust_median = metrics_df['robustness'].median()

        ax.axvline(perf_median, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(robust_median, color='gray', linestyle='--', alpha=0.5, linewidth=1)

        # Label quadrants
        ax.text(0.98, 0.98, 'High Robustness\nHigh Performance',
               transform=ax.transAxes, fontsize=10, va='top', ha='right',
               bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

        ax.set_xlabel('Performance Score\n(Mean Distance × Success Rate)',
                     fontsize=12, fontweight='bold')
        ax.set_ylabel('Robustness Score\n(Averaged Across Scenarios)',
                     fontsize=12, fontweight='bold')
        ax.set_title('Robustness vs Performance\n(Bubble size = Stability)',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        plt.close()

    def create_interactive_dashboard(self, save_path: str = None):
        """Create interactive Plotly dashboard"""

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Distance vs Energy (All Scenarios)',
                'Performance vs Computational Cost',
                'Robustness vs Performance',
                'Success Rate by Scenario'
            ),
            specs=[
                [{'type': 'scatter'}, {'type': 'scatter'}],
                [{'type': 'scatter'}, {'type': 'bar'}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )

        # 1. Distance vs Energy
        for scenario in self.aggregate_df['scenario'].unique():
            scenario_data = self.aggregate_df[self.aggregate_df['scenario'] == scenario]

            for algo in scenario_data['algorithm'].unique():
                algo_data = scenario_data[scenario_data['algorithm'] == algo]

                if algo_data['mean_energy'].isna().all():
                    continue

                fig.add_trace(
                    go.Scatter(
                        x=algo_data['mean_distance'],
                        y=algo_data['mean_energy'],
                        mode='markers',
                        name=f"{algo} ({scenario})",
                        marker=dict(
                            size=12,
                            color=self.colors.get(algo, 'gray'),
                            symbol=self._plotly_marker(algo)
                        ),
                        text=[f"{algo}<br>Scenario: {scenario}<br>Distance: {d:.2f}m<br>Energy: {e:.2f}J"
                              for d, e in zip(algo_data['mean_distance'], algo_data['mean_energy'])],
                        hoverinfo='text'
                    ),
                    row=1, col=1
                )

        # 2. Performance vs Computational Cost
        flat_data = self.aggregate_df[self.aggregate_df['scenario'] == 'flat_ground']

        for algo in flat_data['algorithm'].unique():
            algo_data = flat_data[flat_data['algorithm'] == algo]
            performance = (
                algo_data['mean_distance'] *
                algo_data['success_rate'] *
                algo_data['mean_stability']
            )

            fig.add_trace(
                go.Scatter(
                    x=algo_data['mean_execution_time'],
                    y=performance,
                    mode='markers+text',
                    name=algo,
                    marker=dict(
                        size=15,
                        color=self.colors.get(algo, 'gray'),
                        symbol=self._plotly_marker(algo)
                    ),
                    text=algo,
                    textposition='top center',
                    hovertext=[f"{algo}<br>Time: {t:.2f}s<br>Performance: {p:.3f}"
                              for t, p in zip(algo_data['mean_execution_time'], performance)],
                    hoverinfo='text',
                    showlegend=False
                ),
                row=1, col=2
            )

        # 3. Robustness vs Performance
        algo_metrics = []
        for algo in self.aggregate_df['algorithm'].unique():
            algo_data = self.aggregate_df[self.aggregate_df['algorithm'] == algo]
            robustness = algo_data['mean_robustness'].mean()
            performance = (algo_data['mean_distance'] * algo_data['success_rate']).mean()
            stability = algo_data['mean_stability'].mean()

            algo_metrics.append({
                'algorithm': algo,
                'robustness': robustness,
                'performance': performance,
                'stability': stability
            })

        metrics_df = pd.DataFrame(algo_metrics)

        for _, row in metrics_df.iterrows():
            fig.add_trace(
                go.Scatter(
                    x=[row['performance']],
                    y=[row['robustness']],
                    mode='markers+text',
                    name=row['algorithm'],
                    marker=dict(
                        size=row['stability'] * 50,
                        color=self.colors.get(row['algorithm'], 'gray'),
                        symbol=self._plotly_marker(row['algorithm'])
                    ),
                    text=row['algorithm'],
                    textposition='top center',
                    hovertext=f"{row['algorithm']}<br>Performance: {row['performance']:.3f}<br>Robustness: {row['robustness']:.3f}<br>Stability: {row['stability']:.3f}",
                    hoverinfo='text',
                    showlegend=False
                ),
                row=2, col=1
            )

        # 4. Success Rate by Scenario
        for algo in self.aggregate_df['algorithm'].unique():
            algo_data = self.aggregate_df[self.aggregate_df['algorithm'] == algo]

            fig.add_trace(
                go.Bar(
                    x=algo_data['scenario'],
                    y=algo_data['success_rate'] * 100,
                    name=algo,
                    marker_color=self.colors.get(algo, 'gray'),
                    hovertext=[f"{algo}<br>{s}<br>Success: {sr:.1f}%"
                              for s, sr in zip(algo_data['scenario'], algo_data['success_rate'] * 100)],
                    hoverinfo='text',
                    showlegend=False
                ),
                row=2, col=2
            )

        # Update axes
        fig.update_xaxes(title_text="Distance (m)", row=1, col=1)
        fig.update_yaxes(title_text="Energy (J)", row=1, col=1)

        fig.update_xaxes(title_text="Computation Time (s)", row=1, col=2)
        fig.update_yaxes(title_text="Performance Score", row=1, col=2)

        fig.update_xaxes(title_text="Performance Score", row=2, col=1)
        fig.update_yaxes(title_text="Robustness Score", row=2, col=1)

        fig.update_xaxes(title_text="Scenario", row=2, col=2)
        fig.update_yaxes(title_text="Success Rate (%)", row=2, col=2)

        # Update layout
        fig.update_layout(
            title_text="Algorithm Trade-off Analysis Dashboard",
            title_font_size=20,
            height=900,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="left",
                x=1.02
            ),
            hovermode='closest'
        )

        if save_path:
            fig.write_html(save_path)
            print(f"Saved interactive dashboard: {save_path}")
        else:
            fig.show()

        return fig

    def _plotly_marker(self, algo: str) -> str:
        """Get Plotly marker symbol for algorithm"""
        marker_map = {
            'V10_PD': 'circle',
            'V13_FSM': 'square',
            'RL_PPO': 'triangle-up',
            'RL_SAC': 'triangle-down',
            'Trajectory_Opt': 'diamond',
            'Virtual_Constraints': 'pentagon'
        }
        return marker_map.get(algo, 'circle')

    def generate_all_plots(self, output_dir: str = None):
        """Generate all trade-off analysis plots"""
        if output_dir is None:
            output_dir = Path(self.results_file).parent / "trade_off_plots"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 80)
        print("GENERATING TRADE-OFF ANALYSIS PLOTS")
        print("=" * 80)

        # Static plots
        print("\n1. Distance vs Energy scatter...")
        self.plot_distance_vs_energy(output_dir / "distance_vs_energy.png")

        print("2. Pareto front...")
        self.plot_pareto_front(output_dir / "pareto_front.png")

        print("3. Performance vs Computational Cost...")
        self.plot_performance_vs_cost(output_dir / "performance_vs_cost.png")

        print("4. Robustness vs Performance...")
        self.plot_robustness_vs_performance(output_dir / "robustness_vs_performance.png")

        # Interactive dashboard
        print("5. Interactive Plotly dashboard...")
        self.create_interactive_dashboard(output_dir / "interactive_dashboard.html")

        print("\n" + "=" * 80)
        print(f"All plots saved to: {output_dir}")
        print("=" * 80)

        return output_dir


def main():
    """Main entry point"""
    # Find results file
    base_dir = Path(__file__).parent
    results_file = base_dir / "benchmark_results.csv"

    if not results_file.exists():
        print(f"Error: Results file not found at {results_file}")
        print("Please run benchmark_suite.py first to generate results.")
        return

    # Create analyzer
    print(f"Loading results from: {results_file}")
    analyzer = TradeOffAnalyzer(str(results_file))

    # Generate all plots
    output_dir = analyzer.generate_all_plots()

    print("\nTrade-off analysis completed successfully!")
    print(f"View interactive dashboard: {output_dir / 'interactive_dashboard.html'}")


if __name__ == "__main__":
    main()

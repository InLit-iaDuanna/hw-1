"""
Learning Curves Visualization for RL Algorithm Comparison
Plots training metrics from TensorBoard logs for PPO, SAC, and Imitation Learning
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import glob
from pathlib import Path


class LearningCurvePlotter:
    """Plot and compare learning curves from TensorBoard logs"""

    def __init__(self, log_base_dir="logs"):
        """
        Initialize plotter

        Args:
            log_base_dir: Base directory containing TensorBoard logs
        """
        self.log_base_dir = Path(log_base_dir)
        self.algorithms = ["PPO", "SAC", "Imitation"]
        self.colors = {
            "PPO": "#1f77b4",
            "SAC": "#ff7f0e",
            "Imitation": "#2ca02c"
        }
        self.data = {}

    def load_tensorboard_logs(self, log_dir, tags):
        """
        Load TensorBoard event files

        Args:
            log_dir: Directory containing TensorBoard logs
            tags: List of metric tags to extract

        Returns:
            Dictionary of {tag: (steps, values)}
        """
        event_files = glob.glob(str(log_dir / "**" / "events.out.tfevents.*"), recursive=True)

        if not event_files:
            print(f"Warning: No event files found in {log_dir}")
            return {}

        # Use the most recent event file
        event_file = max(event_files, key=os.path.getmtime)

        ea = EventAccumulator(event_file)
        ea.Reload()

        data = {}
        available_tags = ea.Tags()

        for tag in tags:
            if tag in available_tags.get('scalars', []):
                events = ea.Scalars(tag)
                steps = [e.step for e in events]
                values = [e.value for e in events]
                data[tag] = (np.array(steps), np.array(values))
            else:
                print(f"Warning: Tag '{tag}' not found in {log_dir}")

        return data

    def load_all_algorithms(self):
        """Load logs for all algorithms"""
        tags = [
            'rollout/ep_rew_mean',
            'rollout/ep_len_mean',
            'train/success_rate',
            'rollout/success_rate',
            'time/total_timesteps'
        ]

        for algo in self.algorithms:
            algo_dir = self.log_base_dir / algo.lower()

            if not algo_dir.exists():
                print(f"Warning: Directory not found for {algo}: {algo_dir}")
                continue

            print(f"Loading {algo} logs from {algo_dir}...")
            self.data[algo] = self.load_tensorboard_logs(algo_dir, tags)

    def smooth_curve(self, values, weight=0.9):
        """
        Apply exponential moving average smoothing

        Args:
            values: Array of values to smooth
            weight: Smoothing factor (0-1, higher = more smoothing)

        Returns:
            Smoothed values
        """
        smoothed = []
        last = values[0] if len(values) > 0 else 0

        for value in values:
            smoothed_val = last * weight + (1 - weight) * value
            smoothed.append(smoothed_val)
            last = smoothed_val

        return np.array(smoothed)

    def find_convergence_point(self, steps, values, window=100, threshold=0.05):
        """
        Find convergence point where variance stabilizes

        Args:
            steps: Training steps
            values: Metric values
            window: Window size for computing variance
            threshold: Relative variance threshold for convergence

        Returns:
            Convergence step (or None if not converged)
        """
        if len(values) < window * 2:
            return None

        smoothed = self.smooth_curve(values)

        for i in range(window, len(smoothed) - window):
            recent_var = np.var(smoothed[i-window:i])
            future_var = np.var(smoothed[i:i+window])
            mean_val = np.mean(smoothed[i:i+window])

            if mean_val != 0:
                relative_var = future_var / (abs(mean_val) + 1e-8)
                if relative_var < threshold:
                    return steps[i]

        return None

    def plot_learning_curves(self, save_path="learning_curves.png"):
        """Plot comprehensive learning curves comparison"""
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. Episode Reward
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_metric(
            ax1,
            metric_keys=['rollout/ep_rew_mean'],
            title='Episode Reward vs Training Steps',
            ylabel='Mean Episode Reward',
            smooth=True
        )

        # 2. Episode Length
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_metric(
            ax2,
            metric_keys=['rollout/ep_len_mean'],
            title='Episode Length vs Training Steps',
            ylabel='Mean Episode Length',
            smooth=True
        )

        # 3. Success Rate
        ax3 = fig.add_subplot(gs[1, 0])
        self._plot_metric(
            ax3,
            metric_keys=['train/success_rate', 'rollout/success_rate'],
            title='Success Rate vs Training Steps',
            ylabel='Success Rate',
            smooth=True,
            ylim=[0, 1.05]
        )

        # 4. Sample Efficiency Comparison
        ax4 = fig.add_subplot(gs[1, 1])
        self._plot_sample_efficiency(ax4)

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved learning curves to {save_path}")
        plt.close()

    def _plot_metric(self, ax, metric_keys, title, ylabel, smooth=True, ylim=None):
        """Plot a single metric for all algorithms"""
        convergence_points = {}

        for algo in self.algorithms:
            if algo not in self.data:
                continue

            # Try to find the metric in the available keys
            steps, values = None, None
            for key in metric_keys:
                if key in self.data[algo]:
                    steps, values = self.data[algo][key]
                    break

            if steps is None or values is None:
                continue

            # Plot raw data (lighter)
            ax.plot(steps, values, alpha=0.2, color=self.colors[algo], linewidth=0.5)

            # Plot smoothed data
            if smooth:
                smoothed = self.smooth_curve(values, weight=0.9)
                ax.plot(steps, smoothed, label=algo, color=self.colors[algo], linewidth=2)

                # Find and mark convergence point
                conv_step = self.find_convergence_point(steps, values)
                if conv_step is not None:
                    convergence_points[algo] = conv_step
                    conv_idx = np.argmin(np.abs(steps - conv_step))
                    ax.axvline(conv_step, color=self.colors[algo], linestyle='--',
                             alpha=0.5, linewidth=1)
                    ax.plot(conv_step, smoothed[conv_idx], 'o',
                           color=self.colors[algo], markersize=8)
            else:
                ax.plot(steps, values, label=algo, color=self.colors[algo], linewidth=2)

        ax.set_xlabel('Training Steps', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')

        if ylim:
            ax.set_ylim(ylim)

        # Add convergence annotations
        if convergence_points:
            textstr = "Convergence:\n" + "\n".join(
                [f"{algo}: {int(step):,}" for algo, step in convergence_points.items()]
            )
            ax.text(0.98, 0.02, textstr, transform=ax.transAxes,
                   fontsize=8, verticalalignment='bottom', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    def _plot_sample_efficiency(self, ax):
        """Plot sample efficiency comparison"""
        efficiency_data = {}

        for algo in self.algorithms:
            if algo not in self.data:
                continue

            # Get reward data
            if 'rollout/ep_rew_mean' in self.data[algo]:
                steps, rewards = self.data[algo]['rollout/ep_rew_mean']
                smoothed = self.smooth_curve(rewards, weight=0.9)

                # Calculate area under curve (cumulative reward)
                auc = np.trapz(smoothed, steps)

                # Find steps to reach thresholds
                max_reward = np.max(smoothed)
                thresholds = [0.5, 0.75, 0.9]

                steps_to_threshold = []
                for thresh in thresholds:
                    target = max_reward * thresh
                    idx = np.where(smoothed >= target)[0]
                    if len(idx) > 0:
                        steps_to_threshold.append(steps[idx[0]])
                    else:
                        steps_to_threshold.append(steps[-1])

                efficiency_data[algo] = {
                    'auc': auc,
                    'steps_to_threshold': steps_to_threshold,
                    'final_reward': smoothed[-1],
                    'max_steps': steps[-1]
                }

        if not efficiency_data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            return

        # Plot steps to reach performance thresholds
        x = np.arange(len(thresholds))
        width = 0.25

        for i, algo in enumerate(self.algorithms):
            if algo in efficiency_data:
                steps = efficiency_data[algo]['steps_to_threshold']
                offset = (i - 1) * width
                ax.bar(x + offset, steps, width, label=algo,
                      color=self.colors[algo], alpha=0.8)

        ax.set_xlabel('Performance Threshold (% of Max)', fontsize=11)
        ax.set_ylabel('Steps Required', fontsize=11)
        ax.set_title('Sample Efficiency Comparison', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'{int(t*100)}%' for t in thresholds])
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')

        # Add efficiency metrics as text
        textstr = "Efficiency Metrics:\n"
        for algo in self.algorithms:
            if algo in efficiency_data:
                final = efficiency_data[algo]['final_reward']
                steps = efficiency_data[algo]['max_steps']
                textstr += f"{algo}: {final:.1f} @ {int(steps):,}\n"

        ax.text(0.98, 0.98, textstr, transform=ax.transAxes,
               fontsize=8, verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    def plot_individual_curves(self, save_dir="individual_curves"):
        """Plot individual detailed curves for each algorithm"""
        os.makedirs(save_dir, exist_ok=True)

        for algo in self.algorithms:
            if algo not in self.data or not self.data[algo]:
                continue

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f'{algo} Training Metrics', fontsize=14, fontweight='bold')

            metrics = [
                ('rollout/ep_rew_mean', 'Episode Reward', axes[0, 0]),
                ('rollout/ep_len_mean', 'Episode Length', axes[0, 1]),
                ('train/success_rate', 'Success Rate (Train)', axes[1, 0]),
                ('rollout/success_rate', 'Success Rate (Rollout)', axes[1, 1])
            ]

            for metric_key, title, ax in metrics:
                if metric_key in self.data[algo]:
                    steps, values = self.data[algo][metric_key]

                    # Raw data
                    ax.plot(steps, values, alpha=0.3, color=self.colors[algo],
                           linewidth=0.5, label='Raw')

                    # Smoothed
                    smoothed = self.smooth_curve(values, weight=0.9)
                    ax.plot(steps, smoothed, color=self.colors[algo],
                           linewidth=2, label='Smoothed')

                    # Convergence point
                    conv_step = self.find_convergence_point(steps, values)
                    if conv_step is not None:
                        conv_idx = np.argmin(np.abs(steps - conv_step))
                        ax.axvline(conv_step, color='red', linestyle='--',
                                 alpha=0.5, label=f'Conv: {int(conv_step):,}')
                        ax.plot(conv_step, smoothed[conv_idx], 'ro', markersize=8)

                    ax.set_xlabel('Training Steps')
                    ax.set_ylabel(title)
                    ax.set_title(title)
                    ax.legend(loc='best')
                    ax.grid(True, alpha=0.3)
                else:
                    ax.text(0.5, 0.5, f'{metric_key}\nnot available',
                           ha='center', va='center', transform=ax.transAxes)
                    ax.set_title(title)

            plt.tight_layout()
            save_path = os.path.join(save_dir, f'{algo.lower()}_metrics.png')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved {algo} individual curves to {save_path}")
            plt.close()

    def generate_summary_stats(self, save_path="training_summary.txt"):
        """Generate text summary of training statistics"""
        with open(save_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("RL ALGORITHM TRAINING COMPARISON SUMMARY\n")
            f.write("=" * 60 + "\n\n")

            for algo in self.algorithms:
                if algo not in self.data or not self.data[algo]:
                    continue

                f.write(f"\n{algo}\n")
                f.write("-" * 40 + "\n")

                # Episode Reward
                if 'rollout/ep_rew_mean' in self.data[algo]:
                    steps, rewards = self.data[algo]['rollout/ep_rew_mean']
                    smoothed = self.smooth_curve(rewards, weight=0.9)
                    conv_step = self.find_convergence_point(steps, rewards)

                    f.write(f"Episode Reward:\n")
                    f.write(f"  Initial:    {smoothed[0]:.2f}\n")
                    f.write(f"  Final:      {smoothed[-1]:.2f}\n")
                    f.write(f"  Max:        {np.max(smoothed):.2f}\n")
                    f.write(f"  Improvement: {smoothed[-1] - smoothed[0]:.2f}\n")
                    if conv_step:
                        f.write(f"  Converged at: {int(conv_step):,} steps\n")

                # Episode Length
                if 'rollout/ep_len_mean' in self.data[algo]:
                    steps, lengths = self.data[algo]['rollout/ep_len_mean']
                    smoothed = self.smooth_curve(lengths, weight=0.9)

                    f.write(f"\nEpisode Length:\n")
                    f.write(f"  Initial:    {smoothed[0]:.2f}\n")
                    f.write(f"  Final:      {smoothed[-1]:.2f}\n")
                    f.write(f"  Mean:       {np.mean(smoothed):.2f}\n")

                # Success Rate
                for key in ['train/success_rate', 'rollout/success_rate']:
                    if key in self.data[algo]:
                        steps, success = self.data[algo][key]
                        smoothed = self.smooth_curve(success, weight=0.9)

                        f.write(f"\nSuccess Rate ({key.split('/')[0]}):\n")
                        f.write(f"  Initial:    {smoothed[0]:.2%}\n")
                        f.write(f"  Final:      {smoothed[-1]:.2%}\n")
                        f.write(f"  Max:        {np.max(smoothed):.2%}\n")
                        break

                # Total training steps
                if 'rollout/ep_rew_mean' in self.data[algo]:
                    steps, _ = self.data[algo]['rollout/ep_rew_mean']
                    f.write(f"\nTotal Training Steps: {int(steps[-1]):,}\n")

                f.write("\n")

        print(f"Saved training summary to {save_path}")


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Plot RL learning curves')
    parser.add_argument('--log-dir', type=str, default='logs',
                       help='Base directory containing TensorBoard logs')
    parser.add_argument('--output', type=str, default='learning_curves.png',
                       help='Output path for main comparison plot')
    parser.add_argument('--individual', action='store_true',
                       help='Also generate individual plots for each algorithm')
    parser.add_argument('--summary', type=str, default='training_summary.txt',
                       help='Output path for text summary')

    args = parser.parse_args()

    # Initialize plotter
    plotter = LearningCurvePlotter(log_base_dir=args.log_dir)

    # Load all algorithm data
    plotter.load_all_algorithms()

    # Generate main comparison plot
    plotter.plot_learning_curves(save_path=args.output)

    # Generate individual plots if requested
    if args.individual:
        plotter.plot_individual_curves()

    # Generate summary statistics
    plotter.generate_summary_stats(save_path=args.summary)

    print("\nDone! Generated:")
    print(f"  - Main comparison: {args.output}")
    if args.individual:
        print(f"  - Individual plots: individual_curves/")
    print(f"  - Summary stats: {args.summary}")


if __name__ == "__main__":
    main()

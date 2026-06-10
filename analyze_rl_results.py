#!/usr/bin/env python3
"""
Residual RL Performance Analyzer
分析训练结果并生成可视化报告
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def load_results():
    """加载所有训练结果"""
    base_path = Path(__file__).parent

    results = {}

    # Zero residual test
    zero_path = base_path / "logs/residual_rl_v2/test_zero_residual_v2_report.json"
    if zero_path.exists():
        with open(zero_path) as f:
            results['zero'] = json.load(f)

    # 100k training
    train_path = base_path / "logs/residual_rl_v2/train_sanity_100k_report.json"
    if train_path.exists():
        with open(train_path) as f:
            results['train'] = json.load(f)

    # Residual sweep
    sweep_path = base_path / "logs/residual_rl_v2/residual_sweep_results.json"
    if sweep_path.exists():
        with open(sweep_path) as f:
            results['sweep'] = json.load(f)

    return results

def print_summary(results):
    """打印结果摘要"""
    print("=" * 80)
    print("Residual RL V2 - 完整性能分析")
    print("=" * 80)
    print()

    # Zero residual
    if 'zero' in results:
        zero = results['zero']
        print("【1】Zero Residual Identity Test")
        print("-" * 80)
        print(f"  基线距离: {zero['baseline_distance']:.3f}m")
        print(f"  测试距离: {zero['statistics']['avg_distance']:.3f}m ± {zero['statistics']['std_distance']:.6f}m")
        print(f"  成功率: {zero['statistics']['success_rate']*100:.0f}%")
        print(f"  诊断: {zero['diagnosis']}")
        print()

    # Training
    if 'train' in results:
        train = results['train']
        print("【2】100k PPO Training Results")
        print("-" * 80)
        print(f"  Baseline: {train['baseline']['mean_distance_m']:.3f}m")
        print(f"  Final: {train['final_eval']['mean_distance_m']:.3f}m")

        improvement = (train['final_eval']['mean_distance_m'] - train['baseline']['mean_distance_m']) / train['baseline']['mean_distance_m'] * 100
        print(f"  提升: +{improvement:.2f}%")
        print(f"  成功率: {train['final_eval']['success_rate']*100:.0f}%")
        print()

        print("  训练曲线:")
        for eval_point in train['eval_history']:
            ts = eval_point['timestep']
            dist = eval_point['mean_distance_m']
            imp = (dist - train['baseline']['mean_distance_m']) / train['baseline']['mean_distance_m'] * 100
            print(f"    {ts:6d} steps: {dist:.3f}m (+{imp:+.2f}%)")
        print()

    # Sweep
    if 'sweep' in results:
        sweep = results['sweep']
        print("【3】Residual Sweep Results")
        print("-" * 80)
        best = sweep['best_result']
        print(f"  最佳策略:")
        print(f"    Action: [{best['left_action']:.1f}, {best['right_action']:.1f}]")
        print(f"    Scale: {best['residual_scale']:.2f}")
        print(f"    距离: {best['mean_distance_m']:.3f}m")
        print(f"    提升: +{best['improvement_pct']:.2f}%")
        print()

        print(f"  扫描统计:")
        print(f"    总样本数: {sweep['num_results']}")
        print(f"    有效样本: {sweep['num_good_results']} (>{sweep['pass_improvement_pct']:.0f}% 提升)")
        print()

        # Top 5
        print("  Top 5 策略:")
        sorted_results = sorted(sweep['all_results'],
                              key=lambda x: x['mean_distance_m'],
                              reverse=True)[:5]
        for i, r in enumerate(sorted_results, 1):
            print(f"    {i}. [{r['left_action']:+.1f}, {r['right_action']:+.1f}] "
                  f"@ scale={r['residual_scale']:.2f} → "
                  f"{r['mean_distance_m']:.3f}m (+{r['improvement_pct']:.2f}%)")
        print()

    print("=" * 80)

def create_visualizations(results, output_dir="analysis_output"):
    """生成可视化图表"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Residual RL V2 - 完整性能分析', fontsize=16, fontweight='bold')

    # 1. Training curve
    if 'train' in results:
        ax = axes[0, 0]
        train = results['train']

        timesteps = [0] + [e['timestep'] for e in train['eval_history']]
        distances = [train['baseline']['mean_distance_m']] + \
                   [e['mean_distance_m'] for e in train['eval_history']]

        ax.plot(timesteps, distances, 'o-', linewidth=2, markersize=8, label='PPO Training')
        ax.axhline(train['baseline']['mean_distance_m'], color='r',
                  linestyle='--', label='Baseline (V13.7)')
        ax.axhline(train['prior_eval']['mean_distance_m'], color='g',
                  linestyle='--', label='Prior Action [0.5, 1.0]')

        ax.set_xlabel('Training Steps', fontsize=12)
        ax.set_ylabel('Distance (m)', fontsize=12)
        ax.set_title('Training Curve (100k PPO)', fontsize=13, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    # 2. Sweep heatmap
    if 'sweep' in results:
        ax = axes[0, 1]
        sweep = results['sweep']

        # 准备数据
        scales = sorted(list(set(r['residual_scale'] for r in sweep['all_results'])))
        actions_left = sorted(list(set(r['left_action'] for r in sweep['all_results'])))

        # 创建热力图数据 (仅显示 left_action vs scale, right_action=1.0)
        data = np.zeros((len(scales), len(actions_left)))
        for r in sweep['all_results']:
            if r['right_action'] == 1.0:  # 筛选 right_action=1.0
                i = scales.index(r['residual_scale'])
                j = actions_left.index(r['left_action'])
                data[i, j] = r['improvement_pct']

        im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=-5, vmax=8)
        ax.set_xticks(range(len(actions_left)))
        ax.set_xticklabels([f'{a:.1f}' for a in actions_left])
        ax.set_yticks(range(len(scales)))
        ax.set_yticklabels([f'{s:.2f}' for s in scales])
        ax.set_xlabel('Left Action', fontsize=12)
        ax.set_ylabel('Residual Scale', fontsize=12)
        ax.set_title('Sweep Heatmap (right=1.0)\nImprovement %',
                    fontsize=13, fontweight='bold')
        plt.colorbar(im, ax=ax)

    # 3. Performance comparison
    ax = axes[1, 0]

    methods = []
    distances = []
    colors = []

    if 'zero' in results:
        methods.append('Baseline\n(V13.7)')
        distances.append(results['zero']['statistics']['avg_distance'])
        colors.append('#3498db')

    if 'train' in results:
        methods.append('100k PPO\nBest')
        distances.append(results['train']['final_eval']['mean_distance_m'])
        colors.append('#e74c3c')

        methods.append('Prior Action\n[0.5, 1.0]')
        distances.append(results['train']['prior_eval']['mean_distance_m'])
        colors.append('#2ecc71')

    if 'sweep' in results:
        methods.append('Sweep Best\n[0.5, 1.0]')
        distances.append(results['sweep']['best_result']['mean_distance_m'])
        colors.append('#f39c12')

    bars = ax.bar(methods, distances, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Distance (m)', fontsize=12)
    ax.set_title('Performance Comparison', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar, dist in zip(bars, distances):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{dist:.3f}m',
               ha='center', va='bottom', fontweight='bold')

    # 4. Improvement distribution
    if 'sweep' in results:
        ax = axes[1, 1]
        sweep = results['sweep']

        improvements = [r['improvement_pct'] for r in sweep['all_results']
                       if r['success_rate'] == 1.0]

        ax.hist(improvements, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax.axvline(0, color='r', linestyle='--', linewidth=2, label='Baseline')
        ax.axvline(results['sweep']['best_result']['improvement_pct'],
                  color='g', linestyle='--', linewidth=2, label='Best')

        ax.set_xlabel('Improvement (%)', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Improvement Distribution (Successful Runs)',
                    fontsize=13, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_file = output_path / "residual_rl_v2_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[OK] Visualization saved: {output_file}")

    return output_file

def main():
    print("Loading training results...")
    results = load_results()

    if not results:
        print("[ERROR] No training result files found")
        return

    print(f"[OK] Loaded {len(results)} result files")
    print()

    # 打印摘要
    print_summary(results)

    # 生成可视化
    print("Generating visualizations...")
    output_file = create_visualizations(results)

    print()
    print("=" * 80)
    print("Analysis Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

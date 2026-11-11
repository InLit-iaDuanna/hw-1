"""对比不同优化算法的性能。

在相同问题上运行多个优化器，绘制收敛曲线和性能对比图。

Example:
    python compare_optimizers.py --config configs/v137_fsm_timing.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent

sys.path.insert(0, str(HW1_ROOT))

from run_optimization import (
    build_evaluate_func,
    build_objective,
    build_parameter_space,
    load_config,
)


def run_all_optimizers(config_path: Path, output_dir: Path, budget: int = 50):
    """运行所有优化器并对比性能。

    Args:
        config_path: 配置文件路径
        output_dir: 输出目录
        budget: 每个优化器的评估预算
    """
    print(f"加载配置: {config_path}")
    config = load_config(config_path)

    print("构建参数空间和目标函数...")
    param_space = build_parameter_space(config)
    objective = build_objective(config)
    evaluate_func = build_evaluate_func(config)

    # 优化器配置
    optimizers_config = [
        ("bayesian", "贝叶斯优化"),
        ("genetic", "遗传算法"),
        ("random", "随机搜索"),
    ]

    results = {}
    times = {}

    # 运行每个优化器
    for optimizer_name, display_name in optimizers_config:
        print(f"\n{'=' * 60}")
        print(f"运行 {display_name} ({optimizer_name})")
        print("=" * 60)

        start_time = time.time()

        try:
            if optimizer_name == "bayesian":
                from auto_optimization.optimizers import BayesianOptimizer

                optimizer = BayesianOptimizer(
                    param_space=param_space,
                    objective=objective,
                    evaluate_func=evaluate_func,
                    n_initial_points=min(10, budget // 5),
                )
                result = optimizer.optimize(budget=budget, verbose=True)

            elif optimizer_name == "genetic":
                from auto_optimization.optimizers import GeneticAlgorithm

                # 调整代数以匹配预算
                population_size = 20
                n_generations = budget // population_size

                optimizer = GeneticAlgorithm(
                    param_space=param_space,
                    objective=objective,
                    evaluate_func=evaluate_func,
                    population_size=population_size,
                    n_generations=n_generations,
                )
                result = optimizer.optimize(verbose=True)

            elif optimizer_name == "random":
                from auto_optimization.optimizers import RandomSearch

                optimizer = RandomSearch(
                    param_space=param_space,
                    objective=objective,
                    evaluate_func=evaluate_func,
                )
                result = optimizer.optimize(budget=budget, verbose=True)

            else:
                continue

            elapsed = time.time() - start_time
            times[optimizer_name] = elapsed
            results[optimizer_name] = {
                "result": result,
                "display_name": display_name,
            }

            print(f"  完成！用时: {elapsed:.2f}s")
            print(f"  最优值: {result.best_value:.6f}")

        except Exception as e:
            print(f"  错误: {e}")
            continue

    # 保存结果
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存详细结果
    for optimizer_name, data in results.items():
        result = data["result"]
        result_path = output_dir / f"{optimizer_name}_{timestamp}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_params": result.best_params,
                    "best_value": result.best_value,
                    "n_evaluations": result.n_evaluations,
                    "convergence_curve": result.convergence_curve,
                    "all_values": result.all_values,
                    "metadata": result.metadata,
                },
                f,
                indent=2,
            )

    # 绘制对比图
    plot_comparison(results, times, output_dir / f"comparison_{timestamp}.png")

    # 打印汇总表
    print_summary_table(results, times)


def plot_comparison(results: dict, times: dict, output_path: Path):
    """绘制优化器对比图。

    Args:
        results: 优化结果字典
        times: 运行时间字典
        output_path: 输出图像路径
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 收敛曲线
    ax1 = axes[0]
    for optimizer_name, data in results.items():
        result = data["result"]
        display_name = data["display_name"]
        curve = result.convergence_curve
        ax1.plot(
            range(1, len(curve) + 1),
            curve,
            marker="o",
            markersize=3,
            label=display_name,
        )

    ax1.set_xlabel("评估次数", fontsize=12)
    ax1.set_ylabel("最优值", fontsize=12)
    ax1.set_title("收敛曲线对比", fontsize=14, fontweight="bold")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # 最终性能对比
    ax2 = axes[1]
    optimizer_names = [data["display_name"] for data in results.values()]
    best_values = [data["result"].best_value for data in results.values()]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    bars = ax2.bar(optimizer_names, best_values, color=colors[: len(optimizer_names)])
    ax2.set_ylabel("最优值", fontsize=12)
    ax2.set_title("最终性能对比", fontsize=14, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    # 添加数值标签
    for bar, value in zip(bars, best_values):
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{value:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n对比图已保存到: {output_path}")


def print_summary_table(results: dict, times: dict):
    """打印汇总表。

    Args:
        results: 优化结果字典
        times: 运行时间字典
    """
    print("\n" + "=" * 80)
    print("优化器性能汇总")
    print("=" * 80)
    print(f"{'优化器':<15} {'最优值':<12} {'评估次数':<12} {'运行时间(s)':<15}")
    print("-" * 80)

    for optimizer_name, data in results.items():
        result = data["result"]
        display_name = data["display_name"]
        runtime = times.get(optimizer_name, 0)

        print(
            f"{display_name:<15} "
            f"{result.best_value:<12.6f} "
            f"{result.n_evaluations:<12} "
            f"{runtime:<15.2f}"
        )

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="对比优化算法性能")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="配置文件路径 (YAML)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=50,
        help="每个优化器的评估预算",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="auto_optimization/results/comparison",
        help="输出目录",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    run_all_optimizers(config_path, output_dir, args.budget)


if __name__ == "__main__":
    main()

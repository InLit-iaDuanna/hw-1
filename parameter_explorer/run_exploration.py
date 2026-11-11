"""参数空间探索主流程。

整合采样、建模、分析、优化和可视化的完整工作流。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

try:
    from .optimizer import (
        BayesianOptimizer,
        GeneticAlgorithmOptimizer,
        MultiObjectiveOptimizer,
    )
    from .response_surface import build_response_surface
    from .sensitivity_analyzer import SensitivityAnalyzer
    from .space_sampler import ParameterRange, SpaceSampler
    from .visualizer import ParameterVisualizer
except ImportError:
    from optimizer import (
        BayesianOptimizer,
        GeneticAlgorithmOptimizer,
        MultiObjectiveOptimizer,
    )
    from response_surface import build_response_surface
    from sensitivity_analyzer import SensitivityAnalyzer
    from space_sampler import ParameterRange, SpaceSampler
    from visualizer import ParameterVisualizer


class ParameterExplorer:
    """参数空间探索器（主接口）。"""

    def __init__(
        self,
        param_ranges: list[ParameterRange],
        output_dir: Path | str,
        objective_func: Callable[[dict[str, float]], float],
        verbose: bool = True,
    ):
        """
        Args:
            param_ranges: 参数范围列表
            output_dir: 输出目录
            objective_func: 目标函数（接受参数字典，返回标量）
            verbose: 是否打印进度
        """
        self.param_ranges = param_ranges
        self.param_names = [p.name for p in param_ranges]
        self.param_bounds = [(p.min_value, p.max_value) for p in param_ranges]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.objective_func = objective_func
        self.verbose = verbose

        # 初始化组件
        self.sampler = SpaceSampler(param_ranges)
        self.visualizer = ParameterVisualizer(output_dir=self.output_dir)
        self.sensitivity_analyzer = SensitivityAnalyzer(
            self.param_names, self.param_bounds
        )

        # 存储结果
        self.samples: np.ndarray | None = None
        self.objectives: np.ndarray | None = None
        self.response_surface: Any = None

    def initial_sampling(
        self, method: str = "lhs", n_samples: int = 50, seed: int | None = None
    ) -> dict[str, Any]:
        """初始采样。

        Args:
            method: 采样方法 ("grid", "random", "lhs", "sobol")
            n_samples: 采样数（grid 模式下是每维采样数）
            seed: 随机种子

        Returns:
            采样结果字典
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Initial Sampling: {method.upper()}")
            print(f"{'='*60}")

        if method == "grid":
            self.samples, param_dicts = self.sampler.grid_sample(n_per_dim=n_samples)
        elif method == "random":
            self.samples, param_dicts = self.sampler.random_sample(
                n_samples=n_samples, seed=seed
            )
        elif method == "lhs":
            self.samples, param_dicts = self.sampler.lhs_sample(
                n_samples=n_samples, seed=seed
            )
        elif method == "sobol":
            self.samples, param_dicts = self.sampler.sobol_sample(
                n_samples=n_samples, seed=seed
            )
        else:
            raise ValueError(f"Unknown sampling method: {method}")

        # 评估目标函数
        self.objectives = np.array([self.objective_func(pd) for pd in param_dicts])

        if self.verbose:
            print(f"Sampled {len(self.samples)} points")
            print(
                f"Objective range: [{self.objectives.min():.4f}, {self.objectives.max():.4f}]"
            )
            print(
                f"Mean: {self.objectives.mean():.4f}, Std: {self.objectives.std():.4f}"
            )

        # 保存结果
        results = {
            "method": method,
            "n_samples": len(self.samples),
            "samples": self.samples.tolist(),
            "objectives": self.objectives.tolist(),
            "param_dicts": param_dicts,
        }

        with open(
            self.output_dir / "initial_sampling.json", "w", encoding="utf-8"
        ) as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 可视化参数分布
        self.visualizer.plot_parameter_distribution(
            self.samples, self.param_names, filename=f"param_distribution_{method}.png"
        )

        return results

    def fit_response_surface(self, method: str = "gp", **kwargs: Any) -> None:
        """拟合响应曲面。

        Args:
            method: 方法类型 ("gp", "polynomial", "rbf", "ensemble")
            **kwargs: 传递给模型的参数
        """
        if self.samples is None or self.objectives is None:
            raise RuntimeError("Must run initial_sampling first")

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Fitting Response Surface: {method.upper()}")
            print(f"{'='*60}")

        self.response_surface = build_response_surface(
            self.samples, self.objectives, method=method, **kwargs
        )

        if self.verbose:
            print(f"Response surface fitted with {len(self.samples)} samples")

    def sensitivity_analysis(
        self,
        method: str = "morris",
        n_samples: int = 512,
        calc_second_order: bool = False,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """灵敏度分析。

        Args:
            method: 方法类型 ("sobol", "morris")
            n_samples: 采样数
            calc_second_order: 是否计算二阶交互（仅 Sobol）
            seed: 随机种子

        Returns:
            灵敏度分析结果
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Sensitivity Analysis: {method.upper()}")
            print(f"{'='*60}")

        if method == "sobol":
            results = self.sensitivity_analyzer.sobol_analysis(
                self.objective_func,
                n_samples=n_samples,
                calc_second_order=calc_second_order,
                seed=seed,
            )
            # 可视化
            self.visualizer.plot_sensitivity_bar(
                self.param_names,
                results["ST"],
                errors=results["ST_conf"],
                ylabel="Total Sobol Index",
                title="Parameter Sensitivity (Sobol)",
                filename="sensitivity_sobol.png",
            )

            if calc_second_order:
                interaction_matrix = self.sensitivity_analyzer.interaction_matrix(
                    results
                )
                if interaction_matrix is not None:
                    self.visualizer.plot_interaction_heatmap(
                        interaction_matrix,
                        self.param_names,
                        filename="interaction_heatmap.png",
                    )

        elif method == "morris":
            results = self.sensitivity_analyzer.morris_screening(
                self.objective_func, n_trajectories=n_samples, seed=seed
            )
            # 可视化
            self.visualizer.plot_sensitivity_bar(
                self.param_names,
                results["mu_star"],
                errors=results["mu_star_conf"],
                ylabel="Morris μ*",
                title="Parameter Sensitivity (Morris)",
                filename="sensitivity_morris.png",
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        # 参数排名
        ranked = self.sensitivity_analyzer.rank_parameters(results, method=method)
        if self.verbose:
            print("\nParameter Ranking:")
            for i, (name, score) in enumerate(ranked, 1):
                print(f"  {i}. {name}: {score:.4f}")

        # 保存结果
        results["ranked_params"] = ranked
        with open(
            self.output_dir / f"sensitivity_{method}.json", "w", encoding="utf-8"
        ) as f:
            # 转换 numpy 数组为列表
            serializable_results = {
                k: (v.tolist() if isinstance(v, np.ndarray) else v)
                for k, v in results.items()
            }
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        return results

    def optimize(
        self,
        method: str = "bayesian",
        n_iterations: int = 50,
        seed: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """参数优化。

        Args:
            method: 优化方法 ("bayesian", "genetic", "nelder_mead")
            n_iterations: 迭代次数
            seed: 随机种子
            **kwargs: 传递给优化器的参数

        Returns:
            优化结果
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Optimization: {method.upper()}")
            print(f"{'='*60}")

        if method == "bayesian":
            optimizer = BayesianOptimizer(
                self.param_names, self.param_bounds, random_state=seed
            )
            results = optimizer.optimize(
                self.objective_func,
                n_iterations=n_iterations,
                verbose=self.verbose,
                **kwargs,
            )

            # 绘制优化历史
            all_values = np.array(results["all_values"])
            best_values = np.maximum.accumulate(all_values)
            iterations = np.arange(len(all_values))

            self.visualizer.plot_optimization_history(
                iterations,
                best_values,
                all_values,
                title="Bayesian Optimization History",
                filename="optimization_bayesian.png",
            )

        elif method == "genetic":
            optimizer = GeneticAlgorithmOptimizer(
                self.param_names, self.param_bounds, seed=seed
            )
            results = optimizer.optimize(
                self.objective_func,
                max_generations=n_iterations,
                verbose=self.verbose,
                **kwargs,
            )

        else:
            raise ValueError(f"Unknown method: {method}")

        if self.verbose:
            print("\nOptimization completed!")
            print(f"Best value: {results['best_value']:.4f}")
            print("Best parameters:")
            for name, value in results["best_params"].items():
                print(f"  {name}: {value:.6f}")

        # 保存结果
        with open(
            self.output_dir / f"optimization_{method}.json", "w", encoding="utf-8"
        ) as f:
            serializable_results = {
                k: (v.tolist() if isinstance(v, np.ndarray) else v)
                for k, v in results.items()
            }
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        return results

    def multi_objective_optimize(
        self,
        objective_funcs: list[Callable[[dict[str, float]], float]],
        objective_names: list[str],
        maximize: list[bool],
        n_generations: int = 100,
        population_size: int = 100,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """多目标优化。

        Args:
            objective_funcs: 目标函数列表
            objective_names: 目标名称列表
            maximize: 是否最大化（每个目标）
            n_generations: 代数
            population_size: 种群大小
            seed: 随机种子

        Returns:
            优化结果（包含 Pareto 前沿）
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print("Multi-Objective Optimization")
            print(f"{'='*60}")

        optimizer = MultiObjectiveOptimizer(
            self.param_names,
            self.param_bounds,
            n_objectives=len(objective_funcs),
            population_size=population_size,
            seed=seed,
        )

        results = optimizer.optimize(
            objective_funcs,
            maximize=maximize,
            n_generations=n_generations,
            verbose=self.verbose,
        )

        # 可视化 Pareto 前沿（仅支持 2 个目标）
        if len(objective_funcs) == 2:
            self.visualizer.plot_pareto_front(
                results["pareto_objectives"],
                obj1_name=objective_names[0],
                obj2_name=objective_names[1],
                filename="pareto_front.png",
            )

        if self.verbose:
            print(f"\nFound {results['n_solutions']} Pareto-optimal solutions")

        # 保存结果
        with open(
            self.output_dir / "optimization_multiobjective.json", "w", encoding="utf-8"
        ) as f:
            serializable_results = {
                k: (v.tolist() if isinstance(v, np.ndarray) else v)
                for k, v in results.items()
            }
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        return results

    def visualize_2d_slices(
        self, fixed_params: dict[str, float] | None = None, n_points: int = 100
    ) -> None:
        """可视化 2D 参数切片。

        Args:
            fixed_params: 固定参数值（未指定的参数使用最优值或中值）
            n_points: 每个切片的点数
        """
        if self.response_surface is None:
            raise RuntimeError("Must fit response surface first")

        if self.verbose:
            print(f"\n{'='*60}")
            print("Generating 2D Slices")
            print(f"{'='*60}")

        # 确定固定参数值
        if fixed_params is None:
            fixed_params = {}

        # 未指定的参数使用最优值或中值
        best_idx = np.argmax(self.objectives) if self.objectives is not None else 0
        base_params = (
            {name: self.samples[best_idx, i] for i, name in enumerate(self.param_names)}
            if self.samples is not None
            else {
                pr.name: (pr.min_value + pr.max_value) / 2 for pr in self.param_ranges
            }
        )
        base_params.update(fixed_params)

        # 为每个参数生成切片
        for i, param_range in enumerate(self.param_ranges):
            param_name = param_range.name

            # 生成参数值
            param_values = param_range.sample(n_points, method="linspace")

            # 构造样本矩阵
            X_slice = np.zeros((n_points, len(self.param_names)))
            for j, name in enumerate(self.param_names):
                if name == param_name:
                    X_slice[:, j] = param_values
                else:
                    X_slice[:, j] = base_params[name]

            # 预测
            y_pred = self.response_surface.predict(X_slice)

            # 提取实际采样点（在该参数维度附近）
            if self.samples is not None and self.objectives is not None:
                tolerance = (param_range.max_value - param_range.min_value) * 0.1
                mask = np.abs(self.samples[:, i] - base_params[param_name]) < tolerance
                samples_x = self.samples[mask, i] if mask.any() else None
                samples_y = self.objectives[mask] if mask.any() else None
            else:
                samples_x, samples_y = None, None

            # 绘制
            self.visualizer.plot_2d_slice(
                param_name,
                param_values,
                y_pred,
                samples_x=samples_x,
                samples_y=samples_y,
                filename=f"slice_2d_{param_name}.png",
            )

    def visualize_3d_surface(
        self,
        param1_name: str,
        param2_name: str,
        fixed_params: dict[str, float] | None = None,
        n_points: int = 50,
    ) -> None:
        """可视化 3D 响应曲面。

        Args:
            param1_name: 第一个参数名称
            param2_name: 第二个参数名称
            fixed_params: 固定参数值
            n_points: 每个维度的点数
        """
        if self.response_surface is None:
            raise RuntimeError("Must fit response surface first")

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Generating 3D Surface: {param1_name} vs {param2_name}")
            print(f"{'='*60}")

        # 找到参数索引
        idx1 = self.param_names.index(param1_name)
        idx2 = self.param_names.index(param2_name)
        param_range1 = self.param_ranges[idx1]
        param_range2 = self.param_ranges[idx2]

        # 确定固定参数值
        if fixed_params is None:
            fixed_params = {}
        best_idx = np.argmax(self.objectives) if self.objectives is not None else 0
        base_params = (
            {name: self.samples[best_idx, i] for i, name in enumerate(self.param_names)}
            if self.samples is not None
            else {
                pr.name: (pr.min_value + pr.max_value) / 2 for pr in self.param_ranges
            }
        )
        base_params.update(fixed_params)

        # 生成网格
        p1_values = param_range1.sample(n_points, method="linspace")
        p2_values = param_range2.sample(n_points, method="linspace")
        P1, P2 = np.meshgrid(p1_values, p2_values, indexing="ij")

        # 构造样本矩阵
        X_grid = np.zeros((n_points * n_points, len(self.param_names)))
        for i, name in enumerate(self.param_names):
            if name == param1_name:
                X_grid[:, i] = P1.ravel()
            elif name == param2_name:
                X_grid[:, i] = P2.ravel()
            else:
                X_grid[:, i] = base_params[name]

        # 预测
        y_pred = self.response_surface.predict(X_grid).reshape(n_points, n_points)

        # 提取实际采样点
        if self.samples is not None and self.objectives is not None:
            samples_x = self.samples[:, idx1]
            samples_y = self.samples[:, idx2]
            samples_z = self.objectives
        else:
            samples_x, samples_y, samples_z = None, None, None

        # 绘制 3D 曲面
        self.visualizer.plot_3d_surface(
            param1_name,
            param2_name,
            p1_values,
            p2_values,
            y_pred,
            samples_x=samples_x,
            samples_y=samples_y,
            samples_z=samples_z,
            filename=f"surface_3d_{param1_name}_{param2_name}.png",
        )

        # 绘制等高线
        self.visualizer.plot_contour(
            param1_name,
            param2_name,
            p1_values,
            p2_values,
            y_pred,
            samples_x=samples_x,
            samples_y=samples_y,
            filename=f"contour_{param1_name}_{param2_name}.png",
        )

    def generate_report(self) -> str:
        """生成探索报告。

        Returns:
            报告文本
        """
        report = []
        report.append("=" * 80)
        report.append("PARAMETER SPACE EXPLORATION REPORT")
        report.append("=" * 80)
        report.append("")

        # 参数信息
        report.append("Parameters:")
        for pr in self.param_ranges:
            report.append(f"  - {pr.name}: [{pr.min_value:.4f}, {pr.max_value:.4f}]")
        report.append("")

        # 采样信息
        if self.samples is not None:
            report.append(f"Samples: {len(self.samples)}")
            report.append(
                f"Objective range: [{self.objectives.min():.4f}, {self.objectives.max():.4f}]"
            )
            report.append(
                f"Mean: {self.objectives.mean():.4f}, Std: {self.objectives.std():.4f}"
            )
            report.append("")

        # 最优参数
        if self.objectives is not None:
            best_idx = np.argmax(self.objectives)
            report.append("Best Parameters:")
            for i, name in enumerate(self.param_names):
                report.append(f"  {name}: {self.samples[best_idx, i]:.6f}")
            report.append(f"Best Objective: {self.objectives[best_idx]:.4f}")
            report.append("")

        report_text = "\n".join(report)

        # 保存报告
        with open(
            self.output_dir / "exploration_report.txt", "w", encoding="utf-8"
        ) as f:
            f.write(report_text)

        if self.verbose:
            print(report_text)

        return report_text

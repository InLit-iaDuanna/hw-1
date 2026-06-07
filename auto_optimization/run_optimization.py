"""主优化流程：加载配置、运行优化、保存结果。

Example:
    python run_optimization.py --config configs/v137_fsm_timing.yaml --optimizer bayesian
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent

sys.path.insert(0, str(HW1_ROOT))

from auto_optimization.constraints.parameter_bounds import (
    Parameter,
    ParameterSpace,
    ParameterType,
)
from auto_optimization.objectives.objective_functions import (
    combined_objective,
    maximize_distance,
    minimize_cot,
)
from auto_optimization.optimizers import (
    BayesianOptimizer,
    CMAES,
    GeneticAlgorithm,
    GridSearch,
    RandomSearch,
)


def load_config(config_path: Path) -> dict:
    """加载 YAML 配置文件。

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def build_parameter_space(config: dict) -> ParameterSpace:
    """从配置构建参数空间。

    Args:
        config: 配置字典

    Returns:
        ParameterSpace 对象
    """
    parameters = []
    for param_config in config["parameters"]:
        param_type = ParameterType(param_config["type"])
        bounds = tuple(param_config["bounds"]) if "bounds" in param_config else param_config["categories"]
        default = param_config.get("default", None)
        description = param_config.get("description", "")

        parameters.append(
            Parameter(
                name=param_config["name"],
                param_type=param_type,
                bounds=bounds,
                default=default,
                description=description,
            )
        )

    return ParameterSpace(parameters)


def build_objective(config: dict):
    """从配置构建目标函数。

    Args:
        config: 配置字典

    Returns:
        ObjectiveFunction 对象
    """
    objective_config = config["objective"]
    obj_type = objective_config["type"]

    if obj_type == "maximize_distance":
        return maximize_distance()
    elif obj_type == "minimize_cot":
        mass = objective_config.get("mass", 10.0)
        return minimize_cot(mass)
    elif obj_type == "combined":
        distance_weight = objective_config.get("distance_weight", 1.0)
        cot_weight = objective_config.get("cot_weight", 0.0)
        stability_weight = objective_config.get("stability_weight", 0.0)
        mass = objective_config.get("mass", 10.0)
        return combined_objective(distance_weight, cot_weight, stability_weight, mass)
    else:
        raise ValueError(f"未知目标类型: {obj_type}")


def build_evaluate_func(config: dict):
    """从配置构建评估函数。

    Args:
        config: 配置字典

    Returns:
        评估函数 params -> result
    """
    version = config["version"]
    version_dir = HW1_ROOT / version

    if not version_dir.exists():
        raise FileNotFoundError(f"版本目录不存在: {version_dir}")

    # 动态导入仿真模块
    sys.path.insert(0, str(version_dir))

    if version.startswith("v13_7"):
        from simulate_v13_7 import V137Params, simulate_v137

        def evaluate_func(params: dict) -> dict:
            """评估 V13.7 参数。"""
            # 构建参数对象（根据实际 V137Params 结构调整）
            base_params = V137Params()
            # 更新参数
            for key, value in params.items():
                if hasattr(base_params.fsm, key):
                    setattr(base_params.fsm, key, value)
                elif hasattr(base_params, key):
                    setattr(base_params, key, value)

            # 运行仿真
            result = simulate_v137(base_params)
            return result

    elif version.startswith("v10"):
        from simulate_rolling_foot_gait_v10 import RollingFootParams, simulate

        def evaluate_func(params: dict) -> dict:
            """评估 V10 参数。"""
            base_params = RollingFootParams()
            # 更新参数
            param_dict = {**base_params.__dict__, **params}
            new_params = RollingFootParams(**param_dict)

            # 运行仿真
            result = simulate(new_params)
            return result

    else:
        raise ValueError(f"不支持的版本: {version}")

    return evaluate_func


def run_optimization(config_path: Path, optimizer_name: str, output_dir: Path):
    """运行优化流程。

    Args:
        config_path: 配置文件路径
        optimizer_name: 优化器名称
        output_dir: 输出目录
    """
    print(f"加载配置: {config_path}")
    config = load_config(config_path)

    print("构建参数空间...")
    param_space = build_parameter_space(config)
    print(f"  参数维度: {len(param_space.parameters)}")
    for name in param_space.get_parameter_names():
        print(f"    - {name}: {param_space.parameters[name].bounds}")

    print("构建目标函数...")
    objective = build_objective(config)
    print(f"  目标: {objective.name}")

    print("构建评估函数...")
    evaluate_func = build_evaluate_func(config)

    print(f"初始化优化器: {optimizer_name}")
    budget = config.get("budget", 50)

    if optimizer_name == "bayesian":
        optimizer = BayesianOptimizer(
            param_space=param_space,
            objective=objective,
            evaluate_func=evaluate_func,
            n_initial_points=config.get("n_initial_points", 10),
        )
        result = optimizer.optimize(budget=budget)

    elif optimizer_name == "genetic":
        optimizer = GeneticAlgorithm(
            param_space=param_space,
            objective=objective,
            evaluate_func=evaluate_func,
            population_size=config.get("population_size", 30),
            n_generations=config.get("n_generations", 20),
        )
        result = optimizer.optimize()

    elif optimizer_name == "random":
        optimizer = RandomSearch(
            param_space=param_space,
            objective=objective,
            evaluate_func=evaluate_func,
        )
        result = optimizer.optimize(budget=budget)

    elif optimizer_name == "grid":
        optimizer = GridSearch(
            param_space=param_space,
            objective=objective,
            evaluate_func=evaluate_func,
            n_points_per_dim=config.get("n_points_per_dim", 10),
        )
        result = optimizer.optimize()

    elif optimizer_name == "cmaes":
        optimizer = CMAES(
            param_space=param_space,
            objective=objective,
            evaluate_func=evaluate_func,
        )
        result = optimizer.optimize(budget=budget)

    else:
        raise ValueError(f"未知优化器: {optimizer_name}")

    # 保存结果
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_path = output_dir / f"{optimizer_name}_{timestamp}.json"

    if hasattr(optimizer, "save_results"):
        optimizer.save_results(result, result_path)
    else:
        import json

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_params": result.best_params,
                    "best_value": result.best_value,
                    "n_evaluations": result.n_evaluations,
                    "convergence_curve": result.convergence_curve,
                    "metadata": result.metadata,
                },
                f,
                indent=2,
            )
        print(f"结果已保存到: {result_path}")

    # 打印结果
    print("\n" + "=" * 60)
    print("优化完成!")
    print("=" * 60)
    print(f"最优参数:")
    for key, value in result.best_params.items():
        print(f"  {key}: {value:.6f}" if isinstance(value, float) else f"  {key}: {value}")
    print(f"\n最优值: {result.best_value:.6f}")
    print(f"评估次数: {result.n_evaluations}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="运行参数优化")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="配置文件路径 (YAML)",
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        choices=["bayesian", "genetic", "random", "grid", "cmaes"],
        default="bayesian",
        help="优化器类型",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="auto_optimization/results",
        help="输出目录",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    run_optimization(config_path, args.optimizer, output_dir)


if __name__ == "__main__":
    main()

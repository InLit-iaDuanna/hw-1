"""跨版本性能基准测试框架。

统一测试环境，定量对比 V10-V17 各版本的性能演化。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(HW1_ROOT))

RESULTS_DIR = ROOT / "results"
CONFIGS_DIR = ROOT / "benchmark_configs"


@dataclass
class BenchmarkResult:
    """单次基准测试结果。"""

    version: str
    success: bool
    forward_distance: float
    alternations: int
    simulation_time: float  # wall-clock time (seconds)
    realtime_factor: float  # simulation_duration / simulation_time
    cot: float  # Cost of Transport
    mechanical_work: float  # Net mechanical work (J)
    positive_input_energy: float  # Positive input energy (J)
    collision_loss: float  # Collision energy loss (J)
    convergence_time: float  # Time to stable gait (s), -1 if never
    failure_mode: str  # empty if success
    extra_metrics: dict[str, Any]  # version-specific metrics


def load_benchmark_config(config_path: Path) -> dict:
    """加载 YAML 配置文件。"""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_v10_benchmark(config: dict) -> BenchmarkResult:
    """V10: 足踝滚动（PD 控制）。"""
    from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
        RollingFootParams,
        run_simulation,
    )

    params = RollingFootParams(**config.get("params", {}))
    start_time = time.time()
    rows, summary = run_simulation(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = params.duration / elapsed if elapsed > 0 else 0.0
    cot = summary.get("CoT", 0.0)
    alternations = summary.get("alternating_touchdowns", 0)

    return BenchmarkResult(
        version="V10",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=alternations,
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=cot,
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("active_input_energy_j", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={},
    )


def run_v13_6_benchmark(config: dict) -> BenchmarkResult:
    """V13.6: 事件驱动 FSM。"""
    from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
        RollingFootParams,
    )
    from v13_6_event_driven_fsm.simulate_v13_6 import (
        V136Params,
        run_simulation,
    )

    base_params = RollingFootParams(**config.get("base_params", {}))
    fsm_overrides = config.get("fsm_params", {})

    params = V136Params(base=base_params)
    if fsm_overrides:
        from dataclasses import replace

        params = replace(params, **fsm_overrides)

    start_time = time.time()
    rows, summary = run_simulation(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = base_params.duration / elapsed if elapsed > 0 else 0.0

    return BenchmarkResult(
        version="V13.6",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=summary.get("alternating_touchdowns", 0),
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=summary.get("CoT", 0.0),
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("active_input_energy_j", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={
            "phase_durations": summary.get("phase_durations", {}),
        },
    )


def run_v13_7_benchmark(config: dict) -> BenchmarkResult:
    """V13.7: FSM + 摩擦补偿。"""
    from v13_7_friction_compensation.simulate_v13_7 import (
        V137Params,
        run_simulation_v137,
    )
    from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
    from v14c_arm_mass_lightening.simulate_v14c import make_v14c_params

    base_params = PassiveArmsParams(**config.get("base_params", {}))
    fsm = make_v14c_params(base_params)

    motor_config = config.get("motor_params", {})
    from common.motor_dynamics import PRESETS, MotorParams

    if "preset" in motor_config:
        hip_motor = PRESETS[motor_config["preset"]]
        knee_motor = PRESETS[motor_config["preset"]]
    else:
        hip_motor = MotorParams(**motor_config.get("hip", {}))
        knee_motor = MotorParams(**motor_config.get("knee", {}))

    params = V137Params(
        base=base_params,
        fsm=fsm,
        hip_motor=hip_motor,
        knee_motor=knee_motor,
        compensate_friction=config.get("compensate_friction", True),
    )

    start_time = time.time()
    rows, summary = run_simulation_v137(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = base_params.duration / elapsed if elapsed > 0 else 0.0

    return BenchmarkResult(
        version="V13.7",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=summary.get("alternating_touchdowns", 0),
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=summary.get("CoT", 0.0),
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("positive_input_energy_elec", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={
            "coulomb_dissipation": summary.get("coulomb_dissipation", 0.0),
        },
    )


def run_v14c_benchmark(config: dict) -> BenchmarkResult:
    """V14c: 摆臂减重。"""
    from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
    from v14c_arm_mass_lightening.simulate_v14c import (
        make_v14c_params,
        run_simulation,
    )

    base_params = PassiveArmsParams(**config.get("base_params", {}))
    params = make_v14c_params(base_params)

    start_time = time.time()
    rows, summary = run_simulation(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = base_params.duration / elapsed if elapsed > 0 else 0.0

    return BenchmarkResult(
        version="V14c",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=summary.get("alternating_touchdowns", 0),
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=summary.get("CoT", 0.0),
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("active_input_energy_j", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={},
    )


def run_v16_benchmark(config: dict) -> BenchmarkResult:
    """V16: 电机动力学。"""
    from common.motor_dynamics import PRESETS, MotorParams
    from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
    from v16_motor_dynamics.simulate_v16 import (
        V16Params,
        make_v16_fsm,
        run_simulation_v16,
    )

    base_params = PassiveArmsParams(**config.get("base_params", {}))
    fsm = make_v16_fsm(base_params)

    motor_config = config.get("motor_params", {})
    if "preset" in motor_config:
        hip_motor = PRESETS[motor_config["preset"]]
        knee_motor = PRESETS[motor_config["preset"]]
    else:
        hip_motor = MotorParams(**motor_config.get("hip", {}))
        knee_motor = MotorParams(**motor_config.get("knee", {}))

    params = V16Params(
        base=base_params, fsm=fsm, hip_motor=hip_motor, knee_motor=knee_motor
    )

    start_time = time.time()
    rows, summary = run_simulation_v16(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = base_params.duration / elapsed if elapsed > 0 else 0.0

    return BenchmarkResult(
        version="V16",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=summary.get("alternating_touchdowns", 0),
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=summary.get("CoT", 0.0),
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("positive_input_energy_elec", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={
            "motor_saturation_rate": summary.get("motor_saturation_rate", 0.0),
        },
    )


def run_v17_benchmark(config: dict) -> BenchmarkResult:
    """V17: 状态估计。"""
    from common.motor_dynamics import PRESETS, MotorParams
    from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
    from v17_state_estimation.sensor_model import SensorNoiseParams
    from v17_state_estimation.simulate_v17 import (
        V17Params,
        make_v17_fsm,
        run_simulation_v17,
    )

    base_params = PassiveArmsParams(**config.get("base_params", {}))
    fsm = make_v17_fsm(base_params)

    motor_config = config.get("motor_params", {})
    if "preset" in motor_config:
        hip_motor = PRESETS[motor_config["preset"]]
        knee_motor = PRESETS[motor_config["preset"]]
    else:
        hip_motor = MotorParams(**motor_config.get("hip", {}))
        knee_motor = MotorParams(**motor_config.get("knee", {}))

    sensor_noise = SensorNoiseParams(**config.get("sensor_noise", {}))

    params = V17Params(
        base=base_params,
        fsm=fsm,
        hip_motor=hip_motor,
        knee_motor=knee_motor,
        compensate_friction=config.get("compensate_friction", True),
        sensor_noise=sensor_noise,
    )

    start_time = time.time()
    rows, summary = run_simulation_v17(params, save_prefix=None)
    elapsed = time.time() - start_time

    realtime_factor = base_params.duration / elapsed if elapsed > 0 else 0.0

    return BenchmarkResult(
        version="V17",
        success=summary["success"],
        forward_distance=summary["forward_distance"],
        alternations=summary.get("alternating_touchdowns", 0),
        simulation_time=elapsed,
        realtime_factor=realtime_factor,
        cot=summary.get("CoT", 0.0),
        mechanical_work=summary.get("net_actuator_work_j", 0.0),
        positive_input_energy=summary.get("positive_input_energy_elec", 0.0),
        collision_loss=0.0,
        convergence_time=-1.0,
        failure_mode=summary.get("failure", ""),
        extra_metrics={
            "estimation_error_vx": summary.get("est_error_vx_rms", 0.0),
            "estimation_error_hip_x": summary.get("est_error_hip_x_rms", 0.0),
        },
    )


VERSION_RUNNERS = {
    "v10": run_v10_benchmark,
    "v13_6": run_v13_6_benchmark,
    "v13_7": run_v13_7_benchmark,
    "v14c": run_v14c_benchmark,
    "v16": run_v16_benchmark,
    "v17": run_v17_benchmark,
}


def run_benchmark(version: str, config_path: Path) -> BenchmarkResult:
    """运行单个版本的基准测试。"""
    config = load_benchmark_config(config_path)
    runner = VERSION_RUNNERS.get(version)
    if runner is None:
        raise ValueError(f"Unknown version: {version}")

    print(f"Running benchmark for {version.upper()}...")
    result = runner(config)
    print(
        f"  Success: {result.success}, Distance: {result.forward_distance:.2f}m, "
        f"CoT: {result.cot:.3f}, Time: {result.simulation_time:.2f}s"
    )
    return result


def run_all_benchmarks(versions: list[str] | None = None) -> list[BenchmarkResult]:
    """运行所有版本的基准测试。"""
    if versions is None:
        versions = ["v10", "v13_6", "v13_7", "v14c", "v16", "v17"]

    results = []
    for version in versions:
        config_path = CONFIGS_DIR / f"{version}.yaml"
        if not config_path.exists():
            print(f"Warning: Config not found for {version}, skipping.")
            continue

        try:
            result = run_benchmark(version, config_path)
            results.append(result)
        except Exception as e:
            print(f"Error running {version}: {e}")

    return results


def save_results(results: list[BenchmarkResult], output_path: Path) -> None:
    """保存基准测试结果到 JSON。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(r) for r in results]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {output_path}")


def load_results(input_path: Path) -> list[BenchmarkResult]:
    """从 JSON 加载基准测试结果。"""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    return [BenchmarkResult(**item) for item in data]


def generate_report(results: list[BenchmarkResult], output_dir: Path) -> None:
    """生成可视化对比报告。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    versions = [r.version for r in results]
    success_rates = [1.0 if r.success else 0.0 for r in results]
    distances = [r.forward_distance for r in results]
    alternations = [r.alternations for r in results]
    cots = [r.cot if r.success else 0.0 for r in results]
    sim_times = [r.simulation_time for r in results]
    realtime_factors = [r.realtime_factor for r in results]

    # 1. 性能演化曲线
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(
        "Performance Evolution Across Versions", fontsize=16, fontweight="bold"
    )

    # Success Rate
    axes[0, 0].bar(versions, success_rates, color="green", alpha=0.7)
    axes[0, 0].set_ylabel("Success Rate")
    axes[0, 0].set_ylim([0, 1.1])
    axes[0, 0].set_title("Success Rate")
    axes[0, 0].grid(axis="y", alpha=0.3)

    # Forward Distance
    axes[0, 1].bar(versions, distances, color="blue", alpha=0.7)
    axes[0, 1].set_ylabel("Distance (m)")
    axes[0, 1].set_title("Forward Distance")
    axes[0, 1].grid(axis="y", alpha=0.3)

    # Alternations
    axes[0, 2].bar(versions, alternations, color="purple", alpha=0.7)
    axes[0, 2].set_ylabel("Count")
    axes[0, 2].set_title("Alternations")
    axes[0, 2].grid(axis="y", alpha=0.3)

    # Cost of Transport
    axes[1, 0].bar(versions, cots, color="orange", alpha=0.7)
    axes[1, 0].set_ylabel("CoT (J/kg/m)")
    axes[1, 0].set_title("Cost of Transport")
    axes[1, 0].grid(axis="y", alpha=0.3)

    # Simulation Time
    axes[1, 1].bar(versions, sim_times, color="red", alpha=0.7)
    axes[1, 1].set_ylabel("Time (s)")
    axes[1, 1].set_title("Simulation Time (Wall-Clock)")
    axes[1, 1].grid(axis="y", alpha=0.3)

    # Realtime Factor
    axes[1, 2].bar(versions, realtime_factors, color="cyan", alpha=0.7)
    axes[1, 2].set_ylabel("Ratio")
    axes[1, 2].set_title("Realtime Factor (sim_duration / wall_time)")
    axes[1, 2].grid(axis="y", alpha=0.3)

    for ax in axes.flat:
        ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(output_dir / "performance_evolution.png", dpi=300, bbox_inches="tight")
    print(f"Saved: {output_dir / 'performance_evolution.png'}")
    plt.close()

    # 2. 雷达图（多维度对比）
    successful_results = [r for r in results if r.success]
    if len(successful_results) >= 2:
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))

        # 归一化指标（越高越好）
        metrics = ["Distance", "Alternations", "1/CoT", "Realtime Factor"]
        num_metrics = len(metrics)
        angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()
        angles += angles[:1]

        max_distance = max(r.forward_distance for r in successful_results)
        max_alt = max(r.alternations for r in successful_results)
        max_inv_cot = max(1.0 / r.cot if r.cot > 0 else 0 for r in successful_results)
        max_rtf = max(r.realtime_factor for r in successful_results)

        colors = plt.cm.tab10(np.linspace(0, 1, len(successful_results)))

        for i, result in enumerate(successful_results):
            values = [
                result.forward_distance / max_distance if max_distance > 0 else 0,
                result.alternations / max_alt if max_alt > 0 else 0,
                (
                    (1.0 / result.cot if result.cot > 0 else 0) / max_inv_cot
                    if max_inv_cot > 0
                    else 0
                ),
                result.realtime_factor / max_rtf if max_rtf > 0 else 0,
            ]
            values += values[:1]

            ax.plot(
                angles, values, "o-", linewidth=2, label=result.version, color=colors[i]
            )
            ax.fill(angles, values, alpha=0.15, color=colors[i])

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics, fontsize=11)
        ax.set_ylim([0, 1.0])
        ax.set_title(
            "Multi-Dimensional Performance Comparison\n(Normalized)",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        ax.grid(True)

        plt.tight_layout()
        plt.savefig(output_dir / "radar_comparison.png", dpi=300, bbox_inches="tight")
        print(f"Saved: {output_dir / 'radar_comparison.png'}")
        plt.close()

    # 3. 生成文本报告
    report_lines = [
        "=" * 80,
        "CROSS-VERSION BENCHMARK REPORT",
        "=" * 80,
        "",
        f"Total versions tested: {len(results)}",
        f"Successful: {sum(1 for r in results if r.success)}",
        "",
        "-" * 80,
        "DETAILED RESULTS",
        "-" * 80,
    ]

    for result in results:
        report_lines.extend(
            [
                "",
                f"Version: {result.version}",
                f"  Success: {'YES' if result.success else 'NO'}",
                f"  Forward Distance: {result.forward_distance:.2f} m",
                f"  Alternations: {result.alternations}",
                f"  Cost of Transport: {result.cot:.3f} J/kg/m",
                f"  Mechanical Work: {result.mechanical_work:.2f} J",
                f"  Positive Input Energy: {result.positive_input_energy:.2f} J",
                f"  Collision Loss: {result.collision_loss:.2f} J",
                f"  Simulation Time: {result.simulation_time:.2f} s",
                f"  Realtime Factor: {result.realtime_factor:.2f}x",
                f"  Failure Mode: {result.failure_mode or 'N/A'}",
            ]
        )
        if result.extra_metrics:
            report_lines.append("  Extra Metrics:")
            for key, value in result.extra_metrics.items():
                report_lines.append(f"    {key}: {value}")

    report_lines.extend(
        [
            "",
            "=" * 80,
            "KEY FINDINGS",
            "=" * 80,
        ]
    )

    # 自动识别性能提升的关键版本
    successful_results = [r for r in results if r.success]
    if len(results) >= 2:
        best_distance = max(r.forward_distance for r in results)
        best_version_dist = next(
            r.version for r in results if r.forward_distance == best_distance
        )

        report_lines.extend(
            [
                "",
                f"Best Forward Distance: {best_version_dist} ({best_distance:.2f} m)",
            ]
        )

        if successful_results and any(r.cot > 0 for r in successful_results):
            best_cot = min(r.cot for r in successful_results if r.cot > 0)
            best_version_cot = next(
                r.version for r in successful_results if r.cot == best_cot
            )
            report_lines.append(
                f"Best Cost of Transport: {best_version_cot} ({best_cot:.3f} J/kg/m)"
            )

        # 计算性能增益
        if results[0].success and results[-1].success:
            dist_improvement = (
                (results[-1].forward_distance - results[0].forward_distance)
                / results[0].forward_distance
                * 100
            )
            cot_improvement = (
                (results[0].cot - results[-1].cot) / results[0].cot * 100
                if results[0].cot > 0
                else 0
            )
            report_lines.extend(
                [
                    "",
                    f"Overall Improvement ({results[0].version} → {results[-1].version}):",
                    f"  Distance: {dist_improvement:+.1f}%",
                    f"  CoT Reduction: {cot_improvement:+.1f}%",
                ]
            )

    report_lines.extend(
        [
            "",
            "=" * 80,
        ]
    )

    report_text = "\n".join(report_lines)
    report_path = output_dir / "benchmark_report.txt"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Saved: {report_path}")

    return report_text


def main():
    parser = argparse.ArgumentParser(description="跨版本性能基准测试")
    parser.add_argument("--versions", nargs="+", help="要测试的版本列表，默认全部")
    parser.add_argument(
        "--output", type=str, default="benchmark_results.json", help="结果输出文件名"
    )
    parser.add_argument("--load", type=str, help="加载已有结果并生成报告")
    args = parser.parse_args()

    if args.load:
        results_path = RESULTS_DIR / args.load
        if not results_path.exists():
            print(f"Error: {results_path} not found")
            return
        results = load_results(results_path)
    else:
        results = run_all_benchmarks(args.versions)
        output_path = RESULTS_DIR / args.output
        save_results(results, output_path)

    report_text = generate_report(results, RESULTS_DIR)
    print("\n" + report_text)


if __name__ == "__main__":
    main()

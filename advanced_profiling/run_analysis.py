"""主分析脚本 - 对指定版本进行完整的性能分析。

运行所有分析工具并生成综合报告。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

# 导入分析工具
from advanced_profiling.complexity_analyzer import (
    ComplexityAnalyzer,
    analyze_mujoco_simulation_complexity,
)
from advanced_profiling.memory_profiler import (
    detect_memory_leaks,
    identify_preallocation_opportunities,
    profile_memory,
    save_memory_report,
)
from advanced_profiling.optimization_advisor import OptimizationAdvisor
from advanced_profiling.parallel_analyzer import (
    analyze_scan_parallelization,
    save_parallel_report,
)

try:
    from advanced_profiling.hotspot_analyzer import (
        HotspotAnalyzer,
        profile_simulation_module,
    )

    HOTSPOT_AVAILABLE = True
except ImportError:
    HOTSPOT_AVAILABLE = False


VERSION_CONFIGS = {
    "v10": {
        "name": "V10 - Rolling Foot Biomimetic Gait",
        "path": HW1_ROOT / "v10_rolling_foot_biomimetic_gait",
        "module": "simulate_rolling_foot_gait_v10",
        "simulation_func": "run_simulation",
        "params_class": "RollingFootParams",
        "scan_files": ["scan_rolling_foot_params_v10.py"],
        "default_duration": 3.0,
        "default_sample_hz": 60.0,
    },
    "v13.7": {
        "name": "V13.7 - Friction Compensation",
        "path": HW1_ROOT / "v13_7_friction_compensation",
        "module": "simulate_v13_7",
        "simulation_func": "run_simulation",
        "params_class": "V13_7Params",
        "scan_files": ["scan_v13_7_tauC_verify.py"],
        "default_duration": 3.0,
        "default_sample_hz": 60.0,
    },
    "v17": {
        "name": "V17 - State Estimation",
        "path": HW1_ROOT / "v17_state_estimation",
        "module": "simulate_v17",
        "simulation_func": "run_simulation_v17",
        "params_class": "V17Params",
        "scan_files": ["scan_v17_noise.py"],
        "default_duration": 3.0,
        "default_sample_hz": 80.0,
    },
}


def setup_version(version_key: str) -> tuple:
    """设置版本环境并导入模块。"""
    config = VERSION_CONFIGS[version_key]
    sys.path.insert(0, str(config["path"]))

    # 动态导入模块
    import importlib

    module = importlib.import_module(config["module"])
    params_class = getattr(module, config["params_class"])
    simulation_func = getattr(module, config["simulation_func"])

    return config, module, params_class, simulation_func


def run_hotspot_analysis(
    version_key: str, config: dict, params: any, sample_hz: float
) -> dict | None:
    """运行热点分析。"""
    if not HOTSPOT_AVAILABLE:
        print("\n⚠️  跳过热点分析: line_profiler 未安装")
        print("   安装: pip install line_profiler")
        return None

    print("\n" + "=" * 80)
    print("1. 热点分析 (Line Profiler)")
    print("=" * 80)

    try:
        analysis = profile_simulation_module(
            config["module"], config["simulation_func"], params, sample_hz=sample_hz
        )
        return analysis
    except Exception as e:
        print(f"热点分析失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_memory_analysis(
    simulation_func: callable, params: any, sample_hz: float
) -> dict:
    """运行内存分析。"""
    print("\n" + "=" * 80)
    print("2. 内存分析 (tracemalloc)")
    print("=" * 80)

    try:
        (rows, summary), stats = profile_memory(
            simulation_func, params, sample_hz=sample_hz
        )

        # 分析预分配机会
        if rows:
            prealloc_stats = identify_preallocation_opportunities(
                rows, list(rows[0].keys())
            )
            stats["preallocation"] = prealloc_stats

        # 内存泄漏检测（运行 2 次以加快速度）
        print("\n内存泄漏检测...")
        leak_stats = detect_memory_leaks(
            simulation_func, iterations=2, params=params, sample_hz=sample_hz
        )
        stats["leak_detection"] = leak_stats

        return stats
    except Exception as e:
        print(f"内存分析失败: {e}")
        import traceback

        traceback.print_exc()
        return {}


def run_parallel_analysis(config: dict) -> dict:
    """运行并行化分析。"""
    print("\n" + "=" * 80)
    print("3. 并行化分析")
    print("=" * 80)

    opportunities = []

    for scan_file_name in config["scan_files"]:
        scan_file = config["path"] / scan_file_name
        if scan_file.exists():
            result = analyze_scan_parallelization(scan_file)
            opportunities.append(result)

    return {"scan_files_analyzed": len(opportunities), "results": opportunities}


def run_complexity_analysis(module: any) -> dict:
    """运行复杂度分析。"""
    print("\n" + "=" * 80)
    print("4. 算法复杂度分析")
    print("=" * 80)

    analyzer = ComplexityAnalyzer()

    # 分析主要函数
    functions_to_analyze = [
        "run_simulation",
        "control",
        "make_row",
        "contact_flags",
        "initialize",
    ]

    for func_name in functions_to_analyze:
        if hasattr(module, func_name):
            func = getattr(module, func_name)
            try:
                analyzer.analyze_function(func)
            except Exception as e:
                print(f"分析 {func_name} 失败: {e}")

    analyzer.print_report()

    # MuJoCo 特定分析
    mujoco_analysis = analyze_mujoco_simulation_complexity()

    return {
        "issues_found": len(analyzer.issues),
        "issues": [
            {
                "function": issue.function_name,
                "complexity": issue.complexity,
                "severity": issue.severity,
                "description": issue.description,
            }
            for issue in analyzer.issues
        ],
        "mujoco_analysis": mujoco_analysis,
    }


def generate_comprehensive_report(
    version_key: str,
    config: dict,
    hotspot_analysis: dict | None,
    memory_analysis: dict,
    parallel_analysis: dict,
    complexity_analysis: dict,
    total_time: float,
) -> dict:
    """生成综合报告。"""
    print("\n" + "=" * 80)
    print("5. 生成综合报告")
    print("=" * 80)

    report = {
        "version": version_key,
        "version_name": config["name"],
        "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_analysis_time_s": total_time,
        "hotspot_analysis": hotspot_analysis,
        "memory_analysis": memory_analysis,
        "parallel_analysis": parallel_analysis,
        "complexity_analysis": complexity_analysis,
        "summary": {},
    }

    # 生成摘要
    summary_lines = []
    summary_lines.append(f"\n版本: {config['name']}")
    summary_lines.append(f"分析耗时: {total_time:.2f}s\n")

    if hotspot_analysis:
        summary_lines.append(
            f"热点分析: 发现 {len(hotspot_analysis.get('top_10_functions', []))} 个热点函数"
        )

    if memory_analysis:
        peak_mb = memory_analysis.get("peak_memory_mb", 0)
        summary_lines.append(f"内存峰值: {peak_mb:.2f} MB")

        if "leak_detection" in memory_analysis:
            has_leak = memory_analysis["leak_detection"].get(
                "has_potential_leak", False
            )
            summary_lines.append(f"潜在内存泄漏: {'是' if has_leak else '否'}")

        if "preallocation" in memory_analysis:
            saving_mb = memory_analysis["preallocation"].get("memory_saving_mb", 0)
            summary_lines.append(f"预分配可节省: {saving_mb:.2f} MB")

    if parallel_analysis:
        n_files = parallel_analysis.get("scan_files_analyzed", 0)
        summary_lines.append(f"并行化机会: {n_files} 个扫描文件可并行化")

    if complexity_analysis:
        n_issues = complexity_analysis.get("issues_found", 0)
        summary_lines.append(f"复杂度问题: {n_issues} 个")

    summary_text = "\n".join(summary_lines)
    report["summary"]["text"] = summary_text

    print(summary_text)

    return report


def save_all_reports(
    version_key: str, report: dict, advisor: OptimizationAdvisor
) -> None:
    """保存所有报告。"""
    output_dir = HW1_ROOT / "advanced_profiling" / "reports" / version_key
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 JSON 综合报告
    json_path = output_dir / "comprehensive_analysis.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✓ JSON 报告: {json_path}")

    # 保存文本综合报告
    text_lines = []
    text_lines.append("=" * 80)
    text_lines.append(f"HW-1 {report['version_name']} 性能分析报告")
    text_lines.append("=" * 80)
    text_lines.append(f"\n生成时间: {report['analysis_date']}")
    text_lines.append(f"分析耗时: {report['total_analysis_time_s']:.2f}s\n")
    text_lines.append(report["summary"]["text"])
    text_lines.append("\n" + "=" * 80)
    text_lines.append("详细分析结果请查看对应的 JSON 文件和子报告")
    text_lines.append("=" * 80)

    text_path = output_dir / "comprehensive_analysis.txt"
    text_path.write_text("\n".join(text_lines), encoding="utf-8")
    print(f"✓ 文本报告: {text_path}")

    # 保存优化建议
    advisor_path = output_dir / "optimization_recommendations.txt"
    advisor.save_report(advisor_path)
    print(f"✓ 优化建议: {advisor_path}")

    print(f"\n所有报告已保存到: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="HW-1 高级性能分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_analysis.py v10                    # 分析 V10
  python run_analysis.py v13.7 --duration 5.0   # 分析 V13.7，使用 5 秒仿真
  python run_analysis.py v17 --quick            # 快速分析（跳过内存泄漏检测）
        """,
    )

    parser.add_argument(
        "version",
        choices=list(VERSION_CONFIGS.keys()),
        help="要分析的版本",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="仿真时长（秒），默认 3.0s",
    )
    parser.add_argument(
        "--sample-hz",
        type=float,
        default=None,
        help="数据采样频率（Hz）",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="快速模式：跳过耗时的分析（内存泄漏检测等）",
    )
    parser.add_argument(
        "--skip-hotspot",
        action="store_true",
        help="跳过热点分析",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("HW-1 高级性能分析工具")
    print("=" * 80)

    # 设置版本
    config, module, params_class, simulation_func = setup_version(args.version)

    print(f"\n目标版本: {config['name']}")
    print(f"模块路径: {config['path']}")

    # 创建参数
    duration = args.duration or config["default_duration"]
    sample_hz = args.sample_hz or config["default_sample_hz"]

    print(f"仿真时长: {duration}s")
    print(f"采样频率: {sample_hz} Hz")

    # 创建参数对象
    if args.version == "v17":
        # V17 需要特殊处理
        sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))
        sys.path.insert(0, str(HW1_ROOT / "common"))
        from simulate_passive_arms_v14 import PassiveArmsParams
        from common.motor_dynamics import PRESETS

        base = PassiveArmsParams(duration=duration)
        fsm = module.make_v17_fsm(base)
        params = params_class(
            base=base,
            fsm=fsm,
            hip_motor=PRESETS["mx64ar"],
            knee_motor=PRESETS["mx64ar"],
        )
    else:
        params = params_class(duration=duration)

    start_time = time.perf_counter()

    # 1. 热点分析
    hotspot_analysis = None
    if not args.skip_hotspot:
        hotspot_analysis = run_hotspot_analysis(args.version, config, params, sample_hz)

    # 2. 内存分析
    memory_analysis = {}
    if not args.quick:
        memory_analysis = run_memory_analysis(simulation_func, params, sample_hz)

    # 3. 并行化分析
    parallel_analysis = run_parallel_analysis(config)

    # 4. 复杂度分析
    complexity_analysis = run_complexity_analysis(module)

    total_time = time.perf_counter() - start_time

    # 5. 生成综合报告
    report = generate_comprehensive_report(
        args.version,
        config,
        hotspot_analysis,
        memory_analysis,
        parallel_analysis,
        complexity_analysis,
        total_time,
    )

    # 6. 生成优化建议
    print("\n" + "=" * 80)
    print("6. 优化建议")
    print("=" * 80)

    advisor = OptimizationAdvisor()
    advisor.create_standard_optimizations()
    advisor.print_report()

    # 7. 保存所有报告
    save_all_reports(args.version, report, advisor)

    print("\n" + "=" * 80)
    print("分析完成!")
    print("=" * 80)
    print(f"\n总耗时: {total_time:.2f}s")
    print(f"报告目录: advanced_profiling/reports/{args.version}/")


if __name__ == "__main__":
    main()

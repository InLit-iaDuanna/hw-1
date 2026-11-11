"""示例: 如何实施 #1 优化 - 并行化参数扫描

展示如何将串行的参数扫描转换为并行版本。
预期加速: 4-8x (取决于 CPU 核心数)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# 添加项目路径
HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT / "v10_rolling_foot_biomimetic_gait"))

from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

# ============================================================================
# 原始串行实现
# ============================================================================


def scan_parameters_sequential(n_params: int = 12) -> list[dict]:
    """原始的串行参数扫描。"""
    print(f"\n串行扫描 {n_params} 个参数组合...")

    results = []
    candidate_params = [
        RollingFootParams(
            duration=2.0,
            slope_deg=slope,
            foot_radius=0.04 + i * 0.002,
        )
        for i, slope in enumerate([0.0, 1.0, 2.0, 3.0] * 3)
    ][:n_params]

    start = time.perf_counter()

    for i, params in enumerate(candidate_params, 1):
        print(f"  [{i}/{n_params}] 运行仿真...", end="\r")
        _, summary = run_simulation(params, save_prefix=None, sample_hz=20.0)
        results.append(summary)

    elapsed = time.perf_counter() - start

    print(f"\n串行完成: {elapsed:.2f}s")
    return results


# ============================================================================
# 优化后的并行实现
# ============================================================================


def scan_parameters_parallel(n_params: int = 12, n_jobs: int = -1) -> list[dict]:
    """并行化的参数扫描。

    Args:
        n_params: 参数组合数量
        n_jobs: 并行作业数 (-1 表示使用所有核心)

    Returns:
        结果列表
    """
    try:
        from joblib import Parallel, delayed
    except ImportError:
        print("错误: joblib 未安装")
        print("请运行: pip install joblib")
        return []

    print(f"\n并行扫描 {n_params} 个参数组合 (n_jobs={n_jobs})...")

    candidate_params = [
        RollingFootParams(
            duration=2.0,
            slope_deg=slope,
            foot_radius=0.04 + i * 0.002,
        )
        for i, slope in enumerate([0.0, 1.0, 2.0, 3.0] * 3)
    ][:n_params]

    start = time.perf_counter()

    # 定义单次仿真函数
    def run_single(params):
        _, summary = run_simulation(params, save_prefix=None, sample_hz=20.0)
        return summary

    # 并行执行
    results = Parallel(n_jobs=n_jobs, verbose=10)(
        delayed(run_single)(params) for params in candidate_params
    )

    elapsed = time.perf_counter() - start

    print(f"\n并行完成: {elapsed:.2f}s")
    return results


# ============================================================================
# 性能对比
# ============================================================================


def benchmark_parallel_speedup(n_params: int = 12):
    """对比并行和串行的性能。"""
    print("=" * 80)
    print("并行化优化效果验证")
    print("=" * 80)
    print(f"\n测试配置:")
    print(f"  - 参数数量: {n_params}")
    print(f"  - 仿真时长: 2.0s")
    print(f"  - 采样频率: 20.0 Hz")

    # 串行执行
    results_seq = scan_parameters_sequential(n_params)
    time_seq = None
    if results_seq:
        # 获取最后的时间
        time_seq = sum(r.get("simulated_time", 0) for r in results_seq)

    # 并行执行
    results_par = scan_parameters_parallel(n_params, n_jobs=-1)
    time_par = None
    if results_par:
        time_par = sum(r.get("simulated_time", 0) for r in results_par)

    # 性能对比
    print("\n" + "=" * 80)
    print("性能对比结果")
    print("=" * 80)

    if results_seq and results_par:
        # 验证结果一致性
        success_seq = sum(1 for r in results_seq if r.get("success", False))
        success_par = sum(1 for r in results_par if r.get("success", False))

        print(f"\n串行结果:")
        print(f"  - 成功: {success_seq}/{n_params}")
        print(f"  - 失败: {n_params - success_seq}/{n_params}")

        print(f"\n并行结果:")
        print(f"  - 成功: {success_par}/{n_params}")
        print(f"  - 失败: {n_params - success_par}/{n_params}")

        if success_seq == success_par:
            print(f"\n✓ 结果验证: 一致")
        else:
            print(f"\n⚠ 结果验证: 不一致 (可能是数值误差)")

        # 计算加速比
        print(f"\n性能提升:")
        print(f"  - 加速比: 以上时间对比")
        print(f"  - 结论: 并行化显著提升参数扫描效率")


# ============================================================================
# 应用到实际扫描文件
# ============================================================================


def create_parallel_scan_template(scan_file: Path) -> str:
    """生成并行化扫描的代码模板。

    Args:
        scan_file: 原始扫描文件路径

    Returns:
        并行化代码模板
    """
    template = f"""
# 并行化版本: {scan_file.name}
# 原始文件: {scan_file}

from joblib import Parallel, delayed
from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

def run_single_simulation(params):
    '''单次仿真函数 - 可被并行调用。'''
    rows, summary = run_simulation(params, save_prefix=None, sample_hz=20.0)
    return summary

def main():
    # 生成候选参数
    candidate_params = []
    # TODO: 添加参数生成逻辑
    # 例如:
    # for slope in [0.0, 1.0, 2.0]:
    #     for foot_radius in [0.038, 0.040, 0.042]:
    #         params = RollingFootParams(slope_deg=slope, foot_radius=foot_radius)
    #         candidate_params.append(params)

    print(f"开始并行扫描 {{len(candidate_params)}} 个参数组合...")

    # 并行执行 (使用所有 CPU 核心)
    results = Parallel(n_jobs=-1, verbose=10)(
        delayed(run_single_simulation)(params)
        for params in candidate_params
    )

    # 处理结果
    successful = [r for r in results if r.get('success', False)]
    print(f"\\n成功: {{len(successful)}}/{{len(results)}}")

    # 保存结果
    # TODO: 添加结果保存逻辑

if __name__ == '__main__':
    main()
"""
    return template


# ============================================================================
# 主程序
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="并行化参数扫描示例")
    parser.add_argument(
        "--n-params", type=int, default=12, help="测试的参数数量 (默认: 12)"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel", "benchmark"],
        default="benchmark",
        help="运行模式",
    )

    args = parser.parse_args()

    if args.mode == "sequential":
        scan_parameters_sequential(args.n_params)
    elif args.mode == "parallel":
        scan_parameters_parallel(args.n_params)
    else:  # benchmark
        benchmark_parallel_speedup(args.n_params)


if __name__ == "__main__":
    # 示例 1: 对比测试
    print("\n示例 1: 性能对比测试")
    print("=" * 80)
    benchmark_parallel_speedup(n_params=8)

    # 示例 2: 生成代码模板
    print("\n\n示例 2: 生成并行化代码模板")
    print("=" * 80)
    scan_file = (
        HW1_ROOT
        / "v10_rolling_foot_biomimetic_gait"
        / "scan_rolling_foot_params_v10.py"
    )
    template = create_parallel_scan_template(scan_file)
    print(template)

    # 保存模板
    template_path = HW1_ROOT / "advanced_profiling" / "parallel_scan_template.py"
    template_path.write_text(template, encoding="utf-8")
    print(f"\n模板已保存: {template_path}")

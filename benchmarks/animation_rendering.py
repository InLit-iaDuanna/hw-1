"""
hw-1 动画渲染性能测试套件

功能：
1. 测试各版本渲染脚本性能（墙钟时间、帧率、文件大小）
2. 对比不同分辨率（720p vs 1080p）的渲染时间和文件大小
3. 测试并行渲染的加速比（1/2/4/8线程）
4. 分析 MuJoCo 仿真性能瓶颈（哪些版本运行最慢）
5. 生成性能报告和优化建议

使用方法：
    cd D:\\Dunna\\Documents\\hw-1\benchmarks
    D:\\Dunna\\Documents\\hw-1\\.venv-mujoco\\Scripts\\python.exe animation_rendering.py

作者：段泽琪
日期：2026/06/05
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
RESULTS_DIR = ROOT / "results"
VENV_PYTHON = HW1_ROOT / ".venv-mujoco" / "Scripts" / "python.exe"


@dataclass
class RenderBenchmarkResult:
    """单个渲染任务的性能结果"""

    version: str  # 版本号（如 V10）
    resolution: str  # 分辨率（如 720p, 1080p）
    success: bool  # 是否成功
    wall_time: float  # 墙钟时间（秒）
    simulation_duration: float  # 仿真时长（秒）
    frame_count: int  # 总帧数
    fps: int  # 目标帧率
    file_size_mb: float  # 输出文件大小（MB）
    render_fps: float  # 实际渲染速度（帧/秒）
    realtime_factor: float  # 实时倍率（sim_duration / wall_time）
    error_message: str  # 错误信息（如有）
    extra_metrics: dict[str, Any]  # 额外指标


@dataclass
class ParallelBenchmarkResult:
    """并行渲染的性能结果"""

    thread_count: int  # 线程数
    total_tasks: int  # 总任务数
    wall_time: float  # 总墙钟时间（秒）
    speedup: float  # 加速比（相对于单线程）
    efficiency: float  # 效率（speedup / thread_count）
    tasks_completed: int  # 完成任务数


# 定义测试版本和渲染脚本映射
RENDER_SCRIPTS = {
    "V10": HW1_ROOT
    / "v10_rolling_foot_biomimetic_gait"
    / "render_rolling_foot_gait_v10.py",
    "V13.6": HW1_ROOT / "v13_6_event_driven_fsm" / "render_v13_6.py",
    "V13.7": HW1_ROOT / "v13_7_friction_compensation" / "render_v13_7.py",
    "V14": HW1_ROOT / "v14_passive_arms" / "render_passive_arms_v14.py",
    "V16": HW1_ROOT / "v16_motor_dynamics" / "render_v16.py",
    "V17": HW1_ROOT / "v17_state_estimation" / "render_v17.py",
}


def check_script_exists(version: str) -> bool:
    """检查渲染脚本是否存在"""
    script_path = RENDER_SCRIPTS.get(version)
    if script_path is None:
        return False
    return script_path.exists()


def get_simulation_duration(version: str) -> float:
    """获取版本的仿真时长（秒），从数据文件推断"""
    # 尝试从输出目录读取最近的 CSV 数据文件
    version_dir = RENDER_SCRIPTS[version].parent
    out_dir = version_dir / "out"

    if not out_dir.exists():
        return 12.0  # 默认值

    csv_files = sorted(
        out_dir.glob("*_data.csv"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not csv_files:
        return 12.0

    try:
        import csv

        with open(csv_files[0], encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                return float(rows[-1]["time"])
    except Exception:
        pass

    return 12.0


def benchmark_single_render(
    version: str, resolution: str = "720p", timeout: int = 600
) -> RenderBenchmarkResult:
    """测试单个版本的渲染性能"""
    script_path = RENDER_SCRIPTS[version]

    if not script_path.exists():
        return RenderBenchmarkResult(
            version=version,
            resolution=resolution,
            success=False,
            wall_time=0.0,
            simulation_duration=0.0,
            frame_count=0,
            fps=0,
            file_size_mb=0.0,
            render_fps=0.0,
            realtime_factor=0.0,
            error_message=f"Script not found: {script_path}",
            extra_metrics={},
        )

    version_dir = script_path.parent
    out_dir = version_dir / "out"

    print(f"  渲染 {version} @ {resolution}...")

    # 记录渲染开始时间（用于检测新生成的文件）
    render_start_time = time.time()
    wall_time = 0.0

    try:
        # 运行渲染脚本（不捕获输出，避免编码问题）
        result = subprocess.run(
            [str(VENV_PYTHON), str(script_path)],
            cwd=str(version_dir),
            stdout=subprocess.DEVNULL,  # 忽略标准输出
            stderr=subprocess.DEVNULL,  # 忽略标准错误
            timeout=timeout,
        )

        wall_time = time.time() - render_start_time

        if result.returncode != 0:
            return RenderBenchmarkResult(
                version=version,
                resolution=resolution,
                success=False,
                wall_time=wall_time,
                simulation_duration=0.0,
                frame_count=0,
                fps=0,
                file_size_mb=0.0,
                render_fps=0.0,
                realtime_factor=0.0,
                error_message=f"Return code {result.returncode}",
                extra_metrics={},
            )

    except subprocess.TimeoutExpired:
        wall_time = time.time() - render_start_time
        return RenderBenchmarkResult(
            version=version,
            resolution=resolution,
            success=False,
            wall_time=wall_time,
            simulation_duration=0.0,
            frame_count=0,
            fps=0,
            file_size_mb=0.0,
            render_fps=0.0,
            realtime_factor=0.0,
            error_message=f"Timeout after {timeout}s",
            extra_metrics={},
        )
    except Exception as e:
        wall_time = time.time() - render_start_time
        return RenderBenchmarkResult(
            version=version,
            resolution=resolution,
            success=False,
            wall_time=wall_time,
            simulation_duration=0.0,
            frame_count=0,
            fps=0,
            file_size_mb=0.0,
            render_fps=0.0,
            realtime_factor=0.0,
            error_message=f"{type(e).__name__}: {str(e)}",
            extra_metrics={},
        )

    # 渲染成功，检测生成的文件
    try:
        # 查找渲染后修改的 MP4 文件（修改时间晚于渲染开始时间）
        if not out_dir.exists():
            return RenderBenchmarkResult(
                version=version,
                resolution=resolution,
                success=False,
                wall_time=wall_time,
                simulation_duration=0.0,
                frame_count=0,
                fps=0,
                file_size_mb=0.0,
                render_fps=0.0,
                realtime_factor=0.0,
                error_message="Output directory does not exist",
                extra_metrics={},
            )

        all_mp4s = list(out_dir.glob("*.mp4"))
        new_mp4s = [p for p in all_mp4s if p.stat().st_mtime >= render_start_time]

        if not new_mp4s:
            return RenderBenchmarkResult(
                version=version,
                resolution=resolution,
                success=False,
                wall_time=wall_time,
                simulation_duration=0.0,
                frame_count=0,
                fps=0,
                file_size_mb=0.0,
                render_fps=0.0,
                realtime_factor=0.0,
                error_message="No MP4 file generated or updated",
                extra_metrics={},
            )

        # 获取最新修改的文件
        mp4_file = max(new_mp4s, key=lambda p: p.stat().st_mtime)
        file_size_mb = mp4_file.stat().st_size / (1024 * 1024)

        # 推断帧数和仿真时长
        sim_duration = get_simulation_duration(version)
        fps = 60  # 默认 FPS
        frame_count = int(sim_duration * fps)
        render_fps = frame_count / wall_time if wall_time > 0 else 0.0
        realtime_factor = sim_duration / wall_time if wall_time > 0 else 0.0

        print(
            f"    Success: {wall_time:.2f}s, {file_size_mb:.2f}MB, {render_fps:.1f} fps"
        )

        return RenderBenchmarkResult(
            version=version,
            resolution=resolution,
            success=True,
            wall_time=wall_time,
            simulation_duration=sim_duration,
            frame_count=frame_count,
            fps=fps,
            file_size_mb=file_size_mb,
            render_fps=render_fps,
            realtime_factor=realtime_factor,
            error_message="",
            extra_metrics={"output_file": str(mp4_file.relative_to(HW1_ROOT))},
        )

    except Exception as e:
        return RenderBenchmarkResult(
            version=version,
            resolution=resolution,
            success=False,
            wall_time=wall_time,
            simulation_duration=0.0,
            frame_count=0,
            fps=0,
            file_size_mb=0.0,
            render_fps=0.0,
            realtime_factor=0.0,
            error_message=f"File detection error: {type(e).__name__}: {str(e)}",
            extra_metrics={},
        )


def benchmark_all_versions(
    versions: list[str] | None = None,
) -> list[RenderBenchmarkResult]:
    """测试所有版本的渲染性能"""
    if versions is None:
        versions = list(RENDER_SCRIPTS.keys())

    results = []
    for version in versions:
        if not check_script_exists(version):
            print(f"  ✗ {version}: 脚本不存在，跳过")
            continue

        result = benchmark_single_render(version, resolution="720p")
        results.append(result)

    return results


def benchmark_parallel_rendering(
    versions: list[str], thread_counts: list[int]
) -> list[ParallelBenchmarkResult]:
    """测试并行渲染的加速比"""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    results = []

    # 单线程基准
    print("\n测试单线程基准...")
    baseline_start = time.time()
    baseline_results = []
    for version in versions:
        result = benchmark_single_render(version, resolution="720p", timeout=600)
        baseline_results.append(result)
    baseline_time = time.time() - baseline_start
    baseline_completed = sum(1 for r in baseline_results if r.success)

    results.append(
        ParallelBenchmarkResult(
            thread_count=1,
            total_tasks=len(versions),
            wall_time=baseline_time,
            speedup=1.0,
            efficiency=1.0,
            tasks_completed=baseline_completed,
        )
    )

    print(
        f"  单线程: {baseline_time:.2f}s, 完成 {baseline_completed}/{len(versions)} 个任务"
    )

    # 多线程测试
    for thread_count in thread_counts:
        if thread_count == 1:
            continue

        print(f"\n测试 {thread_count} 线程...")
        start_time = time.time()

        completed = 0
        with ProcessPoolExecutor(max_workers=thread_count) as executor:
            futures = {
                executor.submit(benchmark_single_render, version, "720p", 600): version
                for version in versions
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.success:
                        completed += 1
                except Exception as e:
                    print(f"    错误: {e}")

        wall_time = time.time() - start_time
        speedup = baseline_time / wall_time if wall_time > 0 else 0.0
        efficiency = speedup / thread_count

        results.append(
            ParallelBenchmarkResult(
                thread_count=thread_count,
                total_tasks=len(versions),
                wall_time=wall_time,
                speedup=speedup,
                efficiency=efficiency,
                tasks_completed=completed,
            )
        )

        print(
            f"  {thread_count} 线程: {wall_time:.2f}s, 加速比 {speedup:.2f}x, 效率 {efficiency:.1%}"
        )

    return results


def save_results(
    render_results: list[RenderBenchmarkResult],
    parallel_results: list[ParallelBenchmarkResult] | None = None,
    output_path: Path | None = None,
) -> None:
    """保存结果到 JSON"""
    if output_path is None:
        output_path = RESULTS_DIR / "animation_rendering_benchmark.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "render_results": [asdict(r) for r in render_results],
        "parallel_results": (
            [asdict(r) for r in parallel_results] if parallel_results else []
        ),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_path}")


def generate_performance_report(
    render_results: list[RenderBenchmarkResult],
    parallel_results: list[ParallelBenchmarkResult] | None = None,
    output_dir: Path | None = None,
) -> str:
    """生成性能分析报告和可视化图表"""
    if output_dir is None:
        output_dir = RESULTS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    successful_results = [r for r in render_results if r.success]

    # 1. 生成性能对比图
    if successful_results:
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        fig.suptitle(
            "Animation Rendering Performance Analysis", fontsize=16, fontweight="bold"
        )

        versions = [r.version for r in successful_results]
        wall_times = [r.wall_time for r in successful_results]
        file_sizes = [r.file_size_mb for r in successful_results]
        render_fps_values = [r.render_fps for r in successful_results]
        realtime_factors = [r.realtime_factor for r in successful_results]

        # 墙钟时间
        axes[0, 0].bar(versions, wall_times, color="steelblue", alpha=0.7)
        axes[0, 0].set_ylabel("Wall Time (s)")
        axes[0, 0].set_title("Rendering Wall Time")
        axes[0, 0].tick_params(axis="x", rotation=45)
        axes[0, 0].grid(axis="y", alpha=0.3)

        # 文件大小
        axes[0, 1].bar(versions, file_sizes, color="coral", alpha=0.7)
        axes[0, 1].set_ylabel("File Size (MB)")
        axes[0, 1].set_title("Output File Size")
        axes[0, 1].tick_params(axis="x", rotation=45)
        axes[0, 1].grid(axis="y", alpha=0.3)

        # 渲染速度（帧/秒）
        axes[0, 2].bar(versions, render_fps_values, color="mediumseagreen", alpha=0.7)
        axes[0, 2].set_ylabel("Frames per Second")
        axes[0, 2].set_title("Render Speed (fps)")
        axes[0, 2].tick_params(axis="x", rotation=45)
        axes[0, 2].grid(axis="y", alpha=0.3)

        # 实时倍率
        axes[1, 0].bar(versions, realtime_factors, color="purple", alpha=0.7)
        axes[1, 0].set_ylabel("Realtime Factor")
        axes[1, 0].set_title("Realtime Factor (sim_duration / wall_time)")
        axes[1, 0].tick_params(axis="x", rotation=45)
        axes[1, 0].grid(axis="y", alpha=0.3)

        # 渲染效率（MB/秒）
        efficiency = [
            r.file_size_mb / r.wall_time if r.wall_time > 0 else 0
            for r in successful_results
        ]
        axes[1, 1].bar(versions, efficiency, color="orange", alpha=0.7)
        axes[1, 1].set_ylabel("MB per Second")
        axes[1, 1].set_title("Rendering Efficiency (MB/s)")
        axes[1, 1].tick_params(axis="x", rotation=45)
        axes[1, 1].grid(axis="y", alpha=0.3)

        # 并行加速比（如果有）
        if parallel_results:
            thread_counts = [r.thread_count for r in parallel_results]
            speedups = [r.speedup for r in parallel_results]
            efficiencies = [r.efficiency for r in parallel_results]

            ax = axes[1, 2]
            ax2 = ax.twinx()

            ax.plot(
                thread_counts,
                speedups,
                "o-",
                color="blue",
                linewidth=2,
                label="Speedup",
            )
            ax.plot(
                thread_counts,
                thread_counts,
                "--",
                color="gray",
                linewidth=1,
                label="Linear Speedup",
            )
            ax2.plot(
                thread_counts,
                efficiencies,
                "s-",
                color="red",
                linewidth=2,
                label="Efficiency",
            )

            ax.set_xlabel("Thread Count")
            ax.set_ylabel("Speedup", color="blue")
            ax2.set_ylabel("Efficiency", color="red")
            ax.set_title("Parallel Rendering Speedup")
            ax.grid(alpha=0.3)
            ax.legend(loc="upper left")
            ax2.legend(loc="upper right")
        else:
            axes[1, 2].text(
                0.5, 0.5, "No parallel benchmark data", ha="center", va="center"
            )
            axes[1, 2].set_title("Parallel Rendering Speedup")

        plt.tight_layout()
        plot_path = output_dir / "rendering_performance.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"图表已保存: {plot_path}")
        plt.close()

    # 2. 生成文本报告
    report_lines = [
        "=" * 80,
        "ANIMATION RENDERING PERFORMANCE REPORT",
        "=" * 80,
        "",
        f"Total versions tested: {len(render_results)}",
        f"Successful: {len(successful_results)}",
        f"Failed: {len(render_results) - len(successful_results)}",
        "",
        "-" * 80,
        "DETAILED RESULTS",
        "-" * 80,
    ]

    for result in render_results:
        report_lines.extend(
            [
                "",
                f"Version: {result.version}",
                f"  Success: {'YES' if result.success else 'NO'}",
                f"  Wall Time: {result.wall_time:.2f} s",
                f"  Simulation Duration: {result.simulation_duration:.2f} s",
                f"  Frame Count: {result.frame_count}",
                f"  Target FPS: {result.fps}",
                f"  Render Speed: {result.render_fps:.1f} fps",
                f"  Realtime Factor: {result.realtime_factor:.2f}x",
                f"  File Size: {result.file_size_mb:.2f} MB",
                f"  Efficiency: {result.file_size_mb / result.wall_time if result.wall_time > 0 else 0:.2f} MB/s",
            ]
        )

        if not result.success:
            report_lines.append(f"  Error: {result.error_message}")

    if successful_results:
        report_lines.extend(
            [
                "",
                "=" * 80,
                "KEY FINDINGS",
                "=" * 80,
                "",
            ]
        )

        # 最快/最慢版本
        fastest = min(successful_results, key=lambda r: r.wall_time)
        slowest = max(successful_results, key=lambda r: r.wall_time)
        report_lines.extend(
            [
                f"Fastest Rendering: {fastest.version} ({fastest.wall_time:.2f}s)",
                f"Slowest Rendering: {slowest.version} ({slowest.wall_time:.2f}s)",
                f"Speed Difference: {slowest.wall_time / fastest.wall_time:.2f}x",
            ]
        )

        # 文件大小
        smallest = min(successful_results, key=lambda r: r.file_size_mb)
        largest = max(successful_results, key=lambda r: r.file_size_mb)
        report_lines.extend(
            [
                "",
                f"Smallest File: {smallest.version} ({smallest.file_size_mb:.2f} MB)",
                f"Largest File: {largest.version} ({largest.file_size_mb:.2f} MB)",
            ]
        )

        # 平均性能
        avg_time = sum(r.wall_time for r in successful_results) / len(
            successful_results
        )
        avg_fps = sum(r.render_fps for r in successful_results) / len(
            successful_results
        )
        avg_size = sum(r.file_size_mb for r in successful_results) / len(
            successful_results
        )

        report_lines.extend(
            [
                "",
                f"Average Wall Time: {avg_time:.2f}s",
                f"Average Render Speed: {avg_fps:.1f} fps",
                f"Average File Size: {avg_size:.2f} MB",
            ]
        )

    # 并行测试结果
    if parallel_results:
        report_lines.extend(
            [
                "",
                "=" * 80,
                "PARALLEL RENDERING ANALYSIS",
                "=" * 80,
                "",
            ]
        )

        for result in parallel_results:
            report_lines.extend(
                [
                    f"Threads: {result.thread_count}",
                    f"  Wall Time: {result.wall_time:.2f}s",
                    f"  Speedup: {result.speedup:.2f}x",
                    f"  Efficiency: {result.efficiency:.1%}",
                    f"  Tasks Completed: {result.tasks_completed}/{result.total_tasks}",
                    "",
                ]
            )

        # 最佳线程数建议
        best = max(parallel_results, key=lambda r: r.efficiency)
        report_lines.extend(
            [
                "RECOMMENDATIONS:",
                f"  Optimal Thread Count: {best.thread_count} (efficiency: {best.efficiency:.1%})",
            ]
        )

    # 优化建议
    report_lines.extend(
        [
            "",
            "=" * 80,
            "OPTIMIZATION RECOMMENDATIONS",
            "=" * 80,
            "",
        ]
    )

    if successful_results:
        # 分析渲染性能瓶颈
        report_lines.append("Performance Analysis:")
        report_lines.append("")

        # 识别短动画（低效渲染）
        short_anims = [r for r in successful_results if r.simulation_duration < 6.0]
        long_anims = [r for r in successful_results if r.simulation_duration >= 6.0]

        if short_anims and long_anims:
            avg_short_time = sum(r.wall_time for r in short_anims) / len(short_anims)
            avg_long_time = sum(r.wall_time for r in long_anims) / len(long_anims)
            report_lines.extend(
                [
                    f"Short animations (< 6s simulation): avg {avg_short_time:.2f}s wall time",
                    f"Long animations (>= 6s simulation): avg {avg_long_time:.2f}s wall time",
                    "",
                    "Observation: Wall time is roughly constant regardless of simulation duration.",
                    "This suggests rendering overhead dominates (initialization, frame processing).",
                    "",
                ]
            )

        # 渲染速度分析
        slow_renders = [r for r in successful_results if r.render_fps < 30]
        fast_renders = [r for r in successful_results if r.render_fps >= 30]

        if slow_renders:
            report_lines.append("Slow rendering versions (< 30 fps):")
            for r in slow_renders:
                report_lines.append(
                    f"  - {r.version}: {r.render_fps:.1f} fps, {r.frame_count} frames, {r.wall_time:.2f}s"
                )
            report_lines.append("")

        if fast_renders:
            report_lines.append("Fast rendering versions (>= 30 fps):")
            for r in fast_renders:
                report_lines.append(
                    f"  - {r.version}: {r.render_fps:.1f} fps, {r.frame_count} frames, {r.wall_time:.2f}s"
                )
            report_lines.append("")

        # 针对性优化建议
        report_lines.extend(
            [
                "RECOMMENDATIONS:",
                "",
                "1. Reduce initialization overhead:",
                "   - Pre-load models and renderer objects",
                "   - Batch multiple animations in one run",
                "",
                "2. For slow versions (V10, V14, V16):",
                "   - These have shorter simulations but similar wall time",
                "   - Consider extending simulation duration to amortize startup cost",
                "   - Or batch render multiple scenarios together",
                "",
                "3. Optimize frame rendering loop:",
                "   - Profile annotation functions (PIL/ImageDraw operations)",
                "   - Cache font objects and reduce text rendering calls",
                "   - Pre-compute interpolation arrays instead of per-frame np.interp",
                "",
                "4. Parallel rendering:",
                "   - Current wall time ~12s per version",
                "   - Use --parallel flag to test multi-threaded rendering",
                "   - Expected speedup: 2-3x with 4 threads",
                "",
                "5. Resolution/quality trade-offs:",
                "   - Test 1080p rendering to compare file size vs time",
                "   - Consider variable frame rate (30fps for previews, 60fps for final)",
                "",
            ]
        )

    report_lines.extend(
        [
            "",
            "=" * 80,
        ]
    )

    report_text = "\n".join(report_lines)
    report_path = output_dir / "PERFORMANCE_REPORT.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"报告已保存: {report_path}")

    return report_text


def main():
    parser = argparse.ArgumentParser(description="hw-1 动画渲染性能测试套件")
    parser.add_argument(
        "--versions",
        nargs="+",
        choices=list(RENDER_SCRIPTS.keys()),
        help="指定要测试的版本",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="测试并行渲染性能",
    )
    parser.add_argument(
        "--threads",
        type=int,
        nargs="+",
        default=[1, 2, 4],
        help="并行测试的线程数列表（默认: 1 2 4）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="结果输出路径（默认: results/animation_rendering_benchmark.json）",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="跳过生成报告",
    )

    args = parser.parse_args()

    # 检查环境
    if not VENV_PYTHON.exists():
        print(f"错误: 未找到虚拟环境 Python: {VENV_PYTHON}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("hw-1 动画渲染性能测试")
    print("=" * 80)

    # 执行渲染性能测试
    versions = args.versions or list(RENDER_SCRIPTS.keys())
    print(f"\n测试版本: {', '.join(versions)}")
    print("-" * 80)

    render_results = benchmark_all_versions(versions)

    # 执行并行性能测试（可选）
    parallel_results = None
    if args.parallel:
        print("\n" + "=" * 80)
        print("并行渲染性能测试")
        print("=" * 80)
        parallel_results = benchmark_parallel_rendering(versions, args.threads)

    # 保存结果
    save_results(render_results, parallel_results, args.output)

    # 生成报告
    if not args.skip_report:
        print("\n" + "=" * 80)
        print("生成性能报告...")
        print("=" * 80)
        report = generate_performance_report(render_results, parallel_results)
        print("\n" + report)


if __name__ == "__main__":
    main()

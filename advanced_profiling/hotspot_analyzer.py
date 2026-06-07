"""热点分析工具 - 使用 line_profiler 进行逐行性能分析。

识别代码中最耗时的函数和代码行，生成详细的性能报告。
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from line_profiler import LineProfiler
except ImportError:
    LineProfiler = None  # type: ignore

HW1_ROOT = Path(__file__).resolve().parent.parent


class HotspotAnalyzer:
    """热点分析器 - 逐行性能分析。"""

    def __init__(self):
        if LineProfiler is None:
            raise ImportError(
                "line_profiler 未安装。请运行: pip install line_profiler"
            )
        self.profiler = LineProfiler()
        self.results: dict[str, Any] = {}

    def add_function(self, func: Callable) -> None:
        """添加要分析的函数。"""
        self.profiler.add_function(func)

    def add_module_functions(self, module: Any, exclude_private: bool = True) -> int:
        """添加模块中的所有函数。

        Args:
            module: 要分析的模块
            exclude_private: 是否排除私有函数（以_开头）

        Returns:
            添加的函数数量
        """
        count = 0
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj):
                if exclude_private and name.startswith("_"):
                    continue
                # 只添加定义在该模块中的函数
                if obj.__module__ == module.__name__:
                    self.profiler.add_function(obj)
                    count += 1
        return count

    def profile_function(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> tuple[Any, dict[str, Any]]:
        """分析单个函数调用。

        Args:
            func: 要分析的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            (函数返回值, 分析结果字典)
        """
        self.profiler.add_function(func)
        self.profiler.enable()
        result = func(*args, **kwargs)
        self.profiler.disable()

        stats = self.profiler.get_stats()
        analysis = self._analyze_stats(stats)
        return result, analysis

    def _analyze_stats(self, stats: Any) -> dict[str, Any]:
        """分析 line_profiler 统计数据。"""
        hotspots = []

        for key, timings in stats.timings.items():
            filename, start_line, func_name = key
            total_time = 0.0
            line_stats = []

            for line_no, hits, time_us in timings:
                total_time += time_us
                if hits > 0:
                    line_stats.append(
                        {
                            "line": line_no,
                            "hits": hits,
                            "time_us": time_us,
                            "per_hit_us": time_us / hits,
                        }
                    )

            # 按耗时排序
            line_stats.sort(key=lambda x: x["time_us"], reverse=True)

            hotspots.append(
                {
                    "function": func_name,
                    "file": filename,
                    "start_line": start_line,
                    "total_time_us": total_time,
                    "total_time_ms": total_time / 1000.0,
                    "line_count": len(line_stats),
                    "top_lines": line_stats[:10],  # Top 10 最耗时的行
                }
            )

        # 按总耗时排序
        hotspots.sort(key=lambda x: x["total_time_us"], reverse=True)

        total_time_us = sum(h["total_time_us"] for h in hotspots)
        for h in hotspots:
            h["percent"] = (
                100.0 * h["total_time_us"] / total_time_us if total_time_us > 0 else 0
            )

        return {
            "total_time_us": total_time_us,
            "total_time_ms": total_time_us / 1000.0,
            "total_time_s": total_time_us / 1_000_000.0,
            "hotspots": hotspots,
            "top_10_functions": hotspots[:10],
        }

    def print_results(self, analysis: dict[str, Any], top_n: int = 10) -> None:
        """打印分析结果。"""
        print("\n" + "=" * 80)
        print("热点分析结果 (Line Profiler)")
        print("=" * 80)
        print(f"\n总耗时: {analysis['total_time_s']:.3f}s")
        print(f"\n前 {top_n} 个最耗时的函数:\n")

        for i, hotspot in enumerate(analysis["top_10_functions"][:top_n], 1):
            print(f"{i}. {hotspot['function']} - {hotspot['total_time_ms']:.2f}ms ({hotspot['percent']:.1f}%)")
            print(f"   文件: {hotspot['file']}:{hotspot['start_line']}")

            if hotspot["top_lines"]:
                print("   最耗时的代码行:")
                for line_info in hotspot["top_lines"][:5]:
                    print(
                        f"     Line {line_info['line']}: {line_info['time_us']/1000:.2f}ms "
                        f"({line_info['hits']} hits, {line_info['per_hit_us']:.2f}µs/hit)"
                    )
            print()

    def save_report(self, analysis: dict[str, Any], output_path: Path) -> None:
        """保存详细报告到文件。"""
        lines = []
        lines.append("=" * 80)
        lines.append("热点分析报告 (Line Profiler)")
        lines.append("=" * 80)
        lines.append(f"\n总耗时: {analysis['total_time_s']:.3f}s\n")

        lines.append("\n所有函数性能统计:\n")
        for i, hotspot in enumerate(analysis["hotspots"], 1):
            lines.append(
                f"\n{i}. {hotspot['function']} - {hotspot['total_time_ms']:.2f}ms ({hotspot['percent']:.1f}%)"
            )
            lines.append(f"   文件: {hotspot['file']}:{hotspot['start_line']}")
            lines.append(f"   代码行数: {hotspot['line_count']}")

            if hotspot["top_lines"]:
                lines.append("   最耗时的代码行:")
                for line_info in hotspot["top_lines"]:
                    lines.append(
                        f"     Line {line_info['line']}: {line_info['time_us']/1000:.2f}ms "
                        f"({line_info['hits']} hits, {line_info['per_hit_us']:.2f}µs/hit)"
                    )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n详细报告已保存: {output_path}")


def profile_simulation_module(
    module_name: str, simulation_func_name: str, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """分析仿真模块的性能。

    Args:
        module_name: 模块名称 (如 'simulate_rolling_foot_gait_v10')
        simulation_func_name: 仿真函数名称 (如 'run_simulation')
        *args: 仿真函数参数
        **kwargs: 仿真函数关键字参数

    Returns:
        分析结果字典
    """
    analyzer = HotspotAnalyzer()

    # 动态导入模块
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法找到模块: {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # 添加模块中的所有函数
    func_count = analyzer.add_module_functions(module)
    print(f"已添加 {func_count} 个函数进行分析")

    # 获取仿真函数
    sim_func = getattr(module, simulation_func_name)

    # 运行分析
    print(f"\n开始分析 {module_name}.{simulation_func_name}...")
    _, analysis = analyzer.profile_function(sim_func, *args, **kwargs)

    # 打印结果
    analyzer.print_results(analysis)

    # 保存报告
    output_dir = HW1_ROOT / "advanced_profiling" / "reports"
    output_path = output_dir / f"{module_name}_hotspot.txt"
    analyzer.save_report(analysis, output_path)

    return analysis


if __name__ == "__main__":
    # 示例: 分析 V10 仿真
    print("热点分析示例 - V10 Rolling Foot Gait")
    print("需要先安装: pip install line_profiler")

    if LineProfiler is None:
        print("\n错误: line_profiler 未安装")
        print("请运行: pip install line_profiler")
        sys.exit(1)

    # 添加 V10 模块路径
    v10_path = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
    sys.path.insert(0, str(v10_path))

    from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

    # 使用短时仿真进行分析
    params = RollingFootParams(duration=3.0)

    try:
        analysis = profile_simulation_module(
            "simulate_rolling_foot_gait_v10",
            "run_simulation",
            params,
            save_prefix=None,
            sample_hz=20.0,
        )
        print(f"\n分析完成! 总耗时: {analysis['total_time_s']:.3f}s")
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback

        traceback.print_exc()

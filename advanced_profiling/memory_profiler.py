"""内存分析工具 - 使用 memory_profiler 分析内存使用。

识别内存密集型操作、内存泄漏和数组预分配机会。
"""

from __future__ import annotations

import gc
import sys
import tracemalloc
from pathlib import Path
from typing import Any, Callable

try:
    from memory_profiler import profile as memory_profile
except ImportError:
    memory_profile = None  # type: ignore

HW1_ROOT = Path(__file__).resolve().parent.parent


class MemoryAnalyzer:
    """内存分析器 - 追踪内存分配和使用。"""

    def __init__(self):
        self.snapshots: list[Any] = []
        self.peak_memory = 0.0
        self.allocation_stats: dict[str, Any] = {}

    def start(self) -> None:
        """开始内存追踪。"""
        tracemalloc.start()
        gc.collect()
        self.snapshots = [tracemalloc.take_snapshot()]

    def snapshot(self, label: str = "") -> dict[str, Any]:
        """创建内存快照。"""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append(snapshot)

        current, peak = tracemalloc.get_traced_memory()
        self.peak_memory = max(self.peak_memory, peak)

        return {
            "label": label,
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
            "snapshot": snapshot,
        }

    def stop(self) -> dict[str, Any]:
        """停止追踪并返回统计信息。"""
        final_snapshot = self.snapshot("final")
        tracemalloc.stop()

        return {
            "peak_memory_mb": self.peak_memory / 1024 / 1024,
            "final_memory_mb": final_snapshot["current_mb"],
            "snapshots": len(self.snapshots),
        }

    def compare_snapshots(
        self, snapshot1_idx: int = 0, snapshot2_idx: int = -1
    ) -> list[dict[str, Any]]:
        """比较两个快照，识别内存增长。"""
        if len(self.snapshots) < 2:
            return []

        snap1 = self.snapshots[snapshot1_idx]
        snap2 = self.snapshots[snapshot2_idx]

        top_stats = snap2.compare_to(snap1, "lineno")

        differences = []
        for stat in top_stats[:20]:  # Top 20 内存增长
            differences.append(
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_diff_mb": stat.size_diff / 1024 / 1024,
                    "count_diff": stat.count_diff,
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count,
                }
            )

        return differences

    def analyze_top_allocations(self, top_n: int = 10) -> list[dict[str, Any]]:
        """分析最大的内存分配。"""
        if not self.snapshots:
            return []

        snapshot = self.snapshots[-1]
        top_stats = snapshot.statistics("lineno")

        allocations = []
        for stat in top_stats[:top_n]:
            allocations.append(
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count,
                    "avg_size_kb": (
                        stat.size / stat.count / 1024 if stat.count > 0 else 0
                    ),
                }
            )

        return allocations

    def print_report(self, stats: dict[str, Any]) -> None:
        """打印内存分析报告。"""
        print("\n" + "=" * 80)
        print("内存分析报告")
        print("=" * 80)
        print(f"\n峰值内存: {stats['peak_memory_mb']:.2f} MB")
        print(f"最终内存: {stats['final_memory_mb']:.2f} MB")

        if "top_allocations" in stats:
            print("\n前 10 个最大内存分配:\n")
            for i, alloc in enumerate(stats["top_allocations"][:10], 1):
                print(f"{i}. {alloc['size_mb']:.2f} MB ({alloc['count']} 对象)")
                print(f"   平均大小: {alloc['avg_size_kb']:.2f} KB")
                print(f"   位置: {alloc['file']}")
                print()

        if "memory_growth" in stats and stats["memory_growth"]:
            print("\n内存增长 Top 10:\n")
            for i, diff in enumerate(stats["memory_growth"][:10], 1):
                if diff["size_diff_mb"] > 0:
                    print(
                        f"{i}. +{diff['size_diff_mb']:.2f} MB ({diff['count_diff']:+d} 对象)"
                    )
                    print(f"   当前: {diff['size_mb']:.2f} MB ({diff['count']} 对象)")
                    print(f"   位置: {diff['file']}")
                    print()


def profile_memory(
    func: Callable, *args: Any, **kwargs: Any
) -> tuple[Any, dict[str, Any]]:
    """分析函数的内存使用。

    Args:
        func: 要分析的函数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        (函数返回值, 内存统计字典)
    """
    analyzer = MemoryAnalyzer()

    print(f"开始内存分析: {func.__name__}")
    analyzer.start()

    # 初始快照
    analyzer.snapshot("start")

    # 运行函数
    result = func(*args, **kwargs)

    # 结束快照
    analyzer.snapshot("end")
    stats = analyzer.stop()

    # 分析内存分配
    stats["top_allocations"] = analyzer.analyze_top_allocations(top_n=10)
    stats["memory_growth"] = analyzer.compare_snapshots(0, -1)

    # 打印报告
    analyzer.print_report(stats)

    return result, stats


def detect_memory_leaks(
    func: Callable, iterations: int = 3, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """检测内存泄漏 - 多次运行函数观察内存增长。

    Args:
        func: 要测试的函数
        iterations: 运行次数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        泄漏检测结果
    """
    analyzer = MemoryAnalyzer()
    analyzer.start()

    memory_per_iteration = []

    for i in range(iterations):
        gc.collect()
        snapshot = analyzer.snapshot(f"iteration_{i}")
        memory_per_iteration.append(snapshot["current_mb"])

        # 运行函数
        _ = func(*args, **kwargs)

    gc.collect()
    final_snapshot = analyzer.snapshot("final")
    memory_per_iteration.append(final_snapshot["current_mb"])

    analyzer.stop()

    # 分析内存增长趋势
    memory_diffs = [
        memory_per_iteration[i + 1] - memory_per_iteration[i]
        for i in range(len(memory_per_iteration) - 1)
    ]

    avg_growth = sum(memory_diffs) / len(memory_diffs) if memory_diffs else 0
    total_growth = memory_per_iteration[-1] - memory_per_iteration[0]

    has_leak = avg_growth > 0.1  # 如果每次迭代平均增长 > 0.1 MB

    result = {
        "iterations": iterations,
        "memory_per_iteration_mb": memory_per_iteration,
        "memory_diffs_mb": memory_diffs,
        "avg_growth_mb": avg_growth,
        "total_growth_mb": total_growth,
        "has_potential_leak": has_leak,
        "peak_memory_mb": analyzer.peak_memory / 1024 / 1024,
    }

    print("\n" + "=" * 80)
    print("内存泄漏检测结果")
    print("=" * 80)
    print(f"\n运行次数: {iterations}")
    print(f"总内存增长: {total_growth:.2f} MB")
    print(f"平均每次增长: {avg_growth:.2f} MB")
    print(f"峰值内存: {result['peak_memory_mb']:.2f} MB")
    print(f"\n潜在泄漏: {'是' if has_leak else '否'}")

    if has_leak:
        print("\n警告: 检测到潜在内存泄漏!")
        print("建议检查:")
        print("  1. 是否有未清理的大型数组")
        print("  2. 是否有循环引用")
        print("  3. 是否缓存了不必要的数据")

    return result


def identify_preallocation_opportunities(
    simulation_data: list[dict], data_keys: list[str]
) -> dict[str, Any]:
    """识别数组预分配机会。

    Args:
        simulation_data: 仿真数据列表
        data_keys: 数据字段键

    Returns:
        预分配建议
    """
    import numpy as np

    n_steps = len(simulation_data)
    n_fields = len(data_keys)

    # 估算当前内存使用（list of dicts）
    # 假设每个 dict 约 200 bytes overhead, 每个 float 8 bytes
    current_memory_mb = (n_steps * 200 + n_steps * n_fields * 8) / 1024 / 1024

    # 预分配 numpy 数组的内存使用
    preallocated_memory_mb = (n_steps * n_fields * 8) / 1024 / 1024

    memory_saving_mb = current_memory_mb - preallocated_memory_mb
    saving_percent = 100 * memory_saving_mb / current_memory_mb

    result = {
        "n_steps": n_steps,
        "n_fields": n_fields,
        "current_memory_mb": current_memory_mb,
        "preallocated_memory_mb": preallocated_memory_mb,
        "memory_saving_mb": memory_saving_mb,
        "saving_percent": saving_percent,
    }

    print("\n" + "=" * 80)
    print("数组预分配分析")
    print("=" * 80)
    print(f"\n仿真步数: {n_steps}")
    print(f"数据字段数: {n_fields}")
    print(f"\n当前内存 (list[dict]): {current_memory_mb:.2f} MB")
    print(f"预分配内存 (numpy array): {preallocated_memory_mb:.2f} MB")
    print(f"节省: {memory_saving_mb:.2f} MB ({saving_percent:.1f}%)")

    print("\n建议实现:")
    print("```python")
    print("import numpy as np")
    print(f"n_steps = {n_steps}")
    print(f"n_fields = {n_fields}")
    print("data_array = np.zeros((n_steps, n_fields), dtype=np.float64)")
    print("# 在仿真循环中直接写入 data_array[step_idx, :]")
    print(
        "# 结束后转换: rows = [dict(zip(keys, data_array[i])) for i in range(n_steps)]"
    )
    print("```")

    return result


def save_memory_report(stats: dict[str, Any], output_path: Path) -> None:
    """保存内存分析报告。"""
    lines = []
    lines.append("=" * 80)
    lines.append("内存分析报告")
    lines.append("=" * 80)
    lines.append(f"\n峰值内存: {stats['peak_memory_mb']:.2f} MB")
    lines.append(f"最终内存: {stats['final_memory_mb']:.2f} MB\n")

    if "top_allocations" in stats:
        lines.append("\n前 10 个最大内存分配:\n")
        for i, alloc in enumerate(stats["top_allocations"][:10], 1):
            lines.append(f"{i}. {alloc['size_mb']:.2f} MB ({alloc['count']} 对象)")
            lines.append(f"   平均大小: {alloc['avg_size_kb']:.2f} KB")
            lines.append(f"   位置: {alloc['file']}")
            lines.append("")

    if "memory_growth" in stats and stats["memory_growth"]:
        lines.append("\n内存增长分析:\n")
        for i, diff in enumerate(stats["memory_growth"][:10], 1):
            if diff["size_diff_mb"] > 0:
                lines.append(
                    f"{i}. +{diff['size_diff_mb']:.2f} MB ({diff['count_diff']:+d} 对象)"
                )
                lines.append(
                    f"   当前: {diff['size_mb']:.2f} MB ({diff['count']} 对象)"
                )
                lines.append(f"   位置: {diff['file']}")
                lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n内存报告已保存: {output_path}")


if __name__ == "__main__":
    print("内存分析示例")
    print("使用 tracemalloc (Python 标准库) 进行内存追踪")

    # 示例: 分析一个简单函数
    def create_large_list(n: int) -> list[float]:
        """创建大型列表用于测试。"""
        import numpy as np

        return [float(x) for x in np.random.random(n)]

    print("\n测试 1: 基本内存分析")
    result, stats = profile_memory(create_large_list, 1000000)
    print(f"创建了 {len(result)} 个元素")

    print("\n测试 2: 内存泄漏检测")
    leak_stats = detect_memory_leaks(create_large_list, iterations=3, n=500000)

    # 保存报告
    output_dir = HW1_ROOT / "advanced_profiling" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_memory_report(stats, output_dir / "memory_example.txt")

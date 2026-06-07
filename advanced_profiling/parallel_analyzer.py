"""并行化分析工具 - 识别并行化机会并评估收益。

分析代码中可并行的循环，使用 Amdahl's law 评估潜在加速比。
"""

from __future__ import annotations

import ast
import inspect
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

HW1_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ParallelOpportunity:
    """并行化机会。"""

    location: str  # 文件:行号
    function_name: str
    loop_type: str  # for/while
    loop_variable: str
    iteration_count_estimate: int | str
    independence_score: float  # 0-1, 1=完全独立
    potential_speedup: float  # 估算加速比
    difficulty: str  # easy/medium/hard
    recommendation: str
    code_snippet: str


class ParallelAnalyzer:
    """并行化分析器。"""

    def __init__(self):
        self.opportunities: list[ParallelOpportunity] = []

    def analyze_function(self, func: Callable) -> list[ParallelOpportunity]:
        """分析函数中的并行化机会。"""
        source = inspect.getsource(func)
        tree = ast.parse(source)

        opportunities = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                opp = self._analyze_for_loop(node, func)
                if opp:
                    opportunities.append(opp)

        self.opportunities.extend(opportunities)
        return opportunities

    def _analyze_for_loop(
        self, node: ast.For, func: Callable
    ) -> ParallelOpportunity | None:
        """分析 for 循环的并行化潜力。"""
        # 获取循环变量
        if isinstance(node.target, ast.Name):
            loop_var = node.target.id
        else:
            loop_var = "unknown"

        # 分析迭代对象
        iter_info = self._analyze_iterator(node.iter)

        # 分析循环体独立性
        independence = self._analyze_loop_independence(node)

        # 估算潜在加速
        speedup = self._estimate_speedup(independence, iter_info["count"])

        # 确定实现难度
        difficulty = self._assess_difficulty(independence, node)

        # 生成建议
        recommendation = self._generate_recommendation(
            independence, speedup, difficulty, func.__name__, loop_var
        )

        # 提取代码片段
        code_snippet = ast.unparse(node) if hasattr(ast, "unparse") else "<code>"

        return ParallelOpportunity(
            location=f"{func.__module__}:{func.__name__}",
            function_name=func.__name__,
            loop_type="for",
            loop_variable=loop_var,
            iteration_count_estimate=iter_info["count"],
            independence_score=independence,
            potential_speedup=speedup,
            difficulty=difficulty,
            recommendation=recommendation,
            code_snippet=code_snippet[:200],  # 限制长度
        )

    def _analyze_iterator(self, node: ast.expr) -> dict[str, Any]:
        """分析迭代器类型和大小。"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "range":
                    # 尝试提取 range 参数
                    if len(node.args) == 1:
                        if isinstance(node.args[0], ast.Constant):
                            return {"type": "range", "count": node.args[0].value}
                        return {"type": "range", "count": "unknown"}
                    return {"type": "range", "count": "variable"}
                elif node.func.id in ["enumerate", "zip"]:
                    return {"type": node.func.id, "count": "variable"}

        if isinstance(node, ast.Name):
            return {"type": "iterable", "count": "unknown"}

        return {"type": "unknown", "count": "unknown"}

    def _analyze_loop_independence(self, node: ast.For) -> float:
        """分析循环迭代的独立性 (0-1)。"""
        # 简化的独立性分析
        # 检查循环体中是否有依赖前一次迭代的操作

        has_append = False
        has_shared_write = False
        has_accumulator = False

        for body_node in ast.walk(node):
            # 检查是否有 append 操作（通常是独立的）
            if isinstance(body_node, ast.Call):
                if isinstance(body_node.func, ast.Attribute):
                    if body_node.func.attr == "append":
                        has_append = True

            # 检查是否有累加操作（有依赖）
            if isinstance(body_node, ast.AugAssign):
                has_accumulator = True

            # 检查是否有共享变量写入
            if isinstance(body_node, ast.Assign):
                has_shared_write = True

        # 评分逻辑
        score = 1.0

        if has_accumulator:
            score -= 0.4  # 累加操作降低独立性
        if has_shared_write and not has_append:
            score -= 0.3  # 共享写入降低独立性

        return max(0.0, min(1.0, score))

    def _estimate_speedup(
        self, independence: float, iteration_count: int | str
    ) -> float:
        """使用 Amdahl's law 估算加速比。

        Args:
            independence: 独立性得分 (0-1)
            iteration_count: 迭代次数

        Returns:
            估算的加速比
        """
        import os

        n_cores = os.cpu_count() or 4

        # 并行部分比例 (基于独立性)
        p = independence * 0.9  # 假设最多 90% 可并行

        # Amdahl's law: Speedup = 1 / ((1-p) + p/n)
        speedup = 1.0 / ((1 - p) + p / n_cores)

        # 考虑迭代次数（太少则开销大于收益）
        if isinstance(iteration_count, int):
            if iteration_count < 10:
                speedup *= 0.5  # 迭代太少，并行开销大
            elif iteration_count < 100:
                speedup *= 0.8

        return speedup

    def _assess_difficulty(self, independence: float, node: ast.For) -> str:
        """评估并行化实现难度。"""
        if independence >= 0.8:
            return "easy"
        elif independence >= 0.5:
            return "medium"
        else:
            return "hard"

    def _generate_recommendation(
        self,
        independence: float,
        speedup: float,
        difficulty: str,
        func_name: str,
        loop_var: str,
    ) -> str:
        """生成并行化建议。"""
        if independence < 0.3:
            return "不推荐并行化: 迭代间依赖性太强"

        if speedup < 1.2:
            return "不推荐并行化: 预期加速比太低 (< 1.2x)"

        if difficulty == "easy":
            return f"推荐使用 joblib.Parallel: 预期 {speedup:.1f}x 加速"
        elif difficulty == "medium":
            return f"可考虑并行化: 需重构以减少共享状态，预期 {speedup:.1f}x 加速"
        else:
            return f"并行化困难: 需要重大重构，预期 {speedup:.1f}x 加速"

    def print_report(self) -> None:
        """打印并行化分析报告。"""
        print("\n" + "=" * 80)
        print("并行化机会分析报告")
        print("=" * 80)

        if not self.opportunities:
            print("\n未发现明显的并行化机会。")
            return

        print(f"\n发现 {len(self.opportunities)} 个潜在并行化机会:\n")

        # 按加速比排序
        sorted_opps = sorted(
            self.opportunities, key=lambda x: x.potential_speedup, reverse=True
        )

        for i, opp in enumerate(sorted_opps, 1):
            print(f"{i}. {opp.function_name} - 预期加速 {opp.potential_speedup:.1f}x")
            print(f"   位置: {opp.location}")
            print(f"   循环变量: {opp.loop_variable}")
            print(f"   迭代次数: {opp.iteration_count_estimate}")
            print(f"   独立性: {opp.independence_score:.2f}")
            print(f"   难度: {opp.difficulty}")
            print(f"   建议: {opp.recommendation}")
            print()

    def generate_parallel_code(self, opp: ParallelOpportunity) -> str:
        """生成并行化代码模板。"""
        if opp.difficulty == "hard" or opp.potential_speedup < 1.2:
            return "# 不推荐并行化此循环"

        template = f"""
# 并行化: {opp.function_name}
from joblib import Parallel, delayed

def process_single_{opp.loop_variable}({opp.loop_variable}):
    # 原循环体代码
    # ...
    return result

# 并行执行
results = Parallel(n_jobs=-1)(
    delayed(process_single_{opp.loop_variable})({opp.loop_variable})
    for {opp.loop_variable} in iterable
)
"""
        return template


def benchmark_parallel_vs_sequential(
    func: Callable, items: list[Any], n_jobs: int = -1
) -> dict[str, Any]:
    """对比并行和串行执行的性能。

    Args:
        func: 要执行的函数
        items: 输入项列表
        n_jobs: 并行作业数 (-1 表示使用所有核心)

    Returns:
        性能对比结果
    """
    from joblib import Parallel, delayed

    # 串行执行
    print(f"串行执行 {len(items)} 个任务...")
    start = time.perf_counter()
    sequential_results = [func(item) for item in items]
    sequential_time = time.perf_counter() - start

    # 并行执行
    print(f"并行执行 {len(items)} 个任务 (n_jobs={n_jobs})...")
    start = time.perf_counter()
    parallel_results = Parallel(n_jobs=n_jobs)(delayed(func)(item) for item in items)
    parallel_time = time.perf_counter() - start

    speedup = sequential_time / parallel_time if parallel_time > 0 else 0

    result = {
        "n_items": len(items),
        "sequential_time_s": sequential_time,
        "parallel_time_s": parallel_time,
        "speedup": speedup,
        "efficiency": speedup / (n_jobs if n_jobs > 0 else 1),
    }

    print("\n" + "=" * 80)
    print("并行性能基准测试")
    print("=" * 80)
    print(f"\n任务数: {result['n_items']}")
    print(f"串行耗时: {sequential_time:.2f}s")
    print(f"并行耗时: {parallel_time:.2f}s")
    print(f"加速比: {speedup:.2f}x")
    print(f"并行效率: {result['efficiency']:.2%}")

    return result


def analyze_scan_parallelization(scan_file: Path) -> dict[str, Any]:
    """分析参数扫描文件的并行化潜力。

    专门针对 hw-1 项目的 scan_*.py 文件。
    """
    print(f"\n分析参数扫描文件: {scan_file.name}")

    if not scan_file.exists():
        return {"error": "文件不存在"}

    source = scan_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # 查找主要的参数扫描循环
    scan_loops = []

    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            # 检查是否包含 run_simulation 调用
            has_simulation = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        if "simulation" in child.func.id.lower():
                            has_simulation = True

            if has_simulation:
                scan_loops.append(node)

    print(f"发现 {len(scan_loops)} 个参数扫描循环")

    if scan_loops:
        print("\n并行化建议:")
        print("```python")
        print("from joblib import Parallel, delayed")
        print("")
        print("# 定义单次仿真函数")
        print("def run_single_simulation(params):")
        print("    rows, summary = run_simulation(params, sample_hz=20.0)")
        print("    return summary")
        print("")
        print("# 并行执行")
        print("results = Parallel(n_jobs=-1)(")
        print("    delayed(run_single_simulation)(params)")
        print("    for params in candidate_params")
        print(")")
        print("```")

    return {
        "file": scan_file.name,
        "scan_loops_found": len(scan_loops),
        "parallelizable": len(scan_loops) > 0,
        "estimated_speedup": "4-8x (基于典型 CPU 核心数)",
    }


def save_parallel_report(
    opportunities: list[ParallelOpportunity], output_path: Path
) -> None:
    """保存并行化分析报告。"""
    lines = []
    lines.append("=" * 80)
    lines.append("并行化机会分析报告")
    lines.append("=" * 80)
    lines.append(f"\n发现 {len(opportunities)} 个潜在并行化机会\n")

    sorted_opps = sorted(
        opportunities, key=lambda x: x.potential_speedup, reverse=True
    )

    for i, opp in enumerate(sorted_opps, 1):
        lines.append(f"\n{i}. {opp.function_name}")
        lines.append(f"   位置: {opp.location}")
        lines.append(f"   预期加速: {opp.potential_speedup:.1f}x")
        lines.append(f"   独立性得分: {opp.independence_score:.2f}")
        lines.append(f"   实现难度: {opp.difficulty}")
        lines.append(f"   建议: {opp.recommendation}")
        lines.append(f"\n   代码片段:")
        lines.append(f"   {opp.code_snippet[:150]}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n并行化报告已保存: {output_path}")


if __name__ == "__main__":
    print("并行化分析示例")

    # 示例 1: 分析参数扫描文件
    scan_files = [
        HW1_ROOT / "v10_rolling_foot_biomimetic_gait" / "scan_rolling_foot_params_v10.py",
        HW1_ROOT / "v13_7_friction_compensation" / "scan_v13_7_tauC_verify.py",
        HW1_ROOT / "v17_state_estimation" / "scan_v17_noise.py",
    ]

    for scan_file in scan_files:
        if scan_file.exists():
            result = analyze_scan_parallelization(scan_file)
            print(f"\n结果: {result}")

    # 示例 2: 性能基准测试
    print("\n\n示例: 并行 vs 串行基准测试")

    def slow_function(x: int) -> int:
        """模拟耗时计算。"""
        import time

        time.sleep(0.1)
        return x * x

    items = list(range(10))
    benchmark_parallel_vs_sequential(slow_function, items, n_jobs=-1)

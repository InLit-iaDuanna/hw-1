"""算法复杂度分析工具 - 分析时间和空间复杂度。

识别 O(n²) 或更高复杂度的代码，提供替代算法建议。
"""

from __future__ import annotations

import ast
import inspect
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

HW1_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ComplexityIssue:
    """复杂度问题。"""

    location: str
    function_name: str
    complexity: str  # O(n), O(n²), O(n log n), etc.
    issue_type: str  # nested_loops, repeated_search, etc.
    severity: str  # low/medium/high/critical
    description: str
    recommendation: str
    code_snippet: str


class ComplexityAnalyzer:
    """算法复杂度分析器。"""

    def __init__(self):
        self.issues: list[ComplexityIssue] = []

    def analyze_function(self, func: Callable) -> list[ComplexityIssue]:
        """分析函数的算法复杂度。"""
        try:
            source = inspect.getsource(func)
            # Remove leading indentation
            import textwrap

            source = textwrap.dedent(source)
            tree = ast.parse(source)
        except (OSError, TypeError, IndentationError) as e:
            return []

        issues = []

        # 检查嵌套循环
        issues.extend(self._check_nested_loops(tree, func))

        # 检查重复查找
        issues.extend(self._check_repeated_operations(tree, func))

        # 检查低效的数据结构使用
        issues.extend(self._check_inefficient_data_structures(tree, func))

        self.issues.extend(issues)
        return issues

    def _check_nested_loops(
        self, tree: ast.AST, func: Callable
    ) -> list[ComplexityIssue]:
        """检查嵌套循环（可能是 O(n²) 或更高）。"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # 检查是否有嵌套循环
                nested_level = self._count_nested_loops(node)

                if nested_level >= 2:
                    complexity = f"O(n^{nested_level})"
                    severity = "high" if nested_level >= 3 else "medium"

                    code_snippet = (
                        ast.unparse(node)
                        if hasattr(ast, "unparse")
                        else "<nested loops>"
                    )

                    issues.append(
                        ComplexityIssue(
                            location=f"{func.__module__}:{func.__name__}",
                            function_name=func.__name__,
                            complexity=complexity,
                            issue_type="nested_loops",
                            severity=severity,
                            description=f"{nested_level} 层嵌套循环，复杂度为 {complexity}",
                            recommendation=self._recommend_nested_loop_fix(
                                nested_level
                            ),
                            code_snippet=code_snippet[:200],
                        )
                    )

        return issues

    def _count_nested_loops(self, node: ast.For, level: int = 1) -> int:
        """递归计算嵌套循环层数。"""
        max_level = level

        for child in node.body:
            if isinstance(child, ast.For):
                child_level = self._count_nested_loops(child, level + 1)
                max_level = max(max_level, child_level)

        return max_level

    def _check_repeated_operations(
        self, tree: ast.AST, func: Callable
    ) -> list[ComplexityIssue]:
        """检查循环中的重复计算或查找。"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # 检查循环体中是否有重复的昂贵操作
                repeated_ops = self._find_repeated_operations(node)

                for op_type, description in repeated_ops:
                    issues.append(
                        ComplexityIssue(
                            location=f"{func.__module__}:{func.__name__}",
                            function_name=func.__name__,
                            complexity="O(n*m)",
                            issue_type=op_type,
                            severity="medium",
                            description=description,
                            recommendation=self._recommend_caching(op_type),
                            code_snippet="<loop with repeated operations>",
                        )
                    )

        return issues

    def _find_repeated_operations(self, loop_node: ast.For) -> list[tuple[str, str]]:
        """查找循环中的重复操作。"""
        repeated = []

        for node in ast.walk(loop_node):
            # 检查 list.index() 调用（O(n) 查找）
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "index":
                        repeated.append(
                            ("list_index", "循环中使用 list.index() - O(n) 查找")
                        )

            # 检查 in 操作符用于 list（O(n) 查找）
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, (ast.In, ast.NotIn)):
                        repeated.append(
                            ("list_membership", "循环中使用 'in' 查找列表元素")
                        )

            # 检查重复的三角函数计算
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ["sin", "cos", "tan", "sqrt"]:
                        repeated.append(
                            ("repeated_math", "循环中重复计算三角函数或平方根")
                        )

        return repeated

    def _check_inefficient_data_structures(
        self, tree: ast.AST, func: Callable
    ) -> list[ComplexityIssue]:
        """检查低效的数据结构使用。"""
        issues = []

        # 检查是否应该使用 set/dict 而不是 list
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # 查找频繁的成员检查
                membership_checks = 0
                for child in ast.walk(node):
                    if isinstance(child, ast.Compare):
                        for op in child.ops:
                            if isinstance(op, (ast.In, ast.NotIn)):
                                membership_checks += 1

                if membership_checks >= 3:
                    issues.append(
                        ComplexityIssue(
                            location=f"{func.__module__}:{func.__name__}",
                            function_name=func.__name__,
                            complexity="O(n²)",
                            issue_type="inefficient_membership_test",
                            severity="medium",
                            description=f"循环中有 {membership_checks} 次成员检查，应考虑使用 set",
                            recommendation="使用 set 或 dict 替代 list 进行成员检查（O(1) vs O(n)）",
                            code_snippet="<multiple membership tests>",
                        )
                    )

        return issues

    def _recommend_nested_loop_fix(self, level: int) -> str:
        """为嵌套循环提供优化建议。"""
        if level == 2:
            return "考虑: 1) 使用 numpy 向量化; 2) 使用字典/set 减少查找; 3) 预计算可复用的值"
        elif level == 3:
            return "高复杂度! 考虑: 1) 算法重构; 2) 动态规划; 3) 分治法; 4) 空间换时间"
        else:
            return "严重性能问题! 必须重构算法"

    def _recommend_caching(self, op_type: str) -> str:
        """为重复操作提供缓存建议。"""
        recommendations = {
            "list_index": "使用 dict 或创建索引映射: idx_map = {val: i for i, val in enumerate(lst)}",
            "list_membership": "转换为 set: items_set = set(items)",
            "repeated_math": "在循环外预计算: sin_vals = [math.sin(x) for x in angles]",
        }
        return recommendations.get(op_type, "缓存重复计算的结果")

    def estimate_runtime_complexity(
        self, func: Callable, input_sizes: list[int]
    ) -> dict[str, Any]:
        """通过实际运行估算时间复杂度。

        Args:
            func: 要测试的函数（接受一个 int 参数表示输入大小）
            input_sizes: 不同的输入大小进行测试

        Returns:
            复杂度估算结果
        """
        import time

        runtimes = []

        print(f"\n估算 {func.__name__} 的时间复杂度...")

        for n in input_sizes:
            start = time.perf_counter()
            func(n)
            elapsed = time.perf_counter() - start
            runtimes.append(elapsed)
            print(f"  n={n}: {elapsed:.4f}s")

        # 拟合复杂度曲线
        complexity_guess = self._guess_complexity(input_sizes, runtimes)

        return {
            "function": func.__name__,
            "input_sizes": input_sizes,
            "runtimes": runtimes,
            "estimated_complexity": complexity_guess,
        }

    def _guess_complexity(self, sizes: list[int], times: list[float]) -> str:
        """基于运行时间猜测复杂度。"""
        if len(sizes) < 2:
            return "insufficient_data"

        # 计算增长率
        ratios = []
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1] if times[i - 1] > 0 else 0
            ratios.append(time_ratio / size_ratio)

        avg_ratio = sum(ratios) / len(ratios) if ratios else 0

        # 推测复杂度
        if avg_ratio < 1.5:
            return "O(n) 或更好"
        elif avg_ratio < 3:
            return "O(n log n)"
        elif avg_ratio < 6:
            return "O(n^1.5)"
        else:
            return "O(n²) 或更高"

    def print_report(self) -> None:
        """打印复杂度分析报告。"""
        print("\n" + "=" * 80)
        print("算法复杂度分析报告")
        print("=" * 80)

        if not self.issues:
            print("\n未发现明显的复杂度问题。")
            return

        # 按严重程度分组
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for issue in self.issues:
            by_severity[issue.severity].append(issue)

        total = len(self.issues)
        print(f"\n发现 {total} 个复杂度问题:")
        for sev in ["critical", "high", "medium", "low"]:
            if by_severity[sev]:
                print(f"  {sev.upper()}: {len(by_severity[sev])}")

        print("\n详细问题:\n")

        for severity in ["critical", "high", "medium", "low"]:
            issues = by_severity[severity]
            if not issues:
                continue

            print(f"\n{severity.upper()} 优先级:\n")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue.function_name} - {issue.complexity}")
                print(f"   类型: {issue.issue_type}")
                print(f"   描述: {issue.description}")
                print(f"   建议: {issue.recommendation}")
                print()

    def save_report(self, output_path: Path) -> None:
        """保存复杂度分析报告。"""
        lines = []
        lines.append("=" * 80)
        lines.append("算法复杂度分析报告")
        lines.append("=" * 80)
        lines.append(f"\n发现 {len(self.issues)} 个复杂度问题\n")

        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for issue in self.issues:
            by_severity[issue.severity].append(issue)

        for severity in ["critical", "high", "medium", "low"]:
            issues = by_severity[severity]
            if not issues:
                continue

            lines.append(f"\n## {severity.upper()} 优先级 ({len(issues)} 个问题)\n")

            for i, issue in enumerate(issues, 1):
                lines.append(f"{i}. {issue.function_name}")
                lines.append(f"   位置: {issue.location}")
                lines.append(f"   复杂度: {issue.complexity}")
                lines.append(f"   类型: {issue.issue_type}")
                lines.append(f"   描述: {issue.description}")
                lines.append(f"   建议: {issue.recommendation}")
                lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n复杂度报告已保存: {output_path}")


def analyze_mujoco_simulation_complexity() -> dict[str, Any]:
    """分析 MuJoCo 仿真循环的复杂度。"""
    print("\nMuJoCo 仿真循环复杂度分析")
    print("=" * 80)

    analysis = {
        "simulation_loop": {
            "complexity": "O(n_steps)",
            "n_steps_typical": "3000-12000 (duration / timestep)",
            "per_step_operations": [
                "mujoco.mj_step() - O(n_contacts * n_joints) ≈ O(1) 对于固定模型",
                "control() - O(n_actuators) ≈ O(1)",
                "contact_flags() - O(n_contacts) ≈ O(1)",
                "make_row() - O(n_fields) ≈ O(1)",
            ],
            "total_complexity": "O(n_steps) - 线性复杂度",
            "bottleneck": "mujoco.mj_step() 占 60-80% 时间",
        },
        "parameter_scan": {
            "complexity": "O(n_params * n_steps)",
            "n_params_typical": "100-1000",
            "total_complexity": "O(n_params * n_steps) - 可并行化",
            "optimization": "使用 joblib 并行化可获得 4-8x 加速",
        },
        "data_recording": {
            "complexity": "O(n_steps / sample_stride)",
            "overhead": "5-15% 总时间",
            "optimization": "降低 sample_hz 或使用 numpy 数组预分配",
        },
    }

    print("\n仿真循环: O(n_steps)")
    print("  - 典型步数: 3000-12000")
    print("  - 瓶颈: mujoco.mj_step() (60-80% 时间)")
    print("  - 优化: 减少 timestep、简化模型\n")

    print("参数扫描: O(n_params * n_steps)")
    print("  - 典型参数数: 100-1000")
    print("  - 可并行化: 是")
    print("  - 优化: joblib 并行化 (4-8x 加速)\n")

    return analysis


if __name__ == "__main__":
    print("算法复杂度分析示例")

    # 示例 1: 分析嵌套循环
    def nested_loop_example(n: int) -> int:
        """O(n²) 示例。"""
        count = 0
        for i in range(n):
            for j in range(n):
                count += i * j
        return count

    analyzer = ComplexityAnalyzer()
    issues = analyzer.analyze_function(nested_loop_example)
    analyzer.print_report()

    # 示例 2: MuJoCo 仿真复杂度分析
    analyze_mujoco_simulation_complexity()

    # 保存报告
    output_dir = HW1_ROOT / "advanced_profiling" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    analyzer.save_report(output_dir / "complexity_analysis.txt")

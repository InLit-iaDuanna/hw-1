"""解决方案知识库模块。

从 YAML 知识库加载错误解决方案，并提供查询接口。
"""

from pathlib import Path
from typing import Any
import yaml


class Solution:
    """解决方案对象。"""

    def __init__(
        self,
        action: str,
        details: str,
        code: str | None = None,
        priority: int = 0
    ):
        self.action = action
        self.details = details
        self.code = code
        self.priority = priority

    def __repr__(self) -> str:
        return f"Solution(action='{self.action}')"

    def format(self, indent: int = 0) -> str:
        """格式化输出解决方案。"""
        prefix = " " * indent
        lines = [
            f"{prefix}操作: {self.action}",
            f"{prefix}详情: {self.details}"
        ]
        if self.code:
            lines.append(f"{prefix}代码:")
            for line in self.code.split("\n"):
                lines.append(f"{prefix}  {line}")
        return "\n".join(lines)


class ErrorEntry:
    """错误条目对象。"""

    def __init__(
        self,
        error_type: str,
        symptoms: list[str],
        causes: list[str],
        solutions: list[Solution],
        references: list[str],
        severity: str = "medium"
    ):
        self.error_type = error_type
        self.symptoms = symptoms
        self.causes = causes
        self.solutions = solutions
        self.references = references
        self.severity = severity

    def __repr__(self) -> str:
        return f"ErrorEntry(type='{self.error_type}', solutions={len(self.solutions)})"

    def format(self) -> str:
        """格式化输出错误条目。"""
        lines = [
            f"错误类型: {self.error_type}",
            f"严重性: {self.severity}",
            "",
            "症状:",
        ]
        for symptom in self.symptoms:
            lines.append(f"  - {symptom}")

        lines.append("")
        lines.append("可能原因:")
        for cause in self.causes:
            lines.append(f"  - {cause}")

        lines.append("")
        lines.append(f"解决方案 ({len(self.solutions)} 个):")
        for i, solution in enumerate(self.solutions, 1):
            lines.append(f"\n  方案 {i}:")
            lines.append(solution.format(indent=4))

        if self.references:
            lines.append("")
            lines.append("参考资料:")
            for ref in self.references:
                lines.append(f"  - {ref}")

        return "\n".join(lines)


class SolutionDatabase:
    """解决方案知识库。"""

    def __init__(self, yaml_path: Path | str | None = None):
        if yaml_path is None:
            # 默认路径
            yaml_path = Path(__file__).parent / "common_issues.yaml"

        self.yaml_path = Path(yaml_path)
        self.entries: dict[str, ErrorEntry] = {}
        self.categories: dict[str, list[str]] = {}

        if self.yaml_path.exists():
            self.load()

    def load(self) -> None:
        """从 YAML 文件加载知识库。"""
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 解析各个类别
        for category, errors in data.items():
            self.categories[category] = []

            for error_dict in errors:
                error_type = error_dict["error_type"]
                self.categories[category].append(error_type)

                # 解析 solutions
                solutions = []
                for i, sol_dict in enumerate(error_dict.get("solutions", [])):
                    solution = Solution(
                        action=sol_dict.get("action", ""),
                        details=sol_dict.get("details", ""),
                        code=sol_dict.get("code"),
                        priority=i
                    )
                    solutions.append(solution)

                # 创建 ErrorEntry
                entry = ErrorEntry(
                    error_type=error_type,
                    symptoms=error_dict.get("symptoms", []),
                    causes=error_dict.get("causes", []),
                    solutions=solutions,
                    references=error_dict.get("references", []),
                    severity=error_dict.get("severity", "medium")
                )

                self.entries[error_type] = entry

    def get(self, error_type: str) -> ErrorEntry | None:
        """获取指定错误类型的条目。"""
        return self.entries.get(error_type)

    def search(self, keyword: str) -> list[ErrorEntry]:
        """搜索包含关键词的错误条目。"""
        results = []
        keyword_lower = keyword.lower()

        for entry in self.entries.values():
            # 搜索错误类型
            if keyword_lower in entry.error_type.lower():
                results.append(entry)
                continue

            # 搜索症状
            if any(keyword_lower in s.lower() for s in entry.symptoms):
                results.append(entry)
                continue

            # 搜索原因
            if any(keyword_lower in c.lower() for c in entry.causes):
                results.append(entry)
                continue

        return results

    def list_categories(self) -> list[str]:
        """列出所有类别。"""
        return list(self.categories.keys())

    def list_errors_in_category(self, category: str) -> list[str]:
        """列出指定类别下的所有错误类型。"""
        return self.categories.get(category, [])

    def get_all_entries(self) -> list[ErrorEntry]:
        """获取所有错误条目。"""
        return list(self.entries.values())

    def get_solutions(self, error_type: str) -> list[Solution]:
        """获取指定错误的所有解决方案。"""
        entry = self.get(error_type)
        return entry.solutions if entry else []

    def recommend_solutions(
        self,
        error_types: list[str],
        max_solutions_per_error: int = 3
    ) -> dict[str, list[Solution]]:
        """为多个错误类型推荐解决方案。

        Args:
            error_types: 错误类型列表
            max_solutions_per_error: 每个错误返回的最大解决方案数

        Returns:
            {error_type: [Solution, ...], ...} 字典
        """
        recommendations = {}

        for error_type in error_types:
            solutions = self.get_solutions(error_type)
            # 按优先级排序，返回前 N 个
            recommendations[error_type] = solutions[:max_solutions_per_error]

        return recommendations

    def export_markdown(self, output_path: Path | str) -> None:
        """导出知识库为 Markdown 文档。"""
        output_path = Path(output_path)

        lines = [
            "# hw-1 错误诊断知识库",
            "",
            f"共收录 {len(self.entries)} 个常见错误及解决方案。",
            "",
            "## 目录",
            ""
        ]

        # 生成目录
        for category in self.categories:
            lines.append(f"### {category}")
            for error_type in self.categories[category]:
                lines.append(f"- [{error_type}](#{error_type.replace('_', '-')})")
            lines.append("")

        # 生成详细内容
        lines.append("## 详细说明")
        lines.append("")

        for category in self.categories:
            lines.append(f"### {category}")
            lines.append("")

            for error_type in self.categories[category]:
                entry = self.entries[error_type]
                lines.append(f"#### {error_type}")
                lines.append("")
                lines.append(f"**严重性**: {entry.severity}")
                lines.append("")

                lines.append("**症状**:")
                for symptom in entry.symptoms:
                    lines.append(f"- {symptom}")
                lines.append("")

                lines.append("**可能原因**:")
                for cause in entry.causes:
                    lines.append(f"- {cause}")
                lines.append("")

                lines.append(f"**解决方案** ({len(entry.solutions)} 个):")
                for i, sol in enumerate(entry.solutions, 1):
                    lines.append(f"\n{i}. **{sol.action}**")
                    lines.append(f"   - {sol.details}")
                    if sol.code:
                        lines.append(f"   - 代码示例:")
                        lines.append(f"     ```python")
                        lines.append(f"     {sol.code}")
                        lines.append(f"     ```")
                lines.append("")

                if entry.references:
                    lines.append("**参考资料**:")
                    for ref in entry.references:
                        lines.append(f"- {ref}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"知识库已导出到: {output_path}")


if __name__ == "__main__":
    # 测试示例
    db = SolutionDatabase()

    print(f"加载了 {len(db.entries)} 个错误条目")
    print(f"类别: {', '.join(db.list_categories())}")
    print()

    # 查询特定错误
    error_type = "simulation_nan"
    entry = db.get(error_type)
    if entry:
        print(entry.format())
        print("\n" + "=" * 60 + "\n")

    # 搜索关键词
    keyword = "fall"
    results = db.search(keyword)
    print(f"搜索 '{keyword}' 找到 {len(results)} 个结果:")
    for entry in results:
        print(f"  - {entry.error_type} (严重性: {entry.severity})")

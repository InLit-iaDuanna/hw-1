#!/usr/bin/env python3
"""
深度代码质量检查工具
检查代码问题、一致性、最佳实践
"""

import json
import re
from collections import defaultdict
from pathlib import Path


class CodeQualityChecker:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir)
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)

    def check_all(self):
        """执行所有检查"""
        print("=" * 80)
        print("CODE QUALITY CHECKER - Deep Analysis")
        print("=" * 80)
        print()

        self.check_import_star()
        self.check_todos()
        self.check_duplicate_requirements()
        self.check_hardcoded_paths()
        self.check_missing_docstrings()
        self.check_long_functions()
        self.check_inconsistent_naming()
        self.check_unused_imports()

        self.print_report()

    def check_import_star(self):
        """检查 import * 用法"""
        print("[1/8] Checking import * usage...")

        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"from\s+\S+\s+import\s+\*", content):
                    self.issues["import_star"].append(str(py_file))
                    self.stats["import_star"] += 1
            except Exception:
                pass

        print(f"  Found {self.stats['import_star']} files with import *")

    def check_todos(self):
        """检查 TODO/FIXME 标记"""
        print("[2/8] Checking TODO/FIXME markers...")

        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                lines = py_file.read_text(encoding="utf-8", errors="ignore").split("\n")
                for i, line in enumerate(lines, 1):
                    if re.search(r"(TODO|FIXME|XXX|HACK|BUG)", line, re.IGNORECASE):
                        self.issues["todos"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )
                        self.stats["todos"] += 1
            except Exception:
                pass

        print(f"  Found {self.stats['todos']} TODO/FIXME markers")

    def check_duplicate_requirements(self):
        """检查重复的 requirements.txt"""
        print("[3/8] Checking duplicate requirements.txt...")

        req_files = list(self.root_dir.rglob("requirements.txt"))
        req_files = [f for f in req_files if not self._should_skip(f)]

        self.stats["requirements"] = len(req_files)

        # 检查内容重复
        contents = {}
        for req_file in req_files:
            try:
                content = req_file.read_text(encoding="utf-8", errors="ignore").strip()
                if content in contents:
                    self.issues["duplicate_requirements"].append(
                        {"file1": str(contents[content]), "file2": str(req_file)}
                    )
                else:
                    contents[content] = req_file
            except Exception:
                pass

        print(f"  Found {self.stats['requirements']} requirements.txt files")
        print(f"  Found {len(self.issues['duplicate_requirements'])} duplicates")

    def check_hardcoded_paths(self):
        """检查硬编码路径"""
        print("[4/8] Checking hardcoded paths...")

        patterns = [
            r"D:\\Dunna\\Documents\\hw-1",
            r"/home/\w+/",
            r"C:\\Users\\",
        ]

        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for pattern in patterns:
                    if re.search(pattern, content):
                        self.issues["hardcoded_paths"].append(str(py_file))
                        self.stats["hardcoded_paths"] += 1
                        break
            except Exception:
                pass

        print(f"  Found {self.stats['hardcoded_paths']} files with hardcoded paths")

    def check_missing_docstrings(self):
        """检查缺失的 docstring"""
        print("[5/8] Checking missing docstrings...")

        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # 检查函数定义
                func_matches = re.finditer(r"def\s+(\w+)\s*\(", content)
                for match in func_matches:
                    func_name = match.group(1)
                    if func_name.startswith("_"):  # 跳过私有函数
                        continue

                    # 简单检查：函数定义后是否有 """
                    pos = match.end()
                    next_50 = content[pos : pos + 50]
                    if '"""' not in next_50 and "'''" not in next_50:
                        self.stats["missing_docstrings"] += 1

            except Exception:
                pass

        print(
            f"  Found ~{self.stats['missing_docstrings']} functions without docstrings"
        )

    def check_long_functions(self):
        """检查过长的函数"""
        print("[6/8] Checking long functions...")

        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                lines = py_file.read_text(encoding="utf-8", errors="ignore").split("\n")

                current_func = None
                func_start = 0
                indent_level = 0

                for i, line in enumerate(lines):
                    # 检测函数定义
                    match = re.match(r"(\s*)def\s+(\w+)", line)
                    if match:
                        # 保存前一个函数
                        if current_func and (i - func_start) > 100:
                            self.issues["long_functions"].append(
                                {
                                    "file": str(py_file),
                                    "function": current_func,
                                    "lines": i - func_start,
                                }
                            )
                            self.stats["long_functions"] += 1

                        current_func = match.group(2)
                        func_start = i
                        indent_level = len(match.group(1))

            except Exception:
                pass

        print(f"  Found {self.stats['long_functions']} functions >100 lines")

    def check_inconsistent_naming(self):
        """检查命名不一致"""
        print("[7/8] Checking naming conventions...")

        version_dirs = [d for d in self.root_dir.glob("v*") if d.is_dir()]

        # 检查版本目录命名
        for vdir in version_dirs:
            name = vdir.name
            if not re.match(r"v\d+(_[a-z_]+)?$", name):
                self.issues["naming"].append(
                    {
                        "type": "version_dir",
                        "name": name,
                        "expected": "v{number}_{snake_case}",
                    }
                )
                self.stats["naming"] += 1

        print(f"  Found {self.stats['naming']} naming issues")

    def check_unused_imports(self):
        """检查未使用的导入（简化版）"""
        print("[8/8] Checking potentially unused imports...")

        # 这是一个简化检查，只查找明显未使用的情况
        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # 查找 import 语句
                imports = re.findall(r"import\s+(\w+)", content)
                from_imports = re.findall(r"from\s+\S+\s+import\s+(\w+)", content)

                all_imports = set(imports + from_imports)

                # 简单检查：导入的名称在后续代码中是否出现
                for imp in all_imports:
                    if imp == "plt" or imp == "np" or imp == "pd":  # 常见别名
                        continue
                    # 简化：只统计，不详细分析
                    self.stats["total_imports"] += 1

            except Exception:
                pass

        print(
            f"  Scanned {self.stats['total_imports']} imports (detailed analysis needed)"
        )

    def _should_skip(self, path):
        """判断是否跳过该路径"""
        path_str = str(path)
        skip_patterns = [
            ".venv-",
            ".git",
            "__pycache__",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
        ]
        return any(pattern in path_str for pattern in skip_patterns)

    def print_report(self):
        """打印报告"""
        print()
        print("=" * 80)
        print("QUALITY CHECK REPORT")
        print("=" * 80)
        print()

        # 总览
        print("## Summary")
        print()
        total_issues = sum(1 for k, v in self.issues.items() if v and k != "todos")

        print(f"Total issue categories: {total_issues}")
        print()

        # 详细问题
        if self.issues["import_star"]:
            print("## [MEDIUM] Import * Usage")
            print(f"Found in {len(self.issues['import_star'])} files")
            for f in self.issues["import_star"][:5]:
                print(f"  - {f}")
            if len(self.issues["import_star"]) > 5:
                print(f"  ... and {len(self.issues['import_star']) - 5} more")
            print()

        if self.issues["todos"]:
            print("## [LOW] TODO/FIXME Markers")
            print(f"Found {len(self.issues['todos'])} markers")
            for todo in self.issues["todos"][:5]:
                print(f"  - {todo['file']}:{todo['line']}")
                print(f"    {todo['content'][:60]}")
            if len(self.issues["todos"]) > 5:
                print(f"  ... and {len(self.issues['todos']) - 5} more")
            print()

        if self.issues["hardcoded_paths"]:
            print("## [HIGH] Hardcoded Paths")
            print(f"Found in {len(self.issues['hardcoded_paths'])} files")
            for f in self.issues["hardcoded_paths"][:5]:
                print(f"  - {f}")
            if len(self.issues["hardcoded_paths"]) > 5:
                print(f"  ... and {len(self.issues['hardcoded_paths']) - 5} more")
            print()

        if self.issues["duplicate_requirements"]:
            print("## [MEDIUM] Duplicate requirements.txt")
            for dup in self.issues["duplicate_requirements"]:
                print(f"  - {dup['file1']}")
                print(f"    = {dup['file2']}")
            print()

        if self.issues["long_functions"]:
            print("## [MEDIUM] Long Functions (>100 lines)")
            for func in self.issues["long_functions"][:5]:
                print(
                    f"  - {func['function']} in {func['file']} ({func['lines']} lines)"
                )
            if len(self.issues["long_functions"]) > 5:
                print(f"  ... and {len(self.issues['long_functions']) - 5} more")
            print()

        # 统计信息
        print("## Statistics")
        print(f"  - requirements.txt files: {self.stats['requirements']}")
        print(f"  - Functions without docstrings: ~{self.stats['missing_docstrings']}")
        print(f"  - Total imports scanned: {self.stats['total_imports']}")
        print()

        # 建议
        print("## Recommendations")
        print()

        if self.issues["import_star"]:
            print("1. Replace 'import *' with explicit imports")
            print("   - Makes dependencies clear")
            print("   - Avoids namespace pollution")
            print()

        if self.issues["hardcoded_paths"]:
            print("2. Remove hardcoded paths")
            print("   - Use Path(__file__).parent or environment variables")
            print("   - Makes code portable")
            print()

        if self.stats["requirements"] > 10:
            print("3. Consolidate requirements.txt files")
            print("   - Consider a single root requirements.txt")
            print("   - Or use requirements-dev.txt, requirements-prod.txt")
            print()

        if self.issues["long_functions"]:
            print("4. Refactor long functions")
            print("   - Break into smaller, focused functions")
            print("   - Improves readability and testability")
            print()

        print("=" * 80)

    def save_report(self, output_file="code_quality_report.json"):
        """保存报告为JSON"""
        report = {
            "stats": dict(self.stats),
            "issues": {k: v for k, v in self.issues.items() if v},
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to: {output_file}")


def main():
    checker = CodeQualityChecker()
    checker.check_all()
    checker.save_report("code_quality_report.json")


if __name__ == "__main__":
    main()

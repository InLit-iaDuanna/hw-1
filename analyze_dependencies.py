"""
依赖分析脚本 - 收集、分析和优化 hw-1 项目的 Python 依赖
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# 第三方包映射（import名 -> PyPI包名）
PACKAGE_MAPPING = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
}

# 标准库包（Python内置，不需要安装）
STDLIB_PACKAGES = {
    "abc",
    "argparse",
    "ast",
    "collections",
    "csv",
    "dataclasses",
    "datetime",
    "enum",
    "gc",
    "hashlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "pickle",
    "pstats",
    "random",
    "re",
    "shutil",
    "sqlite3",
    "subprocess",
    "sys",
    "tempfile",
    "time",
    "tracemalloc",
    "typing",
    "cProfile",
}

# Abaqus专用包（外部CAE系统，不通过pip安装）
ABAQUS_PACKAGES = {"abaqus", "abaqusConstants", "odbAccess"}


class DependencyAnalyzer:
    """依赖分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.requirements_files: List[Path] = []
        self.all_dependencies: Dict[str, Set[str]] = defaultdict(
            set
        )  # package -> set of versions
        self.imports_found: Set[str] = set()
        self.version_conflicts: List[Tuple[str, List[str]]] = []

    def find_requirements_files(self) -> List[Path]:
        """查找所有 requirements.txt 文件"""
        req_files = list(self.project_root.glob("**/requirements*.txt"))
        # 排除虚拟环境
        req_files = [f for f in req_files if ".venv" not in str(f)]
        self.requirements_files = sorted(req_files)
        return self.requirements_files

    def parse_requirement_line(self, line: str) -> Tuple[str, str] | None:
        """解析 requirements.txt 中的一行

        Returns:
            (package_name, version_spec) or None
        """
        line = line.strip()

        # 跳过注释和空行
        if not line or line.startswith("#"):
            return None

        # 跳过 -r 引用
        if line.startswith("-r "):
            return None

        # 处理 imageio[ffmpeg] 这样的格式
        line = re.sub(r"\[.*?\]", "", line)

        # 匹配包名和版本
        match = re.match(r"^([a-zA-Z0-9_-]+)\s*([><=!~]+.*)?$", line)
        if match:
            package = match.group(1).lower()
            version = match.group(2) or ""
            return (package, version.strip())

        return None

    def collect_dependencies(self):
        """收集所有依赖及其版本"""
        for req_file in self.requirements_files:
            try:
                with open(req_file, encoding="utf-8") as f:
                    for line in f:
                        result = self.parse_requirement_line(line)
                        if result:
                            package, version = result
                            self.all_dependencies[package].add(version)
            except Exception as e:
                print(f"警告: 无法读取 {req_file}: {e}")

    def find_imports_in_code(self) -> Set[str]:
        """扫描代码中的实际导入"""
        py_files = list(self.project_root.glob("**/*.py"))
        # 排除虚拟环境
        py_files = [
            f for f in py_files if ".venv" not in str(f) and "__pycache__" not in str(f)
        ]

        import_pattern = re.compile(r"^\s*(?:from\s+(\w+)|import\s+(\w+))")

        for py_file in py_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    for line in f:
                        match = import_pattern.match(line)
                        if match:
                            package = match.group(1) or match.group(2)
                            if package:
                                self.imports_found.add(package)
            except Exception as e:
                print(f"警告: 无法读取 {py_file}: {e}")

        return self.imports_found

    def detect_version_conflicts(self):
        """检测版本冲突"""
        for package, versions in self.all_dependencies.items():
            # 移除空版本规范
            versions = {v for v in versions if v}

            if len(versions) > 1:
                # 检查是否有完全不兼容的版本（如 ==3.3.7 vs ==2.3.0）
                exact_versions = [v for v in versions if v.startswith("==")]
                if len(exact_versions) > 1 or len(versions) > 1:
                    self.version_conflicts.append((package, sorted(versions)))

    def categorize_imports(self) -> Dict[str, Set[str]]:
        """将导入分类为不同的依赖类型"""
        categories = {
            "core": set(),  # 核心仿真依赖
            "visualization": set(),  # 可视化依赖
            "analysis": set(),  # 数据分析依赖
            "optimization": set(),  # 优化工具依赖
            "dev": set(),  # 开发/测试依赖
            "ui": set(),  # UI工具依赖
            "document": set(),  # 文档生成依赖
            "unused": set(),  # requirements中有但代码未使用
            "external": set(),  # 外部系统（Abaqus等）
        }

        # 核心仿真
        core_packages = {"mujoco", "numpy", "scipy", "imageio", "imageio-ffmpeg"}
        # 可视化
        viz_packages = {"matplotlib", "pillow", "seaborn", "plotly"}
        # 数据分析
        analysis_packages = {"pandas", "pyyaml"}
        # 优化
        opt_packages = {
            "scikit-optimize",
            "deap",
            "cma",
            "scikit-learn",
            "salib",
            "pymoo",
            "joblib",
        }
        # 开发测试
        dev_packages = {"pytest", "pytest-cov", "pytest-xdist", "pytest-timeout"}
        # UI
        ui_packages = {"streamlit"}
        # 文档
        doc_packages = {"python-pptx", "lxml"}

        # 标准化导入名到包名
        imports_normalized = set()
        for imp in self.imports_found:
            if imp in STDLIB_PACKAGES or imp in ABAQUS_PACKAGES:
                continue
            pkg = PACKAGE_MAPPING.get(imp, imp.lower())
            imports_normalized.add(pkg)

        # 分类已声明的依赖
        for package in self.all_dependencies.keys():
            pkg_lower = package.lower()

            if pkg_lower in core_packages:
                categories["core"].add(package)
            elif pkg_lower in viz_packages:
                categories["visualization"].add(package)
            elif pkg_lower in analysis_packages:
                categories["analysis"].add(package)
            elif pkg_lower in opt_packages:
                categories["optimization"].add(package)
            elif pkg_lower in dev_packages:
                categories["dev"].add(package)
            elif pkg_lower in ui_packages:
                categories["ui"].add(package)
            elif pkg_lower in doc_packages:
                categories["document"].add(package)
            else:
                # 默认归为分析类
                categories["analysis"].add(package)

        # 检查未使用的依赖
        for package in self.all_dependencies.keys():
            pkg_lower = package.lower()
            # 映射到导入名
            import_names = [k for k, v in PACKAGE_MAPPING.items() if v == pkg_lower]
            import_names.append(pkg_lower)

            if not any(imp in imports_normalized for imp in import_names):
                # 特殊情况：imageio-ffmpeg 是 imageio 的插件，不直接导入
                if pkg_lower not in ["imageio-ffmpeg"]:
                    categories["unused"].add(package)

        # 标记外部系统
        for imp in self.imports_found:
            if imp in ABAQUS_PACKAGES:
                categories["external"].add(imp)

        return categories

    def get_unified_version(self, package: str) -> str:
        """为包选择统一版本（优先使用最新或最严格的版本）"""
        versions = self.all_dependencies.get(package, set())
        if not versions:
            return ""

        # 移除空版本
        versions = {v for v in versions if v}
        if not versions:
            return ""

        # 优先选择精确版本 ==
        exact_versions = [v for v in versions if v.startswith("==")]
        if exact_versions:
            # 选择最高版本
            return sorted(exact_versions)[-1]

        # 选择最严格的下界 >=
        ge_versions = [v for v in versions if v.startswith(">=")]
        if ge_versions:
            return sorted(ge_versions)[-1]

        # 其他情况返回第一个
        return sorted(versions)[0]

    def generate_report(self) -> str:
        """生成依赖分析报告"""
        report_lines = []

        report_lines.append("# hw-1 项目依赖分析报告")
        report_lines.append("")
        report_lines.append(f"分析日期: {Path(__file__).stat().st_mtime}")
        report_lines.append("")

        # 统计信息
        report_lines.append("## 统计信息")
        report_lines.append("")
        report_lines.append(
            f"- requirements.txt 文件数量: {len(self.requirements_files)}"
        )
        report_lines.append(f"- 唯一依赖包数量: {len(self.all_dependencies)}")
        report_lines.append(f"- 代码中实际导入数量: {len(self.imports_found)}")
        report_lines.append(f"- 检测到的版本冲突: {len(self.version_conflicts)}")
        report_lines.append("")

        # Requirements 文件列表
        report_lines.append("## 发现的 requirements.txt 文件")
        report_lines.append("")
        for req_file in self.requirements_files:
            rel_path = req_file.relative_to(self.project_root)
            report_lines.append(f"- `{rel_path}`")
        report_lines.append("")

        # 所有依赖及版本
        report_lines.append("## 所有依赖及其版本")
        report_lines.append("")
        report_lines.append("| 包名 | 版本规范 | 出现次数 |")
        report_lines.append("|------|----------|----------|")

        for package in sorted(self.all_dependencies.keys()):
            versions = self.all_dependencies[package]
            versions_str = ", ".join(sorted(versions)) if versions else "(无版本)"
            count = len(
                [
                    f
                    for f in self.requirements_files
                    if any(
                        package in line
                        for line in open(f, encoding="utf-8", errors="ignore")
                    )
                ]
            )
            report_lines.append(f"| {package} | {versions_str} | {count} |")

        report_lines.append("")

        # 版本冲突
        if self.version_conflicts:
            report_lines.append("## 版本冲突")
            report_lines.append("")
            report_lines.append("以下包存在多个不同的版本规范:")
            report_lines.append("")

            for package, versions in self.version_conflicts:
                report_lines.append(f"### {package}")
                report_lines.append("")
                for version in versions:
                    report_lines.append(f"- `{version}`")
                report_lines.append("")
                report_lines.append(
                    f"**建议**: 统一使用 `{self.get_unified_version(package)}`"
                )
                report_lines.append("")
        else:
            report_lines.append("## 版本冲突")
            report_lines.append("")
            report_lines.append("未检测到版本冲突。")
            report_lines.append("")

        # 依赖分类
        categories = self.categorize_imports()

        report_lines.append("## 依赖分类")
        report_lines.append("")

        for cat_name, cat_desc in [
            ("core", "核心仿真依赖"),
            ("visualization", "可视化依赖"),
            ("analysis", "数据分析依赖"),
            ("optimization", "优化工具依赖"),
            ("ui", "UI工具依赖"),
            ("document", "文档生成依赖"),
            ("dev", "开发/测试依赖"),
        ]:
            packages = categories[cat_name]
            if packages:
                report_lines.append(f"### {cat_desc}")
                report_lines.append("")
                for package in sorted(packages):
                    version = self.get_unified_version(package)
                    report_lines.append(f"- {package}{version}")
                report_lines.append("")

        # 未使用的依赖
        if categories["unused"]:
            report_lines.append("### 未使用的依赖 (可能可以移除)")
            report_lines.append("")
            report_lines.append(
                "以下包在 requirements.txt 中声明，但在代码中未找到导入:"
            )
            report_lines.append("")
            for package in sorted(categories["unused"]):
                report_lines.append(f"- {package}")
            report_lines.append("")

        # 外部系统依赖
        if categories["external"]:
            report_lines.append("### 外部系统依赖")
            report_lines.append("")
            report_lines.append("以下依赖来自外部系统（不通过 pip 安装）:")
            report_lines.append("")
            for package in sorted(categories["external"]):
                report_lines.append(f"- {package} (Abaqus CAE)")
            report_lines.append("")

        # 优化建议
        report_lines.append("## 优化建议")
        report_lines.append("")
        report_lines.append("### 1. 统一版本管理")
        report_lines.append("")
        report_lines.append("- 在项目根目录维护主 `requirements.txt`")
        report_lines.append("- 子项目使用 `-r ../requirements.txt` 引用")
        report_lines.append("- 仅在子项目有特殊需求时添加额外依赖")
        report_lines.append("")

        report_lines.append("### 2. 分离依赖类型")
        report_lines.append("")
        report_lines.append("- `requirements.txt`: 核心生产依赖")
        report_lines.append("- `requirements-dev.txt`: 开发和测试工具")
        report_lines.append("- `requirements-viz.txt`: 可视化工具（可选）")
        report_lines.append("- `requirements-analysis.txt`: 数据分析工具（可选）")
        report_lines.append("- `requirements-opt.txt`: 参数优化工具（可选）")
        report_lines.append("")

        report_lines.append("### 3. 固定关键版本")
        report_lines.append("")
        report_lines.append("建议为以下关键包固定版本（使用 `==`）:")
        report_lines.append("")
        report_lines.append("- `mujoco`: 仿真引擎核心")
        report_lines.append("- `numpy`: 数值计算基础")
        report_lines.append("- 其他包可使用 `>=` 允许小版本更新")
        report_lines.append("")

        return "\n".join(report_lines)


def main():
    """主函数"""
    project_root = Path(__file__).parent

    print("=" * 60)
    print("hw-1 项目依赖分析工具")
    print("=" * 60)
    print()

    analyzer = DependencyAnalyzer(project_root)

    # 步骤 1: 查找 requirements.txt 文件
    print("步骤 1: 查找 requirements.txt 文件...")
    req_files = analyzer.find_requirements_files()
    print(f"  找到 {len(req_files)} 个文件")

    # 步骤 2: 收集依赖
    print("\n步骤 2: 收集依赖...")
    analyzer.collect_dependencies()
    print(f"  找到 {len(analyzer.all_dependencies)} 个唯一依赖")

    # 步骤 3: 扫描代码导入
    print("\n步骤 3: 扫描代码中的实际导入...")
    analyzer.find_imports_in_code()
    print(f"  找到 {len(analyzer.imports_found)} 个导入")

    # 步骤 4: 检测版本冲突
    print("\n步骤 4: 检测版本冲突...")
    analyzer.detect_version_conflicts()
    print(f"  发现 {len(analyzer.version_conflicts)} 个冲突")

    # 步骤 5: 生成报告
    print("\n步骤 5: 生成报告...")
    report = analyzer.generate_report()

    report_path = project_root / "DEPENDENCY_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  报告已保存到: {report_path}")

    # 步骤 6: 生成优化后的 requirements 文件
    print("\n步骤 6: 生成优化的 requirements 文件...")
    categories = analyzer.categorize_imports()

    # requirements.txt (核心)
    core_req = project_root / "requirements-core.txt"
    with open(core_req, "w", encoding="utf-8") as f:
        f.write("# hw-1 核心依赖 - 仿真运行必需\n")
        f.write("# MuJoCo 仿真引擎和基础数值计算\n\n")
        for package in sorted(categories["core"]):
            version = analyzer.get_unified_version(package)
            f.write(f"{package}{version}\n")
    print(f"  [OK] {core_req}")

    # requirements-viz.txt (可视化)
    viz_req = project_root / "requirements-viz.txt"
    with open(viz_req, "w", encoding="utf-8") as f:
        f.write("# hw-1 可视化依赖\n")
        f.write("# 用于生成图表、动画和可视化结果\n\n")
        f.write("-r requirements-core.txt\n\n")
        for package in sorted(categories["visualization"]):
            version = analyzer.get_unified_version(package)
            f.write(f"{package}{version}\n")
    print(f"  [OK] {viz_req}")

    # requirements-analysis.txt (分析)
    analysis_req = project_root / "requirements-analysis.txt"
    with open(analysis_req, "w", encoding="utf-8") as f:
        f.write("# hw-1 数据分析依赖\n")
        f.write("# 用于数据处理、统计分析和结果导出\n\n")
        f.write("-r requirements-viz.txt\n\n")
        for package in sorted(categories["analysis"]):
            if (
                package not in categories["core"]
                and package not in categories["visualization"]
            ):
                version = analyzer.get_unified_version(package)
                f.write(f"{package}{version}\n")
    print(f"  [OK] {analysis_req}")

    # requirements-opt.txt (优化)
    if categories["optimization"]:
        opt_req = project_root / "requirements-opt.txt"
        with open(opt_req, "w", encoding="utf-8") as f:
            f.write("# hw-1 参数优化依赖\n")
            f.write("# 用于自动参数调优和优化算法\n\n")
            f.write("-r requirements-analysis.txt\n\n")
            for package in sorted(categories["optimization"]):
                version = analyzer.get_unified_version(package)
                f.write(f"{package}{version}\n")
        print(f"  [OK] {opt_req}")

    # requirements-ui.txt (UI)
    if categories["ui"]:
        ui_req = project_root / "requirements-ui.txt"
        with open(ui_req, "w", encoding="utf-8") as f:
            f.write("# hw-1 UI 工具依赖\n")
            f.write("# 用于交互式参数调节界面\n\n")
            f.write("-r requirements-analysis.txt\n\n")
            for package in sorted(categories["ui"]):
                version = analyzer.get_unified_version(package)
                f.write(f"{package}{version}\n")
        print(f"  [OK] {ui_req}")

    # requirements-doc.txt (文档)
    if categories["document"]:
        doc_req = project_root / "requirements-doc.txt"
        with open(doc_req, "w", encoding="utf-8") as f:
            f.write("# hw-1 文档生成依赖\n")
            f.write("# 用于生成 PPT 等文档\n\n")
            for package in sorted(categories["document"]):
                version = analyzer.get_unified_version(package)
                f.write(f"{package}{version}\n")
        print(f"  [OK] {doc_req}")

    # requirements-dev.txt (开发)
    dev_req = project_root / "requirements-dev.txt"
    with open(dev_req, "w", encoding="utf-8") as f:
        f.write("# hw-1 开发依赖\n")
        f.write("# 用于测试、调试和开发工具\n\n")
        f.write("-r requirements-analysis.txt\n\n")
        for package in sorted(categories["dev"]):
            version = analyzer.get_unified_version(package)
            f.write(f"{package}{version}\n")
    print(f"  [OK] {dev_req}")

    print("\n" + "=" * 60)
    print("分析完成!")
    print(f"查看详细报告: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

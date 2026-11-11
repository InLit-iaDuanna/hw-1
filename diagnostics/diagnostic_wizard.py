"""交互式诊断向导。

引导用户一步步诊断问题，并提供个性化的解决方案。
"""

import sys
from pathlib import Path
from typing import Any

from .error_detector import ErrorDetector
from .solution_database import SolutionDatabase


class DiagnosticWizard:
    """交互式诊断向导。"""

    def __init__(self, db: SolutionDatabase | None = None):
        self.db = db or SolutionDatabase()
        self.detector = ErrorDetector()
        self.context: dict[str, Any] = {}

    def run(self) -> None:
        """运行交互式诊断向导。"""
        print("=" * 70)
        print("hw-1 智能错误诊断向导")
        print("=" * 70)
        print()

        # 选择诊断模式
        mode = self._select_mode()

        if mode == "auto":
            self._auto_diagnose()
        elif mode == "interactive":
            self._interactive_diagnose()
        elif mode == "search":
            self._search_knowledge()
        elif mode == "file":
            self._diagnose_from_file()

        print("\n诊断完成。")

    def _select_mode(self) -> str:
        """选择诊断模式。"""
        print("请选择诊断模式:")
        print("  1. 自动诊断 (从文件/数据自动检测)")
        print("  2. 交互式诊断 (回答问题逐步定位)")
        print("  3. 搜索知识库")
        print("  4. 分析特定文件")
        print()

        while True:
            choice = input("请输入选项 [1-4] (或 q 退出): ").strip()

            if choice == "q":
                sys.exit(0)
            elif choice == "1":
                return "auto"
            elif choice == "2":
                return "interactive"
            elif choice == "3":
                return "search"
            elif choice == "4":
                return "file"
            else:
                print("无效选项，请重新输入。")

    def _auto_diagnose(self) -> None:
        """自动诊断模式。"""
        print("\n--- 自动诊断模式 ---")
        print("请提供仿真结果文件路径 (JSON 格式)")
        print("示例: D:\\Dunna\\Documents\\hw-1\\v10\\out\\v10_result.json")
        print()

        file_path = input("文件路径 (或回车跳过): ").strip()

        if not file_path:
            print("未提供文件，返回主菜单。")
            return

        path = Path(file_path)
        if not path.exists():
            print(f"错误: 文件不存在: {path}")
            return

        print(f"\n正在分析文件: {path.name}")

        # 检测错误
        errors = self.detector.detect_from_json(path)

        if not errors:
            print("✓ 未检测到已知错误。")
            return

        print(f"\n检测到 {len(errors)} 个错误:")
        for i, (error_type, severity) in enumerate(errors, 1):
            print(f"  {i}. {error_type} (严重性: {severity})")

        # 显示解决方案
        print("\n" + "=" * 70)
        print("推荐解决方案:")
        print("=" * 70)

        for error_type, severity in errors:
            entry = self.db.get(error_type)
            if entry:
                print(f"\n[{error_type}]")
                solutions = entry.solutions[:3]  # 前 3 个方案
                for i, sol in enumerate(solutions, 1):
                    print(f"\n  方案 {i}: {sol.action}")
                    print(f"  详情: {sol.details}")
                    if sol.code:
                        print("  代码:")
                        for line in sol.code.split("\n"):
                            print(f"    {line}")
            else:
                print(f"\n[{error_type}]")
                print("  未找到解决方案。请查阅项目文档或联系开发者。")

    def _interactive_diagnose(self) -> None:
        """交互式诊断模式。"""
        print("\n--- 交互式诊断模式 ---")
        print("请回答以下问题以定位问题。\n")

        # 问题 1: 仿真是否启动
        if not self._ask_yes_no("仿真能够启动吗？"):
            self._diagnose_startup_failure()
            return

        # 问题 2: 是否出现错误
        if not self._ask_yes_no("仿真运行过程中是否报错？"):
            self._diagnose_performance_issue()
            return

        # 问题 3: 错误类型
        print("\n仿真失败的表现:")
        print("  1. NaN / 数值错误")
        print("  2. 机器人摔倒 (fall_down)")
        print("  3. 机器人飞走 / 爆炸 (fly_away)")
        print("  4. 穿透地面 (penetration)")
        print("  5. 无法交替步态 (stuck)")
        print("  6. 其他")

        choice = input("\n请选择 [1-6]: ").strip()

        error_map = {
            "1": "simulation_nan",
            "2": "fall_down",
            "3": "fly_away",
            "4": "penetration",
            "5": "no_alternation",
        }

        error_type = error_map.get(choice)
        if error_type:
            self._show_solutions(error_type)
        else:
            print("\n未知错误类型。建议:")
            print("  1. 检查日志文件")
            print("  2. 使用自动诊断模式分析输出文件")
            print("  3. 查阅项目文档或版本 README")

    def _diagnose_startup_failure(self) -> None:
        """诊断启动失败。"""
        print("\n仿真无法启动，可能原因:")

        if self._ask_yes_no("是否提示 'ModuleNotFoundError'？"):
            if "mujoco" in input("缺少的模块名称: ").lower():
                self._show_solutions("mujoco_not_found")
            elif "common" in input("缺少的模块名称: ").lower():
                self._show_solutions("common_import_error")
        elif self._ask_yes_no("是否提示 'FileNotFoundError'？"):
            self._show_solutions("model_file_not_found")
        else:
            print("\n建议:")
            print("  1. 检查错误消息")
            print("  2. 确认 Python 版本 (推荐 3.10+)")
            print("  3. 确认虚拟环境已激活 (.venv-mujoco)")

    def _diagnose_performance_issue(self) -> None:
        """诊断性能问题。"""
        print("\n仿真运行但有性能问题:")

        if self._ask_yes_no("仿真速度是否很慢 (低于实时)?"):
            self._show_solutions("simulation_too_slow")
        else:
            print("\n如果步态效果不佳，可能需要:")
            print("  1. 调整控制参数 (参考 V13 参数敏感性分析)")
            print("  2. 检查电机摩擦是否在失败带 (V16)")
            print("  3. 检查摆臂质量是否过重 (V14c)")

    def _search_knowledge(self) -> None:
        """搜索知识库。"""
        print("\n--- 搜索知识库 ---")

        keyword = input("请输入搜索关键词 (如 'nan', 'fall', 'motor'): ").strip()

        if not keyword:
            print("未输入关键词。")
            return

        results = self.db.search(keyword)

        if not results:
            print(f"\n未找到包含 '{keyword}' 的错误条目。")
            return

        print(f"\n找到 {len(results)} 个相关错误:")
        for i, entry in enumerate(results, 1):
            print(f"  {i}. {entry.error_type} (严重性: {entry.severity})")

        # 选择查看详情
        choice = input(f"\n输入编号查看详情 [1-{len(results)}] (或回车返回): ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                print("\n" + "=" * 70)
                print(results[idx].format())
                print("=" * 70)

    def _diagnose_from_file(self) -> None:
        """从文件诊断。"""
        print("\n--- 分析文件 ---")
        print("支持的文件类型: .json, .log")
        print()

        file_path = input("文件路径: ").strip()

        if not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            print(f"错误: 文件不存在: {path}")
            return

        print(f"\n正在分析: {path.name}")

        if path.suffix == ".json":
            errors = self.detector.detect_from_json(path)
        elif path.suffix == ".log":
            errors = self.detector.detect_from_log(path)
        else:
            print(f"不支持的文件类型: {path.suffix}")
            return

        if not errors:
            print("✓ 未检测到已知错误。")
            return

        print(f"\n检测到 {len(errors)} 个错误:")
        for error_type, severity in errors:
            print(f"  - {error_type} (严重性: {severity})")
            self._show_solutions(error_type, indent=4)

    def _show_solutions(self, error_type: str, indent: int = 0) -> None:
        """显示错误的解决方案。"""
        entry = self.db.get(error_type)
        prefix = " " * indent

        if not entry:
            print(f"{prefix}未找到 '{error_type}' 的解决方案。")
            return

        print(f"{prefix}\n错误类型: {error_type}")
        print(f"{prefix}严重性: {entry.severity}")

        if entry.causes:
            print(f"{prefix}\n可能原因:")
            for cause in entry.causes:
                print(f"{prefix}  - {cause}")

        if entry.solutions:
            print(f"{prefix}\n推荐解决方案:")
            for i, sol in enumerate(entry.solutions[:3], 1):
                print(f"{prefix}\n  方案 {i}: {sol.action}")
                print(f"{prefix}  详情: {sol.details}")
                if sol.code:
                    print(f"{prefix}  代码示例:")
                    for line in sol.code.split("\n"):
                        print(f"{prefix}    {line}")

        if entry.references:
            print(f"{prefix}\n参考资料:")
            for ref in entry.references:
                print(f"{prefix}  - {ref}")

    def _ask_yes_no(self, question: str) -> bool:
        """询问是/否问题。"""
        while True:
            answer = input(f"{question} [y/n]: ").strip().lower()
            if answer in ["y", "yes", "是", "是的"]:
                return True
            elif answer in ["n", "no", "否", "不是"]:
                return False
            else:
                print("请输入 y 或 n")


def main() -> None:
    """命令行入口。"""
    wizard = DiagnosticWizard()
    wizard.run()


if __name__ == "__main__":
    main()

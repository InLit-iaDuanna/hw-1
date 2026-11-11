#!/usr/bin/env python
"""V18 快速渲染脚本 - 预设常用任务。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = Path("D:/Dunna/Documents/hw-1/.venv-mujoco/Scripts/python.exe")
RENDER_SCRIPT = ROOT / "render_v18.py"


def run_task(task_name: str):
    """运行预设渲染任务。"""

    tasks = {
        "1": {
            "name": "失败案例 (roll_k=100)",
            "args": [
                "--mode",
                "single",
                "--roll-stiffness",
                "100",
                "--duration",
                "6.0",
            ],
        },
        "2": {
            "name": "稳定案例 (roll_k=500)",
            "args": [
                "--mode",
                "single",
                "--roll-stiffness",
                "500",
                "--duration",
                "6.0",
            ],
        },
        "3": {
            "name": "对比动画 (100 vs 500)",
            "args": ["--mode", "comparison", "--duration", "6.0"],
        },
        "4": {
            "name": "失败案例双视角",
            "args": ["--mode", "dual", "--roll-stiffness", "100", "--duration", "6.0"],
        },
        "5": {
            "name": "参数扫描 (roll_k=50,150,300)",
            "args": None,  # 特殊处理
        },
    }

    if task_name not in tasks:
        print(f"错误: 未知任务 '{task_name}'")
        return

    task = tasks[task_name]
    print(f"\n{'='*60}")
    print(f"任务: {task['name']}")
    print(f"{'='*60}\n")

    if task_name == "5":
        # 参数扫描
        for k in [50, 150, 300]:
            print(f"\n>>> 渲染 roll_k={k}")
            subprocess.run(
                [
                    str(PYTHON),
                    str(RENDER_SCRIPT),
                    "--mode",
                    "single",
                    "--roll-stiffness",
                    str(k),
                    "--duration",
                    "5.0",
                ]
            )
    else:
        subprocess.run([str(PYTHON), str(RENDER_SCRIPT)] + task["args"])

    print(f"\n{'='*60}")
    print("任务完成！")
    print(f"{'='*60}\n")


def main():
    print("\n" + "=" * 60)
    print("V18 侧向稳定性渲染 - 快速任务")
    print("=" * 60)
    print("\n可用任务:")
    print("  1. 失败案例 (roll_k=100) - 侧视+前视")
    print("  2. 稳定案例 (roll_k=500) - 侧视+前视")
    print("  3. 对比动画 (100 vs 500) - 并排对比")
    print("  4. 失败案例双视角 - 侧视+前视拼接")
    print("  5. 参数扫描 (roll_k=50,150,300) - 批量生成")
    print("\n使用方法:")
    print(f"  python {Path(__file__).name} <任务编号>")
    print("\n示例:")
    print(f"  python {Path(__file__).name} 3")
    print("=" * 60 + "\n")

    if len(sys.argv) < 2:
        print("请指定任务编号 (1-5)")
        sys.exit(1)

    task_num = sys.argv[1]
    run_task(task_num)


if __name__ == "__main__":
    main()

"""V12 三视图并排可视化：用 subprocess 同时启动 V09 / V10 / V11 三个 MuJoCo viewer 窗口。

每个窗口是一个独立 Python 进程（避免 OpenGL 上下文冲突）。
三个窗口由用户手动拖拽并排即可。

不重跑任何仿真，只读已有 out/*_data.csv 回放。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv-mujoco" / "Scripts" / "python.exe"


JOBS = [
    {
        "label": "V09 仿生稳定",
        "cwd": ROOT / "v09_stable_biomimetic_gait",
        "script": "view_stable_gait_v9.py",
        "args": [],
    },
    {
        "label": "V10 滚动足",
        "cwd": ROOT / "v10_rolling_foot_biomimetic_gait",
        "script": "view_rolling_foot_gait_v10.py",
        "args": [],
    },
    {
        "label": "V11 平地基线",
        "cwd": ROOT,
        "script": "v11_rugged_terrain_robustness/view_rugged_gait_v11.py",
        "args": ["--prefix", "v11_sanity_flat"],
    },
]


def main() -> None:
    if not PYTHON.exists():
        print(f"[error] 找不到 Python 解释器：{PYTHON}")
        sys.exit(1)

    print("=" * 60)
    print("V12 三视图并排可视化")
    print("=" * 60)
    print("将依次启动 3 个 MuJoCo 窗口（每个窗口一个独立进程）")
    print("启动后请手动把 3 个窗口并排拖到屏幕上")
    print("关闭任何一个窗口即结束该版本回放，本启动器不会自动退出")
    print("如需全部停止，关闭所有 MuJoCo 窗口或在本终端按 Ctrl+C")
    print("=" * 60)

    procs: list[tuple[str, subprocess.Popen]] = []
    for job in JOBS:
        cmd = [str(PYTHON), job["script"], *job["args"]]
        print(f"[启动] {job['label']}  (cwd={job['cwd'].name})")
        p = subprocess.Popen(cmd, cwd=str(job["cwd"]))
        procs.append((job["label"], p))
        time.sleep(0.8)

    print("\n[ok] 3 个窗口已启动。请把它们拖到屏幕上并排观察。")
    print("    左：V09 (步周期 0.45s, CoT=0.083)")
    print("    中：V10 (步周期 0.80s, CoT=0.072, 滚动足)")
    print("    右：V11 (V10 + 平地复现)")
    print("\n[等待] 按 Ctrl+C 关闭所有窗口...")

    try:
        for label, p in procs:
            p.wait()
            print(f"[结束] {label} 窗口已关闭")
    except KeyboardInterrupt:
        print("\n[中断] 正在关闭所有窗口...")
        for label, p in procs:
            if p.poll() is None:
                p.terminate()
        for label, p in procs:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[完成] 已退出")


if __name__ == "__main__":
    main()

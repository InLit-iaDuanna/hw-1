r"""
hw-1 批量高清渲染脚本
功能：将优先级 A/B 动画重新渲染为 1920×1080 高清版本

使用方法：
    cd D:\Dunna\Documents\hw-1
    .\.venv-mujoco\Scripts\Activate.ps1
    python batch_render_hd.py --priority A
    python batch_render_hd.py --priority B
    python batch_render_hd.py --all

作者：段泽琪
日期：2026/06/05
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent


@dataclass
class RenderTask:
    """渲染任务定义"""

    version: str  # 版本号（如 v10）
    script_path: Path  # 渲染脚本绝对路径
    tag: str  # 输出文件tag（传给 --tag 参数）
    priority: str  # 优先级 A/B/C
    description: str  # 任务描述
    requires_tag: bool = True  # 脚本是否支持 --tag 参数


# 定义渲染任务清单
RENDER_TASKS = [
    # ========== 优先级 A：核心展示动画 ==========
    RenderTask(
        version="V10",
        script_path=HW1_ROOT
        / "v10_rolling_foot_biomimetic_gait"
        / "render_rolling_foot_gait_v10.py",
        tag="v10_rolling_foot_walk_HD",
        priority="A",
        description="足踝滚动仿生步态 - 最推荐展示",
        requires_tag=False,  # 该脚本不支持 --tag，需要修改
    ),
    RenderTask(
        version="V13.7",
        script_path=HW1_ROOT / "v13_7_friction_compensation" / "render_v13_7.py",
        tag="v13_7_smoke_compensated_mx64ar_HD",
        priority="A",
        description="摩擦补偿 ON - MX64AR电机",
    ),
    RenderTask(
        version="V13.7",
        script_path=HW1_ROOT / "v13_7_friction_compensation" / "render_v13_7.py",
        tag="v13_7_smoke_compensated_ec_i40_HD",
        priority="A",
        description="摩擦补偿 ON - EC-i40电机",
    ),
    RenderTask(
        version="V17",
        script_path=HW1_ROOT / "v17_state_estimation" / "render_v17.py",
        tag="v17_mx64ar_noise1_HD",
        priority="A",
        description="状态估计 + 传感器噪声 - 硬件落地关键",
    ),
    # ========== 优先级 B：推荐升级 ==========
    RenderTask(
        version="V13.6",
        script_path=HW1_ROOT / "v13_6_event_driven_fsm" / "render_v13_6.py",
        tag="v13_6_baseline_walk_HD",
        priority="B",
        description="事件驱动有限状态机",
    ),
    RenderTask(
        version="V14",
        script_path=HW1_ROOT / "v14_passive_arms" / "render_passive_arms_v14.py",
        tag="v14_baseline_HD",
        priority="B",
        description="被动摆臂版",
        requires_tag=False,  # 该脚本不支持 --tag
    ),
    RenderTask(
        version="V16",
        script_path=HW1_ROOT / "v16_motor_dynamics" / "render_v16.py",
        tag="v16_smoke_ideal_HD",
        priority="B",
        description="电机动力学 - 理想情况",
    ),
    RenderTask(
        version="V09",
        script_path=HW1_ROOT
        / "v09_stable_biomimetic_gait"
        / "render_stable_gait_v9.py",
        tag="v9_stable_walk_HD",
        priority="B",
        description="准被动稳定步态",
        requires_tag=False,
    ),
]


def check_environment():
    """检查渲染环境依赖"""
    print("=" * 60)
    print("检查渲染环境...")
    print("=" * 60)

    # 检查 Python 环境
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"Python 路径: {sys.executable}")

    # 检查必要的库
    required_packages = ["mujoco", "imageio", "numpy", "PIL"]
    missing_packages = []

    for pkg in required_packages:
        try:
            if pkg == "PIL":
                __import__("PIL")
            else:
                __import__(pkg)
            print(f"✓ {pkg} 已安装")
        except ImportError:
            print(f"✗ {pkg} 未安装")
            missing_packages.append(pkg)

    # 检查字体文件
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        print(f"✓ 字体文件存在: {font_path}")
    else:
        print(f"✗ 字体文件缺失: {font_path}")

    # 检查 imageio-ffmpeg
    try:
        import imageio_ffmpeg

        print(f"✓ imageio-ffmpeg 已安装: {imageio_ffmpeg.get_ffmpeg_version()}")
    except ImportError:
        print("⚠ imageio-ffmpeg 未安装，建议安装以获得更好的视频编码")
        print("  安装命令: pip install imageio-ffmpeg")

    if missing_packages:
        print("\n" + "=" * 60)
        print("错误：缺少必要的依赖包，请先安装：")
        print(f"  pip install {' '.join(missing_packages)}")
        print("=" * 60)
        return False

    print("\n环境检查通过！\n")
    return True


def run_render_task(task: RenderTask, dry_run: bool = False) -> bool:
    """执行单个渲染任务"""
    print("=" * 60)
    print(f"[{task.priority}] {task.version}: {task.description}")
    print("=" * 60)
    print(f"脚本路径: {task.script_path}")
    print(f"输出标签: {task.tag}")

    if not task.script_path.exists():
        print(f"✗ 错误：脚本不存在 - {task.script_path}")
        return False

    if dry_run:
        print("⚠ [DRY RUN] 跳过实际执行")
        return True

    # 构建命令
    cmd = [sys.executable, str(task.script_path)]
    if task.requires_tag:
        cmd.extend(["--tag", task.tag])

    print(f"执行命令: {' '.join(cmd)}")
    print("-" * 60)

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=task.script_path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(result.stdout)
            print(f"✓ 渲染成功！耗时: {elapsed:.1f} 秒")
            return True
        else:
            print("✗ 渲染失败！")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except Exception as e:
        print(f"✗ 执行异常: {e}")
        return False


def archive_720p_videos():
    """归档720p原版视频到 archive_720p 目录"""
    print("\n" + "=" * 60)
    print("归档 720p 原版视频...")
    print("=" * 60)

    archive_dir = HW1_ROOT / "archive_720p"
    archive_dir.mkdir(exist_ok=True)

    archived_count = 0
    for task in RENDER_TASKS:
        version_dir = task.script_path.parent
        out_dir = version_dir / "out"

        if not out_dir.exists():
            continue

        # 查找对应的原始视频（去掉 _HD 后缀）
        original_tag = task.tag.replace("_HD", "")
        original_video = out_dir / f"{original_tag}.mp4"

        if original_video.exists():
            archive_path = archive_dir / f"{original_tag}_720p.mp4"
            if not archive_path.exists():
                print(f"归档: {original_video.name} → {archive_path.name}")
                import shutil

                shutil.copy2(original_video, archive_path)
                archived_count += 1

    print(f"✓ 归档完成，共 {archived_count} 个文件")
    print(f"归档目录: {archive_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="hw-1 批量高清渲染脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python batch_render_hd.py --priority A          # 仅渲染优先级A
  python batch_render_hd.py --priority B          # 仅渲染优先级B
  python batch_render_hd.py --all                 # 渲染所有任务
  python batch_render_hd.py --all --dry-run       # 预览所有任务（不执行）
  python batch_render_hd.py --list                # 列出所有任务
  python batch_render_hd.py --archive             # 归档720p原版
        """,
    )

    parser.add_argument(
        "--priority",
        choices=["A", "B", "C"],
        help="指定优先级（A=核心展示, B=推荐升级, C=保持现状）",
    )
    parser.add_argument("--all", action="store_true", help="渲染所有任务（A+B）")
    parser.add_argument("--list", action="store_true", help="列出所有任务清单")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")
    parser.add_argument("--skip-check", action="store_true", help="跳过环境检查")
    parser.add_argument("--archive", action="store_true", help="归档720p原版视频")

    args = parser.parse_args()

    # 列出任务清单
    if args.list:
        print("\n" + "=" * 60)
        print("hw-1 高清渲染任务清单")
        print("=" * 60)
        for priority in ["A", "B"]:
            tasks = [t for t in RENDER_TASKS if t.priority == priority]
            print(f"\n优先级 {priority}: {len(tasks)} 个任务")
            print("-" * 60)
            for i, task in enumerate(tasks, 1):
                print(f"{i}. [{task.version}] {task.description}")
                print(f"   脚本: {task.script_path.name}")
                print(f"   标签: {task.tag}")
        print("\n" + "=" * 60)
        return

    # 归档模式
    if args.archive:
        archive_720p_videos()
        return

    # 环境检查
    if not args.skip_check:
        if not check_environment():
            sys.exit(1)

    # 筛选任务
    if args.all:
        selected_tasks = [t for t in RENDER_TASKS if t.priority in ["A", "B"]]
    elif args.priority:
        selected_tasks = [t for t in RENDER_TASKS if t.priority == args.priority]
    else:
        parser.print_help()
        return

    if not selected_tasks:
        print("没有选择任何任务")
        return

    print("\n" + "=" * 60)
    print(f"准备渲染 {len(selected_tasks)} 个任务")
    if args.dry_run:
        print("⚠ DRY RUN 模式：不会实际执行渲染")
    print("=" * 60)

    # 执行任务
    success_count = 0
    failed_tasks = []

    for i, task in enumerate(selected_tasks, 1):
        print(f"\n进度: [{i}/{len(selected_tasks)}]")
        if run_render_task(task, dry_run=args.dry_run):
            success_count += 1
        else:
            failed_tasks.append(task)
        print()

    # 总结
    print("\n" + "=" * 60)
    print("渲染任务完成")
    print("=" * 60)
    print(f"成功: {success_count}/{len(selected_tasks)}")
    if failed_tasks:
        print(f"失败: {len(failed_tasks)}")
        print("失败任务：")
        for task in failed_tasks:
            print(f"  - [{task.version}] {task.description}")
    print("=" * 60)

    if not args.dry_run and success_count > 0:
        print("\n建议后续操作：")
        print("1. 验证生成的 HD 视频分辨率和质量")
        print("2. 运行 python batch_render_hd.py --archive 归档720p原版")
        print("3. 更新项目文档（README/CLAUDE.md）")


if __name__ == "__main__":
    main()

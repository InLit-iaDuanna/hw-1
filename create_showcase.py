#!/usr/bin/env python3
"""
hw-1 精选合集生成器

功能：
- 生成答辩/论文用的精选动画合集
- 自动剪辑关键片段
- 添加标题卡和转场
- 生成学术展示用的10分钟版本

用法：
    python create_showcase.py --output showcase_defense.mp4      # 答辩版
    python create_showcase.py --type paper --output paper.mp4     # 论文补充材料版
    python create_showcase.py --custom v05 v10 v13_6 v18          # 自定义版本
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

ROOT = Path(__file__).parent.resolve()

# 精选版本定义
SHOWCASE_DEFINITIONS = {
    "defense": {
        "name": "博士答辩精选版",
        "duration_target": 600,  # 10分钟
        "clips": [
            {
                "version": "v05_hybrid_compass_proof",
                "video": "out/hybrid_compass_mujoco.mp4",
                "title": "V05 - 被动极限环理论证明",
                "duration": 90,
                "start": 0,
                "description": "混合动力学系统 Poincaré 收敛与 Floquet 稳定性",
            },
            {
                "version": "v10_rolling_foot_biomimetic_gait",
                "video": "out/v10_rolling_foot_walk.mp4",
                "title": "V10 - 仿生足踝滚动步态",
                "duration": 120,
                "start": 0,
                "description": "脚跟-足底-脚趾三段式接触，准被动控制",
            },
            {
                "version": "v13_6_event_driven_fsm",
                "video": "out/v13_6_baseline_walk.mp4",
                "title": "V13.6 - 四相位FSM控制律",
                "duration": 90,
                "start": 0,
                "description": "事件驱动状态机，显式相位切换",
            },
            {
                "version": "v18_3d_lateral_stability",
                "video": "out/v18_baseline.mp4",
                "title": "V18 - 3D侧向稳定探索",
                "duration": 60,
                "start": 0,
                "description": "被动侧向稳定不可能性证明",
            },
        ],
    },
    "paper": {
        "name": "论文补充材料版",
        "duration_target": 900,  # 15分钟
        "clips": [
            {
                "version": "v01_mujoco_compass_gait",
                "video": "out/passive_compass_gait.mp4",
                "title": "V01 - 首次被动尝试",
                "duration": 45,
                "start": 0,
                "description": "MuJoCo软接触真实动力学",
            },
            {
                "version": "v05_hybrid_compass_proof",
                "video": "out/hybrid_compass_mujoco.mp4",
                "title": "V05 - 极限环证明",
                "duration": 90,
                "start": 0,
                "description": "Poincaré截面与Floquet分析",
            },
            {
                "version": "v09_stable_biomimetic_gait",
                "video": "out/v9_stable_walk.mp4",
                "title": "V09 - 稳定准被动步态",
                "duration": 60,
                "start": 0,
                "description": "髋膝PD + 踝被动基准",
            },
            {
                "version": "v10_rolling_foot_biomimetic_gait",
                "video": "out/v10_rolling_foot_walk.mp4",
                "title": "V10 - 足踝滚动仿生",
                "duration": 120,
                "start": 0,
                "description": "三段式滚动接触机制",
            },
            {
                "version": "v13_6_event_driven_fsm",
                "video": "out/v13_6_baseline_walk.mp4",
                "title": "V13.6 - FSM相位控制",
                "duration": 90,
                "start": 0,
                "description": "四相位显式时序锁定",
            },
            {
                "version": "v14_passive_arms",
                "video": "out/v14_baseline.mp4",
                "title": "V14 - 被动摆臂",
                "duration": 60,
                "start": 0,
                "description": "上肢摆动耦合步态",
            },
            {
                "version": "v16_motor_dynamics",
                "video": "out/v16_smoke_mx64ar_full.mp4",
                "title": "V16 - 电机动力学",
                "duration": 60,
                "start": 0,
                "description": "MX-64AR带宽与延迟",
            },
            {
                "version": "v17_state_estimation",
                "video": "out/v17_mx64ar_noise1.mp4",
                "title": "V17 - 传感器噪声",
                "duration": 60,
                "start": 0,
                "description": "编码器噪声与滤波",
            },
            {
                "version": "v18_3d_lateral_stability",
                "video": "out/v18_baseline.mp4",
                "title": "V18 - 3D侧向探索",
                "duration": 90,
                "start": 0,
                "description": "被动侧向稳定否定结果",
            },
        ],
    },
    "milestone": {
        "name": "关键里程碑版",
        "duration_target": 300,  # 5分钟
        "clips": [
            {
                "version": "v05_hybrid_compass_proof",
                "video": "out/hybrid_compass_mujoco.mp4",
                "title": "V05 - 极限环证明",
                "duration": 75,
                "start": 0,
                "description": "理论基础",
            },
            {
                "version": "v10_rolling_foot_biomimetic_gait",
                "video": "out/v10_rolling_foot_walk.mp4",
                "title": "V10 - 仿生步态",
                "duration": 90,
                "start": 0,
                "description": "机械转译",
            },
            {
                "version": "v13_6_event_driven_fsm",
                "video": "out/v13_6_baseline_walk.mp4",
                "title": "V13.6 - FSM控制",
                "duration": 75,
                "start": 0,
                "description": "控制策略",
            },
            {
                "version": "v18_3d_lateral_stability",
                "video": "out/v18_baseline.mp4",
                "title": "V18 - 3D化边界",
                "duration": 60,
                "start": 0,
                "description": "理论边界",
            },
        ],
    },
}


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_title_card(text: str, description: str, output: Path, duration: float = 3.0):
    """使用ffmpeg创建标题卡"""
    # 深蓝灰背景 #0F172A
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0F172A:s=1920x1080:d={duration}",
        "-vf",
        f"drawtext=fontfile=Arial.ttf:text='{text}':fontcolor=white:fontsize=56:x=(w-text_w)/2:y=(h-text_h)/2-50:box=0,"
        f"drawtext=fontfile=Arial.ttf:text='{description}':fontcolor=0x94A3B8:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+50:box=0",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]

    subprocess.run(cmd, capture_output=True, check=True)


def trim_video(input_path: Path, output: Path, start: float, duration: float):
    """剪切视频片段"""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]

    subprocess.run(cmd, capture_output=True, check=True)


def concatenate_videos(video_list: List[Path], output: Path):
    """连接多个视频"""
    # 创建concat文件列表
    concat_file = output.parent / "concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for video in video_list:
            f.write(f"file '{video.resolve()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    concat_file.unlink()  # 清理临时文件


def create_showcase(
    showcase_type: str, output: Path, custom_clips: Optional[List[str]] = None
):
    """创建精选合集"""

    if not check_ffmpeg():
        print("错误: 未找到 ffmpeg，请先安装 ffmpeg", file=sys.stderr)
        print("下载: https://ffmpeg.org/download.html", file=sys.stderr)
        sys.exit(1)

    # 获取合集定义
    if custom_clips:
        print(f"使用自定义版本: {', '.join(custom_clips)}")
        clips = []
        for version_short in custom_clips:
            # 查找匹配的版本
            matched = list(ROOT.glob(f"{version_short}*"))
            if not matched:
                print(f"警告: 未找到版本 {version_short}", file=sys.stderr)
                continue

            version_dir = matched[0]
            out_dir = version_dir / "out"
            if not out_dir.exists():
                print(f"警告: {version_dir.name} 无输出目录", file=sys.stderr)
                continue

            # 查找mp4文件
            mp4_files = list(out_dir.glob("*.mp4"))
            if not mp4_files:
                print(f"警告: {version_dir.name} 无视频文件", file=sys.stderr)
                continue

            # 使用第一个找到的视频
            clips.append(
                {
                    "version": version_dir.name,
                    "video": f"out/{mp4_files[0].name}",
                    "title": version_dir.name,
                    "duration": 60,
                    "start": 0,
                    "description": "",
                }
            )

        showcase_def = {"name": "自定义合集", "clips": clips}
    else:
        if showcase_type not in SHOWCASE_DEFINITIONS:
            print(f"错误: 未知的合集类型 '{showcase_type}'", file=sys.stderr)
            print(
                f"可用类型: {', '.join(SHOWCASE_DEFINITIONS.keys())}", file=sys.stderr
            )
            sys.exit(1)

        showcase_def = SHOWCASE_DEFINITIONS[showcase_type]

    print(f"\n正在创建: {showcase_def['name']}")
    print("=" * 80)

    # 临时文件目录
    temp_dir = ROOT / "showcase_temp"
    temp_dir.mkdir(exist_ok=True)

    all_clips = []
    total_duration = 0

    try:
        for i, clip in enumerate(showcase_def["clips"]):
            version_dir = ROOT / clip["version"]
            video_path = version_dir / clip["video"]

            # 检查视频是否存在
            if not video_path.exists():
                if clip.get("optional", False):
                    print(f"  跳过（可选）: {clip['title']}")
                    continue
                else:
                    print(f"  警告: 未找到视频 {video_path}", file=sys.stderr)
                    continue

            print(f"\n[{i+1}/{len(showcase_def['clips'])}] 处理: {clip['title']}")

            # 创建标题卡
            title_card = temp_dir / f"title_{i:02d}.mp4"
            print(f"  生成标题卡...")
            create_title_card(
                clip["title"], clip["description"], title_card, duration=3.0
            )
            all_clips.append(title_card)

            # 剪切视频片段
            trimmed = temp_dir / f"clip_{i:02d}.mp4"
            print(f"  剪切片段 (起始: {clip['start']}s, 时长: {clip['duration']}s)...")
            trim_video(video_path, trimmed, clip["start"], clip["duration"])
            all_clips.append(trimmed)

            total_duration += 3.0 + clip["duration"]
            print(f"  ✓ 完成")

        if not all_clips:
            print("\n错误: 没有可用的视频片段", file=sys.stderr)
            sys.exit(1)

        # 连接所有片段
        print(f"\n连接 {len(all_clips)} 个片段...")
        concatenate_videos(all_clips, output)

        print("\n" + "=" * 80)
        print(f"✓ 合集创建成功!")
        print(f"  输出文件: {output}")
        print(f"  总时长: {total_duration:.1f}秒 ({total_duration/60:.1f}分钟)")
        print(f"  片段数: {len(all_clips)//2}")

    finally:
        # 清理临时文件
        print("\n清理临时文件...")
        for temp_file in temp_dir.glob("*"):
            temp_file.unlink()
        temp_dir.rmdir()


def main():
    parser = argparse.ArgumentParser(description="hw-1 精选合集生成器")
    parser.add_argument(
        "--type",
        choices=["defense", "paper", "milestone"],
        default="defense",
        help="合集类型（默认: defense）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "showcase_defense.mp4",
        help="输出文件路径",
    )
    parser.add_argument(
        "--custom", nargs="+", metavar="VERSION", help="自定义版本列表（忽略--type）"
    )

    args = parser.parse_args()

    # 确保输出目录存在
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # 创建合集
    create_showcase(args.type, args.output, args.custom)


if __name__ == "__main__":
    main()

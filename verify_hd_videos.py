"""
hw-1 视频质量验证脚本
功能：检查生成的 HD 视频是否符合质量标准

使用方法：
    python verify_hd_videos.py
    python verify_hd_videos.py --tag v10_rolling_foot_walk_HD
    python verify_hd_videos.py --compare  # 对比 720p vs 1080p

作者：段泽琪
日期：2026/06/05
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent


@dataclass
class VideoInfo:
    """视频信息"""

    path: Path
    exists: bool = False
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    duration: float = 0.0
    size_mb: float = 0.0
    bitrate_kbps: float = 0.0


def check_ffprobe_available() -> bool:
    """检查 ffprobe 是否可用"""
    try:
        subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def get_video_info(video_path: Path) -> VideoInfo:
    """获取视频详细信息（使用 ffprobe）"""
    info = VideoInfo(path=video_path)

    if not video_path.exists():
        return info

    info.exists = True
    info.size_mb = video_path.stat().st_size / (1024 * 1024)

    if not check_ffprobe_available():
        print("⚠ ffprobe 不可用，跳过详细信息检查")
        return info

    try:
        # 获取视频流信息
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name,duration,bit_rate",
            "-of",
            "default=noprint_wrappers=1",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 解析输出
        for line in result.stdout.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                if key == "width":
                    info.width = int(value)
                elif key == "height":
                    info.height = int(value)
                elif key == "r_frame_rate":
                    # 格式: "60/1"
                    if "/" in value:
                        num, denom = value.split("/")
                        info.fps = float(num) / float(denom)
                elif key == "codec_name":
                    info.codec = value
                elif key == "duration":
                    info.duration = float(value)
                elif key == "bit_rate":
                    info.bitrate_kbps = float(value) / 1000

    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"⚠ 解析视频信息失败: {e}")

    return info


def verify_hd_quality(info: VideoInfo, tag: str) -> tuple[bool, list[str]]:
    """验证 HD 视频质量是否符合标准"""
    issues = []
    passed = True

    # 检查分辨率
    if info.width != 1920 or info.height != 1080:
        issues.append(f"✗ 分辨率错误: {info.width}×{info.height} (预期 1920×1080)")
        passed = False
    else:
        issues.append(f"✓ 分辨率正确: {info.width}×{info.height}")

    # 检查帧率
    if abs(info.fps - 60.0) > 1.0:
        issues.append(f"⚠ 帧率异常: {info.fps:.1f} fps (预期 60 fps)")
    else:
        issues.append(f"✓ 帧率正确: {info.fps:.1f} fps")

    # 检查编码器
    if info.codec and info.codec != "h264":
        issues.append(f"⚠ 编码器非 H.264: {info.codec}")
    elif info.codec:
        issues.append(f"✓ 编码器正确: {info.codec}")

    # 检查文件大小
    if info.size_mb < 0.5:
        issues.append(f"⚠ 文件过小: {info.size_mb:.2f} MB (可能渲染失败)")
    elif info.size_mb > 5.0:
        issues.append(f"⚠ 文件过大: {info.size_mb:.2f} MB (编码质量过高)")
    else:
        issues.append(f"✓ 文件大小合理: {info.size_mb:.2f} MB")

    # 检查时长
    if info.duration > 0:
        if info.duration < 3.0:
            issues.append(f"⚠ 时长过短: {info.duration:.1f} s (可能仿真失败)")
        else:
            issues.append(f"✓ 时长正常: {info.duration:.1f} s")

    return passed, issues


def find_hd_videos() -> list[Path]:
    """查找所有 HD 视频文件"""
    hd_videos = []
    for out_dir in HW1_ROOT.rglob("out"):
        for video in out_dir.glob("*_HD.mp4"):
            hd_videos.append(video)
    return sorted(hd_videos)


def compare_720p_vs_1080p():
    """对比 720p 和 1080p 版本"""
    print("=" * 80)
    print("对比 720p vs 1080p 版本")
    print("=" * 80)

    hd_videos = find_hd_videos()

    if not hd_videos:
        print("未找到 HD 视频文件")
        return

    comparison_data = []

    for hd_path in hd_videos:
        # 查找对应的 720p 版本（去掉 _HD 后缀）
        tag_720p = hd_path.stem.replace("_HD", "")
        path_720p = hd_path.parent / f"{tag_720p}.mp4"

        info_720p = get_video_info(path_720p) if path_720p.exists() else None
        info_1080p = get_video_info(hd_path)

        comparison_data.append((tag_720p, info_720p, info_1080p))

    # 打印对比表格
    print(f"\n{'版本':<30} {'分辨率':<15} {'大小 (MB)':<12} {'码率 (kbps)':<15}")
    print("-" * 80)

    for tag, info_720p, info_1080p in comparison_data:
        print(f"\n{tag}")

        if info_720p and info_720p.exists:
            print(
                f"  720p:  {info_720p.width}×{info_720p.height:<7} "
                f"{info_720p.size_mb:>8.2f}      {info_720p.bitrate_kbps:>10.1f}"
            )
        else:
            print("  720p:  [原版不存在或已归档]")

        if info_1080p.exists:
            print(
                f"  1080p: {info_1080p.width}×{info_1080p.height:<7} "
                f"{info_1080p.size_mb:>8.2f}      {info_1080p.bitrate_kbps:>10.1f}"
            )

            if info_720p and info_720p.exists:
                size_ratio = info_1080p.size_mb / info_720p.size_mb
                print(f"  增长:  {size_ratio:.2f}x")
        else:
            print("  1080p: [HD 版本不存在]")


def main():
    parser = argparse.ArgumentParser(
        description="hw-1 视频质量验证脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--tag", help="验证指定标签的视频")
    parser.add_argument("--compare", action="store_true", help="对比 720p vs 1080p")
    parser.add_argument("--all", action="store_true", help="验证所有 HD 视频")

    args = parser.parse_args()

    # 对比模式
    if args.compare:
        compare_720p_vs_1080p()
        return

    # 单个视频验证
    if args.tag:
        # 查找视频文件
        video_path = None
        for out_dir in HW1_ROOT.rglob("out"):
            candidate = out_dir / f"{args.tag}.mp4"
            if candidate.exists():
                video_path = candidate
                break

        if not video_path:
            print(f"✗ 视频不存在: {args.tag}.mp4")
            return

        print("=" * 80)
        print(f"验证视频: {args.tag}")
        print("=" * 80)

        info = get_video_info(video_path)

        if not info.exists:
            print(f"✗ 文件不存在: {video_path}")
            return

        print(f"\n路径: {video_path}")
        print(f"大小: {info.size_mb:.2f} MB")

        if check_ffprobe_available():
            print(f"分辨率: {info.width}×{info.height}")
            print(f"帧率: {info.fps:.1f} fps")
            print(f"编码器: {info.codec}")
            print(f"时长: {info.duration:.1f} s")
            print(f"码率: {info.bitrate_kbps:.1f} kbps")

            if "_HD" in args.tag:
                print("\n质量检查结果:")
                passed, issues = verify_hd_quality(info, args.tag)
                for issue in issues:
                    print(f"  {issue}")
                print(f"\n{'✓ 质量验证通过' if passed else '✗ 质量验证失败'}")
        else:
            print("\n⚠ ffprobe 未安装，无法获取详细信息")
            print("安装 ffmpeg 以启用完整验证功能")

        return

    # 验证所有 HD 视频
    if args.all or not (args.tag or args.compare):
        hd_videos = find_hd_videos()

        if not hd_videos:
            print("未找到 HD 视频文件")
            print("\n请先运行渲染脚本：")
            print("  python batch_render_hd.py --priority A")
            return

        print("=" * 80)
        print(f"验证所有 HD 视频 (共 {len(hd_videos)} 个)")
        print("=" * 80)

        results = []

        for video_path in hd_videos:
            tag = video_path.stem
            info = get_video_info(video_path)

            if check_ffprobe_available():
                passed, issues = verify_hd_quality(info, tag)
                results.append((tag, passed, info))
            else:
                results.append((tag, None, info))

        # 打印汇总表格
        print(f"\n{'标签':<40} {'分辨率':<15} {'大小 (MB)':<12} {'状态'}")
        print("-" * 80)

        for tag, passed, info in results:
            status = "✓ 通过" if passed else "✗ 失败" if passed is False else "⚠ 跳过"
            print(
                f"{tag:<40} {info.width}×{info.height:<10} {info.size_mb:>8.2f}      {status}"
            )

        # 统计
        if check_ffprobe_available():
            passed_count = sum(1 for _, p, _ in results if p is True)
            failed_count = sum(1 for _, p, _ in results if p is False)

            print("\n" + "=" * 80)
            print(f"验证完成: {passed_count} 通过, {failed_count} 失败")
            print("=" * 80)

            if failed_count > 0:
                print("\n失败的视频：")
                for tag, passed, _ in results:
                    if passed is False:
                        print(f"  - {tag}")
        else:
            print("\n⚠ ffprobe 未安装，无法进行质量验证")
            print("安装 ffmpeg：https://ffmpeg.org/download.html")


if __name__ == "__main__":
    main()

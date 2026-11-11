"""生成视频预览图。"""

from pathlib import Path

import imageio.v2 as imageio

OUT_DIR = Path(__file__).resolve().parent / "out"


def extract_preview_frame(video_path: Path, frame_idx: int = 0) -> None:
    """从视频中提取预览帧。"""
    reader = imageio.get_reader(str(video_path))
    try:
        frame = reader.get_data(frame_idx)
        preview_path = video_path.with_suffix(".png")
        imageio.imwrite(str(preview_path), frame)
        print(f"[preview] {video_path.name} -> {preview_path.name}")
    finally:
        reader.close()


def main():
    # 扰动恢复视频：提取第150帧（约5秒处，扰动开始衰减）
    video1 = OUT_DIR / "v13b_perturbation_recovery.mp4"
    if video1.exists():
        extract_preview_frame(video1, frame_idx=150)

    # 相平面视频：提取第10帧（约一半进度）
    video2 = OUT_DIR / "v13b_phase_portrait.mp4"
    if video2.exists():
        extract_preview_frame(video2, frame_idx=10)


if __name__ == "__main__":
    main()

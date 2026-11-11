"""
渲染脚本高清升级模板
用途：将现有 720p 渲染脚本升级为 1920×1080 HD 版本

升级清单：
1. 修改 mujoco.Renderer 分辨率参数
2. 优化 imageio 编码器参数（使用 H.264 高质量编码）
3. 调整标注字体大小（720p → 1080p 需 × 1.5）
4. 调整标注位置和矩形大小（保持比例）
5. 支持 --tag 参数（用于批处理脚本）
6. 添加 HD 后缀到输出文件名

作者：段泽琪
日期：2026/06/05
"""

# ============================================================
# 第一步：修改 Renderer 分辨率
# ============================================================

# OLD (720p):
renderer = mujoco.Renderer(model, height=720, width=1280)

# NEW (1080p):
renderer = mujoco.Renderer(model, height=1080, width=1920)


# ============================================================
# 第二步：优化 imageio 编码器
# ============================================================

# OLD 方法 1 (mimsave):
imageio.mimsave(out_path, frames, fps=60)

# OLD 方法 2 (基础 get_writer):
with imageio.get_writer(out_path, fps=60) as writer:
    for frame in frames:
        writer.append_data(frame)

# NEW (H.264 高质量编码):
with imageio.get_writer(
    out_path,
    fps=60,
    codec="libx264",
    quality=8,  # CRF 值，8=高质量（范围0-51，值越小越好）
    pixelformat="yuv420p",  # 标准色彩空间，兼容性好
    macro_block_size=1,  # 避免尺寸对齐警告
) as writer:
    for frame in frames:
        writer.append_data(frame)

# 注意：需要安装 imageio-ffmpeg
# pip install imageio-ffmpeg


# ============================================================
# 第三步：调整标注字体大小（720p → 1080p）
# ============================================================

# OLD (720p):
title_font = ImageFont.truetype(str(FONT), 28)  # 或 30
info_font = ImageFont.truetype(str(FONT), 20)

# NEW (1080p):
title_font = ImageFont.truetype(str(FONT), 42)  # 28 × 1.5 = 42
info_font = ImageFont.truetype(str(FONT), 30)  # 20 × 1.5 = 30


# 或者使用辅助函数：
def _font(size: int, scale: float = 1.5):
    """获取缩放后的字体"""
    if FONT.exists():
        return ImageFont.truetype(str(FONT), int(size * scale))
    return ImageFont.load_default()


# 使用：
title_font = _font(28, scale=1.5)  # 自动缩放到 42
info_font = _font(20, scale=1.5)  # 自动缩放到 30


# ============================================================
# 第四步：调整标注矩形位置和大小
# ============================================================

# 原则：保持相对比例，所有坐标 × 1.5

# OLD (720p, width=1280, height=720):
draw.rectangle((24, 22, 1040, 154), fill=(8, 14, 24, 188))
draw.text((42, 34), "标题", font=title_font, fill=(255, 255, 255))
draw.text((44, 82), "信息行1", font=info_font, fill=(232, 238, 244))
draw.text((44, 116), "信息行2", font=info_font, fill=(172, 255, 191))

# NEW (1080p, width=1920, height=1080):
draw.rectangle((36, 33, 1560, 231), fill=(8, 14, 24, 188))
draw.text((63, 51), "标题", font=title_font, fill=(255, 255, 255))
draw.text((66, 123), "信息行1", font=info_font, fill=(232, 238, 244))
draw.text((66, 174), "信息行2", font=info_font, fill=(172, 255, 191))

# 计算方法：
# 矩形左上角：(24, 22) → (24×1.5, 22×1.5) = (36, 33)
# 矩形右下角：(1040, 154) → (1040×1.5, 154×1.5) = (1560, 231)
# 文本位置同理


# ============================================================
# 第五步：支持 --tag 参数（用于批处理）
# ============================================================


# OLD (硬编码文件名):
def main() -> None:
    out_path = OUT_DIR / "v10_rolling_foot_walk.mp4"
    preview_path = OUT_DIR / "v10_rolling_foot_walk_preview.png"


# NEW (支持 --tag 参数):
import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v10_rolling_foot_walk_HD")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    out_path = OUT_DIR / f"{args.tag}.mp4"
    preview_path = OUT_DIR / f"{args.tag}_preview.png"


# ============================================================
# 第六步：完整示例（对比 V17 渲染脚本）
# ============================================================


# === 720p 原版 ===
def render_720p():
    renderer = mujoco.Renderer(model, height=720, width=1280)
    title_font = ImageFont.truetype(str(FONT), 28)
    info_font = ImageFont.truetype(str(FONT), 20)

    def annotate(frame):
        draw.rectangle((24, 22, 1250, 186), fill=(8, 14, 24, 195))
        draw.text((42, 30), "Title", font=title_font, fill=(255, 255, 255))
        draw.text((44, 68), "Info 1", font=info_font, fill=(232, 238, 244))
        draw.text((44, 98), "Info 2", font=info_font, fill=(172, 255, 191))
        return np.array(image)

    with imageio.get_writer(out_path, fps=60) as writer:
        for frame in frames:
            writer.append_data(annotate(frame))


# === 1080p HD 版 ===
def render_1080p_hd():
    renderer = mujoco.Renderer(model, height=1080, width=1920)
    title_font = ImageFont.truetype(str(FONT), 42)  # 28 × 1.5
    info_font = ImageFont.truetype(str(FONT), 30)  # 20 × 1.5

    def annotate(frame):
        # 矩形坐标 × 1.5
        draw.rectangle((36, 33, 1875, 279), fill=(8, 14, 24, 195))
        draw.text((63, 45), "Title", font=title_font, fill=(255, 255, 255))
        draw.text((66, 102), "Info 1", font=info_font, fill=(232, 238, 244))
        draw.text((66, 147), "Info 2", font=info_font, fill=(172, 255, 191))
        return np.array(image)

    with imageio.get_writer(
        out_path,
        fps=60,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as writer:
        for frame in frames:
            writer.append_data(annotate(frame))


# ============================================================
# 第七步：辅助函数 - 自动缩放标注坐标
# ============================================================


def scale_coords(coords: tuple, scale: float = 1.5) -> tuple:
    """缩放坐标元组（用于从720p升级到1080p）"""
    return tuple(int(c * scale) for c in coords)


# 使用示例：
# OLD:
draw.rectangle((24, 22, 1250, 186), fill=(8, 14, 24, 195))

# NEW:
rect_720p = (24, 22, 1250, 186)
rect_1080p = scale_coords(rect_720p, scale=1.5)
draw.rectangle(rect_1080p, fill=(8, 14, 24, 195))


# ============================================================
# 第八步：验证输出质量
# ============================================================

# 使用 ffprobe 验证（需要安装 ffmpeg）:
# ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of default=noprint_wrappers=1 output.mp4

# 预期输出：
# width=1920
# height=1080
# r_frame_rate=60/1
# codec_name=h264


# Python 验证代码：
def verify_video_quality(video_path: Path):
    """验证生成的视频质量"""
    import subprocess

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,codec_name",
        "-of",
        "default=noprint_wrappers=1",
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"视频质量验证：{video_path.name}")
        print(result.stdout)
    except FileNotFoundError:
        print("⚠ ffprobe 未安装，跳过质量验证")


# ============================================================
# 常见问题 FAQ
# ============================================================

"""
Q1: 为什么字体大小要 × 1.5？
A1: 分辨率从 1280×720 升级到 1920×1080，宽高比保持 16:9 不变，
    但宽度从 1280 → 1920，缩放因子为 1920/1280 = 1.5。
    为了保持标注的相对大小一致，所有尺寸参数都要 × 1.5。

Q2: quality=8 是最佳值吗？
A2: CRF 值范围 0-51，值越小质量越高文件越大：
    - 0-10: 接近无损（推荐学术展示）
    - 18-23: 高质量（平衡质量和大小）
    - 24-28: 中等质量
    quality=8 是高质量设置，适合学术论文补充材料。

Q3: 为什么需要 pixelformat='yuv420p'？
A3: yuv420p 是最通用的色彩空间，确保：
    - 所有播放器兼容（VLC/PotPlayer/Windows Media Player）
    - PowerPoint 可以正常嵌入
    - 网页浏览器可以直接播放

Q4: macro_block_size=1 是什么？
A4: 防止 imageio 自动调整视频尺寸导致的警告信息。
    设为 1 表示不进行宏块对齐调整。

Q5: 渲染时间会增加多少？
A5: 1080p 像素数是 720p 的 2.25 倍（1920×1080 / 1280×720），
    预计渲染时间增加 2-2.5 倍。单个 12 秒视频约需 6-10 分钟。

Q6: 如何批量转换所有脚本？
A6: 使用提供的 batch_render_hd.py 脚本：
    python batch_render_hd.py --all
"""


# ============================================================
# 升级检查清单
# ============================================================

"""
渲染脚本升级前检查：
□ 备份原始 720p 脚本
□ 修改 Renderer 分辨率 → 1920×1080
□ 修改 imageio 编码器 → H.264 quality=8
□ 调整标注字体大小 → × 1.5
□ 调整标注矩形坐标 → × 1.5
□ 添加 --tag 参数支持
□ 更新输出文件名 → 添加 _HD 后缀
□ 测试运行单个视频
□ 验证分辨率和质量
□ 检查文件大小合理性（1.5-3 MB）
□ 提交代码前验证播放器兼容性
"""

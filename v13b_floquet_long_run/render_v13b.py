"""V13b 扰动恢复可视化：生成 MP4 动画展示极限环收敛过程。

输出：
1. v13b_perturbation_recovery.mp4  — 4 个扰动场景的步态动画（左上/右上/左下/右下）
2. v13b_phase_portrait.mp4          — 相平面轨迹螺旋收敛到极限环的动画

学术价值：展示 Floquet 慢模 |λ|=0.944 对应的扰动衰减过程，可视化 4D 极限环稳定性。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib

matplotlib.use("Agg")  # 使用非交互式后端
import matplotlib.pyplot as plt
import mujoco
import numpy as np
from matplotlib.patches import Circle
from PIL import Image, ImageDraw, ImageFont

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
HW1 = ROOT.parent
V10_DIR = HW1 / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1))

from simulate_rolling_foot_gait_v10 import (  # noqa: E402
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)

from common.poincare import collect_section  # noqa: E402

OUT_DIR = ROOT / "out"
FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")

STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")


def load_csv_data(path: Path) -> dict[str, np.ndarray]:
    """加载 CSV 数据，返回字典 {key: np.ndarray}。"""
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = {}
    if rows:
        for key in rows[0].keys():
            try:
                data[key] = np.array([float(row[key]) for row in rows])
            except (ValueError, KeyError):
                # 保留字符串字段
                data[key] = [row[key] for row in rows]
    return data


def qpos_at_time(t: float, data: dict[str, np.ndarray]) -> list[float]:
    """插值得到时刻 t 的 qpos。"""
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def render_gait_frame(
    renderer: mujoco.Renderer,
    camera: mujoco.MjvCamera,
    sim_data: mujoco.MjData,
    t: float,
    data: dict[str, np.ndarray],
    case_info: dict,
    fixed_point: np.ndarray,
    lambda_slow: float,
) -> np.ndarray:
    """渲染单帧步态动画，叠加扰动信息和收敛指标。"""
    sim_data.qpos[:] = qpos_at_time(t, data)
    sim_data.qvel[:] = 0.0
    mujoco.mj_forward(sim_data.model, sim_data)
    camera.lookat[:] = [float(sim_data.qpos[0]) + 0.25, 0.0, 0.55]
    renderer.update_scene(sim_data, camera=camera)
    frame = renderer.render()

    # 叠加文字信息
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    try:
        title_font = ImageFont.truetype(str(FONT_PATH), 22)
        font = ImageFont.truetype(str(FONT_PATH), 16)
    except Exception:
        title_font = ImageFont.load_default()
        font = ImageFont.load_default()

    axis = case_info["axis"]
    delta = case_info["delta"]
    distances = case_info.get("distances_to_fp", [])

    # 当前 Poincare 点索引（基于时间和触地事件）
    # 构建行字典时只转换数值字段
    rows_for_section = []
    for i in range(len(data["time"])):
        row = {}
        for key in data.keys():
            val = data[key][i]
            if isinstance(val, (int, float, np.number)):
                row[key] = float(val)
            else:
                row[key] = val
        rows_for_section.append(row)

    section_pts = collect_section(rows_for_section, STATE_KEYS)
    current_idx = min(len(section_pts) - 1, int(t / 0.8))  # 粗略估计
    current_dist = distances[current_idx] if current_idx < len(distances) else np.nan

    # 背景框
    draw.rectangle((10, 10, 630, 140), fill=(8, 14, 24, 200))
    draw.text(
        (20, 18),
        f"扰动轴: {axis}  δ = {delta:+.4f}",
        font=title_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (20, 50),
        f"时刻: {t:.2f} s  |  Poincare 步: {current_idx + 1}",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (20, 75),
        f"到极限环距离: {current_dist:.4f}",
        font=font,
        fill=(172, 255, 191),
    )
    draw.text(
        (20, 100),
        f"Floquet 慢模: |λ| = {lambda_slow:.4f}",
        font=font,
        fill=(255, 220, 100),
    )
    draw.text(
        (20, 115),
        f"预期衰减: d_k = d_0 · {lambda_slow:.3f}^k",
        font=font,
        fill=(200, 200, 200),
    )

    return np.array(image)


def create_perturbation_recovery_video(
    params: RollingFootParams,
    cases: list[dict],
    fixed_point: np.ndarray,
    lambda_slow: float,
    fps: int = 30,
) -> None:
    """生成 4 格扰动恢复视频（2x2 布局）。"""
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    # 为每个 case 创建独立的渲染器和数据
    renderers = []
    cameras = []
    sim_datas = []
    case_data = []

    for case in cases:
        axis = case["axis"]
        csv_path = OUT_DIR / f"v13b_dist_{axis}_data.csv"
        data = load_csv_data(csv_path)
        case_data.append(data)

        renderer = mujoco.Renderer(model, height=360, width=640)
        camera = mujoco.MjvCamera()
        camera.distance = 3.4
        camera.azimuth = 66
        camera.elevation = -18
        renderers.append(renderer)
        cameras.append(camera)
        sim_datas.append(mujoco.MjData(model))

    # 找到最长的仿真时间
    max_duration = max(float(data["time"][-1]) for data in case_data)
    n_frames = int(max_duration * fps)

    print(f"[render] 生成扰动恢复视频，{n_frames} 帧 @ {fps} fps ...")
    frames = []
    for frame_idx in range(n_frames):
        t = frame_idx / fps

        # 渲染 4 个子视频帧
        subframes = []
        for i, (renderer, camera, sim_data, data, case) in enumerate(
            zip(renderers, cameras, sim_datas, case_data, cases)
        ):
            if t <= float(data["time"][-1]):
                subframe = render_gait_frame(
                    renderer, camera, sim_data, t, data, case, fixed_point, lambda_slow
                )
            else:
                # 超时则保持最后一帧
                subframe = render_gait_frame(
                    renderer,
                    camera,
                    sim_data,
                    float(data["time"][-1]),
                    data,
                    case,
                    fixed_point,
                    lambda_slow,
                )
            subframes.append(subframe)

        # 拼接为 2x2 布局
        top = np.hstack([subframes[0], subframes[1]])
        bottom = np.hstack([subframes[2], subframes[3]])
        combined = np.vstack([top, bottom])
        frames.append(combined)

        if (frame_idx + 1) % 100 == 0:
            print(f"  进度: {frame_idx + 1}/{n_frames}")

    out_path = OUT_DIR / "v13b_perturbation_recovery.mp4"
    imageio.mimsave(str(out_path), frames, fps=fps)
    print(f"[render] -> {out_path}")


def create_phase_portrait_video(
    cases: list[dict],
    fixed_point: np.ndarray,
    lambda_slow: float,
    fps: int = 30,
) -> None:
    """生成相平面轨迹动画（2x2 子图：右髋、右膝、复平面）。"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    # 加载所有 case 的 Poincare 截面数据
    all_sections = []
    for case in cases:
        axis = case["axis"]
        csv_path = OUT_DIR / f"v13b_dist_{axis}_data.csv"
        data = load_csv_data(csv_path)
        # 构建行字典时只转换数值字段
        rows = []
        for i in range(len(data["time"])):
            row = {}
            for key in data.keys():
                val = data[key][i]
                if isinstance(val, (int, float, np.number)):
                    row[key] = float(val)
                else:
                    row[key] = val
            rows.append(row)
        section_pts = collect_section(rows, STATE_KEYS)
        all_sections.append(section_pts)

    # 找到最大步数
    max_steps = max(len(sec) for sec in all_sections)

    # 设置轴范围
    all_pts = np.vstack(all_sections)
    hip_range = [all_pts[:, 0].min() - 0.05, all_pts[:, 0].max() + 0.05]
    hip_vel_range = [all_pts[:, 1].min() - 0.1, all_pts[:, 1].max() + 0.1]
    knee_range = [all_pts[:, 2].min() - 0.05, all_pts[:, 2].max() + 0.05]
    knee_vel_range = [all_pts[:, 3].min() - 0.1, all_pts[:, 3].max() + 0.1]

    print(f"[render] 生成相平面动画，{max_steps} 步 @ {fps} fps ...")
    frames = []

    for step in range(1, max_steps + 1):
        for ax in axes:
            ax.clear()

        colors = ["C0", "C1", "C2", "C3"]

        # 子图 0: 右髋相平面
        ax = axes[0]
        for i, (section_pts, case) in enumerate(zip(all_sections, cases)):
            if step <= len(section_pts):
                pts = section_pts[:step]
                ax.plot(
                    pts[:, 0],
                    pts[:, 1],
                    "o-",
                    color=colors[i],
                    alpha=0.6,
                    markersize=4,
                    label=case["axis"],
                )
                # 当前点高亮
                ax.plot(
                    pts[-1, 0],
                    pts[-1, 1],
                    "o",
                    color=colors[i],
                    markersize=8,
                    markeredgecolor="white",
                    markeredgewidth=1.5,
                )
        ax.plot(
            fixed_point[0],
            fixed_point[1],
            "rx",
            markersize=12,
            markeredgewidth=2,
            label="极限环",
        )
        ax.set_xlim(hip_range)
        ax.set_ylim(hip_vel_range)
        ax.set_xlabel("right_hip (rad)")
        ax.set_ylabel("right_hip_vel (rad/s)")
        ax.set_title("右髋相平面轨迹")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")

        # 子图 1: 右膝相平面
        ax = axes[1]
        for i, (section_pts, case) in enumerate(zip(all_sections, cases)):
            if step <= len(section_pts):
                pts = section_pts[:step]
                ax.plot(
                    pts[:, 2],
                    pts[:, 3],
                    "o-",
                    color=colors[i],
                    alpha=0.6,
                    markersize=4,
                    label=case["axis"],
                )
                ax.plot(
                    pts[-1, 2],
                    pts[-1, 3],
                    "o",
                    color=colors[i],
                    markersize=8,
                    markeredgecolor="white",
                    markeredgewidth=1.5,
                )
        ax.plot(
            fixed_point[2],
            fixed_point[3],
            "rx",
            markersize=12,
            markeredgewidth=2,
            label="极限环",
        )
        ax.set_xlim(knee_range)
        ax.set_ylim(knee_vel_range)
        ax.set_xlabel("right_knee (rad)")
        ax.set_ylabel("right_knee_vel (rad/s)")
        ax.set_title("右膝相平面轨迹")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")

        # 子图 2: 到极限环的距离衰减曲线
        ax = axes[2]
        for i, (section_pts, case) in enumerate(zip(all_sections, cases)):
            if step <= len(section_pts):
                distances = np.linalg.norm(
                    section_pts[:step] - fixed_point[None, :], axis=1
                )
                k_arr = np.arange(len(distances))
                ax.semilogy(
                    k_arr,
                    distances,
                    "o-",
                    color=colors[i],
                    alpha=0.7,
                    markersize=4,
                    label=case["axis"],
                )
                # 理论曲线
                if len(distances) > 0:
                    d0 = float(distances[0]) if distances[0] > 0 else 1e-3
                    k_th = np.arange(len(distances))
                    ax.semilogy(
                        k_th,
                        d0 * np.power(lambda_slow, k_th),
                        "--",
                        color=colors[i],
                        alpha=0.4,
                        linewidth=1.5,
                    )
        ax.set_xlabel("Poincaré 步 k")
        ax.set_ylabel("||x_k - fp|| (log)")
        ax.set_title(f"扰动衰减 (理论 |λ|={lambda_slow:.3f})")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8, loc="best")

        # 子图 3: Floquet 乘子复平面标注
        ax = axes[3]
        theta = np.linspace(0, 2 * np.pi, 200)
        ax.plot(np.cos(theta), np.sin(theta), "k--", lw=1, alpha=0.5, label="单位圆")

        # 加载 Floquet 特征值
        summary = json.loads((OUT_DIR / "v13b_floquet_summary.json").read_text())
        eigvals_real = np.array(summary["eigvals_real"])
        eigvals_imag = np.array(summary["eigvals_imag"])

        ax.scatter(
            eigvals_real,
            eigvals_imag,
            s=100,
            c="red",
            marker="x",
            linewidths=2,
            label="Floquet 乘子",
            zorder=10,
        )

        # 标注慢模
        slow_idx = np.argmax(np.abs(eigvals_real + 1j * eigvals_imag))
        ax.annotate(
            f"慢模\n|λ|={lambda_slow:.3f}",
            xy=(eigvals_real[slow_idx], eigvals_imag[slow_idx]),
            xytext=(eigvals_real[slow_idx] + 0.3, eigvals_imag[slow_idx] + 0.2),
            fontsize=10,
            arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
        )

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect("equal")
        ax.set_xlabel("Re")
        ax.set_ylabel("Im")
        ax.set_title("Floquet 乘子谱")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")

        fig.suptitle(
            f"V13b 极限环收敛过程 (Poincaré 步 {step}/{max_steps})\n"
            f"Floquet 慢模 |λ|={lambda_slow:.3f}  理论周期倍增时间 ln(2)/ln(1/|λ|)≈12 步",
            fontsize=13,
        )
        fig.tight_layout()

        # 渲染到图像
        fig.canvas.draw()
        # 使用 buffer_rgba() 替代已弃用的 tostring_rgb()
        buf = fig.canvas.buffer_rgba()
        frame = np.asarray(buf)[:, :, :3]  # 取前3通道（RGB）
        frames.append(frame)

        if step % 5 == 0:
            print(f"  进度: {step}/{max_steps}")

    plt.close(fig)

    out_path = OUT_DIR / "v13b_phase_portrait.mp4"
    imageio.mimsave(str(out_path), frames, fps=fps)
    print(f"[render] -> {out_path}")


def main() -> None:
    # 加载扰动恢复数据
    summary_path = OUT_DIR / "v13b_disturbance_summary.json"
    if not summary_path.exists():
        print(f"[render] 错误: 未找到 {summary_path.name}")
        print("[render] 请先运行 disturbance_recovery_v13b.py 生成数据")
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    fixed_point = np.array(summary["fixed_point"])
    lambda_slow = float(summary["lambda_floquet_slow"])
    cases = summary["cases"]
    params = RollingFootParams(**summary["baseline_params"])

    print(f"[render] V13b 扰动恢复可视化")
    print(f"[render] 固定点: {fixed_point}")
    print(f"[render] Floquet 慢模: |λ| = {lambda_slow:.4f}")
    print(f"[render] 扰动场景数: {len(cases)}")

    # 生成扰动恢复视频（步态动画）
    create_perturbation_recovery_video(params, cases, fixed_point, lambda_slow, fps=30)

    # 生成相平面轨迹视频
    create_phase_portrait_video(cases, fixed_point, lambda_slow, fps=5)

    print("[render] 完成！")


if __name__ == "__main__":
    main()

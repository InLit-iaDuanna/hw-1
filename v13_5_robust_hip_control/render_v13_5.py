"""V13.5 渲染脚本：三方案对比 + Plan C 扫描热图。

输出：
  - v13_5_plan_comparison.mp4：Plan A/A'/C 三方案失败过程并排对比
  - v13_5_scan_heatmap.mp4：Plan C 参数扫描热图动画（foot_radius × leg_scale）
  - v13_5_planC_kE_Estar_heatmap.png：Plan C 自身参数敏感性静态图

用法：
  python render_v13_5.py --mode comparison
  python render_v13_5.py --mode heatmap
  python render_v13_5.py --mode all
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(ROOT.parent))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)  # noqa: E402

from common import set_style  # noqa: E402

OUT_DIR = ROOT / "out"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_csv(tag: str):
    """加载 CSV 数据为字典数组。"""
    path = OUT_DIR / f"{tag}_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = ["time", *QPOS_KEYS, "hip_clearance", "input_energy"]
    return {k: np.array([float(r[k]) for r in rows]) for k in keys}


def load_summary(tag: str) -> dict:
    path = OUT_DIR / f"{tag}_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def qpos_at(t: float, data) -> list[float]:
    """插值获取时刻 t 的 qpos。"""
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def render_frame(model, renderer, camera, qpos: list[float]) -> np.ndarray:
    """渲染单帧。"""
    sim_data = mujoco.MjData(model)
    sim_data.qpos[:] = qpos
    sim_data.qvel[:] = 0.0
    mujoco.mj_forward(model, sim_data)
    camera.lookat[:] = [float(sim_data.qpos[0]) + 0.25, 0.0, 0.55]
    renderer.update_scene(sim_data, camera=camera)
    return renderer.render()


def render_comparison(fps: int = 60) -> None:
    """渲染 Plan A/A'/C 三方案失败对比动画（三列并排）。"""
    print("[render_v13_5] 渲染三方案对比...")

    # 方案 A：baseline（实际是退化到 V10 的 alpha=0），失败案例用 F02_a0.2
    # 方案 A'：提力矩限幅（用 V13 G 切片的失败案例，这里用 alpha=0 代表）
    # 方案 C：能量整形 bang-bang（baseline 失败）
    plans = [
        {
            "tag": "v13_5_baseline",
            "label": "Plan A：步周期自适应",
            "desc": "EMA 跟踪实测步周期\n→ 12 步成功 (α=0退化V10)",
        },
        {
            "tag": "v13_5_F02_a0.2",
            "label": "Plan A'：非零自适应",
            "desc": "α=0.2 调整步周期\n→ 立即 fall_down",
        },
        {
            "tag": "v13_5_planC_baseline",
            "label": "Plan C：能量整形 bang-bang",
            "desc": "E_star=52.66J, k_E=7.5\n→ 0/36 成功率",
        },
    ]

    # 加载数据
    datasets = []
    summaries = []
    for plan in plans:
        try:
            data = load_csv(plan["tag"])
            summary = load_summary(plan["tag"])
            datasets.append(data)
            summaries.append(summary)
        except FileNotFoundError as e:
            print(f"  警告：{e}")
            return

    # 找最长仿真时长
    max_duration = max(float(d["time"][-1]) for d in datasets)

    # 设置渲染
    params = RollingFootParams(**summaries[0]["params"])
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    renderer = mujoco.Renderer(model, height=480, width=426)
    camera = mujoco.MjvCamera()
    camera.distance = 3.2
    camera.azimuth = 66
    camera.elevation = -18

    # 渲染帧
    n_frames = max(1, int(max_duration * fps))
    frames_combined = []

    for idx in range(n_frames):
        t = idx / fps
        panels = []

        for i, (data, summary, plan) in enumerate(zip(datasets, summaries, plans)):
            # 渲染机器人
            qpos = qpos_at(min(t, float(data["time"][-1])), data)
            frame = render_frame(model, renderer, camera, qpos)

            # 标注
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img, "RGBA")
            title_font = ImageFont.truetype(str(FONT), 20)
            font = ImageFont.truetype(str(FONT), 14)

            # 半透明背景
            draw.rectangle((10, 10, 416, 110), fill=(8, 14, 24, 200))
            draw.text((20, 16), plan["label"], font=title_font, fill=(255, 255, 255))
            draw.text((20, 48), plan["desc"], font=font, fill=(232, 238, 244))

            # 当前状态
            if t <= float(data["time"][-1]):
                clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
                status = f"t={t:.2f}s  髋高={clearance:.2f}m"
                color = (172, 255, 191) if summary["success"] else (255, 172, 172)
            else:
                status = f"ENDED: {summary['failure']}"
                color = (255, 172, 172)

            draw.text((20, 85), status, font=font, fill=color)
            panels.append(np.array(img))

        # 拼接三列
        combined = np.hstack(panels)

        # 顶部总标题
        h, w = combined.shape[:2]
        header = np.zeros((80, w, 3), dtype=np.uint8)
        header_img = Image.fromarray(header)
        header_draw = ImageDraw.Draw(header_img, "RGBA")
        header_font = ImageFont.truetype(str(FONT), 28)
        header_draw.rectangle((0, 0, w, 80), fill=(24, 28, 36, 255))
        header_draw.text(
            (w // 2, 40),
            "V13.5 三方案对比：均失败 → 引出 V13.6 FSM",
            font=header_font,
            fill=(255, 255, 255),
            anchor="mm",
        )
        combined = np.vstack([np.array(header_img), combined])
        frames_combined.append(combined)

    out = OUT_DIR / "v13_5_plan_comparison.mp4"
    imageio.mimsave(out, frames_combined, fps=fps)
    print(f"  -> {out}")

    preview = OUT_DIR / "v13_5_plan_comparison_preview.png"
    imageio.imwrite(preview, frames_combined[min(len(frames_combined) - 1, 60)])
    print(f"  -> {preview}")


def render_scan_heatmap() -> None:
    """渲染 Plan C 扫描热图动画（参数空间扫描过程）。"""
    print("[render_v13_5] 渲染 Plan C 扫描热图...")

    # 加载 Plan C 切片 C 数据
    csv_path = OUT_DIR / "v13_5_planC_C_foot_leg.csv"
    meta_path = OUT_DIR / "v13_5_planC_C_foot_leg_meta.json"
    if not csv_path.exists() or not meta_path.exists():
        print(f"  警告：{csv_path} 或 {meta_path} 不存在，跳过热图渲染")
        return

    with csv_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # 提取参数
    foot_radii = sorted({float(r["foot_radius_x"]) for r in rows})
    leg_scales = sorted({float(r["leg_scale_y"]) for r in rows})
    grid_size = len(foot_radii)

    # 构建热图矩阵
    grid_success = np.zeros((grid_size, grid_size))
    grid_alt = np.zeros((grid_size, grid_size))
    grid_failure = np.empty((grid_size, grid_size), dtype=object)

    for r in rows:
        i = foot_radii.index(float(r["foot_radius_x"]))
        j = leg_scales.index(float(r["leg_scale_y"]))
        grid_success[j, i] = 1.0 if r["success"] == "True" else 0.0
        grid_alt[j, i] = int(r["alternating_touchdowns"])
        grid_failure[j, i] = r["failure"]

    # 对比数据（V10 baseline）
    v10_comparison = json.loads(
        (OUT_DIR / "v13_5_planC_vs_v10.json").read_text(encoding="utf-8")
    )

    # 设置绘图样式
    set_style()
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    # 生成静态热图
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle(
        f"V13.5 Plan C 扫描：0/36 成功 vs V10 6/36 (16.7%) — 能量整形方案被否决",
        fontsize=15,
    )

    # 左图：成功/失败热图
    ax = axes[0]
    im = ax.imshow(
        grid_success,
        origin="lower",
        aspect="auto",
        cmap="RdYlGn",
        extent=[
            foot_radii[0] - 0.002,
            foot_radii[-1] + 0.002,
            leg_scales[0] - 0.02,
            leg_scales[-1] + 0.02,
        ],
        vmin=0,
        vmax=1,
    )
    ax.set_xticks(foot_radii)
    ax.set_yticks(leg_scales)
    ax.set_xlabel("foot_radius / m")
    ax.set_ylabel("leg_scale")
    ax.set_title("成功（绿）/ 失败（红）")
    for i, fr in enumerate(foot_radii):
        for j, ls in enumerate(leg_scales):
            fail_text = (
                grid_failure[j, i]
                .replace("completed", "OK")
                .replace("fall_down", "fall")
                .replace("backward", "back")
                .replace("nan_or_unstable", "nan")
            )
            ax.text(
                fr,
                ls,
                fail_text,
                ha="center",
                va="center",
                fontsize=7,
                color="black" if grid_success[j, i] > 0.5 else "white",
            )
    fig.colorbar(im, ax=ax)

    # 右图：触地数热图
    ax = axes[1]
    im = ax.imshow(
        grid_alt,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=[
            foot_radii[0] - 0.002,
            foot_radii[-1] + 0.002,
            leg_scales[0] - 0.02,
            leg_scales[-1] + 0.02,
        ],
    )
    ax.set_xticks(foot_radii)
    ax.set_yticks(leg_scales)
    ax.set_xlabel("foot_radius / m")
    ax.set_ylabel("leg_scale")
    ax.set_title("交替触地数（最大 12）")
    for i, fr in enumerate(foot_radii):
        for j, ls in enumerate(leg_scales):
            ax.text(
                fr,
                ls,
                f"{int(grid_alt[j, i])}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if grid_alt[j, i] < 6 else "black",
            )
    fig.colorbar(im, ax=ax)

    out = OUT_DIR / "v13_5_planC_C_foot_leg_heatmap.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  -> {out}")

    # 生成动画：逐点扫描过程
    frames = []
    scan_order = [(i, j) for i in range(grid_size) for j in range(grid_size)]

    for step, (i, j) in enumerate(scan_order):
        fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
        fig.suptitle(
            f"V13.5 Plan C 扫描进度：{step + 1}/36 点 — 当前 foot_r={foot_radii[i]:.3f}m leg_scale={leg_scales[j]:.2f}",
            fontsize=15,
        )

        # 左图：成功热图（逐渐填充）
        ax = axes[0]
        partial_success = np.full_like(grid_success, np.nan)
        for si, sj in scan_order[: step + 1]:
            partial_success[sj, si] = grid_success[sj, si]

        im = ax.imshow(
            partial_success,
            origin="lower",
            aspect="auto",
            cmap="RdYlGn",
            extent=[
                foot_radii[0] - 0.002,
                foot_radii[-1] + 0.002,
                leg_scales[0] - 0.02,
                leg_scales[-1] + 0.02,
            ],
            vmin=0,
            vmax=1,
        )
        ax.set_xticks(foot_radii)
        ax.set_yticks(leg_scales)
        ax.set_xlabel("foot_radius / m")
        ax.set_ylabel("leg_scale")
        ax.set_title("成功（绿）/ 失败（红）")
        ax.plot(foot_radii[i], leg_scales[j], "ko", markersize=10)  # 当前点

        # 右图：累计统计
        ax = axes[1]
        ax.axis("off")
        n_scanned = step + 1
        n_success = sum(
            grid_success[sj, si] for si, sj in scan_order[: step + 1]
        )
        success_rate = n_success / n_scanned * 100

        info_text = f"""
Plan C 参数扫描统计

已扫描：{n_scanned} / 36 点
成功：{int(n_success)} 点
成功率：{success_rate:.1f}%

当前点：
  foot_radius = {foot_radii[i]:.3f} m
  leg_scale = {leg_scales[j]:.2f}
  结果：{'✓ 成功' if grid_success[j, i] > 0.5 else f'✗ {grid_failure[j, i]}'}
  触地数：{int(grid_alt[j, i])}

对比 V10 baseline：
  V10 成功率：16.7% (6/36)
  Plan C 成功率：{success_rate:.1f}%
  差值：{success_rate - 16.7:+.1f} pp

E_star = {meta['E_star']} J
k_E = {meta['k_E']} Nm/J
"""
        ax.text(
            0.1,
            0.5,
            info_text,
            fontsize=13,
            verticalalignment="center",
            family="sans-serif",
        )

        # 转为图像
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        img = img[:, :, :3]  # 移除 alpha 通道
        frames.append(img)
        plt.close(fig)

    # 最后添加 5 秒结论帧
    fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)
    fig.suptitle(
        "V13.5 Plan C 扫描结论：0/36 成功 — 方案被否决",
        fontsize=16,
        color="red",
    )
    ax.axis("off")
    conclusion = """
【V13.5 三方案总结】

Plan A（步周期自适应）：
  - 假设：相位错位是孤立点根因
  - 结果：α>0 时立即失败，EMA 扰乱极限环
  - 否决依据：period_history 抖动 0.40–0.63s

Plan A'（提力矩限幅）：
  - 假设：τ_limit=4Nm 太低，提高后 kp 容差变宽
  - 结果：反直觉 —— τ_limit 提高后全部失败
  - 否决依据：切片 G，τ_limit=4→20 时成功率 4/6→0/6

Plan C（能量整形 bang-bang）：
  - 假设：显式建模饱和供能，E_error → hip_amplitude
  - 结果：0/36 成功（vs V10 6/36 = 16.7%）
  - 否决依据：本次扫描 + k_E×E_star 敏感性扫描均 0%

【机理修正】
V10 hip 不是 PD 跟踪，而是 **bang-bang 隐式饱和驱动**：
  - baseline 成功时 58.8% 时间在饱和
  - PD 增益本质是**饱和占空比的形状参数**
  - 单一标量目标（角度/能量）不足以替代时序锁定

【决议】
→ V13.6 事件驱动 FSM：从"步态时序结构"层面切入
   分相位控制（stance_early/late, swing_thrust/retract）
"""
    ax.text(0.5, 0.5, conclusion, fontsize=12, verticalalignment="center", ha="center", family="sans-serif")
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    img = img[:, :, :3]  # 移除 alpha 通道
    for _ in range(5 * 30):  # 5秒，30fps
        frames.append(img)
    plt.close(fig)

    out_mp4 = OUT_DIR / "v13_5_scan_heatmap.mp4"
    imageio.mimsave(out_mp4, frames, fps=30)
    print(f"  -> {out_mp4}")


def render_kE_Estar_heatmap() -> None:
    """渲染 k_E × E_star 敏感性静态热图。"""
    print("[render_v13_5] 渲染 k_E × E_star 敏感性...")

    csv_path = OUT_DIR / "v13_5_planC_kE_Estar.csv"
    meta_path = OUT_DIR / "v13_5_planC_kE_Estar_meta.json"
    if not csv_path.exists() or not meta_path.exists():
        print(f"  警告：{csv_path} 或 {meta_path} 不存在，跳过")
        return

    with csv_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    k_Es = sorted({float(r["k_E_x"]) for r in rows})
    E_stars = sorted({float(r["E_star_y"]) for r in rows})

    grid_success = np.zeros((len(E_stars), len(k_Es)))
    for r in rows:
        i = k_Es.index(float(r["k_E_x"]))
        j = E_stars.index(float(r["E_star_y"]))
        grid_success[j, i] = 1.0 if r["success"] == "True" else 0.0

    set_style()
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]

    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    n_success = int(grid_success.sum())
    fig.suptitle(
        f"V13.5 Plan C 参数敏感性：k_E × E_star （{n_success}/{len(rows)} 成功）",
        fontsize=15,
    )

    im = ax.imshow(
        grid_success,
        origin="lower",
        aspect="auto",
        cmap="RdYlGn",
        extent=[k_Es[0] - 1, k_Es[-1] + 1, E_stars[0] - 0.5, E_stars[-1] + 0.5],
        vmin=0,
        vmax=1,
    )
    ax.set_xticks(k_Es)
    ax.set_yticks(E_stars)
    ax.set_xlabel("k_E / (Nm/J)")
    ax.set_ylabel("E_star / J")
    ax.set_title("成功（绿）/ 失败（红）— baseline 物理（foot_r=0.04, leg_scale=1.0）")
    fig.colorbar(im, ax=ax)

    out = OUT_DIR / "v13_5_planC_kE_Estar_heatmap.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="V13.5 渲染：三方案对比 + Plan C 扫描热图")
    parser.add_argument(
        "--mode",
        choices=["comparison", "heatmap", "all"],
        default="all",
        help="渲染模式：comparison=三方案对比，heatmap=扫描热图，all=全部",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.mode in ["comparison", "all"]:
        render_comparison()

    if args.mode in ["heatmap", "all"]:
        render_scan_heatmap()
        render_kE_Estar_heatmap()

    print("[render_v13_5] 完成")


if __name__ == "__main__":
    main()

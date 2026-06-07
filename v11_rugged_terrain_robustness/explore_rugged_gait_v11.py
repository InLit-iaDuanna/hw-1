"""V11 交互式参数 explorer：滑块调地形振幅 / 脉冲 / 脉冲时刻 / 相位噪声 / 种子，
点击 Run 跑一次仿真，绘制 hip 轨迹、触地序列、地形剖面与状态摘要；
点击 View 3D 在 MuJoCo passive viewer 里回放最近一次仿真。

快捷键：R = Run，V = View 3D，0 = Reset，1/2/3 = 预设 Flat / Terrain / Hard

用法：
    .\\.venv-mujoco\\Scripts\\python.exe .\v11_rugged_terrain_robustness\\explore_rugged_gait_v11.py
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from matplotlib.widgets import Button, Slider

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulate_rugged_gait_v11 import (  # noqa: E402
    RuggedScenario,
    load_v10_best_params,
    run_rugged_simulation,
)

from common import terrain  # noqa: E402
from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (  # noqa: E402
    RollingFootParams,
)

VIEW_PREFIX = "v11_explore_last"
VIEW_SCRIPT = ROOT / "view_rugged_gait_v11.py"
BASE_PARAMS = load_v10_best_params()
DURATION = 12.0

# 配色：参考 V11 报告口径，左脚冷色、右脚暖色、扰动用红、地形用沙色
C_LEFT = "#1f7a3a"
C_RIGHT = "#b06000"
C_TRACE = "#1f5fa8"
C_HIP = "#2c3e50"
C_IMPULSE = "#c0392b"
C_TERRAIN = "#8a6f3e"
C_TERRAIN_FILL = "#d6c39a"
C_BG = "#f7f7f4"
C_PANEL = "#ffffff"

PRESETS = {
    "Flat": {"amp": 0.000, "imp": 0.0, "imp_t": 4.0, "sigma": 0.0, "seed": 0},
    "Terrain": {"amp": 0.015, "imp": 0.0, "imp_t": 4.0, "sigma": 0.0, "seed": 0},
    "Hard": {"amp": 0.040, "imp": 60.0, "imp_t": 4.0, "sigma": 0.0, "seed": 0},
}


def simulate(amp, imp, imp_t, sigma, seed):
    scenario = RuggedScenario(
        terrain_amplitude_m=amp,
        terrain_wavelength_m=1.2,
        terrain_seed=seed,
        impulse_force_n=imp,
        impulse_t_s=imp_t,
        impulse_duration_s=0.05,
        contact_phase_noise_s=sigma,
        contact_phase_seed=seed,
    )
    params = RollingFootParams(**{**asdict(BASE_PARAMS), "duration": DURATION})
    rows, summary = run_rugged_simulation(params, scenario, save_prefix=VIEW_PREFIX)
    return rows, summary, scenario


def terrain_profile(amp, seed, length_m=90.0):
    if amp <= 0.0:
        xs = np.linspace(-1, 30, 200)
        return xs, np.zeros_like(xs)
    grid = terrain.generate_profile(amp, 1.2, length_m=length_m, seed=seed)
    heights = grid[0] * amp
    xs = np.linspace(-length_m / 2.0, length_m / 2.0, heights.size)
    return xs, heights


def main() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.facecolor": C_PANEL,
            "axes.edgecolor": "#cccccc",
            "axes.labelcolor": "#333333",
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "xtick.color": "#555555",
            "ytick.color": "#555555",
            "grid.color": "#e3e3e3",
            "grid.linewidth": 0.8,
            "figure.facecolor": C_BG,
        }
    )

    fig = plt.figure(figsize=(15, 9.5))
    fig.canvas.manager.set_window_title("V11 Rugged Gait Explorer")

    # ---- 主区域：左 3 个图 + 右状态卡片 ----
    gs = fig.add_gridspec(
        3,
        2,
        height_ratios=[1, 1, 1.15],
        width_ratios=[3.2, 1],
        left=0.06,
        right=0.985,
        top=0.96,
        bottom=0.34,
        hspace=0.42,
        wspace=0.14,
    )
    ax_hipx = fig.add_subplot(gs[0, 0])
    ax_hipz = fig.add_subplot(gs[1, 0], sharex=ax_hipx)
    ax_terrain = fig.add_subplot(gs[2, 0])
    ax_status = fig.add_subplot(gs[:, 1])
    ax_status.set_xlim(0, 1)
    ax_status.set_ylim(0, 1)
    ax_status.set_xticks([])
    ax_status.set_yticks([])
    for spine in ax_status.spines.values():
        spine.set_visible(False)

    for ax in (ax_hipx, ax_hipz, ax_terrain):
        ax.grid(alpha=0.5)

    # ---- 滑块（左侧）+ 数值标签（右侧） ----
    fig.text(0.06, 0.295, "扰动参数", fontsize=11, fontweight="bold", color="#222222")

    slider_specs = [
        ("amp", "地形振幅", "m", 0.0, 0.08, 0.015, 0.001, "{:.3f}"),
        ("imp", "脉冲幅值", "N", 0.0, 120.0, 0.0, 2.0, "{:.0f}"),
        ("imp_t", "脉冲时刻", "s", 0.5, 11.0, 4.0, 0.1, "{:.1f}"),
        ("sigma", "相位噪声 σ", "s", 0.0, 0.08, 0.0, 0.002, "{:.3f}"),
        ("seed", "随机种子", "", 0, 9, 0, 1, "{:d}"),
    ]

    sliders = {}
    value_labels = {}
    y_top = 0.255
    dy = 0.038
    for i, (key, label, unit, vmin, vmax, vinit, step, fmt) in enumerate(slider_specs):
        y = y_top - i * dy
        ax_s = fig.add_axes([0.13, y, 0.46, 0.022])
        s = Slider(
            ax_s,
            label,
            vmin,
            vmax,
            valinit=vinit,
            valstep=step,
            color="#6aa3d8",
            initcolor="none",
            track_color="#dbe4ee",
        )
        s.label.set_fontsize(10)
        s.valtext.set_visible(False)  # 用自己的 label
        sliders[key] = s
        # 自定义数值显示
        unit_str = f" {unit}" if unit else ""
        txt = fig.text(
            0.605,
            y + 0.011,
            fmt.format(vinit) + unit_str,
            fontsize=10,
            fontfamily="DejaVu Sans Mono",
            va="center",
            color="#1f3a5f",
            fontweight="bold",
        )
        value_labels[key] = (txt, fmt, unit_str)

        def make_updater(k, fmt_, unit_):
            def _u(val):
                value_labels[k][0].set_text(
                    fmt_.format(
                        val
                        if not isinstance(val, float) or fmt_ != "{:d}"
                        else int(val)
                    )
                    + unit_
                )

            return _u

        s.on_changed(make_updater(key, fmt, unit_str))

    # ---- 按钮区（右下） ----
    fig.text(0.66, 0.295, "动作", fontsize=11, fontweight="bold", color="#222222")
    btn_run = Button(
        fig.add_axes([0.66, 0.220, 0.10, 0.055]),
        "▶ Run  (R)",
        color="#cfe3f5",
        hovercolor="#9bc5e8",
    )
    btn_view = Button(
        fig.add_axes([0.77, 0.220, 0.11, 0.055]),
        "🎬 View 3D  (V)",
        color="#d4ecd5",
        hovercolor="#9fd9a0",
    )
    btn_reset = Button(
        fig.add_axes([0.89, 0.220, 0.09, 0.055]),
        "↺ Reset  (0)",
        color="#eeeeee",
        hovercolor="#cccccc",
    )
    for b in (btn_run, btn_view, btn_reset):
        b.label.set_fontsize(10)
        b.label.set_fontweight("bold")

    fig.text(0.66, 0.180, "预设场景", fontsize=11, fontweight="bold", color="#222222")
    btn_p1 = Button(
        fig.add_axes([0.66, 0.110, 0.10, 0.055]),
        "1  Flat\n(0/0N)",
        color="#e8f5e8",
        hovercolor="#bfe0bf",
    )
    btn_p2 = Button(
        fig.add_axes([0.77, 0.110, 0.10, 0.055]),
        "2  Terrain\n(15mm/0N)",
        color="#fff7e0",
        hovercolor="#f1d99e",
    )
    btn_p3 = Button(
        fig.add_axes([0.88, 0.110, 0.10, 0.055]),
        "3  Hard\n(40mm/60N)",
        color="#fbe0e0",
        hovercolor="#e8a0a0",
    )
    for b in (btn_p1, btn_p2, btn_p3):
        b.label.set_fontsize(9)

    # 底部 hint
    fig.text(
        0.5,
        0.03,
        "口径：V11 = V10 准被动滚动足步态 + 地形/脉冲/相位扰动；非纯被动；失败如实报告。",
        ha="center",
        fontsize=9,
        color="#666666",
        style="italic",
    )

    # ---- 状态卡片（右侧 ax_status） ----
    badge_box = FancyBboxPatch(
        (0.05, 0.86),
        0.9,
        0.10,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=0,
        facecolor="#dddddd",
        transform=ax_status.transAxes,
    )
    ax_status.add_patch(badge_box)
    badge_text = ax_status.text(
        0.5,
        0.91,
        "等待 Run",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="center",
        color="#444444",
        transform=ax_status.transAxes,
    )
    failure_text = ax_status.text(
        0.5,
        0.815,
        "",
        fontsize=9,
        ha="center",
        va="center",
        color="#666666",
        transform=ax_status.transAxes,
    )

    # 指标卡片
    metric_lines = ax_status.text(
        0.05,
        0.74,
        "",
        fontsize=10,
        va="top",
        ha="left",
        transform=ax_status.transAxes,
        color="#222222",
        linespacing=1.6,
    )

    last = {"rows": None, "summary": None, "scenario": None}
    viewer_proc: dict[str, subprocess.Popen | None] = {"p": None}

    def render(rows, summary, scenario):
        for ax in (ax_hipx, ax_hipz, ax_terrain):
            ax.clear()
            ax.grid(alpha=0.5)

        t = np.array([r["time"] for r in rows])
        hip_x = np.array([r["hip_x"] for r in rows])
        hip_z = np.array([r["hip_z"] for r in rows])
        left_c = np.array([r["left_contact"] for r in rows]).astype(bool)
        right_c = np.array([r["right_contact"] for r in rows]).astype(bool)
        events = summary["contact_events"]
        ok = summary["success"]
        impulse_in_range = (
            scenario.impulse_force_n > 0 and scenario.impulse_t_s <= t[-1]
        )

        # subplot 1: 前进距离
        ax_hipx.plot(t, hip_x - hip_x[0], color=C_TRACE, lw=1.6, label="forward x")
        if impulse_in_range:
            ax_hipx.axvspan(
                scenario.impulse_t_s,
                scenario.impulse_t_s + scenario.impulse_duration_s,
                color=C_IMPULSE,
                alpha=0.18,
                label=f"脉冲 {scenario.impulse_force_n:.0f}N",
            )
        for ev in events:
            c = C_LEFT if ev["foot"] == "left" else C_RIGHT
            ax_hipx.axvline(ev["time"], color=c, alpha=0.20, lw=0.8)
        ax_hipx.set_ylabel("前进距离 (m)")
        ax_hipx.legend(loc="upper left", fontsize=8, framealpha=0.85)
        title_color = "#1f7a3a" if ok else "#a02020"
        ax_hipx.set_title(
            f"地形 {scenario.terrain_amplitude_m:.3f}m · 脉冲 {scenario.impulse_force_n:.0f}N@{scenario.impulse_t_s:.1f}s · "
            f"σ={scenario.contact_phase_noise_s:.3f}s · seed={scenario.terrain_seed}  →  "
            f"{'SUCCESS' if ok else 'FAIL: ' + summary['failure']}",
            color=title_color,
        )

        # subplot 2: hip z + 触地带
        z_lo, z_hi = float(hip_z.min()) - 0.02, float(hip_z.max()) + 0.02
        ax_hipz.plot(t, hip_z, color=C_HIP, lw=1.4, label="hip z")
        ax_hipz.fill_between(
            t,
            z_lo,
            z_hi,
            where=left_c,
            color=C_LEFT,
            alpha=0.13,
            step="post",
            label="左脚触地",
        )
        ax_hipz.fill_between(
            t,
            z_lo,
            z_hi,
            where=right_c,
            color=C_RIGHT,
            alpha=0.13,
            step="post",
            label="右脚触地",
        )
        if impulse_in_range:
            ax_hipz.axvspan(
                scenario.impulse_t_s,
                scenario.impulse_t_s + scenario.impulse_duration_s,
                color=C_IMPULSE,
                alpha=0.18,
            )
        ax_hipz.set_ylim(z_lo, z_hi)
        ax_hipz.set_xlabel("时间 (s)")
        ax_hipz.set_ylabel("hip 高度 (m)")
        ax_hipz.legend(loc="lower left", fontsize=8, ncol=3, framealpha=0.85)

        # subplot 3: 地形 + hip 轨迹（矢状面）
        xs, zs = terrain_profile(scenario.terrain_amplitude_m, scenario.terrain_seed)
        x_lo = min(float(hip_x.min()), 0.0) - 0.5
        x_hi = max(float(hip_x.max()) + 0.8, 4.0)
        mask = (xs >= x_lo) & (xs <= x_hi)
        xs_v, zs_v = xs[mask], zs[mask]
        z_floor = float(zs_v.min()) - 0.05 if zs_v.size else -0.05
        ax_terrain.fill_between(xs_v, z_floor, zs_v, color=C_TERRAIN_FILL, alpha=0.7)
        ax_terrain.plot(xs_v, zs_v, color=C_TERRAIN, lw=1.2, label="地形剖面")
        ax_terrain.plot(hip_x, hip_z, color=C_TRACE, lw=1.6, label="hip 轨迹", zorder=3)
        ax_terrain.plot(
            hip_x[0], hip_z[0], "o", color="#1f7a3a", ms=8, label="起点", zorder=4
        )
        end_marker = "^" if ok else "X"
        end_color = "#1f7a3a" if ok else "#c0392b"
        ax_terrain.plot(
            hip_x[-1],
            hip_z[-1],
            end_marker,
            color=end_color,
            ms=10,
            label="终点 " + ("(成功)" if ok else "(摔倒)"),
            zorder=4,
        )
        if impulse_in_range:
            imp_idx = int(np.searchsorted(t, scenario.impulse_t_s))
            imp_idx = min(imp_idx, len(hip_x) - 1)
            ax_terrain.plot(
                hip_x[imp_idx],
                hip_z[imp_idx],
                "*",
                color=C_IMPULSE,
                ms=14,
                label="脉冲位置",
                zorder=4,
            )
        ax_terrain.set_xlabel("x (m)")
        ax_terrain.set_ylabel("z (m)")
        ax_terrain.set_xlim(x_lo, x_hi)
        ax_terrain.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.85)
        ax_terrain.set_aspect("equal", adjustable="datalim")

        # 状态徽章
        n_left = sum(1 for e in events if e["foot"] == "left")
        n_right = sum(1 for e in events if e["foot"] == "right")
        if ok:
            badge_box.set_facecolor("#cdebd2")
            badge_text.set_text("✓  SUCCESS")
            badge_text.set_color("#1f7a3a")
            failure_text.set_text("到达成功标准")
        else:
            badge_box.set_facecolor("#f5d7d4")
            badge_text.set_text("✗  FAIL")
            badge_text.set_color("#a02020")
            failure_text.set_text(f"模式: {summary['failure']}")

        metrics = (
            f"仿真时长     {summary['simulated_time']:>6.2f} s\n"
            f"前进距离     {summary['forward_distance']:>6.2f} m\n"
            f"交替触地     {summary['alternating_touchdowns']:>6d} 次\n"
            f"  左 {n_left:>2}   右 {n_right:>2}\n"
            f"\n"
            f"主动能量     {summary['active_input_energy_j']:>6.2f} J\n"
            f"净作动功     {summary['net_actuator_work_j']:>6.2f} J\n"
            f"脉冲生效步   {summary['impulse_active_steps']:>6d}\n"
            f"\n"
            f"研究口径\n"
            f"  准被动鲁棒性 / 敏感性\n"
            f"  (非纯被动)"
        )
        metric_lines.set_text(metrics)
        fig.canvas.draw_idle()

    # ---- 回调 ----
    def set_status(text, color="#444444"):
        badge_box.set_facecolor("#dddddd")
        badge_text.set_text(text)
        badge_text.set_color(color)
        failure_text.set_text("")
        fig.canvas.draw_idle()
        fig.canvas.flush_events()

    def on_run(_e=None):
        set_status("⏳  仿真中…")
        rows, summary, scenario = simulate(
            float(sliders["amp"].val),
            float(sliders["imp"].val),
            float(sliders["imp_t"].val),
            float(sliders["sigma"].val),
            int(sliders["seed"].val),
        )
        last["rows"], last["summary"], last["scenario"] = rows, summary, scenario
        render(rows, summary, scenario)

    def on_view_3d(_e=None):
        if last["rows"] is None:
            set_status("先点 Run 跑一次仿真")
            return
        p = viewer_proc["p"]
        if p is not None and p.poll() is None:
            return
        viewer_proc["p"] = subprocess.Popen(
            [sys.executable, str(VIEW_SCRIPT), "--prefix", VIEW_PREFIX],
            cwd=str(ROOT),
        )

    def on_reset(_e=None):
        for s in sliders.values():
            s.reset()

    def apply_preset(name):
        p = PRESETS[name]
        sliders["amp"].set_val(p["amp"])
        sliders["imp"].set_val(p["imp"])
        sliders["imp_t"].set_val(p["imp_t"])
        sliders["sigma"].set_val(p["sigma"])
        sliders["seed"].set_val(p["seed"])
        on_run()

    btn_run.on_clicked(on_run)
    btn_view.on_clicked(on_view_3d)
    btn_reset.on_clicked(on_reset)
    btn_p1.on_clicked(lambda _e: apply_preset("Flat"))
    btn_p2.on_clicked(lambda _e: apply_preset("Terrain"))
    btn_p3.on_clicked(lambda _e: apply_preset("Hard"))

    def on_key(event):
        k = (event.key or "").lower()
        if k == "r":
            on_run()
        elif k == "v":
            on_view_3d()
        elif k == "0":
            on_reset()
        elif k == "1":
            apply_preset("Flat")
        elif k == "2":
            apply_preset("Terrain")
        elif k == "3":
            apply_preset("Hard")
        elif k == "escape":
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    on_run()
    plt.show()


if __name__ == "__main__":
    main()

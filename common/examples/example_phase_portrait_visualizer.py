"""示例：PhasePortraitVisualizer 使用演示。

展示相空间轨迹可视化的各种功能：
1. 基本 2D 相位图
2. 时间颜色编码
3. 矢量场和零斜线叠加
4. 多轨迹对比
5. 3D 相空间可视化
6. 多视图投影
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.phase_portrait_visualizer import (
    PhasePortraitVisualizer,
    StateVariable,
    quick_phase_portrait,
)
from common.plot_styles import set_style

# 设置绘图风格
set_style()

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def example_1_basic_phase_portrait():
    """示例 1: 基本 2D 相位图 - 简谐振子。"""
    print("\n=== Example 1: Basic Phase Portrait ===")

    # 简谐振子: d²x/dt² + ω²x = 0
    omega = 2.0
    t = np.linspace(0, 4 * np.pi, 500)
    x = np.cos(omega * t)
    x_dot = -omega * np.sin(omega * t)

    # 快速绘图
    fig, ax = quick_phase_portrait(
        x, x_dot,
        xlabel=r"Position $x$ [m]",
        ylabel=r"Velocity $\dot{x}$ [m/s]",
        title="Simple Harmonic Oscillator Phase Portrait",
        output_path=OUTPUT_DIR / "example_1_basic.png",
    )

    print(f"Saved: {OUTPUT_DIR / 'example_1_basic.png'}")


def example_2_time_encoded_trajectory():
    """示例 2: 时间颜色编码 - 阻尼振子。"""
    print("\n=== Example 2: Time-Encoded Trajectory ===")

    # 阻尼振子: d²x/dt² + 2ζω dx/dt + ω²x = 0
    omega = 2.0
    zeta = 0.1  # 欠阻尼
    omega_d = omega * np.sqrt(1 - zeta**2)

    t = np.linspace(0, 6 * np.pi, 800)
    x = np.exp(-zeta * omega * t) * np.cos(omega_d * t)
    x_dot = -zeta * omega * x - omega_d * np.exp(-zeta * omega * t) * np.sin(omega_d * t)

    vis = PhasePortraitVisualizer()
    vis.add_trajectory(x, x_dot, time=t, label="Damped oscillator")
    vis.add_annotation(0, "Initial", color="green", marker="*", size=100)
    vis.add_annotation(-1, "Final (damped)", color="red", marker="s", size=80)

    fig, ax = plt.figure(figsize=(10, 6)), plt.gca()
    vis.plot(
        ax=ax,
        xlabel=r"Position $x$ [m]",
        ylabel=r"Velocity $\dot{x}$ [m/s]",
        title="Damped Harmonic Oscillator with Time Encoding",
        show_start_end=False,  # 使用自定义标注
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "example_2_time_encoded.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_2_time_encoded.png'}")


def example_3_vector_field_and_nullclines():
    """示例 3: 矢量场和零斜线 - Van der Pol 振子。"""
    print("\n=== Example 3: Vector Field and Nullclines ===")

    # Van der Pol 振子: d²x/dt² - μ(1-x²)dx/dt + x = 0
    mu = 1.5

    def van_der_pol(state, t):
        x, v = state
        dx_dt = v
        dv_dt = mu * (1 - x**2) * v - x
        return [dx_dt, dv_dt]

    # 数值积分
    from scipy.integrate import odeint

    t = np.linspace(0, 30, 3000)
    state0 = [0.1, 0.1]
    sol = odeint(van_der_pol, state0, t)
    x, v = sol[:, 0], sol[:, 1]

    # 创建可视化器
    vis = PhasePortraitVisualizer()

    # 添加轨迹
    vis.add_trajectory(x, v, label="Limit cycle")

    # 添加矢量场
    vis.add_vector_field(
        dx_dt=lambda X, Y: Y,
        dy_dt=lambda X, Y: mu * (1 - X**2) * Y - X,
        x_range=(-3, 3),
        y_range=(-3, 3),
        density=15,
        color="gray",
        alpha=0.3,
    )

    # 添加零斜线
    # dx/dt = 0 => v = 0
    x_null_1 = np.linspace(-3, 3, 100)
    y_null_1 = np.zeros_like(x_null_1)

    # dv/dt = 0 => v = x / (μ(1-x²))
    x_null_2 = np.linspace(-2.5, 2.5, 100)
    y_null_2 = x_null_2 / (mu * (1 - x_null_2**2) + 1e-6)

    vis.add_nullcline(x_null_1, y_null_1, label=r"$\dot{x}=0$", color="blue")
    vis.add_nullcline(x_null_2, y_null_2, label=r"$\dot{v}=0$", color="red")

    fig, ax = plt.figure(figsize=(10, 8)), plt.gca()
    vis.plot(
        ax=ax,
        xlabel=r"Position $x$",
        ylabel=r"Velocity $v$",
        title=f"Van der Pol Oscillator (μ={mu}) with Phase Portrait Analysis",
        xlim=(-3, 3),
        ylim=(-3, 3),
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "example_3_vector_field.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_3_vector_field.png'}")


def example_4_multiple_trajectories():
    """示例 4: 多轨迹对比 - 不同初始条件。"""
    print("\n=== Example 4: Multiple Trajectories Comparison ===")

    # Duffing 振子: d²x/dt² + δ dx/dt + αx + βx³ = 0
    delta, alpha, beta = 0.1, -1.0, 1.0

    def duffing(state, t):
        x, v = state
        dx_dt = v
        dv_dt = -delta * v - alpha * x - beta * x**3
        return [dx_dt, dv_dt]

    from scipy.integrate import odeint

    vis = PhasePortraitVisualizer()

    # 多个初始条件
    initial_conditions = [
        ([0.5, 0.0], "IC1: x=0.5"),
        ([1.0, 0.0], "IC2: x=1.0"),
        ([1.5, 0.0], "IC3: x=1.5"),
        ([0.1, 1.0], "IC4: x=0.1, v=1.0"),
    ]

    colors = ["blue", "green", "orange", "purple"]

    t = np.linspace(0, 50, 5000)

    for (ic, label), color in zip(initial_conditions, colors):
        sol = odeint(duffing, ic, t)
        x, v = sol[:, 0], sol[:, 1]
        vis.add_trajectory(x, v, label=label, color=color, linewidth=1.2, alpha=0.7)

    fig, ax = plt.figure(figsize=(10, 8)), plt.gca()
    vis.plot(
        ax=ax,
        xlabel=r"Position $x$",
        ylabel=r"Velocity $v$",
        title="Duffing Oscillator: Multiple Initial Conditions",
        show_start_end=False,  # 太多起点终点会显得杂乱
        xlim=(-2, 2),
        ylim=(-2, 2),
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "example_4_multiple_trajectories.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_4_multiple_trajectories.png'}")


def example_5_3d_phase_space():
    """示例 5: 3D 相空间 - Lorenz 吸引子。"""
    print("\n=== Example 5: 3D Phase Space - Lorenz Attractor ===")

    # Lorenz 系统
    sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0

    def lorenz(state, t):
        x, y, z = state
        dx_dt = sigma * (y - x)
        dy_dt = x * (rho - z) - y
        dz_dt = x * y - beta * z
        return [dx_dt, dy_dt, dz_dt]

    from scipy.integrate import odeint

    t = np.linspace(0, 40, 10000)
    state0 = [1.0, 1.0, 1.0]
    sol = odeint(lorenz, state0, t)
    x, y, z = sol[:, 0], sol[:, 1], sol[:, 2]

    vis = PhasePortraitVisualizer()
    vis.add_trajectory(x, y, z, time=t, label="Lorenz attractor", colormap="plasma")

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    vis.plot(
        ax=ax,
        xlabel=r"$x$",
        ylabel=r"$y$",
        zlabel=r"$z$",
        title=f"Lorenz Attractor (σ={sigma}, ρ={rho}, β={beta:.2f})",
        show_start_end=True,
    )

    # 调整视角
    ax.view_init(elev=20, azim=45)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "example_5_3d_lorenz.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_5_3d_lorenz.png'}")


def example_6_multi_view_projection():
    """示例 6: 3D 多视图投影。"""
    print("\n=== Example 6: 3D Multi-View Projection ===")

    # Rössler 吸引子
    a, b, c = 0.2, 0.2, 5.7

    def rossler(state, t):
        x, y, z = state
        dx_dt = -y - z
        dy_dt = x + a * y
        dz_dt = b + z * (x - c)
        return [dx_dt, dy_dt, dz_dt]

    from scipy.integrate import odeint

    t = np.linspace(0, 100, 10000)
    state0 = [1.0, 1.0, 1.0]
    sol = odeint(rossler, state0, t)
    x, y, z = sol[:, 0], sol[:, 1], sol[:, 2]

    # 定义状态变量
    x_var = StateVariable(name="x", symbol="x", unit="", latex=r"$x$")
    y_var = StateVariable(name="y", symbol="y", unit="", latex=r"$y$")
    z_var = StateVariable(name="z", symbol="z", unit="", latex=r"$z$")

    vis = PhasePortraitVisualizer()
    fig = vis.create_multi_view(
        x, y, z,
        x_var, y_var, z_var,
        title=f"Rössler Attractor Multi-View (a={a}, b={b}, c={c})",
        figsize=(14, 10),
    )

    fig.savefig(OUTPUT_DIR / "example_6_multiview.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_6_multiview.png'}")


def example_7_gait_phase_portrait():
    """示例 7: 步态相位图示例 - 仿真数据。"""
    print("\n=== Example 7: Gait Phase Portrait ===")

    # 模拟步态数据：腿部摆动
    t = np.linspace(0, 4, 400)  # 4 个步态周期

    # 髋关节角度和角速度（正弦模拟）
    hip_angle = 0.5 * np.sin(2 * np.pi * t) + 0.1 * np.sin(4 * np.pi * t)
    hip_velocity = np.gradient(hip_angle, t)

    # 膝关节角度和角速度
    knee_angle = 0.3 * np.sin(2 * np.pi * t + np.pi / 4) + 0.05 * np.sin(6 * np.pi * t)
    knee_velocity = np.gradient(knee_angle, t)

    # 脚跟触地时刻（每个周期一次）
    heel_strike_indices = [int(i * 400 / 4) for i in range(5)]

    vis = PhasePortraitVisualizer()

    # 髋关节相位图
    vis.add_trajectory(
        hip_angle, hip_velocity,
        time=t,
        label="Hip joint",
        colormap="viridis",
    )

    # 标注脚跟触地
    for idx in heel_strike_indices[:-1]:  # 排除最后一个
        vis.add_annotation(
            idx,
            f"HS {idx // 100}",
            color="red",
            marker="o",
            size=60,
        )

    fig, ax = plt.figure(figsize=(10, 7)), plt.gca()
    vis.plot(
        ax=ax,
        xlabel=r"Hip Angle $\theta_{hip}$ [rad]",
        ylabel=r"Hip Velocity $\dot{\theta}_{hip}$ [rad/s]",
        title="Hip Joint Phase Portrait with Heel Strike Events",
        show_start_end=False,
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "example_7_gait_phase.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {OUTPUT_DIR / 'example_7_gait_phase.png'}")


def main():
    """运行所有示例。"""
    print("=" * 60)
    print("PhasePortraitVisualizer Examples")
    print("=" * 60)

    example_1_basic_phase_portrait()
    example_2_time_encoded_trajectory()
    example_3_vector_field_and_nullclines()
    example_4_multiple_trajectories()
    example_5_3d_phase_space()
    example_6_multi_view_projection()
    example_7_gait_phase_portrait()

    print("\n" + "=" * 60)
    print(f"All examples completed! Outputs saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

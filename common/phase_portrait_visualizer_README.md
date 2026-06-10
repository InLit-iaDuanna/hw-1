# PhasePortraitVisualizer

相空间轨迹可视化工具，用于绘制动态系统的相位图、轨迹分析和状态空间探索。

## 功能特性

- ✅ **2D/3D 相轨迹绘制** - 支持平面和三维相空间可视化
- ✅ **时间颜色编码** - 使用颜色映射显示轨迹的时间演化
- ✅ **轨迹标注** - 灵活标注起点、终点、事件点等关键位置
- ✅ **矢量场叠加** - 在相平面上显示系统动力学矢量场
- ✅ **零斜线/等倾线** - 绘制 nullclines 和 isoclines 辅助分析
- ✅ **多轨迹对比** - 同时可视化多条轨迹（不同初始条件、参数等）
- ✅ **多视图投影** - 3D 轨迹的正交平面投影
- ✅ **自动轴标签** - 支持单位、LaTeX 符号的智能标签生成

## 快速开始

### 基本用法

```python
from common.phase_portrait_visualizer import quick_phase_portrait
import numpy as np

# 简谐振子
t = np.linspace(0, 4 * np.pi, 500)
x = np.cos(t)
x_dot = -np.sin(t)

fig, ax = quick_phase_portrait(
    x, x_dot,
    xlabel=r"Position $x$ [m]",
    ylabel=r"Velocity $\dot{x}$ [m/s]",
    title="Simple Harmonic Oscillator",
    output_path="phase_portrait.png"
)
```

### 高级用法 - 完整控制

```python
from common.phase_portrait_visualizer import PhasePortraitVisualizer
import numpy as np

# 创建可视化器
vis = PhasePortraitVisualizer()

# 添加主轨迹（带时间颜色编码）
vis.add_trajectory(
    x, y, 
    time=t, 
    label="Main trajectory",
    colormap="viridis"
)

# 添加标注点
vis.add_annotation(0, "Initial condition", color="green", marker="*", size=100)
vis.add_annotation(-1, "Final state", color="red", marker="s", size=80)
vis.add_annotation(250, "Event", color="yellow", marker="o", size=60)

# 添加矢量场
vis.add_vector_field(
    dx_dt=lambda x, y: y,
    dy_dt=lambda x, y: -x,
    x_range=(-2, 2),
    y_range=(-2, 2),
    density=15
)

# 添加零斜线
x_null = np.linspace(-2, 2, 100)
y_null = np.zeros_like(x_null)
vis.add_nullcline(x_null, y_null, label=r"$\dot{x}=0$", color="blue")

# 绘制
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 8))
vis.plot(
    ax=ax,
    xlabel=r"Position $x$",
    ylabel=r"Velocity $\dot{x}$",
    title="Phase Portrait with Analysis",
    xlim=(-2, 2),
    ylim=(-2, 2)
)
plt.savefig("advanced_phase_portrait.png", dpi=300, bbox_inches="tight")
```

## API 参考

### PhasePortraitVisualizer

主要可视化类。

#### 方法

##### `add_trajectory(x, y, z=None, label="", color=None, linewidth=1.5, alpha=0.8, linestyle="-", time=None, colormap="viridis")`

添加轨迹到可视化器。

**参数:**
- `x, y` (array): 状态空间坐标
- `z` (array, optional): 第三维坐标（3D 相空间）
- `label` (str): 轨迹标签
- `color` (str, optional): 线条颜色（None 则自动分配）
- `linewidth` (float): 线宽
- `alpha` (float): 透明度 [0, 1]
- `linestyle` (str): 线型 ('-', '--', '-.', ':')
- `time` (array, optional): 时间数组（用于颜色编码）
- `colormap` (str): 颜色映射名称

##### `add_annotation(index, label, color="red", marker="o", size=50, zorder=5, trajectory_index=0)`

添加轨迹标注点。

**参数:**
- `index` (int): 轨迹点索引（支持负数索引）
- `label` (str): 标注文本
- `color` (str): 标注颜色
- `marker` (str): 标记符号 ('o', '*', 's', '^', 'x', 等)
- `size` (int): 标记大小
- `zorder` (int): 绘制层级
- `trajectory_index` (int): 要标注的轨迹索引

##### `add_vector_field(dx_dt, dy_dt, x_range, y_range, density=20, color="gray", alpha=0.4, scale=None)`

添加矢量场（仅 2D）。

**参数:**
- `dx_dt` (callable): x 方向导数函数 `f(X, Y) -> dX/dt`
- `dy_dt` (callable): y 方向导数函数 `f(X, Y) -> dY/dt`
- `x_range` (tuple): x 坐标范围 `(min, max)`
- `y_range` (tuple): y 坐标范围 `(min, max)`
- `density` (int): 网格密度
- `color` (str): 矢量颜色
- `alpha` (float): 透明度
- `scale` (float, optional): 矢量缩放因子

##### `add_nullcline(x, y, label="", color="black", linestyle="--", linewidth=1.0, alpha=0.6)`

添加零斜线或等倾线（仅 2D）。

**参数:**
- `x, y` (array): 曲线坐标
- `label` (str): 曲线标签
- `color` (str): 线条颜色
- `linestyle` (str): 线型
- `linewidth` (float): 线宽
- `alpha` (float): 透明度

##### `plot(ax=None, xlabel="State x", ylabel="State y", zlabel="State z", title="", show_legend=True, show_grid=True, show_start_end=True, equal_aspect=False, xlim=None, ylim=None, zlim=None)`

绘制相空间轨迹。

**参数:**
- `ax` (Axes, optional): matplotlib Axes 对象（None 则创建新图）
- `xlabel, ylabel, zlabel` (str): 坐标轴标签
- `title` (str): 图表标题
- `show_legend` (bool): 是否显示图例
- `show_grid` (bool): 是否显示网格
- `show_start_end` (bool): 是否自动标注起点和终点
- `equal_aspect` (bool): 是否使用等比例坐标轴
- `xlim, ylim, zlim` (tuple, optional): 坐标轴范围

**返回:**
- `Axes`: matplotlib Axes 对象

##### `create_multi_view(x, y, z, x_var, y_var, z_var, title="3D State Space Multi-View", figsize=(14, 10))`

创建 3D 状态空间的多视图投影。

**参数:**
- `x, y, z` (array): 三维状态坐标
- `x_var, y_var, z_var` (StateVariable): 状态变量配置
- `title` (str): 总标题
- `figsize` (tuple): 图形尺寸

**返回:**
- `Figure`: matplotlib Figure 对象

##### `clear()`

清空所有轨迹和标注。

### StateVariable

状态变量配置类，用于生成标准化的轴标签。

```python
from common.phase_portrait_visualizer import StateVariable

# 创建状态变量
hip_angle = StateVariable(
    name="hip_angle",
    symbol="θ_hip",
    unit="rad",
    latex=r"$\theta_{hip}$"
)

# 生成标签
label = hip_angle.get_label()  # "$\theta_{hip}$ [rad]"
label_no_unit = hip_angle.get_label(include_unit=False)  # "$\theta_{hip}$"
```

### TrajectoryAnnotation

轨迹标注配置类（通常不需要直接使用，由 `add_annotation` 创建）。

## 使用示例

### 示例 1: 阻尼振子

```python
from common.phase_portrait_visualizer import PhasePortraitVisualizer
from scipy.integrate import odeint
import numpy as np

# 阻尼振子: d²x/dt² + 2ζω dx/dt + ω²x = 0
omega, zeta = 2.0, 0.1

def damped_oscillator(state, t):
    x, v = state
    return [v, -2 * zeta * omega * v - omega**2 * x]

t = np.linspace(0, 10, 1000)
sol = odeint(damped_oscillator, [1.0, 0.0], t)

vis = PhasePortraitVisualizer()
vis.add_trajectory(sol[:, 0], sol[:, 1], time=t, colormap="plasma")
vis.plot(
    xlabel=r"Position $x$ [m]",
    ylabel=r"Velocity $\dot{x}$ [m/s]",
    title=f"Damped Oscillator (ζ={zeta}, ω={omega})"
)
```

### 示例 2: Van der Pol 振子与矢量场

```python
mu = 1.5

def van_der_pol(state, t):
    x, v = state
    return [v, mu * (1 - x**2) * v - x]

t = np.linspace(0, 30, 3000)
sol = odeint(van_der_pol, [0.1, 0.1], t)

vis = PhasePortraitVisualizer()
vis.add_trajectory(sol[:, 0], sol[:, 1], label="Limit cycle")

# 添加矢量场
vis.add_vector_field(
    dx_dt=lambda X, Y: Y,
    dy_dt=lambda X, Y: mu * (1 - X**2) * Y - X,
    x_range=(-3, 3),
    y_range=(-3, 3),
    density=15
)

# 添加零斜线
x_null = np.linspace(-3, 3, 100)
vis.add_nullcline(x_null, np.zeros_like(x_null), label=r"$\dot{x}=0$", color="blue")

vis.plot(
    xlabel=r"$x$",
    ylabel=r"$v$",
    title=f"Van der Pol Oscillator (μ={mu})",
    xlim=(-3, 3),
    ylim=(-3, 3)
)
```

### 示例 3: 3D Lorenz 吸引子

```python
sigma, rho, beta = 10.0, 28.0, 8.0/3.0

def lorenz(state, t):
    x, y, z = state
    return [
        sigma * (y - x),
        x * (rho - z) - y,
        x * y - beta * z
    ]

t = np.linspace(0, 40, 10000)
sol = odeint(lorenz, [1.0, 1.0, 1.0], t)

vis = PhasePortraitVisualizer()
vis.add_trajectory(sol[:, 0], sol[:, 1], sol[:, 2], time=t, colormap="plasma")

fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
vis.plot(
    ax=ax,
    xlabel="x", ylabel="y", zlabel="z",
    title=f"Lorenz Attractor (σ={sigma}, ρ={rho}, β={beta:.2f})"
)
ax.view_init(elev=20, azim=45)
plt.show()
```

### 示例 4: 步态相位图

```python
from common.phase_portrait_visualizer import PhasePortraitVisualizer
import numpy as np

# 模拟步态数据
t = np.linspace(0, 4, 400)
hip_angle = 0.5 * np.sin(2 * np.pi * t)
hip_velocity = np.gradient(hip_angle, t)

# 脚跟触地时刻
heel_strikes = [0, 100, 200, 300, 400]

vis = PhasePortraitVisualizer()
vis.add_trajectory(hip_angle, hip_velocity, time=t, colormap="viridis")

# 标注脚跟触地
for i, hs in enumerate(heel_strikes[:-1]):
    vis.add_annotation(hs, f"HS{i}", color="red", marker="o", size=60)

vis.plot(
    xlabel=r"Hip Angle $\theta_{hip}$ [rad]",
    ylabel=r"Hip Velocity $\dot{\theta}_{hip}$ [rad/s]",
    title="Gait Phase Portrait with Heel Strike Events",
    show_start_end=False
)
```

### 示例 5: 多初始条件对比

```python
# Duffing 振子
delta, alpha, beta = 0.1, -1.0, 1.0

def duffing(state, t):
    x, v = state
    return [v, -delta * v - alpha * x - beta * x**3]

vis = PhasePortraitVisualizer()

initial_conditions = [
    ([0.5, 0.0], "IC1"),
    ([1.0, 0.0], "IC2"),
    ([1.5, 0.0], "IC3"),
]

colors = ["blue", "green", "orange"]
t = np.linspace(0, 50, 5000)

for (ic, label), color in zip(initial_conditions, colors):
    sol = odeint(duffing, ic, t)
    vis.add_trajectory(sol[:, 0], sol[:, 1], label=label, color=color)

vis.plot(
    xlabel=r"$x$", ylabel=r"$v$",
    title="Duffing Oscillator: Multiple Initial Conditions",
    show_start_end=False
)
```

## 与项目其他模块的集成

### 与 PoincareAnalyzer 结合

```python
from common.poincare_analyzer import PoincareAnalyzer
from common.phase_portrait_visualizer import PhasePortraitVisualizer

# 运行仿真得到 rows
# rows = simulate(...)

# Poincaré 分析
poincare = PoincareAnalyzer(rows, state_keys=("q1", "q1_dot"))
section_pts = poincare.detect_section()

# 提取完整轨迹
q1 = [r["q1"] for r in rows]
q1_dot = [r["q1_dot"] for r in rows]

# 相位图可视化
vis = PhasePortraitVisualizer()
vis.add_trajectory(q1, q1_dot, label="Trajectory", color="blue", alpha=0.5)

# 叠加 Poincaré 截面点
if len(section_pts) > 0:
    vis.add_trajectory(
        section_pts[:, 0], 
        section_pts[:, 1],
        label="Poincaré section",
        color="red",
        marker="o",
        linestyle="none"
    )

vis.plot(
    xlabel=r"$\theta$ [rad]",
    ylabel=r"$\dot{\theta}$ [rad/s]",
    title="Phase Portrait with Poincaré Section"
)
```

### 与 SimulationRunner 结合

```python
from common.simulation_runner import SimulationRunner
from common.phase_portrait_visualizer import PhasePortraitVisualizer

runner = SimulationRunner(model, data)
result = runner.run(duration=10.0)

if result.success:
    rows = result.data
    
    # 提取状态
    hip_q = [r["hip_angle"] for r in rows]
    hip_v = [r["hip_velocity"] for r in rows]
    t = [r["time"] for r in rows]
    
    # 可视化
    vis = PhasePortraitVisualizer()
    vis.add_trajectory(hip_q, hip_v, time=t, colormap="viridis")
    vis.plot(
        xlabel=r"Hip Angle [rad]",
        ylabel=r"Hip Velocity [rad/s]",
        title="Simulation Phase Portrait"
    )
```

## 完整示例脚本

完整的使用示例见 `common/examples/example_phase_portrait_visualizer.py`，包含：
1. 基本 2D 相位图
2. 时间颜色编码
3. 矢量场和零斜线
4. 多轨迹对比
5. 3D 相空间（Lorenz 吸引子）
6. 多视图投影（Rössler 吸引子）
7. 步态相位图

运行示例：
```bash
python common/examples/example_phase_portrait_visualizer.py
```

## 测试

运行单元测试：
```bash
pytest tests/unit/test_phase_portrait_visualizer.py -v
```

## 注意事项

1. **3D 可视化** - 3D 轨迹需要创建 3D axes：
   ```python
   fig = plt.figure()
   ax = fig.add_subplot(111, projection='3d')
   vis.plot(ax=ax, ...)
   ```

2. **时间颜色编码** - 当使用 `time` 参数时，将自动使用 LineCollection 绘制渐变色轨迹。

3. **矢量场密度** - 密度过高会使图形杂乱，建议 10-20。

4. **内存管理** - 处理长轨迹时，考虑使用 `vis.clear()` 释放内存。

5. **保存格式** - 建议使用 SVG 或 PDF 格式用于论文发表：
   ```python
   plt.savefig("figure.svg", format="svg", bbox_inches="tight")
   ```

## 相关模块

- `common.poincare_analyzer` - Poincaré 截面分析
- `common.plot_styles` - 统一绘图风格
- `common.energy_metrics` - 能量指标计算
- `paper_figures.generators.fig_phase_portrait` - 论文图表生成

## 版权

hw-1 项目 © 2024-2026

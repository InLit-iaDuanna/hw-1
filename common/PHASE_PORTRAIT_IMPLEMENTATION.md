# PhasePortraitVisualizer Implementation Summary

## 实现概述

为 hw-1 项目实现了完整的相空间轨迹可视化工具 `PhasePortraitVisualizer`，用于动态系统的相位图绘制、轨迹分析和状态空间探索。

## 创建的文件

### 1. 核心实现
**文件**: `D:\Dunna\Documents\hw-1\common\phase_portrait_visualizer.py`

包含以下核心组件：
- `PhasePortraitVisualizer` 类 - 主要可视化器
- `StateVariable` 数据类 - 状态变量配置（名称、符号、单位、LaTeX）
- `TrajectoryAnnotation` 数据类 - 轨迹标注配置
- `quick_phase_portrait()` 函数 - 快速绘图便捷函数

### 2. 示例代码
**文件**: `D:\Dunna\Documents\hw-1\common\examples\example_phase_portrait_visualizer.py`

包含 7 个完整示例：
1. 基本 2D 相位图（简谐振子）
2. 时间颜色编码（阻尼振子）
3. 矢量场和零斜线（Van der Pol 振子）
4. 多轨迹对比（Duffing 振子，不同初始条件）
5. 3D 相空间（Lorenz 吸引子）
6. 多视图投影（Rössler 吸引子）
7. 步态相位图示例

### 3. 单元测试
**文件**: `D:\Dunna\Documents\hw-1\tests\unit\test_phase_portrait_visualizer.py`

20 个单元测试覆盖：
- 初始化和基本功能
- 2D/3D 轨迹添加
- 时间编码轨迹
- 多轨迹支持
- 标注功能
- 矢量场和零斜线
- 绘图功能（2D、3D、多视图）
- StateVariable 和 TrajectoryAnnotation 类
- 快速绘图函数

**测试结果**: ✅ 20/20 测试通过

### 4. 文档
**文件**: `D:\Dunna\Documents\hw-1\common\phase_portrait_visualizer_README.md`

完整文档包含：
- 功能特性列表
- 快速开始指南
- 完整 API 参考
- 5 个实用示例
- 与项目其他模块的集成指南
- 注意事项和最佳实践

### 5. 模块导出
**修改文件**: `D:\Dunna\Documents\hw-1\common\__init__.py`

添加导出：
```python
from .phase_portrait_visualizer import (
    PhasePortraitVisualizer,
    StateVariable,
    TrajectoryAnnotation,
    quick_phase_portrait,
)
```

## 核心功能

### 1. 轨迹绘制
- ✅ 2D 相空间轨迹
- ✅ 3D 相空间轨迹
- ✅ 时间颜色编码（渐变色显示时间演化）
- ✅ 多轨迹对比（同时显示多条轨迹）
- ✅ 自定义颜色、线宽、透明度、线型

### 2. 标注功能
- ✅ 灵活的轨迹点标注（起点、终点、事件点）
- ✅ 支持正负索引
- ✅ 自定义标记符号、颜色、大小
- ✅ 自动起点/终点标注

### 3. 动力学分析工具
- ✅ 矢量场可视化（quiver plot）
- ✅ 零斜线（nullclines）绘制
- ✅ 等倾线（isoclines）支持
- ✅ 可自定义密度、颜色、透明度

### 4. 高级功能
- ✅ 3D 多视图投影（3D + XY + XZ）
- ✅ 等比例坐标轴选项
- ✅ 坐标范围控制
- ✅ 自动轴标签生成（StateVariable）
- ✅ LaTeX 符号和单位支持

## API 设计亮点

### 1. 链式 API 设计
```python
vis = PhasePortraitVisualizer()
vis.add_trajectory(x, y, label="Traj")
vis.add_annotation(0, "Start", color="green")
vis.add_vector_field(dx_dt, dy_dt, ...)
vis.plot(xlabel="x", ylabel="y")
```

### 2. 灵活的轴标签管理
```python
hip = StateVariable(
    name="hip_angle",
    symbol="θ_hip", 
    unit="rad",
    latex=r"$\theta_{hip}$"
)
label = hip.get_label()  # "$\theta_{hip}$ [rad]"
```

### 3. 快速绘图便捷函数
```python
fig, ax = quick_phase_portrait(
    x, y,
    xlabel="Position", 
    ylabel="Velocity",
    output_path="phase.png"
)
```

## 与项目集成

### 1. 与 PoincareAnalyzer 结合
```python
poincare = PoincareAnalyzer(rows, state_keys=("q1", "q1_dot"))
section_pts = poincare.detect_section()

vis = PhasePortraitVisualizer()
vis.add_trajectory(q1, q1_dot, label="Trajectory")
# 叠加 Poincaré 截面点
vis.add_trajectory(section_pts[:, 0], section_pts[:, 1], ...)
```

### 2. 与 SimulationRunner 结合
```python
result = runner.run(duration=10.0)
if result.success:
    vis = PhasePortraitVisualizer()
    vis.add_trajectory(hip_q, hip_v, time=t)
    vis.plot(...)
```

### 3. 使用统一绘图风格
```python
from common.plot_styles import set_style, PALETTE

set_style()  # 设置全局风格
vis.add_trajectory(x, y, color=PALETTE["left"])
```

## 技术实现细节

### 1. 时间颜色编码
使用 `LineCollection` 实现渐变色轨迹：
```python
from matplotlib.collections import LineCollection
points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)
lc = LineCollection(segments, cmap=colormap, ...)
lc.set_array(time)
```

### 2. 3D 可视化
支持 `mpl_toolkits.mplot3d` 的 3D 轨迹和多视图投影：
```python
from mpl_toolkits.mplot3d.art3d import Line3DCollection
```

### 3. 矢量场绘制
使用 `meshgrid` + `quiver` 实现：
```python
X, Y = np.meshgrid(x_grid, y_grid)
U = dx_dt(X, Y)
V = dy_dt(X, Y)
ax.quiver(X, Y, U, V, ...)
```

## 使用场景

### 1. 被动步态研究
- 髋关节/膝关节相位图
- 步态周期可视化
- 脚跟触地事件标注
- 极限环分析

### 2. 控制系统分析
- 状态轨迹演化
- 吸引子可视化
- 稳定性分析
- 矢量场和零斜线研究

### 3. 论文图表生成
- 高质量相位图（SVG/PDF 输出）
- 多轨迹对比图
- 3D 相空间可视化
- 多视图投影

### 4. 调试和探索
- 快速可视化仿真结果
- 多参数/初始条件对比
- 异常行为诊断
- 交互式探索

## 示例输出

运行示例脚本将生成以下图表（保存在 `common/examples/output/`）：
1. `example_1_basic.png` - 简谐振子基本相位图
2. `example_2_time_encoded.png` - 阻尼振子时间颜色编码
3. `example_3_vector_field.png` - Van der Pol 振子 + 矢量场 + 零斜线
4. `example_4_multiple_trajectories.png` - Duffing 振子多轨迹对比
5. `example_5_3d_lorenz.png` - Lorenz 吸引子 3D 可视化
6. `example_6_multiview.png` - Rössler 吸引子多视图投影
7. `example_7_gait_phase.png` - 步态相位图

## 扩展性

### 易于扩展的功能点
1. **新的标注类型** - 通过继承 `TrajectoryAnnotation`
2. **自定义颜色映射** - 支持任意 matplotlib colormap
3. **新的分析工具** - 添加方法到 `PhasePortraitVisualizer`
4. **导出格式** - 支持所有 matplotlib 输出格式

### 未来可能的增强
- 交互式相位图（使用 plotly）
- 动画轨迹（使用 matplotlib.animation）
- 自动吸引子检测
- 分岔图生成
- 李雅普诺夫指数可视化

## 性能考虑

- 长轨迹（>10000 点）使用时间颜色编码可能较慢
- 3D 轨迹渲染比 2D 更耗资源
- 矢量场密度建议保持在 10-20
- 使用 `vis.clear()` 释放内存

## 依赖关系

必需：
- `numpy` - 数组操作
- `matplotlib` - 绘图后端
- `mpl_toolkits.mplot3d` - 3D 绘图

可选（用于示例）：
- `scipy` - 数值积分（`odeint`）

## 文件路径总结

```
D:\Dunna\Documents\hw-1\
├── common\
│   ├── phase_portrait_visualizer.py          # 核心实现 (681 行)
│   ├── phase_portrait_visualizer_README.md   # 完整文档
│   ├── __init__.py                            # 已更新导出
│   └── examples\
│       └── example_phase_portrait_visualizer.py  # 示例脚本 (7 个示例)
└── tests\
    └── unit\
        └── test_phase_portrait_visualizer.py  # 单元测试 (20 个测试)
```

## 验证

✅ **单元测试**: 20/20 测试通过
✅ **代码风格**: 遵循项目规范（docstrings、类型提示）
✅ **文档**: 完整的 API 参考和使用示例
✅ **集成**: 已添加到 `common.__init__.py`
✅ **示例**: 7 个实用示例覆盖主要功能

## 总结

成功实现了功能完整、文档齐全、测试覆盖的 `PhasePortraitVisualizer` 工具，提供：
- 灵活的 2D/3D 相空间轨迹绘制
- 丰富的标注和分析功能（矢量场、零斜线、多轨迹）
- 与项目现有模块（PoincareAnalyzer、SimulationRunner）无缝集成
- 面向科研论文的高质量图表输出
- 完善的文档和测试

该工具将显著提升 hw-1 项目的动力学分析和可视化能力。

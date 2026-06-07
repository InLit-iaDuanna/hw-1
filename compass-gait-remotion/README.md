# Compass Gait Remotion 动画讲解材料

本项目使用 [Remotion](https://www.remotion.dev/) 为 hw-1 步态研究项目生成高质量的动画讲解材料。

## 📦 项目结构

```
compass-gait-remotion/
├── src/
│   ├── compositions/
│   │   ├── FSMStateTransition.tsx      # V13.6 四相位状态机动画
│   │   ├── RollingFootAnimation.tsx    # V10 足踝滚动动画
│   │   ├── PhaseVisualization.tsx      # 步态相位可视化
│   │   └── GaitComparison.tsx          # V10 vs V13.6 对比
│   ├── Root.tsx                        # Remotion 根组件
│   └── index.ts                        # 入口文件
├── package.json
├── tsconfig.json
└── README.md
```

## 🎬 可用动画

### 1. FSMStateTransition — V13.6 四相位状态机

**时长**: 8秒 (240帧 @ 30fps)  
**分辨率**: 1920×1080

展示 V13.6 事件驱动 FSM 的四个相位及其切换逻辑：

- **stance_early** (支撑早期): Loading Response + Mid-Stance
- **stance_late** (支撑晚期): Terminal Stance + Pre-Swing
- **swing_thrust** (摆动推进): Initial Swing
- **swing_retract** (摆动回收): Mid Swing + Terminal Swing

**特点**:
- 动态高亮当前激活相位
- 显示相位切换条件（u ≥ 0.5 / 接触切换）
- 实时相位进度百分比
- 支撑相 vs 摆动相颜色区分

**渲染命令**:
```bash
npm start  # 启动 Remotion Studio 预览
npx remotion render FSMStateTransition out/fsm_state_transition.mp4
```

---

### 2. RollingFootAnimation — V10 足踝滚动仿生步态

**时长**: 10秒 (300帧 @ 30fps)  
**分辨率**: 1920×1080

展示 V10 版本的脚跟-足底-脚趾滚动接触过程：

- **脚跟接触** (Heel Strike): 0-30% 步态周期
- **足底滚动** (Foot Flat): 25-70% 步态周期
- **脚趾离地** (Toe Off): 65-100% 步态周期

**特点**:
- 足部三段式结构可视化（脚跟/足底/脚趾）
- 踝关节旋转角度动画
- 接触相位时间轴
- 被动踝关节特性标注

**渲染命令**:
```bash
npx remotion render RollingFootAnimation out/rolling_foot_animation.mp4
```

---

### 3. PhaseVisualization — 步态相位可视化

**时长**: 10秒 (300帧 @ 30fps)  
**分辨率**: 1920×1080

实时显示步态过程中的：

- **相位时间轴**: 五段相位连续切换
- **关节角度**: 髋/膝/踝三关节角度实时曲线
- **接触状态**: 左右脚接触地面指示器
- **时间进度**: 仿真时间计数器

**特点**:
- 三关节角度柱状图动画
- 接触状态脉冲式高亮
- 相位进度条实时追踪
- 数据驱动的动态可视化

**渲染命令**:
```bash
npx remotion render PhaseVisualization out/phase_visualization.mp4
```

---

### 4. GaitComparison — V10 vs V13.6 对比

**时长**: 12秒 (360帧 @ 30fps)  
**分辨率**: 1920×1080

横向对比两种控制方案：

| 指标 | V10 PD控制 | V13.6 FSM控制 |
|------|-----------|--------------|
| 前进距离 | 4.85 m | 4.86 m |
| 输入能量 | 15.2 J | 17.45 J |
| CoT | 0.065 | 0.072 |
| 切片C成功率 | 16.7% | 11.1% |

**特点**:
- 分屏对比布局
- 逐项指标动画展开
- 控制律特性文字说明
- 双色编码（蓝色V10 / 绿色V13.6）

**渲染命令**:
```bash
npx remotion render GaitComparison out/gait_comparison.mp4
```

## 🚀 快速开始

### 安装依赖

```bash
cd D:\Dunna\Documents\hw-1\compass-gait-remotion
npm install
```

### 启动 Remotion Studio

```bash
npm start
```

浏览器会自动打开 `http://localhost:3000`，可在浏览器中预览和调试所有动画。

### 渲染单个视频

```bash
npx remotion render <CompositionId> out/<output-file>.mp4
```

示例：
```bash
npx remotion render FSMStateTransition out/fsm_states.mp4
```

### 渲染所有视频

```bash
npx remotion render FSMStateTransition out/fsm_state_transition.mp4
npx remotion render RollingFootAnimation out/rolling_foot_animation.mp4
npx remotion render PhaseVisualization out/phase_visualization.mp4
npx remotion render GaitComparison out/gait_comparison.mp4
```

### 渲染为静态帧 (调试用)

```bash
npx remotion still FSMStateTransition out/fsm_frame.png --frame=120
```

## 🔧 自定义与扩展

### 修改动画参数

在 `src/Root.tsx` 中修改 Composition 的 `defaultProps`：

```tsx
<Composition
  id="FSMStateTransition"
  component={FSMStateTransition}
  durationInFrames={240}  // 修改时长
  fps={30}                // 修改帧率
  width={1920}            // 修改分辨率
  height={1080}
  defaultProps={{
    phases: ['stance_early', 'stance_late', 'swing_thrust', 'swing_retract'],
  }}
/>
```

### 添加新动画

1. 在 `src/compositions/` 创建新组件文件
2. 在 `src/Root.tsx` 中注册新 Composition
3. 运行 `npm start` 预览

示例：

```tsx
// src/compositions/NewAnimation.tsx
import React from 'react';
import {AbsoluteFill} from 'remotion';

export const NewAnimation: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* 你的动画内容 */}
    </AbsoluteFill>
  );
};
```

```tsx
// src/Root.tsx
import {NewAnimation} from './compositions/NewAnimation';

<Composition
  id="NewAnimation"
  component={NewAnimation}
  durationInFrames={300}
  fps={30}
  width={1920}
  height={1080}
/>
```

## 📊 数据集成

### 从 Python 仿真导出数据

当前动画使用模拟数据。要使用真实仿真数据：

1. **导出 CSV 数据**（Python 脚本已生成）:
   - V10: `../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv`
   - V13.6: `../v13_6_event_driven_fsm/out/v13_6_baseline_data.csv`

2. **在 Remotion 中加载 CSV**:

```tsx
// 示例：读取 CSV 并解析
import {staticFile, continueRender, delayRender} from 'remotion';
import {useEffect, useState} from 'react';

export const DataDrivenAnimation: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    fetch(staticFile('../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv'))
      .then((res) => res.text())
      .then((csv) => {
        const rows = csv.split('\n').map(row => row.split(','));
        setData(rows);
        continueRender(handle);
      });
  }, [handle]);

  // 使用 data 渲染动画
  return <AbsoluteFill>{/* ... */}</AbsoluteFill>;
};
```

### 自动化数据同步

创建 Python 脚本自动导出 Remotion 所需格式：

```python
# export_for_remotion.py
import pandas as pd
import json

def export_phase_data(csv_path, json_output):
    df = pd.read_csv(csv_path)
    
    # 提取关键帧数据
    keyframes = df[['time', 'hip_x', 'hip_z', 'left_hip', 'left_knee', 
                    'left_ankle', 'left_contact', 'right_contact']].to_dict('records')
    
    with open(json_output, 'w') as f:
        json.dump(keyframes, f, indent=2)

# 导出
export_phase_data(
    '../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv',
    'public/v10_data.json'
)
```

然后在 Remotion 中加载 JSON：

```tsx
import data from '../public/v10_data.json';
```

## 🎨 设计规范

### 颜色方案

- **背景**: `#0F172A` (深蓝灰)
- **主文字**: `#F1F5F9` (浅白)
- **次要文字**: `#94A3B8` (灰色)
- **强调色**: `#FBBF24` (金黄)
- **V10 相关**: `#3B82F6` (蓝色)
- **V13.6 相关**: `#10B981` (绿色)
- **支撑相**: `#3B82F6` / `#1D4ED8`
- **摆动相**: `#10B981` / `#059669`
- **接触标识**: `#EF4444` (红) / `#F59E0B` (橙) / `#10B981` (绿)

### 字体

- **标题**: Arial, 56-64px, bold
- **副标题**: Arial, 32-42px, normal
- **正文**: Arial, 20-24px, normal
- **代码/数据**: monospace, 20px

### 布局

- **边距**: 40-100px
- **间距**: 20-60px
- **动画时长**: 每个关键动作 30-60 帧 (1-2秒)

## 🛠️ 故障排查

### 问题：npm install 失败

```bash
# 清除缓存重试
npm cache clean --force
npm install
```

### 问题：渲染卡住不动

检查是否有 `delayRender()` 未配对 `continueRender()`：

```tsx
const [handle] = useState(() => delayRender());
// ... 加载数据后必须调用
continueRender(handle);
```

### 问题：白屏或组件未显示

1. 检查浏览器控制台错误
2. 确认组件返回了 `<AbsoluteFill>` 或 React 元素
3. 运行 `npx remotion still <CompositionId> out/debug.png` 检查静帧

### 问题：性能卡顿

- 减少复杂 SVG 或大图像
- 使用 `useMemo` 缓存计算
- 降低帧率或分辨率测试

## 📝 与主项目集成

### 在论文中引用

```latex
\begin{figure}
  \centering
  \includegraphics[width=0.8\textwidth]{hw-1/compass-gait-remotion/out/fsm_state_transition.mp4}
  \caption{V13.6 四相位 FSM 状态转换动画}
  \label{fig:fsm-animation}
\end{figure}
```

### 在演示文稿中使用

1. 导出为 MP4：`npx remotion render <Id> out/<name>.mp4`
2. 嵌入 PowerPoint / Keynote
3. 或导出 GIF：`npx remotion render <Id> out/<name>.gif`

### 自动化渲染流水线

```powershell
# render_all.ps1
cd D:\Dunna\Documents\hw-1\compass-gait-remotion

$compositions = @(
    "FSMStateTransition",
    "RollingFootAnimation",
    "PhaseVisualization",
    "GaitComparison"
)

foreach ($comp in $compositions) {
    Write-Host "Rendering $comp..."
    npx remotion render $comp "out/$comp.mp4"
}

Write-Host "All animations rendered!"
```

## 🔗 相关资源

- [Remotion 官方文档](https://www.remotion.dev/docs)
- [Remotion 示例库](https://www.remotion.dev/showcase)
- [React 文档](https://react.dev/)
- [主项目 README](../README.md)
- [V10 README](../v10_rolling_foot_biomimetic_gait/README.md)
- [V13.6 README](../v13_6_event_driven_fsm/README.md)

## 📄 License

本项目遵循主项目的 License。

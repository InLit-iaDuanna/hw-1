# 快速开始指南

## 🚀 5分钟上手

### 第一步：安装依赖

```bash
cd D:\Dunna\Documents\hw-1\compass-gait-remotion
npm install
```

安装时间：约 2-3 分钟（首次）

### 第二步：启动预览

```bash
npm start
```

浏览器会自动打开 `http://localhost:3000`，可以看到四个可用的动画。

### 第三步：渲染视频

#### 方法 1：使用自动化脚本（推荐）

```powershell
# 渲染所有动画（中等质量）
.\scripts\render_all.ps1

# 高质量渲染（用于最终输出）
.\scripts\render_all.ps1 -HighQuality

# 快速预览（低质量，渲染快）
.\scripts\render_all.ps1 -LowQuality

# 只渲染单个动画
.\scripts\render_all.ps1 -Only FSMStateTransition
```

#### 方法 2：手动渲染单个动画

```bash
# FSM 状态机动画
npx remotion render FSMStateTransition out/fsm_state_transition.mp4

# 足踝滚动动画
npx remotion render RollingFootAnimation out/rolling_foot_animation.mp4

# 相位可视化
npx remotion render PhaseVisualization out/phase_visualization.mp4

# 对比动画
npx remotion render GaitComparison out/gait_comparison.mp4
```

### 完成！

渲染完成的视频在 `out/` 目录下。

---

## 📊 使用真实仿真数据（可选）

当前动画使用模拟数据。如果想用真实仿真数据：

### 1. 导出数据

```powershell
cd D:\Dunna\Documents\hw-1\compass-gait-remotion

# 批量导出所有版本的数据
..\.venv-mujoco\Scripts\python.exe utils\batch_export.py

# 或单独导出某个版本
..\.venv-mujoco\Scripts\python.exe utils\export_for_remotion.py `
  --input ../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv `
  --output public/data/v10_data.json `
  --sample-rate 2
```

### 2. 修改组件加载数据

在 `src/compositions/*.tsx` 中使用导出的数据：

```tsx
import {staticFile, continueRender, delayRender} from 'remotion';
import {useEffect, useState} from 'react';

export const DataDrivenAnimation: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    fetch(staticFile('data/v10_data.json'))
      .then((res) => res.json())
      .then((json) => {
        setData(json);
        continueRender(handle);
      });
  }, [handle]);

  // 使用 data 渲染...
};
```

---

## 🎬 各动画说明

### 1. FSMStateTransition (8秒)

V13.6 四相位状态机可视化，展示：
- 四个相位的循环切换
- 切换条件（u ≥ 0.5 / 接触事件）
- 当前相位高亮和进度

**适用场景**：论文中解释 FSM 控制律

### 2. RollingFootAnimation (10秒)

V10 足踝滚动动画，展示：
- 脚跟-足底-脚趾三段式接触
- 踝关节旋转
- 接触相位时间轴

**适用场景**：演示仿生机械设计

### 3. PhaseVisualization (10秒)

步态相位可视化，展示：
- 实时相位切换
- 三关节角度变化
- 左右脚接触状态

**适用场景**：步态分析报告

### 4. GaitComparison (12秒)

V10 vs V13.6 对比，展示：
- 控制律特性对比
- 性能指标对比（距离/能量/CoT/成功率）
- 分屏动画展示

**适用场景**：方案对比汇报

---

## ⚙️ 自定义修改

### 修改动画时长

编辑 `src/Root.tsx`：

```tsx
<Composition
  id="FSMStateTransition"
  durationInFrames={300}  // 改为 300 帧 = 10秒
  fps={30}
  // ...
/>
```

### 修改分辨率

```tsx
<Composition
  width={3840}   // 4K
  height={2160}
  // ...
/>
```

### 修改颜色/文字

编辑对应的 `src/compositions/*.tsx` 文件，搜索要修改的文字或颜色值。

---

## 🐛 常见问题

### Q: npm install 卡住

A: 使用国内镜像：
```bash
npm config set registry https://registry.npmmirror.com
npm install
```

### Q: 渲染时内存不足

A: 降低分辨率或使用 `--concurrency=1`：
```bash
npx remotion render FSMStateTransition out/test.mp4 --concurrency=1
```

### Q: 白屏或组件不显示

A: 检查浏览器控制台错误，或渲染静帧调试：
```bash
npx remotion still FSMStateTransition out/debug.png --frame=60
```

### Q: 想要导出 GIF

A: 使用 `--codec=gif`：
```bash
npx remotion render FSMStateTransition out/fsm.gif --codec=gif
```

---

## 📖 更多信息

详细文档请参考 [README.md](README.md)

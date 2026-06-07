# Remotion 动画使用指南

本文档说明如何使用和自定义 compass-gait-remotion 项目中的动画组件。

## 📋 目录

- [快速开始](#快速开始)
- [可用动画列表](#可用动画列表)
- [渲染命令](#渲染命令)
- [自定义动画](#自定义动画)
- [性能优化](#性能优化)
- [故障排查](#故障排查)
- [集成到主项目](#集成到主项目)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd D:\Dunna\Documents\hw-1\compass-gait-remotion
npm install
```

### 2. 启动预览

```bash
npm start
```

浏览器会自动打开 `http://localhost:3000`，可实时预览所有动画。

### 3. 渲染单个视频

```bash
npm run render:roadmap
```

---

## 🎬 可用动画列表

### 1. FSMStateTransition — V13.6 四相位状态机

**时长**: 8秒 (240帧 @ 30fps)  
**用途**: 展示事件驱动FSM的四个相位及切换逻辑

**特点**:
- 动态高亮当前激活相位
- 显示切换条件（u ≥ 0.5 / 接触切换）
- 支撑相 vs 摆动相颜色区分
- 实时相位进度百分比

**渲染**:
```bash
npm run render:fsm
# 输出: out/fsm_state_transition.mp4
```

---

### 2. RollingFootAnimation — V10 足踝滚动

**时长**: 10秒 (300帧 @ 30fps)  
**用途**: 展示脚跟-足底-脚趾滚动接触过程

**特点**:
- 足部三段式结构可视化
- 踝关节旋转角度动画
- 接触相位时间轴
- 准被动仿生特性标注

**渲染**:
```bash
npm run render:rolling
# 输出: out/rolling_foot_animation.mp4
```

---

### 3. PhaseVisualization — 步态相位可视化

**时长**: 10秒 (300帧 @ 30fps)  
**用途**: 实时显示关节角度和接触状态

**特点**:
- 三关节（髋/膝/踝）角度柱状图
- 左右脚接触指示器
- 相位进度条
- 仿真时间计数器

**渲染**:
```bash
npm run render:phase
# 输出: out/phase_visualization.mp4
```

---

### 4. GaitComparison — V10 vs V13.6 对比

**时长**: 12秒 (360帧 @ 30fps)  
**用途**: 横向对比两种控制方案

**对比指标**:
- 前进距离: 4.85m vs 4.86m
- 输入能量: 15.2J vs 17.45J
- CoT: 0.065 vs 0.072
- 切片C成功率: 16.7% vs 11.1%

**渲染**:
```bash
npm run render:comparison
# 输出: out/gait_comparison.mp4
```

---

### 5. FrictionCompensation — V13.7 摩擦补偿 ✨ 新增

**时长**: 12秒 (360帧 @ 30fps)  
**用途**: 展示有无摩擦补偿的性能差异

**对比效果**:
- 能量损失减少: -68%
- 行走距离增加: +52%
- 稳定性提升: +82%

**特点**:
- 分屏对比布局
- 逐项指标动画展开
- 成功/失败状态可视化
- 关键改进说明

**渲染**:
```bash
npm run render:friction
# 输出: out/friction_compensation.mp4
```

---

### 6. TechnicalRoadmap — 技术路线图 ✨ 新增

**时长**: 15秒 (450帧 @ 30fps)  
**用途**: 展示从V01到V25的完整技术演进

**技术阶段**:
1. **V01-V05**: 基础探索 (Compass Gait, Limit Cycle)
2. **V06-V09**: 准被动控制 (能量整形, PD控制)
3. **V10-V13**: 滚动足与FSM (足踝滚动, 摩擦补偿)
4. **V14-V17**: 执行器建模 (被动臂, SEA, 电机动力学)
5. **V18-V21**: 3D拓展 (侧向稳定, 髋外展, 步宽控制)
6. **V22-V25**: 硬件实现 (机械设计, Sim-to-Real)

**特点**:
- 时间轴动画
- 节点高亮
- 关键特性标注
- 底部统计信息

**渲染**:
```bash
npm run render:roadmap
# 输出: out/technical_roadmap.mp4
```

---

### 7. MotorDynamics — V16 电机动力学 ✨ 新增

**时长**: 12秒 (360帧 @ 30fps)  
**用途**: 展示电机性能限制与失败带分析

**内容**:
- **左侧**: Maxon EC45 电机规格
  - 额定/峰值扭矩
  - 额定/峰值转速
  - 电阻和扭矩常数
- **右侧**: 失败带可视化
  - 髋膝角度参数空间
  - 成功区域 vs 失败带
  - 数据点动画连线

**特点**:
- 电机转子旋转动画
- 失败带实时绘制
- 参数空间可视化
- 图例说明

**渲染**:
```bash
npm run render:motor
# 输出: out/motor_dynamics.mp4
```

---

### 8. DataDrivenExample — 数据驱动示例

**时长**: 10秒 (300帧 @ 30fps)  
**用途**: 展示如何加载真实仿真数据

**功能**:
- 从 JSON 文件加载数据
- 容错处理（数据不存在时使用模拟数据）
- 六关节角度实时显示
- 左右脚接触状态

**使用方法**:
```bash
# 先导出数据
python utils/export_for_remotion.py \
  --input ../v10_rolling_foot_biomimetic_gait/out/v10_data.csv \
  --output public/data/v10_data.json

# 然后渲染
remotion render DataDrivenExample out/data_driven.mp4
```

---

## 🎨 渲染命令

### 快速渲染所有动画

```bash
# 方法1: 使用 npm scripts
npm run render:fsm
npm run render:rolling
npm run render:phase
npm run render:comparison
npm run render:friction
npm run render:roadmap
npm run render:motor

# 方法2: 使用 PowerShell 脚本（如果已创建）
.\scripts\render_all.ps1

# 方法3: 手动逐个渲染
npx remotion render FSMStateTransition out/fsm.mp4
npx remotion render TechnicalRoadmap out/roadmap.mp4
```

### 自定义渲染参数

```bash
# 指定帧范围
npx remotion render TechnicalRoadmap out/roadmap_clip.mp4 \
  --frames=0-150

# 修改帧率
npx remotion render FSMStateTransition out/fsm_60fps.mp4 \
  --override-fps=60

# 修改分辨率
npx remotion render TechnicalRoadmap out/roadmap_720p.mp4 \
  --width=1280 --height=720

# 调整视频质量 (CRF: 越小质量越高)
npx remotion render TechnicalRoadmap out/roadmap_hq.mp4 \
  --crf=15

# 快速预览 (低质量)
npx remotion render TechnicalRoadmap out/roadmap_preview.mp4 \
  --crf=28 --scale=0.5
```

### 渲染为静态帧

```bash
# 渲染单帧 (PNG)
npx remotion still TechnicalRoadmap out/roadmap_frame.png --frame=200

# 渲染多帧
for frame in 0 100 200 300; do
  npx remotion still TechnicalRoadmap out/roadmap_$frame.png --frame=$frame
done
```

---

## 🔧 自定义动画

### 修改动画参数

在 `src/Root.tsx` 中修改 `defaultProps`:

```tsx
<Composition
  id="TechnicalRoadmap"
  component={TechnicalRoadmap}
  durationInFrames={450}  // 修改时长
  fps={30}                // 修改帧率
  width={1920}            // 修改分辨率
  height={1080}
  defaultProps={{
    startVersion: 10,     // 从V10开始
    endVersion: 20,       // 到V20结束
  }}
/>
```

### 修改颜色方案

在组件文件中修改颜色常量:

```tsx
// FrictionCompensation.tsx
const withoutCompensation = {
  // ... 数据
};

// 修改颜色
<ComparisonCard
  title="无摩擦补偿"
  color="#EF4444"  // 改为其他颜色
  // ...
/>
```

### 调整动画速度

```tsx
// 减慢动画速度（增加时长）
durationInFrames={600}  // 从450改为600

// 加快动画速度（减少时长）
durationInFrames={300}  // 从450改为300
```

### 添加中英文字幕

```tsx
// 在任何组件中添加字幕
<div
  style={{
    position: 'absolute',
    bottom: 100,
    left: 0,
    right: 0,
    textAlign: 'center',
    color: '#F1F5F9',
    fontSize: 28,
  }}
>
  技术演进历程 | Technical Evolution
</div>
```

---

## ⚡ 性能优化

### 1. 渲染性能优化

```bash
# 增加并发数（多核CPU）
npx remotion render TechnicalRoadmap out/roadmap.mp4 \
  --concurrency=4

# 使用 ANGLE OpenGL 渲染器
# 已在 remotion.config.ts 中配置

# 禁用不必要的功能
npx remotion render TechnicalRoadmap out/roadmap.mp4 \
  --disable-keyboard-shortcuts
```

### 2. 代码优化

```tsx
// 使用 useMemo 缓存计算
import {useMemo} from 'react';

const expensiveData = useMemo(() => {
  return computeExpensiveData(props);
}, [props]);

// 避免在每帧重新创建对象
const style = useMemo(() => ({
  backgroundColor: '#0F172A',
  // ...
}), []);
```

### 3. 预渲染优化

```bash
# 首次渲染会下载 Chrome Headless Shell
# 后续渲染会使用缓存，速度更快

# 清除缓存（如需重新下载）
npx remotion clear-cache
```

---

## 🐛 故障排查

### 问题1: npm install 失败

**解决方案**:
```bash
# 清除缓存
npm cache clean --force

# 删除 node_modules 重新安装
Remove-Item -Recurse -Force node_modules
npm install
```

### 问题2: 渲染白屏或报错

**诊断步骤**:
```bash
# 1. 检查 TypeScript 编译错误
npm test

# 2. 渲染静态帧检查
npx remotion still TechnicalRoadmap out/debug.png --frame=100

# 3. 查看浏览器控制台（npm start 时）
```

**常见原因**:
- 组件未正确导出
- Props 类型不匹配
- 未处理的异常

### 问题3: TypeScript 错误

当前版本存在一些类型警告，但不影响渲染:

```bash
# 跳过 TypeScript 检查直接渲染
npx remotion render TechnicalRoadmap out/roadmap.mp4 --skip-type-check
```

### 问题4: 渲染速度慢

**优化方案**:
```bash
# 使用低质量快速预览
npx remotion render TechnicalRoadmap out/roadmap.mp4 \
  --crf=28 --scale=0.5

# 只渲染前100帧测试
npx remotion render TechnicalRoadmap out/roadmap_test.mp4 \
  --frames=0-100
```

### 问题5: 内存不足

```bash
# 减少并发数
npx remotion render TechnicalRoadmap out/roadmap.mp4 \
  --concurrency=1

# 降低分辨率
npx remotion render TechnicalRoadmap out/roadmap.mp4 \
  --width=1280 --height=720
```

---

## 🔗 集成到主项目

### 1. 在论文中引用

**LaTeX**:
```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.9\textwidth]{hw-1/compass-gait-remotion/out/technical_roadmap.pdf}
  \caption{V01至V25技术演进路线图}
  \label{fig:tech-roadmap}
\end{figure}
```

**转换为 PDF**:
```bash
# 使用 ffmpeg 转换
ffmpeg -i out/technical_roadmap.mp4 -vf "select=eq(n\,100)" -vframes 1 out/technical_roadmap.pdf
```

### 2. 在演示文稿中使用

**PowerPoint / Keynote**:
- 直接插入 MP4 视频
- 设置自动播放
- 循环播放选项

**在线演示**:
```bash
# 导出为 GIF（文件较大，不推荐）
ffmpeg -i out/technical_roadmap.mp4 -vf "fps=15,scale=960:-1" out/technical_roadmap.gif

# 推荐: 托管视频并分享链接
```

### 3. 与 Python 仿真集成

**自动化流水线**:
```bash
# 1. 运行仿真
python v13_7_friction_compensation/simulate_v13_7.py

# 2. 导出数据
cd compass-gait-remotion
python utils/export_for_remotion.py \
  --input ../v13_7_friction_compensation/out/data.csv \
  --output public/data/v13_7_data.json

# 3. 渲染动画
npm run render:friction

# 4. 复制到输出目录
Copy-Item out/*.mp4 ../outputs/animations/
```

### 4. 集成到 dashboard

在主项目的 `dashboard` 中嵌入动画:

```python
# dashboard/app.py
import streamlit as st

st.title("步态动画展示")

# 嵌入视频
video_file = open('../compass-gait-remotion/out/technical_roadmap.mp4', 'rb')
video_bytes = video_file.read()
st.video(video_bytes)

# 或使用 HTML iframe
st.markdown("""
<video width="960" height="540" controls>
  <source src="../compass-gait-remotion/out/technical_roadmap.mp4" type="video/mp4">
</video>
""", unsafe_allow_html=True)
```

---

## 📊 输出规格

所有动画默认输出规格:

- **分辨率**: 1920×1080 (Full HD)
- **帧率**: 30 fps
- **编码**: H.264
- **格式**: MP4
- **质量**: CRF 18 (高质量)
- **文件大小**: 约 5-15 MB/分钟

---

## 🎯 最佳实践

### 1. 开发流程

```bash
# 1. 启动预览服务器
npm start

# 2. 在浏览器中实时调试
# http://localhost:3000

# 3. 修改代码，保存后自动刷新

# 4. 渲染测试帧
npx remotion still MyAnimation out/test.png --frame=100

# 5. 满意后渲染完整视频
npm run render:myanimation
```

### 2. 版本控制

```bash
# 不要提交 node_modules 和 out 目录
# 已在 .gitignore 中配置

# 提交新动画组件
git add src/compositions/NewAnimation.tsx
git commit -m "feat: add NewAnimation component"
```

### 3. 代码组织

```
src/
├── compositions/          # 动画组件
│   ├── FSMStateTransition.tsx
│   ├── TechnicalRoadmap.tsx
│   └── ...
├── components/           # 可复用组件（如需）
│   └── MetricCard.tsx
├── utils/               # 工具函数（如需）
│   └── interpolation.ts
├── Root.tsx             # 注册所有 Composition
└── index.ts             # 入口文件
```

---

## 📚 参考资源

- [Remotion 官方文档](https://www.remotion.dev/docs)
- [Remotion 示例库](https://www.remotion.dev/showcase)
- [React 文档](https://react.dev/)
- [主项目 README](../README.md)

---

## 📝 更新日志

### v2.0.0 (2026-06-05)

**新增动画**:
- ✨ FrictionCompensation: V13.7 摩擦补偿对比
- ✨ TechnicalRoadmap: V01-V25 技术演进路线图
- ✨ MotorDynamics: V16 电机动力学与失败带

**改进**:
- 🔧 升级 TypeScript 至 5.3.3
- 🔧 修复 tsconfig.json moduleResolution 配置
- 🔧 添加 npm scripts 快速渲染命令
- 📝 完善文档和使用指南

**已知问题**:
- TypeScript 存在类型警告（不影响渲染）
- 可通过 `--skip-type-check` 跳过

### v1.0.0 (2026-06-04)

- 🎉 初始版本
- 5个基础动画组件
- 完整文档和工具脚本

---

**文档版本**: 2.0.0  
**最后更新**: 2026-06-05  
**维护者**: hw-1 项目组

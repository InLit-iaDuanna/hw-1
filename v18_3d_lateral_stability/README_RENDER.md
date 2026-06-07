# V18 侧向稳定性渲染系统

## 概述

V18 渲染脚本用于展示 3D 被动式步态机器人的侧向稳定性。通过对比不同 `hip_roll` 刚度参数，展示侧向失败和成功的行走过程。

## 核心功能

### 1. 仿真与录制 (`run_and_record_v18`)
- 运行 V18 矢状面控制器 + 侧向被动弹性
- 以 60fps 记录状态快照（qpos, qvel, roll, hip_y, 步数）
- 检测失败条件（侧向跌倒、漂移、NaN）

### 2. 多视角渲染 (`render_view`)
- **侧视图 (Sagittal)**: azimuth=90°, 展示矢状面步态
- **前视图 (Frontal)**: azimuth=0°, 展示冠状面侧向振荡
- 相机跟随 hip_x 位置
- 中文标注：时间、Roll角度、侧向位移、步数

### 3. 对比拼接 (`render_comparison`)
- 并排对比两个条件（如 roll_k=100 vs roll_k=500）
- 自动填充帧数到相同长度
- 底部添加条件标签

## 使用方法

### 模式 1: 单条件渲染（双视角）

```powershell
python render_v18.py --mode single --roll-stiffness 100 --duration 6.0
```

**输出**:
- `v18_rollk100_sagittal.mp4` - 侧视图
- `v18_rollk100_frontal.mp4` - 前视图

### 模式 2: 对比渲染

```powershell
python render_v18.py --mode comparison --duration 6.0
```

**输出**:
- `v18_comparison.mp4` - 并排对比视频
- `v18_comparison_metadata.json` - 定量对比数据

### 模式 3: 双视角拼接

```powershell
python render_v18.py --mode dual --roll-stiffness 100 --duration 6.0
```

**输出**:
- `v18_rollk100_dual.mp4` - 侧视+前视并排

## 技术细节

### 渲染参数
- **分辨率**: 1280×720 (单视角) / 640×720 (拼接)
- **帧率**: 60 fps
- **编码器**: libx264, quality=8
- **字体**: 微软雅黑 (msyh.ttc)

### 相机配置

| 视角 | distance | azimuth | elevation | lookat |
|------|----------|---------|-----------|--------|
| 侧视 | 3.0 | 90° | -10° | [hip_x, 0, 0.5] |
| 前视 | 2.5 | 0° | 0° | [hip_x, 0, 0.5] |

### 标注系统

#### 主信息框（左上）
- 时间: 当前仿真时间
- Roll角度: 带颜色指示（>15° 红色警告）
- 侧向位移: hip_y 单位毫米（>150mm 红色）
- 步数: alternating touchdowns 计数

#### 参数框（右上）
- Roll刚度 (hip_roll_stiffness)
- Roll阻尼 (hip_roll_damping)
- 初始扰动 (init_hip_roll_deg)

## 生成的视频

### v18_lateral_divergence.mp4
- **roll_k = 100** (低刚度)
- 展示侧向振荡逐渐增大直至失败
- 侧视图，6秒，235帧
- 最终 roll ≈ 6.5°, hip_y ≈ -110mm

### v18_comparison.mp4
- **左**: roll_k=100 (失败) - 振荡发散
- **右**: roll_k=500 (稳定) - 快速收敛
- 并排对比，展示刚度对侧向稳定性的影响
- 最终对比: 6.5° vs 0.02°

### v18_rollk100_frontal.mp4
- roll_k=100 的前视图
- 清晰展示侧向摆动的增长过程

## 对比数据

```json
{
  "fail_case": {
    "roll_stiffness": 100.0,
    "final_steps": 4,
    "final_roll_deg": 6.48,
    "final_hip_y": -0.110 m
  },
  "stable_case": {
    "roll_stiffness": 500.0,
    "final_steps": 4,
    "final_roll_deg": -0.018,
    "final_hip_y": -0.032 m
  }
}
```

**结论**: roll_k=500 将侧向偏移减少 71%，roll角度减少 99.7%。

## 依赖项

- `mujoco` >= 3.0
- `imageio` >= 2.31
- `Pillow` >= 10.0
- `numpy`

## 文件结构

```
v18_3d_lateral_stability/
├── render_v18.py              # 渲染主脚本
├── simulate_v18.py            # 仿真逻辑
├── model_3d.py                # 3D模型生成
├── README_RENDER.md           # 本文档
└── out/
    ├── v18_lateral_divergence.mp4
    ├── v18_comparison.mp4
    ├── v18_rollk100_sagittal.mp4
    ├── v18_rollk100_frontal.mp4
    └── v18_comparison_metadata.json
```

## 扩展用法

### 自定义参数对比

```python
params_custom = Lateral3DParams(
    hip_roll_stiffness=200.0,
    hip_roll_damping=1.0,
    init_hip_roll_deg=5.0,
    duration=8.0,
)
frames = run_and_record_v18(params_custom, target_duration=8.0)
rendered = render_view(frames, params_custom, "sagittal")
```

### 批量参数扫描

```powershell
foreach ($k in 50,100,200,500,1000) {
    python render_v18.py --mode single --roll-stiffness $k --duration 6.0
}
```

## 已知限制

- Windows 控制台 Unicode 字符显示问题（已替换✓为[OK]）
- 大视频文件需要 FFmpeg 后处理压缩
- 仿真时间 >10s 时渲染内存占用较大

## 版本历史

- **2026-06-05**: 初始版本，支持 single/dual/comparison 三种模式
- 中文标注系统完成
- 对比元数据导出功能

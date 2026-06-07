# 会议海报制作指南

本文档提供 hw-1 项目会议海报的制作指南和模板说明。

## 海报规格

- **尺寸**：A0（841 × 1189 mm）
- **方向**：竖向（Portrait）
- **分辨率**：300 DPI
- **格式**：PowerPoint (.pptx) 或 PDF
- **打印成本**：约 80-120 元（彩色喷绘）

## 布局设计（3 列）

```
┌─────────────────────────────────────────────────┐
│              标题区（居中）                        │
│   Event-Driven FSM Control for                  │
│   Quasi-Passive Biped Walking                   │
│                                                 │
│   Zeqi Duan | 段泽琪                            │
│   School of Mechanical Engineering              │
├───────────┬─────────────┬─────────────────────┤
│  左列      │   中列       │      右列            │
│           │             │                     │
│ 研究背景   │  核心方法    │   硬件设计          │
│           │             │                     │
│ 问题定义   │  FSM 相位图  │   否定结果          │
│           │             │                     │
│ 版本演化   │  摩擦补偿    │   结论与展望        │
│ 时间线     │             │                     │
│           │  稳定域热图  │   QR 码             │
│           │             │   （视频链接）       │
│           │  能量效率    │                     │
│           │             │                     │
├───────────┴─────────────┴─────────────────────┤
│        底部：参考文献 | 致谢 | 联系方式          │
└─────────────────────────────────────────────────┘
```

## 内容模块

### 标题区（高度 ~15 cm）

- **标题**：Event-Driven Finite State Machine Control for Quasi-Passive Biped Walking with Friction Compensation
  - 字体：Arial Bold, 80 pt
  - 颜色：深蓝色 (#1a4d7a)

- **作者信息**：
  ```
  Zeqi Duan (段泽琪)
  School of Mechanical Engineering
  [University Name]
  Email: [email]
  ```
  - 字体：Arial, 36 pt

- **Logo**：学校 Logo（左上角）、会议 Logo（右上角）

---

### 左列：研究背景与动机

#### 1. 研究背景（~20 cm）

**标题**：Background & Motivation

**内容**：
- 人类行走能量效率（CoT ≈ 0.05）远优于主动机器人（CoT ≈ 0.8）
- 准被动步态：最小化能量输入 + 利用自然动力学
- 挑战：真实电机摩擦破坏稳定性

**配图**：
- 人类行走剪影 vs 机器人示意图
- CoT 对比柱状图

#### 2. 研究问题（~15 cm）

**标题**：Research Questions

**内容**（4 个要点）：
1. 如何设计控制律应对电机摩擦？
2. 前馈补偿能否恢复性能？
3. 低成本传感器噪声容限？
4. 侧向被动稳定的物理极限？

#### 3. 版本演化时间线（~50 cm）

**标题**：Development Pipeline (V01-V24)

**配图**：fig1_version_evolution.pdf（旋转 90°）

**关键里程碑标注**：
- V05：纯被动极限环证明
- V10：准被动 PD 控制
- V13.7：摩擦补偿
- V17：状态估计
- V22：硬件设计

---

### 中列：核心方法与结果

#### 1. FSM 控制律（~25 cm）

**标题**：Event-Driven FSM Control

**配图**：v13_6_event_driven_fsm/out/v13_6_baseline_report.png

**文字说明**：
```
4-Phase Finite State Machine:
1. Pre-Liftoff: PD control
2. Early Swing: Energy injection
3. Late Swing: Negative feedback
4. Pre-Touchdown: Braking

Phase transitions: Contact force, hip angle, hip velocity
```

#### 2. 摩擦补偿（~25 cm）

**标题**：Friction Compensation (V13.7)

**配图**：对比图（左：无补偿失败，右：有补偿成功）
- v13_7_friction_compensation/out/v13_7_smoke_no_comp_mx64ar_preview.png
- v13_7_friction_compensation/out/v13_7_smoke_compensated_mx64ar_preview.png

**公式**：
```
τ_output = τ_FSM + τ_C · sign_smooth(ω_joint)
```

**结果表格**：
| 配置 | 前向距离 | 结果 |
|------|---------|------|
| 无补偿 | 0.19 m | ✗ |
| 有补偿 | 4.63 m | ✓ |

#### 3. 稳定域热图（~25 cm）

**标题**：Parameter Sensitivity (V13)

**配图**：fig2_stability_domain.pdf

**文字说明**：
```
Success rate: 16.7% (V10) → 27.8% (V13.7)
Key finding: Friction compensation expands stability domain by +11.1 pp
```

#### 4. 能量效率（~20 cm）

**标题**：Energy Efficiency

**配图**：fig3_energy_analysis.pdf

**结果**：
```
CoT = 0.066 (本研究)
vs Human: 0.05
vs Literature: 0.15-0.20
19.5% improvement over V10
```

---

### 右列：硬件与讨论

#### 1. 硬件设计（~30 cm）

**标题**：Hardware Design (V22)

**配图**：fig5_hardware_specs.pdf

**规格表**：
```
Leg length: 1.00 m
Total mass: 5.5 kg
Actuator: Dynamixel MX-64AR × 4
Controller: Raspberry Pi 4B (1000 Hz)
Sensor: 4096 CPR encoder + IMU
Cost: 6800 CNY (~$950 USD)
```

#### 2. 否定结果的学术价值（~30 cm）

**标题**：Negative Results (V18-V20)

**内容（3 个发现）**：

**V18: Passive Lateral Stability**
- Finding: Sagittal passive ⊥ Lateral passive
- k_roll < 200: Divergence
- k_roll ≥ 500: Equivalent to 2D

**V19: Hip Abduction Actuation**
- Actuation authority gap: 5-10×
- Drift rate: 0.05-0.10 m/step
- Correction: <0.01 m/step

**V20: Step Width Control**
- Complexity underestimated
- Smoke test failed (1s)
- Decision gate: Skip V21 → V22

**配图**：V18 滚转角发散曲线

#### 3. 结论与展望（~25 cm）

**标题**：Conclusion & Future Work

**主要贡献**：
- ✓ Friction compensation eliminates failure band
- ✓ Sensor noise tolerance: 3× safety margin
- ✓ Theoretical limits of lateral passive stability
- ✓ Complete hardware design ($950, ready to build)

**下一步**：
- V25: Hardware walking (3 months)
- Long-term simulation (verify Floquet)
- 3D control revisited with real data

#### 4. 二维码（~15 cm）

**Video Supplement**
- QR 码链接到 YouTube 播放列表
- "Scan for video demos"

---

### 底部：参考文献与致谢（~10 cm）

**参考文献**（精选 5 篇）：
1. McGeer (1990). Passive Dynamic Walking. IJRR.
2. Collins et al. (2005). Efficient Bipedal Robots. Science.
3. Goswami et al. (1996). Compass-Like Biped Robot. INRIA.
4. Wisse et al. (2007). Ankle Springs. IEEE T-RO.
5. Bloesch et al. (2013). State Estimation for Legged Robots. RSS.

**致谢**：
```
This work was supported by [Funding Source].
Thanks to [Advisors] for valuable guidance.
```

**联系方式**：
```
Email: [email]
GitHub: [repository URL]
Project site: [website]
```

---

## 配色方案

使用项目标准配色（colorblind-friendly）：

- **成功**：#2a7a3b（深绿）
- **警告**：#d68b00（橙色）
- **失败**：#b3331b（深红）
- **中性**：#3a3a3a（深灰）
- **强调**：#0c789f（蓝色）

**背景**：
- 主背景：白色 (#FFFFFF)
- 模块背景：浅灰色 (#F5F5F5)
- 标题栏：深蓝渐变 (#1a4d7a → #2b6ba5)

---

## 字体规范

- **标题**：Arial Bold, 60-80 pt
- **小标题**：Arial Bold, 40-50 pt
- **正文**：Arial, 28-32 pt
- **图表标注**：Arial, 24-28 pt
- **参考文献**：Arial, 20-24 pt

---

## 图表要求

1. **高分辨率**：所有图片 ≥300 DPI
2. **统一风格**：使用 paper_figures/ 生成的 PDF 图表
3. **清晰标注**：轴标签、图例、单位
4. **避免截断**：预留边距

---

## 制作流程

### Step 1: 准备图片

从 paper_figures/output/ 和各版本 out/ 目录复制关键图表到 poster_figures/：

```powershell
# 复制关键图表
Copy-Item "D:\Dunna\Documents\hw-1\paper_figures\output\*.pdf" `
  -Destination "D:\Dunna\Documents\hw-1\publications\poster\poster_figures\"

Copy-Item "D:\Dunna\Documents\hw-1\v13_6_event_driven_fsm\out\v13_6_baseline_report.png" `
  -Destination "D:\Dunna\Documents\hw-1\publications\poster\poster_figures\"

# ... 其他图表
```

### Step 2: 创建 PowerPoint

1. 打开 PowerPoint
2. 设计 → 页面设置 → 自定义 → 84.1 cm × 118.9 cm
3. 插入 → 形状 → 矩形（创建 3 列布局）
4. 插入图片、文本框
5. 调整字体、颜色

### Step 3: 导出 PDF

1. 文件 → 另存为 → PDF
2. 选项 → 优化：标准（联机发布和打印）
3. 保存为 poster_final.pdf

### Step 4: 打印

- **在线打印**：快印客、一撕得、淘宝（搜索"学术海报打印"）
- **成本**：80-120 元（A0 彩色喷绘 + 覆膜）
- **交付时间**：2-3 天

---

## PowerPoint 模板文件

模板文件路径：`D:\Dunna\Documents\hw-1\publications\poster\poster_template.pptx`

**使用说明**：
1. 打开模板文件
2. 替换 [Placeholder] 文本和图片
3. 调整内容适配实际数据
4. 导出 PDF

---

## 常见问题

**Q1: 图片模糊怎么办？**

A: 确保原图 ≥300 DPI。PowerPoint 中右键图片 → 设置图片格式 → 压缩 → 不压缩。

**Q2: 字体太小看不清？**

A: 海报观看距离通常 1-2 米，正文字号应 ≥28 pt。打印前可在电脑上放大 200% 预览。

**Q3: 颜色打印出来偏差？**

A: 使用 CMYK 色彩模式（打印色）而非 RGB（屏幕色）。与打印店确认色彩校准。

**Q4: 海报运输如何保护？**

A: 使用海报筒（约 10 元）。或覆膜后卷起，用塑料袋包裹。

---

## 会议投稿清单

以下会议接受海报：

### ICRA 2027
- 截稿：2026-09-15
- 海报尺寸：A0 竖向
- 展示时间：2 小时
- 地点：[城市]

### IROS 2026
- 截稿：2026-03-01
- 海报尺寸：A0 竖向
- 展示时间：2 小时
- 地点：[城市]

### Humanoids 2026
- 截稿：2026-06-30
- 海报尺寸：A0 竖向
- 展示时间：1.5 小时
- 地点：[城市]

---

## 更新日志

- **2026-06-04**：初始海报制作指南
- **待补充**：PowerPoint 模板文件（手动创建）
- **待补充**：实际打印效果照片

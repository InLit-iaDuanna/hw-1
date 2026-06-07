# 补充材料 - 演示视频索引

本文档索引 hw-1 项目中的关键演示视频，用于论文补充材料、会议海报二维码链接和答辩演示。

## 视频组织结构

```
hw-1/
├── v05_hybrid_compass_proof/out/
├── v10_rolling_foot_biomimetic_gait/out/
├── v13_6_event_driven_fsm/out/
├── v13_7_friction_compensation/out/
├── v16_motor_dynamics/out/
├── v17_state_estimation/out/
└── [其他版本]/out/
```

---

## 主要演示视频

### 1. 纯被动极限环证明（V05）

**文件路径**：`D:\Dunna\Documents\hw-1\v05_hybrid_compass_proof\out\hybrid_compass_walk.mp4`

**时长**：约 10 秒

**内容描述**：
- 指南针步态在斜坡（γ=0.05 rad）上的纯被动行走
- 无主动驱动，仅重力和碰撞
- 展示 Poincaré 截面收敛过程
- 5-6 次触地后达到稳定极限环

**用途**：
- 论文 Introduction（说明被动步态原理）
- 答辩 Slide 6（纯被动极限环）

**关键帧**：
- 0:00 - 初始状态（静止）
- 0:03 - 第 3 次触地（接近极限环）
- 0:08 - 稳定周期步态

---

### 2. 准被动滚动足步态（V10）

**文件路径**：`D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\out\v10_rolling_foot_walk.mp4`

**时长**：约 8 秒

**内容描述**：
- 髋部和膝部 PD 控制
- 圆弧足（rolling foot）降低碰撞损失
- 前向距离 4.52 m，10 次触地
- CoT = 0.082

**用途**：
- 论文 Methodology（准被动控制基线）
- 答辩 Slide 7（V10 PD 控制）
- 会议海报（中央展示区）

**关键帧**：
- 0:00 - 启动（第 1 次触地）
- 0:04 - 稳定行走（第 5-6 次触地）
- 0:07 - 最后一步（第 10 次触地）

---

### 3. FSM 4 相位控制（V13.6）

**文件路径**：`D:\Dunna\Documents\hw-1\v13_6_event_driven_fsm\out\v13_6_baseline_walk.mp4`

**时长**：约 8 秒

**内容描述**：
- 事件驱动有限状态机
- 4 个相位切换（Pre-Liftoff → Early Swing → Late Swing → Pre-Touchdown）
- 相位转移可视化（颜色编码）
- 前向距离 4.38 m

**用途**：
- 论文 Methodology（FSM 设计）
- 答辩 Slide 8（FSM 控制律）

**配套图表**：
- `v13_6_baseline_report.png`（FSM 状态转移图 + 相位空间轨迹）

---

### 4. 摩擦补偿对比（V13.7）

**文件路径**（3 个视频）：

1. **无补偿失败**：`D:\Dunna\Documents\hw-1\v13_7_friction_compensation\out\v13_7_smoke_no_comp_mx64ar.mp4`
   - 时长：约 2 秒
   - MX-64AR 电机，无摩擦补偿
   - 前向距离 0.19 m，4 次触地后跌倒
   - 展示摩擦破坏稳定性

2. **补偿后成功**：`D:\Dunna\Documents\hw-1\v13_7_friction_compensation\out\v13_7_smoke_compensated_mx64ar.mp4`
   - 时长：约 8 秒
   - MX-64AR 电机，前馈摩擦补偿
   - 前向距离 4.63 m，10 次触地
   - 完全恢复性能

3. **EC-i40 验证**：`D:\Dunna\Documents\hw-1\v13_7_friction_compensation\out\v13_7_smoke_compensated_ec_i40.mp4`
   - 时长：约 8 秒
   - EC-i 40 电机（低摩擦），有补偿
   - 验证补偿方法的通用性

**用途**：
- 论文 Results（摩擦补偿效果）
- 答辩 Slide 10（关键突破）
- 会议海报（对比展示）

**建议并排播放**：无补偿（左）vs 有补偿（右）

---

### 5. 状态估计噪声鲁棒性（V17）

**文件路径**：`D:\Dunna\Documents\hw-1\v17_state_estimation\out\v17_mx64ar_noise1_walk.mp4`

**时长**：约 8 秒

**内容描述**：
- 编码器量化（4096 CPR）+ Kalman 滤波
- noise_scale = 1.0×（MX-64AR 真实噪声）
- 前向距离 4.67 m，10 次触地
- 实时显示估计误差（RMSE）

**用途**：
- 论文 Results（状态估计验证）
- 答辩 Slide 11（传感器闭环）

**配套图表**：
- `v17_state_estimation_error.png`（速度估计 RMSE vs 时间）

---

### 6. 电机动力学对比（V16）

**文件路径**（2 个视频）：

1. **理想电机**：`D:\Dunna\Documents\hw-1\v16_motor_dynamics\out\v16_smoke_ideal.mp4`
   - 时长：约 8 秒
   - 理想驱动器（无摩擦），前向距离 4.62 m
   - 基线对照

2. **MX-64AR 失败**：`D:\Dunna\Documents\hw-1\v16_motor_dynamics\out\v16_smoke_mx64ar_full.mp4`
   - 时长：约 2 秒
   - MX-64AR 真实摩擦，前向距离 0.19 m
   - 展示摩擦破坏性

**用途**：
- 论文 Results（电机摩擦影响）
- 答辩 Slide 9（电机摩擦的破坏性）

---

### 7. SEA 直驱对比（V15.1）

**文件路径**（2 个视频）：

1. **高刚度弹簧**：`D:\Dunna\Documents\hw-1\v15_1_sea_direct\out\v151_smoke_k10000.mp4`
   - 时长：约 8 秒
   - k=10000 N·m/rad，复现 V14c 性能

2. **柔性弹簧**：`D:\Dunna\Documents\hw-1\v15_1_sea_direct\out\v151_smoke_k00500.mp4`
   - 时长：约 8 秒
   - k=500 N·m/rad，前向距离 4.92 m（最佳）
   - 弹簧变形 1.6 度

**用途**：
- 补充材料（SEA 探索）
- 会议海报（机械升级路径）

---

## 视频技术规格

| 规格 | 值 |
|------|-----|
| 分辨率 | 1920×1080 (Full HD) |
| 帧率 | 60 fps |
| 编码 | H.264 |
| 文件格式 | .mp4 |
| 平均文件大小 | 2-5 MB（8 秒视频）|
| 渲染工具 | MuJoCo viewer + FFmpeg |

---

## 视频生成命令

所有视频通过以下 Python 脚本生成：

```powershell
# 示例：V10 滚动足步态
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_v10.py --render --save-video
```

输出：`v10_rolling_foot_biomimetic_gait\out\v10_rolling_foot_walk.mp4`

---

## 在线发布建议

### YouTube Playlist（推荐）

创建公开播放列表："HW-1 Quasi-Passive Biped Walking - Video Supplement"

播放列表结构：
1. V05 - Passive Limit Cycle Proof
2. V10 - Quasi-Passive Rolling Foot Gait
3. V13.6 - Event-Driven FSM Control
4. V13.7 - Friction Compensation (Before/After)
5. V16 - Motor Dynamics Impact
6. V17 - State Estimation with Sensor Noise

每个视频添加：
- 标题（英文）
- 描述（含参数、结果摘要）
- 标签：biped robot, passive walking, quasi-passive, FSM control
- 链接到 GitHub 仓库（如公开）

### 二维码生成

为会议海报生成二维码，链接到 YouTube 播放列表：

```
https://youtube.com/playlist?list=[PLAYLIST_ID]
```

工具：https://www.qr-code-generator.com/

---

## 关键帧截图

从视频中提取关键帧（PNG 格式），用于论文图表：

```powershell
# 使用 FFmpeg 提取第 3 秒帧
ffmpeg -i v10_rolling_foot_walk.mp4 -ss 00:00:03 -vframes 1 v10_keyframe_3s.png
```

建议关键帧：
- V10: 0:04（稳定行走）
- V13.7（无补偿）: 0:01（跌倒前）
- V13.7（有补偿）: 0:04（稳定行走）
- V17: 0:05（展示估计误差叠加）

---

## 版权与引用

所有视频属于 hw-1 项目，用于学术出版和教育目的。

建议引用格式：

```
Duan, Z. (2026). HW-1 Quasi-Passive Biped Walking - Video Supplement. 
Available at: [YouTube/GitHub URL]
```

---

## 更新日志

- **2026-06-04**：初始视频索引创建，包含 V05/V10/V13.6/V13.7/V16/V17
- **待补充**：V18-V20（3D 探索，如有可视化）
- **待补充**：V22 硬件设计动画（CAD 装配过程）

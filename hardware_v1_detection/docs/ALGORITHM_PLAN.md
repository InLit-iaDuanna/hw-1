# 硬件 V1 — 核心算法落地计划

**状态**：计划确定（待实现）
**日期**：2026-06-13
**定位**：偏瘫步态**检测**设备的 PC 侧算法栈 —— 从 IMU 原始计数到临床报告
**前置**：6×BMI160（双足/双小腿/双大腿）+ 骨盆 BMX055，200 Hz，单时间基，`raw.npz` 已落盘

> **范围红线**：V1 只做检测。本文档所有算法仅用于**评估/出报告**，不产生任何作用于患者的控制输出。

---

## 0. 两项已定决策（2026-06-13）

1. **加双大腿 IMU（6×BMI160）** → V1 直出**完整 sagittal 关节角**：
   - 膝角 = 大腿 pitch − 小腿 pitch
   - 髋角 = 大腿 pitch − 骨盆 pitch
   - 踝角代理 = 小腿 pitch − 足 pitch
2. **临床层基准用文献正常值**，不用 V10 仿真值（stride 1.2–1.4 m / cadence 100–120 steps/min / knee ROM ~60° / hip ROM ~40° / ankle ROM ~25°）。分类规则（SI 阈值、ROM 比例、患侧判定）沿用 `gait_medical_system` 现有实现。

---

## 1. 五层流水线总览

数据从原始 IMU 计数到临床报告穿过 5 层，每层产出独立中间文件，层间解耦、可单独验证。

```
raw.npz  (45×int16, 已有)
   │
 [L0] 标定层   去偏置 + scale + 安装姿态对齐      → calibrated.npz
   │
 [L1] 姿态层   节段 pitch（互补滤波）+ 关节角      → segments.npz
   │
 [L2] 事件层   heel-strike / toe-off 检测         → events.csv      ★命门
   │
 [L3] 指标层   关节角 ROM / 对称性 / 周期 / 相位差  → metrics.json
   │
 [L4] 临床层   偏瘫分类 + 患侧 + 跌倒风险 + 建议    → report.json
```

**关键判断**：L2 事件层是 V1 的命门。无 FSR 时，所有时空对称性指标都依赖 IMU 自检 heel-strike/toe-off。这一层准，后面全准；这一层抖，后面全废。落地路线上要最早、最独立地把它验证掉。

---

## 2. 各层算法选型 + 复用映射

### L0 标定层
| 子项 | 方法 | 来源 |
|---|---|---|
| 陀螺零偏 | 静置均值，存 raw counts | **已有** `calibration/calibrate_static.py` |
| 加速度零偏+scale | 六面静置最小二乘 `a_meas = S·a_true + b` | **新写**，格式抄 V23 辨识工作流 |
| 磁力计硬铁/软铁 | 椭球拟合（仅骨盆 BMX055） | **新写** |
| IMU 安装姿态对齐 | 直立站姿下用重力定竖直轴 → 解传感器轴→解剖轴旋转 R | **新写**，出关节角的前提 |

### L1 姿态层（新写，但简单）
- 只做 **sagittal 平面 pitch**，不做全 3D 四元数 —— 偏瘫核心指标都在矢状面，够用且鲁棒
- 互补滤波 `pitch = α·(pitch + ω·dt) + (1-α)·atan2(a)`，α≈0.98；比 Madgwick 简单、无收敛问题、对 200 Hz 足够
- 骨盆 BMX055 额外用磁力计出绝对 yaw，做左右坐标对齐锚点
- 关节角由节段角差直出（见 §0 决策 1），6 IMU 齐全后膝/髋/踝全可算
- 可选平滑：对节段角接 V17 `JointKalmanFilter`（2 状态常速度 KF），降抖

### L2 事件层（新写检测器 + 复用 FSM）★技术风险最高
- IMU heel-strike：足部 `|a|` 撞击峰值 + 足部陀螺 pitch 过零（摆动末期 ω 第一次回正）双判据
- IMU toe-off：足部陀螺 pitch 正向峰值
- 检测器输出 0/1 contact → 灌进 **`hardware_ready_controller/phase_fsm.py`**（4-phase FSM）+ **`common/simulation_framework.update_contact_state()`**（35 ms 防抖，220 ms 最小间隔）
- 边沿检测复用 `analysis_pipeline/feature_extractor.py` 的 `detect_heel_strikes/toe_offs`

### L3 指标层（大部分复用）
| 指标 | 来源 |
|---|---|
| 左右对称性（Robinson SI） | **直接复用** `gait_medical_system/diagnosis/stroke_gait_classifier.py` |
| 步态周期 / duty factor / 双支撑比 | **复用** `analysis_pipeline/feature_extractor.py`，补左右独立计算 |
| 周期重复性 / 稳定性 | **直接复用** `common/poincare_analyzer.py`（原生 `mode="heel_strike"`），Floquet \|λ\| 作客观稳定性指标 |
| foot drop 角 | heel-strike 时刻足部 pitch，L1+L2 出来后直接算 |
| 关节角 ROM（膝/髋/踝） | 由 L1 关节角逐周期取峰峰值 |

### L4 临床层（直接复用，仅换基准值）
- `stroke_gait_classifier.py`：对称性分级、患侧判定、膝异常、跌倒风险、康复建议 —— **整套直接用**
- `baseline_extractor.py`：**唯一改动** —— 健康基准换文献正常值（见 §0 决策 2）

---

## 3. 复用账本（工作量一眼清）

| 层 | 直接复用 | 改写复用 | 必须新写 |
|---|---|---|---|
| L0 标定 | 陀螺零偏 | — | 加速度/磁力计标定、安装姿态对齐 |
| L1 姿态 | — | V17 `JointKalmanFilter`（可选） | 互补滤波 pitch + 关节角 |
| L2 事件 | FSM、接触防抖、边沿检测 | `ContactDetector`（力→IMU） | **IMU HS/TO 检测器** |
| L3 指标 | Poincaré、对称性公式 | feature_extractor 补左右 | foot drop 角、逐周期 ROM |
| L4 临床 | 整个分类器 | — | 换基准值 |

新写量集中在 **L0 标定**与 **L2 事件检测器**两块，其余靠现有资产拼装。

---

## 4. 落地里程碑（4 阶段，逐层验收）

```
M1 链路+标定  烧固件 → 60s 采集验链路 → L0 全套标定
             验收：静态 |a|≈1g，pitch 漂移 <1°/min，crc_errors≈0，mcu_rate≈200Hz

M2 事件检测   L1 pitch+关节角 → L2 HS/TO 检测器                       ★命门
             验收：与视频/秒表对齐，事件时间误差 <50 ms

M3 指标       L3 对称性/ROM/周期/foot drop
             验收：健康受试者 SI<10%，周期 CV 合理，关节角 ROM 接近文献

M4 临床报告   L4 接分类器（文献基准）
             验收：能出"偏差+患侧+风险+建议"报告
```

每个里程碑产出独立中间文件，失败能定位到层。**M2 是技术风险最高点**：拿到硬件后第一时间用健康人 + 视频对照专攻这一关。过不了就回头考虑加 FSR（ADS1115 与接口已预留）。

---

## 5. 中间文件契约（接在现有 session.py 输出之后，不改其契约）

| 文件 | 产出层 | 内容 |
|---|---|---|
| `raw.npz` | 已有 | `seq[N], ts_us[N], status[N], values[N,45], sensor_names[7]` |
| `calibrated.npz` | L0 | 去偏置+scale 后的 a/ω（工程单位）+ 安装对齐旋转 R |
| `segments.npz` | L1 | 7 节段 pitch + 膝/髋/踝关节角 + 骨盆 yaw |
| `events.csv` | L2 | 逐侧 heel-strike / toe-off 时间戳 + phase 标签 |
| `metrics.json` | L3 | 对称性、相位差、duty factor、ROM、foot drop、Floquet \|λ\| |
| `report.json` | L4 | 偏瘫分级、患侧、跌倒风险、康复建议 |

---

## 6. 已知风险与预案

1. **L2 IMU 事件检测精度不足** → 预案：加 FSR 鞋垫（ADS1115 已留），提供足底压力真值
2. **安装姿态漂移**（绑带松动改变 IMU 朝向） → 每次采集前做一次直立站姿重标定 R
3. **磁力计受布线/电池干扰** → 标定远离金属；yaw 仅作左右对齐锚点，不作主指标
4. **长 session 内存增长**（session.py 全量留内存） → 复诊级长采集需改内存映射/分段写
5. **临床口径错配** → 报告须标注"工程估计指标，非医学诊断"；基准用文献值并注明来源

---

## 7. 下一步

待硬件到位后按 M1→M4 推进。先实现 L0+L2 两块新写量，其余拼装现有资产。固件和 PC 协议已按 V1 最终形态对齐为 `HWV1_BMI_SENSOR_COUNT=6`、payload `45×int16`、`SENSOR_NAMES=7`。

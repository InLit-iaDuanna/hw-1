# V13.6 — 事件驱动 FSM hip 控制律

**状态**：tier B（部分恢复，4/36 = 11.1%；vs V10 16.7%、plan C 0.0%）
**日期**：2026-05-28
**定位**：V13.5 三方案否决后的修正版本（在 V14 之前插入）。**准被动**（hip 主动 FSM + knee PD + ankle 被动），不是纯被动也不是鲁棒控制器。

## 1. 设计动机（一句话）

V13.5 三方案（A 步周期前馈 / A' 提力矩限幅 / C 能量整形 bang-bang）均被实验否决。
教训：V10 稳定性来自 hip 力矩 ⊗ 触地相位的**隐式时序锁定**——任何"单一标量目标"压成一维都会丢失稳定信息。
V13.6 的应对：把 V10 的隐式 bang-bang **解构成 4 段显式 phase**，每段独立的 (k_E, k_PD, τ_max) 三元组，使时序锁定从隐式变显式、可读、可调。

## 2. FSM 状态与切换

### 状态

| state | 相位 u | 适用腿 | 临床步态周期对位 |
|---|---|---|---|
| `stance_early`  | [0.0, 0.5] | 支撑腿 | Loading Response + Mid-Stance |
| `stance_late`   | [0.5, 1.0] | 支撑腿 | Terminal Stance + Pre-Swing |
| `swing_thrust`  | [0.0, 0.5] | 摆动腿 | Initial Swing |
| `swing_retract` | [0.5, 1.0] | 摆动腿 | Mid Swing + Terminal Swing |

### 切换条件

- `stance_*` ↔ `swing_*` ：由 `accepted_contact` 触发（V10 已有的 `stable_contact_time` 0.035 s + `min_event_interval` 0.22 s 抗抖）；接触切换时同时复位 `burst_start_t`，让 phase 内相位 `u = (t - burst_start_t)/gait_period` 重新归 0。
- `stance_early` → `stance_late` ：`u ≥ 0.5`
- `swing_thrust` → `swing_retract` ：`u ≥ 0.5`
- 异常保护：`hip_clearance < recovery_clearance`（髋部过低疑似跌倒）时强制 stance phase 退回 `stance_early`，关闭 push-off 推力。

### 传感器映射（康复设备应用对位）

- 接触切换：鞋底压力开关阈值（脚跟/前掌/趾区分可丰富 phase 内时序细化）
- 相位 u：内部计时器 + 接触事件复位（IMU 步频估计可作 redundancy）
- clearance：髋部 IMU 高度积分
- 整机能量 E：mass × (KE + PE)，由肢段 IMU 估算（康复设备实测时可用关节编码器代替）

## 3. 控制律实现

### Phase-local 力矩

```
e_q = target(u) - q_hip                # target 用 V10-style smoothstep 连续轨迹（避免 phase 切换时刻的目标阶跃）
PD  = k_PD * e_q - kd * qdot
若 k_E == 0 :
    τ = clip(PD, -τ_max, +τ_max)        # 纯 PD phase（stance_*, swing_retract）
若 k_E  > 0 :
    e_E = E_target - E_current
    A   = clip(k_E * max(0, e_E), 0, τ_max)
    sgn = sign(e_q)
    α   = smoothstep((u - 0.85)/0.15)   # 末段 PD 平滑过渡（u>0.85 渐入）
    τ   = clip(A*sgn + α*PD, -τ_max, +τ_max)
```

knee 沿用 V10 PD（V13 切片确认 knee 不是孤立点的主因）；ankle 仍被动弹簧阻尼。

### 为什么 target 不 phase-local

最初设计是每 phase 各自的 `target_deg`，但 smoke 测试显示 phase 切换瞬间的目标阶跃（4° → 22° / -22° → 20°）会破坏 V10 的 smoothstep 时序锁定，baseline 即摔。改为：**phase 只控制"力如何作用"，目标轨迹由整体步态时序决定**——这与临床直觉一致（医生调节"该相位用多大力"，目标轨迹不分段）。

### 默认参数（baseline 通过验证）

| phase | k_E | k_PD | τ_max | kd | E_target |
|---|---:|---:|---:|---:|---:|
| stance_early  | 0.0 | 30 | 4 | 6 | — |
| stance_late   | 0.0 | 30 | 4 | 6 | — |
| swing_thrust  | 7.5 | 10 | 4 | 6 | 52.66 J |
| swing_retract | 0.0 | 30 | 2 | 6 | — |

（E_target 来自 V13b Floquet 测得的极限环能量 52.66 ± 0.53 J。）

## 4. 实验结果

### Step A — Baseline 验证（V10 几何 slope=0, foot_radius=0.04, leg_scale=1.0, duration=12 s）

| 指标 | 值 |
|---|---|
| success | True |
| alternating touchdowns | 11 |
| forward distance | 4.86 m |
| simulated time | 11.99 s |
| input energy | 17.45 J |
| **CoT** | **0.072** |
| phase transitions | 22 |
| failure | completed |

phase 时间占比（左右合并）：stance_early 4.34 s / stance_late 7.66 s / swing_thrust 4.34 s / swing_retract 7.66 s（后段更长是因为 stance_late 包含 push-off 准备段，与 u=0.5 切换点保持一致）。

### Step B — V13 切片 C 同栅格复扫（foot_radius × leg_scale, 6×6 = 36 点，每点 12 s）

**V13.6 = 4/36 = 11.1%**

成功格（V13.6）：(0.038, 1.020), (0.042, 0.980), (0.042, 1.020), (0.042, 1.060) — 中等 foot_radius / 中-长 leg_scale 集中带。

**失败模式分布**：
- fall_down 23 (63.9%)
- stuck 9 (25.0%)
- completed (success) 4 (11.1%)
- 无 nan / fly_away

### Step C — V10 / plan C / V13.6 横向对比

| 控制器 | 切片 C 成功 | 成功率 | Δ vs V10 | 主要失败 |
|---|---:|---:|---:|---|
| **V10 baseline PD** | 6/36 | 16.7% | — | stuck 16, fall 14 |
| V13.5 plan C (能量整形 bang-bang) | 0/36 | 0.0% | −16.7 pp | fall 主导 |
| **V13.6 FSM (本版)** | 4/36 | **11.1%** | **−5.6 pp** | fall 23, stuck 9 |

成功格分布注意：V10 成功在 (0.034/0.038, 短腿) 与 (0.046, 长腿) 两个**对角带**；V13.6 成功在中央 (0.038-0.042, 1.0±) **方块区**——FSM 的可行域在几何上**位置不同**，不是 V10 集合的子集。说明 FSM 没简单复刻 V10 极限环，而是切到另一邻近极限环。

## 5. 决策（按任务定义档位）

| 档位 | 切片 C 成功率 | 适用 | 下一步 |
|---|---|---|---|
| A ≥ 17% | — | — | — |
| **B 6–16%** | **11.1%（本版）** | **路线正确但参数未调优** | **进 V13.6.1：每 phase 上独立 grid search（k_E, k_PD, τ_max）扩到 ≥V10 的 17%** |
| C 0–5% | — | — | — |

→ **决策档：tier B。** V13.6.1 推荐方向：
1. 在 4 个成功格的 (foot_radius, leg_scale) 邻域上对 swing_thrust 的 (k_E, k_PD, E_target) 做 5×5 grid search
2. 单独评估 stance_late 的 τ_max 提到 5–6 是否能挽回 V10 在 (0.046, 长腿) 的成功带
3. 若 17% 不达标但稳定地停在 11–14%，再考虑模仿学习路线 V13.7

## 6. 学术诚信口径

- V13.6 是**准被动**（hip + knee 主动 FSM）——与 V10/V13.5/V14 同档，**不可写"纯被动"**。
- "事件驱动 FSM"**不是鲁棒控制器**——切片 C 11.1% < V10 16.7%，未达 V10 水平。
- baseline 通过 ≠ 鲁棒；V13.5 plan C 也通过了 baseline 但切片 0/36。**判定鲁棒性必须看切片 C**。
- 康复设备应用对位是**设计意图**而不是临床验证；任何"用于康复"的表述需限定为"对位明确，未临床测试"。
- V13.6 解决了 plan C 的能量稳态破坏步态时序问题（11.1% > 0%），但**没有完全恢复**到 V10 的孤立点集合（11.1% < 16.7%），符合 §10.2 教训"FSM 是正确路线但需独立调参"。

## 7. 文件清单

- `simulate_v13_6.py` — FSM 控制律 + 仿真主入口
- `view_v13_6.py` — mujoco 交互式回放
- `render_v13_6.py` — mp4 渲染（叠加 phase 标注）
- `analyze_v13_6.py` — 步态分析报告（5 子图）
- `scan_v13_6_C.py` — V13 切片 C 同栅格 6×6 复扫
- `out/v13_6_baseline_*` — baseline 数据（CSV / phases / summary / report PNG / mp4）
- `out/v13_6_C_foot_leg.csv` — 36 点扫描原始数据
- `out/v13_6_C_heatmap.png` — 成功 / 触地数热图
- `out/v13_6_vs_v10_planC.json` — 三列横向对比

## 8. 复现命令

```powershell
cd D:\Dunna\Documents\hw-1\v13_6_event_driven_fsm
..\.venv-mujoco\Scripts\python.exe simulate_v13_6.py --duration 12 --save-prefix v13_6_baseline
..\.venv-mujoco\Scripts\python.exe analyze_v13_6.py
..\.venv-mujoco\Scripts\python.exe render_v13_6.py
..\.venv-mujoco\Scripts\python.exe scan_v13_6_C.py --grid 6 --duration 12
```

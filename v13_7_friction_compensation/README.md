# V13.7 — Friction Compensation（前馈库仑摩擦补偿）

**非纯被动（准被动 + L1 电机模型 + 前馈补偿）**

## 版本定位

V13.7 在 V16 揭示的 FSM-摩擦共振问题基础上，验证前馈补偿策略：在 FSM 输出端加 `τ_C_eff·sign_smooth(ω_joint)` 前馈项，精确对消电机内部库仑摩擦，使 MX-64AR 电机从 V16 失败带完全恢复行走能力。

**关键成果**：V13.7 验证通过后，V16 升级为 `motor_dynamics_compatible_with_friction_compensation`，V17 状态估计启动条件具备。

## 核心思路

V16 揭示 FSM 与库仑摩擦 τ_C 形成非单调耦合共振，MX-64AR spec τ_C=0.20 N·m 落入失败带。
V13.7 的前馈补偿策略是：在 FSM 控制律输出后、送入电机模型前，加一个等大反号的补偿力矩，
精确对消电机内部扣减的库仑摩擦项。

```
τ_compensated = τ_fsm + τ_C_eff · sign_smooth(ω_joint, ε)
```

**物理原理**：库仑摩擦是确定性的、方向依赖的力，可通过前馈精确补偿。补偿后电机看到的净扭矩等于 FSM 期望输出，恢复 V14c 的理想力矩源特性。

## 实验设计

### Smoke 测试（4 档对照）
1. **compensated_mx64ar**：补偿 + MX-64AR（核心验证）
2. **no_comp_mx64ar**：不补偿 + MX-64AR（与 V16 一致，应失败）
3. **compensated_ideal**：补偿 + 理想电机（退化对照，应还原 V14c）
4. **no_comp_ideal**：理想电机基准

### τ_C 全网格验证
τ_C_eff ∈ {0, 0.013, 0.034, 0.10, 0.20, 0.27, 0.68, 1.7, 3.0} × {raw, compensated} = 18 格
- **raw**：V16 原配置（验证失败带再现）
- **compensated**：加补偿（验证修复效果）

### 期望结果
- `compensated_mx64ar`: success=True, forward ≈ 4.6 m（与 V14c 一致）
- `no_comp_mx64ar`: success=False（与 V16 mx64ar_full 一致）
- `compensated_ideal`: 严格还原 V14c（0% 偏差）

## 关键发现

### Smoke 测试结果

| 配置 | success | alt_td | forward (m) | CoT_mech | 对比 |
|---|---|---|---|---|---|
| **compensated_mx64ar** | ✓ | 10 | **4.63** | 0.066 | 核心验证通过 |
| no_comp_mx64ar | ✗ | 4 | 0.19 | - | 与 V16 一致 |
| compensated_ideal | ✓ | 10 | 4.62 | 0.064 | V14c 退化对照 |
| no_comp_ideal | ✓ | 10 | 4.62 | 0.064 | 基准 |

**关键观察**：
- **完全恢复**：compensated_mx64ar forward=4.63m（V16 无补偿 0.19m → 24× 改善）
- **CoT 增量可接受**：0.066 vs V14c 0.064（+3%，补偿开销）
- **ec_i40 也通过**：τ_C_eff=0.10 补偿后 10/10 全成功

### τ_C 全网格验证结果

| τ_C_eff (N·m) | raw | compensated |
|---|---|---|
| 0.000 | ✓ | ✓ |
| 0.013 | ✗ | ✓ |
| 0.034 | ✓ | ✓ |
| 0.10 | ✗ | ✓ |
| **0.20 (MX-64)** | ✗ | **✓** |
| 0.27 | ✓ | ✓ |
| 0.68 | ✗ | ✓ |
| 1.7 | ✗ | ✓ |
| 3.0 | ✗ | ✓ |

**统计**：补偿版 10/10 全通过，V16 失败带 6 点全部修复。

## Verdict

**Primary**：`friction_compensation_full_recovery`

补偿后完全恢复 V14c 水平，MX-64AR 可用于硬件落地。

**V16 升级**：`motor_dynamics_compatible_with_friction_compensation`

**V17 启动条件具备**：稳定控制律 + 电机模型已验证，可进入传感器闭环状态估计。
## 脚本与运�?
| 脚本 | 用�?|
|---|---|
| `simulate_v13_7.py` | 核心仿真（V13.6.1 FSM + L1 电机 + 前馈补偿�?|
| `smoke_v13_7.py` | 4 档对�?smoke（补�?不补�?× mx64ar/ideal�?|
| `analyze_v13_7.py` | 汇�?verdict + V16 升级判定 |
| `render_v13_7.py` | 离线 MP4 渲染（带 HUD 标注�?|
| `view_v13_7.py` | 交互�?MuJoCo 查看�?|

```powershell
cd D:\Dunna\Documents\hw-1

# 4 �?smoke（~2 min�?.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\smoke_v13_7.py

# τ_C 全网格验证（18 格，~4 min�?.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\scan_v137_comp_matrix.py

# 分析 verdict
.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\analyze_v13_7.py

# 渲染对比 MP4（需 smoke 产物�?.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\render_v13_7.py --tag v13_7_smoke_compensated_mx64ar
.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\render_v13_7.py --tag v13_7_smoke_no_comp_mx64ar

# 交互查看
.\.venv-mujoco\Scripts\python.exe .\v13_7_friction_compensation\view_v13_7.py --motor-preset mx64ar --compensate
```

## 输出产物

- `out/smoke_v137_table.json`�? �?smoke 结果汇�?- `out/scan_v137_comp_matrix.json`：τ_C 全网格验证（18 格）
- `out/v137_verdict.json`：综合判�?+ V16/V17 升级决策
- `out/v137_smoke_compensated_mx64ar.mp4`：补偿版行走动画
- `out/v137_smoke_no_comp_mx64ar.mp4`：无补偿对照（失败）
- `out/v137_comp_vs_raw_comparison.png`：补偿效果对比图

## 依赖关系

- **基于**：V16（L1 电机模型�? V14c（V13.6.1 FSM�?- **为何铺路**：V17 状态估计（稳定控制律前提）、V22 硬件设计（MX-64AR 可用性确认）

## 与后续版本的关系

### V17 状态估�?V13.7 提供稳定的摩擦补偿控制律，V17 在此基础上加入传感器噪声�?Kalman 滤波�?
### V22 硬件设计
V13.7 确认 MX-64AR 可用（通过补偿），�?V22 电机选型提供最终验证�?
## 报告表述

V13.7 应表述为"准被�?+ 真实电机动力�?+ 前馈摩擦补偿"，强调：
- 库仑摩擦补偿是确定性前馈，不是反馈自适应
- 补偿�?CoT 增量 ~3%（可接受的控制开销�?- MX-64AR 在补偿下完全恢复 V14c 性能

**不可声称**�?- 自适应控制或学习控制（这是确定性前馈）
- 消除所有电机非理想性（仅补偿库仑摩擦，粘滞摩擦和惯量仍存在�?

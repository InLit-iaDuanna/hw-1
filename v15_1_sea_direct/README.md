# V15.1 SEA Direct-Drive（串联弹性驱动器 - 扭矩直传模式）

**非纯被动（准被动 + SEA + FSM 扭矩控制）**

## 版本定位

V15.1 是首个成功的 SEA（串联弹性驱动器）实现版本。采用 motor body + series hinge spring 拓扑，FSM 扭矩直传电机，成功复现 V14c 稳定性并在柔性弹簧配置下展现更优性能。

**关键修正**（相对 V15.2）：
1. `_FsmDataView` 喂入绝对髋角度（`q_motor + q_link`）而非相对角度
2. 去除 Pratt 内环，FSM 扭矩直传（ctrl_limit = 4 N·m）

## SEA 架构说明

```
hip body
+-- left_motor_rotor (I_yy=0.002 kg·m², mass=0.01 kg)
|   +-- joint: left_hip_motor (actuated, ±4 N·m)
|   +-- left_thigh
|       +-- joint: left_hip_link (stiffness=k_sea, damping=c_sea, springref=0)
|       +-- left_shank -> foot
```

**弹簧力模型**：`F_spring = -k_sea * q_link - c_sea * qd_link`

**退化特性**：k_sea → ∞ 时，q_link → 0，系统退化为 V14c 刚性连接。

## 与 V15.2 的关键区别

V15.2 失败的原因：
- `_FsmDataView` 仅喂入 `q_link`（相对角度 ~0.05°）→ FSM 误判髋关节不动
- Pratt 内环（Kp=1000, motor_ctrl_limit=30 N·m）与 FSM 事件驱动逻辑冲突

V15.1 的修正：
- FSM 看到绝对角度（motor + link 总和）
- 电机直接接收 FSM 扭矩指令（无内环干扰）

## 实验设计

### 参数扫描
- **弹簧刚度**：k_sea ∈ {500, 1000, 5000, 10000} N·m/rad
- **几何参数**：切片 C（foot_radius × leg_scale 6×6 网格）
- **控制律**：完全继承 V14c（V13.6.1 best FSM + arm_mass=0.01）

### 验证目标
1. **退化对照**：k_sea=10000（刚性）必须精确复现 V14c
2. **柔性探索**：k_sea=500-1000 区间寻找最优配置
3. **稳定性验证**：切片 C 成功率 ≥ V14c（5/36 = 13.9%）

## 关键发现

**Verdict**：`v151_sea_direct_preserves_v14c_stability`

### 退化测试（k_sea=10000）
| 指标 | V15.1 | V14c | 偏差 |
|------|-------|------|------|
| forward | 4.87 m | 4.62 m | +5.6% |
| alt_td | 11 | 10 | +1 |
| success | True | True | ✓ |

**结论**：刚性弹簧配置成功复现 V14c，实现正确。

### 切片 C 扫描结果
| k_sea (N·m/rad) | 成功率 | 最佳 forward |
|----------------|--------|-------------|
| 500 | 3/36 (8.3%) | **4.92 m** |
| 1000 | 4/36 (11.1%) | 跌倒（共振带）|
| 5000 | 5/36 (13.9%) | 4.85 m |
| 10000 | 5/36 (13.9%) | 4.87 m |

**关键发现**：
- **k=500 在最佳格 (foot=0.042, leg=1.02) 达到 forward=4.92 m**（优于 V14c 4.62 m）
- 弹簧偏转量 ~1.6°（可视化明显）
- k=1000 存在共振失败带（类似 V16 τ_C 非单调现象）

### Rotor 参数
- mass=0.01 kg
- I_yy=0.004 kg·m²
- bearing_damping=0.001 N·m·s/rad

## 运行命令

```powershell
cd D:\Dunna\Documents\hw-1
$env:PYTHONIOENCODING='utf-8'

# 单次仿真
.\.venv-mujoco\Scripts\python.exe .\v15_1_sea_direct\simulate_v151.py `
  --k-sea 1000 --foot-radius 0.042 --leg-scale 1.02 --save-prefix v151_test

# Smoke 测试（退化验证 + 刚度扫描）
.\.venv-mujoco\Scripts\python.exe .\v15_1_sea_direct\smoke_v151.py

# 全网格扫描（4 × 6 × 6 = 144 格）
.\.venv-mujoco\Scripts\python.exe .\v15_1_sea_direct\scan_v151_k_geom.py

# 分析与可视化
.\.venv-mujoco\Scripts\python.exe .\v15_1_sea_direct\analyze_v151.py
```

## 输出产物

- `out/smoke_v151_table.json`：退化测试与刚度扫描结果
- `out/v151_C_k_geom.csv`：144 格全网格数据
- `out/v151_scan_status.json`：扫描状态汇总
- `out/v151_verdict.json`：综合判定结果
- `out/v151_heatmap_*.png`：成功率热力图（按刚度分层）
- `out/v151_*.mp4`：行走动画（HUD 显示弹簧偏转）

## 验证标准

**必须通过**：
- k_sea=1e6 或 10000：success=true，alt_td ≥ 10，forward ~ 4.6 m（±10%）
- 弹簧偏转可视化：k_sea=500 时 spring deflection > 0.5 deg

**成功标准**：
- Grid k=5000: 成功率 ≥ V14c（5/36 = 13.9%）

## 依赖关系

- **基于**：V14c（V13.6.1 best FSM + arm_mass=0.01）
- **修正自**：V15.2（修复 FSM 输入错误 + 移除内环）
- **为何铺路**：V15.1L1（SEA + V16 电机动力学合体）

## 与后续版本的关系

### V15.1L1（SEA + 电机动力学）
V15.1 + V16 合体实验：
- mx64ar_raw k=500: forward=3.96m/9td（V16 rigid 0.19m → 20× 改善）
- mx64ar+V13.7补偿 k=500: forward=4.90m **PASS**
- k=10000+补偿: 失败（刚性弹簧 + J_eff 耦合不稳定）

**推荐配置**：k=500 + V13.7 摩擦补偿

### V16 电机动力学
V15 与 V16 完全解耦（V16 直接 fork V14c），但 V15.1L1 证明 SEA 可部分缓冲电机摩擦影响。

## 报告表述

V15.1 应表述为"准被动 + 串联弹性驱动器（SEA）行走"，强调：
- FSM 扭矩控制模式与 SEA 兼容
- 柔性弹簧（k=500）可改善冲击响应
- 刚性配置（k→∞）精确退化为 V14c

**不可声称**：
- 纯被动行走（hip 和 knee 仍有主动控制）
- SEA 提供被动稳定性（弹簧仅做缓冲，稳定性来自 FSM）

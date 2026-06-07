# V16 — Motor Dynamics（L1 一阶电机动力学）

**非纯被动（准被动 + 真实电机模型）**

## 版本定位

V16 在 V14c 稳定基线上引入 L1 一阶电机模型（转子惯量 + 库仑/粘滞摩擦 + 电流饱和），验证 V13.6.1 best FSM 在硬件实参下的工作性。控制律完全不动，仅替换"理想力矩源"为可参数化的真实电机层。

**关键发现**：MX-64AR 电机的库仑摩擦（τ_C=0.20 N·m）与 FSM 形成非单调耦合共振，导致控制失效。

## 与 V15 的关系

V15（hip SEA）由另一窗口并行推进，V16 与之**完全解耦**——直接 fork V14c，不依赖 V15 的 SEA 模型。这样设计可以：
1. 独立验证电机动力学影响
2. 避免 SEA + 电机双变量耦合的复杂性
3. 为后续 V15.1L1（SEA + 电机）提供清晰对照

V15.0 PEA 已实测打破 V14c FSM 工作点，V15.1 真 SEA 修正后，可考虑 V16+V15 协同版（V15.1L1）。

## L1 电机模型

### 公式

```
1. τ_sat = N · η · Kt · I_max                  # 关节侧饱和扭矩
2. τ_after_sat = clip(tau_desired, ±τ_sat)
3. τ_friction_C = τ_C_motor · N · η · sign_smooth(ω_joint, ε=0.01)
4. τ_out = τ_after_sat - τ_friction_C
```

粘滞摩擦 `b·N²` 加到 XML `<joint damping>`，转子惯量 `J_rotor·N²` 加到 XML `<joint armature>`，由 MuJoCo 隐式积分器一次性处理（dt=1 ms 不变，无 sub-step）。

### 电机预设库（`common/motor_dynamics.py:PRESETS`）

| 预设 | 型号 | J_eff (kg·m²) | b_eff (N·m·s/rad) | τ_C_eff (N·m) | τ_sat_peak (N·m) |
|---|---|---|---|---|---|
| `ideal` | 退化对照（J=b=τ_C=0, I_max=∞） | 0 | 0 | 0 | 1e9 |
| `mx64ar` | Dynamixel MX-64AR @12V (200:1) | 2.8e-3 | 0.050 | **0.20** | 5.99 |
| `ec_i40_53` | Maxon EC-i 40 70W + GP32 53:1 | 9.4e-3 | 0.011 | 0.11 | 13.46 |

## 实验设计

### Smoke 测试（5 档预设）
1. **ideal**：退化对照（必须 0.0% 偏差复现 V14c）
2. **mx64ar_J_only**：仅转子惯量
3. **mx64ar_friction**：惯量 + 摩擦（无电流限制）
4. **mx64ar_full**：完整 MX-64AR 模型
5. **ec_i40_53_full**：Maxon 电机对照

### τ_C 临界扫描
固定 mx64 的 J/b/τ_sat，仅变化 τ_C_motor ∈ [0, 3.0] N·m（10 档），找出成功/失败边界。

### 控制变量
- 几何参数固定：arm_mass=0.01, foot_radius=0.042, leg_scale=1.02（V14c 最佳格）
- 控制律不动：V13.6.1 best FSM
- sign_smooth 的 ε 扫描 {0.001, 0.01, 0.05} 验证物理性

## 关键发现

### Smoke 测试结果（baseline 工作格）

| preset | success | alt_td | forward (m) | mech (J) | failure |
|---|---|---|---|---|---|
| `ideal` | ✓ | 10 | 4.617 | 16.236 | completed |
| `mx64ar_J_only` | ✓ | 10 | 4.594 | 16.145 | completed |
| `mx64ar_friction` | ✗ | 4 | 0.190 | 3.358 | fall_down |
| `mx64ar_full` | ✗ | 4 | 0.189 | 3.390 | fall_down |
| `ec_i40_53_full` | ✗ | 3 | 0.192 | 3.571 | stuck |

**关键观察**：
- **L0 退化对照严格通过**：`ideal` 与 V14c 0.0000% 偏差（13 位小数精度）
- **L1 健康检查失败**：`mx64ar_full` forward 偏差 95.9%（fall_down）
- 摩擦项是支配主因（friction_only 与 full 几乎相同）
- 转子惯量单独影响 0.5%（不致命）

### τ_C 临界扫描结果（非单调！）

| τ_C_eff_joint (N·m) | success | forward (m) | 区间 |
|---:|:---:|---:|---|
| 0.000 | ✓ | 4.630 | **成功带** |
| 0.013 | ✗ | 0.163 | 失败带开始 |
| **0.034** | ✓ | 4.451 | **成功带恢复** |
| 0.067 | ✗ | 0.174 | 失败带 |
| 0.101-0.201 | ✗ | 0.17-0.19 | **MX-64 落在此** |
| **0.268** | ✓ | 3.732 | **成功带恢复** |
| 0.402+ | ✓ | 3.890+ | 成功带 |

**核心发现**：
- **非单调性**：成功带 {0, 0.034, ≥0.27} N·m，失败带 [0.013, 0.20] N·m
- **MX-64AR spec τ_C_eff = 0.20 N·m 落入失败带正中央**
- sign_smooth 的 ε 在 {0.001, 0.01, 0.05} 50× 范围内 verdict 不变 → **物理共振，非数值伪影**

## Verdict

**Primary**：`motor_dynamics_breaks_fsm_revisit_control`  
**Sub-finding**：`tau_C_FSM_resonant_coupling_non_monotonic`

τ_C 与 FSM 的耦合不是单调的摩擦增大→性能下降，而是特定频段的共振破坏了 FSM 的相位时序。这是 V13.6.1 FSM 设计时未预见的物理约束。

## V22 硬件选型约束

V16 揭示的非单调共振现象意味着：**不可按上界保证选型，必须 FSM 实测**。

三条可行路径：

### 路径 1：低摩擦方案
选 `τ_C_eff < 0.013 N·m` 的关节模组
- 双 BLDC + 谐波减速器
- τ_C_motor ≈ 1e-4 N·m at N=200, η=0.85
- **优点**：避开失败带，无需补偿
- **缺点**：成本高（单关节 >3000 元）

### 路径 2：V13.7 摩擦补偿（推荐）
在 FSM 输出端加前馈补偿：`τ_comp = τ_C_eff·sign_smooth(ω_joint)`
- 验证 MX-64AR spec 下能否恢复 FSM
- **优点**：成本低，MX-64AR 可用
- **结果**：V13.7 已验证通过（10/10 全成功）

### 路径 3：选择恢复带电机
寻找 τ_C_eff 落在 `[0.27, ∞)` 的型号
- 典型直驱电机或低减速比方案
- **优点**：无需补偿
- **缺点**：需更大功率裕度，重量增加

## 运行命令

```powershell
cd D:\Dunna\Documents\hw-1

# 环境（与 V14c 同口径）
.\.venv-mujoco\Scripts\python.exe -m pip install -r v16_motor_dynamics\requirements.txt

# 单次仿真
.\.venv-mujoco\Scripts\python.exe .\v16_motor_dynamics\simulate_v16.py --motor-preset mx64ar

# 5 档 smoke（~60s）
.\.venv-mujoco\Scripts\python.exe .\v16_motor_dynamics\smoke_v16.py

# τ_C 临界扫描（10 档，~2 min）
.\.venv-mujoco\Scripts\python.exe .\v16_motor_dynamics\scan_v16_tauC_critical.py

# 综合 verdict
.\.venv-mujoco\Scripts\python.exe .\v16_motor_dynamics\analyze_v16.py
```

## 输出产物

| 文件 | 说明 |
|---|---|
| `out/smoke_v16_table.json` | 5 档预设 smoke 结果 + verdict |
| `out/scan_v16_tauC_critical.json` | τ_C 单因素扫描（10 档，找临界） |
| `out/v16_verdict.json` | 综合 verdict + V22 选型约束 |
| `out/v16_smoke_*_summary.json` | 单格 summary（含 motor spec / saturation count / phase saturation rate） |
| `out/v16_models/motor_dyn_walker.xml` | 隔离 XML（不污染 V14/V14c/V15） |

## 依赖关系

- **基于**：V14c（V13.6.1 best FSM + arm_mass=0.01）
- **为何铺路**：V13.7 摩擦补偿、V22 硬件选型约束

## 与 ROADMAP 决策门的关系

**V13/V17/V21** 是 ROADMAP 强制决策门。V16 完成后**必须暂停回顾 V17 决策门假设**：
- V17 原假设：加 IMU/编码器噪声 + 状态估计
- V16 揭示：V13.6.1 FSM 在 mx64 spec 下根本不工作
- **决策**：V17 之前先做 V13.7 摩擦补偿，否则 V17 状态估计建立在不稳定控制律上

**实际执行**：V13.7 → V17 顺序调整，V13.7 完成后 V16 升级为 `motor_dynamics_compatible_with_friction_compensation`

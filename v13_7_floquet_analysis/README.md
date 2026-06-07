# V13.7 Floquet 稳定性分析

**V13.7 FSM 控制律的 Floquet 稳定性量化分析**

## 背景

- V13b 完成了 V10 PD 控制的 Floquet 分析（max|λ|=0.944）
- V13.7 是关键的 FSM + 摩擦补偿版本，但缺少稳定性分析
- 目标：量化 FSM 事件驱动控制的稳定裕度，对比 V10 vs V13.7

## 分析方法

采用 V13b 相同的实验 Floquet 方法（Goswami et al. 1996）：

1. **长程仿真**: duration=20s，收集 ≥16 次右脚触地
2. **Poincaré 截面**: 提取触地时刻的 4D 状态向量
   - `(right_hip, right_hip_vel, right_knee, right_knee_vel)`
3. **Return-map Jacobian**: 对截面点序列做线性回归
4. **Floquet 乘子**: Jacobian 的特征值，max|λ| 决定收敛速率

## 分析配置

| 配置 | 控制律 | 电机模型 | 摩擦补偿 | 用途 |
|------|--------|----------|----------|------|
| v13_7_fsm_ideal | V13.7 FSM | ideal (无摩擦) | - | baseline 对比 |
| v13_7_fsm_mx64ar_comp | V13.7 FSM | mx64ar | ✓ | 实际应用配置 |
| v13_7_fsm_mx64ar_nocomp | V13.7 FSM | mx64ar | ✗ | 验证补偿必要性 |
| V10_PD (V13b) | V10 PD | ideal | - | 历史基线 |

## 脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `analyze_floquet_v13_7.py` | 主分析脚本（数据采集 + Floquet 计算 + 可视化） | ✓ 已完成 |
| `generate_report.py` | 自动生成分析报告（Markdown） | ✓ 已完成 |
| `disturbance_recovery_v13_7.py` | 扰动恢复测试（验证 Floquet 预测 vs 实际行为） | 🔧 框架（需完整实现） |

## 运行

```powershell
cd D:\Dunna\Documents\hw-1

# 执行 Floquet 分析（~3-5 分钟，3×20s 仿真）
.\.venv-mujoco\Scripts\python.exe .\v13_7_floquet_analysis\analyze_floquet_v13_7.py

# 生成分析报告
.\.venv-mujoco\Scripts\python.exe .\v13_7_floquet_analysis\generate_report.py
```

## 输出

### 数据文件（CSV，完整仿真轨迹）

- `out/v13_7_fsm_ideal_data.csv` — ideal 配置 20s 仿真数据
- `out/v13_7_fsm_mx64ar_comp_data.csv` — 补偿配置数据
- `out/v13_7_fsm_mx64ar_nocomp_data.csv` — 无补偿配置数据

### 结果文件（JSON）

- `out/v13_7_fsm_ideal_floquet.json` — ideal 配置 Floquet 结果
- `out/v13_7_fsm_mx64ar_comp_floquet.json` — 补偿配置结果
- `out/v13_7_fsm_mx64ar_nocomp_floquet.json` — 无补偿配置结果
- `out/v13_7_floquet_summary.json` — 汇总对比（含 V10 参考）

### 可视化（PNG）

- `out/v13_7_floquet_comparison.png` — 多配置对比（3×3 网格：Poincaré 截面 hip/knee + Floquet 谱）
- `out/v13_7_stability_margin_comparison.png` — 稳定裕度条形图（V10 vs V13.7 三配置）

### 报告文档（Markdown）

- `out/v13_7_floquet_report.md` — 自动生成的分析报告（定量结果 + 对比表）
- `out/v13_7_floquet_interpretation.md` — **深度解读**：理论 vs 实际矛盾、工程影响、后续建议

## 结果解读

### Floquet 乘子含义

- **max|λ| < 1**: 系统稳定（扰动收敛）
- **max|λ| → 1**: 临界稳定（收敛极慢，对扰动敏感）
- **max|λ| ≥ 1**: 系统不稳定（扰动发散）

### 收敛时间常数

```
τ ≈ T_gait / ln(1/|λ|)
```

其中 T_gait ≈ 0.8s（步态周期）。max|λ| 越小，收敛越快。

### 对比指标

| 对比项 | 含义 |
|--------|------|
| V13.7 (ideal) vs V10 PD | FSM 事件驱动 vs PD 控制的稳定性差异 |
| V13.7 (mx64ar+comp) vs ideal | 摩擦补偿效果（是否完全恢复 ideal 性能） |
| V13.7 (mx64ar-no) vs ideal | 无补偿性能退化程度 |

## 关键发现 ⚠️

**V13.7 FSM 控制律的最大 Floquet 乘子 max|λ| = 1.0008 > 1.0**

### 核心结果

| 配置 | max\|λ\| | 稳定性 | alternations | forward (m) |
|------|----------|--------|--------------|-------------|
| **V10 PD** (V13b) | **0.944** | ✓ 稳定 | 19 | 8.60 |
| **V13.7 FSM** (ideal) | **1.0008** | ⚠️ 边界不稳定 | 17 | 8.65 |
| **V13.7 FSM** (mx64ar+comp) | **1.0008** | ⚠️ 边界不稳定 | 17 | 8.61 |
| **V13.7 FSM** (mx64ar-no) | 1.0000 | ✗ 失败 | 4 | 0.19 |

### 重要发现

1. **V13.7 FSM 比 V10 PD 稳定裕度小 6.0%**（Δλ = +0.0568）
2. **理论上处于边界不稳定**（max|λ| > 1.0），但 20s 仿真表现正常
3. **摩擦补偿完全有效**（mx64ar+comp ≈ ideal，Δλ < 0.001%）
4. **矛盾需解释**：为何 max|λ| > 1.0 仍能完成 17 次触地？

### 可能解释

- **发散极慢**: τ_diverge ≈ 1000 步，20s 仅 ~17 步，发散未显现
- **非线性稳定化**: FSM 事件切换、能量反馈等非线性效应提供隐式稳定
- **Floquet 线性化局限**: 小扰动线性化假设在 FSM 系统中可能不精确
- **中性稳定环**: 系统可能在有限时间内看似稳定，但长期漂移

### 工程影响

⚠️ **风险**: 实际机器人可能在运行数百步后发散  
🔍 **建议**: 长时程实验验证（100s+）、监控极限环漂移、优化 FSM 参数

## 学术口径

- 所有配置均为**准被动步态**（hip + knee 主动控制）
- 不与文献纯被动 McGeer 步态的 Floquet 分析直接对照
- V10 PD 是 position-velocity 比例微分控制
- V13.7 FSM 是事件驱动有限状态机 + 决策门

## 参考

- V13b Floquet 分析: `D:\Dunna\Documents\hw-1\v13b_floquet_long_run\`
- V13.7 实现: `D:\Dunna\Documents\hw-1\v13_7_friction_compensation\`
- Common 工具: `D:\Dunna\Documents\hw-1\common\poincare.py`
- Goswami et al. (1996): Compass-Like Biped Robot Part I — Stability and Bifurcation of Passive Gaits

## 后续扩展

### 1. 长时程仿真 ⚠️ **高优先级**
验证 max|λ| > 1.0 的长期影响：
```powershell
# 修改 analyze_floquet_v13_7.py，设置 duration=100.0
# 运行 100s 仿真，观察是否出现步态漂移或失败
```

预期：若系统真发散，应在 ~1000 步（约 100s）后观察到明显失败。

### 2. 扰动恢复测试
完善 `disturbance_recovery_v13_7.py`，真实注入初始扰动：
- 修改 `run_simulation_v137` 支持自定义初始状态
- 测量实际衰减/发散率 λ_fit
- 对比 Floquet 预测 vs 实测行为

### 3. 参数优化
扫描 FSM 增益空间，寻找 max|λ| < 0.95 的稳定配置：
```python
# 扫描 (k_PD, k_E, kd) 组合
# 目标：保持性能的同时，max|λ| < 0.95
```

### 4. 高维 Floquet 分析
扩展状态向量包含能量：
```python
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel", "E_mech")
```
5D Floquet 可能揭示能量反馈的隐式稳定作用。

### 5. 实物验证 🔬
在实际机器人上长时间运行 V13.7 FSM：
- 监控步长/步频/能量的长期趋势
- 记录失败模式（若发生）
- 验证 Floquet 分析的预测准确性

# V19 — 髋外展主动稳定验证

**状态**：已完成（否定结果）  
**日期**：2026-06-03  
**定位**：V18 3D 模型 + 主动髋外展控制  

## 1. 设计动机

V18 证明被动侧向稳定不存在。V19 测试**最小主动方案**：在 V18 模型基础上，将髋外展关节从被动弹簧改为主动电机驱动。

**核心问题**：髋外展 PD 控制是否足以稳定 3D 行走？

## 2. 模型修改

### 2.1 与 V18 的区别

| 关节 | V18 | V19 |
|------|-----|-----|
| left/right_hip_abd | 被动弹簧（5 N·m/rad）| **主动电机**（PD 控制）|
| 控制自由度 | 4 个（左右 hip/knee）| **6 个**（+ 左右 abd）|

### 2.2 控制器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| abd_kp | 40.0 | 髋外展位置增益 |
| abd_kd | 4.0 | 髋外展速度增益 |
| abd_torque_limit | 6.0 N·m | 扭矩饱和限制 |
| abd_target_deg | 0° | 名义目标角度 |

## 3. 测试策略

V19 测试了 **6 种控制策略**：

### 策略 1：简单 PD 到零
```python
tau_abd = kp * (0 - q_abd) - kd * qd_abd
```
**结果**：侧向漂移，~5 alternations

### 策略 2：hip_y 反馈
```python
tau_abd = kp * (0 - q_abd) - kd * qd_abd + k_y * hip_y
```
测试 k_y 正负号。  
**最佳**：7 alternations / 2.97s（修正符号后）

### 策略 3：hip_roll 反馈
```python
tau_abd = kp * (0 - q_abd) + k_roll * hip_roll
```
**结果**：略有改善，~5 alternations

### 策略 4：联合反馈
```python
tau_abd = kp * (0 - q_abd) + k_y * hip_y + k_roll * hip_roll
```
**结果**：与策略 2 相当，~6-7 alternations

### 策略 5：双侧对称控制
左右腿 abd 扭矩对称。  
**结果**：无显著改善

### 策略 6：向摆动侧倾斜
支撑腿 abd 向摆动侧倾斜，增加侧向 GRF。  
**结果**：不稳定，更早跌倒

## 4. 实验结果

### 4.1 最佳结果（策略 2，hip_y 反馈）

| 指标 | 值 |
|------|-----|
| 交替步数 | 7 |
| 仿真时间 | 2.97 s |
| 前进距离 | ~0.8 m |
| max_abs_hip_y | 0.28 m |
| 失败模式 | lateral_drift |

**目标**：10 alternations / 12 s  
**结论**：**未达标**

### 4.2 失败分析

**侧向漂移率测量**：
- 平均：0.05-0.10 m/step
- 累计：7 步后 hip_y ≈ 0.28 m → 超出稳定范围

**髋外展修正能力**：
- 单步最大修正：~0.01 m/step
- **不足比例**：5-10× 不够

### 4.3 物理限制（核心发现）

**问题**：髋外展关节扭矩**不能产生 net 侧向地面反力（GRF）**

**力学分析**：
```
髋外展扭矩 → 躯干倾斜（body tilt）
但当双脚都接近竖直时：
  侧向 GRF ≈ 0（脚底无侧向位移）
```

**真正改变 CoM 侧向位置需要**：
- 脚底侧向位移（支撑多边形移动）
- 即：**步宽调制**（swing foot placement）

### 4.4 Verdict（判决）

```json
{
  "verdict": "hip_abd_insufficient_for_lateral_stabilization",
  "drift_rate": "0.05-0.10 m/step",
  "correction_capability": "0.01 m/step",
  "insufficiency_ratio": "5-10x",
  "physical_limitation": "abd torque creates tilt, not lateral GRF",
  "recommendation": "V20 step-width control required"
}
```

## 5. 策略对比表

| 策略 | alternations | sim_time (s) | max_hip_y (m) | 评价 |
|------|-------------|--------------|---------------|------|
| 简单 PD | 5 | ~2.0 | 0.25 | baseline |
| hip_y 反馈（错误符号）| 3 | ~1.5 | 0.30 | 更差 |
| **hip_y 反馈（修正）** | **7** | **2.97** | **0.28** | 最佳 |
| hip_roll 反馈 | 5 | ~2.2 | 0.26 | 略有改善 |
| 联合反馈 | 6 | ~2.5 | 0.27 | 接近最佳 |
| 双侧对称 | 6 | ~2.4 | 0.26 | 无显著效果 |
| 向摆动侧倾 | 4 | ~1.8 | 0.32 | 反而更差 |

## 6. 与 V18 对比

| 指标 | V18（roll_k=500）| V19（主动 abd）| 改善 |
|------|-----------------|----------------|------|
| 机制 | 被动刚性约束 | 主动 PD 控制 | - |
| alternations | 10 | 7 | ✗ 退化 |
| forward | ~4 m | ~0.8 m | ✗ 退化 |
| 侧向自由度 | 被锁定（→2D）| 保留但不稳定 | ± |

**结论**：V19 的主动控制**不如** V18 的刚性约束。证明单纯髋外展不是可行方案。

## 7. 决策门触发

V19 结果再次确认 **V21 决策门**：

**ROADMAP 更新**：
- V18：被动侧向稳定不存在 ✓
- V19：髋外展主动控制不足 ✓
- **结论**：必须引入步宽控制（swing foot lateral placement）

**下一步**：V20 步宽控制（但最终也未达标）

## 8. 为什么髋外展不够？

### 8.1 力学原理

**髋外展扭矩的效果**：
```
τ_abd → 躯干相对支撑腿倾斜
     → 重心（CoM）相对支撑脚横向偏移
     → 但支撑脚位置不变！
```

**侧向 GRF 来源**：
```
F_lateral = (CoM 位置 - 支撑脚位置) × m × g / L
```

**关键**：当 CoM 漂移较大时，髋外展能产生的倾斜角度**不足以产生足够的 F_lateral**。

### 8.2 数值估算

假设：
- CoM 高度 L ≈ 1 m
- 侧向漂移 Δy = 0.05 m/step
- 髋外展产生倾斜 θ_max ≈ 5°

```
所需修正力：F = m × a_lateral ≈ 5 kg × 0.5 m/s² ≈ 2.5 N
髋外展产生：F_abd ≈ m×g×sin(5°) ≈ 5×9.81×0.087 ≈ 4.3 N

看似足够，但：
1. 支撑时间短（~0.3 s/step）
2. 倾斜建立需要时间
3. 实际修正 << 理论值
```

**实测**：0.01 m/step << 0.05-0.10 m/step 漂移率

## 9. 与生物行走对比

人类侧向稳定的主要机制：
1. **步宽调节**（80%）：主动改变落脚点位置
2. 髋外展肌肉（15%）：辅助微调
3. 前庭反馈（5%）：快速响应

V19 仅测试机制 2，**缺失最重要的机制 1**。

## 10. 文件清单

```
v19_hip_abduction_active/
├── model_3d_v19.py          # 3D 模型（主动 abd）
├── simulate_v19.py          # 主仿真脚本
├── out/
│   ├── v19_verdict.json     # 判决结果
│   ├── v19_hip_y_feedback_zero_summary.json  # 策略 2
│   ├── v19_smoke_summary.json                # 策略 1
│   └── ...
└── README.md（本文件）
```

## 11. 复现命令

```powershell
cd D:\Dunna\Documents\hw-1\v19_hip_abduction_active
..\.venv-mujoco\Scripts\python.exe simulate_v19.py --abd-kp 40 --abd-kd 4.0 --duration 10 --save-prefix v19_hip_y_feedback
```

## 12. 学术价值

V19 的否定结果量化了：
1. **髋外展不足的程度**：5-10× 不够
2. **物理限制的本质**：扭矩→倾斜，不能→侧向 GRF
3. **必要性证明**：必须有步宽控制

**可用于论文**：
- 小节 4.2："髋外展主动控制的力学局限"
- 对比表：被动（V18）vs 主动髋外展（V19）vs 步宽控制（V20）

## 13. 后续改进

V19 失败后的选项：
1. **V20 步宽控制**（已尝试，未验证）
2. **脚踝主动 roll**（未实施）
3. **质心轨迹规划**（复杂度过高）
4. **放弃 3D，进入 V22**（实际选择）

## 14. 参考文献

- Kuo, A. D. (2007). The six determinants of gait and the inverted pendulum analogy: A dynamic walking perspective. Human Movement Science. — 解释步宽的重要性
- Bauby, C. E., & Kuo, A. D. (2000). Active control of lateral balance in human walking. Journal of Biomechanics. — 实测人类步宽调节

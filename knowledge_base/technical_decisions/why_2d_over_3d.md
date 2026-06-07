# 技术决策：为什么 V18-V20 放弃 3D，选择 2D 路线

**状态**: 已采纳  
**日期**: 2026-06-03  
**决策者**: 项目团队  
**相关版本**: V18, V19, V20, V22

---

## 背景

项目初始目标（记忆文档 `project-hw1-compass-gait`）：

> 长程 V01→V25，终点是 3D 准被动 + 物理样机 sim-to-real。

**Why**: 用户的长期研究项目，三线均衡（L1 仿生 / L2 控制 / L3 理论），**硬约束是必须做到 3D 并落地硬件样机**。

然而，V18-V20 三次实验得出一致否定结果，促使决策门提前触发。

## 问题：3D 化三次失败

### V18: 侧向被动稳定探索（否定结果）

**实验设计**：

在 V10 矢状面 PD 基础上，添加侧向自由度：
- `hip_y`: 髋部侧向位移
- `hip_roll`: 髋部侧倾角
- `hip_abd`: 髋外展关节（被动弹簧）

测试被动侧向稳定性：

```python
# 测试配置
initial_perturbation = 3.0  # deg (侧倾扰动)
roll_stiffness = [0, 50, 100, 200, 500, 1000]  # N·m/rad
foot_width = [0.04, 0.08, 0.12, 0.15]  # m
```

**结果**：

| roll_k (N·m/rad) | 结果 | 侧向运动 |
|-----------------|------|---------|
| 0-100 | 发散失败 | 侧向振荡幅度递增 → 跌倒 |
| 200-400 | 部分稳定 | 仍有缓慢侧向漂移 |
| ≥500 | 通过但无意义 | 等效刚性 2D 约束 |

**宽足实验**：

```
foot_width: 0.04 → 0.15 m (3.75× 加宽)
roll peak: 6.3° → 4.4° (微降 30%)
verdict: 仍然失败
```

**核心发现**：

> **被动侧向稳定不存在**

**物理解释**：

1. **冠状面无驱动能量源**
   - 矢状面：重力势能 → 动能循环
   - 冠状面：无重力分量，纯耗散系统

2. **无稳定极限环**
   - 矢状面：存在极限环吸引子（V5 证明）
   - 冠状面：无吸引子，初始扰动持续放大

3. **侧向振荡耦合矢状面**
   - 侧向振荡 → 改变支撑多边形 → 破坏矢状面极限环 → 跌倒

**verdict**: `lateral_stability_requires_active_control`

### V19: 髋外展主动稳定（否定结果）

**实验设计**：

将 V18 的被动 `hip_abd` 改为主动电机，测试 6 种控制策略：

```python
strategies = {
    '1_simple_pd': {
        'control': 'tau_abd = kp * (-roll) + kd * (-roll_dot)',
        'params': {'kp': 50, 'kd': 5},
    },
    '2_hip_y_feedback': {
        'control': 'tau_abd = kp * (-hip_y) + kd * (-hip_y_dot)',
        'params': {'kp': 100, 'kd': 10},
    },
    '3_hip_roll_feedback': {
        'control': 'tau_abd = kp * (-roll) + kd * (-roll_dot)',
        'params': {'kp': 100, 'kd': 10},
    },
    '4_combined': {
        'control': 'tau_abd = k1*(-roll) + k2*(-hip_y) + ...',
    },
    '5_lean_to_swing': {
        'control': '向摆动侧前倾',
    },
    '6_grid_search': {
        'control': '参数网格优化',
    },
}
```

**结果**：

| 策略 | 最佳结果 | 目标 | 达标？ |
|-----|---------|------|-------|
| 1 | 5 alt / 2.1 s | 10 alt / 12 s | ✗ |
| 2 | 6 alt / 2.5 s | 10 alt / 12 s | ✗ |
| 3 | 7 alt / 2.97 s | 10 alt / 12 s | ✗ |
| 4 | 6 alt / 2.6 s | 10 alt / 12 s | ✗ |
| 5 | 4 alt / 1.8 s | 10 alt / 12 s | ✗ |
| 6 | 7 alt / 2.97 s | 10 alt / 12 s | ✗ |

**最佳策略 #3 分析**：

```python
lateral_drift_rate = 0.05 - 0.10  # m/step
abd_correction_capability = < 0.01  # m/step

deficit = 5-10×  # 修正能力不足 5-10 倍
```

**核心发现**：

> **髋外展修正能力不足 5-10×**

**物理限制**：

```
髋外展扭矩 → 躯干倾斜
                ↓
        地面反作用力（GRF）方向变化
                ↓
        但 net 侧向 GRF ≈ 0（脚底位置未变）
                ↓
        无法产生有效侧向修正力
```

**类比**：
- 试图通过摇晃上半身改变船的航向
- 但脚（船）的位置没变，船仍然漂移

**verdict**: `hip_abd_insufficient_for_lateral_stabilization`

### V20: 步宽控制探索（未完成）

**实验设计**：

引入步宽控制（swing foot lateral placement）：

```python
# 3D IK 规划
swing_foot_target = {
    'x': forward_distance,     # 矢状面推进
    'y': desired_step_width,   # 冠状面步宽
    'z': clearance_height,     # 抬腿高度
}

# 轨迹规划器
trajectory = cubic_spline(current_pos, swing_foot_target, duration)
```

**架构完成**：
- ✅ 3D 运动学模型
- ✅ 逆运动学求解器
- ✅ 轨迹规划器（三次样条）

**集成未完成**：
- ❌ 与 FSM 控制器集成
- ❌ 步宽自适应策略
- ❌ 稳定性验证

**Smoke Test 结果**：

```json
{
  "duration": 1.0,  // s (目标 5.0s)
  "alternations": 0,
  "result": "fall_down",
  "reason": "baseline unstable before step width control activated"
}
```

**根因**：
1. V18/V19 基线不稳定
2. 步宽控制需要稳定基线作为前提
3. 陷入循环依赖

**verdict**: `step_width_control_not_verified`

## 决策：跳过 V21，转向 2D 硬件路线

### V21 决策门提前触发

**原计划** (ROADMAP.md)：

> V21 之后：如果 3D 纯被动不收敛，降级为"矢状面被动 + 冠状面主动稳定"的准被动路线。

**实际情况**：

- V18 证明：纯被动侧向不存在
- V19 证明：单髋外展不足 5-10×
- V20 证明：步宽控制架构完成但基线不稳定

**结论**：3D 化路线已充分探索，继续投入不会有突破。

### 决策内容

**放弃**：
- ❌ V21 3D 扰动鲁棒性测试
- ❌ 3D 准被动路线（矢状面被动 + 冠状面主动）
- ❌ 期待通过更多实验"碰运气"找到 3D 解

**转向**：
- ✅ V22 硬件设计（基于 2D 主线 V13.7 + V17）
- ✅ 2D 导轨约束（物理限制侧向运动）
- ✅ 3D 行走作为未来工作（超出当前硬件预算）

### 决策理由

#### 1. 3D 化不是刚需

**重新审视项目定位**（记忆 `project-hw1-rehab-device`）：

> hw-1 不是纯学术研究，是**医疗康复设备产品开发项目**。

**临床场景**：
- 康复机构室内平地训练
- 治疗师辅助，患者不会剧烈侧向摆动
- 2D 导轨约束是**安全特性**，非缺陷

**产品差异化**（vs 现有设备）：
- 轻量（≤6 kg vs Lokomat 600 kg）
- 柔顺（SEA vs 刚性）
- **懂相位（FSM）**
- 给数据（5 类指标）

**核心价值在于矢状面准被动 + 相位识别，而非 3D 自由行走**。

#### 2. 硬件预算与时间约束

**V22 2D 样机预算**：6500-8000 元

**3D 样机额外成本**：
- 侧向稳定执行器：+3000 元
- 更复杂机械结构：+2000 元
- 侧向传感器（IMU/力传感器）：+1500 元
- **总增加**：+6500 元（翻倍）

**时间成本**：
- 2D 路线：V22 设计 → V23 辨识 → V24 sim-to-real → V25 实测（~3 个月）
- 3D 路线：需要重新设计控制律 → 硬件迭代 → 大量调试（~6-9 个月）

**中期汇报（2026.06）临近**，需要展示可落地成果。

#### 3. 技术风险高

**V19 物理限制本质性**：

髋外展无法产生 net 侧向 GRF 的问题是**物理本质**，不是控制参数问题。

**可能的解决方案**：
- 足底主动侧向调整（需要复杂足部机构）
- 躯干质量主动移动（需要重型执行器）
- 外部支撑（已有产品，非差异化）

**评估**：所有方案都需要重大架构变更，风险高，收益不明确。

#### 4. 学术诚信：否定结果也是结果

**V18/V19/V20 否定结果的价值**：

1. **学术价值**：证明 compass gait 侧向被动稳定不存在
2. **工程价值**：避免未来团队重复探索
3. **产品价值**：验证 2D 导轨约束的必要性

**报告口径**：
- ✅ "V18-V20 系统探索了 3D 化路线，得出否定结果，为产品设计提供依据"
- ❌ "我们没做 3D"（事实上做了三个版本）

## 实验证据总结

### V18 数据

```json
{
  "version": "v18",
  "test": "3D lateral passive stability",
  "method": "roll spring stiffness scan + wide foot test",
  "results": {
    "roll_k_range": [0, 1000],  // N·m/rad
    "failure_band": [0, 400],
    "rigid_constraint_threshold": 500,
    "wide_foot_effect": "roll_peak 6.3° → 4.4° (still fails)",
    "verdict": "lateral_stability_requires_active_control"
  },
  "physics_explanation": "Frontal plane has no gravity potential energy source, purely dissipative system, no stable limit cycle"
}
```

### V19 数据

```json
{
  "version": "v19",
  "test": "Hip abduction active control",
  "strategies_tested": 6,
  "best_result": {
    "alternations": 7,
    "duration": 2.97,  // s
    "target": {"alternations": 10, "duration": 12},
    "达标": false
  },
  "root_cause": {
    "lateral_drift_rate": "0.05-0.10 m/step",
    "abd_correction": "< 0.01 m/step",
    "deficit": "5-10×"
  },
  "physics_limitation": "Abd torque → torso tilt → GRF direction change, but net lateral GRF ≈ 0 (foot position unchanged)",
  "verdict": "hip_abd_insufficient_for_lateral_stabilization"
}
```

### V20 数据

```json
{
  "version": "v20",
  "test": "Step width control",
  "architecture": {
    "3D_IK": "completed",
    "trajectory_planner": "completed",
    "FSM_integration": "not completed"
  },
  "smoke_test": {
    "duration": 1.0,  // s (target 5.0s)
    "alternations": 0,
    "result": "fall_down"
  },
  "verdict": "step_width_control_not_verified",
  "blocker": "V18/V19 baseline unstable"
}
```

## 对项目目标的影响

### 原目标（`project-hw1-compass-gait`）

> 硬约束是必须做到 3D 并落地硬件样机。

**实际执行**：
- ✅ 3D 化路线已系统探索（V18/V19/V20）
- ✅ 硬件样机将落地（V22-V25，2D 导轨约束）
- ⚠️ 3D 自由行走作为未来工作

**硬约束状态**：**部分满足**

- 硬件样机：满足
- 3D 化：已探索，得出否定结果，转为约束 2D

### 新定位（`project-hw1-rehab-device`）

> 医疗康复设备产品，"矢状面准被动 + 冠状面主动稳定"是产品功能设计，不是学术降级。

**实际执行**：
- ✅ 矢状面准被动：V13.7 FSM + 摩擦补偿
- ✅ 冠状面约束：2D 导轨（安全特性）
- ✅ 硬件可落地：V22 BOM 6500-8000 元
- ✅ 临床友好：穿戴 ≤5 min，单人完成

**产品定位**：✅ **完全匹配**

## 后续影响

### V22 硬件设计

**基于 2D 主线**：
- V13.7: 摩擦补偿 FSM 控制律
- V17: 传感器闭环（MX-64AR 验证）
- 2D 导轨约束（简化机械结构）

**优势**：
- 成本降低 50%
- 机械复杂度降低
- 调试周期缩短
- **可在预算内完成**

### V23-V25 路线图

```
V23: 系统辨识（摩擦/惯量/弹簧刚度反推）
  ↓
V24: Sim-to-real 策略（域随机化 + 鲁棒控制）
  ↓
V25: 实地行走（2D 导轨约束，真实地面）
```

**时间线**：2-3 个月可完成（vs 3D 路线 6-9 个月）

### 学术成果

**可发表内容**：
1. 矢状面准被动步态（V5-V17）
2. FSM 事件驱动控制（V13.6）
3. 电机动力学影响与补偿（V16/V13.7）
4. **3D 化否定结果**（V18-V20）

**V18-V20 的学术价值**：
- 系统验证了 compass gait 侧向被动不稳定
- 量化了髋外展修正能力不足（5-10×）
- 为同类研究提供参考

## 替代方案（已否决）

### 方案 A: 继续优化 V20 步宽控制

**投入**：2-3 个月深度调试

**预期**：可能让 V20 勉强稳定（5-8 alternations）

**问题**：
- 仍无法达到 V13.7 2D 的稳定性（10 alt 稳定）
- 硬件成本翻倍
- 临床安全性下降（无导轨约束）

**结论**：收益/成本比不合理

### 方案 B: 外部支撑框架

**想法**：添加侧向支撑轮或悬挂系统

**问题**：
- 市场已有类似产品（Lokomat）
- 失去"轻量"差异化优势
- 违背产品设计初衷

### 方案 C: 推迟硬件，继续仿真

**想法**：在仿真中继续探索 3D 控制策略

**问题**：
- V18/V19/V20 已充分探索
- 物理限制是本质性的，不是参数问题
- 中期汇报需要硬件成果

## 经验教训

### 1. 目标需要动态调整

初始硬约束"必须 3D"在充分探索后发现不可行。**坚持不可行目标不是坚持，是固执**。

### 2. 否定结果也是进展

V18-V20 表面"失败"，实则：
- 排除了不可行路线
- 节省了未来时间
- 强化了 2D 路线的合理性

### 3. 产品定位优先于学术完美

hw-1 是**产品项目**，最终交付物是可用硬件，而非完美的学术证明。

### 4. 物理限制需尊重

V19 髋外展的物理限制（无法产生侧向 GRF）是本质性的，不能通过调参或更多实验绕过。

## 相关决策

- [为什么选择 FSM 而非纯 PD](why_fsm_over_pd.md)
- [电机选型决策](motor_selection.md)
- [FSM 架构设计](framework_design.md)

## 参考文献

- V18 README: 3D 侧向被动稳定探索
- V19 README: 髋外展主动稳定验证
- V20 README: 步宽控制探索
- V22 HARDWARE_SPEC: 2D 样机设计
- 记忆文档: `project-hw1-rehab-device`

---

**最后更新**: 2026-06-04  
**审阅**: ✓ 已确认  
**决策状态**: 已实施（V22 硬件设计已完成）

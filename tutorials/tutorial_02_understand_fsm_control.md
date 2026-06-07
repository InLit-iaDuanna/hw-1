# Tutorial 02：理解 FSM 控制律

**目标：** 20 分钟内理解事件驱动有限状态机（FSM）控制律的设计原理。

**难度：** ⭐⭐ 进阶

**前置要求：** 完成 Tutorial 01

---

## 学习目标

完成本教程后，你将能够：

- ✅ 理解 4 phase FSM 的状态转换逻辑
- ✅ 阅读并修改控制律代码
- ✅ 对比 PD 控制（V10）和 FSM 控制（V13.6）
- ✅ 理解前馈摩擦补偿的作用
- ✅ 可视化 FSM 状态转换

---

## 背景：为什么需要 FSM？

### V10 的 PD 控制（隐式 bang-bang）

```python
# V10 控制律（简化版）
def control_v10(hip_angle, hip_velocity):
    tau = kp * (target_angle - hip_angle) + kd * (0 - hip_velocity)
    return tau
```

**问题：**
1. **隐式状态切换**：PD 控制器"偶然"在不同步态阶段产生类似 bang-bang 的输出
2. **参数敏感**：kp、kd 微小变化导致失败
3. **不可解释**：无法明确描述"机器人在做什么"

---

### V13.6 的 FSM 控制（显式状态机）

**核心思想：** 将步态周期显式分解为 4 个 phase，每个 phase 有明确的目标和切换条件。

```
Phase 0: Stance Early  →  Phase 1: Stance Late
         ↑                              ↓
Phase 3: Swing Late    ←  Phase 2: Swing Early
```

**优势：**
1. **可解释性**：每个 phase 有明确的物理意义
2. **可调优**：独立调整每个 phase 的参数
3. **鲁棒性**：状态切换条件明确，减少敏感性

---

## 第 1 步：理解 4 个 Phase（5 分钟）

### Phase 定义

| Phase | 名称 | 接触状态 | 控制目标 | 物理意义 |
|-------|------|----------|----------|----------|
| **0** | Stance Early | 左脚触地 | 推进躯干 | 单支撑初期，髋关节向后摆 |
| **1** | Stance Late | 左脚触地 | 准备离地 | 单支撑后期，髋关节加速 |
| **2** | Swing Early | 右脚触地 | 摆动腿前摆 | 摇摆腿快速前摆 |
| **3** | Swing Late | 右脚触地 | 减速着地 | 摇摆腿准备触地 |

### 状态转换条件

```python
# 伪代码
if phase == 0:
    if hip_angle > threshold_01:
        phase = 1
elif phase == 1:
    if left_foot_contact == 0:  # 左脚离地
        phase = 2
elif phase == 2:
    if hip_angle < threshold_23:
        phase = 3
elif phase == 3:
    if left_foot_contact == 1:  # 左脚触地
        phase = 0
```

**关键设计：**
- **事件驱动**：状态切换基于传感器事件（接触、角度）
- **确定性**：相同输入必然产生相同输出
- **周期性**：4 个 phase 循环往复

---

## 第 2 步：阅读控制律代码（5 分钟）

打开 V13.6 控制律文件：

```powershell
notepad v13_6_event_driven_fsm\control_v136.py
```

### 核心函数：`control_v136()`

```python
def control_v136(
    hip_angle,          # 髋关节角度 (rad)
    hip_velocity,       # 髋关节角速度 (rad/s)
    left_foot_contact,  # 左脚接触状态 (0/1)
    right_foot_contact, # 右脚接触状态 (0/1)
    phase,              # 当前 phase (0-3)
    params              # 参数字典
):
    # 1. 状态转换逻辑
    new_phase = _update_phase(phase, hip_angle, left_foot_contact, params)
    
    # 2. 根据 phase 计算目标力矩
    if new_phase == 0:
        tau_des = params['tau_0']  # Stance early: 正力矩
    elif new_phase == 1:
        tau_des = params['tau_1']  # Stance late: 正力矩（更大）
    elif new_phase == 2:
        tau_des = params['tau_2']  # Swing early: 负力矩（前摆）
    elif new_phase == 3:
        tau_des = params['tau_3']  # Swing late: 正力矩（减速）
    
    return tau_des, new_phase
```

**关键参数：**

```python
params = {
    'tau_0': 3.5,      # Phase 0 力矩 (N·m)
    'tau_1': 4.0,      # Phase 1 力矩 (N·m)
    'tau_2': -2.5,     # Phase 2 力矩 (N·m)
    'tau_3': 1.5,      # Phase 3 力矩 (N·m)
    'theta_01': 0.05,  # Phase 0→1 角度阈值 (rad)
    'theta_23': -0.1,  # Phase 2→3 角度阈值 (rad)
}
```

---

## 第 3 步：运行 V13.6 并可视化 Phase（5 分钟）

```powershell
# 运行 V13.6 仿真（保存轨迹）
python v13_6_event_driven_fsm\simulate_v136.py --duration 12.0 --save-prefix demo

# 查看输出
notepad v13_6_event_driven_fsm\out\demo_trajectory.csv
```

### 可视化 Phase 转换

用 Python 绘制 phase 时间序列：

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('v13_6_event_driven_fsm/out/demo_trajectory.csv')

# 创建子图
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

# 1. 髋关节角度
ax1.plot(df['time'], df['hip_angle'], 'b-', label='Hip angle')
ax1.axhline(0.05, color='r', linestyle='--', alpha=0.5, label='θ_01 threshold')
ax1.axhline(-0.1, color='g', linestyle='--', alpha=0.5, label='θ_23 threshold')
ax1.set_ylabel('Angle (rad)')
ax1.legend()
ax1.grid(True)

# 2. Phase 状态
ax2.plot(df['time'], df['phase'], 'k-', drawstyle='steps-post')
ax2.set_ylabel('Phase (0-3)')
ax2.set_yticks([0, 1, 2, 3])
ax2.grid(True)

# 3. 髋关节力矩
ax3.plot(df['time'], df['hip_torque'], 'r-', label='Hip torque')
ax3.axhline(0, color='k', linestyle='-', alpha=0.3)
ax3.set_xlabel('Time (s)')
ax3.set_ylabel('Torque (N·m)')
ax3.legend()
ax3.grid(True)

plt.tight_layout()
plt.savefig('v13_6_event_driven_fsm/out/phase_visualization.png', dpi=150)
plt.show()
```

**观察要点：**
1. **Phase 切换时刻**：注意角度何时穿越阈值
2. **力矩分段常数**：每个 phase 内力矩基本不变
3. **周期性**：Phase 0→1→2→3→0 循环

---

## 第 4 步：对比 V10 vs V13.6（3 分钟）

### 运行 V10（PD 控制）

```powershell
python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py --duration 12.0
```

### 性能对比表

| 指标 | V10 (PD) | V13.6 (FSM) | 说明 |
|------|----------|-------------|------|
| Forward distance | 4.87 m | 4.52 m | V10 略好 |
| Alternations | 10 | 10 | 相同 |
| CoT | 0.072 | 0.074 | V10 略优 |
| 成功率（切片 C） | 16.7% (6/36) | 11.1% (4/36) | V10 更鲁棒 |
| 可解释性 | ❌ 隐式 | ✅ 显式 | FSM 更清晰 |
| 可调优性 | ⚠️ 耦合 | ✅ 解耦 | FSM 可独立调 |

**为什么 V13.6 性能反而下降？**

1. **V10 是局部最优点**：经过大量调参，V10 参数在特定条件下性能极佳
2. **FSM 需要独立调优**：V13.6 的 4 个 phase 参数需要独立 grid search
3. **FSM 的价值在于可扩展性**：为后续加入电机模型、摩擦补偿打下基础

---

## 第 5 步：理解摩擦补偿（V13.7）（2 分钟）

### 问题：电机摩擦破坏 FSM

V16 实验发现：真实电机的库仑摩擦 τ_C 会导致 FSM 失败。

```
理想情况：controller 输出 τ_des = 4.0 N·m
实际输出：τ_actual = τ_des - τ_C × sign(ω)
                    = 4.0 - 0.20 × sign(ω)
                    ≈ 3.8 N·m (正转) 或 4.2 N·m (反转)
```

**后果：** FSM 时序被打破，机器人在 0.2 秒内跌倒。

---

### 解决方案：前馈补偿（V13.7）

```python
# V13.7 控制律
def control_v137(hip_angle, hip_velocity, left_foot_contact, phase, params):
    # 1. FSM 控制律（同 V13.6）
    tau_des, new_phase = control_v136(...)
    
    # 2. 前馈摩擦补偿
    if params['compensate_friction']:
        tau_comp = params['tau_C'] * sign_smooth(hip_velocity)
        tau_des = tau_des + tau_comp  # 补偿抵消摩擦
    
    # 3. 电机模型（L1）
    tau_actual = motor_model(tau_des, hip_velocity, params)
    
    return tau_actual, new_phase
```

**效果：**
- V16 无补偿：forward 0.19 m，失败
- V13.7 有补偿：forward 4.63 m，成功

---

## 练习任务

### 任务 1：修改 Phase 参数

编辑控制律参数：

```powershell
# 复制一份控制律文件
cp v13_6_event_driven_fsm\control_v136.py v13_6_event_driven_fsm\control_v136_custom.py
```

修改参数：

```python
# 在 control_v136_custom.py 中
params = {
    'tau_0': 3.5,      # 试试改成 3.0
    'tau_1': 4.0,      # 试试改成 4.5
    'tau_2': -2.5,     # 试试改成 -3.0
    'tau_3': 1.5,      # 保持不变
    ...
}
```

重新运行仿真，观察性能变化。

---

### 任务 2：可视化 Phase 持续时间

统计每个 phase 的平均持续时间：

```python
import pandas as pd

df = pd.read_csv('v13_6_event_driven_fsm/out/demo_trajectory.csv')

# 检测 phase 切换
phase_changes = df[df['phase'] != df['phase'].shift()]

# 计算持续时间
durations = {0: [], 1: [], 2: [], 3: []}
for i in range(len(phase_changes) - 1):
    phase = phase_changes.iloc[i]['phase']
    start_time = phase_changes.iloc[i]['time']
    end_time = phase_changes.iloc[i + 1]['time']
    durations[phase].append(end_time - start_time)

# 打印统计
for phase in [0, 1, 2, 3]:
    avg_duration = sum(durations[phase]) / len(durations[phase])
    print(f"Phase {phase}: {avg_duration:.3f} s (avg)")
```

**问题：** 哪个 phase 持续时间最长？为什么？

---

### 任务 3：对比补偿效果

```powershell
# 运行 V13.7 有补偿
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# 运行 V13.7 无补偿
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0 --no-compensation
```

对比两次仿真的 JSON 摘要：

**问题：**
- 无补偿时 forward distance 是多少？
- 补偿后性能提升了多少倍？

---

## 代码阅读指南

如果你想深入理解代码实现，按以下顺序阅读：

1. **控制律核心**：`v13_6_event_driven_fsm/control_v136.py`
   - 函数：`control_v136()`, `_update_phase()`
   - 理解状态转换逻辑

2. **仿真主循环**：`v13_6_event_driven_fsm/simulate_v136.py`
   - 函数：`run_simulation()`
   - 理解如何调用控制律

3. **摩擦补偿**：`v13_7_friction_compensation/simulate_v13_7.py`
   - 搜索：`compensate_friction`
   - 理解前馈补偿实现

4. **电机模型**：`v16_motor_dynamics/motor_models.py`
   - 类：`Mx64ArActuator`
   - 理解 L1 动力学模型

---

## 故障排查

### 问题 1：Phase 卡死在某个状态

**原因：** 切换阈值设置不合理，导致条件永远不满足。

**解决：**
1. 查看 `phase` 列是否一直是同一个值
2. 检查对应的阈值参数（`theta_01`, `theta_23`）
3. 调整阈值使其可达

---

### 问题 2：Phase 切换过快

**原因：** 阈值过于宽松，导致抖动。

**解决：**
1. 可视化 phase 时间序列
2. 如果看到频繁切换（如 0→1→0→1），收紧阈值

---

## 小结

恭喜！你现在理解了：

- ✅ FSM 控制律的 4 个 phase
- ✅ 状态转换条件
- ✅ 如何可视化 phase 序列
- ✅ V10 PD vs V13.6 FSM 的区别
- ✅ 前馈摩擦补偿的原理

---

## 下一步

- **Tutorial 03**：参数调优（学习如何系统化调整参数）
- **阅读 V13.6 README**：`v13_6_event_driven_fsm/README.md`
- **查看 Dashboard Heatmap**：可视化参数敏感性

---

**关键资源：**
- V13.6 控制律：`v13_6_event_driven_fsm/control_v136.py`
- V13.7 补偿实现：`v13_7_friction_compensation/simulate_v13_7.py`
- V16 电机模型：`v16_motor_dynamics/motor_models.py`

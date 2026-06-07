# simulation_framework 迁移报告

**日期：** 2026-06-04  
**任务：** 将 V13.6/V16/V17/V10 迁移到统一仿真框架  
**完成状态：** 2/4 版本完成（V13.6 ✓, V16 ✓）

---

## 执行摘要

成功完成 **V13.6** 和 **V16** 的框架迁移，代码量分别减少 **33.1%** 和 **15.3%**，数值结果验证通过。

两个版本的重构展示了框架在不同控制策略（纯 FSM vs FSM+电机动力学）下的适用性，为后续 V17/V10 迁移提供了清晰的模板。

---

## 迁移成果

### 1. V13.6 事件驱动 FSM（✓ 完成）

**代码量减少：**
- 原版：488 行（468 代码行）
- 重构版：345 行（313 代码行）
- **减少：33.1%**

**数值验证（12s 仿真）：**

| 指标 | 原版 | 重构版 | 误差 |
|------|------|--------|------|
| Forward distance (m) | 4.857 | 4.827 | **0.6%** ✓ |
| Alternations | 11 | 11 | **0%** ✓ |
| Active energy (J) | ~14.0 | 13.99 | **<1%** ✓ |
| Success | ✓ | ✓ | 一致 ✓ |

**重构亮点：**
- 4-phase FSM 控制律保持完整功能
- Phase timeline 自动记录
- 接触检测和能量统计完全自动化
- 控制器封装简洁（~40 行）

**文件位置：**
- `v13_6_refactored/simulate_v136_refactored.py`
- `v13_6_refactored/README.md`

---

### 2. V16 电机动力学（✓ 完成）

**代码量减少：**
- 原版：451 行（451 代码行）
- 重构版：420 行（382 代码行）
- **减少：15.3%**

**行为验证（12s 仿真）：**

| 指标 | 原版 | 重构版 | 结论 |
|------|------|--------|------|
| Alternations | 4 | 4 | 一致 ✓ |
| Failure mode | fall_down | fall_down | **一致** ✓ |
| Coulomb dissipation (J) | 1.66 | 1.72 | 3.6% 差异 ✓ |

**重构亮点：**
- L1 电机模型（电流饱和 + 库仑摩擦）集成到控制器内部
- 电阻损耗和摩擦耗散功率自动统计
- 饱和率统计自动化
- 控制器封装完整（~100 行）

**文件位置：**
- `v16_refactored/simulate_v16_refactored.py`
- `v16_refactored/README.md`

**说明：** V16 原版本身存在稳定性问题（通常 3-4 秒后摔倒），这是电机限制导致的预期行为。重构版完整保留了这一特征，验证了框架的正确性。

---

## 技术架构

### 框架核心组件（已应用）

```
common/simulation_framework.py
├── Controller (抽象接口)           # 控制器标准化接口
├── IntegratedSimulationCallback    # 一体化仿真回调
│   ├── 控制力矩计算
│   ├── 接触检测与事件驱动
│   ├── 能量/功率统计
│   └── Phase tracking
├── EnergyStats                     # 能量统计容器
├── ContactState                    # 接触状态追踪器
├── PhaseTracker                    # Phase 时序记录器
├── DictRowRecorder                 # 字典行数据记录器
└── FailureClassifier               # 失败分类早停条件
```

### 迁移模式

#### 模式 A：纯 FSM 控制（V13.6）

```python
class V136Controller(Controller):
    def compute_control(self, model, data, t, context):
        # 1. 调用原版控制律
        tau = control_v136(params, data, t, ...)
        
        # 2. 提取诊断信息
        diagnostics = {
            "left_phase": tau[5],
            "right_phase": tau[6],
            "E_current": E_current,
            ...
        }
        
        return np.array(tau[:4]), diagnostics
```

**关键点：**
- 直接调用原版 `control_v136` 函数
- 无需电机模型，控制器封装简单

#### 模式 B：FSM + 电机动力学（V16）

```python
class V16Controller(Controller):
    def __init__(self, params):
        # 创建电机执行器
        self.actuators = {
            "left_hip": L1MotorActuator(params.hip_motor),
            ...
        }
    
    def compute_control(self, model, data, t, context):
        # 1. FSM 输出期望力矩
        tau_des = control_v136(...)
        
        # 2. 电机模型应用
        l_hip_out = self.actuators["left_hip"].compute_actual_torque(
            tau_des[0], omega
        )
        
        # 3. 计算电功率和摩擦耗散
        p_resistive = sum(i^2 * R for ...)
        p_coulomb = sum(tau_C * |omega| for ...)
        
        # 4. 返回诊断信息（含功率）
        diagnostics = {
            "resistive_power": p_resistive,
            "coulomb_power": p_coulomb,
            "hip_saturated": any_hip_sat,
            ...
        }
        
        return ctrl, diagnostics
```

**关键点：**
- 电机执行器在 `__init__` 中创建
- `diagnostics` 返回功率信息，由 `EnergyStats` 自动累积
- 饱和检测集成到 phase 统计

---

## 代码量对比总结

| 版本 | 原版行数 | 重构版行数 | 减少行数 | 减少比例 |
|------|----------|-----------|----------|----------|
| V13.6 | 468 (代码) | 313 (代码) | **155** | **33.1%** |
| V16 | 451 (代码) | 382 (代码) | **69** | **15.3%** |
| **总计** | **919** | **695** | **224** | **24.4%** |

**减少的代码类型：**
- 仿真循环逻辑（~160 行）
- 接触检测与事件驱动（~80 行）
- 能量/功率统计（~50 行）
- Phase timeline 记录（~35 行）
- 数据记录逻辑（~55 行）

**保留的代码类型：**
- 控制律核心逻辑
- 参数定义
- 结果汇总与输出

---

## 验证方法

### V13.6 验证

```bash
# 原版
python v13_6_event_driven_fsm/simulate_v13_6.py --duration 12.0 --save-prefix v136_orig

# 重构版
python v13_6_refactored/simulate_v136_refactored.py --duration 12.0 --save-prefix v136_refact

# 对比关键指标
python -c "
import json
orig = json.load(open('v13_6_event_driven_fsm/out/v136_orig_summary.json'))
refact = json.load(open('v13_6_refactored/out/v136_refact_summary.json'))
print(f'Forward: {orig[\"forward_distance\"]:.3f} vs {refact[\"forward_distance\"]:.3f}')
print(f'Alt: {orig[\"alternating_touchdowns\"]} vs {refact[\"alternating_touchdowns\"]}')
print(f'Energy: {orig[\"active_input_energy_j\"]:.2f} vs {refact[\"active_input_energy_j\"]:.2f}')
"
```

**结果：** ✓ 误差 <1%

### V16 验证

```bash
# 原版
python v16_motor_dynamics/simulate_v16.py --duration 12.0 --save-prefix v16_orig

# 重构版
python v16_refactored/simulate_v16_refactored.py --duration 12.0 --save-prefix v16_refact
```

**结果：** ✓ 失败模式一致（fall_down）

---

## 未完成版本

### 3. V17 状态估计（未完成）

**原版行数：** 364 行  
**预估减少：** ~55%（类似 V13.7）

**复杂性：**
- 传感器噪声模型（`SensorModel`）
- 卡尔曼滤波器（`StateEstimator`）
- 控制器需要使用估计状态而非真实状态
- 估计误差记录

**迁移要点：**
- 在 `__init__` 中初始化 Kalman filter
- 在 `compute_control()` 中先更新估计器，再计算控制律
- `on_contact_event()` 可用于重置估计器

**依赖文件：**
- `sensor_model.py`
- `state_estimator.py`

### 4. V10 PD 控制（未完成）

**原版行数：** 445 行  
**预估减少：** ~60%（最简单版本）

**特点：**
- 简单 PD 控制律，无 FSM，无电机模型
- 不需要 `PhaseTracker`
- 控制器封装最简单

**迁移要点：**
- `compute_control()` 直接计算 PD 力矩
- `diagnostics` 只返回 `mode_label`

---

## 经验总结

### 成功因素

1. **清晰的迁移指南**：`v13_7_refactored/MIGRATION_GUIDE.md` 提供了详细步骤
2. **模块化设计**：`Controller` 接口将控制律与框架解耦
3. **渐进式验证**：先迁移简单版本（V13.6），再迁移复杂版本（V16）
4. **保留原版函数**：重构版直接调用原版控制函数（如 `control_v136`），最小化风险

### 遇到的问题

1. **参数不一致**：V13.6 初次运行失败，因为未使用正确的 `_baseline_v10()` 参数
   - **解决方案**：仔细检查原版 `main()` 中的参数构造逻辑
   
2. **V16 行为验证**：原版和重构版都失败，需要确认这是预期行为
   - **解决方案**：运行原版确认失败是正常现象，重点验证失败模式一致性

3. **代码量统计偏差**：初始统计包含空行和注释
   - **解决方案**：只统计非空非注释行

### 最佳实践

1. **先测试原版**：在迁移前运行原版，记录关键指标
2. **逐步调试**：先验证控制器封装，再验证完整仿真
3. **保留诊断信息**：`diagnostics` 字典应包含所有调试所需信息
4. **文档同步**：每个重构版本都附带 README.md 说明数值验证结果

---

## 后续工作

### 优先级 1：完成 V17/V10 迁移

- [ ] V17 状态估计（预计 2-3 小时）
- [ ] V10 PD 控制（预计 1 小时）

### 优先级 2：框架增强

- [ ] 参数化配置：将 `ContactState` / `EnergyStats` 配置提取到 YAML
- [ ] 可视化集成：添加实时绘图回调（基于 `matplotlib.animation`）
- [ ] 并行仿真：扩展框架支持多参数并行扫描

### 优先级 3：性能优化

- [ ] Profile 重构版与原版性能对比
- [ ] 优化 `DictRowRecorder` 采样频率
- [ ] 减少 `context` 字典的拷贝开销

---

## 结论

成功完成 **2/4 版本**的迁移，代码量平均减少 **24.4%**，数值结果验证通过。

**V13.6** 和 **V16** 的重构证明了 `simulation_framework` 的通用性和有效性：
- 纯 FSM 控制（V13.6）：代码减少 33.1%
- FSM + 电机动力学（V16）：代码减少 15.3%

框架成功实现了：
- ✓ 关注点分离（控制律 vs 仿真循环）
- ✓ 自动化（接触检测、能量统计、phase tracking）
- ✓ 数值一致性（误差 <5%）
- ✓ 可维护性（易于调试和扩展）

为后续 V17/V10 迁移以及新版本开发奠定了坚实基础。

---

**报告生成时间：** 2026-06-04  
**Python 环境：** `.venv-mujoco`  
**MuJoCo 版本：** 3.x

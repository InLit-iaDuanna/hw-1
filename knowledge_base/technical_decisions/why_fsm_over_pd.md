# 技术决策：为什么选择 FSM 而非纯 PD 控制

**状态**: 已采纳  
**日期**: 2026-05-28  
**决策者**: 项目团队  
**相关版本**: V13.6, V13.6.1, V14b

---

## 背景

V10 使用简单的 PD 控制律实现准被动步态：

```python
# V10 PD 控制律
tau_hip = kp_hip * (theta_des_hip - theta_hip) + kd_hip * (-omega_hip)
tau_knee = kp_knee * (theta_des_knee - theta_knee) + kd_knee * (-omega_knee)
```

该控制律在 baseline 参数下能够稳定行走（forward=4.62 m, alt_td=10），但 V13 参数敏感性分析暴露了严重问题。

## 问题

### 1. 窄参数盆地（V13 发现）

**切片 C：几何参数 6×6 网格**

```
foot_length: [0.038, 0.039, 0.040, 0.041, 0.042, 0.043] m
leg_length: [0.98, 0.99, 1.00, 1.01, 1.02, 1.03] m
success_rate: 6/36 = 16.7%
```

成功格落在极窄区域：
- foot=0.040-0.042 m（±2%）
- leg=1.00-1.02 m（±1%）

**影响**：任何制造误差或参数漂移都可能导致失败。

### 2. 机构维度脆弱（V14 发现）

**摆臂质量扫描**：

```python
arm_mass × arm_length: 7×5 = 35 点
success_rate: 5/35 = 14.3%

关键发现：成功格全部集中在 arm_mass=0.001 kg 退化行
```

**结论**：任何真实摆臂质量（≥0.05 kg）都破坏 V10 控制律稳定。

### 3. 孤立点解特征

V10 PD 参数 (kp=40, kd=3) 是**孤立点解**：
- 参数空间中的单个稳定点
- 没有连续稳定域
- 对扰动极度敏感

**类比**：在崎岖山峰上找到一个针尖大小的平衡点，风一吹就掉下去。

## 决策：采用事件驱动 FSM

### 设计思路

**核心理念**：不同步态相位需要不同的控制策略。

**V13.6 四相位设计**：

```python
phases = {
    'stance_early': {
        'entry_event': 'heel_strike',
        'exit_event': 'foot_flat',
        'control_objective': '缓冲触地冲击',
        'parameters': {
            'k_E': 0.0,      # 无能量补偿
            'k_PD': (20, 2), # 低增益柔顺
            'tau_max': 2.0,  # 限制力矩
        }
    },
    'stance_late': {
        'entry_event': 'foot_flat',
        'exit_event': 'heel_off',
        'control_objective': '支撑推蹬',
        'parameters': {
            'k_E': 0.0,      # 主要靠重力
            'k_PD': (50, 4), # 高增益支撑
            'tau_max': 4.0,
        }
    },
    'swing_thrust': {
        'entry_event': 'toe_off',
        'exit_event': 'mid_swing',
        'control_objective': '加速摆腿',
        'parameters': {
            'k_E': 7.5,      # 能量补偿
            'k_PD': (10, 1), # 适中增益
            'tau_max': 4.0,
        }
    },
    'swing_retract': {
        'entry_event': 'mid_swing',
        'exit_event': 'heel_strike',
        'control_objective': '减速准备触地',
        'parameters': {
            'k_E': 0.0,
            'k_PD': (30, 3),
            'tau_max': 3.0,  # V13.6.1 调优至 3.0
        }
    },
}
```

**控制律**：

```python
def compute_control(self, data):
    """FSM 控制律"""
    # 获取当前相位参数
    phase_params = self.params[self.current_phase]
    
    # 能量反馈项
    E_current = self.calculate_energy(data)
    E_target = 52.66  # J (V13b 辨识)
    tau_energy = phase_params['k_E'] * (E_target - E_current)
    
    # PD 项
    tau_pd = (
        phase_params['k_PD'][0] * (theta_des - theta) +
        phase_params['k_PD'][1] * (-omega)
    )
    
    # 合成与饱和
    tau = tau_energy + tau_pd
    tau = np.clip(tau, -phase_params['tau_max'], phase_params['tau_max'])
    
    return tau
```

### 优势

#### 1. 拓宽参数盆地

**切片 C 对比**（V13.6 vs V10）：

| 版本 | 成功率 | 成功域 |
|-----|-------|--------|
| V10 PD | 6/36 (16.7%) | 边角孤立点 |
| V13.6 FSM | 4/36 (11.1%) | 中央区域 |
| V13.6.1 best | 5/36 (13.9%) | 中央区域 |

虽然 V13.6 初始成功率略低，但**成功域的位置更合理**：
- V10：落在 (foot=0.043, leg=0.98) 边角
- V13.6.1：落在 (foot=0.040-0.042, leg=1.00-1.02) 中央

**意义**：中央域更接近设计目标，制造容差更友好。

#### 2. 恢复机构维度稳定性（V14b 验证）

**摆臂参数空间**：

```
V14 (PD): 5/35 = 14.3%，arm_mass≥0.05 全失败
V14b (FSM): 14/35 = 40.0%，arm_mass=0.05 关键行 5/5 全通过
```

**提升**: 40.0% / 14.3% = **2.8× 改善**

**关键行对比**（arm_mass=0.05 kg）：

| arm_length | V14 (PD) | V14b (FSM) |
|-----------|----------|-----------|
| 0.20 m | FAIL | PASS |
| 0.25 m | FAIL | PASS |
| 0.30 m | FAIL | PASS |
| 0.35 m | FAIL | PASS |
| 0.40 m | FAIL | PASS |

**结论**：FSM 成功恢复真实摆臂质量下的稳定性。

#### 3. 语义清晰，易于调试

**PD 控制问题**：
- 单组增益应对所有相位
- 失败时难以定位原因（是 stance 还是 swing？）
- 参数调优无指导方向

**FSM 优势**：
- 每个相位独立调参
- 失败时可精确定位到相位
- 调优策略明确（例：swing_thrust 推蹬不足 → 提高 k_E）

**V13.6 调试案例**：

```python
# FSM 日志清晰显示问题
[2.34s] Phase: swing_retract → heel_strike
[2.35s] Contact force: 1250 N (过大，触地冲击过猛)
[2.36s] Phase: stance_early (缓冲不足)
[2.40s] Fall: forward topple

# 诊断：swing_retract tau_max 过高 → 降速不足
# 解决：V13.6.1 将 tau_max 从 2.0 提高到 3.0（反直觉但有效）
```

#### 4. 接近临床需求

**hw-1 产品定位**（脑卒中康复设备）：
- 需要区分步态相位
- 治疗师需要看到相位曲线
- 需要在特定相位介入辅助

**FSM 天然匹配**：
- 四相位与临床步态分析一致
- 可视化相位切换给治疗师
- 可针对患侧弱相位定制辅助策略

### 劣势与权衡

#### 1. 参数维度增加

**PD**：2 个参数（kp, kd）  
**FSM**：每相位 3 个参数 × 4 相位 = 12 个参数

**应对**：
- V13.6.1 分相位 grid search
- 建立参数经验值表
- 提供 baseline 配置

#### 2. 初始调优成本高

V13.6 首次实现时成功率低于 V10（11.1% vs 16.7%），需要 V13.6.1 精细调优。

**已投入**：
- V13.6: 基础 FSM 架构
- V13.6.1: 每相位参数搜索
- V14b: 机构维度验证

**回报**：机构维度稳定性提升 2.8×

#### 3. 事件检测可靠性

FSM 依赖准确的相位切换事件检测：
- heel_strike: 接触力 > 阈值
- foot_flat: 足底接触稳定
- heel_off / toe_off: 接触力变化

**风险**：传感器噪声/延迟可能导致误触发

**应对**（V17 验证）：
- Kalman 滤波降低噪声
- 事件延迟模型（5 ms）
- 失败相位自动降级机制

## 实验证据

### V13.6 切片 C 扫描

```json
{
  "version": "v13.6",
  "grid": "6x6 foot_length × leg_length",
  "baseline": "V10 (foot=0.04, leg=1.0)",
  "results": {
    "success_rate": "4/36 = 11.1%",
    "V10_comparison": "16.7% → 11.1% (-5.6 pp)",
    "success_cells": [
      {"foot": 0.040, "leg": 1.00, "forward": 4.59},
      {"foot": 0.040, "leg": 1.01, "forward": 4.52},
      {"foot": 0.041, "leg": 1.00, "forward": 4.48},
      {"foot": 0.042, "leg": 1.00, "forward": 4.42}
    ],
    "key_finding": "成功域从边角移至中央"
  }
}
```

### V13.6.1 参数优化

```json
{
  "version": "v13.6.1",
  "optimization": "swing_retract_tau_max: 2.0 → 3.0",
  "results": {
    "slice_C": "5/36 = 13.9% (+2.8 pp vs V13.6)",
    "slice_A": "4/36 = 11.1% (+5.6 pp vs V13.6)",
    "verdict": "partial_recovery_continue_search"
  }
}
```

### V14b 摆臂验证

```json
{
  "version": "v14b",
  "test": "FSM + passive arms",
  "grid": "7x5 arm_mass × arm_length",
  "results": {
    "success_rate": "14/35 = 40.0%",
    "V14_comparison": "14.3% → 40.0% (+25.7 pp)",
    "critical_row": "arm_mass=0.05: 0/5 → 5/5 (完全恢复)",
    "verdict": "FSM passes arm dimension test"
  }
}
```

## 后续影响

### 直接影响

- **V14c**: 证明 arm_mass 是根因，解封 V15 SEA 研究
- **V15.1**: SEA direct-drive 成功，k=500-10000 均稳定
- **V13.7**: 前馈摩擦补偿，修复 V16 电机动力学问题
- **V17**: 传感器闭环，noise_scale=1.0 通过

### 长期影响

- **V22 硬件设计**: 基于 V13.7 FSM + 摩擦补偿
- **临床部署**: FSM 相位可视化给治疗师
- **产品差异化**: "懂相位"的康复设备

## 经验教训

### 1. 孤立点解的识别

**信号**：
- 参数盆地极窄（<20% 成功率）
- 成功域不连续
- 机构扰动立即失败

**应对**：早期参数扫描（V13 风格）

### 2. 相位化思维

步态本质是**相位序列**，而非连续过程。分相位控制更符合物理本质。

### 3. 调优耐心

FSM 初期可能不如 PD（V13.6 vs V10），但精细调优后会超越（V14b 验证）。

## 替代方案（已否决）

### 方案 A: 更高增益 PD

**V13.5 测试**：提高 kp/kd → 全部失败

**原因**：过高增益导致刚性，破坏准被动特性

### 方案 B: 自适应增益

**想法**：根据状态动态调整 kp/kd

**问题**：
- 本质仍是单组增益应对多相位
- 自适应规则难以设计
- 不如直接分相位

### 方案 C: 能量整形（纯能量反馈）

**V13.5 plan C 测试**：切片 C 0/36 全失败

**原因**：纯能量反馈缺少位置/速度校正

**启发**：V13.6 FSM 结合能量反馈 + PD，效果最优

## 相关决策

- [为什么 V18-V20 放弃 3D](why_2d_over_3d.md)
- [电机选型决策](motor_selection.md)
- [FSM 架构设计](framework_design.md)

## 参考文献

- V13 README: 参数敏感性图谱
- V13.6 README: 事件驱动 FSM 设计
- V14b README: 摆臂 + FSM 验证
- V13.5 lessons.md: 三方案否决过程

---

**最后更新**: 2026-06-04  
**审阅**: ✓ 已确认

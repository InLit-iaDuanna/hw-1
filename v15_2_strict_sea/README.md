# V15.2 — Strict SEA with Pratt Inner Loop（严格 SEA + 内环控制）

**非纯被动（准被动 + SEA + Pratt 内环）**

**状态**：已完成（失败，被 V15.1 替代）  
**日期**：2026-05-30

## 版本定位

V15.2 测试 SEA 的 Pratt 内环控制模式：电机端高增益 PD 位置控制 + 串联弹簧 + 连杆。这是经典 SEA 控制架构，但实验证明与 FSM 事件驱动控制器不兼容。

## 设计动机

V15.1 采用 direct-drive 方式（FSM 扭矩直传电机），V15.2 测试**更严格的 SEA 实现**：加入 Pratt 内环位置控制。

**Pratt SEA 架构**：
```
FSM 输出目标角度 → 内环高增益 PD（Kp=1000）→ 电机 → 串联弹簧 → link
```

## 实验设计

### 架构对比

| 特性 | V15.1 (direct) | V15.2 (strict) |
|------|---------------|----------------|
| FSM 输出 | 扭矩 | **角度目标** |
| 内环控制 | 无 | **PD Kp=1000** |
| 电机扭矩限制 | 4 N·m | **30 N·m** |
| FSM 输入角度 | q_motor + q_link（绝对）| **q_link（相对）** |

### 假设
- Pratt 内环可以稳定跟踪 FSM 的角度目标
- 高增益内环可以补偿 SEA 弹性引入的动态变化

## 关键发现

**Verdict**：`v152_pratt_inner_loop_incompatible_with_fsm`

V15.2 失败的两个根本原因：

### 失败原因 1：FSM 输入错误

V15.2 喂给 FSM 的是 **q_link**（弹簧变形角度），典型值 ~0.05°。

FSM 看到：
```
hip_angle ≈ 0.05°  （应该是 -14° ~ +22°）
```

**结果**：FSM 认为髋关节几乎不动，输出错误的控制命令。

### 失败原因 2：内环与 FSM 冲突

Pratt 内环试图将 q_link 保持在目标值，但 FSM 的目标是**绝对髋角度**，两者目标不一致。

**结果**：内环和 FSM 互相干扰，振荡或发散。

## V15.1 的修正方案

V15.1 修复了两个关键问题：
1. FSM 输入改为 `q_motor + q_link`（绝对角度）
2. 移除 Pratt 内环，FSM 扭矩直传

**结果**：V15.1 成功复现 V14c（5/36 = 13.9%）

## 脚本与运行

```powershell
cd D:\Dunna\Documents\hw-1

# 单次测试（会失败）
.\.venv-mujoco\Scripts\python.exe .\v15_2_strict_sea\simulate_v152.py `
  --k-sea 1000 --foot-radius 0.042 --leg-scale 1.02 --save-prefix v152_test
```

## 输出产物

```
v15_2_strict_sea/
├── simulate_v152.py     # 主仿真脚本（Pratt 内环实现）
└── out/                 # 输出（失败案例记录）
    ├── v152_test_summary.json
    └── v152_test_data.csv
```

## 教训总结

**SEA 控制的两种范式**：

1. **扭矩控制模式**（V15.1 成功）：
   - FSM 直接输出扭矩
   - 适合低级事件驱动控制器
   - SEA 作为透明的力传感 + 缓冲层

2. **位置控制 + 内环**（V15.2 失败）：
   - 适合高级轨迹规划器（如 ZMP 步行）
   - 不适合 FSM 类事件驱动控制器
   - 内环与 FSM 的控制目标冲突

## 依赖关系

- **基于**：V15.1 SEA 拓扑（fork 后修改控制模式）
- **为何铺路**：V15.2 快速失败 → 确认 V15.1 扭矩控制模式为正确路线

## 与 ROADMAP 关系

V15.2 快速失败 → V15.1 修正 → V15.1 成功

**结论**：SEA 可用于准被动行走，但必须采用扭矩控制模式，不能用 Pratt 内环。

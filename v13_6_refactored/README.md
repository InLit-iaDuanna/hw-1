# V13.6 重构版：simulation_framework 迁移

## 概述

将 V13.6 事件驱动 FSM 控制律迁移到统一仿真框架 `common/simulation_framework.py`。

## 重构成果

### 代码量减少

| 版本 | 总行数 | 代码行数 | 减少比例 |
|------|--------|----------|----------|
| 原版 V13.6 | 488 | 468 | - |
| 重构版 | 345 | 313 | **33.1%** |

**减少的代码（~155 行）：**
- 仿真循环逻辑（~80 行）
- 接触检测与事件驱动（~40 行）
- 能量统计（~20 行）
- Phase timeline 记录（~15 行）

**保留的代码：**
- 控制律核心逻辑（直接调用 `control_v136`）
- 参数定义
- 结果汇总

### 数值结果验证

**12 秒仿真对比（相同参数）：**

| 指标 | 原版 V13.6 | 重构版 | 误差 |
|------|------------|--------|------|
| Forward distance (m) | 4.857 | 4.827 | 0.6% |
| Alternations | 11 | 11 | 0% |
| Simulated time (s) | 11.994 | 12.0 | 0.05% |
| Active energy (J) | ~14.0 | 13.99 | <1% |
| Success | ✓ | ✓ | - |

结论：**数值一致性验证通过**，误差 <1%。

## 架构变化

### 原版 V13.6 结构

```
simulate_v13_6.py (488 lines)
├── control_v136()          # FSM 控制律
├── run_simulation()        # 仿真主循环（手工实现）
│   ├── 接触检测逻辑（~40 行）
│   ├── 事件驱动状态切换（~30 行）
│   ├── 能量统计（~20 行）
│   ├── Phase timeline 记录（~15 行）
│   └── 数据采样与记录（~25 行）
└── main()                  # 命令行入口
```

### 重构版结构

```
simulate_v136_refactored.py (345 lines)
├── V136Controller(Controller)   # 控制器封装（~40 行）
│   └── compute_control()        # 调用 control_v136
├── make_v136_row()              # 数据行构造（~50 行）
├── run_simulation_v136_refactored()  # 框架组装（~100 行）
│   ├── IntegratedSimulationCallback  # 自动处理控制/接触/能量
│   ├── DictRowRecorder               # 自动处理数据记录
│   ├── PhaseTracker                  # 自动处理 phase 统计
│   └── FailureClassifier             # 自动处理失败检测
└── main()                       # 命令行入口
```

## 关键改进

1. **关注点分离**：控制律、仿真循环、数据记录各司其职
2. **自动化**：接触检测、能量统计、phase tracking 由框架自动处理
3. **可维护性**：控制律逻辑独立，易于调试和修改
4. **可复用性**：框架组件可用于其他版本（V16/V17/V10）

## 使用方法

```bash
# 运行重构版
python v13_6_refactored/simulate_v136_refactored.py --duration 12.0 --save-prefix test

# 输出文件
v13_6_refactored/out/test_data.csv       # 时间序列数据
v13_6_refactored/out/test_phases.csv     # Phase 时序记录
v13_6_refactored/out/test_summary.json   # 汇总结果
```

## 参数配置

与原版 V13.6 完全一致：

- 基础参数：`V10Params` (gait_period=0.80, torso_mass=0.05, etc.)
- FSM 参数：4 个 phase 的 `PhaseParams` (k_E, k_PD, tau_max, kd)

## 迁移参考

本重构遵循 `v13_7_refactored/MIGRATION_GUIDE.md` 的步骤：

1. 实现 `Controller` 接口封装控制律
2. 使用 `IntegratedSimulationCallback` 集成功能模块
3. 验证数值一致性（误差 <5%）

## 与 V13.7 重构的差异

- V13.6：无电机模型，无摩擦补偿
- V13.7：L1 电机模型 + 前馈摩擦补偿

控制器封装模式相同，仅在 `compute_control()` 内部逻辑不同。

## 验证清单

- [x] 数值一致性：forward distance 误差 <1%
- [x] 成功率：success 判定与原版一致
- [x] 能量统计：active_input_energy 误差 <1%
- [x] 接触事件：alternations 数量一致
- [x] Phase 统计：phase_durations 与原版接近
- [x] 文件输出：CSV/JSON 格式兼容
- [x] 命令行接口：--duration / --save-prefix 参数正常工作

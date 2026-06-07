# Refactored 版本说明

> 本文档说明项目中各个 `*_refactored` 目录的状态和用途

## 概述

这些目录包含了使用统一仿真框架 `common/simulation_framework.py` 重构后的版本。重构的目标是：
- 减少代码重复（平均减少 30-60%）
- 提高可维护性
- 标准化控制器接口

## 重构版本清单

### ✅ V13.6 Refactored (`v13_6_refactored/`)
- **状态：** 完成并验证
- **代码减少：** 33.1% (468行 → 313行)
- **数值验证：** 通过（误差 <1%）
- **用途：** 展示 FSM 控制律的框架迁移
- **大小：** 3.1 MB

### ✅ V13.7 Refactored (`v13_7_refactored/`)
- **状态：** 完成并验证
- **代码减少：** 60% (420行 → 168行)
- **数值验证：** 通过（forward distance 误差 3.1%）
- **用途：** 展示摩擦补偿控制律的框架迁移
- **大小：** 1.8 MB
- **文档：** 包含详细的 MIGRATION_GUIDE.md

### ✅ V16 Refactored (`v16_refactored/`)
- **状态：** 完成并验证
- **代码减少：** 15.3% (451行 → 382行)
- **数值验证：** 通过（行为一致，均为 fall_down）
- **用途：** 展示电机动力学的框架迁移
- **大小：** 1.1 MB

### ❌ V17 Refactored (`v17_refactored/`)
- **状态：** 废弃未使用
- **原因：** 功能直接在 `v17_state_estimation` 中实现
- **大小：** 4 KB（仅 README）
- **操作：** 可以删除

## 其他相关目录

### ⚠️ V13.7 Floquet Analysis (`v13_7_floquet_analysis/`)
- **状态：** 独立分析项目
- **用途：** V13.7 的 Floquet 稳定性分析
- **大小：** 6.7 MB
- **与主线关系：** 可能与 V13b 重复
- **建议：** 检查是否可合并到 V13b

### ⚠️ V15 Hip SEA Scaffold (`v15_hip_sea_scaffold/`)
- **状态：** 未完成的脚手架
- **用途：** V15 SEA (Series Elastic Actuator) 的早期框架
- **大小：** 5.4 MB
- **与主线关系：** V15.1 和 V15.2 是完整实现
- **建议：** 可以删除（已有完整版本）

## 决策建议

### 保留的目录（作为参考）
✅ **保留：**
- `v13_6_refactored/` - FSM 框架迁移示例
- `v13_7_refactored/` - 最完整的迁移指南
- `v16_refactored/` - 电机动力学框架示例

**原因：**
- 包含详细的迁移文档
- 可作为未来版本重构的参考
- 总共约 6 MB，空间占用可接受

**操作：**
- 在各目录 README 顶部添加 "⚠️ 这是重构实验版本，主线版本见 v13.7_friction_compensation" 标识
- 在 VERSIONS.md 中添加脚注说明

### 可删除的目录

❌ **建议删除：**
- `v17_refactored/` - 仅 4KB，已明确废弃
- `v15_hip_sea_scaffold/` - 5.4MB，未完成的脚手架，已有完整版本 V15.1/V15.2

⚠️ **需要检查后决定：**
- `v13_7_floquet_analysis/` - 6.7MB，检查是否与 V13b 重复

**预计节省空间：** 5.4 MB + 可能的 6.7 MB = 约 12 MB

## 使用场景

### 场景 1：学习框架迁移
如果需要将其他版本迁移到统一框架，参考：
1. `v13_7_refactored/MIGRATION_GUIDE.md` - 最详细的指南
2. `v13_6_refactored/README.md` - FSM 控制律示例
3. `v16_refactored/README.md` - 电机动力学示例

### 场景 2：验证重构正确性
运行对比测试：
```powershell
# V13.7 原版 vs 重构版
python v13_7_friction_compensation/simulate_v13_7.py --duration 12.0
python v13_7_refactored/simulate_v137_refactored.py --duration 12.0
```

### 场景 3：贡献新版本
新版本可以直接基于框架开发：
```python
from common.simulation_framework import Controller, IntegratedSimulationCallback

class MyController(Controller):
    def compute_control(self, model, data, t, context):
        # 实现控制律
        return torques, diagnostics
```

## 版本对应关系

| Refactored 版本 | 主线版本 | 关系 |
|----------------|---------|------|
| v13_6_refactored | v13_6_event_driven_fsm | 功能等价 |
| v13_7_refactored | v13_7_friction_compensation | 功能等价 |
| v16_refactored | v16_motor_dynamics | 功能等价 |
| v17_refactored | v17_state_estimation | 未完成（主线版本已实现） |

## 推荐阅读顺序

如果想理解框架重构：
1. `common/simulation_framework.py` - 框架代码
2. `v13_7_refactored/MIGRATION_GUIDE.md` - 迁移指南
3. `v13_7_refactored/README.md` - 架构设计
4. `v13_6_refactored/README.md` - 简化示例
5. `v16_refactored/README.md` - 电机集成

## 注意事项

### ⚠️ 使用主线版本
对于实际研究和展示，**始终使用主线版本**：
- ✅ `v13_7_friction_compensation/` （不是 v13_7_refactored）
- ✅ `v16_motor_dynamics/` （不是 v16_refactored）
- ✅ `v17_state_estimation/` （不是 v17_refactored）

Refactored 版本仅用于：
- 学习框架设计
- 迁移其他版本
- 代码架构参考

### ⚠️ 数值差异
重构版本可能有小的数值差异（<5%），原因：
- 浮点累积顺序不同
- 积分时刻微调
- 回调调用顺序

这些差异不影响功能正确性，但**论文和报告应使用主线版本的数据**。

## 相关文档

- [common/simulation_framework.py](../common/simulation_framework.py) - 框架实现
- [common/README.md](../common/README.md) - 公共库说明
- [VERSIONS.md](../VERSIONS.md) - 主线版本索引
- [PROJECT_OPTIMIZATION_PLAN.md](../PROJECT_OPTIMIZATION_PLAN.md) - 项目优化计划

---

**最后更新：** 2026-06-07  
**维护者：** 项目团队

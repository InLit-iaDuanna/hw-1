## Refactored 版本说明

本项目包含三个 `*_refactored` 目录（`v13_6_refactored/`, `v13_7_refactored/`, `v16_refactored/`），它们**不是临时实验残留**，而是基于 `common/simulation_framework.py` 统一框架的重构示例版本。

### 用途

这些版本展示如何将独立的仿真脚本迁移到统一框架：
- **减少重复代码**：仿真循环、接触检测、能量统计等逻辑统一到框架
- **标准化接口**：提供 `Controller` 抽象接口供优化工具使用
- **架构参考**：为未来版本（V17+）提供框架集成示例

### 与主版本的关系

Refactored 版本与主版本**并行存在**，而非替代关系：
- **主版本**（如 `v13_7_friction_compensation/`）：独立完整实现，稳定可靠
- **Refactored 版本**（如 `v13_7_refactored/`）：框架适配示例，代码量减少 33-60%

两者功能等价（验证误差 <5%），但架构不同。

### 实际应用

- `v13_7_refactored` 被 `auto_optimization/` 和 `parameter_explorer/` 工具依赖
- 包含完整的迁移指南（`MIGRATION_GUIDE.md` 14KB）
- 在 `render_all.py` 的渲染列表中

### 文档

详细迁移流程和架构设计见各 refactored 目录中的：
- `README.md` - 功能说明和验证结果
- `MIGRATION_GUIDE.md` - 从独立脚本迁移到框架的步骤
- `REFACTORING_REPORT.md` - 重构决策和性能对比

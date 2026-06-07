# hw-1 项目知识库

欢迎来到 hw-1 脑卒中康复步态训练辅助设备项目的知识库。

## 项目简介

hw-1 是一款面向康复机构的下肢步态训练辅助设备，专为脑卒中患者（Brunnstrom IV 期）设计。

**核心特点**：
- **轻**：≤ 6 kg（vs Lokomat 600 kg / ReWalk 23 kg）
- **柔**：髋部 SEA 柔顺辅助（vs 刚性牵引）
- **懂相位**：FSM 实时识别四相位步态
- **给数据**：5 类训练指标可量化导出

**技术路线**：基于 Compass Gait 被动动态步行理论，V01-V25 长程迭代，最终落地硬件样机。

## 快速导航

### 常见问题 (FAQ)

- [仿真相关问题](faq/simulation.md) — NaN 错误、稳定性判断、时间步长设置
- [参数设置问题](faq/parameters.md) — PD 增益、FSM 相位时长、质量范围
- [调试问题](faq/debugging.md) — 跌倒诊断、可视化工具、性能分析
- [环境配置问题](faq/environment.md) — Python 环境、依赖安装、常见错误

### 最佳实践

- [代码规范](best_practices/coding_standards.md) — 命名约定、类型注解、文档规范
- [仿真工作流](best_practices/simulation_workflow.md) — 从参数设置到结果分析的完整流程 ⭐ 新增
- [参数调优策略](best_practices/parameter_tuning.md) — 系统化参数搜索方法 ⭐ 新增
- [版本控制规范](best_practices/version_control.md) — 版本命名、commit 规范、分支管理 ⭐ 新增

### 技术决策记录 (ADR)

- [为什么选择 FSM 而非纯 PD 控制](technical_decisions/why_fsm_over_pd.md)
- [为什么 V18-V20 放弃 3D，选择 2D 路线](technical_decisions/why_2d_over_3d.md)
- [电机选型决策：MX-64AR 与摩擦补偿](technical_decisions/motor_selection.md) — 计划添加
- [为什么选择事件驱动 FSM 架构](technical_decisions/framework_design.md) — 计划添加

### 故障排查

- [常见错误](troubleshooting/common_errors.md) — 错误信息及解决方案
- [性能问题](troubleshooting/performance_issues.md) — 仿真速度、内存占用（计划添加）
- [数据问题](troubleshooting/data_problems.md) — 数据丢失、格式错误、可视化异常（计划添加）

### 其他资源

- [术语表](glossary.md) — 项目术语中英文对照
- [README](README.md) — 知识库使用说明

## 项目关键文档

建议新协作者按以下顺序阅读项目根目录文档：

1. **README.md** — 项目概述、目录结构、运行命令
2. **VERSIONS.md** — V01-V24 已完成版本的定位与结论
3. **ROADMAP.md** — V11-V25 长程规划，含决策门
4. **CLAUDE.md** — 协作约定与避坑要点

## 当前状态（2026-06-05）

- ✅ 阶段 1 (V01-V13)：2D 步态研究链条完成
- ✅ 阶段 2 (V14-V17)：2D 机械升级完成，主线已闭环
- ✅ V18-V20：3D 探索得出三次否定结果
- ✅ V22-V24：硬件设计文档链完成
- ✅ 知识库与教程系统：全面升级完成 ⭐ 新增
- ⏳ V25：实地行走（待硬件制作完成）

## 贡献

知识库由项目团队维护。如发现内容过时或错误，请：

1. 直接修改对应 Markdown 文件
2. 提交时在 commit message 中说明修改原因
3. 重大变更需在团队会议中讨论

## 搜索

使用 `Grep` 工具在知识库中搜索关键词：

```powershell
# 示例：搜索 FSM 相关内容
grep -r "FSM" knowledge_base/
```

或使用编辑器的全局搜索功能。

---

最后更新：2026-06-04

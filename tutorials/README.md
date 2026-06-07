# hw-1 交互式教程

针对新用户（或未来的自己）的分步教程，每个教程约 15-20 分钟。

---

## 教程清单

| 教程 | 时长 | 难度 | 前置要求 |
|------|------|------|----------|
| [01 - 运行第一个仿真](tutorial_01_run_first_simulation.md) | 15 分钟 | ⭐ 入门 | 无 |
| [02 - 理解 FSM 控制律](tutorial_02_understand_fsm_control.md) | 20 分钟 | ⭐⭐ 进阶 | 完成教程 01 |
| [03 - 参数调优](tutorial_03_parameter_tuning.md) | 25 分钟 | ⭐⭐⭐ 高级 | 完成教程 02 |
| [04 - 研究者深度教程](tutorial_04_research_workflow.md) | 45 分钟 | ⭐⭐⭐⭐ 研究级 | 完成教程 01-03 | ⭐ 新增
| [05 - 开发者贡献指南](tutorial_05_developer_guide.md) | 30 分钟 | ⭐⭐⭐ 高级 | 完成教程 01-02 | ⭐ 新增

---

## 推荐学习顺序

### 第 1 天：快速上手

1. **阅读 QUICKSTART.md**（30 分钟）
   - 了解项目概览
   - 配置环境

2. **教程 01：运行第一个仿真**（15 分钟）
   - 运行 V13.7 仿真
   - 查看输出结果
   - 理解成功判据

3. **打开 Dashboard**（10 分钟）
   - 浏览所有版本
   - 查看 Timeline View
   - 使用 Compare View 对比 V10 vs V13.7

---

### 第 2 天：理解控制律

1. **教程 02：理解 FSM 控制律**（20 分钟）
   - 理解 4 phase FSM 结构
   - 查看控制律代码
   - 运行不同控制策略

2. **对比实验**（20 分钟）
   - 运行 V10（PD 控制）
   - 运行 V13.6（FSM 控制）
   - 对比性能差异

---

### 第 3 天：参数调优

1. **教程 03：参数调优**（25 分钟）
   - 理解参数空间
   - 使用 Heatmap View 查看敏感性
   - 手动调整参数

2. **跨版本分析**（20 分钟）
   - 运行 `cross_version_analysis/compare_versions.py`
   - 生成稳定域可视化

---

## 教程内容预览

### Tutorial 01：运行第一个仿真

- ✅ 环境激活
- ✅ 运行 V13.7 仿真
- ✅ 理解输出文件
- ✅ 可视化查看
- ✅ 故障排查

### Tutorial 02：理解 FSM 控制律

- ✅ FSM 状态机原理
- ✅ 4 个 phase 的触发条件
- ✅ 控制律代码阅读
- ✅ 对比 V10 vs V13.6
- ✅ 摩擦补偿原理

### Tutorial 03：参数调优

- ✅ 关键参数解释
- ✅ 参数敏感性分析
- ✅ 手动调优实践
- ✅ 使用 Dashboard Heatmap
- ✅ 批量扫描工具

### Tutorial 04：研究者深度教程 ⭐ 新增

- ✅ V12 能量分析工具
- ✅ V13b Floquet 稳定性分析
- ✅ 跨版本对比分析
- ✅ 论文级图表生成
- ✅ 极限环理论与仿真对应

### Tutorial 05：开发者贡献指南 ⭐ 新增

- ✅ 创建新版本骨架
- ✅ 编写控制律代码
- ✅ 添加单元测试
- ✅ 更新文档和 Dashboard
- ✅ 提交代码和 PR

---

## 其他资源

- **QUICKSTART.md**: 30 分钟快速入门
- **LEARNING_PATHS.md**: 系统化学习路径（新手→专家）⭐ 新增
- **Dashboard**: 可视化项目总览
- **knowledge_base/**: 完整知识库（FAQ + 最佳实践 + 技术决策）
- **ROADMAP.md**: 理解长期规划
- **各版本 README.md**: 详细技术文档

---

## 推荐学习路径

**新手用户：**
1. QUICKSTART.md（30 分钟）
2. Tutorial 01 → 02 → 03（1 小时）
3. Dashboard 浏览（10 分钟）

**研究者：**
1. Tutorial 01-03（1 小时）
2. Tutorial 04 深度教程（45 分钟）
3. 查看 LEARNING_PATHS.md 路径 C

**开发者：**
1. Tutorial 01-02（35 分钟）
2. Tutorial 05 开发指南（30 分钟）
3. 查看 LEARNING_PATHS.md 路径 E

详细路径请参考：**[LEARNING_PATHS.md](../LEARNING_PATHS.md)** ⭐

---

**开始学习：打开 [tutorial_01_run_first_simulation.md](tutorial_01_run_first_simulation.md)**

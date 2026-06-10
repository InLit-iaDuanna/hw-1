# 指南针步态研究项目 - 总导航

> **快速开始：30 分钟上手本项目** → [QUICKSTART.md](QUICKSTART.md)

---

## 🎯 我是新人，从哪里开始？

### 第一步：了解项目（5 分钟）
👉 阅读 [README.md](README.md) - 项目概述和目录结构

### 第二步：快速运行（10 分钟）
👉 跟随 [QUICKSTART.md](QUICKSTART.md) 运行第一个示例

### 第三步：浏览可视化（10 分钟）
👉 打开浏览器访问 `dashboard/index.html` - 交互式版本看板

### 第四步：深入学习（可选）
👉 查看 [tutorials/](tutorials/) - 分步教程

---

## 📊 核心文档速查

| 文档 | 用途 | 阅读时间 |
|------|------|----------|
| **[README.md](README.md)** | 项目总览、环境配置 | 10 分钟 |
| **[QUICKSTART.md](QUICKSTART.md)** | 快速入门指南 | 30 分钟 |
| **[VERSIONS.md](VERSIONS.md)** | 完整版本索引（V01-V24） | 20 分钟 |
| **[VERSION_MILESTONES.md](VERSION_MILESTONES.md)** | 关键里程碑（5-8 个核心版本） | 5 分钟 ⭐ |
| **[ROADMAP.md](ROADMAP.md)** | 长期规划和决策门 | 10 分钟 |
| **[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)** | 当前进度和完成情况 | 5 分钟 |
| **[TOOLS_CHEATSHEET.md](TOOLS_CHEATSHEET.md)** | 所有命令速查表 | 随时查阅 📌 |
| **[CLAUDE.md](CLAUDE.md)** | AI 协作约定（开发者用） | 10 分钟 |

---

## 🔬 关键版本速览

| 版本 | 定位 | 可视化 | 用途 |
|------|------|--------|------|
| **V05** | 纯被动极限环证明 | ✅ [动画](v05_hybrid_compass_proof/out/) | 理论基础 |
| **V10** | 足踝滚动仿生步态 | ✅ [动画](v10_rolling_foot_biomimetic_gait/out/) | **推荐展示** ⭐ |
| **V11** | 地形扰动鲁棒性 | ✅ [报告](v11_rugged_terrain_robustness/out/) | 稳定性边界 |
| **V13** | 参数敏感性图谱 | ✅ [图谱](v13_parameter_sensitivity_atlas/out/) | 设计容差 |
| **V13.7** | 摩擦补偿控制 | ✅ [动画](v13_7_friction_compensation/out/) | **当前最成熟** ⭐ |
| **V17** | 传感器闭环估计 | ✅ [动画](v17_state_estimation/out/) | 硬件就绪 |
| **V22-V24** | 硬件设计文档 | 📄 [设计文档](v22_hardware_design/) | 样机制作 |

完整版本对比 → [VERSIONS.md](VERSIONS.md)

---

## 📚 文档库

### 核心文档（必读）
- [README.md](README.md) - 项目总览
- [QUICKSTART.md](QUICKSTART.md) - 快速入门
- [VERSIONS.md](VERSIONS.md) - 版本索引
- [ROADMAP.md](ROADMAP.md) - 长期规划

### 技术文档
- [docs/DEPENDENCY_GUIDE.md](docs/DEPENDENCY_GUIDE.md) - 依赖管理
- [docs/DATA_MANAGEMENT.md](docs/DATA_MANAGEMENT.md) - 数据组织
- [docs/CI_CD_GUIDE.md](docs/CI_CD_GUIDE.md) - CI/CD 流程
- [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) - Git 工作流

### 可视化与动画
- [docs/ANIMATIONS.md](docs/ANIMATIONS.md) - 动画制作指南
- [docs/FIGURES_INDEX.md](docs/FIGURES_INDEX.md) - 图表索引
- [docs/rendering/](docs/rendering/) - 高清渲染

### 学习资源
- [tutorials/](tutorials/) - 交互式教程
- [docs/LEARNING_PATHS.md](docs/LEARNING_PATHS.md) - 学习路径
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - 故障排查

### 分析报告
- [docs/analysis/](docs/analysis/) - 专题分析
- [docs/archived/](docs/archived/) - 历史报告

完整文档索引 → [docs/README.md](docs/README.md)

---

## 🎨 可视化看板

### 交互式 Dashboard
```powershell
# 在浏览器中打开
start dashboard/index.html
```

**功能：**
- 📊 Grid View - 所有版本卡片
- 📈 Timeline View - 项目演进时间线
- 🔄 Compare View - 版本对比
- 📉 Trends View - 性能趋势
- 🔥 Heatmap View - 参数敏感性

### 关键可视化文件
```
v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png
v06_mve_gait_homework/out/v6_mve_report.png
v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk.mp4  ⭐ 推荐
v11_rugged_terrain_robustness/out/v11_robustness_report.png
v13_7_friction_compensation/out/v137_walk.mp4  ⭐ 当前最优
```

---

## 🛠️ 常用命令速查

### 运行仿真
```powershell
# 激活环境
.\.venv-mujoco\Scripts\activate

# 运行最成熟版本（V13.7）
python v13_7_friction_compensation\simulate_v137.py --duration 12.0

# 查看可视化
python v13_7_friction_compensation\view_v137.py

# 渲染视频
python v13_7_friction_compensation\render_v137.py
```

### 数据分析
```powershell
# 横向版本对比
python cross_version_analysis/compare_versions.py

# 参数优化
python parameter_tuner/optimize.py --version v13.7

# 基准测试
python benchmarks/run_benchmarks.py
```

### 开发工具
```powershell
# 运行测试
pytest tests/

# 代码格式化
black .

# Linting
ruff check .
```

完整命令列表 → [TOOLS_CHEATSHEET.md](TOOLS_CHEATSHEET.md)

---

## 📖 推荐阅读路径

### 路径 1：快速了解（1 小时）
1. [README.md](README.md) - 10 分钟
2. [VERSION_MILESTONES.md](VERSION_MILESTONES.md) - 5 分钟
3. [QUICKSTART.md](QUICKSTART.md) - 30 分钟
4. `dashboard/index.html` - 15 分钟

### 路径 2：深入研究（1 天）
1. 路径 1 的所有内容
2. [VERSIONS.md](VERSIONS.md) - 完整版本索引
3. [ROADMAP.md](ROADMAP.md) - 理解战略规划
4. [tutorials/](tutorials/) - 跟随教程实践
5. 关键版本代码阅读（V05, V10, V13.7）

### 路径 3：贡献开发（持续）
1. 路径 2 的所有内容
2. [CLAUDE.md](CLAUDE.md) - 协作约定
3. [docs/CI_CD_GUIDE.md](docs/CI_CD_GUIDE.md) - 开发流程
4. [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) - Git 规范
5. 阅读 `common/` 公共库代码

---

## 🎓 学习资源

### 教程系列
- [tutorials/01_first_simulation.md](tutorials/01_first_simulation.md) - 第一个仿真
- [tutorials/02_understanding_versions.md](tutorials/02_understanding_versions.md) - 理解版本演进
- [tutorials/03_parameter_tuning.md](tutorials/03_parameter_tuning.md) - 参数调优
- [tutorials/04_visualization.md](tutorials/04_visualization.md) - 可视化技巧

### 参考资料
- **论文：** [publications/](publications/)
- **演示文稿：** [presentations/](presentations/)
- **外部资源：** [references/](references/)

---

## 💡 快速问题解答

### Q: 项目目标是什么？
A: 研究被动和准被动动态步行，从理论证明到硬件实现。最终目标是制作一个可行走的物理样机。

### Q: 哪个版本最值得看？
A: **V10**（足踝滚动，最佳展示）和 **V13.7**（摩擦补偿，当前最成熟）

### Q: 如何快速运行一个示例？
A: 见 [QUICKSTART.md](QUICKSTART.md) 第 3 节

### Q: 文档太多，看哪些？
A: 必读 4 个：README → QUICKSTART → VERSION_MILESTONES → dashboard

### Q: 遇到错误怎么办？
A: 查看 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### Q: 想参与开发？
A: 先读 [CLAUDE.md](CLAUDE.md) 和 [docs/CI_CD_GUIDE.md](docs/CI_CD_GUIDE.md)

---

## 📞 项目信息

- **仓库：** `D:\Dunna\Documents\hw-1`
- **Python 环境：** `.venv-mujoco`
- **主要工具：** MuJoCo, NumPy, Matplotlib, imageio
- **文档更新：** 2026-06-07

---

**提示：** 如果这是你第一次打开项目，建议直接前往 [QUICKSTART.md](QUICKSTART.md) 开始！

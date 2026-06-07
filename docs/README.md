# 文档库索引

> 所有项目文档的组织和索引

## 📁 文档结构

```
docs/
├── README.md (本文件)
├── DEPENDENCY_GUIDE.md         # 依赖管理
├── DATA_MANAGEMENT.md          # 数据组织
├── CI_CD_GUIDE.md              # CI/CD 流程
├── GIT_WORKFLOW.md             # Git 工作流
├── ANIMATIONS.md               # 动画制作
├── FIGURES_INDEX.md            # 图表索引
├── LEARNING_PATHS.md           # 学习路径
├── TROUBLESHOOTING.md          # 故障排查
├── analysis/                   # 专题分析
│   └── v18_v21_negative_results.md
├── rendering/                  # 渲染指南
│   └── HD_RENDERING_GUIDE.md
└── archived/                   # 历史文档
    ├── refactored_versions/
    └── [各类历史报告]
```

## 📚 按主题分类

### 🚀 入门文档
- [../README.md](../README.md) - 项目总览
- [../QUICKSTART.md](../QUICKSTART.md) - 快速入门
- [../INDEX.md](../INDEX.md) - 总导航

### 📖 版本文档
- [../VERSIONS.md](../VERSIONS.md) - 完整版本索引
- [../VERSION_MILESTONES.md](../VERSION_MILESTONES.md) - 关键里程碑
- [../PROJECT_PROGRESS.md](../PROJECT_PROGRESS.md) - 项目进度
- [../ROADMAP.md](../ROADMAP.md) - 长期规划

### 🔧 技术文档
- [DEPENDENCY_GUIDE.md](DEPENDENCY_GUIDE.md) - 依赖管理
- [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md) - 数据组织
- [CI_CD_GUIDE.md](CI_CD_GUIDE.md) - 持续集成
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - 版本控制

### 🎨 可视化文档
- [ANIMATIONS.md](ANIMATIONS.md) - 动画制作指南
- [FIGURES_INDEX.md](FIGURES_INDEX.md) - 图表索引
- [rendering/HD_RENDERING_GUIDE.md](rendering/HD_RENDERING_GUIDE.md) - 高清渲染

### 📊 分析文档
- [analysis/v18_v21_negative_results.md](analysis/v18_v21_negative_results.md) - 3D 探索失败分析

### 🎓 学习资源
- [LEARNING_PATHS.md](LEARNING_PATHS.md) - 推荐学习路径
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 常见问题解决
- [../tutorials/](../tutorials/) - 交互式教程

### 🛠️ 开发文档
- [../CLAUDE.md](../CLAUDE.md) - AI 协作约定
- [../TOOLS_CHEATSHEET.md](../TOOLS_CHEATSHEET.md) - 命令速查

### 📦 历史归档
- [archived/](archived/) - 历史报告和废弃文档
  - 优化报告
  - 迁移报告
  - 验证报告
  - Refactored 版本说明

## 🔍 按用户角色分类

### 新用户（第一次接触项目）
1. [../INDEX.md](../INDEX.md) - 总导航
2. [../README.md](../README.md) - 项目概览
3. [../QUICKSTART.md](../QUICKSTART.md) - 快速入门
4. [../VERSION_MILESTONES.md](../VERSION_MILESTONES.md) - 关键版本

### 研究者（深入理解原理）
1. [../VERSIONS.md](../VERSIONS.md) - 完整版本演进
2. [../ROADMAP.md](../ROADMAP.md) - 研究规划
3. [analysis/](analysis/) - 专题分析
4. 各版本 README.md

### 开发者（参与代码贡献）
1. [../CLAUDE.md](../CLAUDE.md) - 协作约定
2. [CI_CD_GUIDE.md](CI_CD_GUIDE.md) - 开发流程
3. [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - 代码管理
4. [DEPENDENCY_GUIDE.md](DEPENDENCY_GUIDE.md) - 环境配置

### 演示者（准备展示材料）
1. [../VERSION_MILESTONES.md](../VERSION_MILESTONES.md) - 核心成果
2. [ANIMATIONS.md](ANIMATIONS.md) - 动画资源
3. [FIGURES_INDEX.md](FIGURES_INDEX.md) - 图表资源
4. [../dashboard/](../dashboard/) - 交互式看板

## 📝 文档编写规范

### 命名规范
- 使用 `UPPER_SNAKE_CASE.md` 表示重要指南
- 使用 `lower_snake_case.md` 表示一般文档
- README.md 用于目录索引

### 结构规范
```markdown
# 标题

> 简短描述（一句话）

## 概述
[2-3 段概述]

## 主要内容
[详细内容]

## 参考资料
[相关链接]
```

### 交叉引用
使用相对路径链接：
```markdown
详见 [QUICKSTART.md](../QUICKSTART.md)
参考 [common/README.md](../common/README.md)
```

## 🔄 文档维护

### 更新频率
- **核心文档**（README, QUICKSTART, VERSIONS）：每个新版本后更新
- **技术文档**（DEPENDENCY, CI_CD）：变更时更新
- **分析文档**：实验完成后添加

### 归档策略
当文档过时或被替代时：
1. 移动到 `archived/` 目录
2. 在新文档中说明"合并自"或"替代"
3. 更新本索引

### 清理规则
- 临时笔记：实验结束后删除或归档
- 重复内容：合并为单一文档
- 过时报告：归档但不删除（保留历史）

## 🆘 获取帮助

- **找不到文档？** 查看 [../INDEX.md](../INDEX.md) 总导航
- **遇到技术问题？** 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **想参与贡献？** 查看 [../CLAUDE.md](../CLAUDE.md)

---

**最后更新：** 2026-06-07

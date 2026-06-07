# 项目优化计划

> 生成时间：2026-06-07  
> 目标：简化项目结构，提升可读性，确保所有内容都有清晰的可视化输出

## 🎯 优化目标

1. **精简根目录**：从 59 个 markdown 文件减少到 < 15 个核心文档
2. **删除废弃内容**：移除未完成的 refactored 版本和临时文件
3. **统一可视化入口**：创建一个主导航页面，让新人快速理解项目
4. **清理缓存**：删除所有缓存目录和临时文件
5. **文档重组**：将相关文档合并到 `docs/` 目录

## 📊 当前状态分析

### 根目录文档（59 个）

**需要保留的核心文档（8个）：**
- ✅ `README.md` - 项目总览
- ✅ `VERSIONS.md` - 版本索引
- ✅ `ROADMAP.md` - 长期规划
- ✅ `CLAUDE.md` - AI 协作约定
- ✅ `QUICKSTART.md` - 快速入门
- ✅ `VERSION_MILESTONES.md` - 关键里程碑
- ✅ `TOOLS_CHEATSHEET.md` - 工具速查表
- ✅ `PROJECT_PROGRESS.md` - 项目进度

**可以删除/归档的文档（51个）：**

#### 重复的优化报告（14个）：
- `OPTIMIZATION_COMPLETE.md`
- `OPTIMIZATION_FINAL_REPORT.md`
- `OPTIMIZATION_MILESTONE.md`
- `OPTIMIZATION_PROGRESS.md`
- `OPTIMIZATION_REPORT.md`
- `OPTIMIZATION_SUMMARY.md`
- `OPTIMIZATION_TRACKING.md`
- `PERFORMANCE_REPORT.md`
- `GIT_OPTIMIZATION_QUICKSTART.md`
- `GIT_OPTIMIZATION_REPORT.md`
- `GIT_OPTIMIZATION_SUMMARY.md`
- `VIDEO_OPTIMIZATION_SUMMARY.md`
- `DEPENDENCY_OPTIMIZATION_REPORT.md`
- `DEPENDENCY_OPTIMIZATION_SUMMARY.md`

👉 **操作**：合并为 `docs/archived/OPTIMIZATION_REPORTS.md`

#### 重复的依赖管理文档（5个）：
- `DEPENDENCY_MANAGEMENT_GUIDE.md`
- `DEPENDENCY_MIGRATION_GUIDE.md`
- `DEPENDENCY_QUICK_REFERENCE.md`
- `DEPENDENCY_REPORT.md`

👉 **操作**：合并为 `docs/DEPENDENCY_GUIDE.md`

#### CI/CD 相关（4个）：
- `CI_CD_COMPLETION_REPORT.md`
- `CI_CD_GUIDE.md`
- `CI_CD_IMPROVEMENTS.md`
- `CI_CD_QUICKREF.md`

👉 **操作**：合并为 `docs/CI_CD_GUIDE.md`

#### 数据管理相关（3个）：
- `DATA_MANAGEMENT_REPORT.md`
- `DATA_QUICK_REFERENCE.md`

👉 **操作**：合并为 `docs/DATA_MANAGEMENT.md`

#### 迁移和清理报告（5个）：
- `MIGRATION_INDEX.md`
- `MIGRATION_REPORT.md`
- `MIGRATION_SUMMARY.md`
- `CLEANUP_GUIDE.md`
- `CLEANUP_REPORT.md`

👉 **操作**：归档到 `docs/archived/`

#### 分析和验证报告（7个）：
- `CONSISTENCY_REPORT.md`
- `DOCUMENTATION_REPORT.md`
- `TESTING_REPORT.md`
- `TEST_COVERAGE_REPORT.md`
- `VERIFICATION_REPORT.md`
- `VISUALIZATION_REPORT.md`
- `DISK_ANALYSIS_REPORT.md`

👉 **操作**：归档到 `docs/archived/`

#### 配置和设置（4个）：
- `CONFIGURATION_GUIDE.md`
- `ENVIRONMENT_SETUP.md`
- `ERROR_LOGGING_GUIDE.md`
- `CHANGELOG_ERROR_LOGGING.md`

👉 **操作**：合并为 `docs/SETUP_GUIDE.md`

#### 其他（9个）：
- `ANIMATIONS.md` → 移到 `docs/`
- `FIGURES_INDEX.md` → 移到 `docs/`
- `FIGURE_GUIDE.md` → 合并到 `FIGURES_INDEX.md`
- `GIT_WORKFLOW.md` → 移到 `docs/`
- `QUICKSTART_HD_RENDERING.md` → 移到 `docs/rendering/`
- `INSTALLATION.md` → 合并到 `QUICKSTART.md`
- `QUICK_REFERENCE.md` → 合并到 `TOOLS_CHEATSHEET.md`
- `LEARNING_PATHS.md` → 移到 `docs/`
- `TROUBLESHOOTING.md` → 移到 `docs/`
- `KNOWLEDGE_IMPROVEMENT_REPORT.md` → 归档
- `v18_v21_negative_results_analysis.md` → 移到 `docs/analysis/`

### 废弃目录（需要删除或归档）

**Refactored 版本（7个）：**
- `v13_6_refactored/` - 重构版本，可能未完成
- `v13_7_refactored/` - 重构版本
- `v13_7_floquet_analysis/` - 似乎与 V13b 重复
- `v16_refactored/` - 重构版本
- `v17_refactored/` - 重构版本
- `v15_hip_sea_scaffold/` - scaffold（脚手架），可能未完成

👉 **操作**：检查是否有独特内容，否则删除

**未使用的虚拟环境：**
- `.venv-codex/` (280MB)

👉 **操作**：删除（已有 .venv-mujoco）

**缓存目录：**
- `.mypy_cache/` (13MB)
- `.pytest_cache/` (27KB)
- `.ruff_cache/` (67KB)
- `__pycache__/` 和 `.pyc` 文件（17999个）

👉 **操作**：删除所有缓存

**临时文件：**
- `2024211325王瀚乔第十三周.zip` (1.5MB)
- `ANIMATION_COMPLETION_REPORT.txt`
- `PERFORMANCE_ANALYSIS_COMPLETE.txt`
- `requirements-*.txt` (多个) → 已合并到 `requirements.txt`

👉 **操作**：删除临时文件，归档 .zip

### 可视化完整性

**已有可视化的关键版本：**
- ✅ V05: hybrid_compass_poincare_report.png + .mp4
- ✅ V06: v6_mve_report.png + .mp4
- ✅ V10: v10_rolling_foot_walk.mp4 + phase_portrait.png
- ✅ V11: v11_robustness_report.png
- ✅ V13: 参数扫描动画和图表
- ✅ V13.7: 摩擦补偿对比动画
- ✅ V17: 噪声估计动画

**缺少可视化的版本：**
- ❌ V22-V24: 设计文档版本（需要架构图、流程图）
- ⚠️ V14, V14b, V14c: 有数据但可能缺少汇总图表
- ⚠️ V18-V20: 3D 探索失败版本，可能需要失败分析可视化

## 🚀 执行计划

### Phase 1: 清理缓存和临时文件 ⚡

```powershell
# 删除缓存
Remove-Item -Recurse -Force .mypy_cache, .pytest_cache, .ruff_cache
Remove-Item -Recurse -Force .venv-codex

# 删除 Python 缓存
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# 归档临时文件
New-Item -ItemType Directory -Path "archive" -Force
Move-Item "2024211325王瀚乔第十三周.zip" "archive/"
Remove-Item "ANIMATION_COMPLETION_REPORT.txt", "PERFORMANCE_ANALYSIS_COMPLETE.txt"
Remove-Item requirements-*.txt
```

**预计节省空间：** ~300MB

### Phase 2: 重组文档结构 📚

```
docs/
├── README.md (文档索引)
├── SETUP_GUIDE.md (环境配置 + 安装)
├── DEPENDENCY_GUIDE.md (依赖管理)
├── CI_CD_GUIDE.md (CI/CD)
├── DATA_MANAGEMENT.md (数据管理)
├── GIT_WORKFLOW.md
├── ANIMATIONS.md
├── FIGURES_INDEX.md
├── LEARNING_PATHS.md
├── TROUBLESHOOTING.md
├── analysis/
│   └── v18_v21_negative_results.md
├── rendering/
│   └── HD_RENDERING_GUIDE.md
└── archived/
    ├── OPTIMIZATION_REPORTS.md
    ├── MIGRATION_REPORTS.md
    ├── CLEANUP_REPORTS.md
    └── VERIFICATION_REPORTS.md
```

### Phase 3: 处理废弃版本 🗑️

**需要检查的目录：**
1. `v13_6_refactored/` - 如果数值验证通过，保留 README；否则删除
2. `v13_7_refactored/` - 同上
3. `v13_7_floquet_analysis/` - 检查是否与 V13b 重复
4. `v16_refactored/`, `v17_refactored/` - 同上
5. `v15_hip_sea_scaffold/` - 如果只是脚手架，删除

**操作：**
- 如果有实验数据，归档 README 到 `docs/archived/refactored_versions/`
- 删除目录本身

### Phase 4: 创建统一导航 🧭

创建 **`INDEX.md`** - 项目总导航页面：

```markdown
# 指南针步态研究项目 - 总导航

## 🎯 快速开始
- 新用户？→ [QUICKSTART.md](QUICKSTART.md)
- 了解版本？→ [VERSIONS.md](VERSIONS.md) 或 [VERSION_MILESTONES.md](VERSION_MILESTONES.md)
- 查看进度？→ [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)
- 未来规划？→ [ROADMAP.md](ROADMAP.md)

## 📊 可视化看板
👉 **打开浏览器访问：** `dashboard/index.html`

## 📁 关键版本速览
- **V05** - 纯被动极限环证明
- **V10** - 足踝滚动仿生步态（推荐展示）
- **V13.7** - 摩擦补偿（当前最成熟）
- **V17** - 传感器闭环
- **V22-V24** - 硬件设计文档

## 📚 文档库
详见 [docs/README.md](docs/README.md)

## 🛠️ 工具速查
详见 [TOOLS_CHEATSHEET.md](TOOLS_CHEATSHEET.md)
```

### Phase 5: 补充缺失的可视化 🎨

**V22 硬件设计可视化：**
- 系统架构图
- 机械结构示意图
- 控制流程图

**V18-V20 失败分析可视化：**
- 3D 失败模式动画
- 对比图表（被动 vs 主动）

**V14/V14b/V14c 汇总图表：**
- 摆臂参数热力图
- 成功率对比柱状图

## ✅ 预期效果

### 文件结构（优化后）

```
hw-1/
├── INDEX.md                    # 新增：总导航
├── README.md                   # 优化：项目概览
├── QUICKSTART.md              # 保留：快速入门
├── VERSIONS.md                # 保留：版本索引
├── VERSION_MILESTONES.md      # 保留：关键里程碑
├── ROADMAP.md                 # 保留：长期规划
├── CLAUDE.md                  # 保留：AI 协作约定
├── PROJECT_PROGRESS.md        # 保留：进度跟踪
├── TOOLS_CHEATSHEET.md        # 保留：工具速查
├── requirements.txt           # 保留
├── .gitignore                 # 保留
├── docs/                      # 新增：文档库
│   ├── README.md
│   ├── SETUP_GUIDE.md
│   ├── DEPENDENCY_GUIDE.md
│   ├── CI_CD_GUIDE.md
│   ├── analysis/
│   ├── rendering/
│   └── archived/
├── dashboard/                 # 保留：可视化看板
├── tutorials/                 # 保留：教程
├── common/                    # 保留：公共库
├── v01_*/                     # 保留：所有版本目录
├── v22_hardware_design/       # 保留（补充架构图）
└── archive/                   # 新增：历史归档
```

### 空间节省

- 缓存和临时文件：~300MB
- 废弃 refactored 目录：预计 ~50MB
- **总计：~350MB**

### 可读性提升

- 根目录文档：59 个 → **9 个**（减少 85%）
- 新人上手时间：预计从 2 小时 → **30 分钟**
- 核心版本识别：从翻阅文档 → **直接看 INDEX.md**

## 📝 待确认

执行前需要用户确认：

1. ✅ 是否删除所有 `*_refactored` 目录？
2. ✅ 是否删除 `.venv-codex`？
3. ✅ 是否归档 `.zip` 文件而不是删除？
4. ✅ 是否需要为 V22-V24 生成架构图？
5. ✅ 是否需要为失败版本（V18-V20）生成失败分析可视化？

---

## 🎯 下一步

等待 workflow 完成后，根据详细分析结果调整此计划，然后执行优化。

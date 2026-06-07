# hw-1 项目知识库使用说明

本知识库为 hw-1 脑卒中康复步态训练辅助设备项目提供集中化的文档、FAQ、技术决策和故障排查指南。

## 目录结构

```
knowledge_base/
├── index.md                    # 知识库首页（从这里开始）
├── glossary.md                 # 术语表（中英文对照）
├── README.md                   # 本文件
│
├── faq/                        # 常见问题
│   ├── simulation.md           # 仿真相关问题（NaN、稳定性、时间步长）
│   ├── parameters.md           # 参数设置问题（PD 增益、FSM、质量范围）
│   ├── debugging.md            # 调试问题（跌倒诊断、可视化、性能分析）
│   └── environment.md          # 环境配置问题（Python、依赖、PowerShell）
│
├── best_practices/             # 最佳实践
│   ├── coding_standards.md    # 代码规范
│   ├── simulation_workflow.md # 仿真工作流
│   ├── parameter_tuning.md    # 参数调优策略
│   └── version_control.md     # 版本控制规范
│
├── technical_decisions/        # 技术决策记录 (ADR)
│   ├── why_fsm_over_pd.md     # 为什么选择 FSM 而非纯 PD
│   ├── why_2d_over_3d.md      # 为什么 V18-V20 放弃 3D
│   ├── motor_selection.md     # 电机选型决策
│   └── framework_design.md    # FSM 架构设计
│
└── troubleshooting/            # 故障排查
    ├── common_errors.md        # 常见错误及解决方案
    ├── performance_issues.md   # 性能问题
    └── data_problems.md        # 数据问题
```

## 快速开始

### 新协作者入门

**推荐阅读顺序**：

1. **项目概览**（项目根目录）
   - [README.md](../README.md) — 项目概述、目录结构、运行命令
   - [VERSIONS.md](../VERSIONS.md) — V01-V24 版本索引
   - [ROADMAP.md](../ROADMAP.md) — V11-V25 长程规划

2. **协作约定**（项目根目录）
   - [CLAUDE.md](../CLAUDE.md) — 协作约定与避坑要点

3. **知识库核心文档**（本目录）
   - [index.md](index.md) — 知识库导航
   - [glossary.md](glossary.md) — 术语表（快速查阅）

4. **按需深入**
   - 遇到仿真问题 → [faq/simulation.md](faq/simulation.md)
   - 不知如何调参 → [faq/parameters.md](faq/parameters.md)
   - 环境配置报错 → [faq/environment.md](faq/environment.md)
   - 想了解设计决策 → [technical_decisions/](technical_decisions/)

**预计时间**：1-2 小时通读核心文档，按需查阅 FAQ。

### 遇到问题时

**步骤 1：查阅 FAQ**

```
问题类型             → 查阅文档
仿真出现 NaN         → faq/simulation.md#Q1
不知如何设置 PD 增益  → faq/parameters.md#Q1
仿真跌倒了           → faq/debugging.md#Q1
pip 安装超时         → faq/environment.md#Q2
```

**步骤 2：搜索关键词**

使用 `Grep` 工具或编辑器全局搜索：

```powershell
# 在知识库中搜索 "FSM"
cd D:\Dunna\Documents\hw-1\knowledge_base
grep -r "FSM" .

# 或使用 PowerShell
Get-ChildItem -Recurse -Include *.md | Select-String "FSM"
```

**步骤 3：查看相关技术决策**

如果问题涉及设计选择，查阅 `technical_decisions/`：

```
为什么用 FSM？        → technical_decisions/why_fsm_over_pd.md
为什么不做 3D？       → technical_decisions/why_2d_over_3d.md
如何选电机？          → technical_decisions/motor_selection.md
```

**步骤 4：查看版本文档**

如果问题与特定版本相关，查阅版本 README：

```
V10 基线如何运行？    → v10_rolling_foot_biomimetic_gait/README.md
V13.6 FSM 如何用？   → v13_6_event_driven_fsm/README.md
V22 硬件如何设计？   → v22_hardware_design/README.md
```

## 使用场景

### 场景 1：配置新开发环境

**需求**：在新机器上配置 hw-1 开发环境。

**文档链**：
1. [faq/environment.md#Q1](faq/environment.md) — Python 环境配置
2. [faq/environment.md#Q2](faq/environment.md) — 依赖安装（阿里云镜像）
3. [faq/environment.md#Q5](faq/environment.md) — PyCharm 配置

### 场景 2：运行 V10 baseline 仿真

**需求**：运行 V10 baseline，验证环境正常。

**步骤**：

```powershell
# 1. 切换到项目目录
cd D:\Dunna\Documents\hw-1

# 2. 运行 V10 view 脚本
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py
```

**预期结果**：打开 MuJoCo viewer，机器人稳定行走 ~5 秒。

**故障排查**：
- 报错 `ModuleNotFoundError: No module named 'mujoco'` → [faq/environment.md#Q2](faq/environment.md)
- 报错 `ModuleNotFoundError: No module named 'common'` → [faq/environment.md#Q12](faq/environment.md)
- 仿真 NaN → [faq/simulation.md#Q1](faq/simulation.md)

### 场景 3：调整 FSM 参数

**需求**：修改 V13.6 FSM 的相位参数，提高成功率。

**文档链**：
1. [faq/parameters.md#Q2](faq/parameters.md) — FSM 相位时长确定
2. [best_practices/parameter_tuning.md](best_practices/parameter_tuning.md) — 参数调优策略
3. [technical_decisions/why_fsm_over_pd.md](technical_decisions/why_fsm_over_pd.md) — FSM 设计理念

**参考配置**：V13.6.1 best candidate（在技术决策文档中）

### 场景 4：理解为什么不做 3D

**需求**：向导师/评审解释为什么放弃 3D 化路线。

**文档**：[technical_decisions/why_2d_over_3d.md](technical_decisions/why_2d_over_3d.md)

**关键论据**：
1. V18 证明侧向被动稳定不存在（物理本质）
2. V19 证明髋外展修正能力不足 5-10×
3. V20 步宽控制架构完成但基线不稳定
4. 2D 导轨约束是产品安全特性，非缺陷
5. 成本和时间约束（3D 翻倍预算）

### 场景 5：准备中期汇报

**需求**：整理项目成果，准备中期汇报 PPT。

**推荐材料**：

1. **项目定位**：[../README.md](../README.md) + 记忆 `project-hw1-rehab-device`
2. **版本演化**：[../VERSIONS.md](../VERSIONS.md) 依赖树图
3. **关键指标**：
   - V10 baseline: forward=4.62m, alt_td=10, CoT=0.07
   - V13 参数盆地: 16.7% (孤立点解)
   - V13.6 FSM: 中央域，语义清晰
   - V14b 摆臂: 40% (2.8× 提升)
   - V17 传感器: noise_scale=2× 通过
   - V18-V20: 三次否定结果
   - V22 硬件: BOM 6500-8000 元
4. **技术亮点**：
   - [technical_decisions/why_fsm_over_pd.md](technical_decisions/why_fsm_over_pd.md) — FSM 优势
   - [technical_decisions/why_2d_over_3d.md](technical_decisions/why_2d_over_3d.md) — 务实决策
5. **可视化素材**：
   - v10/out/v10_rolling_foot_walk.mp4
   - v11/out/v11_robustness_report.png
   - v12/out/v12_report.png
   - v13/out/v13_atlas_report.png

## 维护与更新

### 何时更新知识库

**触发条件**：

1. **新版本完成**：更新 FAQ 中的参考版本号和参数
2. **重大技术决策**：添加新的 ADR（技术决策记录）
3. **发现新坑**：更新 troubleshooting/ 和 faq/
4. **最佳实践变化**：更新 best_practices/
5. **术语新增**：更新 glossary.md

### 如何贡献

**步骤**：

1. **编辑相应 Markdown 文件**
   - 保持格式一致（参考现有文档）
   - 添加内部链接和相关资源

2. **更新 index.md**（如果添加新文件）
   - 在导航中添加链接

3. **提交变更**
   ```powershell
   git add knowledge_base/
   git commit -m "docs: update knowledge base - [具体变更]"
   ```

4. **说明修改原因**
   - commit message 中简要说明
   - 重大变更在团队会议中讨论

### 文档规范

**Markdown 格式**：

- 使用标准 Markdown 语法
- 代码块指定语言（\`\`\`python, \`\`\`powershell）
- 表格对齐
- 内部链接使用相对路径

**内容风格**：

- **FAQ**: 问答格式，每个问题独立，包含代码示例
- **技术决策**: ADR 格式（背景/问题/决策/理由/影响）
- **最佳实践**: 规范 + 示例 + 反例
- **故障排查**: 症状 → 原因 → 解决方案

**示例问题格式**：

```markdown
### Q1: 问题标题

**常见原因**：
1. 原因 1
2. 原因 2

**解决方案**：
[具体步骤或代码]

**验证**：
[如何确认问题解决]

**相关资源**：
- [相关文档链接]
```

## 工具与脚本

### 搜索脚本（可选）

创建简单的搜索脚本：

```powershell
# scripts/search_kb.ps1
param(
    [string]$keyword
)

Write-Host "Searching for '$keyword' in knowledge base..." -ForegroundColor Green

$results = Get-ChildItem -Path "D:\Dunna\Documents\hw-1\knowledge_base" -Recurse -Include *.md |
    Select-String -Pattern $keyword -Context 1

foreach ($result in $results) {
    Write-Host "`n$($result.Path):" -ForegroundColor Yellow
    Write-Host "  Line $($result.LineNumber): $($result.Line)" -ForegroundColor Cyan
}
```

**使用**：

```powershell
.\scripts\search_kb.ps1 "FSM"
```

### 生成静态网站（可选）

使用 MkDocs 生成静态网站：

**安装 MkDocs**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip install mkdocs mkdocs-material
```

**配置** (`mkdocs.yml`，项目根目录)：

```yaml
site_name: hw-1 Knowledge Base
theme:
  name: material
  palette:
    primary: indigo
    accent: indigo

docs_dir: knowledge_base
site_dir: knowledge_base_site

nav:
  - Home: index.md
  - Glossary: glossary.md
  - FAQ:
    - Simulation: faq/simulation.md
    - Parameters: faq/parameters.md
    - Debugging: faq/debugging.md
    - Environment: faq/environment.md
  - Best Practices:
    - Coding Standards: best_practices/coding_standards.md
    - Simulation Workflow: best_practices/simulation_workflow.md
    - Parameter Tuning: best_practices/parameter_tuning.md
    - Version Control: best_practices/version_control.md
  - Technical Decisions:
    - FSM vs PD: technical_decisions/why_fsm_over_pd.md
    - 2D vs 3D: technical_decisions/why_2d_over_3d.md
    - Motor Selection: technical_decisions/motor_selection.md
  - Troubleshooting:
    - Common Errors: troubleshooting/common_errors.md
    - Performance: troubleshooting/performance_issues.md
    - Data Problems: troubleshooting/data_problems.md
```

**生成网站**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m mkdocs build
```

**本地预览**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m mkdocs serve
# 访问 http://127.0.0.1:8000
```

## 常见问题

### 知识库文档与版本 README 有什么区别？

| 类型 | 作用 | 示例 |
|-----|------|------|
| 版本 README | 特定版本的说明文档 | v10_rolling_foot_biomimetic_gait/README.md |
| 知识库 FAQ | 跨版本的通用问题 | faq/simulation.md (适用所有版本) |
| 知识库 ADR | 技术决策的完整记录 | technical_decisions/why_fsm_over_pd.md |

**原则**：
- 版本特定内容 → 版本 README
- 通用知识和方法 → 知识库
- 重大决策的背景和理由 → ADR

### 如何处理过时的信息？

**发现过时内容时**：

1. **标记过时**（如果信息仍有历史价值）
   ```markdown
   > ⚠️ **已过时**：此方法适用于 V10，V13.6+ 请使用 FSM。
   ```

2. **更新内容**（如果信息可更新）
   ```markdown
   ~~旧方法~~

   **推荐方法**（2026-06-04 更新）：
   [新方法]
   ```

3. **删除内容**（如果完全不适用）
   - 在 commit message 中说明删除原因

### 知识库太大，如何快速定位？

**技巧**：

1. **从 index.md 导航**：按问题类型快速跳转
2. **使用 glossary.md**：查术语定义和相关文档链接
3. **善用编辑器搜索**：Ctrl+Shift+F 全局搜索
4. **记住常用文档**：
   - 仿真问题 → faq/simulation.md
   - 参数问题 → faq/parameters.md
   - 设计决策 → technical_decisions/

## 反馈与建议

**如果你发现**：
- 文档有误或过时
- 缺少重要问题的解答
- 格式混乱难以阅读
- 术语表缺少关键术语

**请**：
- 直接修改并提交（小改动）
- 或在团队会议中提出（大改动）

**知识库是活文档，由项目团队共同维护。**

---

**相关资源**：
- [项目 README](../README.md)
- [VERSIONS.md](../VERSIONS.md)
- [ROADMAP.md](../ROADMAP.md)
- [CLAUDE.md](../CLAUDE.md)

---

**最后更新**: 2026-06-04  
**维护者**: hw-1 项目团队

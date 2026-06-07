# Git 优化快速参考指南

## 已完成的优化

### 1. 配置文件更新
- ✅ `.gitignore` - 增强排除规则（ABAQUS、Jupyter、数据文件）
- ✅ `.gitattributes` - 行尾符规范化、Git LFS 配置
- ✅ `GIT_WORKFLOW.md` - 完整工作流文档
- ✅ `GIT_OPTIMIZATION_REPORT.md` - 详细优化报告

### 2. GitHub 模板
- ✅ `.github/ISSUE_TEMPLATE/bug_report.md`
- ✅ `.github/ISSUE_TEMPLATE/feature_request.md`
- ✅ `.github/ISSUE_TEMPLATE/version_request.md`
- ✅ `.github/PULL_REQUEST_TEMPLATE.md`

### 3. 清理脚本
- ✅ `git_optimization_cleanup.ps1` - 自动化清理脚本

---

## 立即执行（10分钟）

### 选项 A: 自动化清理（推荐）

```powershell
cd D:\Dunna\Documents\hw-1
.\git_optimization_cleanup.ps1
```

这个脚本会：
1. 移除敏感的 ABAQUS .env 文件
2. 询问是否移除 ABAQUS 输出文件（.odb, .prt）
3. 暂存所有新配置文件
4. 提供标准化的提交信息
5. 可选择立即提交或稍后手动提交

### 选项 B: 手动清理

```powershell
cd D:\Dunna\Documents\hw-1

# 1. 移除敏感文件
git rm --cached fea_heel_strike/out/Job_HeelStrike.env

# 2. 可选：移除 ABAQUS 输出文件
git rm --cached fea_heel_strike/out/*.odb
git rm --cached fea_heel_strike/out/*.prt

# 3. 暂存新配置文件
git add .gitignore .gitattributes GIT_WORKFLOW.md GIT_OPTIMIZATION_REPORT.md
git add .github/ISSUE_TEMPLATE/*.md .github/PULL_REQUEST_TEMPLATE.md

# 4. 提交
git commit -m "chore: optimize Git configuration and workflow

- Update .gitignore to exclude ABAQUS output and data files
- Add .gitattributes for line endings and Git LFS configuration
- Add comprehensive Git workflow documentation
- Add Issue and PR templates for better collaboration
- Remove sensitive ABAQUS env file from tracking
"
```

---

## 近期执行（按需）

### 1. 初始化分支结构（如果需要）

```powershell
# 确认当前在主分支
git branch -M main

# 创建开发分支
git checkout -b develop

# 推送到远程（如果已配置远程仓库）
git push -u origin main
git push -u origin develop
```

### 2. 安装 Pre-commit Hooks

```powershell
.\.venv-mujoco\Scripts\activate
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### 3. 初始化 Git LFS（渐进式方案）

```powershell
# 1. 安装 Git LFS
# 下载: https://git-lfs.github.com/
# 或使用 Scoop: scoop install git-lfs

# 2. 初始化
git lfs install

# 3. 验证配置（.gitattributes 已配置规则）
git lfs track

# 从此新增的 mp4 文件自动使用 LFS
```

### 4. 配置 GitHub 分支保护（在 GitHub 网站上）

1. 进入仓库 Settings → Branches
2. 添加保护规则：
   - 分支名称：`main`
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Include administrators

---

## 提交信息规范

从现在开始，遵循 Conventional Commits 规范：

### 格式
```
<type>(<scope>): <subject>
```

### 常用类型
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构
- `perf`: 性能优化
- `docs`: 文档
- `test`: 测试
- `ci`: CI/CD
- `chore`: 其他

### 示例
```bash
git commit -m "feat(v16): add motor dynamics simulation"
git commit -m "fix(fsm): correct heel-strike state transition"
git commit -m "docs(readme): update quickstart guide"
git commit -m "perf(v13): optimize jacobian computation"
```

---

## 工作流速查

### 日常开发

```bash
# 1. 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/v17-state-estimation

# 2. 开发和提交
git add <files>
git commit -m "feat(v17): implement kalman filter"

# 3. 定期同步
git fetch origin
git rebase origin/develop

# 4. 推送并创建 PR
git push -u origin feature/v17-state-estimation
gh pr create --base develop --title "feat(v17): Add state estimation"
```

### 代码质量检查

```powershell
# 格式化
black .
ruff check --fix .

# 类型检查
mypy common/

# 运行测试
pytest tests/unit -v
pytest tests/regression -v -m "not slow"

# Pre-commit 检查
pre-commit run --all-files
```

---

## 关键文件说明

### `.gitignore`
排除不应提交的文件：
- 虚拟环境（.venv-mujoco, .venv-codex）
- 编译产物（__pycache__, *.pyc）
- ABAQUS 输出（*.odb, *.env）
- IDE 配置（.idea, .vscode）
- 临时文件（*.tmp, *.log）

### `.gitattributes`
规范文件处理：
- 行尾符：Python/配置文件用 LF，Windows 脚本用 CRLF
- Git LFS：mp4, h5, odb 等大文件
- 语言统计：排除 node_modules、虚拟环境
- 导出归档：排除测试和 CI 文件

### `GIT_WORKFLOW.md`
详细的工作流文档，包括：
- 分支策略和命名规范
- 提交信息规范（Conventional Commits）
- Pull Request 流程
- 代码审查要求
- 版本发布流程
- Git LFS 使用指南
- 常见问题排查

### `GIT_OPTIMIZATION_REPORT.md`
完整的优化报告，包括：
- 现状分析
- 问题识别
- 解决方案
- 实施计划
- 风险评估

---

## 已识别的问题

### 🔴 高优先级（必须处理）
- [x] ABAQUS .env 文件包含 API 密钥 → 已添加到 .gitignore，需移除跟踪

### 🟡 中优先级（建议处理）
- [ ] 27 个 mp4 文件已被 Git 跟踪（共 15-20 MB）→ 可选择 LFS 迁移
- [ ] ABAQUS 输出文件（.odb, .prt）已被跟踪 → 建议移除

### 🟢 低优先级（可选）
- [ ] 未配置分支保护规则
- [ ] 未启用提交信息自动检查

---

## 常见问题

### Q: 为什么要移除 ABAQUS .env 文件？
A: 该文件包含 `ANTHROPIC_AUTH_TOKEN` 等敏感信息，不应提交到 Git。

### Q: mp4 文件是否需要 Git LFS？
A: 当前 mp4 文件较小（0.1-2 MB），影响有限。建议渐进式迁移：现有文件保留，新文件自动使用 LFS。

### Q: 如何撤销错误的提交？
A: 使用 `git revert <commit>` 创建反向提交，或 `git reset --soft HEAD^` 撤销最后一次提交（保留更改）。

### Q: Pre-commit hooks 检查失败怎么办？
A: 运行 `black .` 和 `ruff check --fix .` 自动修复，然后重新提交。

---

## 参考资源

- **详细文档**: `GIT_WORKFLOW.md`
- **优化报告**: `GIT_OPTIMIZATION_REPORT.md`
- **项目文档**: `README.md`, `QUICKSTART.md`
- **在线资源**:
  - [Conventional Commits](https://www.conventionalcommits.org/)
  - [Git LFS](https://git-lfs.github.com/)
  - [Pre-commit](https://pre-commit.com/)

---

## 检查清单

优化完成后，确认以下项目：

- [ ] 已执行 `git_optimization_cleanup.ps1` 或手动清理
- [ ] 已提交所有配置文件更新
- [ ] 已移除敏感的 .env 文件
- [ ] 已安装 pre-commit hooks
- [ ] 已阅读 `GIT_WORKFLOW.md`
- [ ] 团队成员了解新的工作流规范
- [ ] （可选）已初始化 Git LFS
- [ ] （可选）已配置分支保护规则

---

**文档版本**: 1.0.0  
**创建日期**: 2026-06-05  
**适用项目**: hw-1 步态训练辅助设备仿真研究

---

## 下一步

1. 执行清理脚本: `.\git_optimization_cleanup.ps1`
2. 审查更改: `git status` 和 `git diff --cached`
3. 提交更改
4. 安装 pre-commit hooks
5. 与团队分享 `GIT_WORKFLOW.md`

# Git 工作流文档 - hw-1 项目

## 目录

1. [分支策略](#分支策略)
2. [提交信息规范](#提交信息规范)
3. [Pull Request 流程](#pull-request-流程)
4. [代码审查要求](#代码审查要求)
5. [版本发布流程](#版本发布流程)
6. [常用命令速查](#常用命令速查)
7. [Git LFS 使用指南](#git-lfs-使用指南)

---

## 分支策略

### 主分支

**main** (主分支)
- 始终保持稳定可发布状态
- 所有代码必须经过 PR 审查和 CI 通过才能合并
- 受保护分支，不允许直接推送
- 对应已验证的版本里程碑（如 V13.7, V14c, V15 等）

**develop** (开发分支)
- 日常开发的集成分支
- 包含最新的已完成但未发布的功能
- 定期合并到 main 进行发布

### 功能分支命名规范

```
feature/<版本号>-<简短描述>     # 新功能开发
bugfix/<问题描述>               # Bug 修复
refactor/<模块名>               # 代码重构
docs/<文档主题>                 # 文档更新
experiment/<实验名称>           # 实验性探索
```

**示例：**
```bash
feature/v16-motor-dynamics
bugfix/fsm-state-transition
refactor/common-library
docs/quickstart-guide
experiment/3d-stability-test
```

### 分支生命周期

```
1. 从 develop 创建功能分支
   git checkout develop
   git pull origin develop
   git checkout -b feature/v16-motor-dynamics

2. 定期同步 develop 分支
   git fetch origin
   git rebase origin/develop

3. 完成后创建 PR 合并回 develop
   git push -u origin feature/v16-motor-dynamics

4. 合并后删除远程分支
   git push origin --delete feature/v16-motor-dynamics
```

---

## 提交信息规范

采用 **Conventional Commits** 规范，便于自动生成变更日志和语义化版本。

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(v16): add motor dynamics simulation` |
| `fix` | Bug 修复 | `fix(fsm): correct state transition logic` |
| `refactor` | 代码重构 | `refactor(common): extract gait analysis utils` |
| `perf` | 性能优化 | `perf(v13): optimize jacobian computation` |
| `docs` | 文档更新 | `docs(readme): update quickstart guide` |
| `style` | 代码格式 | `style: apply black formatting` |
| `test` | 测试相关 | `test(common): add unit tests for controllers` |
| `build` | 构建系统 | `build: update dependencies` |
| `ci` | CI/CD 配置 | `ci: add benchmark workflow` |
| `chore` | 其他杂项 | `chore: clean up old experiment files` |

### Scope 范围

建议使用版本号或模块名：
- `v13`, `v14`, `v15`, `v16` 等版本号
- `common`, `fsm`, `controller`, `analysis` 等模块名
- `ci`, `docs`, `tests` 等基础设施

### Subject 主题

- 使用命令式语气（如 "add" 而非 "added"）
- 不要大写首字母
- 不要以句号结尾
- 限制在 50 字符以内

### Body 正文（可选）

- 详细说明修改的原因和实现细节
- 与上一行空一行
- 每行不超过 72 字符

### Footer 页脚（可选）

- 引用相关 Issue：`Closes #123`
- Breaking changes：`BREAKING CHANGE: change controller API`

### 提交示例

```bash
# 简单提交
git commit -m "feat(v16): add MX-64AR motor model"

# 详细提交
git commit -m "feat(v16): add realistic motor dynamics simulation

- Implement motor inertia and friction models
- Add Dynamixel MX-64AR parameters
- Support torque saturation and velocity limits

Closes #45"

# Breaking change
git commit -m "refactor(common)!: change controller interface

BREAKING CHANGE: Controller.step() now requires dt parameter.
Update all controllers to pass time step explicitly."
```

---

## Pull Request 流程

### 1. PR 前检查清单

在创建 PR 之前，确保：

```powershell
# 1. 代码格式化
black .
ruff check --fix .

# 2. 类型检查
mypy common/

# 3. 运行测试
pytest tests/unit -v
pytest tests/regression -v -m "not slow"

# 4. 确保没有未提交的更改
git status

# 5. 同步最新的 develop 分支
git fetch origin
git rebase origin/develop
```

### 2. 创建 PR

```bash
# 推送分支
git push -u origin feature/v16-motor-dynamics

# 使用 GitHub CLI 创建 PR（推荐）
gh pr create --base develop --title "feat(v16): Add motor dynamics simulation" --body "
## 变更说明
- 实现电机动力学模型（惯性、摩擦、饱和）
- 添加 Dynamixel MX-64AR 参数
- 支持扭矩和速度限制

## 测试情况
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 手动验证 V16 仿真正常运行

## 相关 Issue
Closes #45
"
```

### 3. PR 标题规范

标题遵循提交信息规范：
```
feat(v16): Add motor dynamics simulation
fix(fsm): Correct heel-strike state transition
docs: Update Git workflow documentation
```

### 4. PR 描述模板

```markdown
## 变更说明
简要描述此 PR 的主要变更内容。

## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 性能优化 (perf)
- [ ] 测试 (test)

## 测试情况
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动验证通过
- [ ] 添加了新测试

## 检查清单
- [ ] 代码符合项目风格规范（black + ruff）
- [ ] 添加/更新了必要的文档
- [ ] 没有引入新的警告或错误
- [ ] 所有 CI 检查通过

## 相关 Issue
Closes #<issue-number>

## 截图/演示（如适用）
[添加仿真结果、图表等]
```

### 5. CI 自动检查

PR 创建后，GitHub Actions 会自动运行：
- ✅ 代码格式检查（Black, Ruff）
- ✅ 类型检查（Mypy）
- ✅ 单元测试（Pytest）
- ✅ 集成测试
- ✅ 代码覆盖率报告

所有检查必须通过才能合并。

---

## 代码审查要求

### 审查者职责

1. **功能正确性**
   - 代码逻辑是否正确
   - 是否满足需求
   - 边界情况是否处理

2. **代码质量**
   - 是否符合项目代码风格
   - 命名是否清晰
   - 是否有重复代码
   - 注释是否充分

3. **测试覆盖**
   - 是否有足够的测试
   - 测试是否覆盖关键路径
   - 是否有回归测试

4. **文档完整性**
   - README 是否更新
   - 代码注释是否清晰
   - 是否需要更新教程

5. **性能和安全**
   - 是否有性能问题
   - 是否引入安全风险
   - 资源使用是否合理

### 审查流程

```bash
# 1. 拉取 PR 分支到本地
gh pr checkout <PR-number>

# 2. 运行代码和测试
.\.venv-mujoco\Scripts\activate
python <新增脚本>.py

# 3. 检查代码质量
black --check .
ruff check .
mypy common/

# 4. 在 GitHub 上提交审查意见
# - 使用 "Comment" 提出问题
# - 使用 "Request changes" 要求修改
# - 使用 "Approve" 批准合并
```

### 审查标准

**必须修复（Blocking）：**
- 功能性 bug
- 测试失败
- 安全漏洞
- 违反项目规范

**建议改进（Non-blocking）：**
- 代码优化建议
- 命名改进
- 注释补充
- 文档完善

---

## 版本发布流程

### 版本号规范

采用语义化版本：`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的重大变更（如 V13 → V14）
- **MINOR**: 向后兼容的功能增加（如 V13.6 → V13.7）
- **PATCH**: 向后兼容的 Bug 修复（如 V13.7.0 → V13.7.1）

### 发布步骤

#### 1. 准备发布

```bash
# 1. 确保 develop 分支最新
git checkout develop
git pull origin develop

# 2. 创建发布分支
git checkout -b release/v1.2.0

# 3. 更新版本号
# 编辑 pyproject.toml 中的 version
# 编辑 PROJECT_PROGRESS.md 标记完成状态

# 4. 生成变更日志
git log v1.1.0..HEAD --pretty=format:"- %s" >> CHANGELOG.md

# 5. 提交版本更新
git add .
git commit -m "chore: prepare release v1.2.0"
```

#### 2. 测试和验证

```powershell
# 运行完整测试套件
pytest tests/ -v

# 运行性能基准测试
python benchmarks/benchmark_runner.py

# 手动验证关键版本
python v13_7_friction_compensation\simulate_v13_7.py
python v16_motor_dynamics\simulate_v16.py
```

#### 3. 合并到 main

```bash
# 1. 合并到 main
git checkout main
git merge --no-ff release/v1.2.0 -m "Release v1.2.0"

# 2. 创建标签
git tag -a v1.2.0 -m "Release v1.2.0

Major changes:
- feat(v16): Add motor dynamics simulation
- fix(fsm): Improve state transition robustness
- perf(v13): Optimize Jacobian computation
"

# 3. 推送到远程
git push origin main
git push origin v1.2.0

# 4. 合并回 develop
git checkout develop
git merge main
git push origin develop

# 5. 删除发布分支
git branch -d release/v1.2.0
```

#### 4. GitHub Release

```bash
# 使用 GitHub CLI 创建 Release
gh release create v1.2.0 \
  --title "Release v1.2.0 - Motor Dynamics Integration" \
  --notes "$(cat RELEASE_NOTES.md)" \
  --target main
```

---

## 常用命令速查

### 日常开发

```bash
# 查看状态
git status
git log --oneline --graph --all -10

# 创建分支
git checkout -b feature/new-feature

# 暂存和提交
git add <files>
git commit -m "feat(scope): description"

# 同步远程
git fetch origin
git rebase origin/develop

# 推送分支
git push -u origin feature/new-feature
```

### 分支管理

```bash
# 查看所有分支
git branch -a

# 删除本地分支
git branch -d feature/old-feature

# 删除远程分支
git push origin --delete feature/old-feature

# 清理已合并分支
git branch --merged | grep -v "\*\|main\|develop" | xargs -n 1 git branch -d
```

### 撤销操作

```bash
# 撤销未暂存的修改
git checkout -- <file>

# 撤销暂存
git reset HEAD <file>

# 修改最后一次提交
git commit --amend

# 撤销最后一次提交（保留修改）
git reset --soft HEAD^

# 撤销最后一次提交（丢弃修改，慎用！）
git reset --hard HEAD^
```

### 查看历史

```bash
# 查看提交历史
git log --oneline --graph --all

# 查看某个文件的历史
git log --follow <file>

# 查看某次提交的详情
git show <commit-hash>

# 查看谁修改了某行代码
git blame <file>
```

### 解决冲突

```bash
# 1. 拉取最新代码时冲突
git fetch origin
git rebase origin/develop
# 解决冲突后
git add <resolved-files>
git rebase --continue

# 2. 放弃 rebase
git rebase --abort

# 3. 使用合并而非 rebase
git merge origin/develop
# 解决冲突后
git add <resolved-files>
git commit
```

---

## Git LFS 使用指南

### 安装和初始化

```powershell
# 1. 安装 Git LFS（Windows）
# 下载：https://git-lfs.github.com/
# 或使用 Scoop: scoop install git-lfs

# 2. 初始化 Git LFS
git lfs install

# 3. 验证 LFS 配置
git lfs version
```

### 迁移现有 mp4 文件到 LFS

```powershell
# ⚠️ 警告：此操作会重写 Git 历史，需要团队协调

# 1. 备份仓库
cd D:\Dunna\Documents\
cp -r hw-1 hw-1-backup

# 2. 迁移 mp4 文件到 LFS
cd hw-1
git lfs migrate import --include="*.mp4" --everything

# 3. 强制推送（需要团队同意）
git push --force --all origin
git push --force --tags origin

# 4. 团队成员重新克隆仓库
# git clone <repository-url>
```

### 日常使用

```bash
# 跟踪新的 mp4 文件（已在 .gitattributes 配置，自动生效）
git add v17_new_version/out/simulation.mp4
git commit -m "feat(v17): add simulation results"

# 查看 LFS 文件
git lfs ls-files

# 拉取 LFS 文件
git lfs pull

# 查看 LFS 存储使用
git lfs ls-files --size
```

### LFS 最佳实践

1. **限制文件大小**：单个文件不超过 100MB（GitHub 限制）
2. **清理旧版本**：定期清理不需要的 LFS 文件
3. **CI/CD 配置**：确保 CI 环境安装了 Git LFS

```yaml
# GitHub Actions 中启用 LFS
- uses: actions/checkout@v4
  with:
    lfs: true
```

---

## 最佳实践总结

### Do's ✅

- ✅ 经常提交，保持提交粒度小而专注
- ✅ 提交前运行测试和代码检查
- ✅ 编写清晰的提交信息
- ✅ 定期同步 develop 分支
- ✅ 使用功能分支开发
- ✅ 通过 PR 合并代码
- ✅ 认真进行代码审查

### Don'ts ❌

- ❌ 不要直接推送到 main
- ❌ 不要提交大文件（使用 Git LFS）
- ❌ 不要提交敏感信息（密码、密钥）
- ❌ 不要提交虚拟环境（.venv-mujoco）
- ❌ 不要使用 `git push --force`（除非团队同意）
- ❌ 不要在 PR 中混合无关的修改
- ❌ 不要忽略 CI 失败

---

## 问题排查

### 常见问题

**Q: 如何撤销已推送的错误提交？**
```bash
# 1. 在本地撤销提交
git revert <commit-hash>
git push origin <branch>

# 2. 如果是私有分支且无人使用，可以强制推送
git reset --hard <commit-hash>
git push --force origin <branch>
```

**Q: 如何处理 "detached HEAD" 状态？**
```bash
# 如果想保留当前修改
git checkout -b temp-branch
git checkout develop
git merge temp-branch

# 如果不需要当前修改
git checkout develop
```

**Q: 如何清理 .gitignore 后仍被跟踪的文件？**
```bash
# 从 Git 中移除但保留本地文件
git rm --cached <file>
git commit -m "chore: remove tracked file from git"

# 批量清理
git rm -r --cached .
git add .
git commit -m "chore: apply updated .gitignore"
```

---

## 参考资源

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git LFS Documentation](https://git-lfs.github.com/)
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Semantic Versioning](https://semver.org/)

---

**文档版本**: 1.0.0  
**最后更新**: 2026-06-05  
**维护者**: hw-1 项目团队

# HW-1 项目 CI/CD 完整指南

本文档详细介绍 hw-1 项目的持续集成与持续交付（CI/CD）自动化流程。

---

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [本地 CI/CD](#本地-cicd)
- [GitHub Actions](#github-actions)
- [自动化脚本](#自动化脚本)
- [Git Hooks](#git-hooks)
- [配置文件](#配置文件)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 概述

### CI/CD 架构

hw-1 项目提供**双轨 CI/CD 方案**：

1. **本地 CI 脚本**：适合日常开发，无需远程仓库，即时反馈
2. **GitHub Actions**：适合团队协作，自动化测试、部署和监控

### CI/CD 流程图

```
┌─────────────────┐
│   代码修改      │
└────────┬────────┘
         │
         ├──► pre-commit hook ──► 格式化、linting
         │
         ├──► 本地测试 (.\ci\run_tests.ps1)
         │
         ├──► pre-push hook ──► 单元测试
         │
         ▼
┌─────────────────┐
│   Push 到远程   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         GitHub Actions 工作流            │
├─────────────────────────────────────────┤
│ 1. 测试套件 (多 Python 版本)            │
│ 2. 代码质量检查 (black, ruff, mypy)     │
│ 3. 安全扫描 (bandit, safety, pip-audit) │
│ 4. 性能基准测试                          │
│ 5. 文档生成                              │
└────────┬────────────────────────────────┘
         │
         ├──► 成功 ──► 合并到主分支
         │
         └──► 失败 ──► 通知开发者修复
```

---

## 快速开始

### 1. 安装开发依赖

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. 安装 Git Hooks

```powershell
.\ci\install_hooks.ps1
```

### 3. 运行完整 CI 流程

```powershell
# 快速模式（跳过慢速测试和完整基准）
.\ci\run_all_ci.ps1 -Quick

# 完整模式（包含所有检查）
.\ci\run_all_ci.ps1

# 完整模式 + 文档生成
.\ci\run_all_ci.ps1 -GenerateDocs
```

### 4. 验证安装

```powershell
# 检查工具是否安装成功
python -m pytest --version
python -m black --version
python -m ruff --version
python -m mypy --version
```

---

## 本地 CI/CD

### CI 脚本总览

| 脚本 | 功能 | 用途 |
|------|------|------|
| `run_tests.ps1` | 运行测试套件 | 单元测试、集成测试、覆盖率 |
| `run_quality.ps1` | 代码质量检查 | 格式化、linting、类型检查 |
| `run_benchmarks.ps1` | 性能基准测试 | 跨版本性能对比 |
| `generate_docs.ps1` | 生成文档 | 覆盖率报告、API 文档 |
| `run_all_ci.ps1` | 完整 CI 流程 | 一键运行所有检查 |
| `install_hooks.ps1` | 安装 Git hooks | 自动化 pre-commit/pre-push |
| `check_health.ps1` | 项目健康检查 | 覆盖率、复杂度、技术债务 |
| `update_dashboard.ps1` | 更新 dashboard | 自动更新数据可视化 |
| `generate_weekly_report.ps1` | 生成周报 | 项目进度总结 |

### 详细使用说明

#### 1. 测试套件 (`run_tests.ps1`)

```powershell
# 运行所有测试 + 覆盖率
.\ci\run_tests.ps1 -Coverage

# 并行运行测试（加速）
.\ci\run_tests.ps1 -Parallel -Coverage

# 只运行单元测试
.\ci\run_tests.ps1 -Markers "unit"

# 只运行回归测试
.\ci\run_tests.ps1 -Markers "regression"

# 详细输出（调试用）
.\ci\run_tests.ps1 -Verbose
```

**输出**：
- 终端测试结果
- `htmlcov/index.html` - 覆盖率 HTML 报告
- `coverage.json` - 覆盖率 JSON 数据

#### 2. 代码质量检查 (`run_quality.ps1`)

```powershell
# 运行所有质量检查
.\ci\run_quality.ps1

# 自动修复格式问题
.\ci\run_quality.ps1 -Fix

# 只运行特定工具
.\ci\run_quality.ps1 -Tool "black"
.\ci\run_quality.ps1 -Tool "ruff"
.\ci\run_quality.ps1 -Tool "mypy"

# 严格模式（任何警告都报错）
.\ci\run_quality.ps1 -Strict
```

**质量工具说明**：

| 工具 | 功能 | 自动修复 |
|------|------|---------|
| **Black** | 代码格式化（PEP8 风格） | ✓ |
| **Ruff** | 快速 linting（替代 flake8/pylint） | ✓ (部分) |
| **Mypy** | 静态类型检查 | ✗ |
| **Radon** | 圈复杂度分析 | ✗ |

#### 3. 性能基准测试 (`run_benchmarks.ps1`)

```powershell
# 运行所有版本基准测试
.\ci\run_benchmarks.ps1

# 与上次结果对比（检测回归）
.\ci\run_benchmarks.ps1 -Compare

# 只测试特定版本
.\ci\run_benchmarks.ps1 -Versions "v10,v13_7_refactored,v17"

# 生成可视化报告
.\ci\run_benchmarks.ps1 -Compare -GenerateReport

# 自定义回归阈值（默认 10%）
.\ci\run_benchmarks.ps1 -Compare -Threshold 15
```

**输出**：
- `benchmarks/results/benchmark_YYYYMMDD_HHMMSS.json` - 原始数据
- `benchmarks/results/performance_evolution.png` - 性能演化图
- `benchmarks/results/radar_comparison.png` - 雷达对比图
- `benchmarks/results/benchmark_report.txt` - 文本报告

#### 4. 文档生成 (`generate_docs.ps1`)

```powershell
# 生成覆盖率报告
.\ci\generate_docs.ps1

# 生成 API 文档（需要 pdoc）
.\ci\generate_docs.ps1 -ApiDocs

# 更新 README 徽章
.\ci\generate_docs.ps1 -UpdateBadges
```

#### 5. 项目健康检查 (`check_health.ps1`)

```powershell
# 运行健康检查
.\ci\check_health.ps1

# 详细输出
.\ci\check_health.ps1 -Detailed

# JSON 格式输出（用于自动化）
.\ci\check_health.ps1 -Json
```

**检查项目**：
- 测试覆盖率（目标 ≥80%）
- 代码复杂度（高复杂度函数数量）
- 技术债务（TODO/FIXME/HACK 计数）
- 文档新鲜度（README 更新时间）
- Git 活动（近 7 天提交数）
- 依赖安全（提示运行完整扫描）
- 基准测试新鲜度（最后运行时间）

#### 6. 更新 Dashboard (`update_dashboard.ps1`)

```powershell
# 更新 dashboard 数据
.\ci\update_dashboard.ps1

# 强制更新（即使数据未变化）
.\ci\update_dashboard.ps1 -Force
```

**更新内容**：
- `dashboard/data/coverage_history.json` - 覆盖率历史
- `dashboard/data/latest_benchmark.json` - 最新基准结果
- `dashboard/data/project_stats.json` - 项目统计

#### 7. 生成周报 (`generate_weekly_report.ps1`)

```powershell
# 生成本周报告
.\ci\generate_weekly_report.ps1

# 指定输出目录
.\ci\generate_weekly_report.ps1 -OutputPath "reports"
```

**报告内容**：
- Git 统计（提交数、贡献者）
- 代码变更统计
- 质量指标（覆盖率、待办事项）
- 性能基准结果
- 本周亮点（手动填写）
- 下周计划（手动填写）

---

## GitHub Actions

### 工作流总览

| 工作流 | 触发条件 | 功能 |
|--------|---------|------|
| `tests.yml` | Push/PR | 多版本 Python 测试 (3.9/3.10/3.11) |
| `code_quality.yml` | Push/PR | 代码质量检查 |
| `security.yml` | Push/PR/周一 | 依赖安全扫描 |
| `benchmarks.yml` | Push/PR/周日 | 性能基准测试 |
| `docs.yml` | Push to main | 文档生成 + GitHub Pages |
| `weekly-benchmark.yml` | 周日 02:00 | 完整基准测试 + 回归检测 |
| `health-check.yml` | 周一/三/五 | 项目健康检查 |
| `release.yml` | Tag push | 自动发布流程 |

### 工作流详解

#### 1. 测试套件 (`tests.yml`)

**触发条件**：
- Push 到 `main` 或 `develop` 分支
- Pull Request 到 `main` 或 `develop`
- 手动触发

**测试矩阵**：
```yaml
python-version: ["3.9", "3.10", "3.11"]
```

**步骤**：
1. 安装 Python + 依赖
2. 运行单元测试
3. 运行集成测试（跳过 slow 标记）
4. 生成覆盖率报告
5. 上传到 Codecov
6. 归档测试结果

#### 2. 代码质量 (`code_quality.yml`)

**检查项目**：
- Black 格式检查
- Ruff linting
- Mypy 类型检查（允许失败）
- Radon 复杂度分析
- Bandit 安全检查（允许失败）

#### 3. 安全扫描 (`security.yml`)

**扫描工具**：
- **Safety**: 检查已知的依赖漏洞（CVE 数据库）
- **Bandit**: 代码安全问题检测（硬编码密码、SQL 注入等）
- **pip-audit**: PyPI 依赖审计

**输出**：
- `safety-report.json`
- `bandit-report.json`
- `pip-audit-report.json`
- `security-summary.md`

#### 4. 性能基准 (`benchmarks.yml`)

**运行模式**：
- Push/PR: 运行关键版本快速测试
- 周日定时: 运行完整版本测试
- 手动触发: 可选测试范围

**对比分析**：
- 与上次结果对比
- 检测性能回归（CoT、仿真时间）
- 生成对比报告
- PR 评论中显示结果

#### 5. 每周基准 (`weekly-benchmark.yml`)

**功能**：
- 每周日 02:00 UTC 自动运行
- 完整版本基准测试
- 与历史结果对比
- 检测到回归自动创建 Issue

#### 6. 健康检查 (`health-check.yml`)

**检查频率**：每周一、三、五

**检查项目**：
- 测试覆盖率（阈值 70%）
- 代码复杂度
- 技术债务计数
- 文档新鲜度

**告警机制**：
- 覆盖率 < 70%：自动创建 Issue
- 生成健康报告 artifact

#### 7. 自动发布 (`release.yml`)

**触发条件**：
- Tag push (`v*.*.*`)
- 手动触发（指定版本号）

**发布流程**：
1. 运行完整 CI 流程
2. 运行完整基准测试
3. 生成发布说明（changelog）
4. 创建 GitHub Release
5. 上传构建产物（benchmark 结果、文档、覆盖率报告）

---

## 自动化脚本

### 定时任务配置

使用 Windows 任务计划程序或 cron（WSL）定期运行自动化脚本。

#### 示例：每周日运行基准测试

**PowerShell 脚本** (`scheduled_benchmark.ps1`):

```powershell
$ErrorActionPreference = "Stop"
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe benchmarks/benchmark_runner.py --output weekly_benchmark.json
.\ci\update_dashboard.ps1
```

**Windows 任务计划程序**：
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每周日 02:00
4. 操作：启动程序
   - 程序：`powershell.exe`
   - 参数：`-ExecutionPolicy Bypass -File "D:\Dunna\Documents\hw-1\scheduled_benchmark.ps1"`

---

## Git Hooks

### 安装 Git Hooks

```powershell
.\ci\install_hooks.ps1
```

### Hooks 说明

#### 1. Pre-commit Hook

**触发时机**：`git commit` 之前

**执行操作**：
- 运行 Black 格式化（自动修复）
- 运行 Ruff linting（自动修复）
- 失败则阻止提交

**跳过方式**（不推荐）：
```bash
git commit --no-verify
```

#### 2. Pre-push Hook

**触发时机**：`git push` 之前

**执行操作**：
- 运行单元测试（`-m unit`）
- 失败则阻止推送

**跳过方式**（不推荐）：
```bash
git push --no-verify
```

#### 3. Commit-msg Hook

**触发时机**：`git commit` 之前（消息验证）

**验证规则**：
- Commit message 至少 10 个字符
- 可选：检查是否引用 Issue 编号

### 使用 pre-commit 框架（推荐）

```powershell
# 安装 pre-commit
pip install pre-commit

# 安装 hooks 到 .git/hooks
pre-commit install

# 手动运行所有 hooks
pre-commit run --all-files

# 更新 hooks 版本
pre-commit autoupdate
```

`.pre-commit-config.yaml` 已配置好以下 hooks：
- black（格式化）
- ruff（linting）
- trailing-whitespace（去除行尾空格）
- end-of-file-fixer（文件末尾换行）
- check-yaml/json/toml（配置文件检查）
- mypy（类型检查）

---

## 配置文件

### 核心配置文件

#### 1. `ci/ci_config.yaml`

CI/CD 流程的中心配置文件。

**关键配置项**：

```yaml
testing:
  coverage:
    minimum: 80  # 最低覆盖率
  timeout:
    unit: 10
    integration: 30
    slow: 300

quality:
  tools:
    black: true
    ruff: true
    mypy: true
    radon: true
  strict:
    black: true
    ruff: true
    mypy: false  # 允许 mypy 警告

benchmarks:
  regression_threshold:
    cot: 10  # CoT 增加 >10% 报警
    simulation_time: 15
    memory: 20

github_actions:
  triggers:
    push_branches: ["main", "develop"]
    schedule: "0 0 * * 0"  # 每周日
```

#### 2. `pyproject.toml`

工具配置（Black、Ruff、Mypy）。

```toml
[tool.black]
line-length = 88
target-version = ["py39", "py310", "py311"]

[tool.ruff]
line-length = 88
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.10"
disallow_untyped_defs = false
check_untyped_defs = true
```

#### 3. `pytest.ini`

测试框架配置。

```ini
[pytest]
testpaths = tests
markers =
    unit: 单元测试
    regression: 回归测试
    integration: 集成测试
    slow: 慢速测试
```

#### 4. `.pre-commit-config.yaml`

Pre-commit hooks 配置。

---

## 最佳实践

### 日常开发流程

```powershell
# 1. 开始开发前：拉取最新代码
git pull

# 2. 创建功能分支
git checkout -b feature/my-feature

# 3. 开发过程中：快速验证
.\ci\run_quality.ps1 -Fix
.\ci\run_tests.ps1 -Markers "unit"

# 4. 提交前：完整检查
.\ci\run_all_ci.ps1 -Quick

# 5. 提交代码（会自动触发 pre-commit hooks）
git add .
git commit -m "feat: add new feature"

# 6. 推送代码（会自动触发 pre-push hooks）
git push origin feature/my-feature

# 7. 创建 Pull Request
# GitHub Actions 会自动运行所有检查
```

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**：
```
feat(v17): add Kalman filter state estimator

- Implement sensor noise simulation
- Add position and velocity estimation
- Update benchmark configs for V17

Closes #123
```

### 分支管理策略

```
main
  ├── develop
  │   ├── feature/new-feature
  │   ├── feature/another-feature
  │   └── fix/bug-fix
  └── release/v1.2.0
```

- **main**: 稳定版本，只接受 PR
- **develop**: 开发主分支
- **feature/**: 功能开发分支
- **fix/**: Bug 修复分支
- **release/**: 发布准备分支

### 代码审查清单

在 PR 审查时检查：

- [ ] 所有 CI 检查通过
- [ ] 测试覆盖率 ≥ 80%
- [ ] 代码格式符合规范（Black + Ruff）
- [ ] 类型注解完整（Mypy 无错误）
- [ ] 性能无回归（基准测试通过）
- [ ] 文档已更新
- [ ] Commit 信息规范
- [ ] 无安全漏洞（Bandit + Safety）

### 性能优化技巧

1. **并行测试**：使用 `-Parallel` 标志利用多核 CPU
   ```powershell
   .\ci\run_tests.ps1 -Parallel -Coverage
   ```

2. **增量测试**：只运行失败的测试
   ```bash
   pytest --lf  # last failed
   pytest --ff  # failed first
   ```

3. **跳过慢速测试**：开发时跳过标记为 `slow` 的测试
   ```powershell
   .\ci\run_tests.ps1 -Markers "not slow"
   ```

4. **缓存依赖**：GitHub Actions 已配置 pip cache

---

## 故障排除

### 常见问题

#### 1. 虚拟环境找不到

**错误**：
```
Virtual environment not found: .venv-mujoco\Scripts\python.exe
```

**解决**：
```powershell
# 检查虚拟环境
Test-Path ".venv-mujoco\Scripts\python.exe"

# 重新创建虚拟环境
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\pip.exe install -r requirements-dev.txt
```

#### 2. PowerShell 执行策略错误

**错误**：
```
cannot be loaded because running scripts is disabled
```

**解决**：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3. 测试超时

**解决**：
```powershell
# 跳过慢速测试
.\ci\run_tests.ps1 -Markers "not slow"

# 或修改 pytest.ini 增加超时
[pytest]
timeout = 300
```

#### 4. Git Hooks 不生效

**原因**：Hooks 文件无执行权限或格式错误

**解决**：
```powershell
# 重新安装 hooks
.\ci\install_hooks.ps1 -Force

# 或使用 pre-commit 框架
pre-commit install --overwrite
```

#### 5. 基准测试回归误报

**原因**：环境波动导致性能噪声

**解决**：
```powershell
# 调整回归阈值
.\ci\run_benchmarks.ps1 -Compare -Threshold 15

# 或在 ci_config.yaml 中修改默认阈值
```

#### 6. GitHub Actions 失败

**调试步骤**：
1. 查看失败步骤的日志
2. 在本地复现问题：
   ```powershell
   .\ci\run_all_ci.ps1
   ```
3. 修复后推送新提交
4. GitHub Actions 自动重新运行

#### 7. 依赖冲突

**解决**：
```powershell
# 重新安装依赖
pip install --upgrade -r requirements-dev.txt

# 或清理缓存重装
pip cache purge
pip install -r requirements-dev.txt
```

### 调试技巧

#### 1. 详细输出模式

```powershell
# 测试详细输出
.\ci\run_tests.ps1 -Verbose

# pytest 详细模式
pytest -vv --tb=long
```

#### 2. 只运行特定测试

```powershell
# 运行单个测试文件
pytest tests/unit/test_specific.py

# 运行单个测试函数
pytest tests/unit/test_specific.py::test_function_name

# 使用关键字过滤
pytest -k "test_gait"
```

#### 3. 进入调试器

```powershell
# 失败时自动进入 pdb
pytest --pdb

# 在特定位置设置断点
# 在代码中添加：
import pdb; pdb.set_trace()
```

#### 4. 查看覆盖率详情

```powershell
# 生成覆盖率报告
pytest --cov=common --cov-report=html

# 在浏览器中打开
Start-Process htmlcov\index.html
```

---

## 附录

### A. CI/CD 工具对比

| 工具 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| **GitHub Actions** | 与 GitHub 深度集成，免费额度大 | 仅限 GitHub 仓库 | 开源项目、团队协作 |
| **本地 CI 脚本** | 即时反馈，无需网络，隐私保护 | 无自动化触发，依赖本地环境 | 研究项目、离线开发 |
| **pre-commit** | 轻量级，本地运行快 | 功能有限 | 代码格式化、简单检查 |

### B. 性能基准历史数据

查看 `benchmarks/results/` 目录中的历史 JSON 文件，分析性能趋势。

### C. 覆盖率历史趋势

查看 `dashboard/data/coverage_history.json` 了解覆盖率演化。

### D. 相关资源

- [pytest 文档](https://docs.pytest.org/)
- [Black 文档](https://black.readthedocs.io/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [pre-commit 文档](https://pre-commit.com/)

---

**文档版本**: v1.0.0  
**创建日期**: 2026-06-05  
**最后更新**: 2026-06-05  
**维护者**: hw-1 项目组

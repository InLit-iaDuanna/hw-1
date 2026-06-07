# CI/CD 自动化流程

hw-1 项目的持续集成与持续交付自动化基础设施。

## 概述

本项目提供双轨 CI/CD 方案：
- **本地 CI 脚本**：适合研究项目日常开发，无需 Git 远程仓库
- **GitHub Actions**：适合协作开发和自动化发布

## 目录结构

```
ci/
├── run_tests.ps1          # 测试套件运行器
├── run_quality.ps1        # 代码质量检查
├── run_benchmarks.ps1     # 性能基准测试
├── generate_docs.ps1      # 文档生成器
└── run_all_ci.ps1         # 完整 CI 流程

.github/workflows/
├── tests.yml              # 测试工作流
├── code_quality.yml       # 质量检查工作流
├── benchmarks.yml         # 性能基准工作流
└── docs.yml               # 文档生成工作流
```

## 快速开始

### 本地 CI 使用

#### 1. 运行测试套件

```powershell
# 运行所有测试（带覆盖率）
.\ci\run_tests.ps1 -Coverage

# 并行运行测试（加速）
.\ci\run_tests.ps1 -Parallel -Coverage

# 只运行单元测试
.\ci\run_tests.ps1 -Markers "unit"

# 只运行回归测试
.\ci\run_tests.ps1 -Markers "regression"
```

#### 2. 代码质量检查

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

#### 3. 性能基准测试

```powershell
# 运行所有版本基准测试
.\ci\run_benchmarks.ps1

# 与上次结果对比（检测回归）
.\ci\run_benchmarks.ps1 -Compare

# 只测试特定版本
.\ci\run_benchmarks.ps1 -Versions "v10,v13_7,v17"

# 生成可视化报告
.\ci\run_benchmarks.ps1 -Compare -GenerateReport

# 自定义回归阈值（默认 10%）
.\ci\run_benchmarks.ps1 -Compare -Threshold 15
```

#### 4. 生成文档

```powershell
# 生成覆盖率报告
.\ci\generate_docs.ps1

# 生成 API 文档（需要 pdoc）
.\ci\generate_docs.ps1 -ApiDocs

# 更新 README 徽章
.\ci\generate_docs.ps1 -UpdateBadges
```

#### 5. 完整 CI 流程

```powershell
# 运行完整 CI 流程
.\ci\run_all_ci.ps1

# 快速模式（跳过慢速测试）
.\ci\run_all_ci.ps1 -Quick

# 自动修复代码问题
.\ci\run_all_ci.ps1 -Fix

# 跳过基准测试（加速）
.\ci\run_all_ci.ps1 -NoBenchmarks

# 生成文档
.\ci\run_all_ci.ps1 -GenerateDocs
```

### GitHub Actions 使用

#### 触发条件

- **tests.yml**: 推送到 main/develop 分支或 PR
- **code_quality.yml**: 推送到 main/develop 分支或 PR
- **benchmarks.yml**: 推送到 main 分支、PR 或每周日自动运行
- **docs.yml**: 推送到 main 分支

#### 手动触发

在 GitHub 仓库页面：
1. 点击 "Actions" 标签
2. 选择工作流
3. 点击 "Run workflow"

## CI 流程详解

### 1. 测试套件 (run_tests.ps1)

**功能：**
- 运行 pytest 测试套件
- 生成覆盖率报告（HTML + JSON）
- 支持并行测试（pytest-xdist）
- 支持标记过滤（unit, regression, integration, slow）

**退出码：**
- 0: 所有测试通过
- 非 0: 至少一个测试失败

**输出：**
- 终端测试结果
- `htmlcov/index.html` - 覆盖率 HTML 报告
- `coverage.json` - 覆盖率 JSON 数据

### 2. 代码质量检查 (run_quality.ps1)

**检查项目：**

| 工具 | 检查内容 | 自动修复 |
|------|---------|---------|
| Black | 代码格式化 | ✓ |
| Ruff | Linting（PEP8、bugbear 等） | ✓ (部分) |
| Mypy | 类型检查 | ✗ |
| Radon | 圈复杂度分析 | ✗ |

**退出码：**
- 0: 所有检查通过
- 非 0: 发现质量问题

### 3. 性能基准 (run_benchmarks.ps1)

**功能：**
- 运行跨版本性能基准测试
- 对比历史结果检测回归
- 生成可视化报告

**回归检测：**
- CoT 增加 > 阈值 → 报警
- 仿真时间增加 > 阈值 → 警告
- 成功变失败 → 报错

**输出：**
- `benchmarks/results/benchmark_YYYYMMDD_HHMMSS.json` - 原始数据
- `benchmarks/results/performance_evolution.png` - 性能演化图
- `benchmarks/results/radar_comparison.png` - 雷达对比图
- `benchmarks/results/benchmark_report.txt` - 文本报告

### 4. 文档生成 (generate_docs.ps1)

**生成内容：**
- 测试覆盖率报告（来自 coverage.py）
- API 文档（pdoc/sphinx）
- README 徽章更新
- 文档索引页

**README 徽章更新：**

在 README.md 中添加标记：
```markdown
<!-- BADGES:START -->
<!-- BADGES:END -->
```

运行 `.\ci\generate_docs.ps1 -UpdateBadges` 自动更新徽章。

## 配置文件

### pytest.ini

测试配置已在项目根目录定义：
- 测试发现规则
- 标记定义（unit, regression, integration, slow）
- 覆盖率设置

### pyproject.toml

质量工具配置：
- Black 格式化规则
- Ruff linting 规则
- Mypy 类型检查规则

### .pre-commit-config.yaml

Git pre-commit hooks（可选）：
```bash
pip install pre-commit
pre-commit install
```

每次 commit 前自动运行质量检查。

## 常见工作流

### 日常开发

```powershell
# 开发前：确保环境干净
.\ci\run_quality.ps1 -Fix
.\ci\run_tests.ps1 -Markers "unit"

# 开发中：快速验证
.\ci\run_tests.ps1 -Markers "unit" -Verbose

# 提交前：完整检查
.\ci\run_all_ci.ps1 -Quick
```

### 版本发布前

```powershell
# 完整 CI 流程 + 文档
.\ci\run_all_ci.ps1 -GenerateDocs

# 性能基准对比
.\ci\run_benchmarks.ps1 -Compare -GenerateReport
```

### 调试测试失败

```powershell
# 详细输出
.\ci\run_tests.ps1 -Verbose

# 只运行失败的测试
pytest --lf

# 进入调试器
pytest --pdb
```

### 性能回归调查

```powershell
# 生成完整报告
.\ci\run_benchmarks.ps1 -Compare -GenerateReport -Threshold 5

# 查看历史趋势
# 检查 benchmarks/results/ 中的历史 JSON 文件
```

## 依赖安装

CI 脚本使用的 Python 包：

```bash
# 测试框架（已在 requirements.txt）
pip install pytest pytest-cov pytest-xdist pytest-timeout

# 质量工具
pip install black ruff mypy radon

# 文档工具
pip install pdoc
# 或
pip install sphinx sphinx-rtd-theme

# 基准测试（已在 requirements.txt）
pip install pyyaml
```

## 故障排除

### 问题 1: 虚拟环境找不到

**错误：** `Virtual environment not found`

**解决：**
```powershell
# 确认 .venv-mujoco 存在
Test-Path "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe"

# 如果不存在，创建虚拟环境
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\pip.exe install -r requirements.txt
```

### 问题 2: PowerShell 执行策略

**错误：** `cannot be loaded because running scripts is disabled`

**解决：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题 3: 测试超时

**解决：**
```powershell
# 跳过慢速测试
.\ci\run_tests.ps1 -Markers "unit"

# 或增加超时（修改 pytest.ini）
[pytest]
timeout = 300
```

### 问题 4: 基准测试回归误报

如果基准测试结果存在噪声（环境因素），可调整阈值：

```powershell
# 放宽到 15%
.\ci\run_benchmarks.ps1 -Compare -Threshold 15
```

## 扩展与自定义

### 添加新测试标记

编辑 `pytest.ini`：
```ini
[pytest]
markers =
    unit: 单元测试
    regression: 回归测试
    integration: 集成测试
    slow: 慢速测试
    your_marker: 你的描述
```

### 添加自定义 CI 步骤

创建新脚本 `ci/your_script.ps1`，参考现有脚本结构：
```powershell
param(
    [switch]$YourFlag
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $PROJECT_ROOT

# 你的逻辑
Write-Host "Running custom step..." -ForegroundColor Yellow

exit 0
```

然后在 `run_all_ci.ps1` 中集成。

## 性能优化

- **并行测试**：使用 `-Parallel` 可利用多核 CPU
- **增量测试**：使用 `pytest --lf` 只运行上次失败的测试
- **缓存依赖**：GitHub Actions 已配置 pip cache
- **跳过慢速基准**：使用 `-Quick` 模式或指定版本

## 最佳实践

1. **提交前运行 CI**：避免破坏主分支
   ```powershell
   .\ci\run_all_ci.ps1 -Quick
   ```

2. **定期运行完整基准**：检测长期性能趋势
   ```powershell
   .\ci\run_benchmarks.ps1 -Compare -GenerateReport
   ```

3. **保持高覆盖率**：目标 > 80%
   ```powershell
   .\ci\run_tests.ps1 -Coverage
   ```

4. **自动修复格式问题**：减少手动调整
   ```powershell
   .\ci\run_quality.ps1 -Fix
   ```

5. **使用 pre-commit hooks**：自动化质量检查
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## 维护与更新

### 更新 CI 脚本

CI 脚本位于 `ci/` 目录，直接编辑即可。

### 更新 GitHub Actions

GitHub Actions 配置位于 `.github/workflows/`。修改后推送到远程仓库自动生效。

### 版本控制

CI 脚本和配置文件应纳入版本控制：
```
ci/
.github/workflows/
pytest.ini
pyproject.toml
.pre-commit-config.yaml
```

## 相关文档

- [pytest 文档](https://docs.pytest.org/)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Black 文档](https://black.readthedocs.io/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Mypy 文档](https://mypy.readthedocs.io/)

# HW-1 CI/CD 快速参考

## 日常命令速查表

### 开发前检查
```powershell
# 检查项目健康状况
.\ci\check_health.ps1

# 拉取最新代码
git pull
```

### 开发中快速验证
```powershell
# 自动修复格式问题
.\ci\run_quality.ps1 -Fix

# 运行单元测试
.\ci\run_tests.ps1 -Markers "unit"

# 组合：格式化 + 单元测试
.\ci\run_quality.ps1 -Fix; if ($?) { .\ci\run_tests.ps1 -Markers "unit" }
```

### 提交前完整检查
```powershell
# 快速模式（推荐）
.\ci\run_all_ci.ps1 -Quick

# 完整模式
.\ci\run_all_ci.ps1

# 完整模式 + 文档生成
.\ci\run_all_ci.ps1 -GenerateDocs
```

### 测试相关
```powershell
# 基础测试
.\ci\run_tests.ps1 -Coverage                    # 所有测试 + 覆盖率
.\ci\run_tests.ps1 -Parallel -Coverage          # 并行运行（加速）
.\ci\run_tests.ps1 -Markers "unit"              # 只运行单元测试
.\ci\run_tests.ps1 -Markers "regression"        # 只运行回归测试
.\ci\run_tests.ps1 -Markers "not slow"          # 跳过慢速测试
.\ci\run_tests.ps1 -Verbose                     # 详细输出

# 高级测试
pytest --lf                                      # 只运行上次失败的测试
pytest --ff                                      # 先运行失败的测试
pytest --pdb                                     # 失败时进入调试器
pytest tests/unit/test_specific.py              # 运行单个文件
pytest -k "test_gait"                            # 关键字过滤
```

### 代码质量
```powershell
# 完整质量检查
.\ci\run_quality.ps1                             # 所有检查
.\ci\run_quality.ps1 -Fix                        # 自动修复
.\ci\run_quality.ps1 -Strict                     # 严格模式

# 单独工具
.\ci\run_quality.ps1 -Tool "black"               # 只运行 Black
.\ci\run_quality.ps1 -Tool "ruff"                # 只运行 Ruff
.\ci\run_quality.ps1 -Tool "mypy"                # 只运行 Mypy
.\ci\run_quality.ps1 -Tool "radon"               # 只运行 Radon

# 手动运行工具
python -m black .                                # 格式化所有文件
python -m black --check .                        # 检查格式
python -m ruff check .                           # Linting
python -m ruff check --fix .                     # Linting + 自动修复
python -m mypy common/                           # 类型检查
```

### 性能基准
```powershell
# 基础基准测试
.\ci\run_benchmarks.ps1                          # 运行所有版本
.\ci\run_benchmarks.ps1 -Compare                 # 与上次对比
.\ci\run_benchmarks.ps1 -Compare -GenerateReport # 对比 + 可视化

# 指定版本测试
.\ci\run_benchmarks.ps1 -Versions "v10,v13_7_refactored,v17"

# 自定义阈值
.\ci\run_benchmarks.ps1 -Compare -Threshold 15
```

### 文档生成
```powershell
.\ci\generate_docs.ps1                           # 生成覆盖率报告
.\ci\generate_docs.ps1 -ApiDocs                  # 生成 API 文档
.\ci\generate_docs.ps1 -UpdateBadges             # 更新 README 徽章
```

### 项目监控
```powershell
.\ci\check_health.ps1                            # 健康检查
.\ci\check_health.ps1 -Detailed                  # 详细输出
.\ci\check_health.ps1 -Json                      # JSON 输出

.\ci\update_dashboard.ps1                        # 更新 dashboard 数据
.\ci\generate_weekly_report.ps1                  # 生成周报
```

### Git Hooks
```powershell
# 安装 hooks
.\ci\install_hooks.ps1                           # 安装
.\ci\install_hooks.ps1 -Force                    # 强制覆盖

# 使用 pre-commit 框架（推荐）
pip install pre-commit                           # 安装
pre-commit install                               # 启用
pre-commit run --all-files                       # 手动运行所有 hooks
pre-commit autoupdate                            # 更新 hooks 版本

# 跳过 hooks（不推荐）
git commit --no-verify                           # 跳过 pre-commit
git push --no-verify                             # 跳过 pre-push
```

### Git 工作流
```powershell
# 功能开发
git checkout -b feature/my-feature               # 创建功能分支
# ... 开发 ...
.\ci\run_all_ci.ps1 -Quick                       # 提交前检查
git add .
git commit -m "feat: add new feature"            # 提交（自动运行 pre-commit）
git push origin feature/my-feature               # 推送（自动运行 pre-push）

# Bug 修复
git checkout -b fix/bug-name                     # 创建修复分支
# ... 修复 ...
.\ci\run_tests.ps1 -Markers "unit"               # 快速验证
git commit -m "fix: resolve bug"
git push origin fix/bug-name
```

---

## Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型（type）
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例
```bash
feat(v17): add Kalman filter state estimator

- Implement sensor noise simulation
- Add position and velocity estimation
- Update benchmark configs for V17

Closes #123
```

---

## 测试标记（Markers）

```python
@pytest.mark.unit          # 单元测试（快速）
@pytest.mark.regression    # 回归测试（仿真）
@pytest.mark.integration   # 集成测试
@pytest.mark.slow          # 慢速测试（>5秒）
```

### 使用方式
```powershell
pytest -m "unit"                                 # 只运行单元测试
pytest -m "regression"                           # 只运行回归测试
pytest -m "not slow"                             # 跳过慢速测试
pytest -m "unit or regression"                   # 运行多种标记
```

---

## 快捷键绑定（可选）

在 PowerShell profile 中添加别名（`$PROFILE`）：

```powershell
# 导航
function cdhw { Set-Location "D:\Dunna\Documents\hw-1" }

# CI 快捷方式
function ci-quick { & "D:\Dunna\Documents\hw-1\ci\run_all_ci.ps1" -Quick }
function ci-full { & "D:\Dunna\Documents\hw-1\ci\run_all_ci.ps1" }
function ci-test { & "D:\Dunna\Documents\hw-1\ci\run_tests.ps1" -Markers "unit" }
function ci-fix { & "D:\Dunna\Documents\hw-1\ci\run_quality.ps1" -Fix }
function ci-health { & "D:\Dunna\Documents\hw-1\ci\check_health.ps1" }

# 使用示例
# cdhw          # 跳转到项目目录
# ci-quick      # 运行快速 CI
# ci-fix        # 自动修复格式
```

---

## 常见问题快速修复

| 问题 | 命令 |
|------|------|
| 格式不符合规范 | `.\ci\run_quality.ps1 -Fix` |
| 测试失败 | `pytest --lf` (只运行失败的测试) |
| 虚拟环境问题 | 重新创建：`python -m venv .venv-mujoco` |
| Hooks 不生效 | `.\ci\install_hooks.ps1 -Force` |
| 依赖过时 | `pip install --upgrade -r requirements-dev.txt` |
| 覆盖率不足 | 查看 `htmlcov\index.html` 找缺失覆盖的文件 |

---

## CI 执行时间参考

| 模式 | 时间 | 说明 |
|------|------|------|
| 单元测试 | ~1 分钟 | `.\ci\run_tests.ps1 -Markers "unit"` |
| 质量检查 | ~30 秒 | `.\ci\run_quality.ps1` |
| 快速 CI | ~2-3 分钟 | `.\ci\run_all_ci.ps1 -Quick` |
| 完整 CI | ~5-10 分钟 | `.\ci\run_all_ci.ps1` |
| 基准测试 | ~3-5 分钟 | `.\ci\run_benchmarks.ps1` |

---

## 相关文档

- **[CI_CD_GUIDE.md](CI_CD_GUIDE.md)**: 完整指南（8000+ 字）
- **[CI_CD_IMPROVEMENTS.md](CI_CD_IMPROVEMENTS.md)**: 改进总结
- **[ci/README.md](ci/README.md)**: CI 脚本说明

---

**快速参考版本**: v1.0.0  
**最后更新**: 2026-06-05

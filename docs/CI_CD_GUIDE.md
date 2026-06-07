# CI/CD 指南

> 合并自：CI_CD_GUIDE.md, CI_CD_IMPROVEMENTS.md, CI_CD_QUICKREF.md, CI_CD_COMPLETION_REPORT.md

## 概述

本项目使用 GitHub Actions 进行持续集成和持续部署。

## 工作流

### 1. 代码质量检查 (`.github/workflows/code_quality.yml`)

**触发条件：** 每次 push 和 pull request

**检查项：**
- ✅ Black 代码格式化
- ✅ Ruff linting
- ✅ MyPy 类型检查

```yaml
name: Code Quality
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Black
        run: black --check .
      - name: Run Ruff
        run: ruff check .
```

### 2. 测试 (`.github/workflows/tests.yml`)

**触发条件：** 每次 push 到 main 分支

**测试项：**
- ✅ 单元测试
- ✅ 集成测试
- ✅ 覆盖率报告

```bash
# 本地运行测试
pytest tests/ --cov=common --cov-report=html
```

### 3. 基准测试 (`.github/workflows/benchmarks.yml`)

**触发条件：** 手动触发或周度自动运行

**测试内容：**
- 仿真性能
- 渲染性能
- 内存使用

### 4. 文档构建 (`.github/workflows/docs.yml`)

**触发条件：** docs/ 目录变更

**构建内容：**
- API 文档
- 用户指南
- 教程

## 本地开发流程

### Pre-commit Hooks

项目使用 pre-commit 确保代码质量：

```powershell
# 安装 pre-commit
pip install pre-commit

# 安装 hooks
pre-commit install

# 手动运行所有 hooks
pre-commit run --all-files
```

### 代码格式化

```powershell
# 格式化所有 Python 文件
black .

# 检查但不修改
black --check .
```

### Linting

```powershell
# 运行 Ruff
ruff check .

# 自动修复
ruff check --fix .
```

### 类型检查

```powershell
# 运行 MyPy
mypy common/ --ignore-missing-imports
```

## 发布流程

### 1. 版本标记

```powershell
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 2. 自动发布

标签推送后，GitHub Actions 会自动：
1. 运行完整测试套件
2. 构建文档
3. 创建 GitHub Release
4. 上传产物

## 故障排查

### CI 失败

**问题：** 测试在 CI 中失败但本地通过

**解决：**
1. 检查 Python 版本是否一致
2. 确保依赖版本固定
3. 查看 CI 日志获取详细错误

### Pre-commit Hook 失败

**问题：** 提交时 hook 失败

**解决：**
```powershell
# 跳过 hooks（仅紧急情况）
git commit --no-verify

# 或修复问题后重新提交
black .
ruff check --fix .
git add .
git commit
```

## 参考资料

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [pre-commit 文档](https://pre-commit.com/)
- [配置文件](.github/workflows/)

# hw-1 项目环境设置指南

本文档提供 hw-1 步态训练辅助设备仿真研究项目的完整环境设置指南。

---

## 目录

- [快速开始](#快速开始)
- [虚拟环境说明](#虚拟环境说明)
- [环境变量配置](#环境变量配置)
- [IDE 设置推荐](#ide-设置推荐)
- [编辑器插件推荐](#编辑器插件推荐)
- [故障排查](#故障排查)
- [环境管理脚本](#环境管理脚本)

---

## 快速开始

### 1. 自动化环境设置（推荐）

使用提供的 PowerShell 脚本自动验证或重建环境：

```powershell
# 验证现有环境
.\scripts\setup_env.ps1 -Verify

# 清理并重建环境（需要确认）
.\scripts\setup_env.ps1 -Clean

# 强制重建（不询问确认）
.\scripts\setup_env.ps1 -Clean -Force
```

### 2. 手动环境设置

如果需要手动设置环境：

```powershell
# 1. 确保 Python 3.10 已安装
python --version  # 应显示 Python 3.10.x

# 2. 创建虚拟环境（如果不存在）
python -m venv .venv-mujoco

# 3. 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 4. 升级 pip
python -m pip install --upgrade pip setuptools wheel

# 5. 安装项目依赖
pip install -r requirements.txt

# 6. 安装开发工具（可选）
pip install -e .[dev]

# 7. 安装 pre-commit hooks（推荐）
pre-commit install
```

### 3. 验证安装

```powershell
# 测试 MuJoCo 导入
python -c "import mujoco; print(f'MuJoCo {mujoco.__version__}')"

# 运行测试套件
pytest tests/ -v

# 运行示例仿真
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

---

## 虚拟环境说明

### 为什么有两个虚拟环境？

项目中存在两个虚拟环境，用途不同：

| 环境 | Python 版本 | 用途 | 创建者 |
|------|------------|------|--------|
| `.venv-mujoco` | 3.10.11 | 主要开发环境，运行 MuJoCo 仿真 | 手动创建 |
| `.venv-codex` | 3.12.13 | Claude Code 内部使用 | Claude Code 自动 |

### 推荐使用策略

- **日常开发**：使用 `.venv-mujoco`
- **运行仿真**：使用 `.venv-mujoco`
- **运行测试**：使用 `.venv-mujoco`
- **Claude Code 交互**：自动使用 `.venv-codex`，无需手动切换

### 虚拟环境激活

```powershell
# 激活主要环境
.\.venv-mujoco\Scripts\Activate.ps1

# 退出虚拟环境
deactivate
```

### 虚拟环境管理

```powershell
# 导出当前环境的包列表
pip freeze > requirements-freeze.txt

# 清理并重建环境
Remove-Item -Recurse -Force .venv-mujoco
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt

# 查看已安装的包
pip list

# 检查过期的包
pip list --outdated
```

---

## 环境变量配置

### 创建 .env 文件

项目提供了 `.env.example` 模板：

```powershell
# 复制模板
Copy-Item .env.example .env

# 编辑配置（使用你喜欢的编辑器）
notepad .env
```

### 关键环境变量

以下是最重要的环境变量配置：

```bash
# 项目根路径
HW1_PROJECT_ROOT=D:\Dunna\Documents\hw-1

# 虚拟环境路径
HW1_VENV_MUJOCO=D:\Dunna\Documents\hw-1\.venv-mujoco

# 日志级别（开发时设为 DEBUG，生产时设为 INFO）
LOG_LEVEL=INFO

# 启用性能分析（调试性能问题时）
ENABLE_PROFILING=false

# MuJoCo 渲染后端
MUJOCO_GL=egl
```

### 在 Python 中加载环境变量

项目未内置环境变量加载，如需使用可添加 `python-dotenv`：

```powershell
# 安装 python-dotenv
pip install python-dotenv

# 在脚本中加载
# 在 Python 脚本顶部添加：
from dotenv import load_dotenv
load_dotenv()

import os
project_root = os.getenv('HW1_PROJECT_ROOT')
```

---

## IDE 设置推荐

### Visual Studio Code

#### 1. 安装 VS Code

下载：https://code.visualstudio.com/

#### 2. 推荐扩展

安装以下扩展以获得最佳开发体验：

```json
{
  "recommendations": [
    "ms-python.python",              // Python 支持
    "ms-python.vscode-pylance",      // Python 语言服务器
    "ms-python.black-formatter",     // Black 格式化
    "charliermarsh.ruff",            // Ruff 代码检查
    "ms-python.mypy-type-checker",   // Mypy 类型检查
    "editorconfig.editorconfig",     // EditorConfig 支持
    "eamodio.gitlens",               // Git 增强
    "github.copilot",                // GitHub Copilot（可选）
    "ms-vscode.powershell",          // PowerShell 支持
    "bierner.markdown-mermaid",      // Markdown 图表
    "yzhang.markdown-all-in-one"     // Markdown 增强
  ]
}
```

将上述内容保存到 `.vscode/extensions.json`（已在下一步创建）。

#### 3. 工作区设置

创建 `.vscode/settings.json`：

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\.venv-mujoco\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    },
    "editor.rulers": [88]
  },
  
  "black-formatter.args": [
    "--line-length=88"
  ],
  
  "ruff.lint.args": [
    "--config=${workspaceFolder}\\pyproject.toml"
  ],
  
  "mypy-type-checker.args": [
    "--config-file=${workspaceFolder}\\pyproject.toml"
  ],
  
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ],
  
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true,
    "**/*.pyc": true
  },
  
  "files.watcherExclude": {
    "**/.venv-mujoco/**": true,
    "**/.venv-codex/**": true,
    "**/node_modules/**": true,
    "**/.git/objects/**": true
  },
  
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": "explicit"
  },
  
  "terminal.integrated.defaultProfile.windows": "PowerShell",
  "terminal.integrated.env.windows": {
    "HW1_PROJECT_ROOT": "${workspaceFolder}"
  }
}
```

#### 4. 启动配置

创建 `.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: 当前文件",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true,
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: 仿真脚本",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/v13_7_refactored/simulate_v13_7.py",
      "console": "integratedTerminal",
      "args": [
        "--duration",
        "10.0"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v"
      ],
      "console": "integratedTerminal",
      "justMyCode": false,
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

### PyCharm

#### 1. 项目设置

项目已包含 `.idea/` 配置目录，PyCharm 会自动识别。

#### 2. 配置 Python 解释器

1. 打开 **File > Settings > Project: hw-1 > Python Interpreter**
2. 点击齿轮图标 > **Add**
3. 选择 **Existing environment**
4. 浏览到 `D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe`
5. 点击 **OK**

#### 3. 配置代码风格

1. 打开 **File > Settings > Editor > Code Style > Python**
2. 点击齿轮图标 > **Import Scheme > EditorConfig**
3. 项目的 `.editorconfig` 会自动应用

#### 4. 配置运行配置

1. 右键点击 `simulate_v13_7.py`
2. 选择 **Modify Run Configuration**
3. 设置：
   - **Working directory**: `D:\Dunna\Documents\hw-1`
   - **Environment variables**: `PYTHONPATH=D:\Dunna\Documents\hw-1`
   - **Parameters**: `--duration 10.0`

---

## 编辑器插件推荐

### VS Code 必备插件

| 插件 | 用途 | 优先级 |
|------|------|--------|
| Python | Python 语言支持 | ⭐⭐⭐ |
| Pylance | 智能代码补全 | ⭐⭐⭐ |
| Black Formatter | 代码格式化 | ⭐⭐⭐ |
| Ruff | 快速 Lint | ⭐⭐⭐ |
| EditorConfig | 统一代码风格 | ⭐⭐ |
| GitLens | Git 增强 | ⭐⭐ |
| PowerShell | PowerShell 支持 | ⭐⭐ |
| Markdown All in One | Markdown 增强 | ⭐⭐ |

### PyCharm 插件推荐

| 插件 | 用途 | 优先级 |
|------|------|--------|
| .ignore | .gitignore 支持 | ⭐⭐ |
| Rainbow Brackets | 括号配对高亮 | ⭐ |
| Key Promoter X | 快捷键学习 | ⭐ |

---

## 故障排查

### 问题 1：MuJoCo 导入失败

**症状**：
```
ImportError: DLL load failed while importing _render
```

**解决方案**：
```powershell
# 1. 确认使用正确的虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 2. 重新安装 MuJoCo
pip uninstall mujoco
pip install mujoco>=3.3.7

# 3. 验证安装
python -c "import mujoco; print(mujoco.__version__)"
```

### 问题 2：pytest 找不到模块

**症状**：
```
ModuleNotFoundError: No module named 'common'
```

**解决方案**：
```powershell
# 确保 PYTHONPATH 包含项目根目录
$env:PYTHONPATH = "D:\Dunna\Documents\hw-1"
pytest tests/

# 或者安装项目为可编辑包
pip install -e .
```

### 问题 3：pre-commit hooks 失败

**症状**：
```
[ERROR] File not found
```

**解决方案**：
```powershell
# 重新安装 pre-commit hooks
pre-commit uninstall
pre-commit install

# 手动运行检查所有文件
pre-commit run --all-files
```

### 问题 4：虚拟环境损坏

**症状**：
```
python.exe 找不到或无法启动
```

**解决方案**：
```powershell
# 使用设置脚本重建
.\scripts\setup_env.ps1 -Clean -Force
```

### 问题 5：PowerShell 执行策略错误

**症状**：
```
无法加载文件 activate.ps1，因为在此系统上禁止运行脚本
```

**解决方案**：
```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或仅对当前会话
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

---

## 环境管理脚本

### setup_env.ps1

主要环境设置和验证脚本。

**用法**：

```powershell
# 验证环境
.\scripts\setup_env.ps1 -Verify

# 清理重建
.\scripts\setup_env.ps1 -Clean

# 强制重建（不询问）
.\scripts\setup_env.ps1 -Clean -Force
```

**功能**：
- 验证 Python 3.10 安装
- 检查虚拟环境状态
- 验证依赖安装
- 检查配置文件完整性
- 运行快速导入测试
- 生成环境报告

### 其他实用脚本

项目还包含其他管理脚本：

```powershell
# 清理临时文件
.\cleanup_temp.ps1

# 压缩大型数据文件
.\compress_large_data.ps1

# 归档旧版本
.\archive_old_versions.ps1

# 运行监控
.\run_monitoring.ps1
```

---

## 开发工作流

### 日常开发流程

```powershell
# 1. 激活环境
.\.venv-mujoco\Scripts\Activate.ps1

# 2. 拉取最新代码
git pull

# 3. 安装/更新依赖
pip install -r requirements.txt

# 4. 运行测试
pytest tests/ -v

# 5. 开始开发
# ... 修改代码 ...

# 6. 运行代码检查
ruff check .
black .
mypy common/

# 7. 运行测试
pytest tests/

# 8. 提交代码
git add .
git commit -m "feat: 描述你的修改"

# 9. 推送
git push
```

### 运行仿真工作流

```powershell
# 1. 激活环境
.\.venv-mujoco\Scripts\Activate.ps1

# 2. 运行仿真（示例：V13.7）
python v13_7_refactored\simulate_v13_7.py --duration 12.0

# 3. 分析结果
python v13_7_refactored\analyze_v13_7.py

# 4. 可视化
python v13_7_refactored\view_v13_7.py

# 5. 渲染视频（可选）
python v13_7_refactored\render_v13_7.py
```

---

## 性能优化建议

### 排除大型目录

在 IDE 中排除以下目录以提高性能：

- `.venv-mujoco/`
- `.venv-codex/`
- `node_modules/`
- `.git/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`

### Git 性能优化

```powershell
# 启用 Git 文件系统监控
git config core.fsmonitor true
git config core.untrackedcache true

# 禁用自动 gc
git config gc.auto 0
```

---

## 联系与支持

- **项目负责人**：段泽琪
- **学号**：2024211317
- **邮箱**：2024211317@buct.edu.cn

如有问题，请参考：
1. [README.md](README.md) - 项目概述
2. [QUICKSTART.md](QUICKSTART.md) - 快速入门
3. [CLAUDE.md](CLAUDE.md) - 协作约定

---

## 附录：完整配置文件清单

项目配置文件完整清单：

| 文件 | 用途 | 状态 |
|------|------|------|
| `pyproject.toml` | 现代 Python 项目配置 | ✅ 已有 |
| `setup.py` | 包安装配置 | ✅ 新增 |
| `requirements.txt` | 依赖列表 | ✅ 已有 |
| `pytest.ini` | Pytest 配置 | ✅ 已有 |
| `.pre-commit-config.yaml` | Git hooks | ✅ 已有 |
| `.editorconfig` | 编辑器风格 | ✅ 新增 |
| `.gitignore` | Git 忽略规则 | ✅ 已有 |
| `.env.example` | 环境变量模板 | ✅ 新增 |
| `.vscode/settings.json` | VS Code 设置 | 📝 见本文档 |
| `.vscode/launch.json` | 调试配置 | 📝 见本文档 |
| `.vscode/extensions.json` | 推荐扩展 | 📝 见本文档 |
| `.idea/*` | PyCharm 配置 | ✅ 已有 |

---

**最后更新**：2026-06-05

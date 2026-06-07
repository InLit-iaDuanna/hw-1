# hw-1 项目配置文件总结

本文档汇总了 hw-1 项目中所有配置文件的用途和位置。

---

## 配置文件清单

### Python 项目配置

| 文件 | 用途 | 状态 |
|------|------|------|
| `pyproject.toml` | 现代 Python 项目配置（Black、Ruff、Mypy、项目元数据） | ✅ 已完善 |
| `setup.py` | 包安装配置，支持 `pip install -e .` | ✅ 新增 |
| `requirements.txt` | 生产环境依赖列表 | ✅ 已有 |
| `pytest.ini` | Pytest 测试框架配置 | ✅ 已有 |

### 代码质量工具

| 文件 | 用途 | 状态 |
|------|------|------|
| `.pre-commit-config.yaml` | Git pre-commit hooks 配置 | ✅ 已有 |
| `.editorconfig` | 统一编辑器代码风格 | ✅ 新增 |
| `.gitignore` | Git 忽略规则 | ✅ 已有 |

### 环境管理

| 文件 | 用途 | 状态 |
|------|------|------|
| `.env.example` | 环境变量模板 | ✅ 新增 |
| `.env` | 实际环境变量（用户创建，不入库） | 📝 可选 |

### IDE 配置

| 文件/目录 | 用途 | 状态 |
|----------|------|------|
| `.vscode/settings.json` | VS Code 工作区设置 | ✅ 新增 |
| `.vscode/launch.json` | VS Code 调试配置 | ✅ 新增 |
| `.vscode/extensions.json` | VS Code 推荐扩展 | ✅ 新增 |
| `.idea/` | PyCharm 项目配置 | ✅ 已有 |

### 管理脚本

| 文件 | 用途 | 状态 |
|------|------|------|
| `scripts/setup_env.ps1` | 环境设置和验证主脚本 | ✅ 新增 |
| `scripts/check_deps.ps1` | 依赖检查和更新脚本 | ✅ 新增 |
| `scripts/switch_env.ps1` | 虚拟环境切换助手 | ✅ 新增 |

### 文档

| 文件 | 用途 | 状态 |
|------|------|------|
| `ENVIRONMENT_SETUP.md` | 完整环境设置指南 | ✅ 新增 |
| `README.md` | 项目总览 | ✅ 已有 |
| `CLAUDE.md` | AI 助手协作约定 | ✅ 已有 |

---

## 虚拟环境架构

项目使用两个独立的虚拟环境：

### .venv-mujoco（主要开发环境）
- **Python 版本**: 3.10.11
- **用途**: 日常开发、运行仿真、测试
- **关键依赖**: MuJoCo 3.3.7+, NumPy 2.2.6+, Matplotlib 3.10.7+
- **激活**: `.\.venv-mujoco\Scripts\Activate.ps1`

### .venv-codex（Claude Code 环境）
- **Python 版本**: 3.12.13
- **用途**: Claude Code 内部使用
- **管理**: 由 Claude Code 自动管理
- **说明**: 用户无需手动维护

---

## 配置文件详解

### pyproject.toml

现代 Python 项目的核心配置文件，包含：

- **项目元数据**: 名称、版本、作者、描述
- **依赖管理**: 生产依赖和可选依赖（dev、docs、profiling）
- **Black 配置**: 代码格式化，行长 88
- **Ruff 配置**: 快速 Linter，替代 Flake8/isort
- **Mypy 配置**: 类型检查，渐进式启用
- **命令行入口**: `hw1-benchmark` 等命令

**关键配置**:
```toml
[tool.black]
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM"]
```

### setup.py

包安装配置，支持可编辑安装：

```powershell
# 安装开发模式
pip install -e .

# 安装所有可选依赖
pip install -e .[dev,docs,profiling]
```

**提供的命令行工具**:
- `hw1-benchmark` - 运行基准测试
- `hw1-monitor` - 系统监控
- `hw1-profile` - 性能分析

### .editorconfig

统一不同编辑器的代码风格：

- **Python**: 4 空格缩进，UTF-8 编码
- **YAML/JSON**: 2 空格缩进
- **PowerShell**: Windows 行尾 (CRLF)
- **行尾**: 自动插入最终换行符

所有主流编辑器（VS Code、PyCharm、Sublime Text）都支持 EditorConfig。

### .pre-commit-config.yaml

Git 提交前自动运行的检查：

1. **Black** - 代码格式化
2. **Ruff** - 代码检查和自动修复
3. **Trailing whitespace** - 删除行尾空格
4. **YAML/JSON/TOML** - 格式验证
5. **Large files** - 防止提交大文件（>5MB）
6. **Mypy** - 类型检查（仅 common/ 目录）

**安装 hooks**:
```powershell
pre-commit install
```

**手动运行**:
```powershell
pre-commit run --all-files
```

### .env.example

环境变量模板，包含：

- **路径配置**: 项目根目录、数据目录、输出目录
- **Python 环境**: 虚拟环境路径
- **MuJoCo 配置**: 渲染设置、模型路径
- **仿真参数**: 默认时长、时间步长、帧率
- **测试配置**: 并行进程数、超时设置
- **日志配置**: 日志级别、格式、文件路径
- **可视化配置**: Matplotlib 后端、图形格式
- **开发工具**: 调试模式、性能分析

**使用方法**:
```powershell
# 复制模板
Copy-Item .env.example .env

# 根据本地环境编辑
notepad .env
```

---

## VS Code 配置说明

### settings.json

工作区设置，包括：

- **Python 解释器**: 自动使用 `.venv-mujoco`
- **格式化器**: Black（保存时自动格式化）
- **Linter**: Ruff
- **类型检查**: Mypy
- **测试框架**: Pytest
- **文件排除**: 隐藏 `__pycache__`、`.pytest_cache` 等
- **终端**: 默认使用 PowerShell

### launch.json

调试配置，预设了多个启动配置：

1. **Python: 当前文件** - 调试当前打开的 Python 文件
2. **Python: 仿真脚本 (V13.7)** - 调试 V13.7 仿真
3. **Python: 仿真脚本 (V14)** - 调试 V14 被动摆臂
4. **Python: 仿真脚本 (V19)** - 调试 V19 髋外展主动
5. **Python: Pytest 当前文件** - 调试当前测试文件
6. **Python: Pytest 所有测试** - 调试所有测试
7. **Python: 基准测试** - 调试基准测试

### extensions.json

推荐安装的 VS Code 扩展：

- `ms-python.python` - Python 支持
- `ms-python.vscode-pylance` - 智能补全
- `ms-python.black-formatter` - Black 格式化
- `charliermarsh.ruff` - Ruff Linter
- `ms-python.mypy-type-checker` - Mypy 类型检查
- `editorconfig.editorconfig` - EditorConfig 支持
- `eamodio.gitlens` - Git 增强
- `ms-vscode.powershell` - PowerShell 支持
- `yzhang.markdown-all-in-one` - Markdown 支持

---

## 管理脚本使用指南

### setup_env.ps1 - 环境设置主脚本

**验证现有环境**:
```powershell
.\scripts\setup_env.ps1 -Verify
```

**清理并重建环境**:
```powershell
.\scripts\setup_env.ps1 -Clean
```

**强制重建（不询问）**:
```powershell
.\scripts\setup_env.ps1 -Clean -Force
```

**功能**:
- 检查 Python 3.10 安装
- 验证虚拟环境状态
- 检查配置文件完整性
- 验证依赖安装
- 运行快速导入测试
- 生成环境报告

### check_deps.ps1 - 依赖管理脚本

**检查依赖状态**:
```powershell
.\scripts\check_deps.ps1
```

**更新所有依赖**:
```powershell
.\scripts\check_deps.ps1 -Update
```

**导出依赖列表**:
```powershell
.\scripts\check_deps.ps1 -Freeze
```

### switch_env.ps1 - 环境切换助手

**显示所有环境信息**:
```powershell
.\scripts\switch_env.ps1
```

**查看 MuJoCo 环境**:
```powershell
.\scripts\switch_env.ps1 mujoco
```

**查看 Codex 环境**:
```powershell
.\scripts\switch_env.ps1 codex
```

---

## 开发工作流最佳实践

### 1. 首次设置

```powershell
# 验证环境
.\scripts\setup_env.ps1 -Verify

# 如果需要，重建环境
.\scripts\setup_env.ps1 -Clean

# 安装 pre-commit hooks
.\.venv-mujoco\Scripts\Activate.ps1
pre-commit install
```

### 2. 日常开发

```powershell
# 激活环境
.\.venv-mujoco\Scripts\Activate.ps1

# 开始编码
# ... 修改代码 ...

# 运行代码检查（自动修复）
ruff check . --fix
black .

# 运行测试
pytest tests/ -v

# 提交代码（pre-commit 会自动运行检查）
git add .
git commit -m "描述"
```

### 3. 定期维护

```powershell
# 检查依赖更新
.\scripts\check_deps.ps1

# 更新依赖
.\scripts\check_deps.ps1 -Update

# 导出锁定的依赖版本
.\scripts\check_deps.ps1 -Freeze

# 验证环境健康
.\scripts\setup_env.ps1 -Verify
```

### 4. 故障排查

```powershell
# 生成环境报告
.\scripts\setup_env.ps1 -Verify
# 查看 ENVIRONMENT_REPORT.txt

# 检查虚拟环境状态
.\scripts\switch_env.ps1

# 重建损坏的环境
.\scripts\setup_env.ps1 -Clean -Force
```

---

## 配置文件与 Git

### 应入库的文件

- `pyproject.toml`
- `setup.py`
- `requirements.txt`
- `pytest.ini`
- `.pre-commit-config.yaml`
- `.editorconfig`
- `.gitignore`
- `.env.example`
- `.vscode/*.json`
- `scripts/*.ps1`
- `ENVIRONMENT_SETUP.md`

### 不应入库的文件

- `.env` - 个人环境变量配置
- `.venv-mujoco/` - 虚拟环境
- `.venv-codex/` - 虚拟环境
- `__pycache__/` - Python 缓存
- `.pytest_cache/` - Pytest 缓存
- `.mypy_cache/` - Mypy 缓存
- `.ruff_cache/` - Ruff 缓存
- `ENVIRONMENT_REPORT.txt` - 生成的报告

---

## 常见问题

### Q: 为什么有 pyproject.toml 和 setup.py？

A: `pyproject.toml` 是现代标准，但 `setup.py` 提供了更好的兼容性和灵活性。两者互补使用。

### Q: 需要手动创建 .env 文件吗？

A: 不必须。`.env.example` 提供了模板，按需创建 `.env` 并配置即可。

### Q: pre-commit hooks 会影响提交速度吗？

A: 会略有影响，但能防止提交低质量代码。可以用 `--no-verify` 跳过（不推荐）。

### Q: 两个虚拟环境都需要维护吗？

A: 只需维护 `.venv-mujoco`。`.venv-codex` 由 Claude Code 自动管理。

### Q: VS Code 配置会影响 PyCharm 吗？

A: 不会。两个 IDE 使用独立的配置文件。

---

## 相关文档

- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - 详细环境设置指南
- [README.md](README.md) - 项目概述
- [CLAUDE.md](CLAUDE.md) - AI 助手协作约定
- [QUICKSTART.md](QUICKSTART.md) - 快速入门

---

**最后更新**: 2026-06-05
**维护者**: 段泽琪 (2024211317@buct.edu.cn)

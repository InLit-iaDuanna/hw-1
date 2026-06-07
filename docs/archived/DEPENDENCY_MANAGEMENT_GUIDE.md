# hw-1 项目依赖管理指南

## 概述

本指南提供 hw-1 项目 Python 依赖的完整管理方案，包括依赖安装、更新、故障排除和最佳实践。

## 目录

1. [依赖文件结构](#依赖文件结构)
2. [快速开始](#快速开始)
3. [依赖层级说明](#依赖层级说明)
4. [安装指南](#安装指南)
5. [版本管理策略](#版本管理策略)
6. [常见问题与故障排除](#常见问题与故障排除)
7. [依赖更新流程](#依赖更新流程)
8. [最佳实践](#最佳实践)

---

## 依赖文件结构

项目采用分层依赖管理策略，根据功能需求组织依赖：

```
hw-1/
├── requirements-core.txt          # 核心仿真依赖（必需）
├── requirements-viz.txt           # 可视化依赖（推荐）
├── requirements-analysis.txt      # 数据分析依赖（推荐）
├── requirements-opt.txt           # 参数优化依赖（可选）
├── requirements-ui.txt            # UI工具依赖（可选）
├── requirements-dev.txt           # 开发测试依赖（开发者）
└── requirements.txt               # 旧版统一依赖（已废弃，保留以兼容）
```

### 依赖层级关系

```
requirements-core.txt (核心)
    ↓
requirements-viz.txt (可视化，引用 core)
    ↓
requirements-analysis.txt (分析，引用 viz)
    ↓
├── requirements-opt.txt (优化，引用 analysis)
├── requirements-ui.txt (UI，引用 analysis)
└── requirements-dev.txt (开发，引用 analysis)
```

---

## 快速开始

### 最小安装（仅运行仿真）

```powershell
# 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 安装核心依赖
pip install -r requirements-core.txt
```

### 标准安装（包含可视化和分析）

```powershell
# 推荐：大多数用户使用此配置
pip install -r requirements-analysis.txt
```

### 完整安装（包含所有功能）

```powershell
# 安装所有依赖（开发者、研究者）
pip install -r requirements-opt.txt
pip install -r requirements-ui.txt
pip install -r requirements-dev.txt
```

---

## 依赖层级说明

### 1. requirements-core.txt（核心仿真依赖）

**用途**: MuJoCo 仿真运行的最小依赖集

**包含**:
- `mujoco==3.3.7` - MuJoCo 物理仿真引擎
- `numpy==2.2.6` - 数值计算基础库
- `scipy>=1.10.0` - 科学计算工具
- `imageio==2.37.2` - 图像/视频 IO
- `imageio-ffmpeg==0.6.0` - 视频编码支持

**适用场景**:
- 仅需运行仿真脚本
- 无人机/服务器环境
- CI/CD 最小化安装

### 2. requirements-viz.txt（可视化依赖）

**用途**: 生成图表、动画和可视化结果

**额外包含**:
- `matplotlib==3.10.7` - 2D 绘图
- `pillow` - 图像处理
- `seaborn>=0.12.0` - 统计可视化
- `plotly>=5.17.0` - 交互式图表

**适用场景**:
- 需要查看仿真结果图表
- 生成动画和视频
- 数据可视化分析

### 3. requirements-analysis.txt（数据分析依赖）

**用途**: 数据处理、统计分析和结果导出

**额外包含**:
- `pandas>=2.0.0` - 数据处理
- `pyyaml>=6.0` - YAML 配置文件解析

**适用场景**:
- 大规模数据处理
- 跨版本性能对比
- 导出分析报告

### 4. requirements-opt.txt（参数优化依赖）

**用途**: 自动参数调优和优化算法

**额外包含**:
- `scikit-optimize>=0.9.0` - 贝叶斯优化
- `deap>=1.3.1` - 遗传算法
- `cma>=3.2.2` - CMA-ES 优化
- `scikit-learn>=1.3.0` - 机器学习工具
- `pymoo>=0.6.0` - 多目标优化
- `salib>=1.4.7` - 敏感性分析
- `joblib>=1.3.0` - 并行计算

**适用场景**:
- 使用 `auto_optimization/` 工具
- 使用 `parameter_explorer/` 工具
- 大规模参数空间搜索

### 5. requirements-ui.txt（UI 工具依赖）

**用途**: 交互式参数调节界面

**额外包含**:
- `streamlit>=1.28.0` - Web UI 框架

**适用场景**:
- 使用 `parameter_tuner/` 交互式调参工具
- 需要 Web 界面查看结果

### 6. requirements-dev.txt（开发测试依赖）

**用途**: 开发调试和自动化测试

**额外包含**:
- `pytest>=7.4.0` - 测试框架
- `pytest-cov>=4.1.0` - 测试覆盖率
- `pytest-xdist>=3.3.0` - 并行测试
- `pytest-timeout>=2.1.0` - 测试超时控制

**适用场景**:
- 开发新功能
- 运行测试套件
- CI/CD 测试环境

---

## 安装指南

### 首次环境搭建

```powershell
# 1. 创建虚拟环境（如果不存在）
python -m venv .venv-mujoco

# 2. 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 3. 升级 pip
python -m pip install --upgrade pip

# 4. 根据需求安装依赖（选择以下之一）

# 选项 A: 标准安装（推荐）
pip install -r requirements-analysis.txt

# 选项 B: 最小安装
pip install -r requirements-core.txt

# 选项 C: 完整安装
pip install -r requirements-analysis.txt
pip install -r requirements-opt.txt
pip install -r requirements-ui.txt
pip install -r requirements-dev.txt
```

### 验证安装

```powershell
# 验证核心包
python -c "import mujoco; print(f'MuJoCo {mujoco.__version__}')"
python -c "import numpy; print(f'NumPy {numpy.__version__}')"

# 运行测试（如果安装了 dev 依赖）
pytest --version
```

### 子项目依赖

某些版本目录（v01-v16）有自己的 `requirements.txt`，但这些**已过时**。建议：

```powershell
# 不要在子目录安装依赖
# cd v01_mujoco_compass_gait
# pip install -r requirements.txt  # ❌ 不推荐

# 而是在项目根目录统一安装
cd D:\Dunna\Documents\hw-1
pip install -r requirements-analysis.txt  # ✅ 推荐
```

---

## 版本管理策略

### 版本锁定策略

| 包 | 版本策略 | 理由 |
|---|----------|------|
| `mujoco` | `==3.3.7` 精确锁定 | 物理引擎核心，版本敏感 |
| `numpy` | `==2.2.6` 精确锁定 | 数值计算基础，API 变化大 |
| `matplotlib` | `==3.10.7` 精确锁定 | 绘图结果一致性 |
| `imageio` | `==2.37.2` 精确锁定 | 视频编码兼容性 |
| `scipy` | `>=1.10.0` 最低版本 | 向后兼容性好 |
| `pandas` | `>=2.0.0` 最低版本 | API 稳定 |
| 其他 | `>=x.y.z` 最低版本 | 允许小版本更新 |

### 版本冲突解决

#### 已知冲突 1: numpy 版本

**问题**: 不同依赖要求不同的 numpy 版本
- V01 锁定 `numpy==2.2.6`
- auto_optimization 要求 `numpy>=1.21.0`
- parameter_explorer 要求 `numpy>=1.24.0`

**解决方案**: 统一使用 `numpy==2.2.6`（向后兼容）

```powershell
pip install numpy==2.2.6
```

#### 已知冲突 2: mujoco 版本

**问题**: 版本要求范围不一致
- `mujoco>=2.3.0` (auto_optimization)
- `mujoco>=3.0` (v15 系列)
- `mujoco==3.3.7` (v01, v16)

**解决方案**: 统一使用 `mujoco==3.3.7`（最新稳定版）

```powershell
pip install mujoco==3.3.7
```

---

## 常见问题与故障排除

### 问题 1: 导入 mujoco 失败

**症状**:
```
ImportError: DLL load failed while importing _render
```

**原因**: Windows 缺少 Visual C++ 运行库

**解决方案**:
1. 下载安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 重启 PowerShell
3. 重新激活虚拟环境

### 问题 2: numpy 版本不兼容

**症状**:
```
AttributeError: module 'numpy' has no attribute 'float'
```

**原因**: numpy 2.0+ 移除了旧的别名

**解决方案**:
```powershell
pip install numpy==2.2.6
# 或者如果需要旧版本
pip install "numpy<2.0"
```

### 问题 3: matplotlib 中文显示问题

**症状**: 图表中文显示为方框

**解决方案**:
```python
# 在脚本开头添加
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

### 问题 4: imageio-ffmpeg 编码失败

**症状**:
```
RuntimeError: ffmpeg not found
```

**解决方案**:
```powershell
# 重新安装 imageio-ffmpeg
pip uninstall imageio-ffmpeg -y
pip install imageio-ffmpeg==0.6.0

# 验证
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
```

### 问题 5: pytest 找不到模块

**症状**:
```
ModuleNotFoundError: No module named 'common'
```

**原因**: Python 路径配置问题

**解决方案**:
```powershell
# 在项目根目录运行测试
cd D:\Dunna\Documents\hw-1
$env:PYTHONPATH = $PWD
pytest
```

### 问题 6: 虚拟环境激活失败

**症状**:
```
Activate.ps1 cannot be loaded because running scripts is disabled
```

**解决方案**:
```powershell
# 设置执行策略（管理员权限）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或者使用激活脚本
& .\.venv-mujoco\Scripts\Activate.ps1
```

---

## 依赖更新流程

### 检查可更新包

```powershell
# 列出过期包
pip list --outdated

# 仅检查特定包
pip list --outdated | Select-String "numpy|scipy|matplotlib"
```

### 更新非核心依赖

```powershell
# 更新可视化工具（相对安全）
pip install --upgrade seaborn plotly

# 更新数据分析工具
pip install --upgrade pandas pyyaml
```

### 更新核心依赖（谨慎）

⚠️ **警告**: 更新核心依赖前请备份环境

```powershell
# 1. 备份当前环境
pip freeze > requirements-backup-$(Get-Date -Format 'yyyyMMdd').txt

# 2. 更新 numpy（高风险）
pip install --upgrade numpy

# 3. 测试关键功能
python -c "import numpy as np; import mujoco; print('OK')"

# 4. 运行完整测试套件
pytest

# 5. 如果失败，回滚
pip install -r requirements-backup-yyyyMMdd.txt
```

### 锁定新版本

如果更新成功，更新 requirements 文件：

```powershell
# 导出当前环境
pip freeze > requirements-current.txt

# 手动编辑 requirements-core.txt，更新版本号
# 例如: numpy==2.2.6 -> numpy==2.3.0
```

---

## 最佳实践

### 1. 虚拟环境隔离

✅ **推荐**:
```powershell
# 每个项目独立虚拟环境
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
```

❌ **避免**:
```powershell
# 在系统全局安装
pip install mujoco  # 可能污染系统 Python
```

### 2. 依赖最小化原则

✅ **推荐**:
```powershell
# 根据实际需求安装
pip install -r requirements-core.txt  # 仅需仿真
```

❌ **避免**:
```powershell
# 一次性安装所有依赖
pip install -r requirements-opt.txt  # 实际不用优化工具
```

### 3. 版本锁定策略

✅ **推荐**:
```
# requirements-core.txt
mujoco==3.3.7      # 核心包精确锁定
numpy==2.2.6       # 核心包精确锁定
scipy>=1.10.0      # 辅助包最低版本
```

❌ **避免**:
```
# 不指定版本（不可复现）
mujoco
numpy
scipy
```

### 4. 定期审计依赖

```powershell
# 每月检查安全漏洞
pip install safety
safety check

# 每季度审查依赖使用情况
python analyze_dependencies.py
```

### 5. 文档同步

更新依赖后，同步更新文档：

1. 更新 `requirements-*.txt`
2. 重新运行 `python analyze_dependencies.py`
3. 更新 `DEPENDENCY_REPORT.md`
4. 提交 Git 记录

```powershell
git add requirements-*.txt DEPENDENCY_REPORT.md
git commit -m "chore: update dependencies to numpy 2.3.0"
```

---

## 依赖关系图

![依赖关系图](DEPENDENCY_GRAPH.png)

## 版本兼容性矩阵

![版本矩阵](DEPENDENCY_VERSION_MATRIX.png)

---

## 附录

### A. 完整依赖列表

详见 [DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md)

### B. 子项目依赖映射

| 子项目 | 推荐依赖文件 |
|--------|-------------|
| v01-v16 仿真脚本 | requirements-viz.txt |
| auto_optimization/ | requirements-opt.txt |
| parameter_tuner/ | requirements-ui.txt |
| parameter_explorer/ | requirements-opt.txt |
| data_storage/ | requirements-analysis.txt |
| analysis_pipeline/ | requirements-analysis.txt |
| benchmarks/ | requirements-analysis.txt |
| 测试开发 | requirements-dev.txt |

### C. 外部依赖

以下依赖来自外部系统，不通过 pip 安装：

- **Abaqus CAE** (商业 FEA 软件)
  - `abaqus`
  - `abaqusConstants`
  - `odbAccess`
  
  仅在运行 Abaqus 集成脚本时需要。

### D. Python 版本要求

- **最低版本**: Python 3.9
- **推荐版本**: Python 3.10 或 3.11
- **已测试版本**: Python 3.10.11, 3.11.5

### E. 操作系统兼容性

| 操作系统 | 支持状态 | 备注 |
|---------|---------|------|
| Windows 10/11 | ✅ 完全支持 | 主要开发环境 |
| Linux (Ubuntu 20.04+) | ✅ 支持 | 需手动配置 ffmpeg |
| macOS | ⚠️ 部分支持 | MuJoCo 渲染可能有问题 |

---

## 贡献与反馈

如发现依赖问题或有改进建议，请：

1. 检查 [DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md)
2. 运行 `python analyze_dependencies.py` 重新分析
3. 提交问题报告，包含：
   - 错误信息
   - Python 版本 (`python --version`)
   - 依赖版本 (`pip freeze`)
   - 操作系统信息

---

**最后更新**: 2026-06-05  
**维护者**: hw-1 项目组

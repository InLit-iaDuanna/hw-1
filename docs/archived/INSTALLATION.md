# hw-1 项目安装指南

本文档提供 hw-1 步态训练辅助设备仿真研究项目的完整安装指南，确保新用户在 10 分钟内完成环境配置并运行第一个示例。

---

## 目录

- [系统要求](#系统要求)
- [快速安装（推荐）](#快速安装推荐)
- [详细安装步骤](#详细安装步骤)
- [安装验证](#安装验证)
- [安装方案对比](#安装方案对比)
- [常见问题排查](#常见问题排查)

---

## 系统要求

### 最低要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 11 / Windows 10 (20H2+) |
| **Python** | 3.9+ (推荐 3.10.11) |
| **RAM** | 8 GB+ (推荐 16 GB) |
| **磁盘空间** | 5 GB 可用空间 |
| **显卡** | 支持 OpenGL 3.3+ (用于 MuJoCo 渲染) |

### 推荐配置

- **Python 3.10.11** (项目已在此版本测试)
- **Visual Studio Build Tools 2019+** (用于编译某些 C 扩展)
- **Git** 2.40+ (用于版本控制)
- **Visual Studio Code** 或 **PyCharm** (IDE)

### 可选工具

- **Conda/Miniconda** (如果偏好 conda 环境管理)
- **MATLAB R2020b+** (仅需要对照 MATLAB 版本时)
- **Node.js 18+** (仅需要 Remotion 动画时)

---

## 快速安装（推荐）

### 方案 1：使用现有虚拟环境（最快，1 分钟）

项目已配置好 `.venv-mujoco` 虚拟环境，直接使用：

```powershell
# 1. 进入项目目录
cd D:\Dunna\Documents\hw-1

# 2. 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 3. 验证安装
python -c "import mujoco; print('MuJoCo version:', mujoco.__version__)"

# 4. 运行示例
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

如果步骤 2 报错"禁止运行脚本"，执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 方案 2：全新安装（推荐新用户，5-10 分钟）

```powershell
# 1. 克隆项目（如果尚未克隆）
git clone https://github.com/your-repo/hw-1.git
cd hw-1

# 2. 创建虚拟环境
python -m venv .venv-mujoco

# 3. 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 4. 升级 pip
python -m pip install --upgrade pip setuptools wheel

# 5. 安装项目依赖
pip install -r requirements.txt

# 6. 安装项目为可编辑包（推荐）
pip install -e .

# 7. 验证安装
python -c "import mujoco; print('MuJoCo', mujoco.__version__)"
pytest tests/ -v

# 8. 运行示例
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

---

## 详细安装步骤

### 步骤 1：安装 Python 3.10

#### 选项 A：从官网下载

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.10.11 Windows 安装器
3. 运行安装器，**勾选 "Add Python to PATH"**
4. 选择 "Customize installation"
5. 确保勾选：
   - pip
   - py launcher
   - for all users (optional)
6. 完成安装

#### 选项 B：使用 Chocolatey

```powershell
choco install python --version=3.10.11
```

#### 选项 C：使用 winget

```powershell
winget install Python.Python.3.10
```

验证安装：
```powershell
python --version  # 应显示 Python 3.10.11
pip --version     # 应显示 pip 23.0+
```

### 步骤 2：配置 PowerShell 执行策略

Windows 默认禁止运行未签名的 PowerShell 脚本，需要调整：

```powershell
# 查看当前策略
Get-ExecutionPolicy

# 设置为 RemoteSigned（推荐）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或仅对当前会话临时允许
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### 步骤 3：创建虚拟环境

```powershell
# 进入项目目录
cd D:\Dunna\Documents\hw-1

# 创建虚拟环境
python -m venv .venv-mujoco
```

### 步骤 4：激活虚拟环境

```powershell
# 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 确认激活成功（提示符前应显示 (.venv-mujoco)）
# (.venv-mujoco) PS D:\Dunna\Documents\hw-1>
```

### 步骤 5：升级基础工具

```powershell
# 升级 pip、setuptools、wheel
python -m pip install --upgrade pip setuptools wheel
```

### 步骤 6：安装项目依赖

#### 标准安装（推荐）

包含核心仿真 + 可视化 + 数据分析：

```powershell
pip install -r requirements.txt
```

#### 最小安装

仅核心仿真依赖（适用于服务器/CI 环境）：

```powershell
pip install -r requirements-core.txt
```

#### 完整安装

包含所有功能（优化、UI、开发工具）：

```powershell
pip install -r requirements.txt
pip install -r requirements-opt.txt
pip install -r requirements-ui.txt
pip install -r requirements-dev.txt
```

#### 通过 setup.py 安装

```powershell
# 可编辑安装（开发推荐）
pip install -e .

# 完整安装（包含开发依赖）
pip install -e .[dev]

# 安装所有可选依赖
pip install -e .[all]
```

### 步骤 7：配置环境变量（可选）

```powershell
# 复制环境变量模板
Copy-Item .env.example .env

# 使用编辑器打开并根据本地环境修改
notepad .env
```

关键配置项：
- `HW1_PROJECT_ROOT` - 项目根路径
- `HW1_VENV_MUJOCO` - 虚拟环境路径
- `MUJOCO_GL` - MuJoCo 渲染后端（默认 `egl`）
- `LOG_LEVEL` - 日志级别（开发时 `DEBUG`，生产时 `INFO`）

### 步骤 8：安装 pre-commit hooks（开发者）

```powershell
# 安装 pre-commit
pip install pre-commit

# 安装 git hooks
pre-commit install

# 手动运行检查所有文件
pre-commit run --all-files
```

---

## 安装验证

### 基础验证

```powershell
# 1. 检查 Python 版本
python --version

# 2. 检查虚拟环境激活
where python  # 应指向 .venv-mujoco\Scripts\python.exe

# 3. 验证 MuJoCo 安装
python -c "import mujoco; print('MuJoCo', mujoco.__version__)"

# 4. 验证核心依赖
python -c "import numpy; import matplotlib; import scipy; print('Core dependencies OK')"

# 5. 检查已安装包
pip list
```

### 运行测试套件

```powershell
# 运行所有测试
pytest tests/ -v

# 运行快速测试（跳过慢速测试）
pytest tests/ -v -m "not slow"

# 检查测试覆盖率
pytest tests/ --cov=common --cov-report=html
```

### 运行示例仿真

```powershell
# V13.7 - 推荐的起点版本
python v13_7_refactored\simulate_v13_7.py --duration 5.0

# V10 - 足踝滚动仿生
python v10_rolling_foot_biomimetic_gait\simulate_v10.py --duration 5.0
```

预期输出：
```
MuJoCo 3.3.7+
Simulation started: duration=5.0s
Phase: stance -> swing transitions: 8
Forward distance: 2.31 m
Cost of Transport: 0.068
Simulation completed successfully
Video saved to: out/v13_7_simulation.mp4
```

### 性能基准测试（可选）

```powershell
# 运行性能基准
python benchmarks\benchmark_runner.py --versions v10 v13_7

# 查看结果
cat benchmarks\benchmark_results.json
```

---

## 安装方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **venv (推荐)** | 轻量、快速、项目隔离好 | 不管理 Python 版本 | 日常开发、CI/CD |
| **Conda** | 管理 Python 版本和系统库 | 较重、安装慢 | 跨平台、多环境 |
| **全局安装** | 无需激活环境 | 版本冲突风险高 | **不推荐** |

### 使用 Conda 安装

```powershell
# 1. 创建 conda 环境
conda env create -f environment.yml

# 2. 激活环境
conda activate hw-1

# 3. 验证安装
python -c "import mujoco; print('MuJoCo', mujoco.__version__)"

# 4. 运行示例
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

更新环境：
```powershell
conda env update -f environment.yml --prune
```

删除环境：
```powershell
conda env remove -n hw-1
```

---

## 常见问题排查

### 问题 1：PowerShell 执行策略错误

**症状：**
```
无法加载文件 activate.ps1，因为在此系统上禁止运行脚本
```

**解决方案：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

如果仍然失败，使用管理员权限运行 PowerShell：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

### 问题 2：MuJoCo 导入失败 - DLL 加载错误

**症状：**
```
ImportError: DLL load failed while importing _render: 找不到指定的模块
```

**原因：** 缺少 Visual C++ 运行库

**解决方案：**

1. 安装 Visual C++ Redistributable：
   - 下载：https://aka.ms/vs/17/release/vc_redist.x64.exe
   - 运行安装器
   - 重启计算机

2. 或安装 Visual Studio Build Tools：
   ```powershell
   winget install Microsoft.VisualStudio.2022.BuildTools
   ```

3. 重新安装 MuJoCo：
   ```powershell
   pip uninstall mujoco
   pip install mujoco>=3.3.7
   ```

### 问题 3：Python 版本不匹配

**症状：**
```
ERROR: This package requires Python >=3.9, but you have Python 3.8
```

**解决方案：**

升级到 Python 3.10：
```powershell
# 使用 winget
winget install Python.Python.3.10

# 或使用 Chocolatey
choco install python --version=3.10.11

# 重新创建虚拟环境
Remove-Item -Recurse -Force .venv-mujoco
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 问题 4：pip 安装超时或速度慢

**症状：**
```
ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443)
```

**解决方案 1：** 使用国内镜像（临时）
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**解决方案 2：** 配置永久镜像
```powershell
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

国内常用镜像源：
- 清华大学：https://pypi.tuna.tsinghua.edu.cn/simple
- 阿里云：https://mirrors.aliyun.com/pypi/simple
- 腾讯云：https://mirrors.cloud.tencent.com/pypi/simple

### 问题 5：numpy 版本冲突

**症状：**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**解决方案：**
```powershell
# 卸载所有相关包
pip uninstall numpy scipy matplotlib -y

# 重新安装
pip install -r requirements.txt
```

### 问题 6：测试找不到模块

**症状：**
```
ModuleNotFoundError: No module named 'common'
```

**解决方案 1：** 设置 PYTHONPATH
```powershell
$env:PYTHONPATH = "D:\Dunna\Documents\hw-1"
pytest tests/
```

**解决方案 2：** 安装项目为可编辑包
```powershell
pip install -e .
pytest tests/
```

### 问题 7：虚拟环境损坏

**症状：**
```
python.exe 找不到或无法启动
```

**解决方案：**
```powershell
# 删除损坏的虚拟环境
Remove-Item -Recurse -Force .venv-mujoco

# 重新创建
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 问题 8：中文路径或空格问题

**症状：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\我的文档\\...'
```

**解决方案：**

项目路径应避免中文和空格。如果必须使用，确保在 PowerShell 中正确引用：
```powershell
# 使用引号包裹路径
cd "D:\我的 文档\hw-1"
```

### 问题 9：matplotlib 中文显示乱码

**症状：**
图表中的中文显示为方框 □□□

**解决方案：**

项目已配置 `common/plot_styles.py` 使用 Microsoft YaHei 字体，Windows 默认支持。

如果仍有问题：
```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

### 问题 10：内存不足

**症状：**
```
MemoryError: Unable to allocate array
```

**解决方案：**

1. 减少仿真时长：
   ```powershell
   python simulate_v13_7.py --duration 5.0  # 而不是 60.0
   ```

2. 降低视频分辨率（编辑脚本中的 `camera_resolution`）

3. 关闭其他应用程序释放内存

4. 增加虚拟内存（系统设置）

---

## Windows 11 特定说明

### Windows Terminal 配置

推荐使用 Windows Terminal 而非传统 cmd.exe：

1. 安装 Windows Terminal：
   ```powershell
   winget install Microsoft.WindowsTerminal
   ```

2. 设置默认配置文件为 PowerShell

3. 在项目目录右键选择 "Open in Terminal"

### Windows Defender 排除项

为提升性能，将以下目录添加到 Windows Defender 排除列表：

1. 打开 Windows 安全中心 > 病毒和威胁防护 > 管理设置 > 排除项
2. 添加以下文件夹：
   - `D:\Dunna\Documents\hw-1\.venv-mujoco`
   - `D:\Dunna\Documents\hw-1\.git`
   - `D:\Dunna\Documents\hw-1\__pycache__`

### 长路径支持

如果遇到路径过长错误，启用长路径支持：

```powershell
# 以管理员身份运行
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
                 -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## 下一步

安装完成后，建议阅读：

1. **QUICKSTART.md** - 10 分钟快速入门教程
2. **README.md** - 项目概述和目录结构
3. **VERSIONS.md** - 各版本定位和功能说明
4. **ENVIRONMENT_SETUP.md** - 环境配置详解

开始开发：
```powershell
# 激活环境
.\.venv-mujoco\Scripts\Activate.ps1

# 运行 V13.7（推荐起点）
python v13_7_refactored\simulate_v13_7.py --duration 12.0

# 运行测试
pytest tests/ -v

# 启动交互式 Jupyter
jupyter notebook
```

---

## 获取帮助

如果遇到本文档未涵盖的问题：

1. 查看 **TROUBLESHOOTING.md** - 完整故障排查指南
2. 查看 **DEPENDENCY_MANAGEMENT_GUIDE.md** - 依赖管理详解
3. 查看项目 Issues：https://github.com/your-repo/hw-1/issues
4. 联系项目负责人：
   - 姓名：段泽琪
   - 学号：2024211317
   - 邮箱：2024211317@buct.edu.cn

---

**最后更新：** 2026-06-05  
**适用版本：** hw-1 v1.0.0  
**测试环境：** Windows 11 22H2 + Python 3.10.11

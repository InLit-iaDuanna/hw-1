# hw-1 项目故障排查指南

本文档提供 hw-1 项目常见问题的系统化排查方案，涵盖环境配置、依赖管理、仿真运行、性能优化等方面。

---

## 目录

- [快速诊断](#快速诊断)
- [环境问题](#环境问题)
- [依赖问题](#依赖问题)
- [仿真运行问题](#仿真运行问题)
- [性能问题](#性能问题)
- [Windows 特定问题](#windows-特定问题)
- [开发工具问题](#开发工具问题)
- [高级排查](#高级排查)

---

## 快速诊断

运行诊断脚本快速检测环境问题：

```powershell
# 检查 Python 和虚拟环境
python --version
where python

# 检查关键依赖
python -c "import sys; print('Python:', sys.version)"
python -c "import mujoco; print('MuJoCo:', mujoco.__version__)"
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)"

# 检查 PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"

# 列出已安装包
pip list --format=freeze | Select-String -Pattern "mujoco|numpy|matplotlib|scipy"
```

---

## 环境问题

### 问题 1：虚拟环境未激活

**症状：**
- `pip install` 安装到全局 Python
- `import` 找不到已安装的包
- `where python` 指向非虚拟环境路径

**诊断：**
```powershell
where python
# 正确：D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe
# 错误：C:\Users\...\AppData\Local\Programs\Python\Python310\python.exe
```

**解决方案：**
```powershell
# 激活虚拟环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\Activate.ps1

# 确认激活成功（提示符应显示 (.venv-mujoco)）
where python
```

### 问题 2：PowerShell 执行策略限制

**症状：**
```
无法加载文件 activate.ps1，因为在此系统上禁止运行脚本
```

**解决方案 1：** 仅当前用户
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**解决方案 2：** 仅当前会话
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

**解决方案 3：** 使用 cmd 激活
```cmd
.venv-mujoco\Scripts\activate.bat
```

**解决方案 4：** 使用绝对路径调用 Python
```powershell
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe your_script.py
```

### 问题 3：虚拟环境损坏

**症状：**
- `python.exe` 找不到或无法启动
- 激活脚本报错
- `pip list` 返回空或报错

**诊断：**
```powershell
Test-Path .venv-mujoco\Scripts\python.exe
Test-Path .venv-mujoco\Scripts\pip.exe
```

**解决方案：**
```powershell
# 1. 备份当前包列表（如果可以运行）
.\.venv-mujoco\Scripts\pip.exe freeze > requirements-backup.txt

# 2. 删除损坏的虚拟环境
Remove-Item -Recurse -Force .venv-mujoco

# 3. 重新创建虚拟环境
python -m venv .venv-mujoco

# 4. 激活并安装依赖
.\.venv-mujoco\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 问题 4：Python 版本不匹配

**症状：**
```
ERROR: This package requires Python >=3.9, but you have Python 3.8
```

**诊断：**
```powershell
python --version
```

**解决方案：**

升级 Python（方法 1 - winget）：
```powershell
winget install Python.Python.3.10
```

升级 Python（方法 2 - Chocolatey）：
```powershell
choco install python --version=3.10.11
```

升级 Python（方法 3 - 手动下载）：
- 访问 https://www.python.org/downloads/
- 下载 Python 3.10.11 安装器
- 勾选 "Add Python to PATH"

重新创建虚拟环境：
```powershell
Remove-Item -Recurse -Force .venv-mujoco
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 依赖问题

### 问题 5：MuJoCo 导入失败 - DLL 错误

**症状：**
```
ImportError: DLL load failed while importing _render: 找不到指定的模块
```

**原因：** 缺少 Visual C++ 运行库或 OpenGL 支持

**解决方案 1：** 安装 Visual C++ Redistributable
```powershell
# 下载并安装
# https://aka.ms/vs/17/release/vc_redist.x64.exe

# 或使用 winget
winget install Microsoft.VCRedist.2015+.x64
```

**解决方案 2：** 安装 Visual Studio Build Tools
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

**解决方案 3：** 重新安装 MuJoCo
```powershell
pip uninstall mujoco -y
pip cache purge
pip install mujoco>=3.3.7
```

**解决方案 4：** 检查 OpenGL 支持
```powershell
# 更新显卡驱动
# NVIDIA: https://www.nvidia.com/Download/index.aspx
# AMD: https://www.amd.com/en/support
# Intel: https://www.intel.com/content/www/us/en/download-center/home.html
```

### 问题 6：numpy 版本冲突

**症状：**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
ImportError: numpy.core.multiarray failed to import
```

**诊断：**
```powershell
pip list | Select-String numpy
python -c "import numpy; print(numpy.__version__)"
```

**解决方案：**
```powershell
# 卸载所有相关包
pip uninstall numpy scipy matplotlib pandas -y

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

### 问题 7：依赖安装超时

**症状：**
```
ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443)
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None))
```

**解决方案 1：** 使用国内镜像（临时）
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**解决方案 2：** 配置永久镜像
```powershell
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
```

**解决方案 3：** 增加超时时间
```powershell
pip install -r requirements.txt --timeout=300
```

**国内常用镜像源：**
- 清华大学：https://pypi.tuna.tsinghua.edu.cn/simple
- 阿里云：https://mirrors.aliyun.com/pypi/simple
- 腾讯云：https://mirrors.cloud.tencent.com/pypi/simple
- 中国科技大学：https://pypi.mirrors.ustc.edu.cn/simple

### 问题 8：包安装后仍找不到模块

**症状：**
```
ModuleNotFoundError: No module named 'common'
```

**诊断：**
```powershell
# 检查包是否安装
pip list | Select-String common

# 检查 Python 搜索路径
python -c "import sys; print('\n'.join(sys.path))"

# 检查是否在正确的虚拟环境
where python
```

**解决方案 1：** 设置 PYTHONPATH
```powershell
$env:PYTHONPATH = "D:\Dunna\Documents\hw-1"
python your_script.py
```

**解决方案 2：** 安装项目为可编辑包
```powershell
pip install -e .
```

**解决方案 3：** 在脚本中添加路径
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 现在可以导入 common
from common import energy_metrics
```

---

## 仿真运行问题

### 问题 9：仿真启动失败

**症状：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'common/models/compass_gait.xml'
```

**诊断：**
```powershell
# 检查当前工作目录
Get-Location

# 检查模型文件是否存在
Test-Path common\models\compass_gait.xml
```

**解决方案：**
```powershell
# 确保从项目根目录运行
cd D:\Dunna\Documents\hw-1
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

### 问题 10：仿真立即崩溃或不稳定

**症状：**
- 仿真 < 1 秒就结束
- 模型倒地或飞出场景
- `nan` 或 `inf` 出现在数据中

**诊断：**
```python
# 检查数据中的 nan/inf
import numpy as np
print("NaN in data:", np.isnan(data).any())
print("Inf in data:", np.isinf(data).any())
```

**可能原因和解决方案：**

1. **数值不稳定：** 时间步长过大
   ```python
   # 减小时间步长（在脚本或 XML 中）
   model.opt.timestep = 0.0005  # 从 0.001 减至 0.0005
   ```

2. **物理参数不合理：** 质量/惯量/刚度异常
   ```python
   # 检查模型参数
   print("Body masses:", model.body_mass)
   print("Joint stiffness:", model.jnt_stiffness)
   ```

3. **初始状态不稳定：** 从非稳定点开始
   ```python
   # 使用已知的稳定初始状态
   data.qpos[:] = stable_initial_qpos
   data.qvel[:] = stable_initial_qvel
   ```

4. **接触检测问题：** 地面接触失效
   ```xml
   <!-- 在 XML 中调整接触参数 -->
   <option integrator="RK4" timestep="0.001">
     <flag contact="enable" energy="enable"/>
   </option>
   ```

### 问题 11：视频渲染失败

**症状：**
```
RuntimeError: Failed to initialize GLFW
OSError: cannot write mode RGBA as JPEG
```

**解决方案 1：** GLFW 初始化失败
```powershell
# 安装 GLFW
pip install glfw

# 设置 MuJoCo 渲染后端
$env:MUJOCO_GL = "glfw"
python your_script.py
```

**解决方案 2：** 图像格式错误
```python
# 使用 PNG 而不是 JPEG（支持 RGBA）
imageio.imwrite("output.png", image)

# 或转换为 RGB 保存为 JPEG
import numpy as np
image_rgb = image[:, :, :3]  # 去掉 alpha 通道
imageio.imwrite("output.jpg", image_rgb)
```

**解决方案 3：** ffmpeg 缺失
```powershell
# 安装 imageio-ffmpeg
pip install imageio-ffmpeg

# 或手动安装 ffmpeg
winget install Gyan.FFmpeg
```

### 问题 12：仿真速度慢

**症状：**
- 仿真 1 秒实时时间需要 > 10 秒
- CPU 占用率 100%

**诊断：**
```python
import time
start = time.time()
for _ in range(1000):
    mujoco.mj_step(model, data)
elapsed = time.time() - start
print(f"1000 steps: {elapsed:.3f}s, {1000/elapsed:.1f} steps/s")
```

**优化方案：**

1. **禁用不必要的渲染：**
   ```python
   # 仅保存最终状态，不逐帧渲染
   render_interval = 100  # 每 100 步渲染一次
   ```

2. **使用更大的时间步长：**
   ```python
   model.opt.timestep = 0.002  # 从 0.001 增至 0.002
   ```

3. **简化模型：**
   - 减少接触点数量
   - 使用简化的碰撞几何体
   - 减少自由度

4. **使用编译优化的 NumPy：**
   ```powershell
   pip uninstall numpy
   pip install numpy --no-binary numpy  # 从源码编译（慢但性能好）
   # 或使用 conda 的优化版本
   conda install numpy
   ```

---

## 性能问题

### 问题 13：内存占用过高

**症状：**
```
MemoryError: Unable to allocate array
系统内存占用 > 90%
```

**诊断：**
```python
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024**2:.1f} MB")

# 检查数组大小
import numpy as np
print(f"Array size: {data.qpos.nbytes / 1024**2:.1f} MB")
```

**优化方案：**

1. **减少仿真时长：**
   ```powershell
   python simulate_v13_7.py --duration 5.0  # 而不是 60.0
   ```

2. **降低采样率：**
   ```python
   # 不保存每一帧
   save_interval = 10  # 每 10 帧保存一次
   ```

3. **使用更小的数据类型：**
   ```python
   # 使用 float32 而不是 float64
   data_array = np.array(trajectory, dtype=np.float32)
   ```

4. **流式处理：**
   ```python
   # 逐批保存，不在内存中累积
   with h5py.File("output.h5", "w") as f:
       for i, frame in enumerate(simulation):
           f[f"frame_{i}"] = frame
   ```

5. **关闭其他应用程序：**
   ```powershell
   # 查看内存占用
   Get-Process | Sort-Object -Property WS -Descending | Select-Object -First 10
   ```

### 问题 14：磁盘空间不足

**症状：**
```
OSError: [Errno 28] No space left on device
```

**诊断：**
```powershell
# 检查磁盘空间
Get-PSDrive -PSProvider FileSystem

# 查找大文件
Get-ChildItem D:\Dunna\Documents\hw-1 -Recurse -File | 
    Sort-Object Length -Descending | 
    Select-Object -First 20 FullName, @{N='Size(MB)';E={[math]::Round($_.Length/1MB,2)}}
```

**解决方案：**

1. **清理临时文件：**
   ```powershell
   .\cleanup_temp.ps1
   ```

2. **压缩大数据文件：**
   ```powershell
   .\compress_large_data.ps1
   ```

3. **移除旧视频：**
   ```powershell
   Get-ChildItem -Path .\v*\out -Filter *.mp4 -Recurse | 
       Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
       Remove-Item -Confirm
   ```

4. **使用视频压缩：**
   ```python
   # 降低视频比特率和分辨率
   imageio.mimwrite(
       "output.mp4", 
       frames, 
       fps=30, 
       quality=7,  # 从 10 降至 7
       macro_block_size=16
   )
   ```

---

## Windows 特定问题

### 问题 15：路径过长

**症状：**
```
FileNotFoundError: [WinError 206] 文件名或扩展名太长
```

**解决方案 1：** 启用长路径支持
```powershell
# 以管理员身份运行
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
                 -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# 重启计算机
```

**解决方案 2：** 使用更短的路径
```powershell
# 将项目移至更短路径
Move-Item D:\Dunna\Documents\hw-1 D:\hw-1
```

### 问题 16：中文路径问题

**症状：**
```
UnicodeDecodeError: 'gbk' codec can't decode byte
FileNotFoundError: [Errno 2] No such file or directory
```

**解决方案 1：** 设置环境变量
```powershell
$env:PYTHONIOENCODING = "utf-8"
python your_script.py
```

**解决方案 2：** 在脚本中指定编码
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取文件时指定编码
with open("文件.txt", "r", encoding="utf-8") as f:
    content = f.read()
```

**解决方案 3：** 避免使用中文路径
```powershell
# 使用英文路径
D:\Dunna\Documents\hw-1  # 而不是 D:\段\文档\hw-1
```

### 问题 17：Windows Defender 减慢速度

**症状：**
- `pip install` 异常缓慢
- 文件 I/O 操作缓慢
- CPU 占用波动

**解决方案：** 添加排除项

1. 打开 Windows 安全中心
2. 病毒和威胁防护 > 管理设置 > 排除项
3. 添加文件夹：
   - `D:\Dunna\Documents\hw-1\.venv-mujoco`
   - `D:\Dunna\Documents\hw-1\.git`
   - `D:\Dunna\Documents\hw-1\__pycache__`
   - `%LocalAppData%\pip\cache`

### 问题 18：防火墙阻止网络访问

**症状：**
```
ProxyError: Cannot connect to proxy
SSL: CERTIFICATE_VERIFY_FAILED
```

**解决方案 1：** 临时禁用 SSL 验证（不推荐）
```powershell
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org package_name
```

**解决方案 2：** 配置代理
```powershell
$env:HTTP_PROXY = "http://proxy.example.com:8080"
$env:HTTPS_PROXY = "http://proxy.example.com:8080"
pip install package_name
```

**解决方案 3：** 更新证书
```powershell
pip install --upgrade certifi
```

---

## 开发工具问题

### 问题 19：VS Code 无法识别虚拟环境

**症状：**
- 自动补全不工作
- Import 显示错误但代码可以运行
- 调试器找不到模块

**解决方案：**

1. 选择正确的 Python 解释器：
   - 按 `Ctrl+Shift+P`
   - 输入 "Python: Select Interpreter"
   - 选择 `.venv-mujoco\Scripts\python.exe`

2. 手动配置 `.vscode/settings.json`：
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}\\.venv-mujoco\\Scripts\\python.exe"
   }
   ```

3. 重新加载窗口：
   - `Ctrl+Shift+P` > "Developer: Reload Window"

### 问题 20：Pytest 找不到测试

**症状：**
```
collected 0 items
```

**诊断：**
```powershell
pytest --collect-only
```

**解决方案：**

1. 检查工作目录：
   ```powershell
   cd D:\Dunna\Documents\hw-1
   pytest tests/
   ```

2. 配置 `pytest.ini`（已存在）：
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   ```

3. 确保 `__init__.py` 存在：
   ```powershell
   New-Item tests\__init__.py -ItemType File -Force
   ```

### 问题 21：Git 操作缓慢

**症状：**
- `git status` 需要 > 10 秒
- `git add` 卡住

**解决方案：**

1. 启用 Git 文件系统监控：
   ```powershell
   git config core.fsmonitor true
   git config core.untrackedcache true
   ```

2. 排除大型目录（已在 `.gitignore`）：
   ```
   .venv-mujoco/
   .venv-codex/
   __pycache__/
   *.pyc
   ```

3. 减少 Git 垃圾回收频率：
   ```powershell
   git config gc.auto 0
   ```

4. 压缩 Git 仓库：
   ```powershell
   git gc --aggressive --prune=now
   ```

---

## 高级排查

### 问题 22：神秘的导入错误

**症状：**
- 包已安装但导入失败
- 不同终端表现不一致
- IDE 中正常，命令行失败

**系统排查流程：**

```powershell
# 1. 确认 Python 路径
where python
Get-Command python | Select-Object -ExpandProperty Source

# 2. 确认虚拟环境
$env:VIRTUAL_ENV

# 3. 检查 sys.path
python -c "import sys; import pprint; pprint.pprint(sys.path)"

# 4. 检查包安装位置
pip show mujoco

# 5. 尝试导入并查看详细错误
python -c "import mujoco" -v

# 6. 检查环境变量
Get-ChildItem Env: | Where-Object { $_.Name -match "PYTHON|PATH" }
```

### 问题 23：依赖版本锁定

**需求：** 锁定当前工作的依赖版本

**生成精确版本列表：**
```powershell
pip freeze > requirements-freeze.txt
```

**从锁定版本恢复：**
```powershell
pip install -r requirements-freeze.txt
```

**生成跨平台兼容的锁文件：**
```powershell
pip install pip-tools
pip-compile requirements.txt -o requirements.lock
pip-sync requirements.lock
```

### 问题 24：清理所有环境重新开始

**完全清理流程：**

```powershell
# 1. 退出虚拟环境
deactivate

# 2. 备份当前配置
Copy-Item .env .env.backup
pip freeze > requirements-old.txt

# 3. 删除虚拟环境
Remove-Item -Recurse -Force .venv-mujoco

# 4. 清理 Python 缓存
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Filter "*.pyc" -Recurse -File | Remove-Item -Force

# 5. 清理 pip 缓存
pip cache purge

# 6. 重新创建环境
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 7. 验证安装
pytest tests/ -v
python v13_7_refactored\simulate_v13_7.py --duration 5.0
```

---

## 获取帮助

如果以上方案都无法解决问题：

### 收集诊断信息

```powershell
# 创建诊断报告
$report = @"
=== 系统信息 ===
OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)
OS Version: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Version)

=== Python 环境 ===
Python Version: $(python --version)
Python Path: $(where python)
Virtual Env: $env:VIRTUAL_ENV

=== 已安装包 ===
$(pip list)

=== 环境变量 ===
PYTHONPATH: $env:PYTHONPATH
MUJOCO_GL: $env:MUJOCO_GL

=== 磁盘空间 ===
$(Get-PSDrive -PSProvider FileSystem | Format-Table -AutoSize)
"@

$report | Out-File diagnostic_report.txt -Encoding UTF8
Write-Host "诊断报告已保存到 diagnostic_report.txt"
```

### 联系支持

- **项目负责人：** 段泽琪
- **学号：** 2024211317
- **邮箱：** 2024211317@buct.edu.cn
- **项目仓库：** https://github.com/your-repo/hw-1/issues

提交 Issue 时请附上：
1. 问题描述和复现步骤
2. 完整错误信息
3. `diagnostic_report.txt`
4. 尝试过的解决方案

---

**最后更新：** 2026-06-05  
**适用版本：** hw-1 v1.0.0  
**测试环境：** Windows 11 22H2 + Python 3.10.11

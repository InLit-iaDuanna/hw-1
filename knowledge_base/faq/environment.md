# FAQ：环境配置问题

## Python 环境

### Q1: 如何正确使用项目的 Python 环境？

**hw-1 项目使用固定的虚拟环境**：

```powershell
# 工作目录
cd D:\Dunna\Documents\hw-1

# 直接使用现有 venv（不要重建）
.\.venv-mujoco\Scripts\python.exe <script>.py

# 或激活环境
.\.venv-mujoco\Scripts\Activate.ps1
python <script>.py
```

**重要约定**：
- ✅ **使用现有 `.venv-mujoco/`**：已配置好的 Python 3.10 环境
- ❌ **不要轻易重建 venv**：会导致依赖重新安装，可能版本不一致
- ❌ **不要用系统 Python**：会缺少 MuJoCo 等依赖

### Q2: 依赖安装失败怎么办？

**常见问题：pip 超时**

```powershell
# ✗ 这些源会超时
pip install mujoco  # 直连 pypi.org 超时
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple mujoco  # tuna 镜像也超时

# ✓ 使用阿里云镜像（2026-05 验证可用）
pip install -i https://mirrors.aliyun.com/pypi/simple/ mujoco
```

**完整依赖安装**：

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

**验证安装**：

```powershell
.\.venv-mujoco\Scripts\python.exe -c "import mujoco; print(mujoco.__version__)"
.\.venv-mujoco\Scripts\python.exe -c "import numpy; print(numpy.__version__)"
```

### Q3: 如何重建虚拟环境（如果必须）？

**⚠ 重建前必读**：

1. **先关闭 PyCharm**：否则进程锁定导致删除失败
2. **杀掉残留 Python 进程**：
   ```powershell
   Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*\.venv-mujoco\*" } | Stop-Process -Force
   ```

**重建流程**：

```powershell
cd D:\Dunna\Documents\hw-1

# 1. 删除旧环境
Remove-Item -Recurse -Force .venv-mujoco

# 2. 创建新环境（Python 3.10）
python -m venv .venv-mujoco

# 3. 升级 pip
.\.venv-mujoco\Scripts\python.exe -m pip install --upgrade pip

# 4. 安装依赖（使用阿里云镜像）
.\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 5. 验证
.\.venv-mujoco\Scripts\python.exe -c "import mujoco; print('MuJoCo OK')"
```

### Q4: MuJoCo 版本问题

**项目使用的 MuJoCo 版本**：

```python
# 查看当前版本
import mujoco
print(mujoco.__version__)  # 应该是 2.3.x 或 3.x
```

**常见问题**：

1. **MuJoCo 2.x vs 3.x API 变化**
   ```python
   # MuJoCo 2.x
   import mujoco_py
   
   # MuJoCo 3.x（项目使用）
   import mujoco
   ```

2. **viewer API 变化**
   ```python
   # MuJoCo 2.3
   import mujoco
   import mujoco.viewer
   
   with mujoco.viewer.launch_passive(model, data) as viewer:
       # ...
   ```

3. **XML 兼容性**
   - V10+ 使用 MuJoCo 3.x 格式
   - 旧版本可能需要 `mjcf` 命名空间

### Q5: 如何在 PyCharm 中配置项目？

**配置解释器**：

1. 打开 PyCharm
2. File → Settings → Project: hw-1 → Python Interpreter
3. 点击齿轮图标 → Add
4. 选择 "Existing environment"
5. 路径：`D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe`
6. 确定

**配置运行脚本**：

1. 右键点击 `v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py`
2. 选择 "Modify Run Configuration"
3. Working directory: `D:\Dunna\Documents\hw-1`
4. Python interpreter: `.venv-mujoco`
5. 应用

**避坑点**：
- ✅ Working directory 必须是项目根目录
- ✅ 使用项目专用的 `.venv-mujoco`
- ❌ 不要用 PyCharm 自动创建的 venv

## 依赖管理

### Q6: requirements.txt 包含哪些依赖？

**核心依赖**（参考 V17）：

```txt
# 物理仿真
mujoco>=3.0.0

# 数值计算
numpy>=1.24.0
scipy>=1.10.0

# 可视化
matplotlib>=3.7.0
seaborn>=0.12.0

# 数据处理
pandas>=2.0.0

# 类型检查
typing-extensions>=4.5.0

# 开发工具
pytest>=7.3.0
ruff>=0.0.270
mypy>=1.3.0
```

**验证依赖完整性**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip check
```

### Q7: 如何添加新依赖？

**流程**：

1. **安装依赖**
   ```powershell
   .\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ <package>
   ```

2. **更新 requirements.txt**
   ```powershell
   .\.venv-mujoco\Scripts\python.exe -m pip freeze | Select-String "<package>" >> requirements.txt
   ```

3. **验证**
   ```powershell
   # 在新环境中测试
   .\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
   ```

4. **提交变更**
   ```powershell
   git add requirements.txt
   git commit -m "Add <package> dependency for <feature>"
   ```

### Q8: 如何处理依赖冲突？

**诊断冲突**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip check
```

**常见冲突**：

1. **numpy 版本冲突**
   ```
   mujoco 3.0.0 requires numpy>=1.24.0
   scipy 1.9.0 requires numpy<1.24.0
   ```
   
   **解决方案**：升级 scipy
   ```powershell
   pip install --upgrade scipy
   ```

2. **protobuf 版本冲突**（如果使用 TensorFlow）
   ```powershell
   pip install protobuf==3.20.3
   ```

**强制重新安装**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip install --force-reinstall -i https://mirrors.aliyun.com/pypi/simple/ <package>
```

## PowerShell 相关

### Q9: PowerShell 常见问题

**1. 执行策略限制**

```powershell
# 错误：无法加载文件 Activate.ps1，因为在此系统上禁止运行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**2. 路径包含空格**

```powershell
# ✓ 使用引号
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" script.py

# ✗ 不带引号会报错
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe script.py
```

**3. 环境变量设置**

```powershell
# 临时设置（当前会话）
$env:MUJOCO_GL = "egl"

# 永久设置（用户级别）
[System.Environment]::SetEnvironmentVariable("MUJOCO_GL", "egl", "User")
```

**4. PowerShell vs Bash 语法差异**

| 操作 | Bash | PowerShell |
|------|------|-----------|
| 空设备 | `/dev/null` | `$null` |
| 环境变量 | `$VAR` | `$env:VAR` |
| 行续接 | `\` | `` ` `` (backtick) |
| 管道过滤 | `grep` | `Select-String` |
| 列出文件 | `ls -la` | `Get-ChildItem` |

### Q10: 如何配置 MuJoCo 渲染后端？

**Windows 推荐配置**：

```powershell
# 默认使用 GLFW（桌面渲染）
$env:MUJOCO_GL = "glfw"

# 如果需要无头渲染（服务器/批量任务）
$env:MUJOCO_GL = "egl"  # 需要 EGL 支持
# 或
$env:MUJOCO_GL = "osmesa"  # 软件渲染（慢但兼容性好）
```

**验证渲染后端**：

```python
import mujoco
print(f"MuJoCo GL backend: {mujoco.GLContext.default_backend()}")
```

**常见错误**：

```
GLFW initialization failed
```

**解决方案**：
1. 更新显卡驱动
2. 或改用 osmesa：`$env:MUJOCO_GL = "osmesa"`

## 常见错误

### Q11: ImportError: DLL load failed

**错误信息**：

```
ImportError: DLL load failed while importing _mujoco: 找不到指定的模块。
```

**原因**：缺少 Visual C++ Redistributable

**解决方案**：

1. 下载安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 重启 PowerShell
3. 重新测试导入

### Q12: ModuleNotFoundError: No module named 'common'

**错误信息**：

```python
ModuleNotFoundError: No module named 'common'
```

**原因**：工作目录不正确

**解决方案**：

```powershell
# 确保在项目根目录运行
cd D:\Dunna\Documents\hw-1

# 运行脚本
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py
```

**或在脚本中添加路径**：

```python
import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 现在可以导入 common
from common.energy_metrics import calculate_cot
```

### Q13: numpy._core.multiarray failed to import

**错误信息**：

```
ImportError: numpy._core.multiarray failed to import
```

**原因**：numpy 版本不兼容

**解决方案**：

```powershell
# 重新安装 numpy
.\.venv-mujoco\Scripts\python.exe -m pip uninstall numpy
.\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ numpy>=1.24.0
```

### Q14: 如何在 Git Bash 中运行脚本？

**⚠ 项目使用 PowerShell，不是 Bash**

但如果必须用 Git Bash：

```bash
# 使用绝对路径
/d/Dunna/Documents/hw-1/.venv-mujoco/Scripts/python.exe script.py

# 或切换到 PowerShell
powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe script.py
```

**建议**：
- 项目所有文档和脚本基于 PowerShell
- 使用 Windows Terminal + PowerShell
- 不要混用 Bash 和 PowerShell 语法

### Q15: 如何处理 "python.exe 已停止工作" 崩溃？

**诊断步骤**：

1. **检查是否是仿真参数问题**
   ```python
   # 降低仿真复杂度
   model.opt.timestep = 0.002  # 提高时间步长
   model.opt.iterations = 30   # 降低求解器迭代次数
   ```

2. **检查是否是内存问题**
   ```python
   # 减少数据记录
   if step % 10 == 0:  # 每 10 步记录一次
       trajectory.append(data.qpos.copy())
   ```

3. **运行最小复现案例**
   ```python
   import mujoco
   
   xml = """
   <mujoco>
     <worldbody>
       <body pos="0 0 1">
         <geom type="sphere" size="0.1"/>
       </body>
     </worldbody>
   </mujoco>
   """
   
   model = mujoco.MjModel.from_xml_string(xml)
   data = mujoco.MjData(model)
   
   for _ in range(1000):
       mujoco.mj_step(model, data)
   
   print("Basic test passed")
   ```

4. **如果最小案例也崩溃**：
   - 重新安装 MuJoCo
   - 更新显卡驱动
   - 检查系统 DLL 完整性：`sfc /scannow`（管理员权限）

---

**相关资源**：
- [常见错误](../troubleshooting/common_errors.md)
- [代码规范](../best_practices/coding_standards.md)
- [项目 CLAUDE.md](../../CLAUDE.md)

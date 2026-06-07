# 常见错误及解决方案

本文档收录 hw-1 项目中常见的错误信息及对应的解决方案。

---

## Python 环境错误

### ModuleNotFoundError: No module named 'mujoco'

**错误信息**：
```
ModuleNotFoundError: No module named 'mujoco'
```

**原因**：未安装 MuJoCo 或使用了错误的 Python 环境。

**解决方案**：

```powershell
# 1. 确认使用项目的 Python 环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -c "import sys; print(sys.executable)"

# 2. 安装 MuJoCo（使用阿里云镜像）
.\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ mujoco

# 3. 验证安装
.\.venv-mujoco\Scripts\python.exe -c "import mujoco; print(mujoco.__version__)"
```

**参考**：[FAQ: 环境配置问题 - Q2](../faq/environment.md#q2-依赖安装失败怎么办)

---

### ModuleNotFoundError: No module named 'common'

**错误信息**：
```
ModuleNotFoundError: No module named 'common'
```

**原因**：工作目录不正确，Python 无法找到 `common/` 模块。

**解决方案**：

```powershell
# 确保在项目根目录运行
cd D:\Dunna\Documents\hw-1

# 不要在版本子目录中运行
# ✗ cd v10_rolling_foot_biomimetic_gait  # 错误
# ✓ cd D:\Dunna\Documents\hw-1           # 正确

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

**参考**：[FAQ: 环境配置问题 - Q12](../faq/environment.md#q12-modulenotfounderror-no-module-named-common)

---

### ImportError: DLL load failed

**错误信息**：
```
ImportError: DLL load failed while importing _mujoco: 找不到指定的模块。
```

**原因**：缺少 Visual C++ Redistributable。

**解决方案**：

1. 下载并安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 重启 PowerShell
3. 重新测试

```powershell
.\.venv-mujoco\Scripts\python.exe -c "import mujoco; print('OK')"
```

**参考**：[FAQ: 环境配置问题 - Q11](../faq/environment.md#q11-importerror-dll-load-failed)

---

### numpy._core.multiarray failed to import

**错误信息**：
```
ImportError: numpy._core.multiarray failed to import
```

**原因**：numpy 版本不兼容。

**解决方案**：

```powershell
# 重新安装 numpy
.\.venv-mujoco\Scripts\python.exe -m pip uninstall numpy
.\.venv-mujoco\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ "numpy>=1.24.0"

# 验证
.\.venv-mujoco\Scripts\python.exe -c "import numpy; print(numpy.__version__)"
```

**参考**：[FAQ: 环境配置问题 - Q13](../faq/environment.md#q13-numpy_coremultiarray-failed-to-import)

---

## MuJoCo 仿真错误

### Simulation returns NaN

**错误信息**：
```
WARNING: qpos contains NaN at step 234
```

**常见原因**：

1. **接触参数不合理**
2. **初始状态不稳定**
3. **时间步长过大**
4. **控制力矩饱和**

**诊断流程**：

```python
import numpy as np

# 检查何时出现 NaN
for step in range(n_steps):
    mujoco.mj_step(model, data)
    
    if np.any(np.isnan(data.qpos)):
        print(f"NaN at step {step}, time {data.time:.3f}s")
        print(f"Last valid qpos: {qpos_history[-1]}")
        print(f"Last ctrl: {data.ctrl}")
        break
    
    qpos_history.append(data.qpos.copy())
```

**解决方案**：

1. **使用 V10 稳定接触参数**
   ```xml
   <geom solimp="0 0.95 0.001" solref="0.005 1" friction="1.0 0.005 0.0001"/>
   ```

2. **从稳定初始状态启动**
   ```python
   data.qpos[1] = 0.95  # hip_y 略高于腿长
   data.qvel[:] = 0.0   # 清零速度
   ```

3. **降低时间步长**
   ```python
   model.opt.timestep = 0.001  # 1 ms
   ```

**参考**：[FAQ: 仿真相关问题 - Q1](../faq/simulation.md#q1-为什么仿真出现-nan)

---

### GLFW initialization failed

**错误信息**：
```
ERROR: GLFW initialization failed
```

**原因**：显卡驱动问题或不支持 GLFW。

**解决方案**：

```powershell
# 方案 1：更新显卡驱动
# 访问 NVIDIA/AMD 官网下载最新驱动

# 方案 2：改用 osmesa 软件渲染
$env:MUJOCO_GL = "osmesa"
.\.venv-mujoco\Scripts\python.exe script.py
```

**验证后端**：

```python
import mujoco
print(f"GL backend: {mujoco.GLContext.default_backend()}")
```

**参考**：[FAQ: 环境配置问题 - Q10](../faq/environment.md#q10-如何配置-mujoco-渲染后端)

---

### Contact penetration too deep

**错误信息**：
```
WARNING: Contact penetration -0.05m exceeds threshold
```

**原因**：接触刚度过低或初始状态导致深度穿透。

**解决方案**：

1. **调整 solimp 参数**
   ```xml
   <!-- 提高接触刚度 -->
   <geom solimp="0 0.98 0.001"/>  <!-- 从 0.95 提高到 0.98 -->
   ```

2. **检查初始高度**
   ```python
   # 确保机器人初始位置不在地面以下
   data.qpos[1] = 1.0  # hip_y
   mujoco.mj_forward(model, data)
   print(f"Lowest geom height: {min_geom_height}")
   ```

3. **降低时间步长**（临时缓解）
   ```python
   model.opt.timestep = 0.0005  # 0.5 ms
   ```

---

### Robot immediately falls

**现象**：仿真启动后机器人立即跌倒。

**诊断检查表**：

```python
# 1. 检查初始姿态
print(f"Hip height: {data.qpos[1]:.3f}m")  # 应该 > 0.8
print(f"Hip angle: {data.qpos[2]:.3f}rad") # 应该接近 0

# 2. 检查接触
print(f"Number of contacts: {data.ncon}")  # 应该 >= 1

# 3. 检查控制信号
print(f"Control: {data.ctrl}")  # 不应该全为 0 或极大值

# 4. 检查质量
print(f"Total mass: {np.sum(model.body_mass)}kg")  # 合理范围 50-70 kg
```

**常见原因及解决**：

| 原因 | 检查 | 解决方案 |
|-----|------|---------|
| 初始高度过低 | qpos[1] < 0.8 | 提高到 0.95 |
| 初始速度过大 | qvel[0] > 1.0 | 设为 0 或小推动 0.5 |
| 控制器未启动 | ctrl 全为 0 | 检查控制器初始化 |
| 参数不匹配 | 使用错误参数 | 使用 V10 baseline |
| 模型有误 | 质量/长度异常 | 对比 V10 模型文件 |

**参考**：[FAQ: 调试问题 - Q1](../faq/debugging.md#q1-仿真跌倒了怎么办)

---

## 参数相关错误

### Grid search all failed

**现象**：参数扫描所有格子都失败。

**诊断步骤**：

1. **验证 baseline 配置**
   ```python
   # 先测试已知稳定的 V10 baseline
   config = SimulationConfig(
       foot_length=0.04,
       leg_length=1.0,
       kp_hip=40.0,
       kd_hip=3.0,
   )
   result = run_simulation(config)
   assert result['success'], "Baseline should work"
   ```

2. **检查参数范围**
   ```python
   # 参数范围是否覆盖已知稳定点？
   param_grid = {
       'foot_length': np.linspace(0.038, 0.043, 6),  # V13: 0.040 稳定
       'leg_length': np.linspace(0.98, 1.03, 6),     # V13: 1.00 稳定
   }
   ```

3. **检查模型文件**
   ```python
   # 是否使用了正确的模型？
   model_path = Path(__file__).parent / "model_v10.xml"
   assert model_path.exists()
   ```

**常见原因**：

- ❌ 使用了错误版本的模型文件
- ❌ 参数范围完全偏离稳定域
- ❌ 控制器初始化有误
- ❌ 仿真时长过短（< 5s 无法判断稳定）

**参考**：[FAQ: 参数设置问题 - Q10](../faq/parameters.md#q10-参数扫描网格如何设计)

---

### FSM phase stuck

**现象**：FSM 停在某个相位不切换。

**诊断**：

```python
# 记录相位停留时间
if fsm.phase_elapsed_time > 1.0:  # 超过 1 秒
    print(f"⚠ Phase {fsm.current_phase} stuck for {fsm.phase_elapsed_time:.2f}s")
    print(f"  Trigger signals:")
    print(f"    Contact left: {data.contact_left}")
    print(f"    Contact right: {data.contact_right}")
    print(f"    Hip angle: {data.qpos[hip_idx]:.3f}")
```

**常见原因**：

1. **事件触发条件未满足**
   - 检查接触力阈值
   - 检查角度阈值

2. **传感器信号异常**
   - 接触检测失败
   - 角度读数错误

3. **FSM 逻辑错误**
   - 退出条件设置不当
   - 多个条件冲突

**解决方案**：

```python
# 添加超时保护
if fsm.phase_elapsed_time > MAX_PHASE_DURATION:
    print(f"Phase timeout, force transition")
    fsm.force_next_phase()
```

**参考**：[FAQ: 调试问题 - Q6](../faq/debugging.md#q6-如何调试-fsm-状态机)

---

## 性能问题

### Simulation too slow

**现象**：仿真速度远低于实时（< 0.1× realtime）。

**诊断**：

```python
import time

n_steps = 1000
start = time.time()

for _ in range(n_steps):
    mujoco.mj_step(model, data)

elapsed = time.time() - start
realtime_ratio = (n_steps * model.opt.timestep) / elapsed
print(f"Realtime ratio: {realtime_ratio:.2f}×")
```

**优化方法**：

| 方法 | 提速 | 副作用 |
|-----|------|--------|
| 降低渲染频率 | 2-5× | 视觉不连续 |
| 关闭接触可视化 | 1.2-1.5× | 无 |
| 提高 timestep | 1.5-2× | 可能不稳定 |
| 降低 solver iterations | 1.3-1.8× | 精度下降 |
| 无头渲染（批量） | 10-20× | 无可视化 |

**示例**：

```python
# 降低渲染频率
render_interval = 10  # 每 10 步渲染一次
if step % render_interval == 0:
    viewer.render()

# 关闭不必要的可视化
viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = False
```

**参考**：[FAQ: 调试问题 - Q3](../faq/debugging.md#q3-如何定位性能瓶颈)

---

### Out of memory

**错误信息**：
```
MemoryError: Unable to allocate X GB for array
```

**原因**：记录过多数据或预分配过大数组。

**解决方案**：

1. **降低记录频率**
   ```python
   # ✗ 每步都记录
   trajectory.append(data.qpos.copy())
   
   # ✓ 每 10 步记录一次
   if step % 10 == 0:
       trajectory.append(data.qpos.copy())
   ```

2. **使用增量保存**
   ```python
   # 每 1000 步保存到磁盘，清空内存
   if step % 1000 == 0:
       np.savez_compressed(f"trajectory_part_{step//1000}.npz", 
                           qpos=trajectory['qpos'])
       trajectory['qpos'].clear()
   ```

3. **减少预分配大小**
   ```python
   # ✗ 预分配巨大数组
   n_steps = 1000000
   trajectory = np.zeros((n_steps, model.nq))
   
   # ✓ 合理估计
   duration = 5.0  # s
   n_steps = int(duration / model.opt.timestep)
   trajectory = np.zeros((n_steps, model.nq))
   ```

---

## 数据问题

### JSON serialization error

**错误信息**：
```
TypeError: Object of type 'ndarray' is not JSON serializable
```

**原因**：NumPy 数组无法直接序列化为 JSON。

**解决方案**：

```python
import json
import numpy as np

# ✗ 直接保存 ndarray
result = {'forward': data.qpos[0]}  # ndarray scalar
json.dump(result, f)  # 报错

# ✓ 转换为 Python 类型
result = {'forward': float(data.qpos[0])}  # float
json.dump(result, f)  # 成功

# 或使用自定义编码器
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        return super().default(obj)

json.dump(result, f, cls=NumpyEncoder)
```

---

### CSV column mismatch

**错误信息**：
```
ValueError: Length mismatch: Expected axis has 6 elements, new values have 5 elements
```

**原因**：CSV 列数不匹配。

**解决方案**：

```python
import pandas as pd

# 严格检查列名
expected_columns = ['foot_length', 'leg_length', 'forward', 'alt_td', 'success']

df = pd.read_csv('results.csv')
assert list(df.columns) == expected_columns, f"Column mismatch: {df.columns}"

# 或允许额外列
df = pd.read_csv('results.csv', usecols=expected_columns)
```

---

## Git 相关错误

### Git LFS file not found

**错误信息**：
```
Error downloading object: model.xml (SHA: ...)
```

**原因**：未安装或初始化 Git LFS。

**解决方案**：

```powershell
# 安装 Git LFS
# Windows: 下载 https://git-lfs.github.com/

# 初始化
git lfs install

# 拉取 LFS 文件
git lfs pull
```

---

### Merge conflict in binary file

**现象**：二进制文件（.npz, .mp4）冲突无法自动合并。

**解决方案**：

```powershell
# 选择某一方的版本
git checkout --ours path/to/file.npz    # 保留本地版本
git checkout --theirs path/to/file.npz  # 保留远程版本

# 标记为已解决
git add path/to/file.npz
git commit
```

**最佳实践**：避免在多分支同时修改二进制文件。

---

## PowerShell 相关错误

### Execution policy error

**错误信息**：
```
无法加载文件 Activate.ps1，因为在此系统上禁止运行脚本
```

**解决方案**：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Command not found

**错误信息**：
```
The term 'python' is not recognized...
```

**原因**：PATH 中没有 Python 或使用了错误的命令。

**解决方案**：

```powershell
# ✗ 不要直接用 python
python script.py

# ✓ 使用完整路径
.\.venv-mujoco\Scripts\python.exe script.py

# 或激活环境后再用
.\.venv-mujoco\Scripts\Activate.ps1
python script.py
```

---

## 查找更多信息

- **仿真相关**：[FAQ: 仿真问题](../faq/simulation.md)
- **参数相关**：[FAQ: 参数问题](../faq/parameters.md)
- **环境相关**：[FAQ: 环境配置](../faq/environment.md)
- **调试相关**：[FAQ: 调试问题](../faq/debugging.md)

---

**最后更新**: 2026-06-04

# Common 公共库扩展模块

本文档介绍新增的跨版本通用模块。

## 新增模块概览

### 1. `model_loader.py` - MuJoCo 模型加载器

统一的模型加载接口，支持从 XML 字符串、文件、带缓存加载。

**主要功能：**
- `load_model_from_xml(xml_string)` - 从 XML 字符串加载
- `load_model_from_file(path)` - 从文件加载
- `load_model_from_string_with_cache(xml, cache_dir, name)` - 带缓存的加载（参数扫描场景）
- `get_model_info(model)` - 提取模型信息（关节、执行器、质量等）
- `validate_model(model, required_joints, required_actuators)` - 验证模型组件

**典型用法：**
```python
from common.model_loader import load_model_from_file, get_model_info

model = load_model_from_file("models/walker.xml")
info = get_model_info(model)
print(f"关节数: {info.n_joints}, 总质量: {info.total_mass:.2f} kg")
```

**示例代码：** `common/examples/example_model_loader.py`

---

### 2. `data_io.py` - 数据读写工具

标准化的 CSV、JSON 数据存储，自动添加版本和元数据。

**主要功能：**
- `save_timeseries_csv(path, data, metadata)` - 保存时间序列（自动生成 .meta.json）
- `load_timeseries_csv(path)` - 加载时间序列和元数据
- `save_summary_json(path, summary, metadata)` - 保存参数/结果摘要
- `load_summary_json(path)` - 加载摘要
- `save_pickle(path, obj, metadata)` / `load_pickle(path)` - pickle 序列化（带元数据）

**典型用法：**
```python
from common.data_io import save_timeseries_csv, load_timeseries_csv

# 保存
data = {"time": times, "hip_x": positions, "hip_z": heights}
save_timeseries_csv("out/sim.csv", data, metadata={"slope_deg": 2.5})

# 加载
loaded_data, meta = load_timeseries_csv("out/sim.csv")
slope = meta["metadata"]["slope_deg"]
```

**元数据格式：** 每个 CSV 文件会生成一个 `.csv.meta.json` 文件，包含：
- 版本号、时间戳
- 列名、行数
- 用户自定义元数据（参数、实验配置等）

**示例代码：** `common/examples/example_data_io.py`

---

### 3. `simulation_runner.py` - 通用仿真循环框架

可扩展的仿真执行器，支持回调、早停条件、数据记录。

**主要类：**
- `SimulationRunner` - 仿真执行器
- `Callback` - 回调基类（控制律、数据记录等）
- `EarlyStopCondition` - 早停条件基类（失败检测）

**内置回调：**
- `DataRecorder` - 时间序列数据记录器
- `ControllerCallback` - 通用控制律包装器

**内置早停条件：**
- `NaNDetector` - 检测 NaN/数值不稳定
- `HeightThreshold` - 高度越界检测（摔倒判据）
- `PenetrationDetector` - 穿透检测

**典型用法：**
```python
from common.model_loader import load_model_from_file
from common.simulation_runner import SimulationRunner, DataRecorder, NaNDetector
import mujoco

model = load_model_from_file("model.xml")
data = mujoco.MjData(model)

# 配置数据记录
recorder = DataRecorder(
    sample_hz=200.0,
    extractors={
        "hip_x": lambda m, d: float(d.qpos[0]),
        "hip_z": lambda m, d: float(d.qpos[1]),
    }
)

# 运行仿真
runner = SimulationRunner(
    model, data,
    callbacks=[recorder],
    early_stop_conditions=[NaNDetector()]
)
result = runner.run(duration=10.0)

# 提取数据
if result.success:
    data = recorder.get_numpy_data()
    print(f"仿真完成: {len(data['time'])} 个样本")
```

**自定义回调示例：**
```python
from common.simulation_runner import Callback

class MyController(Callback):
    def on_step(self, model, data, t, step):
        # 在每个仿真步执行控制律
        data.ctrl[0] = 10.0 * (target - data.qpos[0])

runner = SimulationRunner(model, data, callbacks=[MyController()])
```

**示例代码：** `common/examples/example_simulation_runner.py`

---

## 设计原则

1. **向后兼容** - 不破坏现有版本代码，可逐步迁移
2. **类型标注** - 所有公共接口都有完整类型提示
3. **清晰文档** - 函数 docstring 说明参数、返回值、用法
4. **独立性** - 模块间低耦合，可单独使用

---

## 使用建议

### 适合使用场景

- **model_loader**: 参数扫描、批量仿真、模型验证
- **data_io**: 标准化实验数据管理、版本追踪
- **simulation_runner**: 新版本开发、快速原型验证、参数优化

### 不需要立即迁移的场景

- 已稳定的版本（V10-V19）保持原有模式
- 性能关键路径（避免额外抽象开销）
- 版本特定的复杂逻辑（如 V15 的 tendon 注入）

---

## 运行示例

```powershell
cd D:\Dunna\Documents\hw-1

# 模型加载示例
& .venv-mujoco\Scripts\python.exe common\examples\example_model_loader.py

# 数据 I/O 示例
& .venv-mujoco\Scripts\python.exe common\examples\example_data_io.py

# 仿真循环示例
& .venv-mujoco\Scripts\python.exe common\examples\example_simulation_runner.py
```

所有示例已测试通过，输出文件保存在 `out/` 目录。

---

## 后续扩展建议

1. **validation.py** - 参数验证和边界检查工具
2. **visualization.py** - 统一的绘图接口（matplotlib 配置、中文支持）
3. **参数优化工具** - 基于 simulation_runner 的参数扫描框架
4. **单元测试** - 为新模块添加 pytest 测试

---

**创建时间：** 2026-06-04  
**作者：** Kiro (hw-1 公共库扩展)

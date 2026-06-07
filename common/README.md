# 公共库 (common/)

跨版本复用的工具函数和数据结构，避免代码重复。V11+ 版本应优先使用 common/ 库而非重复实现。

## 模块索引

| 模块 | 功能 | 主要函数/类 | 引入版本 |
|------|------|-------------|----------|
| `control_utils.py` | 控制工具 | `smoothstep()`, `limited_pd()`, `ramp_height()` | V20 |
| `mujoco_utils.py` | MuJoCo 工具 | `get_joint_address()`, `get_contact_flags()` | V20 |
| `ik_solvers.py` | 逆运动学 | `solve_2d_leg_ik()`, `solve_3d_leg_ik()` | V20 |
| `energy_metrics.py` | 能量分析 | `cost_of_transport()`, `mechanical_energy_series()` | V12 |
| `poincare.py` | Poincare 截面 | `collect_section()`, `floquet_multipliers()` | V12 |
| `terrain.py` | 地形生成 | `build_rugged_geom_xml()`, `generate_profile()` | V11 |
| `disturbance.py` | 扰动注入 | `apply_impulse()`, `PhaseNoiseSpec` | V11 |
| `motor_dynamics.py` | 电机模型 | `L1MotorActuator`, `PRESETS['mx64ar']`, `joint_armature_with_motor()` | V16 |
| `data_io.py` | 数据持久化 | `save_timeseries_csv()`, `save_summary_json()` | V12 |
| `model_loader.py` | 模型加载 | `load_model_from_file()`, `get_model_info()` | V13 |
| `simulation_runner.py` | 仿真框架 | `SimulationRunner`, `Callback`, `EarlyStopCondition` | V20 |
| `plot_styles.py` | 统一画图 | `set_style()`, `COLORS`, `MARKERS` | V11 |
| `benchmark.py` | 基准场景 | `SCENARIOS`, `register_scenario()` | V12 |

## 快速开始

### 计算运输成本 (CoT)

```python
from common.energy_metrics import cost_of_transport

# 输入能量 17.5 J，质量 5.1 kg，前进距离 4.6 m
cot = cost_of_transport(input_energy_j=17.5, mass_kg=5.1, distance_m=4.6)
print(f"CoT: {cot:.4f}")  # 输出: CoT: 0.0743
```

### 加载电机预设

```python
from common.motor_dynamics import PRESETS, L1MotorActuator

# 加载 Dynamixel MX-64AR 电机参数
mx64 = PRESETS['mx64ar']
print(f"额定扭矩: {mx64.tau_stall} N·m")
print(f"库仑摩擦: {mx64.tau_coulomb} N·m")

# 创建电机执行器（1:1 减速比）
actuator = L1MotorActuator(mx64, gear_ratio=1.0)
tau_motor = actuator.compute_torque(q_des=0.5, q=0.4, qd=1.2, dt=0.001)
```

### 2D 腿部逆运动学

```python
from common.ik_solvers import solve_2d_leg_ik
import numpy as np

# 目标足端位置 (x=0.2m 前方, y=-0.9m 下方)
target_foot = np.array([0.2, -0.9])
hip_pos = np.array([0.0, 0.0])
leg_length = 0.5

hip_angle, knee_angle = solve_2d_leg_ik(
    target_foot, hip_pos, leg_length, leg_length
)
print(f"髋关节角度: {np.degrees(hip_angle):.1f}°")
print(f"膝关节角度: {np.degrees(knee_angle):.1f}°")
```

### 生成崎岖地形

```python
from common.terrain import build_rugged_geom_xml, generate_profile

# 生成地形高度剖面（5m 长，幅值 20mm）
profile = generate_profile(
    length_m=5.0,
    amplitude_mm=20.0,
    wavelength_m=0.8,
    num_points=256
)

# 转换为 MuJoCo hfield XML 字符串
xml_string = build_rugged_geom_xml(profile, name="rugged_terrain")
```

### 使用仿真框架

```python
from common.simulation_runner import SimulationRunner, Callback

class DataRecorder(Callback):
    def __init__(self):
        self.data = []
    
    def on_step(self, model, data, t, step):
        self.data.append({
            'time': t,
            'qpos': data.qpos.copy(),
            'qvel': data.qvel.copy()
        })

# 创建仿真运行器
runner = SimulationRunner(model, data, timestep=0.001)
recorder = DataRecorder()
runner.add_callback(recorder)

# 运行 5 秒仿真
runner.run(duration=5.0)
print(f"记录了 {len(recorder.data)} 个时间步")
```

## 设计原则

1. **向后兼容**: 新增字段用 `Optional`，不破坏旧版本调用
2. **类型注解**: 所有公开函数必须有类型提示
3. **文档字符串**: 复杂函数必须有 docstring（参数、返回值、示例）
4. **单元测试**: `tests/test_common_*.py` 覆盖核心函数

## 使用示例

完整示例见 `common/examples/` 目录：
- `example_model_loader.py` - 模型加载和信息提取
- `example_data_io.py` - 数据保存和加载
- `example_simulation_runner.py` - 仿真框架使用
- `example_integrated_workflow.py` - 完整仿真工作流

## 版本采用情况

| 版本范围 | Common 使用率 | 状态 |
|---------|--------------|------|
| V01-V10 | 0% | 前 common 时代 |
| V11-V17 | 100% | ✅ 完全采用 |
| V18-V19 | 0% | ⚠️ 回退（本地重实现）|
| V20-V21 | 100% | ✅ 已迁移 |
| V22-V24 | N/A | 设计文档 |

**V18/V19 迁移**: 这两个版本使用本地 `_smoothstep()`, `_lpd()` 等函数，应迁移到 common/ 对应函数。

## 迁移指南

如果你的版本脚本有以下模式，可以迁移到 common/：

### 迁移控制函数

**Before**:
```python
def _smoothstep(x, x_min=0.0, x_max=1.0):
    t = np.clip((x - x_min) / (x_max - x_min), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def _lpd(q, qd, target, kp, kd, limit):
    return float(np.clip(kp * (target - q) - kd * qd, -limit, limit))
```

**After**:
```python
from common.control_utils import smoothstep, limited_pd

# 直接使用，签名相同
alpha = smoothstep(t, x_min=0.0, x_max=1.0)
tau = limited_pd(q, qd, target, kp, kd, limit)
```

### 迁移 MuJoCo 工具

**Before**:
```python
def _jaddr(model, joint_name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)

def _contacts(model, data):
    left = False
    right = False
    for i in range(data.ncon):
        # ... 复杂的接触检测逻辑
    return left, right
```

**After**:
```python
from common.mujoco_utils import get_joint_address, get_contact_flags

joint_id = get_joint_address(model, "left_hip")
left, right = get_contact_flags(model, data, "ramp", 
                                 ["left_heel", "left_sole"], 
                                 ["right_heel", "right_sole"])
```

## 添加新模块

如需添加新的 common/ 模块，遵循以下步骤：

1. 创建 `common/new_module.py`
2. 添加完整类型注解和 docstrings
3. 在 `tests/unit/test_new_module.py` 添加单元测试
4. 更新本 README 的模块索引表
5. 在至少一个版本中验证使用

## 常见问题

**Q: 为什么 V18/V19 没有使用 common/?**
A: 这两个版本在 V20 之前开发，当时部分工具（如 `control_utils.py`）尚未加入 common/。建议迁移。

**Q: 如何选择电机预设？**
A: `motor_dynamics.PRESETS` 提供三种：
- `'mx64ar'`: Dynamixel MX-64AR (实际硬件)
- `'ec_i40_53'`: Maxon EC-i 40 (备选方案)
- `'ideal'`: 理想电机（零摩擦，用于对照实验）

**Q: simulation_runner 与直接写仿真循环有什么区别？**
A: `SimulationRunner` 提供统一的 Callback 接口、早停条件、错误处理，推荐用于新版本。旧版本可以保留原有循环。

## 贡献

如发现代码重复或可复用模式，请：
1. 检查是否可抽象为 common/ 函数
2. 确保至少 3 个版本会用到（避免过度抽象）
3. 添加单元测试覆盖边界情况

# 代码规范

本项目遵循统一的代码规范，确保代码质量和可维护性。

## 文件命名

### 版本目录命名

```
v{两位数}_{snake_case_描述}
```

**示例**：
- ✅ `v13_parameter_sensitivity_atlas`
- ✅ `v13_6_event_driven_fsm`
- ✅ `v14c_arm_mass_lightening`
- ❌ `v13-parameter-sensitivity` (不用短横线)
- ❌ `v13_ParameterSensitivity` (不用驼峰)
- ❌ `v1_basic` (必须两位数，应为 v01)

### 脚本命名

每个版本包含四类脚本：

```
v{XX}_{版本名}/
  ├── simulate_*.py    # 运行仿真
  ├── analyze_*.py     # 分析数据
  ├── view_*.py        # 可视化查看
  ├── render_*.py      # 渲染视频
  ├── README.md        # 版本说明
  └── requirements.txt # 依赖（如有特殊）
```

**示例**（V10）：
```
v10_rolling_foot_biomimetic_gait/
  ├── simulate_rolling_foot_v10.py
  ├── analyze_rolling_foot_v10.py
  ├── view_rolling_foot_gait_v10.py
  ├── render_rolling_foot_v10.py
  └── README.md
```

### Python 模块命名

- **模块文件**：`snake_case.py`
- **类**：`PascalCase`
- **函数/变量**：`snake_case`
- **常量**：`UPPER_SNAKE_CASE`

**示例**：

```python
# common/energy_metrics.py

class EnergyAnalyzer:
    """能量分析器"""
    
    MAX_ENERGY_THRESHOLD = 1000.0  # 常量
    
    def __init__(self, model):
        self.model = model
        self.total_energy = 0.0  # 实例变量
    
    def calculate_kinetic_energy(self, data):  # 方法
        """计算动能"""
        return 0.5 * data.qvel.T @ (data.qM @ data.qvel)
```

## 代码结构

### 标准脚本结构

```python
"""
模块文档字符串：简要说明模块功能

Example:
    $ python simulate_v10.py
"""

# 标准库
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 第三方库
import numpy as np
import mujoco
import matplotlib.pyplot as plt

# 项目库
from common.energy_metrics import calculate_cot
from common.poincare import PoincareSectionAnalyzer


# 常量定义
MODEL_XML_PATH = Path(__file__).parent / "model_v10.xml"
OUTPUT_DIR = Path(__file__).parent / "out"
DURATION = 5.0  # s
TIMESTEP = 0.001  # s


# 类定义
class SimulationController:
    """仿真控制器"""
    
    def __init__(self, model: mujoco.MjModel):
        self.model = model
        # ...


# 函数定义
def load_model(xml_path: Path) -> mujoco.MjModel:
    """加载 MuJoCo 模型
    
    Args:
        xml_path: XML 文件路径
    
    Returns:
        MuJoCo 模型对象
    
    Raises:
        FileNotFoundError: 如果文件不存在
    """
    if not xml_path.exists():
        raise FileNotFoundError(f"Model file not found: {xml_path}")
    
    return mujoco.MjModel.from_xml_path(str(xml_path))


def main():
    """主函数"""
    # 加载模型
    model = load_model(MODEL_XML_PATH)
    data = mujoco.MjData(model)
    
    # 运行仿真
    result = run_simulation(model, data, duration=DURATION)
    
    # 保存结果
    save_results(result, OUTPUT_DIR / "result.json")
    
    print(f"✓ Simulation completed: {result['forward']:.2f}m")


if __name__ == "__main__":
    main()
```

### 配置管理

**使用 dataclass 管理参数**：

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SimulationConfig:
    """仿真配置"""
    
    # 基础参数
    duration: float = 5.0  # s
    timestep: float = 0.001  # s
    render: bool = True
    
    # 模型参数
    foot_length: float = 0.04  # m
    leg_length: float = 1.0  # m
    mass: float = 5.1  # kg
    
    # 控制参数
    kp_hip: float = 40.0
    kd_hip: float = 3.0
    kp_knee: float = 50.0
    kd_knee: float = 4.0
    
    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path("out"))
    save_trajectory: bool = True
    
    def validate(self):
        """验证配置合理性"""
        assert self.duration > 0, "Duration must be positive"
        assert self.timestep > 0, "Timestep must be positive"
        assert self.foot_length > 0, "Foot length must be positive"
        # ...

# 使用
config = SimulationConfig(
    duration=10.0,
    foot_length=0.042,
    kp_hip=45.0,
)
config.validate()
```

## 类型注解

### 基本类型注解

```python
from typing import Dict, List, Tuple, Optional, Union

def calculate_energy(
    qpos: np.ndarray,
    qvel: np.ndarray,
    mass: float,
) -> float:
    """计算总能量"""
    kinetic = 0.5 * mass * np.sum(qvel**2)
    potential = mass * 9.81 * qpos[1]
    return kinetic + potential

def analyze_trajectory(
    trajectory: Dict[str, np.ndarray],
    metrics: Optional[List[str]] = None,
) -> Dict[str, float]:
    """分析轨迹"""
    if metrics is None:
        metrics = ['forward', 'alt_td', 'cot']
    
    results: Dict[str, float] = {}
    for metric in metrics:
        results[metric] = compute_metric(trajectory, metric)
    
    return results
```

### MuJoCo 类型注解

```python
import mujoco
from typing import Protocol

# MuJoCo 对象类型
def run_simulation(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    duration: float,
) -> Dict[str, np.ndarray]:
    """运行仿真"""
    # ...

# 自定义协议
class Controller(Protocol):
    """控制器协议"""
    
    def compute(self, data: mujoco.MjData) -> np.ndarray:
        """计算控制信号"""
        ...
    
    def reset(self):
        """重置控制器状态"""
        ...
```

### NumPy 数组注解

```python
import numpy as np
from numpy.typing import NDArray

# 明确数组维度
def process_trajectory(
    qpos: NDArray[np.float64],  # shape: (n_steps, n_qpos)
    qvel: NDArray[np.float64],  # shape: (n_steps, n_qvel)
) -> NDArray[np.float64]:      # shape: (n_steps,)
    """处理轨迹数据"""
    # ...
```

## 文档字符串

### Google 风格文档字符串

```python
def parameter_sweep(
    param_grid: Dict[str, List[float]],
    baseline_config: SimulationConfig,
    output_dir: Path,
) -> pd.DataFrame:
    """参数扫描
    
    在给定参数网格上运行仿真，记录结果。
    
    Args:
        param_grid: 参数网格，如 {'kp': [30, 40, 50], 'kd': [2, 3, 4]}
        baseline_config: 基线配置
        output_dir: 输出目录
    
    Returns:
        包含所有扫描结果的 DataFrame，列包括：
        - 输入参数（kp, kd, ...）
        - 输出指标（forward, alt_td, cot, ...）
        - 状态标志（success, error_msg）
    
    Raises:
        ValueError: 如果 param_grid 为空
        FileNotFoundError: 如果 output_dir 不存在且无法创建
    
    Example:
        >>> config = SimulationConfig()
        >>> grid = {'foot_length': [0.038, 0.040, 0.042]}
        >>> results = parameter_sweep(grid, config, Path("out"))
        >>> print(results[results['success']].shape[0])  # 成功的任务数
        2
    
    Note:
        - 失败的任务会记录在 error_msg 列
        - 每个任务的详细结果保存在 output_dir/task_{id}.json
    """
    if not param_grid:
        raise ValueError("param_grid cannot be empty")
    
    # ...
```

### 类文档字符串

```python
class FSMController:
    """事件驱动有限状态机控制器
    
    实现 V13.6 事件驱动 FSM，包含四个相位：
    - stance_early: 触地缓冲
    - stance_late: 支撑推蹬
    - swing_thrust: 摆动加速
    - swing_retract: 摆动减速
    
    Attributes:
        model: MuJoCo 模型
        current_phase: 当前相位名称
        phase_elapsed_time: 当前相位持续时间
        params: 相位参数字典
    
    Example:
        >>> model = mujoco.MjModel.from_xml_path("model.xml")
        >>> fsm = FSMController(model)
        >>> ctrl = fsm.compute(data)
    """
    
    def __init__(self, model: mujoco.MjModel):
        """初始化控制器
        
        Args:
            model: MuJoCo 模型
        """
        self.model = model
        # ...
```

## 错误处理

### 异常使用

```python
# 输入验证
def set_foot_length(self, length: float):
    """设置足长"""
    if length <= 0:
        raise ValueError(f"Foot length must be positive, got {length}")
    if length > 0.1:
        raise ValueError(f"Foot length {length} exceeds reasonable range (0.1 m)")
    
    self.foot_length = length

# 资源管理
def load_trajectory(filepath: Path) -> Dict[str, np.ndarray]:
    """加载轨迹数据"""
    if not filepath.exists():
        raise FileNotFoundError(f"Trajectory file not found: {filepath}")
    
    try:
        data = np.load(filepath)
        return dict(data)
    except Exception as e:
        raise RuntimeError(f"Failed to load trajectory: {e}") from e

# 仿真失败处理
def run_simulation(model, data, duration):
    """运行仿真"""
    try:
        for step in range(int(duration / model.opt.timestep)):
            mujoco.mj_step(model, data)
            
            # 检查数值稳定性
            if np.any(np.isnan(data.qpos)):
                raise RuntimeError(f"NaN detected at step {step}")
            
            # 检查跌倒
            if data.qpos[1] < 0.3:
                raise RuntimeError(f"Robot fell at step {step}")
    
    except RuntimeError as e:
        print(f"✗ Simulation failed: {e}")
        return {'success': False, 'error': str(e)}
    
    return {'success': True, 'forward': data.qpos[0]}
```

### 警告使用

```python
import warnings

def set_timestep(self, timestep: float):
    """设置时间步长"""
    if timestep > 0.002:
        warnings.warn(
            f"Large timestep {timestep}s may cause instability. "
            "Consider using timestep <= 0.002s",
            UserWarning
        )
    
    self.model.opt.timestep = timestep

# V13 发现的孤立点解
def apply_v10_pd_control(self, kp: float, kd: float):
    """应用 V10 PD 控制律"""
    warnings.warn(
        "V10 PD control is an isolated solution. "
        "Success rate on geometric grid: 16.7%. "
        "Consider using V13.6 FSM control instead.",
        DeprecationWarning
    )
    # ...
```

## 日志记录

### 使用 logging 模块

```python
import logging
from datetime import datetime

# 配置日志
def setup_logging(output_dir: Path, level=logging.INFO):
    """配置日志系统"""
    log_file = output_dir / f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return logging.getLogger(__name__)

# 使用日志
logger = setup_logging(Path("out"))

def run_parameter_sweep(param_grid):
    """运行参数扫描"""
    logger.info(f"Starting parameter sweep: {len(param_grid)} tasks")
    
    for i, params in enumerate(param_grid):
        logger.debug(f"Task {i}: params={params}")
        
        try:
            result = run_simulation(params)
            logger.info(f"Task {i} completed: forward={result['forward']:.2f}m")
        except Exception as e:
            logger.error(f"Task {i} failed: {e}", exc_info=True)
    
    logger.info("Parameter sweep completed")
```

### 不同日志级别

```python
# DEBUG: 详细调试信息
logger.debug(f"FSM state: phase={fsm.phase}, elapsed={fsm.elapsed:.3f}s")

# INFO: 常规信息
logger.info(f"Simulation completed: {result['forward']:.2f}m in {result['time']:.2f}s")

# WARNING: 警告
logger.warning(f"High contact force detected: {force:.1f}N (threshold: 500N)")

# ERROR: 错误
logger.error(f"Simulation diverged at t={data.time:.3f}s")

# CRITICAL: 严重错误
logger.critical(f"Model file corrupted: {model_path}")
```

## 代码质量工具

### Ruff（linter + formatter）

项目使用 Ruff 进行代码检查和格式化。

**配置**（`pyproject.toml`）：

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**使用**：

```powershell
# 检查代码
.\.venv-mujoco\Scripts\python.exe -m ruff check .

# 自动修复
.\.venv-mujoco\Scripts\python.exe -m ruff check --fix .

# 格式化代码
.\.venv-mujoco\Scripts\python.exe -m ruff format .
```

### mypy（类型检查）

**配置**（`pyproject.toml`）：

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "mujoco.*"
ignore_missing_imports = true
```

**使用**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m mypy common/
.\.venv-mujoco\Scripts\python.exe -m mypy v13_6_event_driven_fsm/
```

### pytest（测试）

**测试文件命名**：`test_*.py` 或 `*_test.py`

**示例测试**：

```python
# tests/test_energy_metrics.py

import numpy as np
import pytest
from common.energy_metrics import calculate_cot

def test_calculate_cot_basic():
    """基础 CoT 计算"""
    mass = 5.0  # kg
    distance = 10.0  # m
    energy_input = 50.0  # J
    
    cot = calculate_cot(mass, distance, energy_input)
    
    expected = energy_input / (mass * 9.81 * distance)
    assert abs(cot - expected) < 1e-10

def test_calculate_cot_zero_distance():
    """零距离应该抛出异常"""
    with pytest.raises(ValueError, match="distance must be positive"):
        calculate_cot(5.0, 0.0, 50.0)

def test_calculate_cot_negative_energy():
    """负能量应该抛出异常"""
    with pytest.raises(ValueError, match="energy_input must be non-negative"):
        calculate_cot(5.0, 10.0, -10.0)
```

**运行测试**：

```powershell
.\.venv-mujoco\Scripts\python.exe -m pytest tests/
.\.venv-mujoco\Scripts\python.exe -m pytest -v  # 详细输出
.\.venv-mujoco\Scripts\python.exe -m pytest --cov=common  # 覆盖率
```

## 性能优化

### NumPy 向量化

```python
# ✗ 慢：Python 循环
energies = []
for i in range(len(trajectory)):
    qvel = trajectory['qvel'][i]
    energy = 0.5 * mass * np.sum(qvel**2)
    energies.append(energy)

# ✓ 快：NumPy 向量化
qvel_all = trajectory['qvel']  # shape: (n_steps, n_qvel)
energies = 0.5 * mass * np.sum(qvel_all**2, axis=1)
```

### 预分配数组

```python
# ✗ 慢：动态扩展
trajectory = []
for step in range(n_steps):
    mujoco.mj_step(model, data)
    trajectory.append(data.qpos.copy())  # 每次都 realloc

# ✓ 快：预分配
n_steps = int(duration / model.opt.timestep)
trajectory = np.zeros((n_steps, model.nq))
for step in range(n_steps):
    mujoco.mj_step(model, data)
    trajectory[step] = data.qpos
```

### 缓存计算结果

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def compute_floquet_multipliers(
    qpos_tuple: Tuple[float, ...],
    qvel_tuple: Tuple[float, ...],
) -> np.ndarray:
    """计算 Floquet 乘子（带缓存）"""
    qpos = np.array(qpos_tuple)
    qvel = np.array(qvel_tuple)
    # ... 计算 ...
    return multipliers

# 使用时转为 tuple（可哈希）
multipliers = compute_floquet_multipliers(
    tuple(qpos), tuple(qvel)
)
```

---

**相关资源**：
- [仿真工作流](simulation_workflow.md)
- [参数调优策略](parameter_tuning.md)
- [版本控制规范](version_control.md)
- [项目 pyproject.toml](../../pyproject.toml)

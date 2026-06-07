# HW-1 错误处理与日志系统指南

## 概述

本文档介绍 HW-1 项目的统一错误处理和日志系统。该系统提供：

- **统一的异常类层次结构**：明确的错误分类，便于捕获和处理
- **结构化日志**：支持 JSON 格式，便于分析和查询
- **错误恢复策略**：重试、降级等机制
- **监控和告警**：实时监控系统资源和仿真性能

---

## 目录

1. [快速开始](#快速开始)
2. [异常处理](#异常处理)
3. [日志系统](#日志系统)
4. [错误恢复](#错误恢复)
5. [监控和告警](#监控和告警)
6. [最佳实践](#最佳实践)
7. [示例代码](#示例代码)

---

## 快速开始

### 基本设置

在主脚本开始处设置日志系统：

```python
from common.logging_config import setup_logging, get_logger

# 设置日志（只需调用一次）
setup_logging(
    level="INFO",
    log_dir="out/logs/v19",
    enable_console=True,
    enable_file=True,
)

# 获取 logger
logger = get_logger(__name__)
logger.info("Simulation starting")
```

### 使用自定义异常

```python
from common.exceptions import SimulationFailureError

try:
    run_simulation()
except Exception as e:
    raise SimulationFailureError(
        "Simulation failed due to instability",
        failure_type="lateral_fall",
        time=5.3,
        state={"roll": 0.8, "hip_y": 0.5},
    )
```

---

## 异常处理

### 异常层次结构

```
HW1Error (基类)
├── ModelError
│   ├── ModelLoadError
│   └── ModelValidationError
├── SimulationError
│   ├── SimulationFailureError
│   ├── SimulationTimeoutError
│   └── SimulationNaNError
├── DataError
│   ├── DataValidationError
│   └── DataIOError
└── ControlError
    ├── ControlLimitError
    └── ControlStabilityError
```

### 自定义异常类

所有自定义异常都继承自 `HW1Error`，提供以下特性：

- **上下文信息**：保存错误发生时的参数、状态等
- **异常链**：保留原始异常信息
- **序列化**：可转换为字典，便于日志记录

#### 示例：模型加载错误

```python
from common.exceptions import ModelLoadError

try:
    model = mujoco.MjModel.from_xml_path(path)
except Exception as e:
    raise ModelLoadError(
        "Failed to load MuJoCo model",
        path=str(path),
        xml_hash="abc123",
        original_exception=e,
    )
```

#### 示例：仿真失败

```python
from common.exceptions import SimulationFailureError

if roll > math.radians(45):
    raise SimulationFailureError(
        "Robot fell due to excessive roll",
        failure_type="lateral_fall",
        time=current_time,
        step=step_count,
        state={
            "roll_rad": roll,
            "hip_y": hip_y,
            "hip_velocity": hip_vel,
        },
    )
```

#### 示例：数据验证错误

```python
from common.exceptions import DataValidationError

if len(data_columns) != expected_length:
    raise DataValidationError(
        "Data column length mismatch",
        field="time_series",
        expected=expected_length,
        actual=len(data_columns),
    )
```

### 包装标准异常

使用 `wrap_exception` 将标准 Python 异常转换为 `HW1Error`：

```python
from common.exceptions import wrap_exception

try:
    result = risky_operation()
except ValueError as e:
    raise wrap_exception(
        e,
        message="Invalid parameter value",
        context={"param": param_name, "value": param_value},
    )
```

---

## 日志系统

### 日志配置

#### 基本配置

```python
from common.logging_config import setup_logging

setup_logging(
    level="INFO",              # 日志级别
    log_dir="out/logs",        # 日志目录
    log_file_prefix="hw1",     # 文件前缀
    enable_console=True,       # 控制台输出
    enable_file=True,          # 文件输出
    enable_json=False,         # JSON 格式（用于分析）
    console_colors=True,       # 控制台彩色输出
)
```

#### JSON 格式日志（用于数据分析）

```python
setup_logging(
    level="DEBUG",
    log_dir="out/logs/analysis",
    enable_json=True,  # 启用 JSON 格式
)
```

JSON 日志示例：

```json
{
  "timestamp": "2026-06-05T10:30:45.123456",
  "level": "INFO",
  "logger": "v19_hip_abduction_active.simulate_v19",
  "message": "Simulation completed",
  "context": {
    "duration": 10.0,
    "steps": 5000,
    "success": true
  }
}
```

### 使用 Logger

#### 基本日志记录

```python
from common.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")
```

#### 带上下文的日志

```python
logger.info(
    "Simulation step completed",
    extra={
        "step": step_count,
        "time": simulated_time,
        "energy": total_energy,
    },
)
```

#### 记录异常

```python
try:
    run_simulation()
except Exception as e:
    logger.error("Simulation failed", exc_info=True)
    # 或使用便捷函数
    from common.logging_config import log_exception
    log_exception(logger, e, "Simulation error", {"version": "v19"})
```

### 上下文管理器

使用 `LogContext` 自动附加元数据：

```python
from common.logging_config import LogContext, get_context_logger

logger = get_context_logger(__name__)

with LogContext(experiment="v19", slope_deg=2.5):
    logger.info("Starting simulation")
    # 自动附加: experiment=v19, slope_deg=2.5
    run_simulation()
    logger.info("Simulation completed")
```

### 性能计时装饰器

使用 `@log_execution_time` 自动记录函数执行时间：

```python
from common.logging_config import log_execution_time

@log_execution_time()
def compute_inverse_kinematics(target_pos):
    # 耗时计算
    return solution

# 自动输出: Function 'compute_inverse_kinematics' executed in 0.123s
```

### 标准化日志（仿真开始/结束）

```python
from common.logging_config import log_simulation_start, log_simulation_end

# 记录开始
log_simulation_start(
    logger,
    version="v19",
    params={"slope_deg": 2.5, "duration": 10.0},
)

# ... 运行仿真 ...

# 记录结束
log_simulation_end(
    logger,
    version="v19",
    success=True,
    duration=elapsed_time,
    metrics={
        "distance": max_x,
        "steps": alternations,
        "cot": cost_of_transport,
    },
)
```

---

## 错误恢复

### 错误处理装饰器

#### 基本用法

```python
from common.error_handler import handle_errors
from common.exceptions import ModelError

@handle_errors(
    error_types=(ValueError, KeyError),
    default_return=None,
    log_level="WARNING",
)
def safe_load_config(path):
    # 可能抛出异常的代码
    config = json.loads(path.read_text())
    return config
```

#### 转换异常类型

```python
from common.error_handler import handle_errors
from common.exceptions import ModelLoadError

@handle_errors(
    error_types=(OSError, ValueError),
    raise_as=ModelLoadError,  # 转换为自定义异常
)
def load_model(path):
    return mujoco.MjModel.from_xml_path(path)
```

### 重试装饰器

```python
from common.error_handler import retry_on_failure

@retry_on_failure(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,  # 指数退避
    exceptions=(ConnectionError, TimeoutError),
)
def fetch_remote_data(url):
    # 可能间歇性失败的操作
    return requests.get(url)
```

### 错误恢复策略

#### 降级策略（Fallback）

```python
from common.error_handler import FallbackStrategy, safe_execute_with_recovery

# 使用默认值
strategy = FallbackStrategy(fallback_value=0.0)
result = safe_execute_with_recovery(
    compute_metric,
    strategy,
    data=sim_data,
)

# 使用备用函数
def fallback_computation(error, context):
    logger.warning(f"Using simplified computation: {error}")
    return simplified_compute(context["data"])

strategy = FallbackStrategy(fallback_func=fallback_computation)
result = safe_execute_with_recovery(compute_metric, strategy, data=sim_data)
```

#### 重试策略

```python
from common.error_handler import RetryStrategy, safe_execute_with_recovery

def load_data():
    return pd.read_csv(path)

strategy = RetryStrategy(func=load_data, max_attempts=3, delay=0.5)
result = safe_execute_with_recovery(load_data, strategy)
```

### 安全执行

```python
from common.error_handler import safe_execute

success, result, error = safe_execute(
    risky_function,
    x=10,
    y=20,
    default=None,
    log_errors=True,
)

if success:
    print(f"Result: {result}")
else:
    print(f"Failed: {error}")
    # 继续执行其他逻辑
```

### 错误上下文管理器

```python
from common.error_handler import ErrorContext
from common.exceptions import SimulationError

with ErrorContext(SimulationError, "Simulation failed during integration"):
    # 任何异常都会被转换为 SimulationError
    mujoco.mj_step(model, data)
```

---

## 监控和告警

### 系统资源监控

```python
from common.monitoring import SystemMonitor

# 创建监控器
monitor = SystemMonitor(
    memory_threshold_percent=85.0,
    cpu_threshold_percent=95.0,
    check_interval=1.0,
)

# 开始监控
monitor.start()

# 运行仿真
for step in range(n_steps):
    simulate_step()
    
    # 定期检查（可选，也可以在后台线程）
    if step % 100 == 0:
        monitor.check()

# 停止监控
monitor.stop()

# 生成报告
report = monitor.get_report()
logger.info(f"Resource usage - CPU: {report['cpu']['mean']:.1f}%, "
            f"Memory: {report['memory_mb']['max']:.1f} MB")
```

### 仿真性能监控

```python
from common.monitoring import SimulationMonitor

monitor = SimulationMonitor(
    target_realtime_factor=1.0,
    min_steps_per_second=100.0,
)

monitor.start()

for step in range(n_steps):
    t = step * dt
    simulate_step()
    
    # 更新监控（每隔一段时间）
    if step % 50 == 0:
        monitor.update(
            simulated_time=t,
            step_count=step,
            custom_metrics={"energy": total_energy},
        )

monitor.stop()
report = monitor.get_report()
```

### 性能追踪

```python
from common.monitoring import PerformanceTracker

tracker = PerformanceTracker()

for step in range(n_steps):
    with tracker.track("forward_dynamics"):
        mujoco.mj_forward(model, data)
    
    with tracker.track("control_computation"):
        compute_control()
    
    with tracker.track("integration"):
        mujoco.mj_step(model, data)

# 生成报告
report = tracker.get_report()
for operation, stats in report.items():
    logger.info(f"{operation}: mean={stats['mean']*1000:.2f}ms, "
                f"total={stats['total']:.2f}s")
```

### 告警管理

```python
from common.monitoring import AlertManager, SystemMonitor, SimulationMonitor

# 创建告警管理器
alert_mgr = AlertManager()

# 创建监控器（连接到告警管理器）
sys_monitor = SystemMonitor(alert_callback=alert_mgr.handle_alert)
sim_monitor = SimulationMonitor(alert_callback=alert_mgr.handle_alert)

sys_monitor.start()
sim_monitor.start()

# ... 运行仿真 ...

sys_monitor.stop()
sim_monitor.stop()

# 打印告警摘要
alert_mgr.print_summary()

# 获取特定类别的告警
warnings = alert_mgr.get_alerts(level="WARNING")
for alert in warnings:
    logger.warning(f"Alert: {alert.message}")
```

---

## 最佳实践

### 1. 日志级别使用指南

- **DEBUG**：详细的调试信息（循环内部状态、中间计算结果）
- **INFO**：重要的业务逻辑信息（仿真开始/结束、关键事件）
- **WARNING**：警告信息（接近阈值、可恢复的异常）
- **ERROR**：错误信息（操作失败、需要人工干预）
- **CRITICAL**：严重错误（系统崩溃、数据损坏）

### 2. 异常处理原则

- **具体优于通用**：优先捕获具体的异常类型
- **保留异常链**：使用 `from e` 保留原始异常
- **附加上下文**：记录错误发生时的参数、状态
- **及早验证**：在函数入口处验证参数

示例：

```python
def compute_control(q, qd, target):
    # 及早验证
    if not np.all(np.isfinite(q)):
        raise ControlError("Invalid joint positions (NaN or Inf)")
    
    try:
        torque = pd_controller(q, qd, target)
    except ValueError as e:
        # 保留异常链，附加上下文
        raise ControlError(
            "PD control computation failed",
            context={"q": q.tolist(), "target": target.tolist()},
            original_exception=e,
        ) from e
    
    return torque
```

### 3. 日志性能优化

对于高频调用的代码（如仿真循环），避免在每步记录日志：

```python
# 不推荐：每步都记录
for step in range(n_steps):
    logger.debug(f"Step {step}: x={x}, v={v}")  # 太频繁！

# 推荐：周期性记录或使用条件
for step in range(n_steps):
    if step % 100 == 0:  # 每 100 步记录一次
        logger.debug(f"Step {step}: x={x}, v={v}")
```

### 4. 监控粒度

- **系统监控**：每秒检查一次即可
- **仿真监控**：每 50-100 步更新一次
- **性能追踪**：只在需要调优时启用

### 5. 错误恢复决策树

```
错误发生
├─ 可自动恢复？
│  ├─ 是 → 使用重试或降级策略
│  └─ 否 → 记录日志并抛出异常
├─ 需要告警？
│  ├─ 是 → 触发告警（通过 AlertManager）
│  └─ 否 → 只记录日志
└─ 需要保存现场？
   ├─ 是 → 保存状态到文件（用于调试）
   └─ 否 → 只记录上下文到日志
```

---

## 示例代码

### 完整的仿真脚本模板

```python
"""V19: 3D 行走仿真（带统一错误处理和日志）。"""

from pathlib import Path
import time

from common.logging_config import (
    setup_logging,
    get_logger,
    log_simulation_start,
    log_simulation_end,
)
from common.exceptions import SimulationFailureError, ModelLoadError
from common.error_handler import handle_errors, ErrorContext
from common.monitoring import SystemMonitor, SimulationMonitor, AlertManager

# 设置日志
setup_logging(
    level="INFO",
    log_dir="out/logs/v19",
    log_file_prefix="v19_simulation",
)

logger = get_logger(__name__)


@handle_errors(error_types=(OSError, ValueError), raise_as=ModelLoadError)
def load_model(path: Path):
    """加载模型（带错误处理）。"""
    return mujoco.MjModel.from_xml_path(str(path))


def run_simulation(params):
    """运行仿真（带监控和告警）。"""
    # 记录开始
    log_simulation_start(logger, "v19", params.__dict__)
    
    # 创建监控系统
    alert_mgr = AlertManager()
    sys_monitor = SystemMonitor(alert_callback=alert_mgr.handle_alert)
    sim_monitor = SimulationMonitor(alert_callback=alert_mgr.handle_alert)
    
    sys_monitor.start()
    sim_monitor.start()
    
    start_time = time.time()
    success = False
    
    try:
        # 加载模型
        with ErrorContext(ModelLoadError, "Failed to load model"):
            model = load_model(MODEL_PATH)
            data = mujoco.MjData(model)
        
        # 仿真循环
        for step in range(int(params.duration / params.timestep)):
            t = step * params.timestep
            
            # 控制逻辑
            with ErrorContext(SimulationFailureError, "Control computation failed"):
                compute_control(model, data, params)
            
            # 仿真步进
            mujoco.mj_step(model, data)
            
            # 周期性监控
            if step % 100 == 0:
                sys_monitor.check()
                sim_monitor.update(
                    simulated_time=t,
                    step_count=step,
                )
            
            # 失败检测
            if not np.all(np.isfinite(data.qpos)):
                raise SimulationFailureError(
                    "NaN detected in state",
                    failure_type="nan_or_unstable",
                    time=t,
                    step=step,
                )
        
        success = True
        
    except SimulationFailureError as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        success = False
    
    finally:
        # 停止监控
        sys_monitor.stop()
        sim_monitor.stop()
        
        # 生成报告
        elapsed = time.time() - start_time
        log_simulation_end(logger, "v19", success, elapsed)
        
        # 打印告警摘要
        alert_mgr.print_summary()
        
        # 打印资源使用
        sys_report = sys_monitor.get_report()
        logger.info(f"Max memory: {sys_report['memory_mb']['max']:.1f} MB")
        
        sim_report = sim_monitor.get_report()
        logger.info(f"Avg speed: {sim_report['steps_per_second']['mean']:.1f} steps/s")
    
    return success


if __name__ == "__main__":
    params = V19Params()
    run_simulation(params)
```

---

## 附录

### 模块文件位置

- `common/exceptions.py` - 自定义异常类
- `common/error_handler.py` - 错误处理装饰器和工具
- `common/logging_config.py` - 日志配置和工具
- `common/monitoring.py` - 监控和告警系统

### 依赖项

核心功能无需额外依赖，但以下库可增强功能：

- `psutil`（推荐）：系统资源监控
  ```bash
  pip install psutil
  ```

### 常见问题

**Q: 日志文件在哪里？**

A: 默认在 `out/logs/` 目录，文件名格式为 `{prefix}_{timestamp}.log`

**Q: 如何禁用控制台彩色输出？**

A: 设置 `setup_logging(..., console_colors=False)`

**Q: 如何在多进程环境中使用日志？**

A: 每个进程需要独立调用 `setup_logging()`，建议使用不同的 `log_file_prefix`

**Q: 监控会影响仿真性能吗？**

A: 影响很小（< 1%），但不要在每个仿真步都调用 `check()` 或 `update()`

**Q: 如何导出 JSON 日志进行分析？**

A: 设置 `enable_json=True`，然后使用 Python/jq/pandas 解析：

```python
import json
with open("out/logs/hw1_20260605_103045.log") as f:
    for line in f:
        log_entry = json.loads(line)
        print(log_entry["message"], log_entry.get("context"))
```

---

## 更新日志

- **2026-06-05**: 初始版本，包含异常类、日志系统、错误处理、监控模块

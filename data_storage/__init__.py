"""hw-1 数据存储和索引系统

统一的数据存储和检索接口，基于 SQLite + Pandas。

## 快速开始

```python
from data_storage import create_database, get_connection
from data_storage import import_version_batch, query_simulations, get_best_simulations

# 1. 创建数据库
create_database("data_storage/hw1_data.db")

# 2. 导入数据
conn = get_connection("data_storage/hw1_data.db")
import_version_batch(conn, "V08", "v08_quasi_passive_assisted")

# 3. 查询数据
df = query_simulations(conn, version_name="V08", success_only=True)
best = get_best_simulations(conn, metric="CoT", top_n=5)

conn.close()
```

## 数据库结构

### versions 表
- version_id (PK)
- version_name (UNIQUE): 版本名称，如 "V08"
- description: 版本描述
- created_date: 创建时间
- git_hash: Git commit hash
- notes: 备注

### simulations 表（核心）
- sim_id (PK)
- version_id (FK)
- sim_type: 仿真类型（"param_scan", "single_run"）
- params_json: 参数 JSON 字符串
- success: 是否成功（1/0）
- failure_reason: 失败原因
- forward_distance: 前进距离（m）
- alternating_touchdowns: 交替触地次数
- simulated_time: 仿真时长（s）
- score: 综合分数
- active_input_energy_j: 主动输入能量（J）
- net_actuator_work_j: 执行器净功（J）
- CoT: 能量成本系数
- quasi_passive: 是否准被动（1/0）
- pure_passive: 是否纯被动（1/0）
- timestamp: 记录时间戳
- csv_file: 来源 CSV 文件名
- json_file: 来源 JSON 文件名

### timeseries 表（可选）
- ts_id (PK)
- sim_id (FK)
- time: 时间步（s）
- hip_x, hip_z: 髋关节位置
- hip_vx, hip_vz: 髋关节速度
- joint_angles_json: 关节角度 JSON
- joint_velocities_json: 关节角速度 JSON
- contact_forces_json: 接触力 JSON

### benchmarks 表
- benchmark_id (PK)
- version_id (FK)
- metric_name: 指标名称
- metric_value: 指标值
- metric_unit: 单位
- benchmark_date: 测试日期
- conditions_json: 测试条件
- notes: 备注

## 主要功能

### 数据导入
- `import_scan_csv()`: 导入参数扫描 CSV
- `import_summary_json()`: 导入单次仿真 JSON
- `import_version_batch()`: 批量导入版本目录
- `import_benchmark_table()`: 导入性能对比表

### 数据查询
- `query_simulations()`: 灵活的仿真查询（支持多条件过滤）
- `get_best_simulations()`: 获取最佳性能仿真
- `compare_versions()`: 版本性能对比
- `query_by_param_range()`: 按参数范围查询
- `get_version_summary()`: 版本摘要统计
- `get_benchmark_summary()`: 基准性能对比
- `query_timeseries()`: 查询时间序列数据

### 数据导出
- `export_simulations_csv()`: 导出仿真数据为 CSV
- `export_simulation_json()`: 导出单个仿真为 JSON
- `export_timeseries_csv()`: 导出时间序列数据为 CSV

## 查询示例

### 查找最佳 CoT 的仿真
```python
best_cot = get_best_simulations(conn, metric="CoT", top_n=10, success_only=True)
print(best_cot[["version_name", "CoT", "forward_distance"]])
```

### 对比两个版本
```python
comparison = compare_versions(conn, ["V08", "V09", "V10"])
print(comparison)
```

### 按参数范围筛选
```python
steep_slopes = query_by_param_range(
    conn, "slope_deg", min_value=3.0, max_value=5.0
)
```

### 查询特定版本的成功仿真
```python
v10_success = query_simulations(
    conn,
    version_name="V10",
    success_only=True,
    min_distance=4.0
)
```

### 获取所有版本摘要
```python
summary = get_version_summary(conn)
print(summary)
```

## 性能优化

- 自动索引：version_id, success, score, CoT, timestamp
- 批量插入：使用事务处理
- JSON 查询：支持 SQLite JSON 函数
- Pandas 集成：查询结果直接返回 DataFrame

## 向后兼容

- 保留原有 CSV/JSON 文件格式
- 数据库作为索引层，不替代原始文件
- 可随时从数据库导出为原始格式
"""

from .data_exporter import (
    export_simulation_json,
    export_simulations_csv,
    export_timeseries_csv,
)
from .data_importer import (
    import_benchmark_table,
    import_scan_csv,
    import_summary_json,
    import_version_batch,
)
from .db_schema import (
    DB_VERSION,
    add_version,
    create_database,
    get_connection,
    get_version_id,
)
from .query_interface import (
    compare_versions,
    get_benchmark_summary,
    get_best_simulations,
    get_version_summary,
    query_by_param_range,
    query_simulations,
    query_timeseries,
)

__all__ = [
    # Schema
    "DB_VERSION",
    "create_database",
    "get_connection",
    "add_version",
    "get_version_id",
    # Import
    "import_scan_csv",
    "import_summary_json",
    "import_version_batch",
    "import_benchmark_table",
    # Query
    "query_simulations",
    "get_best_simulations",
    "compare_versions",
    "query_by_param_range",
    "get_version_summary",
    "get_benchmark_summary",
    "query_timeseries",
    # Export
    "export_simulations_csv",
    "export_simulation_json",
    "export_timeseries_csv",
]

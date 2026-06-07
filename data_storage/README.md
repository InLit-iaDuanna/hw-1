# hw-1 数据存储和索引系统

统一的数据存储、检索和查询系统，替代分散的 CSV/JSON 文件。

## 技术栈

- **SQLite**: 轻量级嵌入式数据库，无需服务器
- **Pandas**: 数据分析和操作
- **Python 3.10+**: 类型标注和现代语法

## 快速开始

### 1. 创建数据库

```python
from data_storage import create_database, get_connection

# 创建空数据库
create_database("data_storage/hw1_data.db")
```

### 2. 导入数据

```python
from data_storage import import_version_batch, import_benchmark_table

conn = get_connection("data_storage/hw1_data.db")

# 批量导入单个版本
stats = import_version_batch(conn, "V08", "../v08_quasi_passive_assisted")
print(f"导入 {stats['scan_csv']} 条扫描记录，{stats['summary_json']} 个摘要")

# 导入性能对比表
count = import_benchmark_table(conn, "../v12_energy_cot_analysis/out/v12_energy_cot_table.csv")
print(f"导入 {count} 条基准数据")

conn.close()
```

### 3. 查询数据

```python
from data_storage import (
    get_connection,
    query_simulations,
    get_best_simulations,
    compare_versions,
)

conn = get_connection("data_storage/hw1_data.db")

# 查询特定版本的成功仿真
df = query_simulations(conn, version_name="V10", success_only=True)
print(df[["sim_id", "forward_distance", "CoT", "score"]].head())

# 获取 CoT 最低的前 10 个仿真
best = get_best_simulations(conn, metric="CoT", top_n=10)
print(best)

# 对比多个版本
comparison = compare_versions(conn, ["V08", "V09", "V10", "V11_flat"])
print(comparison)

conn.close()
```

### 4. 高级查询

```python
# 按参数范围筛选
steep_slopes = query_by_param_range(
    conn,
    param_name="slope_deg",
    min_value=3.0,
    max_value=5.0,
    version_name="V07"
)

# 获取所有版本摘要
summary = get_version_summary(conn)
print(summary)

# 获取基准性能对比（透视表格式）
benchmarks = get_benchmark_summary(conn)
print(benchmarks)
```

### 5. 导出数据

```python
from data_storage import export_simulations_csv, export_simulation_json

# 导出查询结果为 CSV
export_simulations_csv(
    conn,
    "exports/v10_success.csv",
    version_name="V10",
    success_only=True
)

# 导出单个仿真为 JSON（兼容原格式）
export_simulation_json(conn, sim_id=123, "exports/sim_123.json")
```

## 数据库结构

### 表设计

1. **versions**: 版本元数据（V01-V24）
2. **simulations**: 仿真记录（参数、结果、性能指标）
3. **timeseries**: 时间序列数据（可选，关键仿真轨迹）
4. **benchmarks**: 性能基准测试结果

### 索引优化

- `idx_sim_version`: 按版本查询
- `idx_sim_success`: 按成功状态过滤
- `idx_sim_score`: 按分数排序
- `idx_sim_cot`: 按 CoT 排序
- `idx_sim_timestamp`: 按时间排序

## 性能特性

- **批量插入**: 事务处理，快速导入大量数据
- **索引查询**: 关键字段自动索引
- **JSON 查询**: 支持参数 JSON 字段查询
- **Pandas 集成**: 查询结果直接返回 DataFrame

## API 文档

### 数据库操作

- `create_database(db_path)`: 创建数据库并初始化表结构
- `get_connection(db_path)`: 获取数据库连接
- `add_version(conn, version_name, description, ...)`: 添加版本
- `get_version_id(conn, version_name)`: 获取版本 ID

### 数据导入

- `import_scan_csv(conn, version_name, csv_path)`: 导入参数扫描 CSV
- `import_summary_json(conn, version_name, json_path)`: 导入摘要 JSON
- `import_version_batch(conn, version_name, version_dir)`: 批量导入版本目录
- `import_benchmark_table(conn, csv_path)`: 导入性能对比表

### 数据查询

- `query_simulations(conn, version_name, success_only, ...)`: 灵活查询仿真
- `get_best_simulations(conn, metric, top_n, ...)`: 获取最佳性能仿真
- `compare_versions(conn, version_names)`: 版本性能对比
- `query_by_param_range(conn, param_name, min_value, max_value)`: 按参数范围查询
- `get_version_summary(conn)`: 版本摘要统计
- `get_benchmark_summary(conn)`: 基准性能对比（透视表）
- `query_timeseries(conn, sim_id)`: 查询时间序列数据

### 数据导出

- `export_simulations_csv(conn, output_path, ...)`: 导出仿真为 CSV
- `export_simulation_json(conn, sim_id, output_path)`: 导出单个仿真为 JSON
- `export_timeseries_csv(conn, sim_id, output_path)`: 导出时间序列为 CSV

## 使用场景

### 场景 1: 快速找到最佳参数组合

```python
best_cot = get_best_simulations(conn, metric="CoT", top_n=1, success_only=True)
best_params = json.loads(best_cot.iloc[0]["params_json"])
print(f"最佳 CoT: {best_cot.iloc[0]['CoT']}")
print(f"参数: {best_params}")
```

### 场景 2: 对比版本演进

```python
versions = ["V08", "V09", "V10", "V11_flat", "V11_terrain"]
comparison = compare_versions(conn, versions)
print(comparison[["version_name", "avg_cot", "max_distance", "max_touchdowns"]])
```

### 场景 3: 参数敏感性分析

```python
# 查找不同坡度下的性能
slopes = [2.0, 2.5, 3.0, 3.5, 4.0]
results = []

for slope in slopes:
    df = query_by_param_range(conn, "slope_deg", slope-0.1, slope+0.1)
    results.append({
        "slope": slope,
        "success_rate": df["success"].mean(),
        "avg_distance": df["forward_distance"].mean()
    })

import pandas as pd
print(pd.DataFrame(results))
```

### 场景 4: 失败模式分析

```python
failures = query_simulations(conn, version_name="V11_hard", success_only=False)
failures = failures[failures["success"] == 0]
print(failures["failure_reason"].value_counts())
```

## 向后兼容

- 保留所有原始 CSV/JSON 文件
- 数据库作为索引和查询加速层
- 可随时从数据库导出为原始格式
- 与现有 `common/data_io.py` 共存

## 文件结构

```
data_storage/
├── __init__.py              # 包导出
├── db_schema.py             # 数据库表结构定义
├── data_importer.py         # 数据导入工具
├── data_exporter.py         # 数据导出工具
├── query_interface.py       # 查询接口
├── hw1_data.db              # SQLite 数据库文件（生成后）
└── README.md                # 本文档
```

## 注意事项

1. **线程安全**: SQLite 支持多线程读，但写操作需要序列化
2. **事务处理**: 批量导入时自动使用事务，提高性能
3. **JSON 字段**: params_json 存储完整参数，支持 JSON 查询
4. **时间序列**: 可选存储，仅用于关键仿真的完整轨迹
5. **备份**: 定期备份 hw1_data.db 文件

## 未来扩展

- [ ] 时间序列数据自动导入
- [ ] 可视化查询结果（集成 matplotlib）
- [ ] 参数优化历史追踪
- [ ] 多版本参数对比可视化
- [ ] 导出为 HDF5 格式（科学计算优化）

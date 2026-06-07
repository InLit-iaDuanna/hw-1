# hw-1 数据存储和索引系统 - 使用指南

## 系统概述

统一的数据存储和索引系统，替代分散的 CSV/JSON 文件，提供高效的数据存储、检索和查询功能。

**技术栈**: SQLite + Pandas
**数据库位置**: `D:\Dunna\Documents\hw-1\data_storage\hw1_data.db`

---

## 快速开始

### 1. 安装依赖

```bash
cd D:\Dunna\Documents\hw-1
.venv-mujoco\Scripts\Activate.ps1
pip install -r data_storage\requirements.txt
```

### 2. 创建数据库并导入数据

```bash
python data_storage\example_import_and_query.py
```

这将：
- 创建数据库
- 导入 V07-V12 版本数据（1899 条仿真记录）
- 导入性能对比表（31 条基准数据）
- 执行示例查询验证功能

### 3. 使用命令行查询工具

```bash
# 查看所有版本摘要
python data_storage\quick_query.py --summary

# 对比版本
python data_storage\quick_query.py --compare V08 V09 V10

# 查找分数最高的 10 个仿真
python data_storage\quick_query.py --best-score 10 --success-only

# 查找 CoT 最低的 5 个仿真
python data_storage\quick_query.py --best-cot 5 --success-only

# 查询特定版本
python data_storage\quick_query.py --version V09 --success-only --limit 20

# 按参数范围查询
python data_storage\quick_query.py --param slope_deg 2.0 4.0 --success-only
```

---

## Python API 使用

### 基本查询

```python
from data_storage import get_connection, query_simulations

conn = get_connection("data_storage/hw1_data.db")

# 查询特定版本的成功仿真
df = query_simulations(conn, version_name="V10", success_only=True)
print(df[["sim_id", "forward_distance", "CoT", "score"]].head())

conn.close()
```

### 性能分析

```python
from data_storage import get_best_simulations, compare_versions

conn = get_connection("data_storage/hw1_data.db")

# 获取 CoT 最低的仿真
best_cot = get_best_simulations(conn, metric="CoT", top_n=10)
print(best_cot)

# 对比多个版本
comparison = compare_versions(conn, ["V08", "V09", "V10", "V11"])
print(comparison)

conn.close()
```

### 参数敏感性分析

```python
from data_storage import query_by_param_range

conn = get_connection("data_storage/hw1_data.db")

# 查询不同坡度下的性能
slopes = [2.0, 2.5, 3.0, 3.5, 4.0]
results = []

for slope in slopes:
    df = query_by_param_range(
        conn, "slope_deg", slope-0.1, slope+0.1, version_name="V07"
    )
    results.append({
        "slope": slope,
        "success_rate": df["success"].mean(),
        "avg_distance": df["forward_distance"].mean()
    })

import pandas as pd
print(pd.DataFrame(results))

conn.close()
```

### 导出数据

```python
from data_storage import export_simulations_csv, export_simulation_json

conn = get_connection("data_storage/hw1_data.db")

# 导出查询结果为 CSV
export_simulations_csv(
    conn,
    "exports/v10_success.csv",
    version_name="V10",
    success_only=True
)

# 导出单个仿真为 JSON（兼容原格式）
export_simulation_json(conn, sim_id=1810, output_path="exports/best_sim.json")

conn.close()
```

---

## 集成到现有代码

### 自动保存到数据库

修改仿真脚本，在保存 CSV/JSON 后自动写入数据库：

```python
from common.data_io import save_summary_json, save_to_database

# 保存原始文件（保持兼容性）
save_summary_json("out/sim_result.json", summary_data)

# 自动保存到数据库（可选）
save_to_database(summary_data, version_name="V13")
```

### 批量导入新版本

```python
from data_storage import get_connection, import_version_batch

conn = get_connection("data_storage/hw1_data.db")

# 导入新版本 V13
stats = import_version_batch(
    conn,
    version_name="V13",
    version_dir="v13_parameter_sensitivity_atlas"
)
print(f"导入 {stats['scan_csv']} 条扫描记录，{stats['summary_json']} 个摘要")

conn.close()
```

---

## 数据库结构

### 核心表

1. **versions**: 版本元数据
   - version_id, version_name, description, created_date, git_hash, notes

2. **simulations**: 仿真记录（参数、结果、性能指标）
   - sim_id, version_id, params_json, success, forward_distance, CoT, score, ...

3. **benchmarks**: 性能基准测试结果
   - benchmark_id, version_id, metric_name, metric_value, metric_unit, ...

4. **timeseries**: 时间序列数据（可选，关键仿真轨迹）
   - ts_id, sim_id, time, hip_x, hip_z, joint_angles_json, ...

### 索引优化

- `idx_sim_version`: 按版本查询
- `idx_sim_success`: 按成功状态过滤
- `idx_sim_score`: 按分数排序
- `idx_sim_cot`: 按 CoT 排序
- `idx_sim_timestamp`: 按时间排序

---

## 常见查询场景

### 1. 找到最佳参数组合

```python
best_cot = get_best_simulations(conn, metric="CoT", top_n=1, success_only=True)
best_params = json.loads(best_cot.iloc[0]["params_json"])
print(f"最佳 CoT: {best_cot.iloc[0]['CoT']}")
print(f"参数: {best_params}")
```

### 2. 版本演进分析

```python
versions = ["V08", "V09", "V10", "V11"]
comparison = compare_versions(conn, versions)
print(comparison[["version_name", "successful_sims", "avg_distance", "max_touchdowns"]])
```

### 3. 失败模式分析

```python
failures = query_simulations(conn, version_name="V07", success_only=False)
failures = failures[failures["success"] == 0]
print(failures["failure_reason"].value_counts())
```

### 4. 参数扫描分析

```python
# 查找特定参数范围的所有仿真
steep_slopes = query_by_param_range(
    conn, "slope_deg", min_value=3.0, max_value=4.0
)
print(f"找到 {len(steep_slopes)} 条记录")
print(steep_slopes.groupby("version_name")["success"].mean())
```

---

## 性能特性

- **批量插入**: 1899 条记录导入耗时 < 2 秒
- **索引查询**: 复杂查询（多条件过滤）< 100ms
- **JSON 查询**: 支持 SQLite JSON 函数，按参数范围查询
- **Pandas 集成**: 查询结果直接返回 DataFrame，支持后续分析

---

## 文件结构

```
data_storage/
├── __init__.py                      # 包导出
├── db_schema.py                     # 数据库表结构定义
├── data_importer.py                 # 数据导入工具
├── data_exporter.py                 # 数据导出工具
├── query_interface.py               # 查询接口
├── example_import_and_query.py      # 示例脚本（创建数据库+导入数据）
├── quick_query.py                   # 命令行查询工具
├── requirements.txt                 # 依赖列表
├── hw1_data.db                      # SQLite 数据库文件
├── USAGE.md                         # 本文档
└── README.md                        # 系统文档
```

---

## 向后兼容

- 保留所有原始 CSV/JSON 文件
- 数据库作为索引和查询加速层
- 可随时从数据库导出为原始格式
- 与现有 `common/data_io.py` 共存

---

## 后续扩展计划

- [ ] 时间序列数据自动导入
- [ ] 可视化查询结果（集成 matplotlib）
- [ ] 参数优化历史追踪
- [ ] 多版本参数对比可视化
- [ ] 导出为 HDF5 格式（科学计算优化）
- [ ] Web 界面（Flask/Streamlit）

---

## 已导入数据统计

- **版本数**: 8 (V07-V12 + 基准版本)
- **仿真总数**: 1899 条
- **成功仿真**: 103 条 (5.4%)
- **基准数据**: 31 条
- **参数扫描记录**: 1882 条
- **摘要记录**: 17 条

---

## 技术支持

如有问题或需要添加新功能，请参考：
- 系统文档: `data_storage/README.md`
- API 文档: 各模块 docstring
- 示例代码: `example_import_and_query.py`

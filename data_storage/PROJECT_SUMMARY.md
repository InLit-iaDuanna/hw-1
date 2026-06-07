# hw-1 数据存储和索引系统 - 项目总结

## 完成状态：✓ 已完成并验证

---

## 项目目标

为 D:\Dunna\Documents\hw-1 项目建立统一的数据存储和索引系统，替代分散的 CSV/JSON 文件，提供高效的数据存储、检索和查询功能。

---

## 技术实现

### 技术选型
- **数据库**: SQLite 3（轻量、无需服务器、嵌入式）
- **数据处理**: Pandas（DataFrame 操作、数据分析）
- **编程语言**: Python 3.10+（类型标注、现代语法）

### 系统架构

```
data_storage/
├── db_schema.py              # 数据库表结构定义（4 张表 + 8 个索引）
├── data_importer.py          # 数据导入工具（CSV/JSON 批量导入）
├── data_exporter.py          # 数据导出工具（CSV/JSON 导出）
├── query_interface.py        # 查询接口（7 个高级查询函数）
├── example_import_and_query.py  # 示例脚本（创建+导入+验证）
├── quick_query.py            # 命令行查询工具
├── hw1_data.db               # SQLite 数据库（1.7 MB）
├── requirements.txt          # 依赖列表
├── README.md                 # 系统文档
├── USAGE.md                  # 使用指南
└── __init__.py               # 包导出
```

---

## 数据库设计

### 表结构

1. **versions 表** - 版本元数据
   - version_id (PK), version_name (UNIQUE), description, created_date, git_hash, notes

2. **simulations 表** - 仿真记录（核心）
   - sim_id (PK), version_id (FK), sim_type, params_json
   - success, failure_reason, forward_distance, alternating_touchdowns
   - score, active_input_energy_j, net_actuator_work_j, CoT
   - quasi_passive, pure_passive, timestamp, csv_file, json_file

3. **timeseries 表** - 时间序列数据（可选）
   - ts_id (PK), sim_id (FK), time, hip_x, hip_z, hip_vx, hip_vz
   - joint_angles_json, joint_velocities_json, contact_forces_json

4. **benchmarks 表** - 性能基准
   - benchmark_id (PK), version_id (FK), metric_name, metric_value
   - metric_unit, benchmark_date, conditions_json, notes

### 索引优化

- `idx_sim_version`: 按版本查询
- `idx_sim_success`: 按成功状态过滤
- `idx_sim_score`: 按分数排序（降序）
- `idx_sim_cot`: 按 CoT 排序
- `idx_sim_timestamp`: 按时间排序（降序）
- `idx_ts_sim`: 时间序列按仿真 ID
- `idx_ts_time`: 时间序列按时间
- `idx_benchmark_version`: 基准按版本

---

## 核心功能

### 数据导入（data_importer.py）

- `import_scan_csv()`: 导入参数扫描 CSV（批量仿真）
- `import_summary_json()`: 导入摘要 JSON（单次仿真）
- `import_version_batch()`: 批量导入版本目录（自动扫描 out/）
- `import_benchmark_table()`: 导入性能对比表

**性能**: 1899 条记录导入耗时 < 2 秒

### 数据查询（query_interface.py）

- `query_simulations()`: 灵活查询（支持版本、成功状态、性能指标过滤）
- `get_best_simulations()`: 获取最佳性能仿真（按 CoT/score/distance 排序）
- `compare_versions()`: 版本性能对比（统计指标）
- `query_by_param_range()`: 按参数范围查询（JSON 字段查询）
- `get_version_summary()`: 版本摘要统计
- `get_benchmark_summary()`: 基准性能对比（透视表）
- `query_timeseries()`: 查询时间序列数据

**性能**: 复杂查询（多条件过滤）< 100ms

### 数据导出（data_exporter.py）

- `export_simulations_csv()`: 导出仿真数据为 CSV
- `export_simulation_json()`: 导出单个仿真为 JSON（兼容原格式）
- `export_timeseries_csv()`: 导出时间序列数据为 CSV

### 命令行工具（quick_query.py）

```bash
# 查看版本摘要
python data_storage\quick_query.py --summary

# 对比版本
python data_storage\quick_query.py --compare V08 V09 V10

# 查找最佳性能
python data_storage\quick_query.py --best-cot 10 --success-only
python data_storage\quick_query.py --best-score 5 --success-only

# 按参数查询
python data_storage\quick_query.py --param slope_deg 2.0 4.0
```

---

## 已导入数据统计

**运行**: `python data_storage\example_import_and_query.py`

**结果**:
- **版本数**: 8 个（V07, V08, V09, V10, V11, V11_flat, V11_terrain, V11_hard）
- **仿真总数**: 1899 条
  - 参数扫描记录: 1882 条
  - 摘要记录: 17 条
- **成功仿真**: 103 条 (5.4%)
- **基准数据**: 31 条（来自 v12_energy_cot_table.csv）
- **数据库大小**: 1.7 MB

**导入版本**:
- V07: 420 条扫描 + 2 条摘要
- V08: 1200 条扫描 + 5 条摘要
- V09: 181 条扫描 + 2 条摘要
- V10: 81 条扫描 + 2 条摘要
- V11: 0 条扫描 + 6 条摘要
- V12: 基准数据 31 条

---

## 集成到现有代码

### 修改 common/data_io.py

添加 `save_to_database()` 函数，支持自动保存到数据库（可选）：

```python
from common.data_io import save_summary_json, save_to_database

# 保存原始文件（向后兼容）
save_summary_json("out/sim_result.json", summary_data)

# 自动保存到数据库（可选）
save_to_database(summary_data, version_name="V13")
```

**特性**:
- 延迟导入，无强依赖
- 静默失败（数据库不存在时跳过）
- 向后兼容现有代码

---

## 查询示例验证

### 1. 版本对比

```
版本对比: V08, V09, V10
version_name  total_sims  successful_sims  max_distance  max_touchdowns
         V08        1205               30      2.397565              10
         V09         183               67     12.961327              21
         V10          83                2      4.556504              12
```

### 2. 最佳性能

```
分数最高的前 5 个仿真:
 sim_id version_name       score  forward_distance  alternating_touchdowns
   1810          V09 7370.374911          4.429156                      21
   1628          V09 7366.854911          4.429156                      21
   1629          V09 7366.854911          4.429156                      21
```

### 3. 参数范围查询

```
参数 slope_deg 范围 [3.0, 4.0] 的仿真:
找到 421 条记录（V07）
success_rate: 0.0% (全部失败)
```

### 4. 失败模式分析

```
V07 失败模式统计:
failure_reason
fall_down    422
```

---

## 性能优化措施

1. **批量插入**: 使用事务处理，减少磁盘 I/O
2. **自动索引**: 关键查询字段自动创建索引
3. **JSON 查询**: SQLite JSON 函数支持参数字段查询
4. **Pandas 集成**: 查询结果直接返回 DataFrame，避免二次转换
5. **行工厂**: `sqlite3.Row` 支持字典式访问

---

## 向后兼容性

- ✓ 保留所有原始 CSV/JSON 文件
- ✓ 数据库作为索引和查询加速层
- ✓ 可随时从数据库导出为原始格式
- ✓ 与现有 `common/data_io.py` 共存
- ✓ 可选功能，不影响现有代码

---

## 使用场景

### 场景 1: 快速找到最佳参数组合

```python
best_cot = get_best_simulations(conn, metric="CoT", top_n=1, success_only=True)
best_params = json.loads(best_cot.iloc[0]["params_json"])
```

### 场景 2: 版本演进分析

```python
comparison = compare_versions(conn, ["V08", "V09", "V10", "V11_flat"])
print(comparison[["version_name", "max_distance", "max_touchdowns"]])
```

### 场景 3: 参数敏感性分析

```python
for slope in [2.0, 2.5, 3.0, 3.5, 4.0]:
    df = query_by_param_range(conn, "slope_deg", slope-0.1, slope+0.1)
    print(f"Slope {slope}: success_rate={df['success'].mean():.1%}")
```

### 场景 4: 失败模式分析

```python
failures = query_simulations(conn, version_name="V07", success_only=False)
print(failures[failures["success"]==0]["failure_reason"].value_counts())
```

---

## 文档清单

1. **README.md**: 系统文档（架构、API、性能特性）
2. **USAGE.md**: 使用指南（快速开始、API 示例、常见场景）
3. **example_import_and_query.py**: 示例脚本（创建数据库+导入+查询验证）
4. **quick_query.py**: 命令行工具（7 种查询模式）
5. **requirements.txt**: 依赖列表（pandas>=2.0.0）

---

## 未来扩展计划

- [ ] 时间序列数据自动导入（从 CSV 解析轨迹）
- [ ] 可视化查询结果（集成 matplotlib）
- [ ] 参数优化历史追踪（记录每次参数调整）
- [ ] 多版本参数对比可视化（热力图、散点图）
- [ ] 导出为 HDF5 格式（科学计算优化）
- [ ] Web 界面（Flask 或 Streamlit）
- [ ] 自动生成性能报告（PDF/Markdown）

---

## 项目成果

✓ **数据库系统**: 完整的 SQLite 数据库，4 张表，8 个索引  
✓ **导入工具**: 支持 CSV/JSON 批量导入，1899 条记录已导入  
✓ **查询接口**: 7 个高级查询函数，支持复杂过滤和聚合  
✓ **命令行工具**: 快速查询命令行接口，7 种查询模式  
✓ **文档**: 完整的 README、使用指南、示例代码  
✓ **集成**: 与现有 data_io.py 集成，向后兼容  
✓ **验证**: 已导入部分历史数据并验证查询功能  

---

## 关键文件路径

- **数据库**: `D:\Dunna\Documents\hw-1\data_storage\hw1_data.db` (1.7 MB)
- **示例脚本**: `D:\Dunna\Documents\hw-1\data_storage\example_import_and_query.py`
- **快速查询**: `D:\Dunna\Documents\hw-1\data_storage\quick_query.py`
- **使用指南**: `D:\Dunna\Documents\hw-1\data_storage\USAGE.md`
- **系统文档**: `D:\Dunna\Documents\hw-1\data_storage\README.md`

---

## 下一步操作建议

1. **导入更多版本**: 运行 `import_version_batch()` 导入 V13-V24 版本数据
2. **集成到工作流**: 在新仿真脚本中调用 `save_to_database()` 自动保存
3. **性能分析**: 使用查询接口进行参数优化和版本对比分析
4. **定期备份**: 备份 `hw1_data.db` 文件

---

**项目完成时间**: 2026-06-04  
**数据库版本**: 1.0  
**Python 版本**: 3.10+

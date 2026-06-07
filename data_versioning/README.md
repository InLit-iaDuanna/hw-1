# hw-1 数据版本控制系统

类似 DVC 的数据版本控制系统，用于追踪仿真结果、模型文件、实验数据的版本变化。

## 设计理念

- **轻量级存储**：只记录文件哈希和元数据，不复制大文件
- **自动追踪**：集成到仿真脚本中，自动记录数据生成
- **完整性验证**：通过哈希验证数据完整性
- **快照管理**：创建时间点快照，标记重要里程碑

## 系统架构

```
data_versioning/
├── data_registry.yaml       # 数据资产注册表（YAML，人类可读）
├── version_tracker.py       # 版本追踪器（注册和追踪数据文件）
├── data_differ.py           # 数据差异对比（CSV、JSON、XML）
├── snapshot_manager.py      # 快照管理（创建、标记、对比快照）
├── restore_data.py          # 恢复历史数据（验证完整性）
└── README.md                # 本文档
```

## 快速开始

### 1. 初始化系统并注册现有数据

```python
from data_versioning.version_tracker import VersionTracker

project_root = r"D:\Dunna\Documents\hw-1"
tracker = VersionTracker(project_root)

# 注册单个文件
tracker.register_file(
    "out/example_summary.json",
    version_tag="V13",
    description="V13 baseline simulation results"
)

# 批量注册目录
assets = tracker.register_directory(
    "out",
    file_patterns=['*.csv', '*.json'],
    version_tag="V13"
)

print(f"Registered {len(assets)} files")
```

### 2. 自动追踪仿真输出（集成到仿真脚本）

```python
from data_versioning.version_tracker import VersionTracker, auto_register_simulation_output

# 在仿真脚本末尾添加
tracker = VersionTracker(r"D:\Dunna\Documents\hw-1")

auto_register_simulation_output(
    tracker=tracker,
    output_file="v13_floquet_long_run/out/simulation_results.csv",
    version_tag="V13",
    experiment_id="floquet_stability_test_001",
    params={"slope_deg": 3.0, "hip_stiffness": 50.0}
)
```

### 3. 创建快照

```python
from data_versioning.snapshot_manager import SnapshotManager

manager = SnapshotManager(r"D:\Dunna\Documents\hw-1")

# 创建全局快照
snapshot_id = manager.create_snapshot(
    name="v13_stable_baseline",
    description="V13 stable version for paper baseline",
    tags=["stable", "paper", "v13"]
)

# 创建特定版本的快照
snapshot_id = manager.create_snapshot(
    name="v19_3d_working",
    description="V19 3D stability working version",
    tags=["v19", "3d"],
    include_versions=["V19"]
)

# 标记里程碑
manager.mark_milestone("v13_stable", snapshot_id)
```

### 4. 对比数据版本

```python
from data_versioning.data_differ import DataDiffer

differ = DataDiffer(r"D:\Dunna\Documents\hw-1")

# 对比两个 CSV 文件
report = differ.compare_csv_files(
    "v13b_floquet_long_run/out/results_v1.csv",
    "v13b_floquet_long_run/out/results_v2.csv"
)

# 生成可读报告
text = differ.generate_diff_report(
    report,
    output_path="data_versioning/diff_report.txt"
)
print(text)
```

### 5. 验证数据完整性

```python
from data_versioning.restore_data import DataRestorer

restorer = DataRestorer(r"D:\Dunna\Documents\hw-1")

# 验证所有数据
results = restorer.verify_all_assets()

print(f"Valid: {results['summary']['valid']}")
print(f"Corrupted: {results['summary']['corrupted']}")
print(f"Missing: {results['summary']['missing']}")

# 生成完整性报告
report = restorer.generate_integrity_report(
    "data_versioning/integrity_report.txt"
)
```

## 核心功能

### 版本追踪（version_tracker.py）

**功能**：
- 注册数据文件（计算 SHA256 哈希）
- 自动分类（仿真结果、模型文件、配置、图表）
- 提取版本标签（V01-V24）
- 记录元数据（大小、时间、实验 ID）
- 链接 Git commit（如果可用）

**API**：
```python
tracker = VersionTracker(project_root)

# 注册文件
asset = tracker.register_file(file_path, category, version_tag, description)

# 批量注册
assets = tracker.register_directory(directory, file_patterns=['*.csv'])

# 查询
asset = tracker.get_asset_by_path(file_path)
assets = tracker.get_assets_by_version("V13")
assets = tracker.get_assets_by_category("simulation_results")

# 验证完整性
result = tracker.verify_file_integrity(file_path)

# 统计信息
stats = tracker.get_statistics()
```

### 数据差异对比（data_differ.py）

**功能**：
- CSV 文件对比（结构差异、统计差异、行级差异）
- JSON 文件对比（递归深度对比，高亮参数变化）
- 文本文件对比（XML 模型文件，unified diff）
- 生成人类可读报告

**API**：
```python
differ = DataDiffer(project_root)

# 对比 CSV
report = differ.compare_csv_files(file1, file2, key_columns=['sim_id'])

# 对比 JSON
report = differ.compare_json_files(file1, file2)

# 对比文本
report = differ.compare_text_files(file1, file2)

# 对比资产
report = differ.compare_assets(asset1, asset2)

# 生成报告
text = differ.generate_diff_report(report, output_path)
```

### 快照管理（snapshot_manager.py）

**功能**：
- 创建时间点快照（记录所有数据状态）
- 过滤快照内容（按类别、版本）
- 标记重要里程碑
- 对比快照差异
- 验证快照完整性
- 导出快照清单

**API**：
```python
manager = SnapshotManager(project_root)

# 创建快照
snapshot_id = manager.create_snapshot(
    name="milestone_name",
    description="Description",
    tags=["stable"],
    include_versions=["V13", "V14"]
)

# 列出快照
snapshots = manager.list_snapshots()

# 获取快照
snapshot = manager.get_snapshot(snapshot_id)

# 对比快照
report = manager.compare_snapshots(snapshot1_id, snapshot2_id)

# 验证快照
result = manager.verify_snapshot_integrity(snapshot_id)

# 标记里程碑
manager.mark_milestone("paper_submission", snapshot_id)

# 导出清单
manager.export_snapshot_manifest(snapshot_id, "manifest.json")
```

### 数据恢复（restore_data.py）

**功能**：
- 验证所有资产完整性
- 查找文件历史版本
- 从快照恢复数据
- 生成完整性报告

**API**：
```python
restorer = DataRestorer(project_root)

# 验证所有数据
results = restorer.verify_all_assets()

# 查找文件版本
versions = restorer.find_file_versions(file_path)

# 验证快照（不实际恢复）
report = restorer.restore_snapshot(snapshot_id, verify_only=True)

# 恢复快照到指定目录
report = restorer.restore_snapshot(snapshot_id, target_dir="restored/")

# 生成报告
text = restorer.generate_integrity_report("integrity_report.txt")
```

## 数据注册表结构

`data_registry.yaml` 是核心配置文件，包含：

```yaml
config:
  project_root: D:\Dunna\Documents\hw-1
  hash_algorithm: sha256

categories:
  simulation_results:
    patterns:
      - "*/out/**/*.csv"
      - "*/out/**/*.json"

assets:
  - asset_id: "out/example.csv_a1b2c3d4"
    file_path: "out/example.csv"
    category: "simulation_results"
    hash: "a1b2c3d4e5f6..."
    size_bytes: 58415
    registered_at: "2026-06-04T12:00:00"
    version_tag: "V13"
    experiment_id: "exp_001"

snapshots:
  - snapshot_id: "snap_20260604_120000"
    name: "v13_stable"
    created_at: "2026-06-04T12:00:00"
    asset_count: 150
    total_size_mb: 45.2
    assets: [...]

milestones:
  - name: "paper_submission"
    snapshot_id: "snap_20260604_120000"
    date: "2026-06-04"
```

## 集成到工作流

### 仿真脚本集成

在仿真脚本末尾添加：

```python
# v13b_floquet_long_run/simulate.py

from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_versioning.version_tracker import auto_register_simulation_output, VersionTracker

# ... 仿真代码 ...

# 自动注册输出
tracker = VersionTracker(project_root)
auto_register_simulation_output(
    tracker=tracker,
    output_file=str(output_csv_path),
    version_tag="V13",
    experiment_id=f"floquet_{timestamp}",
    params=simulation_params
)
```

### CI 流程集成

在 `.github/workflows/data_integrity.yml` 中：

```yaml
name: Data Integrity Check

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # 每周日检查

jobs:
  verify:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Verify data integrity
        run: |
          python -c "
          from data_versioning.restore_data import DataRestorer
          restorer = DataRestorer('.')
          results = restorer.verify_all_assets()
          
          if results['summary']['corrupted'] > 0:
              print('ERROR: Corrupted files detected!')
              exit(1)
          
          print(f\"Verified {results['summary']['valid']} files\")
          "
```

## 使用场景

### 场景 1：论文提交前创建基线快照

```python
manager = SnapshotManager(r"D:\Dunna\Documents\hw-1")

# 创建包含所有论文图表和关键数据的快照
snapshot_id = manager.create_snapshot(
    name="paper_submission_v1",
    description="All data and figures for paper submission",
    tags=["paper", "milestone"],
    include_categories=["figures", "simulation_results", "analysis_results"]
)

# 标记里程碑
manager.mark_milestone("paper_submission", snapshot_id)

# 导出清单
manager.export_snapshot_manifest(
    snapshot_id,
    "paper_submission_manifest.json"
)
```

### 场景 2：对比参数调整前后的结果

```python
differ = DataDiffer(r"D:\Dunna\Documents\hw-1")

# 对比调参前后
report = differ.compare_csv_files(
    "v13_parameter_sensitivity_atlas/out/baseline.csv",
    "v13_parameter_sensitivity_atlas/out/optimized.csv"
)

# 查看统计差异
for col, stats in report["statistical_diff"].items():
    pct = stats.get('mean_pct_change')
    if pct and abs(pct) > 5:  # 变化超过 5%
        print(f"{col}: {pct:+.2f}% change")
```

### 场景 3：验证数据完整性（每周例行检查）

```python
restorer = DataRestorer(r"D:\Dunna\Documents\hw-1")

# 验证所有数据
results = restorer.verify_all_assets()

# 如果有问题，生成报告
if results['summary']['corrupted'] > 0 or results['summary']['missing'] > 0:
    report = restorer.generate_integrity_report(
        "data_versioning/integrity_report.txt"
    )
    
    # 发送警报（邮件、钉钉等）
    send_alert(report)
```

### 场景 4：版本演进分析

```python
tracker = VersionTracker(r"D:\Dunna\Documents\hw-1")

# 获取所有版本的数据资产数量
stats = tracker.get_statistics()

for version, count in sorted(stats['versions'].items()):
    assets = tracker.get_assets_by_version(version)
    total_size = sum(a['size_bytes'] for a in assets)
    print(f"{version}: {count} assets, {total_size/1024/1024:.2f} MB")
```

## 最佳实践

1. **定期创建快照**：
   - 每个重要版本完成后
   - 论文提交前
   - 重大参数调整前

2. **标记里程碑**：
   - 使用有意义的名称
   - 添加详细描述
   - 记录日期

3. **自动追踪**：
   - 在仿真脚本中集成 `auto_register_simulation_output()`
   - 自动记录参数和 Git commit

4. **定期验证**：
   - 每周运行完整性检查
   - 在 CI 中自动验证关键数据

5. **对比分析**：
   - 参数调整前后对比
   - 版本间性能对比
   - 失败模式分析

## 与现有系统集成

- **data_storage 系统**：数据库存储详细仿真数据，版本控制系统追踪文件变化
- **Git**：自动记录 Git commit，关联代码和数据版本
- **CI 流程**：自动验证数据完整性
- **分析管道**：自动追踪分析结果输出

## 限制和注意事项

1. **不存储文件内容**：只记录哈希和元数据，无法直接恢复内容
2. **需要原始文件**：恢复依赖原始文件存在（建议配合备份系统）
3. **哈希计算开销**：大文件哈希计算可能较慢
4. **线程安全**：YAML 读写不是线程安全的（适合单进程使用）

## 未来扩展

- [ ] 集成 Git LFS 支持
- [ ] 云存储备份（S3、Azure Blob）
- [ ] 差分存储（增量备份）
- [ ] Web 界面可视化
- [ ] 自动检测数据漂移
- [ ] 集成到 Dashboard

## 故障排除

**问题：注册大量文件时很慢**
- 使用 `file_patterns` 过滤不需要的文件
- 批量注册时减少单次文件数量

**问题：哈希不匹配**
- 检查文件是否被意外修改
- 验证文件系统完整性
- 查看文件历史版本

**问题：快照太大**
- 使用 `include_versions` 过滤版本
- 使用 `include_categories` 过滤类别
- 只快照关键数据

## 相关文档

- [data_storage 系统](../data_storage/README.md)
- [CI 流程](../ci/README.md)
- [分析管道](../analysis_pipeline/README.md)

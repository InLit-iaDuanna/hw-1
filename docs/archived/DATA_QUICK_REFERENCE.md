# hw-1 数据管理快速参考

## 立即可执行的优化

### 1. 清理缓存文件（释放 ~15 MB）
```powershell
cd D:\Dunna\Documents\hw-1
.\scripts\cleanup_temp_files.ps1 -DryRun  # 先预览
.\scripts\cleanup_temp_files.ps1          # 实际执行
```

### 2. 查看数据清单
```powershell
Get-Content DATA_MANIFEST.json | ConvertFrom-Json | Select-Object -ExpandProperty summary
```

### 3. 验证数据完整性
```python
from data_versioning.restore_data import DataRestorer
restorer = DataRestorer('.')
results = restorer.verify_all_assets()
print(f'Valid: {results["summary"]["valid"]}, Corrupted: {results["summary"]["corrupted"]}')
```

## 数据系统概览

| 系统 | 位置 | 大小 | 用途 |
|------|------|------|------|
| data_storage | `data_storage/hw1_data.db` | 1.71 MB | SQLite 统一数据存储 |
| data_versioning | `data_versioning/data_registry.yaml` | 32 KB | 数据版本控制 |
| 版本输出 | `v*/out/` | 155.34 MB | 各版本仿真结果 |

## 关键数据文件

### 需要保留的文件
- `data_storage/hw1_data.db` - 数据库（建议使用 Git LFS）
- `data_versioning/data_registry.yaml` - 版本注册表
- `*_baseline*.csv` - 基线对比数据
- `*_table.csv` - 性能对比表

### 可复现的文件（可删除后重新生成）
- `*_data.csv` - 仿真时间序列数据（通过 simulate_v*.py 复现）
- `*.mp4` - 视频文件（通过 render_v*.py 复现）
- `*_scan_*.csv` - 参数扫描结果（重新运行扫描脚本）

## 常用操作

### 注册新版本数据到版本控制系统
```python
from data_versioning.version_tracker import VersionTracker
tracker = VersionTracker(r'D:\Dunna\Documents\hw-1')
tracker.register_directory('v25_new_version/out', file_patterns=['*.csv', '*.json'], version_tag='V25')
```

### 创建里程碑快照
```python
from data_versioning.snapshot_manager import SnapshotManager
manager = SnapshotManager(r'D:\Dunna\Documents\hw-1')
snapshot_id = manager.create_snapshot(
    name='paper_submission_2026',
    description='论文提交版本所有数据',
    tags=['paper', 'milestone']
)
```

### 查询性能数据
```python
from data_storage import get_connection, get_best_simulations
conn = get_connection('data_storage/hw1_data.db')
best = get_best_simulations(conn, metric='CoT', top_n=10)
print(best)
```

## Git LFS 设置（推荐）

```bash
git lfs install
git lfs track "*.db"
git lfs track "*.mp4"
git lfs track "**/*_data.csv"
git add .gitattributes
git commit -m "Add Git LFS tracking for large files"
```

## 磁盘空间统计

- **总项目大小**: 1.95 GB
- **虚拟环境**: 1.09 GB (.venv-mujoco + .venv-codex)
- **旧动画工程 项目**: 602 MB
- **版本输出数据**: 155 MB
- **可清理缓存**: ~15 MB

## 数据复现流程

### 示例：复现 V13.7 摩擦补偿数据
```powershell
cd v13_7_friction_compensation
python simulate_v13_7.py      # 生成仿真数据
python render_v13_7.py        # 生成视频
python analyze_v13_7.py       # 生成分析结果
```

## 相关文档

- 完整报告：`DATA_MANAGEMENT_REPORT.md`
- 数据清单：`DATA_MANIFEST.json`
- 清理脚本：`scripts/cleanup_temp_files.ps1`
- 数据存储文档：`data_storage/README.md`
- 版本控制文档：`data_versioning/README.md`

## 技术支持

如遇到数据完整性问题或需要恢复数据，参考：
- `data_versioning/README.md` 故障排除章节
- `data_storage/README.md` 数据导入导出章节

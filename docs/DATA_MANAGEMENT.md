# 数据管理指南

> 合并自：DATA_MANAGEMENT_REPORT.md, DATA_QUICK_REFERENCE.md

## 数据组织

### 目录结构

```
项目/
├── v*/out/              # 各版本的输出数据
├── data_storage/        # 集中数据存储
├── data_versioning/     # 数据版本控制
└── benchmarks/results/  # 基准测试结果
```

### 数据类型

| 类型 | 位置 | 格式 | 用途 |
|------|------|------|------|
| 仿真结果 | `v*/out/*.json` | JSON | 轨迹、能量、统计 |
| 可视化 | `v*/out/*.mp4` | MP4 | 动画视频 |
| 图表 | `v*/out/*.png` | PNG | 分析图表 |
| 原始数据 | `data_storage/` | CSV/HDF5 | 大规模扫描数据 |

## 数据命名规范

### 文件命名

```
{version}_{experiment}_{config}.{ext}

示例：
v13_7_smoke_mx64ar.mp4
v14c_arm_mass_scan_results.json
v17_noise1_estimation.csv
```

### 字段命名

```python
# 推荐：snake_case
data = {
    "forward_distance": 4.63,
    "alternating_touchdowns": 10,
    "mechanical_cot": 0.066
}

# 避免：缩写不清晰
data = {
    "fwd_dist": 4.63,  # ❌
    "alt_td": 10,      # ❌
    "mech_cot": 0.066  # ❌
}
```

## 数据读取

### JSON 结果

```python
import json

# 读取仿真结果
with open("v13_7_friction_compensation/out/smoke_v137_table.json") as f:
    results = json.load(f)
    
print(f"Forward distance: {results['forward']} m")
print(f"Touchdowns: {results['alt_td']}")
```

### CSV 数据

```python
import pandas as pd

# 读取扫描数据
df = pd.read_csv("v14c_arm_mass_lightening/out/v14c_C_m0.01.csv")
print(df.describe())
```

### HDF5 大数据

```python
import h5py

# 读取大规模数据
with h5py.File("data_storage/large_sweep.h5", "r") as f:
    trajectories = f["trajectories"][:]
    energy = f["energy"][:]
```

## 数据版本控制

### Git LFS

对于大文件（>100MB），使用 Git LFS：

```powershell
# 安装 Git LFS
git lfs install

# 跟踪大文件类型
git lfs track "*.mp4"
git lfs track "*.h5"

# 提交
git add .gitattributes
git commit -m "Track large files with LFS"
```

### 数据快照

```powershell
# 创建数据快照
python data_versioning/snapshot.py --version v13.7 --tag "baseline"

# 列出快照
python data_versioning/list_snapshots.py

# 恢复快照
python data_versioning/restore.py --snapshot v13.7_baseline
```

## 数据清理

### 临时文件

```powershell
# 查找临时文件
Get-ChildItem -Recurse -Filter "*_temp.json"

# 删除临时文件
Get-ChildItem -Recurse -Filter "*_temp.*" | Remove-Item
```

### 过期数据

```python
# 使用数据管理工具
from data_storage import DataManager

dm = DataManager()
dm.clean_expired(days=30)  # 删除30天前的临时数据
dm.archive_old_results(versions=["v01", "v02"])  # 归档旧版本
```

## 最佳实践

### 1. 总是保存元数据

```json
{
  "version": "v13.7",
  "timestamp": "2026-06-02T10:30:00",
  "git_commit": "a1b2c3d",
  "parameters": {
    "duration": 12.0,
    "motor": "mx64ar_full"
  },
  "results": {
    "forward": 4.63,
    "alt_td": 10
  }
}
```

### 2. 压缩大文件

```powershell
# 压缩视频（保持质量）
ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4

# 压缩数据
gzip large_data.csv
```

### 3. 定期备份

```powershell
# 备份关键数据
robocopy D:\Dunna\Documents\hw-1 E:\Backup\hw-1 /MIR /XD .venv-mujoco node_modules
```

## 参考资料

- [data_storage/README.md](../data_storage/README.md)
- [data_versioning/README.md](../data_versioning/README.md)
- [DATA_MANIFEST.json](../DATA_MANIFEST.json)

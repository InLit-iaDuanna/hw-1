"""
数据版本控制系统 - 快速参考

常用命令和代码片段。
"""

# ============================================================================
# 1. 初始化和基本使用
# ============================================================================

from data_versioning import VersionTracker, SnapshotManager, DataRestorer

project_root = r"D:\Dunna\Documents\hw-1"

# 初始化追踪器
tracker = VersionTracker(project_root)

# 查看统计
stats = tracker.get_statistics()
print(f"Total: {stats['total_assets']}, Size: {stats['total_size_mb']:.2f} MB")

# ============================================================================
# 2. 注册数据文件
# ============================================================================

# 注册单个文件
tracker.register_file(
    "out/results.csv", version_tag="V13", description="Simulation results"
)

# 批量注册目录
assets = tracker.register_directory(
    "v13_floquet_long_run/out", file_patterns=["*.csv", "*.json"], version_tag="V13"
)

# 自动注册仿真输出（在仿真脚本中使用）
from data_versioning import auto_register_simulation_output

auto_register_simulation_output(
    tracker=tracker,
    output_file="v13/out/sim_001.csv",
    version_tag="V13",
    experiment_id="floquet_test_001",
    params={"slope": 3.0, "stiffness": 50.0},
)

# ============================================================================
# 3. 查询和验证
# ============================================================================

# 查询特定版本的资产
assets = tracker.get_assets_by_version("V13")

# 查询特定类别的资产
assets = tracker.get_assets_by_category("simulation_results")

# 验证文件完整性
result = tracker.verify_file_integrity("out/results.csv")
if result["status"] == "valid":
    print("File is valid")

# 查看文件历史
history = tracker.get_file_history("out/results.csv")
for version in history:
    print(f"{version['registered_at']}: {version['hash'][:8]}")

# ============================================================================
# 4. 快照管理
# ============================================================================

manager = SnapshotManager(project_root)

# 创建快照
snapshot_id = manager.create_snapshot(
    name="v13_stable_baseline",
    description="V13 stable version for paper",
    tags=["stable", "paper", "v13"],
)

# 创建特定版本的快照
snapshot_id = manager.create_snapshot(
    name="v19_3d_working",
    description="V19 3D stability",
    tags=["v19", "3d"],
    include_versions=["V19"],
)

# 列出所有快照
snapshots = manager.list_snapshots()
for snap in snapshots:
    print(f"{snap['name']}: {snap['asset_count']} assets")

# 验证快照完整性
result = manager.verify_snapshot_integrity(snapshot_id)
print(f"Valid: {result['summary']['valid']}/{result['summary']['total']}")

# 对比两个快照
report = manager.compare_snapshots(snapshot1_id, snapshot2_id)
print(f"Added: {report['summary']['added']}")
print(f"Modified: {report['summary']['modified']}")

# 标记里程碑
manager.mark_milestone("paper_submission", snapshot_id)

# ============================================================================
# 5. 数据对比
# ============================================================================

from data_versioning import DataDiffer

differ = DataDiffer(project_root)

# 对比 CSV 文件
report = differ.compare_csv_files("v13/out/baseline.csv", "v13/out/optimized.csv")

# 生成可读报告
text = differ.generate_diff_report(
    report, output_path="data_versioning/diff_report.txt"
)

# 对比 JSON 文件
report = differ.compare_json_files("config_v1.json", "config_v2.json")

# 查看参数变化
for change in report["changes"]:
    if change["type"] == "value_change":
        print(f"{change['path']}: {change['old_value']} -> {change['new_value']}")

# ============================================================================
# 6. 完整性检查
# ============================================================================

restorer = DataRestorer(project_root)

# 验证所有数据
results = restorer.verify_all_assets()
print(f"Valid: {results['summary']['valid']}")
print(f"Corrupted: {results['summary']['corrupted']}")
print(f"Missing: {results['summary']['missing']}")

# 生成完整性报告
report = restorer.generate_integrity_report("data_versioning/integrity_report.txt")

# 验证快照（不实际恢复）
report = restorer.restore_snapshot(snapshot_id, verify_only=True)

# ============================================================================
# 7. 命令行使用
# ============================================================================

# 初始化系统并注册现有数据
# python data_versioning/initialize.py

# 运行示例
# python data_versioning/examples.py

# 完整性检查
# python data_versioning/check_integrity.py

# 完整性检查（CI 模式，失败时退出）
# python data_versioning/check_integrity.py --fail-on-error

# 仿真集成示例
# python data_versioning/integration_example.py

# ============================================================================
# 8. 常见工作流
# ============================================================================

# 工作流 1：论文提交前创建快照
manager = SnapshotManager(project_root)
snapshot_id = manager.create_snapshot(
    name="paper_submission_v1",
    description="All data for paper submission",
    tags=["paper", "milestone"],
    include_categories=["figures", "simulation_results"],
)
manager.mark_milestone("paper_submission", snapshot_id)

# 工作流 2：版本对比分析
differ = DataDiffer(project_root)
report = differ.compare_csv_files("v13/out/results.csv", "v14/out/results.csv")
for col, stats in report["statistical_diff"].items():
    pct = stats.get("mean_pct_change")
    if pct and abs(pct) > 5:
        print(f"{col}: {pct:+.2f}% change")

# 工作流 3：定期完整性检查（每周）
restorer = DataRestorer(project_root)
results = restorer.verify_all_assets()
if results["summary"]["corrupted"] > 0:
    # 发送警报
    report = restorer.generate_integrity_report()
    send_alert(report)

# 工作流 4：查找最佳实验结果
tracker = VersionTracker(project_root)
assets = tracker.get_assets_by_version("V13")
# 根据元数据筛选
best_assets = [a for a in assets if a.get("metadata", {}).get("success")]

# ============================================================================
# 9. CI 集成
# ============================================================================

# .github/workflows/data_integrity.yml
"""
name: Data Integrity Check

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # 每周日

jobs:
  verify:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install pyyaml pandas numpy

      - name: Check data integrity
        run: python data_versioning/check_integrity.py --fail-on-error
"""

# ============================================================================
# 10. 故障排除
# ============================================================================

# 问题：文件哈希不匹配
result = tracker.verify_file_integrity("file.csv")
if result["status"] == "corrupted":
    # 查看历史版本
    history = tracker.get_file_history("file.csv")
    for v in history:
        print(f"{v['registered_at']}: {v['hash'][:8]}")

# 问题：快照验证失败
result = manager.verify_snapshot_integrity(snapshot_id)
for corrupted in result["corrupted"]:
    print(f"Corrupted: {corrupted['file_path']}")

# 问题：大量文件注册慢
# 使用 file_patterns 过滤
assets = tracker.register_directory(
    "out", file_patterns=["*.csv"], recursive=False  # 只注册 CSV  # 不递归
)

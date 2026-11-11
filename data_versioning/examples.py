"""
数据版本控制系统使用示例

演示如何使用各个功能模块。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_versioning import (
    DataDiffer,
    DataRestorer,
    SnapshotManager,
    VersionTracker,
)


def example_version_tracking():
    """示例：版本追踪"""
    print("\n" + "=" * 80)
    print("Example 1: Version Tracking")
    print("=" * 80)

    tracker = VersionTracker(project_root)

    # 查看统计信息
    stats = tracker.get_statistics()
    print("\nRegistry Statistics:")
    print(f"  Total assets: {stats['total_assets']}")
    print(f"  Total size: {stats['total_size_mb']:.2f} MB")

    # 按类别查看
    print("\nBy category:")
    for category, count in stats["categories"].items():
        print(f"  {category}: {count}")

    # 验证单个文件
    if stats["total_assets"] > 0:
        print("\nVerifying file integrity:")
        result = tracker.verify_file_integrity("data_storage/hw1_data.db")
        print(f"  Status: {result['status']}")
        if result["status"] == "valid":
            print(f"  Hash: {result['hash'][:16]}...")


def example_snapshot_management():
    """示例：快照管理"""
    print("\n" + "=" * 80)
    print("Example 2: Snapshot Management")
    print("=" * 80)

    manager = SnapshotManager(project_root)

    # 列出现有快照
    snapshots = manager.list_snapshots()
    print(f"\nExisting snapshots: {len(snapshots)}")

    for snap in snapshots:
        print(f"\n  {snap['name']} ({snap['snapshot_id']})")
        print(f"    Created: {snap['created_at']}")
        print(f"    Assets: {snap['asset_count']}")
        print(f"    Size: {snap['total_size_mb']:.2f} MB")
        print(f"    Tags: {', '.join(snap['tags'])}")


def example_data_comparison():
    """示例：数据对比"""
    print("\n" + "=" * 80)
    print("Example 3: Data Comparison")
    print("=" * 80)

    differ = DataDiffer(project_root)

    # 对比两个 CSV 文件（如果存在）
    trial_00 = project_root / "out" / "trial_00.csv"
    trial_01 = project_root / "out" / "trial_01.csv"

    if trial_00.exists() and trial_01.exists():
        print("\nComparing trial_00.csv vs trial_01.csv:")

        report = differ.compare_csv_files(
            str(trial_00),
            str(trial_01),
        )

        # 显示结构差异
        if "structure_diff" in report:
            rows = report["structure_diff"]["rows"]
            print(
                f"  Row count: {rows['file1']} -> {rows['file2']} (diff: {rows['difference']:+d})"
            )

        # 显示统计差异（前3个）
        if "statistical_diff" in report:
            print("  Statistical differences (top 3):")
            for i, (col, stats) in enumerate(
                list(report["statistical_diff"].items())[:3]
            ):
                pct = stats.get("mean_pct_change")
                if pct is not None:
                    print(f"    {col}: {pct:+.2f}% change in mean")
    else:
        print("\n  Trial files not found, skipping comparison")


def example_integrity_check():
    """示例：完整性检查"""
    print("\n" + "=" * 80)
    print("Example 4: Integrity Check")
    print("=" * 80)

    restorer = DataRestorer(project_root)

    print("\nVerifying all registered assets...")
    results = restorer.verify_all_assets()

    print("\nIntegrity Summary:")
    print(f"  Total: {results['total_assets']}")
    print(
        f"  Valid: {results['summary']['valid']} ({results['summary']['valid_pct']:.1f}%)"
    )
    print(f"  Corrupted: {results['summary']['corrupted']}")
    print(f"  Missing: {results['summary']['missing']}")

    if results["summary"]["corrupted"] > 0:
        print(
            f"\n  WARNING: {results['summary']['corrupted']} corrupted files detected!"
        )

    if results["summary"]["missing"] > 0:
        print(f"\n  WARNING: {results['summary']['missing']} files missing!")


def example_snapshot_verification():
    """示例：快照验证"""
    print("\n" + "=" * 80)
    print("Example 5: Snapshot Verification")
    print("=" * 80)

    manager = SnapshotManager(project_root)

    snapshots = manager.list_snapshots()

    if snapshots:
        # 验证第一个快照
        snapshot_id = snapshots[0]["snapshot_id"]
        print(f"\nVerifying snapshot: {snapshots[0]['name']}")

        result = manager.verify_snapshot_integrity(snapshot_id)

        print("\nSnapshot Integrity:")
        print(f"  Total assets: {result['summary']['total']}")
        print(f"  Valid: {result['summary']['valid']}")
        print(f"  Corrupted: {result['summary']['corrupted']}")
        print(f"  Missing: {result['summary']['missing']}")
    else:
        print("\n  No snapshots found")


def main():
    """运行所有示例"""
    print("=" * 80)
    print("Data Versioning System - Usage Examples")
    print("=" * 80)

    try:
        example_version_tracking()
        example_snapshot_management()
        example_data_comparison()
        example_integrity_check()
        example_snapshot_verification()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Examples Complete")
    print("=" * 80)
    print("\nFor more details, see:")
    print("  - data_versioning/README.md")
    print("  - Individual module docstrings")
    print()


if __name__ == "__main__":
    main()

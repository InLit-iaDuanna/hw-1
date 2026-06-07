"""
数据版本控制系统初始化脚本

注册现有数据文件并创建初始快照。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_versioning.version_tracker import VersionTracker
from data_versioning.snapshot_manager import SnapshotManager


def initialize_data_versioning():
    """初始化数据版本控制系统"""
    print("=" * 80)
    print("Initializing Data Versioning System")
    print("=" * 80)
    print()

    # 初始化追踪器
    tracker = VersionTracker(project_root)
    print(f"Project root: {project_root}")
    print()

    # 注册关键数据目录
    directories_to_register = [
        {
            "path": "out",
            "patterns": ['*.csv', '*.json'],
            "description": "Main output directory",
        },
        {
            "path": "data_storage",
            "patterns": ['*.db'],
            "description": "SQLite database",
        },
        {
            "path": "paper_figures/output",
            "patterns": ['*.pdf', '*.png', '*.svg'],
            "description": "Paper figures",
        },
    ]

    total_registered = 0

    for dir_info in directories_to_register:
        dir_path = project_root / dir_info["path"]

        if not dir_path.exists():
            print(f"Skipping (not found): {dir_info['path']}")
            continue

        print(f"Registering: {dir_info['path']}")
        print(f"  Description: {dir_info['description']}")

        try:
            assets = tracker.register_directory(
                dir_info["path"],
                file_patterns=dir_info["patterns"],
                recursive=True,
            )

            print(f"  Registered: {len(assets)} files")
            total_registered += len(assets)

        except Exception as e:
            print(f"  Error: {e}")

        print()

    # 显示统计信息
    print("=" * 80)
    print("Registration Summary")
    print("=" * 80)

    stats = tracker.get_statistics()

    print(f"Total assets registered: {stats['total_assets']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")
    print()

    if stats['categories']:
        print("By category:")
        for category, count in stats['categories'].items():
            print(f"  {category}: {count}")
        print()

    if stats['versions']:
        print("By version:")
        for version, count in sorted(stats['versions'].items()):
            print(f"  {version}: {count}")
        print()

    # 创建初始快照
    print("=" * 80)
    print("Creating Initial Snapshot")
    print("=" * 80)

    manager = SnapshotManager(project_root)

    try:
        snapshot_id = manager.create_snapshot(
            name="initial_baseline",
            description="Initial baseline - all registered data assets at project setup",
            tags=["baseline", "initial"],
        )

        print()
        print(f"Created snapshot: {snapshot_id}")

        # 标记基线里程碑
        manager.mark_milestone("baseline", snapshot_id)
        print("Marked milestone: baseline")

    except Exception as e:
        print(f"Error creating snapshot: {e}")

    print()
    print("=" * 80)
    print("Initialization Complete")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review data_registry.yaml")
    print("  2. Create version-specific snapshots (e.g., V13, V19)")
    print("  3. Integrate auto_register_simulation_output() into simulation scripts")
    print("  4. Set up periodic integrity checks")
    print()


if __name__ == '__main__':
    initialize_data_versioning()

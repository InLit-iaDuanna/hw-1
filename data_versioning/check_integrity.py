"""
数据完整性检查脚本

验证所有注册数据的完整性，生成报告。
可集成到 CI 流程或定期运行。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_versioning import DataRestorer, SnapshotManager


def check_integrity(generate_report: bool = True, fail_on_error: bool = False):
    """
    检查数据完整性

    Args:
        generate_report: 是否生成详细报告文件
        fail_on_error: 发现错误时是否返回非零退出码

    Returns:
        退出码（0=成功，1=有错误）
    """
    print("=" * 80)
    print("Data Integrity Check")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()

    restorer = DataRestorer(project_root)

    # 验证所有资产
    print("Verifying all registered assets...")
    results = restorer.verify_all_assets()

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total assets: {results['total_assets']}")
    print(
        f"Valid: {results['summary']['valid']} ({results['summary']['valid_pct']:.1f}%)"
    )
    print(f"Corrupted: {results['summary']['corrupted']}")
    print(f"Missing: {results['summary']['missing']}")
    print()

    # 详细错误信息
    if results["summary"]["corrupted"] > 0:
        print("CORRUPTED FILES:")
        print("-" * 80)
        for item in results["corrupted"]:
            print(f"  {item['file_path']}")
            print(f"    Expected: {item['expected_hash']}")
            print(f"    Actual:   {item['actual_hash']}")
        print()

    if results["summary"]["missing"] > 0:
        print("MISSING FILES:")
        print("-" * 80)
        for file_path in results["missing"][:20]:
            print(f"  {file_path}")
        if len(results["missing"]) > 20:
            print(f"  ... and {len(results['missing']) - 20} more")
        print()

    # 验证快照
    print("=" * 80)
    print("SNAPSHOT VERIFICATION")
    print("=" * 80)

    manager = SnapshotManager(project_root)
    snapshots = manager.list_snapshots()

    print(f"Total snapshots: {len(snapshots)}")

    for snap in snapshots:
        print(f"\n  {snap['name']}:")
        snap_result = manager.verify_snapshot_integrity(snap["snapshot_id"])

        print(
            f"    Valid: {snap_result['summary']['valid']}/{snap_result['summary']['total']}"
        )

        if snap_result["summary"]["corrupted"] > 0:
            print(f"    Corrupted: {snap_result['summary']['corrupted']}")

        if snap_result["summary"]["missing"] > 0:
            print(f"    Missing: {snap_result['summary']['missing']}")

    print()

    # 生成报告文件
    if generate_report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = (
            project_root / "data_versioning" / f"integrity_report_{timestamp}.txt"
        )

        text_report = restorer.generate_integrity_report(str(report_path))
        print(f"Report saved to: {report_path}")

        # 也保存 JSON 格式
        json_path = report_path.with_suffix(".json")

        json_results = {
            "checked_at": datetime.now().isoformat(),
            "summary": results["summary"],
            "corrupted": results["corrupted"],
            "missing": results["missing"][:100],  # 限制数量
            "snapshots": [
                {
                    "snapshot_id": snap["snapshot_id"],
                    "name": snap["name"],
                    "verification": manager.verify_snapshot_integrity(
                        snap["snapshot_id"]
                    )["summary"],
                }
                for snap in snapshots
            ],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)

        print(f"JSON report saved to: {json_path}")

    print()
    print("=" * 80)

    # 确定退出状态
    has_errors = (
        results["summary"]["corrupted"] > 0 or results["summary"]["missing"] > 0
    )

    if has_errors:
        print("STATUS: FAILED - Data integrity issues detected")
        exit_code = 1
    else:
        print("STATUS: PASSED - All data verified successfully")
        exit_code = 0

    print("=" * 80)
    print()

    if fail_on_error and has_errors:
        sys.exit(exit_code)

    return exit_code


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check data integrity for hw-1 project"
    )

    parser.add_argument(
        "--no-report", action="store_true", help="Don't generate report files"
    )

    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero code if errors detected (for CI)",
    )

    args = parser.parse_args()

    exit_code = check_integrity(
        generate_report=not args.no_report, fail_on_error=args.fail_on_error
    )

    if args.fail_on_error:
        sys.exit(exit_code)

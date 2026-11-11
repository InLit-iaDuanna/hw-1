"""
数据恢复工具

验证和恢复历史数据版本。
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .version_tracker import VersionTracker
from .snapshot_manager import SnapshotManager


class DataRestorer:
    """数据恢复器"""

    def __init__(self, project_root: str, registry_path: Optional[str] = None):
        """
        初始化数据恢复器

        Args:
            project_root: 项目根目录
            registry_path: 注册表 YAML 文件路径
        """
        self.project_root = Path(project_root)
        self.tracker = VersionTracker(project_root, registry_path)
        self.snapshot_manager = SnapshotManager(project_root, registry_path)

    def verify_all_assets(self) -> Dict[str, Any]:
        """
        验证所有注册资产的完整性

        Returns:
            验证报告字典
        """
        registry = self.tracker.registry
        assets = registry.get("assets", [])

        results = {
            "verified_at": datetime.now().isoformat(),
            "total_assets": len(assets),
            "valid": [],
            "corrupted": [],
            "missing": [],
        }

        print(f"Verifying {len(assets)} assets...")

        for i, asset in enumerate(assets):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(assets)}")

            verification = self.tracker.verify_file_integrity(asset["file_path"])

            if verification["status"] == "valid":
                results["valid"].append(asset["file_path"])
            elif verification["status"] == "corrupted":
                results["corrupted"].append(
                    {
                        "file_path": asset["file_path"],
                        "expected_hash": asset["hash"][:16],
                        "actual_hash": verification.get("current_hash", "N/A")[:16],
                    }
                )
            elif verification["status"] == "missing":
                results["missing"].append(asset["file_path"])

        results["summary"] = {
            "valid": len(results["valid"]),
            "corrupted": len(results["corrupted"]),
            "missing": len(results["missing"]),
            "valid_pct": len(results["valid"]) / len(assets) * 100 if assets else 0,
        }

        return results

    def restore_file_from_backup(
        self,
        file_path: str,
        backup_dir: str,
        verify_hash: bool = True,
    ) -> bool:
        """
        从备份目录恢复文件

        Args:
            file_path: 要恢复的文件路径（相对于项目根目录）
            backup_dir: 备份目录路径
            verify_hash: 是否验证哈希

        Returns:
            是否成功恢复
        """
        file_path = Path(file_path)

        if file_path.is_absolute():
            file_path = file_path.relative_to(self.project_root)

        # 获取资产信息
        asset = self.tracker.get_asset_by_path(str(file_path))

        if not asset:
            print(f"File not registered: {file_path}")
            return False

        # 查找备份文件
        backup_dir = Path(backup_dir)
        backup_file = backup_dir / file_path

        if not backup_file.exists():
            print(f"Backup file not found: {backup_file}")
            return False

        # 验证备份文件哈希
        if verify_hash:
            backup_hash = self.tracker._compute_file_hash(backup_file)

            if backup_hash != asset["hash"]:
                print(f"Backup file hash mismatch!")
                print(f"  Expected: {asset['hash'][:16]}")
                print(f"  Actual:   {backup_hash[:16]}")
                return False

        # 恢复文件
        target_file = self.project_root / file_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(backup_file, target_file)
        print(f"Restored: {file_path}")

        return True

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_dir: Optional[str] = None,
        verify_only: bool = False,
    ) -> Dict[str, Any]:
        """
        恢复快照（或仅验证）

        Args:
            snapshot_id: 快照 ID
            target_dir: 目标目录（None 表示恢复到原位置）
            verify_only: 仅验证，不实际恢复

        Returns:
            恢复报告字典
        """
        snapshot = self.snapshot_manager.get_snapshot(snapshot_id)

        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        if target_dir:
            target_dir = Path(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = self.project_root

        results = {
            "snapshot_id": snapshot_id,
            "restored_at": datetime.now().isoformat(),
            "verify_only": verify_only,
            "success": [],
            "failed": [],
            "skipped": [],
        }

        print(
            f"{'Verifying' if verify_only else 'Restoring'} snapshot: {snapshot['name']}"
        )
        print(f"  Assets: {len(snapshot['assets'])}")

        for asset in snapshot["assets"]:
            file_path = self.project_root / asset["file_path"]

            # 检查文件是否存在
            if not file_path.exists():
                results["failed"].append(
                    {
                        "file_path": asset["file_path"],
                        "reason": "File missing from source",
                    }
                )
                continue

            # 验证哈希
            current_hash = self.tracker._compute_file_hash(file_path)

            if current_hash != asset["hash"]:
                results["failed"].append(
                    {
                        "file_path": asset["file_path"],
                        "reason": "Hash mismatch",
                        "expected": asset["hash"][:16],
                        "actual": current_hash[:16],
                    }
                )
                continue

            # 如果仅验证，跳过复制
            if verify_only:
                results["success"].append(asset["file_path"])
                continue

            # 恢复文件
            target_path = target_dir / asset["file_path"]

            if target_path.exists() and target_path != file_path:
                # 目标文件已存在
                results["skipped"].append(
                    {
                        "file_path": asset["file_path"],
                        "reason": "Target file already exists",
                    }
                )
                continue

            if target_path != file_path:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_path)

            results["success"].append(asset["file_path"])

        results["summary"] = {
            "success": len(results["success"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"]),
        }

        return results

    def find_file_versions(self, file_path: str) -> List[Dict[str, Any]]:
        """
        查找文件的所有历史版本

        Args:
            file_path: 文件路径

        Returns:
            版本列表（按时间倒序）
        """
        history = self.tracker.get_file_history(file_path)

        # 按注册时间倒序排列
        history.sort(key=lambda x: x["registered_at"], reverse=True)

        return history

    def rollback_file(
        self,
        file_path: str,
        target_hash: str,
        backup_current: bool = True,
    ) -> bool:
        """
        回滚文件到特定版本

        Args:
            file_path: 文件路径
            target_hash: 目标哈希值（前缀匹配）
            backup_current: 是否备份当前版本

        Returns:
            是否成功回滚
        """
        # 查找目标版本
        history = self.find_file_versions(file_path)
        target_asset = None

        for asset in history:
            if asset["hash"].startswith(target_hash):
                target_asset = asset
                break

        if not target_asset:
            print(f"Version not found with hash: {target_hash}")
            return False

        file_path = Path(file_path)

        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        # 备份当前版本
        if backup_current and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            shutil.copy2(file_path, backup_path)
            print(f"Backed up current version to: {backup_path}")

        # 验证目标文件存在且哈希匹配
        current_hash = self.tracker._compute_file_hash(file_path)

        if current_hash == target_asset["hash"]:
            print(f"File is already at target version: {target_hash[:16]}")
            return True

        # 实际上，由于我们只记录哈希，无法直接恢复
        # 需要从备份或快照中恢复
        print(f"Cannot rollback: file content not stored in version control.")
        print(
            f"Use restore_snapshot() to restore from a snapshot containing this version."
        )

        return False

    def generate_integrity_report(
        self,
        output_path: Optional[str] = None,
    ) -> str:
        """
        生成完整性报告

        Args:
            output_path: 输出文件路径（可选）

        Returns:
            报告文本
        """
        results = self.verify_all_assets()

        lines = []
        lines.append("=" * 80)
        lines.append("DATA INTEGRITY REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Verified at: {results['verified_at']}")
        lines.append(f"Total assets: {results['total_assets']}")
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(
            f"  Valid:     {results['summary']['valid']} ({results['summary']['valid_pct']:.1f}%)"
        )
        lines.append(f"  Corrupted: {results['summary']['corrupted']}")
        lines.append(f"  Missing:   {results['summary']['missing']}")
        lines.append("")

        if results["corrupted"]:
            lines.append("CORRUPTED FILES")
            lines.append("-" * 80)

            for item in results["corrupted"]:
                lines.append(f"  {item['file_path']}")
                lines.append(f"    Expected: {item['expected_hash']}")
                lines.append(f"    Actual:   {item['actual_hash']}")

            lines.append("")

        if results["missing"]:
            lines.append("MISSING FILES")
            lines.append("-" * 80)

            for file_path in results["missing"][:20]:
                lines.append(f"  {file_path}")

            if len(results["missing"]) > 20:
                lines.append(f"  ... and {len(results['missing']) - 20} more")

            lines.append("")

        lines.append("=" * 80)

        text = "\n".join(lines)

        if output_path:
            output_path = Path(output_path)

            if not output_path.is_absolute():
                output_path = self.project_root / output_path

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"Report saved to: {output_path}")

        return text


if __name__ == "__main__":
    # 示例用法
    project_root = r"D:\Dunna\Documents\hw-1"
    restorer = DataRestorer(project_root)

    # 验证所有资产
    # results = restorer.verify_all_assets()
    # print("\nIntegrity Report:")
    # print(f"  Valid: {results['summary']['valid']}")
    # print(f"  Corrupted: {results['summary']['corrupted']}")
    # print(f"  Missing: {results['summary']['missing']}")

    # 生成报告
    # report = restorer.generate_integrity_report("data_versioning/integrity_report.txt")
    # print(report)

    print("DataRestorer initialized. Use verify_all_assets() to check data integrity.")

"""
快照管理器

创建和管理数据时间点快照。
轻量级存储（只记录文件哈希和元数据，不复制大文件）。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from .version_tracker import VersionTracker


class SnapshotManager:
    """数据快照管理器"""

    def __init__(self, project_root: str, registry_path: Optional[str] = None):
        """
        初始化快照管理器

        Args:
            project_root: 项目根目录
            registry_path: 注册表 YAML 文件路径
        """
        self.project_root = Path(project_root)

        if registry_path is None:
            registry_path = self.project_root / "data_versioning" / "data_registry.yaml"

        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()
        self.tracker = VersionTracker(project_root, registry_path)

    def _load_registry(self) -> Dict[str, Any]:
        """加载数据注册表"""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {self.registry_path}")

        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_registry(self):
        """保存数据注册表"""
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.registry, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_categories: Optional[List[str]] = None,
        include_versions: Optional[List[str]] = None,
    ) -> str:
        """
        创建数据快照

        Args:
            name: 快照名称
            description: 快照描述
            tags: 标签列表（如 ['stable', 'paper-v1']）
            include_categories: 包含的数据类别（None 表示全部）
            include_versions: 包含的版本标签（None 表示全部）

        Returns:
            快照 ID
        """
        # 生成快照 ID
        timestamp = datetime.now()
        snapshot_id = f"snap_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 获取当前资产列表
        assets = self.registry.get('assets', [])

        # 过滤资产
        filtered_assets = []

        for asset in assets:
            # 类别过滤
            if include_categories and asset.get('category') not in include_categories:
                continue

            # 版本过滤
            if include_versions and asset.get('version_tag') not in include_versions:
                continue

            # 验证文件存在性
            file_path = self.project_root / asset['file_path']

            if not file_path.exists():
                print(f"Warning: File missing, skipping: {asset['file_path']}")
                continue

            filtered_assets.append({
                "asset_id": asset['asset_id'],
                "file_path": asset['file_path'],
                "hash": asset['hash'],
                "size_bytes": asset['size_bytes'],
                "category": asset.get('category'),
                "version_tag": asset.get('version_tag'),
            })

        # 计算快照统计
        total_size = sum(a['size_bytes'] for a in filtered_assets)

        # 创建快照条目
        snapshot = {
            "snapshot_id": snapshot_id,
            "name": name,
            "description": description,
            "created_at": timestamp.isoformat(),
            "tags": tags or [],
            "asset_count": len(filtered_assets),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "assets": filtered_assets,
        }

        # 添加到注册表
        if 'snapshots' not in self.registry:
            self.registry['snapshots'] = []

        self.registry['snapshots'].append(snapshot)
        self._save_registry()

        print(f"Created snapshot '{name}' ({snapshot_id})")
        print(f"  Assets: {len(filtered_assets)}")
        print(f"  Total size: {snapshot['total_size_mb']:.2f} MB")

        return snapshot_id

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        snapshots = self.registry.get('snapshots', [])

        return [
            {
                "snapshot_id": s['snapshot_id'],
                "name": s['name'],
                "created_at": s['created_at'],
                "asset_count": s['asset_count'],
                "total_size_mb": s['total_size_mb'],
                "tags": s.get('tags', []),
                "description": s.get('description'),
            }
            for s in snapshots
        ]

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """获取快照详情"""
        snapshots = self.registry.get('snapshots', [])

        for snapshot in snapshots:
            if snapshot['snapshot_id'] == snapshot_id:
                return snapshot

        return None

    def get_snapshot_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取快照"""
        snapshots = self.registry.get('snapshots', [])

        for snapshot in snapshots:
            if snapshot['name'] == name:
                return snapshot

        return None

    def tag_snapshot(self, snapshot_id: str, tag: str):
        """为快照添加标签"""
        snapshots = self.registry.get('snapshots', [])

        for snapshot in snapshots:
            if snapshot['snapshot_id'] == snapshot_id:
                if 'tags' not in snapshot:
                    snapshot['tags'] = []

                if tag not in snapshot['tags']:
                    snapshot['tags'].append(tag)
                    self._save_registry()
                    print(f"Tagged snapshot {snapshot_id} with '{tag}'")
                    return

        print(f"Snapshot not found: {snapshot_id}")

    def mark_milestone(
        self,
        milestone_name: str,
        snapshot_id: str,
        date: Optional[str] = None,
    ):
        """
        标记重要里程碑

        Args:
            milestone_name: 里程碑名称（必须在注册表中预定义）
            snapshot_id: 快照 ID
            date: 日期（默认为当前日期）
        """
        milestones = self.registry.get('milestones', [])

        for milestone in milestones:
            if milestone['name'] == milestone_name:
                milestone['snapshot_id'] = snapshot_id
                milestone['date'] = date or datetime.now().isoformat()
                self._save_registry()
                print(f"Marked milestone '{milestone_name}' at snapshot {snapshot_id}")
                return

        print(f"Milestone not found: {milestone_name}")
        print("Available milestones:", [m['name'] for m in milestones])

    def compare_snapshots(
        self,
        snapshot1_id: str,
        snapshot2_id: str,
    ) -> Dict[str, Any]:
        """
        对比两个快照

        Args:
            snapshot1_id: 第一个快照 ID
            snapshot2_id: 第二个快照 ID

        Returns:
            对比报告字典
        """
        snap1 = self.get_snapshot(snapshot1_id)
        snap2 = self.get_snapshot(snapshot2_id)

        if not snap1:
            raise ValueError(f"Snapshot not found: {snapshot1_id}")
        if not snap2:
            raise ValueError(f"Snapshot not found: {snapshot2_id}")

        # 构建资产字典（按路径索引）
        assets1 = {a['file_path']: a for a in snap1['assets']}
        assets2 = {a['file_path']: a for a in snap2['assets']}

        # 查找差异
        all_paths = set(assets1.keys()) | set(assets2.keys())

        added = []
        removed = []
        modified = []
        unchanged = []

        for path in all_paths:
            if path not in assets1:
                added.append(assets2[path])
            elif path not in assets2:
                removed.append(assets1[path])
            elif assets1[path]['hash'] != assets2[path]['hash']:
                modified.append({
                    "file_path": path,
                    "old_hash": assets1[path]['hash'][:16],
                    "new_hash": assets2[path]['hash'][:16],
                    "old_size": assets1[path]['size_bytes'],
                    "new_size": assets2[path]['size_bytes'],
                    "size_diff": assets2[path]['size_bytes'] - assets1[path]['size_bytes'],
                })
            else:
                unchanged.append(path)

        report = {
            "snapshot1": {
                "id": snapshot1_id,
                "name": snap1['name'],
                "created_at": snap1['created_at'],
            },
            "snapshot2": {
                "id": snapshot2_id,
                "name": snap2['name'],
                "created_at": snap2['created_at'],
            },
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified),
                "unchanged": len(unchanged),
            },
            "details": {
                "added": added,
                "removed": removed,
                "modified": modified,
            },
        }

        return report

    def verify_snapshot_integrity(self, snapshot_id: str) -> Dict[str, Any]:
        """
        验证快照中所有文件的完整性

        Args:
            snapshot_id: 快照 ID

        Returns:
            验证报告字典
        """
        snapshot = self.get_snapshot(snapshot_id)

        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        results = {
            "snapshot_id": snapshot_id,
            "verified_at": datetime.now().isoformat(),
            "valid": [],
            "corrupted": [],
            "missing": [],
        }

        for asset in snapshot['assets']:
            file_path = self.project_root / asset['file_path']

            if not file_path.exists():
                results["missing"].append(asset['file_path'])
                continue

            # 验证哈希
            verification = self.tracker.verify_file_integrity(asset['file_path'])

            if verification['status'] == 'valid':
                results["valid"].append(asset['file_path'])
            elif verification['status'] == 'corrupted':
                results["corrupted"].append({
                    "file_path": asset['file_path'],
                    "expected_hash": asset['hash'][:16],
                    "actual_hash": verification['current_hash'][:16],
                })

        results["summary"] = {
            "total": len(snapshot['assets']),
            "valid": len(results["valid"]),
            "corrupted": len(results["corrupted"]),
            "missing": len(results["missing"]),
        }

        return results

    def export_snapshot_manifest(
        self,
        snapshot_id: str,
        output_path: str,
        format: str = 'json',
    ):
        """
        导出快照清单

        Args:
            snapshot_id: 快照 ID
            output_path: 输出文件路径
            format: 导出格式（json 或 yaml）
        """
        snapshot = self.get_snapshot(snapshot_id)

        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
        elif format == 'yaml':
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(snapshot, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported format: {format}")

        print(f"Exported snapshot manifest to: {output_path}")

    def delete_snapshot(self, snapshot_id: str):
        """删除快照（仅删除元数据，不删除实际文件）"""
        snapshots = self.registry.get('snapshots', [])

        for i, snapshot in enumerate(snapshots):
            if snapshot['snapshot_id'] == snapshot_id:
                del snapshots[i]
                self._save_registry()
                print(f"Deleted snapshot: {snapshot_id}")
                return

        print(f"Snapshot not found: {snapshot_id}")


def create_initial_snapshot(project_root: str) -> str:
    """创建项目初始快照（便捷函数）"""
    manager = SnapshotManager(project_root)

    snapshot_id = manager.create_snapshot(
        name="initial_baseline",
        description="Project initial state - all registered data assets",
        tags=["baseline"],
    )

    # 标记为基线里程碑
    manager.mark_milestone("baseline", snapshot_id)

    return snapshot_id


if __name__ == '__main__':
    # 示例用法
    project_root = r"D:\Dunna\Documents\hw-1"
    manager = SnapshotManager(project_root)

    # 列出现有快照
    snapshots = manager.list_snapshots()
    print("Existing snapshots:")

    for snap in snapshots:
        print(f"  - {snap['name']} ({snap['snapshot_id']}): {snap['asset_count']} assets, {snap['total_size_mb']} MB")

    # 创建新快照
    # snapshot_id = manager.create_snapshot(
    #     name="v13_stable",
    #     description="V13 stable version for paper baseline",
    #     tags=["stable", "paper"],
    #     include_versions=["V13"],
    # )

    # 标记里程碑
    # manager.mark_milestone("v13_stable", snapshot_id)

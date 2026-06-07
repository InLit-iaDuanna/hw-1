"""
数据版本追踪器

自动追踪仿真结果、模型文件和配置文件的版本变化。
每次生成新数据时记录 hash、时间戳、元数据。
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


class VersionTracker:
    """数据版本追踪器"""

    def __init__(self, project_root: str, registry_path: Optional[str] = None):
        """
        初始化版本追踪器

        Args:
            project_root: 项目根目录
            registry_path: 注册表 YAML 文件路径，默认为 data_versioning/data_registry.yaml
        """
        self.project_root = Path(project_root)

        if registry_path is None:
            registry_path = self.project_root / "data_versioning" / "data_registry.yaml"

        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()

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

    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希值"""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """获取文件元数据"""
        stat = file_path.stat()

        return {
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

    def _categorize_file(self, file_path: Path) -> Optional[str]:
        """根据路径模式判断文件类别"""
        relative_path = file_path.relative_to(self.project_root).as_posix()

        for category, info in self.registry['categories'].items():
            patterns = info['patterns']

            for pattern in patterns:
                # 简单的 glob 匹配
                if self._match_pattern(relative_path, pattern):
                    return category

        return None

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """简单的 glob 模式匹配"""
        from fnmatch import fnmatch
        return fnmatch(path, pattern)

    def register_file(
        self,
        file_path: str,
        category: Optional[str] = None,
        version_tag: Optional[str] = None,
        experiment_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        注册单个数据文件

        Args:
            file_path: 文件路径（绝对或相对于 project_root）
            category: 数据类别（自动检测如果为 None）
            version_tag: 版本标签（如 V13, V19）
            experiment_id: 实验 ID
            description: 描述
            metadata: 额外元数据

        Returns:
            注册的资产条目
        """
        file_path = Path(file_path)

        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 计算哈希和元数据
        file_hash = self._compute_file_hash(file_path)
        file_metadata = self._get_file_metadata(file_path)

        # 自动分类
        if category is None:
            category = self._categorize_file(file_path)

        # 自动提取版本标签（从路径）
        if version_tag is None:
            version_tag = self._extract_version_tag(file_path)

        # 构建资产条目
        relative_path = file_path.relative_to(self.project_root).as_posix()

        asset = {
            "asset_id": f"{relative_path}_{file_hash[:8]}",
            "file_path": relative_path,
            "category": category or "unknown",
            "hash": file_hash,
            "size_bytes": file_metadata["size_bytes"],
            "registered_at": datetime.now().isoformat(),
            "modified_at": file_metadata["modified_time"],
            "version_tag": version_tag,
            "experiment_id": experiment_id,
            "description": description,
            "metadata": metadata or {},
        }

        # 检查是否已存在
        existing_assets = self.registry.get('assets', [])

        # 查找相同路径的资产
        same_path_assets = [a for a in existing_assets if a['file_path'] == relative_path]

        if same_path_assets:
            # 检查哈希是否相同
            if same_path_assets[-1]['hash'] == file_hash:
                print(f"File already registered with same hash: {relative_path}")
                return same_path_assets[-1]
            else:
                print(f"File changed, registering new version: {relative_path}")

        # 添加新资产
        if 'assets' not in self.registry:
            self.registry['assets'] = []

        self.registry['assets'].append(asset)
        self._save_registry()

        print(f"Registered: {relative_path} ({category})")
        return asset

    def _extract_version_tag(self, file_path: Path) -> Optional[str]:
        """从文件路径提取版本标签"""
        parts = file_path.parts

        for part in parts:
            # 匹配 v01, v13, V19 等
            if part.lower().startswith('v') and len(part) >= 3:
                # 提取版本号部分
                version_num = part[1:].split('_')[0]
                if version_num.isdigit():
                    return f"V{version_num.zfill(2)}"

        return None

    def register_directory(
        self,
        directory: str,
        category: Optional[str] = None,
        version_tag: Optional[str] = None,
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量注册目录中的文件

        Args:
            directory: 目录路径
            category: 数据类别
            version_tag: 版本标签
            recursive: 是否递归
            file_patterns: 文件模式列表（如 ['*.csv', '*.json']）

        Returns:
            注册的资产列表
        """
        directory = Path(directory)

        if not directory.is_absolute():
            directory = self.project_root / directory

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        assets = []

        if recursive:
            file_iter = directory.rglob('*')
        else:
            file_iter = directory.glob('*')

        for file_path in file_iter:
            if not file_path.is_file():
                continue

            # 文件模式过滤
            if file_patterns:
                if not any(file_path.match(pattern) for pattern in file_patterns):
                    continue

            try:
                asset = self.register_file(
                    str(file_path),
                    category=category,
                    version_tag=version_tag,
                )
                assets.append(asset)
            except Exception as e:
                print(f"Warning: Failed to register {file_path}: {e}")

        return assets

    def get_asset_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """根据路径获取资产"""
        file_path = Path(file_path)

        if file_path.is_absolute():
            file_path = file_path.relative_to(self.project_root)

        relative_path = file_path.as_posix()

        assets = self.registry.get('assets', [])

        # 返回最新版本
        for asset in reversed(assets):
            if asset['file_path'] == relative_path:
                return asset

        return None

    def get_assets_by_version(self, version_tag: str) -> List[Dict[str, Any]]:
        """获取特定版本的所有资产"""
        assets = self.registry.get('assets', [])
        return [a for a in assets if a.get('version_tag') == version_tag]

    def get_assets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """获取特定类别的所有资产"""
        assets = self.registry.get('assets', [])
        return [a for a in assets if a.get('category') == category]

    def verify_file_integrity(self, file_path: str) -> Dict[str, Any]:
        """
        验证文件完整性（对比哈希）

        Returns:
            验证结果字典
        """
        file_path = Path(file_path)

        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        asset = self.get_asset_by_path(str(file_path))

        if asset is None:
            return {
                "status": "not_registered",
                "message": "File not found in registry",
            }

        if not file_path.exists():
            return {
                "status": "missing",
                "message": "File does not exist",
                "registered_hash": asset['hash'],
            }

        current_hash = self._compute_file_hash(file_path)

        if current_hash == asset['hash']:
            return {
                "status": "valid",
                "message": "File integrity verified",
                "hash": current_hash,
            }
        else:
            return {
                "status": "corrupted",
                "message": "File hash mismatch",
                "registered_hash": asset['hash'],
                "current_hash": current_hash,
            }

    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """获取文件的历史版本"""
        file_path = Path(file_path)

        if file_path.is_absolute():
            file_path = file_path.relative_to(self.project_root)

        relative_path = file_path.as_posix()

        assets = self.registry.get('assets', [])
        return [a for a in assets if a['file_path'] == relative_path]

    def get_statistics(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        assets = self.registry.get('assets', [])

        if not assets:
            return {
                "total_assets": 0,
                "total_size_mb": 0,
                "categories": {},
                "versions": {},
            }

        total_size = sum(a['size_bytes'] for a in assets)

        # 按类别统计
        categories = {}
        for asset in assets:
            cat = asset.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        # 按版本统计
        versions = {}
        for asset in assets:
            ver = asset.get('version_tag')
            if ver:
                if ver not in versions:
                    versions[ver] = 0
                versions[ver] += 1

        return {
            "total_assets": len(assets),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "categories": categories,
            "versions": versions,
            "last_registered": assets[-1]['registered_at'] if assets else None,
        }


def auto_register_simulation_output(
    tracker: VersionTracker,
    output_file: str,
    version_tag: str,
    experiment_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
):
    """
    自动注册仿真输出文件（供仿真脚本调用）

    Args:
        tracker: VersionTracker 实例
        output_file: 输出文件路径
        version_tag: 版本标签
        experiment_id: 实验 ID
        params: 仿真参数
    """
    metadata = {}

    if params:
        metadata['params'] = params

    # 尝试从 Git 获取 commit hash
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=tracker.project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            metadata['git_commit'] = result.stdout.strip()
    except Exception:
        pass

    tracker.register_file(
        output_file,
        category='simulation_results',
        version_tag=version_tag,
        experiment_id=experiment_id,
        metadata=metadata,
    )


if __name__ == '__main__':
    # 示例用法
    project_root = r"D:\Dunna\Documents\hw-1"
    tracker = VersionTracker(project_root)

    # 注册单个文件
    # tracker.register_file("out/example_summary.json", version_tag="V13")

    # 批量注册目录
    # assets = tracker.register_directory("out", file_patterns=['*.csv', '*.json'])
    # print(f"Registered {len(assets)} assets")

    # 查看统计
    stats = tracker.get_statistics()
    print("Registry Statistics:")
    print(json.dumps(stats, indent=2))

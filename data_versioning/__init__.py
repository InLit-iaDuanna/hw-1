"""
hw-1 数据版本控制系统

类似 DVC 的轻量级数据版本控制，追踪仿真结果、模型文件、实验数据。
"""

from .version_tracker import VersionTracker, auto_register_simulation_output
from .data_differ import DataDiffer
from .snapshot_manager import SnapshotManager
from .restore_data import DataRestorer

__all__ = [
    'VersionTracker',
    'auto_register_simulation_output',
    'DataDiffer',
    'SnapshotManager',
    'DataRestorer',
]

__version__ = '1.0.0'

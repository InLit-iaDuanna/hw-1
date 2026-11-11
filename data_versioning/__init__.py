"""
hw-1 数据版本控制系统

类似 DVC 的轻量级数据版本控制，追踪仿真结果、模型文件、实验数据。
"""

from .data_differ import DataDiffer
from .restore_data import DataRestorer
from .snapshot_manager import SnapshotManager
from .version_tracker import VersionTracker, auto_register_simulation_output

__all__ = [
    "VersionTracker",
    "auto_register_simulation_output",
    "DataDiffer",
    "SnapshotManager",
    "DataRestorer",
]

__version__ = "1.0.0"

"""数据读写工具：CSV/JSON/pickle，带版本标记和元数据。

设计原则：
- 标准化数据存储格式（CSV 用于时间序列，JSON 用于参数/摘要）
- 自动添加版本和时间戳元数据
- 提供类型安全的加载接口
- 向后兼容现有版本的 CSV 格式

接口：
- save_timeseries_csv(path, data_dict, metadata) -> None
- load_timeseries_csv(path) -> tuple[dict, dict]  # (data, metadata)
- save_summary_json(path, summary, metadata) -> None
- load_summary_json(path) -> dict
- save_pickle(path, obj, metadata) -> None
- load_pickle(path) -> tuple[Any, dict]
"""

from __future__ import annotations

import csv
import json
import pickle
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_VERSION = "hw-1-v1.0"


def save_timeseries_csv(
    path: Path | str,
    data: dict[str, list | np.ndarray],
    *,
    metadata: dict[str, Any] | None = None,
    version: str = DEFAULT_VERSION,
) -> None:
    """保存时间序列数据为 CSV，元数据写入同名 .meta.json 文件。

    Args:
        path: CSV 文件路径
        data: 列名 -> 数据数组的字典，所有数组长度必须相同
        metadata: 可选元数据（参数、版本信息等）
        version: 数据格式版本号

    Example:
        >>> save_timeseries_csv(
        ...     "out/sim_data.csv",
        ...     {"time": times, "hip_x": positions, "hip_z": heights},
        ...     metadata={"slope_deg": 2.5, "duration": 10.0}
        ... )
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not data:
        raise ValueError("数据字典为空")

    # 验证数据长度一致
    lengths = {k: len(v) for k, v in data.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"数据列长度不一致: {lengths}")

    # 转换为列表（处理 numpy 数组）
    rows_dict = {
        k: (v.tolist() if isinstance(v, np.ndarray) else list(v))
        for k, v in data.items()
    }
    n_rows = len(next(iter(rows_dict.values())))

    # 写入 CSV
    fieldnames = list(rows_dict.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n_rows):
            writer.writerow({k: rows_dict[k][i] for k in fieldnames})

    # 保存元数据
    if metadata is not None:
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        meta_content = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "csv_file": path.name,
            "n_rows": n_rows,
            "columns": fieldnames,
            "metadata": _serialize_for_json(metadata),
        }
        meta_path.write_text(
            json.dumps(meta_content, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def load_timeseries_csv(
    path: Path | str,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """加载 CSV 时间序列数据和元数据。

    Args:
        path: CSV 文件路径

    Returns:
        (数据字典, 元数据字典) 元组
        数据字典：列名 -> numpy 数组
        元数据字典：如果 .meta.json 文件存在则加载，否则返回空字典

    Example:
        >>> data, meta = load_timeseries_csv("out/sim_data.csv")
        >>> times = data["time"]
        >>> slope = meta.get("metadata", {}).get("slope_deg", 0.0)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {path}")

    # 读取 CSV
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {}, {}

    # 转换为 numpy 数组
    data = {key: np.array([float(row[key]) for row in rows]) for key in rows[0]}

    # 尝试加载元数据
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    metadata: dict[str, Any] = {}
    if meta_path.exists():
        # 元数据损坏时静默失败，不影响主数据加载
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}

    return data, metadata


def save_summary_json(
    path: Path | str,
    summary: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
    version: str = DEFAULT_VERSION,
) -> None:
    """保存摘要/参数字典为 JSON。

    Args:
        path: JSON 文件路径
        summary: 要保存的字典（支持嵌套、dataclass）
        metadata: 额外元数据（会合并到顶层）
        version: 数据格式版本号

    Example:
        >>> save_summary_json(
        ...     "out/summary.json",
        ...     {"score": 1234.5, "success": True, "params": params},
        ...     metadata={"git_hash": "a1b2c3d"}
        ... )
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        **_serialize_for_json(summary),
    }

    if metadata:
        content["metadata"] = _serialize_for_json(metadata)

    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def load_summary_json(path: Path | str) -> dict[str, Any]:
    """加载 JSON 摘要文件。

    Args:
        path: JSON 文件路径

    Returns:
        解析后的字典
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_pickle(
    path: Path | str,
    obj: Any,
    *,
    metadata: dict[str, Any] | None = None,
    version: str = DEFAULT_VERSION,
) -> None:
    """保存 Python 对象为 pickle，元数据写入同名 .meta.json。

    Args:
        path: pickle 文件路径
        obj: 要序列化的对象
        metadata: 可选元数据
        version: 数据格式版本号

    Note:
        pickle 不跨 Python 版本保证兼容性，仅用于临时缓存。
        长期存储优先使用 CSV/JSON。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)

    # 保存元数据
    if metadata is not None:
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        meta_content = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "pickle_file": path.name,
            "object_type": type(obj).__name__,
            "metadata": _serialize_for_json(metadata),
        }
        meta_path.write_text(
            json.dumps(meta_content, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def load_pickle(path: Path | str) -> tuple[Any, dict[str, Any]]:
    """加载 pickle 文件和元数据。

    Args:
        path: pickle 文件路径

    Returns:
        (反序列化对象, 元数据字典) 元组
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"pickle 文件不存在: {path}")

    with path.open("rb") as f:
        obj = pickle.load(f)

    # 尝试加载元数据
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    metadata: dict[str, Any] = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}

    return obj, metadata


def ensure_output_dir(base_dir: Path | str, subdir: str = "") -> Path:
    """确保输出目录存在，返回绝对路径。

    Args:
        base_dir: 基础输出目录
        subdir: 可选子目录名

    Returns:
        创建后的目录路径（绝对路径）
    """
    path = Path(base_dir)
    if subdir:
        path = path / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


# ============================================================================
# 内部辅助函数
# ============================================================================


def _serialize_for_json(obj: Any) -> Any:
    """递归转换对象为 JSON 可序列化格式。

    处理：
    - dataclass -> dict
    - numpy 数组/标量 -> list/float
    - Path -> str
    - 其他自定义类 -> str(obj)
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if is_dataclass(obj) and not isinstance(obj, type):
        return _serialize_for_json(asdict(obj))

    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, np.generic):
        return obj.item()

    if isinstance(obj, Path):
        return str(obj)

    # 未知类型转为字符串（保留调试信息）
    return str(obj)


def save_to_database(
    data: dict[str, Any],
    db_path: Path | str | None = None,
    version_name: str | None = None,
) -> int | None:
    """将仿真结果保存到数据库（可选功能）。

    需要 data_storage 模块。如果未安装或数据库不存在，则静默跳过。

    Args:
        data: 仿真结果字典（包含 params, score, forward_distance 等）
        db_path: 数据库路径（默认：项目根目录下的 data_storage/hw1_data.db）
        version_name: 版本名称（默认：从环境或上下文推断）

    Returns:
        仿真 ID（sim_id），如果未保存则返回 None

    Example:
        >>> save_to_database(
        ...     {"params": {...}, "score": 1234, "forward_distance": 4.5, ...},
        ...     version_name="V10"
        ... )
    """
    try:
        # 延迟导入，避免强依赖
        from data_storage import get_connection, import_summary_json
        import tempfile
        import json

        if db_path is None:
            # 默认数据库路径
            db_path = Path(__file__).parent.parent / "data_storage" / "hw1_data.db"

        db_path = Path(db_path)
        if not db_path.exists():
            return None  # 数据库不存在，跳过

        if version_name is None:
            return None  # 需要版本名称

        # 创建临时 JSON 文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path = f.name

        try:
            conn = get_connection(db_path)
            sim_id = import_summary_json(
                conn, version_name, temp_path, sim_type="auto_saved"
            )
            conn.close()
            return sim_id
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    except (ImportError, Exception):
        # 模块未安装或其他错误，静默跳过
        return None


__all__ = [
    "save_timeseries_csv",
    "load_timeseries_csv",
    "save_summary_json",
    "load_summary_json",
    "save_pickle",
    "load_pickle",
    "ensure_output_dir",
    "save_to_database",
]

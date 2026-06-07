"""数据导入工具：从现有 CSV/JSON 文件批量导入到数据库

支持的导入模式：
1. 扫描结果 CSV（参数扫描，多行仿真）
2. 摘要 JSON（单次仿真结果）
3. 时间序列 CSV（完整轨迹数据，可选）
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .db_schema import add_version, get_version_id


def import_scan_csv(
    conn: sqlite3.Connection,
    version_name: str,
    csv_path: Path | str,
    sim_type: str = "param_scan",
) -> int:
    """从参数扫描 CSV 导入批量仿真数据。

    CSV 格式要求：
    - 必须包含参数列和结果列
    - 必须列：score, alternating_touchdowns, forward_distance, simulated_time, failure

    Args:
        conn: 数据库连接
        version_name: 版本名称（如 "V07"）
        csv_path: CSV 文件路径
        sim_type: 仿真类型标签

    Returns:
        导入的仿真数量
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    # 确保版本存在
    version_id = get_version_id(conn, version_name)
    if version_id is None:
        version_id = add_version(
            conn, version_name, description=f"从 {csv_path.name} 导入"
        )

    # 读取 CSV
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return 0

    # 识别参数列和结果列
    result_cols = {
        "score",
        "alternating_touchdowns",
        "forward_distance",
        "simulated_time",
        "failure",
        "active_input_energy_j",
        "net_actuator_work_j",
        "CoT",
        "quasi_passive",
        "pure_passive",
    }
    param_cols = [col for col in rows[0].keys() if col not in result_cols]

    cursor = conn.cursor()
    count = 0

    for row in rows:
        # 构造参数 JSON
        params = {col: _parse_value(row[col]) for col in param_cols if col in row}

        # 解析结果字段
        success = 1 if row.get("failure", "fall_down") == "completed" else 0
        failure_reason = row.get("failure", "unknown")

        # 准备插入数据
        insert_data = {
            "version_id": version_id,
            "sim_type": sim_type,
            "params_json": json.dumps(params),
            "success": success,
            "failure_reason": failure_reason if not success else None,
            "forward_distance": _parse_float(row.get("forward_distance")),
            "alternating_touchdowns": _parse_int(row.get("alternating_touchdowns")),
            "simulated_time": _parse_float(row.get("simulated_time")),
            "score": _parse_float(row.get("score")),
            "active_input_energy_j": _parse_float(row.get("active_input_energy_j")),
            "net_actuator_work_j": _parse_float(row.get("net_actuator_work_j")),
            "CoT": _parse_float(row.get("CoT")),
            "quasi_passive": _parse_int(row.get("quasi_passive", "0")),
            "pure_passive": _parse_int(row.get("pure_passive", "0")),
            "timestamp": datetime.now().isoformat(),
            "csv_file": csv_path.name,
        }

        cursor.execute(
            """
            INSERT INTO simulations (
                version_id, sim_type, params_json, success, failure_reason,
                forward_distance, alternating_touchdowns, simulated_time, score,
                active_input_energy_j, net_actuator_work_j, CoT,
                quasi_passive, pure_passive, timestamp, csv_file
            ) VALUES (
                :version_id, :sim_type, :params_json, :success, :failure_reason,
                :forward_distance, :alternating_touchdowns, :simulated_time, :score,
                :active_input_energy_j, :net_actuator_work_j, :CoT,
                :quasi_passive, :pure_passive, :timestamp, :csv_file
            )
        """,
            insert_data,
        )
        count += 1

    conn.commit()
    return count


def import_summary_json(
    conn: sqlite3.Connection,
    version_name: str,
    json_path: Path | str,
    sim_type: str = "single_run",
) -> int:
    """从摘要 JSON 导入单次仿真结果。

    JSON 格式要求：
    - 包含 params 字典
    - 包含结果字段（score, forward_distance, failure 等）

    Args:
        conn: 数据库连接
        version_name: 版本名称
        json_path: JSON 文件路径
        sim_type: 仿真类型标签

    Returns:
        仿真 ID
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {json_path}")

    # 确保版本存在
    version_id = get_version_id(conn, version_name)
    if version_id is None:
        version_id = add_version(
            conn, version_name, description=f"从 {json_path.name} 导入"
        )

    # 读取 JSON
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取参数
    params = data.get("params", {})

    # 解析结果
    success = 1 if data.get("failure", "fall_down") == "completed" else 0
    failure_reason = data.get("failure", "unknown")

    cursor = conn.cursor()
    insert_data = {
        "version_id": version_id,
        "sim_type": sim_type,
        "params_json": json.dumps(params),
        "success": success,
        "failure_reason": failure_reason if not success else None,
        "forward_distance": data.get("forward_distance"),
        "alternating_touchdowns": data.get("alternating_touchdowns"),
        "simulated_time": data.get("simulated_time"),
        "score": data.get("score"),
        "active_input_energy_j": data.get("active_input_energy_j"),
        "net_actuator_work_j": data.get("net_actuator_work_j"),
        "CoT": data.get("CoT"),
        "quasi_passive": 1 if data.get("quasi_passive", False) else 0,
        "pure_passive": 1 if data.get("pure_passive", False) else 0,
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        "json_file": json_path.name,
    }

    cursor.execute(
        """
        INSERT INTO simulations (
            version_id, sim_type, params_json, success, failure_reason,
            forward_distance, alternating_touchdowns, simulated_time, score,
            active_input_energy_j, net_actuator_work_j, CoT,
            quasi_passive, pure_passive, timestamp, json_file
        ) VALUES (
            :version_id, :sim_type, :params_json, :success, :failure_reason,
            :forward_distance, :alternating_touchdowns, :simulated_time, :score,
            :active_input_energy_j, :net_actuator_work_j, :CoT,
            :quasi_passive, :pure_passive, :timestamp, :json_file
        )
    """,
        insert_data,
    )

    conn.commit()
    return cursor.lastrowid


def import_version_batch(
    conn: sqlite3.Connection,
    version_name: str,
    version_dir: Path | str,
    patterns: dict[str, str] | None = None,
) -> dict[str, int]:
    """批量导入一个版本目录下的所有数据文件。

    Args:
        conn: 数据库连接
        version_name: 版本名称
        version_dir: 版本目录路径（如 v08_quasi_passive_assisted）
        patterns: 文件匹配模式（默认：扫描 out/ 目录）

    Returns:
        导入统计 {"scan_csv": count, "summary_json": count}
    """
    version_dir = Path(version_dir)
    out_dir = version_dir / "out"

    if not out_dir.exists():
        raise FileNotFoundError(f"输出目录不存在: {out_dir}")

    stats = {"scan_csv": 0, "summary_json": 0}

    # 导入扫描 CSV
    for csv_file in out_dir.glob("*scan_results.csv"):
        try:
            count = import_scan_csv(conn, version_name, csv_file, sim_type="param_scan")
            stats["scan_csv"] += count
            print(f"  导入 {csv_file.name}: {count} 条仿真记录")
        except Exception as e:
            print(f"  警告：导入 {csv_file.name} 失败: {e}")

    # 导入摘要 JSON
    for json_file in out_dir.glob("*summary.json"):
        try:
            sim_id = import_summary_json(
                conn, version_name, json_file, sim_type="single_run"
            )
            stats["summary_json"] += 1
            print(f"  导入 {json_file.name}: sim_id={sim_id}")
        except Exception as e:
            print(f"  警告：导入 {json_file.name} 失败: {e}")

    return stats


def import_benchmark_table(
    conn: sqlite3.Connection,
    csv_path: Path | str,
) -> int:
    """从性能对比表 CSV 导入基准数据。

    CSV 格式：version, label, mass_kg, distance_m, CoT, ...

    Args:
        conn: 数据库连接
        csv_path: 基准表 CSV 路径

    Returns:
        导入的基准数量
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    cursor = conn.cursor()
    count = 0

    for row in rows:
        version_name = row.get("version", "").strip()
        if not version_name:
            continue

        # 确保版本存在
        version_id = get_version_id(conn, version_name)
        if version_id is None:
            version_id = add_version(
                conn,
                version_name,
                description=row.get("label", ""),
            )

        # 导入关键指标
        metrics = [
            ("mass_kg", row.get("mass_kg"), "kg"),
            ("distance_m", row.get("distance_m"), "m"),
            ("CoT", row.get("CoT"), "dimensionless"),
            ("active_input_energy_j", row.get("active_input_energy_j"), "J"),
            ("alternating_touchdowns", row.get("alternating_touchdowns"), "count"),
        ]

        for metric_name, value_str, unit in metrics:
            value = _parse_float(value_str)
            if value is not None:
                cursor.execute(
                    """
                    INSERT INTO benchmarks (
                        version_id, metric_name, metric_value, metric_unit,
                        benchmark_date, conditions_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        version_id,
                        metric_name,
                        value,
                        unit,
                        datetime.now().isoformat(),
                        json.dumps({"label": row.get("label", "")}),
                    ),
                )
                count += 1

    conn.commit()
    return count


# ============================================================================
# 辅助函数
# ============================================================================


def _parse_value(s: str) -> Any:
    """尝试解析字符串为数值或保留字符串。"""
    s = s.strip()
    if not s:
        return None

    # 尝试整数
    try:
        return int(s)
    except ValueError:
        pass

    # 尝试浮点数
    try:
        return float(s)
    except ValueError:
        pass

    # 保留字符串
    return s


def _parse_float(s: str | None) -> float | None:
    """解析浮点数，失败返回 None。"""
    if s is None or s == "":
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_int(s: str | None) -> int | None:
    """解析整数，失败返回 None。"""
    if s is None or s == "":
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


__all__ = [
    "import_scan_csv",
    "import_summary_json",
    "import_version_batch",
    "import_benchmark_table",
]

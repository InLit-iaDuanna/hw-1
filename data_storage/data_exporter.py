"""数据导出工具：从数据库导出数据为 CSV/JSON

支持：
- 导出查询结果为 CSV
- 导出特定仿真为 JSON
- 批量导出版本数据
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from .query_interface import query_simulations, query_timeseries


def export_simulations_csv(
    conn: sqlite3.Connection,
    output_path: Path | str,
    version_name: str | None = None,
    **query_kwargs,
) -> int:
    """导出仿真数据为 CSV。

    Args:
        conn: 数据库连接
        output_path: 输出 CSV 路径
        version_name: 版本名称过滤
        **query_kwargs: 传递给 query_simulations 的其他参数

    Returns:
        导出的行数
    """
    df = query_simulations(conn, version_name=version_name, **query_kwargs)

    if df.empty:
        print("没有数据可导出")
        return 0

    # 展平参数 JSON 为列
    if "params" in df.columns:
        params_df = pd.json_normalize(df["params"])
        params_df.columns = [f"param_{col}" for col in params_df.columns]
        df = pd.concat([df.drop(columns=["params", "params_json"]), params_df], axis=1)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"已导出 {len(df)} 条记录到 {output_path}")
    return len(df)


def export_simulation_json(
    conn: sqlite3.Connection,
    sim_id: int,
    output_path: Path | str,
) -> None:
    """导出单个仿真为 JSON（兼容原始格式）。

    Args:
        conn: 数据库连接
        sim_id: 仿真 ID
        output_path: 输出 JSON 路径
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            v.version_name,
            s.*
        FROM simulations s
        JOIN versions v ON s.version_id = v.version_id
        WHERE s.sim_id = ?
    """,
        (sim_id,),
    )

    row = cursor.fetchone()
    if not row:
        raise ValueError(f"仿真 ID {sim_id} 不存在")

    row_dict = dict(row)

    # 重构为原始 JSON 格式
    output_data = {
        "version": row_dict["version_name"],
        "sim_id": sim_id,
        "params": json.loads(row_dict["params_json"]),
        "score": row_dict["score"],
        "forward_distance": row_dict["forward_distance"],
        "alternating_touchdowns": row_dict["alternating_touchdowns"],
        "simulated_time": row_dict["simulated_time"],
        "failure": row_dict["failure_reason"] or "completed",
        "active_input_energy_j": row_dict["active_input_energy_j"],
        "net_actuator_work_j": row_dict["net_actuator_work_j"],
        "CoT": row_dict["CoT"],
        "quasi_passive": bool(row_dict["quasi_passive"]),
        "pure_passive": bool(row_dict["pure_passive"]),
        "timestamp": row_dict["timestamp"],
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"已导出仿真 {sim_id} 到 {output_path}")


def export_timeseries_csv(
    conn: sqlite3.Connection,
    sim_id: int,
    output_path: Path | str,
) -> int:
    """导出时间序列数据为 CSV。

    Args:
        conn: 数据库连接
        sim_id: 仿真 ID
        output_path: 输出 CSV 路径

    Returns:
        导出的行数
    """
    df = query_timeseries(conn, sim_id)

    if df.empty:
        print(f"仿真 {sim_id} 没有时间序列数据")
        return 0

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"已导出 {len(df)} 个时间步到 {output_path}")
    return len(df)


__all__ = [
    "export_simulations_csv",
    "export_simulation_json",
    "export_timeseries_csv",
]

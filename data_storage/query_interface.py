"""查询接口：高级数据检索和分析功能

提供便捷的查询 API，支持：
- 按版本查询
- 按性能指标筛选
- 参数范围过滤
- 版本对比
- 最佳性能查询
"""

from __future__ import annotations

import json
import sqlite3

import pandas as pd


def query_simulations(
    conn: sqlite3.Connection,
    version_name: str | None = None,
    success_only: bool = False,
    min_score: float | None = None,
    max_cot: float | None = None,
    min_distance: float | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """查询仿真数据，返回 Pandas DataFrame。

    Args:
        conn: 数据库连接
        version_name: 版本名称过滤（None = 所有版本）
        success_only: 仅返回成功的仿真
        min_score: 最小分数过滤
        max_cot: 最大 CoT 过滤
        min_distance: 最小前进距离过滤
        limit: 返回结果数量限制

    Returns:
        包含仿真数据的 DataFrame
    """
    query = """
        SELECT
            s.sim_id,
            v.version_name,
            s.sim_type,
            s.params_json,
            s.success,
            s.failure_reason,
            s.forward_distance,
            s.alternating_touchdowns,
            s.simulated_time,
            s.score,
            s.active_input_energy_j,
            s.net_actuator_work_j,
            s.CoT,
            s.quasi_passive,
            s.pure_passive,
            s.timestamp,
            s.csv_file,
            s.json_file
        FROM simulations s
        JOIN versions v ON s.version_id = v.version_id
        WHERE 1=1
    """

    params = []

    if version_name:
        query += " AND v.version_name = ?"
        params.append(version_name)

    if success_only:
        query += " AND s.success = 1"

    if min_score is not None:
        query += " AND s.score >= ?"
        params.append(min_score)

    if max_cot is not None:
        query += " AND s.CoT <= ?"
        params.append(max_cot)

    if min_distance is not None:
        query += " AND s.forward_distance >= ?"
        params.append(min_distance)

    query += " ORDER BY s.timestamp DESC"

    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, conn, params=params)

    # 解析参数 JSON
    if not df.empty and "params_json" in df.columns:
        df["params"] = df["params_json"].apply(lambda x: json.loads(x) if x else {})

    return df


def get_best_simulations(
    conn: sqlite3.Connection,
    metric: str = "score",
    top_n: int = 10,
    version_name: str | None = None,
    success_only: bool = True,
) -> pd.DataFrame:
    """获取性能最佳的仿真。

    Args:
        conn: 数据库连接
        metric: 排序指标（"score", "CoT", "forward_distance"）
        top_n: 返回前 N 个结果
        version_name: 版本名称过滤
        success_only: 仅考虑成功的仿真

    Returns:
        排序后的 DataFrame
    """
    valid_metrics = {
        "score": "DESC",
        "CoT": "ASC",
        "forward_distance": "DESC",
        "alternating_touchdowns": "DESC",
    }

    if metric not in valid_metrics:
        raise ValueError(f"无效指标：{metric}，支持：{list(valid_metrics.keys())}")

    order = valid_metrics[metric]

    query = f"""
        SELECT
            s.sim_id,
            v.version_name,
            s.sim_type,
            s.params_json,
            s.forward_distance,
            s.alternating_touchdowns,
            s.score,
            s.CoT,
            s.active_input_energy_j,
            s.timestamp
        FROM simulations s
        JOIN versions v ON s.version_id = v.version_id
        WHERE s.{metric} IS NOT NULL
    """

    params = []

    if success_only:
        query += " AND s.success = 1"

    if version_name:
        query += " AND v.version_name = ?"
        params.append(version_name)

    query += f" ORDER BY s.{metric} {order} LIMIT {top_n}"

    df = pd.read_sql_query(query, conn, params=params)

    if not df.empty and "params_json" in df.columns:
        df["params"] = df["params_json"].apply(lambda x: json.loads(x) if x else {})

    return df


def compare_versions(
    conn: sqlite3.Connection,
    version_names: list[str],
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    """对比多个版本的性能指标。

    Args:
        conn: 数据库连接
        version_names: 要对比的版本名称列表
        metrics: 要对比的指标（None = 所有指标）

    Returns:
        对比结果 DataFrame（版本 x 指标）
    """
    if metrics is None:
        metrics = [
            "forward_distance",
            "alternating_touchdowns",
            "CoT",
            "active_input_energy_j",
            "score",
        ]

    results = []

    for version_name in version_names:
        query = """
            SELECT
                v.version_name,
                COUNT(*) as total_sims,
                SUM(s.success) as successful_sims,
                AVG(s.forward_distance) as avg_distance,
                MAX(s.forward_distance) as max_distance,
                AVG(s.alternating_touchdowns) as avg_touchdowns,
                MAX(s.alternating_touchdowns) as max_touchdowns,
                AVG(s.CoT) as avg_cot,
                MIN(s.CoT) as min_cot,
                AVG(s.score) as avg_score,
                MAX(s.score) as max_score
            FROM simulations s
            JOIN versions v ON s.version_id = v.version_id
            WHERE v.version_name = ?
            GROUP BY v.version_name
        """

        cursor = conn.cursor()
        cursor.execute(query, (version_name,))
        row = cursor.fetchone()

        if row:
            results.append(dict(row))

    return pd.DataFrame(results)


def query_by_param_range(
    conn: sqlite3.Connection,
    param_name: str,
    min_value: float,
    max_value: float,
    version_name: str | None = None,
) -> pd.DataFrame:
    """按参数范围查询仿真。

    Args:
        conn: 数据库连接
        param_name: 参数名称（如 "slope_deg"）
        min_value: 参数最小值
        max_value: 参数最大值
        version_name: 版本名称过滤

    Returns:
        匹配的仿真 DataFrame
    """
    # SQLite JSON 查询
    query = """
        SELECT
            s.sim_id,
            v.version_name,
            s.params_json,
            s.forward_distance,
            s.score,
            s.CoT,
            s.success
        FROM simulations s
        JOIN versions v ON s.version_id = v.version_id
        WHERE json_extract(s.params_json, ?) >= ?
          AND json_extract(s.params_json, ?) <= ?
    """

    params = [f"$.{param_name}", min_value, f"$.{param_name}", max_value]

    if version_name:
        query += " AND v.version_name = ?"
        params.append(version_name)

    df = pd.read_sql_query(query, conn, params=params)

    if not df.empty and "params_json" in df.columns:
        df["params"] = df["params_json"].apply(lambda x: json.loads(x) if x else {})
        df[param_name] = df["params"].apply(lambda p: p.get(param_name))

    return df


def get_version_summary(conn: sqlite3.Connection) -> pd.DataFrame:
    """获取所有版本的摘要统计。

    Returns:
        版本摘要 DataFrame
    """
    query = """
        SELECT
            v.version_name,
            v.description,
            v.created_date,
            COUNT(s.sim_id) as total_simulations,
            SUM(s.success) as successful_simulations,
            ROUND(AVG(s.forward_distance), 3) as avg_distance_m,
            ROUND(MAX(s.forward_distance), 3) as max_distance_m,
            ROUND(AVG(CASE WHEN s.success = 1 THEN s.CoT END), 5) as avg_cot_success,
            ROUND(MIN(CASE WHEN s.success = 1 THEN s.CoT END), 5) as min_cot_success
        FROM versions v
        LEFT JOIN simulations s ON v.version_id = s.version_id
        GROUP BY v.version_id
        ORDER BY v.created_date DESC
    """

    return pd.read_sql_query(query, conn)


def get_benchmark_summary(conn: sqlite3.Connection) -> pd.DataFrame:
    """获取所有版本的基准性能对比。

    Returns:
        基准性能 DataFrame（透视表格式）
    """
    query = """
        SELECT
            v.version_name,
            b.metric_name,
            b.metric_value,
            b.metric_unit
        FROM benchmarks b
        JOIN versions v ON b.version_id = v.version_id
        ORDER BY v.version_name, b.metric_name
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        return df

    # 透视为版本 x 指标格式
    pivot = df.pivot_table(
        index="version_name",
        columns="metric_name",
        values="metric_value",
        aggfunc="first",
    )

    return pivot


def query_timeseries(
    conn: sqlite3.Connection,
    sim_id: int,
) -> pd.DataFrame:
    """查询特定仿真的时间序列数据。

    Args:
        conn: 数据库连接
        sim_id: 仿真 ID

    Returns:
        时间序列 DataFrame
    """
    query = """
        SELECT
            time,
            hip_x,
            hip_z,
            hip_vx,
            hip_vz,
            joint_angles_json,
            joint_velocities_json,
            contact_forces_json
        FROM timeseries
        WHERE sim_id = ?
        ORDER BY time
    """

    df = pd.read_sql_query(query, conn, params=(sim_id,))

    # 解析 JSON 列
    for col in ["joint_angles_json", "joint_velocities_json", "contact_forces_json"]:
        if col in df.columns:
            df[col.replace("_json", "")] = df[col].apply(
                lambda x: json.loads(x) if x else {}
            )

    return df


__all__ = [
    "query_simulations",
    "get_best_simulations",
    "compare_versions",
    "query_by_param_range",
    "get_version_summary",
    "get_benchmark_summary",
    "query_timeseries",
]

"""数据库表结构定义

SQLite 数据库设计：
- versions: 版本元数据
- simulations: 仿真运行记录（参数扫描结果、单次运行）
- timeseries: 时间序列数据（可选，用于关键仿真的完整轨迹）
- benchmarks: 性能基准测试结果
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_VERSION = "1.0"


def create_database(db_path: Path | str) -> None:
    """创建数据库并初始化所有表结构。

    Args:
        db_path: SQLite 数据库文件路径
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON")

    # 版本表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS versions (
            version_id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_date TEXT NOT NULL,
            git_hash TEXT,
            notes TEXT
        )
    """)

    # 仿真表（核心数据）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            sim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL,
            sim_type TEXT NOT NULL,
            params_json TEXT NOT NULL,
            success INTEGER NOT NULL,
            failure_reason TEXT,
            forward_distance REAL,
            alternating_touchdowns INTEGER,
            simulated_time REAL,
            score REAL,
            active_input_energy_j REAL,
            net_actuator_work_j REAL,
            CoT REAL,
            quasi_passive INTEGER DEFAULT 0,
            pure_passive INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            csv_file TEXT,
            json_file TEXT,
            FOREIGN KEY (version_id) REFERENCES versions(version_id)
        )
    """)

    # 时间序列数据表（可选，仅存储关键仿真）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeseries (
            ts_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sim_id INTEGER NOT NULL,
            time REAL NOT NULL,
            hip_x REAL,
            hip_z REAL,
            hip_vx REAL,
            hip_vz REAL,
            joint_angles_json TEXT,
            joint_velocities_json TEXT,
            contact_forces_json TEXT,
            FOREIGN KEY (sim_id) REFERENCES simulations(sim_id)
        )
    """)

    # 性能基准表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            benchmark_date TEXT NOT NULL,
            conditions_json TEXT,
            notes TEXT,
            FOREIGN KEY (version_id) REFERENCES versions(version_id)
        )
    """)

    # 创建索引以优化查询
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_version
        ON simulations(version_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_success
        ON simulations(success)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_score
        ON simulations(score DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_cot
        ON simulations(CoT)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_timestamp
        ON simulations(timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ts_sim
        ON timeseries(sim_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ts_time
        ON timeseries(sim_id, time)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_benchmark_version
        ON benchmarks(version_id)
    """)

    # 存储数据库元数据
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute(
        """
        INSERT OR REPLACE INTO db_metadata (key, value)
        VALUES ('db_version', ?), ('created', datetime('now'))
    """,
        (DB_VERSION,),
    )

    conn.commit()
    conn.close()


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """获取数据库连接，启用外键约束和行工厂。

    Args:
        db_path: 数据库文件路径

    Returns:
        配置好的数据库连接
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # 允许字典式访问
    return conn


def add_version(
    conn: sqlite3.Connection,
    version_name: str,
    description: str = "",
    git_hash: str = "",
    notes: str = "",
) -> int:
    """添加新版本记录。

    Args:
        conn: 数据库连接
        version_name: 版本名称（如 "V08"）
        description: 版本描述
        git_hash: Git commit hash
        notes: 额外备注

    Returns:
        插入的 version_id
    """
    from datetime import datetime

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO versions (version_name, description, created_date, git_hash, notes)
        VALUES (?, ?, ?, ?, ?)
    """,
        (version_name, description, datetime.now().isoformat(), git_hash, notes),
    )

    conn.commit()
    return cursor.lastrowid


def get_version_id(conn: sqlite3.Connection, version_name: str) -> int | None:
    """获取版本 ID，如果不存在则返回 None。

    Args:
        conn: 数据库连接
        version_name: 版本名称

    Returns:
        version_id 或 None
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT version_id FROM versions WHERE version_name = ?", (version_name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


__all__ = [
    "DB_VERSION",
    "create_database",
    "get_connection",
    "add_version",
    "get_version_id",
]

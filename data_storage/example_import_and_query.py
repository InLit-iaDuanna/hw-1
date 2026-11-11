"""示例脚本：创建数据库、导入部分历史数据、验证查询功能

演示：
1. 创建数据库
2. 导入 V07-V12 版本数据
3. 导入性能对比表
4. 执行各种查询
5. 导出示例数据
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_storage import (
    create_database,
    get_connection,
    import_version_batch,
    import_benchmark_table,
    query_simulations,
    get_best_simulations,
    compare_versions,
    get_version_summary,
    get_benchmark_summary,
    query_by_param_range,
)


def main():
    # 设置 UTF-8 输出（Windows 兼容）
    import locale
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # 项目根目录
    hw1_root = Path(__file__).parent.parent
    db_path = Path(__file__).parent / "hw1_data.db"

    print("=" * 60)
    print("hw-1 数据存储系统 - 示例演示")
    print("=" * 60)

    # ========================================================================
    # 1. 创建数据库
    # ========================================================================
    print("\n[1] 创建数据库...")
    create_database(db_path)
    print(f"[OK] 数据库已创建: {db_path}")

    conn = get_connection(db_path)

    # ========================================================================
    # 2. 导入版本数据
    # ========================================================================
    print("\n[2] 导入版本数据...")

    # 导入关键版本（V07-V12）
    versions_to_import = [
        ("V07", "v07_true_contact_exploration"),
        ("V08", "v08_quasi_passive_assisted"),
        ("V09", "v09_stable_biomimetic_gait"),
        ("V10", "v10_rolling_foot_biomimetic_gait"),
        ("V11", "v11_rugged_terrain_robustness"),
        ("V12", "v12_energy_cot_analysis"),
    ]

    total_stats = {"scan_csv": 0, "summary_json": 0}

    for version_name, version_dir in versions_to_import:
        version_path = hw1_root / version_dir
        if not version_path.exists():
            print(f"  [SKIP] 跳过 {version_name}（目录不存在）")
            continue

        print(f"\n  导入 {version_name} ({version_dir})...")
        try:
            stats = import_version_batch(conn, version_name, version_path)
            total_stats["scan_csv"] += stats["scan_csv"]
            total_stats["summary_json"] += stats["summary_json"]
            print(
                f"  [OK] 扫描记录: {stats['scan_csv']}, 摘要: {stats['summary_json']}"
            )
        except Exception as e:
            print(f"  [ERROR] 导入失败: {e}")

    print(f"\n总计导入:")
    print(f"  - 参数扫描记录: {total_stats['scan_csv']}")
    print(f"  - 摘要记录: {total_stats['summary_json']}")

    # ========================================================================
    # 3. 导入性能对比表
    # ========================================================================
    print("\n[3] 导入性能对比表...")
    benchmark_csv = (
        hw1_root / "v12_energy_cot_analysis" / "out" / "v12_energy_cot_table.csv"
    )

    if benchmark_csv.exists():
        try:
            count = import_benchmark_table(conn, benchmark_csv)
            print(f"[OK] 导入 {count} 条基准数据")
        except Exception as e:
            print(f"[ERROR] 导入失败: {e}")
    else:
        print("[SKIP] 基准表文件不存在，跳过")

    # ========================================================================
    # 4. 查询示例
    # ========================================================================
    print("\n[4] 查询示例")
    print("=" * 60)

    # 4.1 版本摘要
    print("\n4.1 所有版本摘要:")
    print("-" * 60)
    summary = get_version_summary(conn)
    print(summary.to_string(index=False))

    # 4.2 最佳 CoT
    print("\n4.2 CoT 最低的前 5 个仿真:")
    print("-" * 60)
    best_cot = get_best_simulations(conn, metric="CoT", top_n=5, success_only=True)
    if not best_cot.empty:
        print(
            best_cot[
                ["version_name", "CoT", "forward_distance", "alternating_touchdowns"]
            ].to_string(index=False)
        )
    else:
        print("无数据")

    # 4.3 最高分数
    print("\n4.3 分数最高的前 5 个仿真:")
    print("-" * 60)
    best_score = get_best_simulations(conn, metric="score", top_n=5, success_only=True)
    if not best_score.empty:
        print(
            best_score[
                ["version_name", "score", "forward_distance", "alternating_touchdowns"]
            ].to_string(index=False)
        )
    else:
        print("无数据")

    # 4.4 版本对比
    print("\n4.4 版本性能对比:")
    print("-" * 60)
    versions_to_compare = ["V08", "V09", "V10"]
    comparison = compare_versions(conn, versions_to_compare)
    if not comparison.empty:
        print(comparison.to_string(index=False))
    else:
        print("无数据")

    # 4.5 基准性能对比
    print("\n4.5 基准性能对比（来自对比表）:")
    print("-" * 60)
    benchmarks = get_benchmark_summary(conn)
    if not benchmarks.empty:
        print(benchmarks.to_string())
    else:
        print("无基准数据")

    # 4.6 按参数范围查询
    print("\n4.6 查询坡度 3.0-4.0 度的仿真 (V07):")
    print("-" * 60)
    try:
        param_query = query_by_param_range(
            conn,
            param_name="slope_deg",
            min_value=3.0,
            max_value=4.0,
            version_name="V07",
        )
        if not param_query.empty:
            print(f"找到 {len(param_query)} 条记录")
            print(
                param_query[["sim_id", "slope_deg", "success", "forward_distance"]]
                .head(10)
                .to_string(index=False)
            )
        else:
            print("无数据")
    except Exception as e:
        print(f"查询失败: {e}")

    # 4.7 失败模式分析
    print("\n4.7 V07 失败模式统计:")
    print("-" * 60)
    v07_all = query_simulations(conn, version_name="V07")
    if not v07_all.empty:
        failures = v07_all[v07_all["success"] == 0]
        if not failures.empty:
            print(failures["failure_reason"].value_counts().to_string())
        else:
            print("所有仿真都成功")
    else:
        print("无 V07 数据")

    # ========================================================================
    # 5. 数据库统计
    # ========================================================================
    print("\n[5] 数据库统计")
    print("=" * 60)

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM versions")
    version_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM simulations")
    sim_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM simulations WHERE success = 1")
    success_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM benchmarks")
    benchmark_count = cursor.fetchone()[0]

    print(f"版本数: {version_count}")
    print(f"仿真总数: {sim_count}")
    print(
        f"成功仿真: {success_count} ({100*success_count/sim_count:.1f}%)"
        if sim_count > 0
        else "成功仿真: 0"
    )
    print(f"基准数据: {benchmark_count}")

    # ========================================================================
    # 完成
    # ========================================================================
    conn.close()

    print("\n" + "=" * 60)
    print("[OK] 示例演示完成")
    print(f"数据库位置: {db_path.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

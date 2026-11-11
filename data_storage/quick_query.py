"""快速查询工具：命令行界面

用法：
    python quick_query.py --best-cot 10              # 查找 CoT 最低的 10 个仿真
    python quick_query.py --best-score 5             # 查找分数最高的 5 个仿真
    python quick_query.py --compare V08 V09 V10      # 对比版本
    python quick_query.py --summary                  # 查看所有版本摘要
    python quick_query.py --version V10              # 查看特定版本
    python quick_query.py --param slope_deg 2 4      # 查询参数范围
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import io

from data_storage import (
    compare_versions,
    get_best_simulations,
    get_connection,
    get_version_summary,
    query_by_param_range,
    query_simulations,
)


def setup_encoding():
    """设置 UTF-8 输出（Windows 兼容）"""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main():
    setup_encoding()

    parser = argparse.ArgumentParser(
        description="hw-1 数据存储系统 - 快速查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db",
        type=str,
        default="data_storage/hw1_data.db",
        help="数据库路径（默认：data_storage/hw1_data.db）",
    )

    # 查询类型
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--best-cot",
        type=int,
        metavar="N",
        help="查找 CoT 最低的 N 个仿真",
    )
    group.add_argument(
        "--best-score",
        type=int,
        metavar="N",
        help="查找分数最高的 N 个仿真",
    )
    group.add_argument(
        "--best-distance",
        type=int,
        metavar="N",
        help="查找前进距离最远的 N 个仿真",
    )
    group.add_argument(
        "--compare",
        type=str,
        nargs="+",
        metavar="VERSION",
        help="对比多个版本（例如：V08 V09 V10）",
    )
    group.add_argument(
        "--summary",
        action="store_true",
        help="查看所有版本摘要",
    )
    group.add_argument(
        "--version",
        type=str,
        metavar="NAME",
        help="查看特定版本的所有仿真",
    )
    group.add_argument(
        "--param",
        type=str,
        nargs=3,
        metavar=("NAME", "MIN", "MAX"),
        help="按参数范围查询（例如：slope_deg 2.0 4.0）",
    )

    # 过滤选项
    parser.add_argument(
        "--success-only",
        action="store_true",
        help="仅显示成功的仿真",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="限制返回结果数量",
    )

    args = parser.parse_args()

    # 数据库路径
    db_path = Path(__file__).parent.parent / args.db
    if not db_path.exists():
        print(f"[ERROR] 数据库不存在: {db_path}")
        print("请先运行 example_import_and_query.py 创建数据库")
        sys.exit(1)

    conn = get_connection(db_path)

    try:
        # 执行查询
        if args.best_cot is not None:
            print(f"CoT 最低的前 {args.best_cot} 个仿真:")
            print("=" * 80)
            df = get_best_simulations(
                conn, metric="CoT", top_n=args.best_cot, success_only=args.success_only
            )
            if not df.empty:
                print(
                    df[
                        [
                            "sim_id",
                            "version_name",
                            "CoT",
                            "forward_distance",
                            "alternating_touchdowns",
                        ]
                    ].to_string(index=False)
                )
            else:
                print("无数据")

        elif args.best_score is not None:
            print(f"分数最高的前 {args.best_score} 个仿真:")
            print("=" * 80)
            df = get_best_simulations(
                conn,
                metric="score",
                top_n=args.best_score,
                success_only=args.success_only,
            )
            if not df.empty:
                print(
                    df[
                        [
                            "sim_id",
                            "version_name",
                            "score",
                            "forward_distance",
                            "alternating_touchdowns",
                        ]
                    ].to_string(index=False)
                )
            else:
                print("无数据")

        elif args.best_distance is not None:
            print(f"前进距离最远的前 {args.best_distance} 个仿真:")
            print("=" * 80)
            df = get_best_simulations(
                conn,
                metric="forward_distance",
                top_n=args.best_distance,
                success_only=args.success_only,
            )
            if not df.empty:
                print(
                    df[
                        [
                            "sim_id",
                            "version_name",
                            "forward_distance",
                            "alternating_touchdowns",
                            "score",
                        ]
                    ].to_string(index=False)
                )
            else:
                print("无数据")

        elif args.compare:
            print(f"版本对比: {', '.join(args.compare)}")
            print("=" * 80)
            df = compare_versions(conn, args.compare)
            if not df.empty:
                print(df.to_string(index=False))
            else:
                print("无数据")

        elif args.summary:
            print("所有版本摘要:")
            print("=" * 80)
            df = get_version_summary(conn)
            print(df.to_string(index=False))

        elif args.version:
            print(f"版本 {args.version} 的仿真:")
            print("=" * 80)
            df = query_simulations(
                conn,
                version_name=args.version,
                success_only=args.success_only,
                limit=args.limit,
            )
            if not df.empty:
                print(
                    df[
                        [
                            "sim_id",
                            "success",
                            "forward_distance",
                            "alternating_touchdowns",
                            "score",
                            "CoT",
                        ]
                    ].to_string(index=False)
                )
                print(f"\n总计: {len(df)} 条仿真")
            else:
                print("无数据")

        elif args.param:
            param_name, min_val, max_val = args.param
            min_val = float(min_val)
            max_val = float(max_val)
            print(f"参数 {param_name} 范围 [{min_val}, {max_val}] 的仿真:")
            print("=" * 80)
            df = query_by_param_range(conn, param_name, min_val, max_val)
            if not df.empty:
                if args.success_only:
                    df = df[df["success"] == 1]
                if args.limit:
                    df = df.head(args.limit)

                print(
                    df[
                        [
                            "sim_id",
                            "version_name",
                            param_name,
                            "success",
                            "forward_distance",
                            "score",
                        ]
                    ].to_string(index=False)
                )
                print(f"\n总计: {len(df)} 条仿真")
            else:
                print("无数据")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

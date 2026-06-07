"""data_io 模块使用示例。

展示 CSV、JSON、pickle 的保存和加载工作流。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 假设 common/ 在 PYTHONPATH 中，或从父目录导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.data_io import (
    load_summary_json,
    load_timeseries_csv,
    save_summary_json,
    save_timeseries_csv,
)


def example_1_save_and_load_timeseries():
    """示例 1：保存和加载时间序列数据。"""
    print("=== 示例 1：时间序列数据 ===")

    # 生成模拟数据
    times = np.linspace(0, 10, 1000)
    positions = np.sin(times) + 0.1 * np.random.randn(1000)
    velocities = np.cos(times) + 0.05 * np.random.randn(1000)

    data = {
        "time": times,
        "position": positions,
        "velocity": velocities,
    }

    metadata = {
        "experiment": "oscillator_test",
        "damping": 0.1,
        "frequency": 1.0,
    }

    # 保存
    output_path = Path("out/example_timeseries.csv")
    save_timeseries_csv(output_path, data, metadata=metadata, version="example-v1.0")
    print(f"已保存时间序列到: {output_path}")
    print(f"元数据文件: {output_path.with_suffix('.csv.meta.json')}")

    # 加载
    loaded_data, loaded_meta = load_timeseries_csv(output_path)
    print(f"加载了 {len(loaded_data)} 列，{len(loaded_data['time'])} 行")
    print(f"元数据: {loaded_meta.get('metadata', {})}")
    print()


def example_2_save_simulation_summary():
    """示例 2：保存仿真摘要（参数 + 结果）。"""
    print("=== 示例 2：仿真摘要 ===")

    summary = {
        "params": {
            "slope_deg": 2.5,
            "duration": 12.0,
            "hip_mass": 5.0,
        },
        "results": {
            "success": True,
            "simulated_time": 12.0,
            "forward_distance": 3.45,
            "alternations": 14,
        },
        "score": 2345.6,
    }

    metadata = {
        "git_hash": "a1b2c3d",
        "notes": "baseline test",
    }

    # 保存
    output_path = Path("out/example_summary.json")
    save_summary_json(output_path, summary, metadata=metadata)
    print(f"已保存摘要到: {output_path}")

    # 加载
    loaded = load_summary_json(output_path)
    print(
        f"加载的摘要: success={loaded['results']['success']}, score={loaded['score']}"
    )
    print(f"版本: {loaded.get('version')}, 时间戳: {loaded.get('timestamp')}")
    print()


def example_3_batch_save():
    """示例 3：批量保存多个试验的数据。"""
    print("=== 示例 3：批量保存 ===")

    for trial_id in range(3):
        # 模拟每次试验的数据
        times = np.linspace(0, 5, 500)
        signal = np.sin(times * (trial_id + 1)) + 0.1 * np.random.randn(500)

        data = {"time": times, "signal": signal}
        metadata = {"trial_id": trial_id, "noise_level": 0.1}

        output_path = Path(f"out/trial_{trial_id:02d}.csv")
        save_timeseries_csv(output_path, data, metadata=metadata)
        print(f"  已保存 trial {trial_id}")

    print("批量保存完成\n")


def example_4_check_metadata():
    """示例 4：检查元数据文件内容。"""
    print("=== 示例 4：元数据内容检查 ===")

    csv_path = Path("out/example_timeseries.csv")
    if csv_path.exists():
        _, meta = load_timeseries_csv(csv_path)
        print(f"CSV 文件: {meta.get('csv_file')}")
        print(f"行数: {meta.get('n_rows')}")
        print(f"列: {meta.get('columns')}")
        print(f"版本: {meta.get('version')}")
        print(f"时间戳: {meta.get('timestamp')}")
        print(f"实验元数据: {meta.get('metadata', {})}")
    else:
        print("请先运行示例 1")
    print()


if __name__ == "__main__":
    # 确保输出目录存在
    Path("out").mkdir(exist_ok=True)

    example_1_save_and_load_timeseries()
    example_2_save_simulation_summary()
    example_3_batch_save()
    example_4_check_metadata()

    print("所有示例运行完成。查看 out/ 目录获取输出文件。")

"""
数据导出工具：将 Python 仿真数据转换为 Remotion 可用格式

用法:
    python utils/export_for_remotion.py --input ../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv --output public/v10_data.json
"""

import argparse
import json
import pandas as pd
from pathlib import Path


def export_phase_data(csv_path: str, json_output: str, sample_rate: int = 1):
    """
    从 CSV 导出关键帧数据为 JSON

    Args:
        csv_path: 输入 CSV 文件路径
        json_output: 输出 JSON 文件路径
        sample_rate: 采样率（每 N 帧取一帧，减小文件大小）
    """
    df = pd.read_csv(csv_path)

    # 按采样率抽取数据
    df_sampled = df.iloc[::sample_rate]

    # 提取关键字段
    keyframes = []
    for _, row in df_sampled.iterrows():
        frame = {
            'time': float(row['time']),
            'hip_x': float(row['hip_x']),
            'hip_z': float(row['hip_z']),
            'left_hip': float(row['left_hip']),
            'left_knee': float(row['left_knee']),
            'left_ankle': float(row['left_ankle']),
            'right_hip': float(row['right_hip']),
            'right_knee': float(row['right_knee']),
            'right_ankle': float(row['right_ankle']),
            'left_contact': bool(row['left_contact']),
            'right_contact': bool(row['right_contact']),
        }

        # 如果有接触细节，也包含
        if 'left_heel_contact' in row:
            frame['left_heel_contact'] = bool(row['left_heel_contact'])
            frame['left_sole_contact'] = bool(row['left_sole_contact'])
            frame['left_toe_contact'] = bool(row['left_toe_contact'])
            frame['right_heel_contact'] = bool(row['right_heel_contact'])
            frame['right_sole_contact'] = bool(row['right_sole_contact'])
            frame['right_toe_contact'] = bool(row['right_toe_contact'])

        # 如果有 phase 信息（V13.6）
        if 'mode' in row:
            frame['mode'] = str(row['mode'])

        keyframes.append(frame)

    # 写入 JSON
    output_path = Path(json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(keyframes, f, indent=2, ensure_ascii=False)

    print(f"✓ 导出 {len(keyframes)} 帧数据到 {json_output}")
    print(f"  原始数据: {len(df)} 帧")
    print(f"  采样率: 1/{sample_rate}")
    print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")


def export_summary_metrics(summary_json: str, output_json: str):
    """
    从 summary JSON 提取汇总指标

    Args:
        summary_json: 输入 summary.json 路径
        output_json: 输出 JSON 路径
    """
    with open(summary_json, 'r') as f:
        summary = json.load(f)

    # 提取关键指标
    metrics = {
        'success': summary.get('success', False),
        'forward_distance': summary.get('forward_distance', 0.0),
        'alternating_touchdowns': summary.get('alternating_touchdowns', 0),
        'input_energy': summary.get('active_input_energy_j', 0.0),
        'cot': summary.get('cost_of_transport', 0.0),
        'simulated_time': summary.get('simulated_time', 0.0),
    }

    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ 导出汇总指标到 {output_json}")
    for key, value in metrics.items():
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description='导出仿真数据到 Remotion 格式')
    parser.add_argument('--input', required=True, help='输入 CSV 文件路径')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    parser.add_argument('--sample-rate', type=int, default=1, help='采样率（默认 1 = 全部导出）')
    parser.add_argument('--summary', help='可选：summary.json 路径，用于导出汇总指标')
    parser.add_argument('--summary-output', help='汇总指标输出路径')

    args = parser.parse_args()

    # 导出时间序列数据
    export_phase_data(args.input, args.output, args.sample_rate)

    # 如果提供了 summary，也导出汇总指标
    if args.summary and args.summary_output:
        export_summary_metrics(args.summary, args.summary_output)


if __name__ == '__main__':
    main()

"""
批量导出所有版本的仿真数据到 Remotion 格式

用法:
    cd D:\Dunna\Documents\hw-1\compass-gait-remotion
    ..\.venv-mujoco\Scripts\python.exe utils\batch_export.py
"""

import sys
from pathlib import Path
import subprocess

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 定义需要导出的版本和文件
EXPORTS = [
    {
        'name': 'V10 足踝滚动',
        'csv': '../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv',
        'json': 'public/data/v10_data.json',
        'summary': '../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_summary.json',
        'summary_json': 'public/data/v10_metrics.json',
        'sample_rate': 2,  # 每 2 帧采样一次，减小文件大小
    },
    {
        'name': 'V13.6 FSM',
        'csv': '../v13_6_event_driven_fsm/out/v13_6_baseline_data.csv',
        'json': 'public/data/v13_6_data.json',
        'summary': '../v13_6_event_driven_fsm/out/v13_6_baseline_summary.json',
        'summary_json': 'public/data/v13_6_metrics.json',
        'sample_rate': 2,
    },
]


def check_file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    path = Path(filepath)
    return path.exists()


def export_version(config: dict):
    """导出单个版本的数据"""
    print(f"\n{'='*60}")
    print(f"导出 {config['name']}")
    print(f"{'='*60}")

    # 检查输入文件是否存在
    if not check_file_exists(config['csv']):
        print(f"⚠️  CSV 文件不存在: {config['csv']}")
        print(f"   跳过此版本")
        return False

    # 构建导出命令
    cmd = [
        sys.executable,
        'utils/export_for_remotion.py',
        '--input', config['csv'],
        '--output', config['json'],
        '--sample-rate', str(config['sample_rate']),
    ]

    # 如果有 summary 文件，也导出
    if 'summary' in config and check_file_exists(config['summary']):
        cmd.extend([
            '--summary', config['summary'],
            '--summary-output', config['summary_json'],
        ])

    # 执行导出
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 导出失败:")
        print(e.stderr)
        return False


def main():
    print("批量导出仿真数据到 Remotion 格式")
    print(f"工作目录: {Path.cwd()}")

    # 确保 public/data 目录存在
    Path('public/data').mkdir(parents=True, exist_ok=True)

    # 导出所有版本
    success_count = 0
    for config in EXPORTS:
        if export_version(config):
            success_count += 1

    # 汇总
    print(f"\n{'='*60}")
    print(f"导出完成: {success_count}/{len(EXPORTS)} 个版本成功")
    print(f"{'='*60}")

    if success_count < len(EXPORTS):
        print("\n提示: 部分版本未导出，请检查对应的仿真输出文件是否存在")
        print("      运行相应版本的 simulate_*.py 生成数据后重试")


if __name__ == '__main__':
    main()

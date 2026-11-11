"""
仿真脚本集成示例

演示如何在仿真脚本中集成数据版本追踪。
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_versioning import VersionTracker, auto_register_simulation_output


def run_example_simulation(output_dir: str, version_tag: str = "V99"):
    """
    示例仿真函数

    Args:
        output_dir: 输出目录
        version_tag: 版本标签
    """
    print(f"Running example simulation for {version_tag}...")

    # 仿真参数
    params = {
        "slope_deg": 3.0,
        "hip_stiffness": 50.0,
        "damping": 2.0,
        "mass": 12.0,
        "simulation_time": 10.0,
    }

    # 模拟生成数据
    np.random.seed(42)
    time = np.linspace(0, params["simulation_time"], 500)
    data = pd.DataFrame(
        {
            "time": time,
            "position": np.sin(2 * np.pi * 0.5 * time) + np.random.randn(500) * 0.1,
            "velocity": np.cos(2 * np.pi * 0.5 * time) + np.random.randn(500) * 0.1,
            "force": np.random.randn(500) * 5.0,
        }
    )

    # 创建输出目录
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"sim_results_{timestamp}.csv"
    data.to_csv(csv_path, index=False)

    print(f"  Saved: {csv_path}")

    # 计算摘要
    summary = {
        "timestamp": timestamp,
        "version": version_tag,
        "params": params,
        "results": {
            "mean_position": float(data["position"].mean()),
            "max_velocity": float(data["velocity"].max()),
            "total_samples": len(data),
        },
    }

    # 保存摘要
    import json

    json_path = output_dir / f"sim_summary_{timestamp}.json"

    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Saved: {json_path}")

    return csv_path, json_path, params


def main():
    """主函数：演示集成数据版本追踪"""
    print("=" * 80)
    print("Simulation Integration Example")
    print("=" * 80)
    print()

    # 初始化版本追踪器
    tracker = VersionTracker(project_root)

    # 运行仿真
    version_tag = "V99_EXAMPLE"
    output_dir = project_root / "data_versioning" / "example_output"

    csv_path, json_path, params = run_example_simulation(output_dir, version_tag)

    print()
    print("Registering simulation outputs...")

    # 方法 1：使用便捷函数自动注册
    experiment_id = f"example_sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    auto_register_simulation_output(
        tracker=tracker,
        output_file=str(csv_path),
        version_tag=version_tag,
        experiment_id=experiment_id,
        params=params,
    )

    # 方法 2：手动注册（更多控制）
    tracker.register_file(
        str(json_path),
        category="simulation_results",
        version_tag=version_tag,
        experiment_id=experiment_id,
        description="Simulation summary with parameters and results",
        metadata={"format": "json", "content_type": "summary"},
    )

    print()
    print("=" * 80)
    print("Integration Complete")
    print("=" * 80)
    print()
    print("Files registered:")
    print(f"  - {csv_path.name}")
    print(f"  - {json_path.name}")
    print()
    print("To integrate into your simulation script:")
    print()
    print("1. Add at the top of your script:")
    print(
        "   from data_versioning import VersionTracker, auto_register_simulation_output"
    )
    print()
    print("2. After saving output files, add:")
    print("   tracker = VersionTracker(project_root)")
    print("   auto_register_simulation_output(")
    print("       tracker=tracker,")
    print("       output_file=output_csv_path,")
    print("       version_tag='V13',")
    print("       experiment_id='exp_001',")
    print("       params=simulation_params")
    print("   )")
    print()
    print("See data_versioning/README.md for more details.")
    print()


if __name__ == "__main__":
    main()

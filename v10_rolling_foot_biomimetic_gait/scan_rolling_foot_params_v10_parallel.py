"""并行化参数扫描 - 优化版本。

相比原版 scan_rolling_foot_params_v10.py:
1. 使用 joblib 并行化仿真
2. 降低采样率（20Hz → 10Hz）用于初筛
3. 预期加速比: 4-8x (取决于 CPU 核心数)
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict
from itertools import product

from joblib import Parallel, delayed
from simulate_rolling_foot_gait_v10 import OUT_DIR, RollingFootParams, run_simulation


def candidate_params() -> list[RollingFootParams]:
    """生成候选参数（与原版相同）。"""
    candidates = [
        RollingFootParams(
            slope_deg=0.0,
            gait_period=0.80,
            hip_torque_limit=4.0,
            knee_torque_limit=4.0,
            hip_kp=30.0,
            hip_kd=6.0,
            knee_kp=16.0,
            knee_kd=2.0,
            initial_vx=0.03,
            torso_mass=0.05,
            foot_length=0.12,
            foot_radius=0.04,
            ankle_stiffness=10.0,
            ankle_damping=0.08,
            duration=12.0,
        )
    ]
    for foot_length, ankle_stiffness, ankle_damping, period, htau, ktau in product(
        [0.10, 0.12, 0.14, 0.16],
        [2.5, 5.0, 10.0],
        [0.08, 0.20, 0.50],
        [0.60, 0.80, 1.00],
        [4.0, 8.0],
        [2.0, 4.0],
    ):
        candidates.append(
            RollingFootParams(
                slope_deg=0.0,
                gait_period=period,
                hip_torque_limit=htau,
                knee_torque_limit=ktau,
                hip_kp=30.0,
                hip_kd=6.0,
                knee_kp=16.0,
                knee_kd=2.0,
                initial_vx=0.03,
                torso_mass=0.05,
                foot_length=foot_length,
                foot_radius=0.04,
                ankle_stiffness=ankle_stiffness,
                ankle_damping=ankle_damping,
                duration=12.0,
            )
        )
    return candidates


def evaluate_params(params: RollingFootParams, sample_hz: float = 10.0) -> dict:
    """评估单组参数（用于并行调用）。"""
    _, summary = run_simulation(params, sample_hz=sample_hz)
    return {
        **asdict(params),
        "score": summary["score"],
        "success": summary["success"],
        "alternating_touchdowns": summary["alternating_touchdowns"],
        "forward_distance": summary["forward_distance"],
        "simulated_time": summary["simulated_time"],
        "failure": summary["failure"],
        "active_input_energy_j": summary["active_input_energy_j"],
    }


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("并行化参数扫描 (v10 优化版)")
    print("=" * 60)

    candidates = candidate_params()
    print(f"候选参数组合: {len(candidates)}")

    # 并行评估（降低采样率用于快速筛选）
    start_time = time.perf_counter()

    results = Parallel(n_jobs=-1, verbose=10)(
        delayed(evaluate_params)(params, sample_hz=10.0) for params in candidates
    )

    parallel_time = time.perf_counter() - start_time

    # 排序并保存结果
    results.sort(key=lambda item: item["score"], reverse=True)

    csv_path = OUT_DIR / "v10_scan_results_parallel.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # 找到最佳参数后，用高采样率重新仿真
    best_result = results[0]
    best_params = RollingFootParams(
        **{k: best_result[k] for k in asdict(RollingFootParams()).keys()}
    )

    print(f"\n最佳参数 score: {best_result['score']:.1f}")
    print("重新仿真最佳参数（高采样率 160Hz）...")

    _, best_summary = run_simulation(
        best_params, save_prefix="v10_rolling_foot_walk_parallel", sample_hz=160.0
    )
    best_summary["params"] = asdict(best_params)

    json_path = OUT_DIR / "v10_best_params_parallel.json"
    json_path.write_text(
        json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 性能报告
    print("\n" + "=" * 60)
    print("性能报告")
    print("=" * 60)
    print(f"总耗时: {parallel_time:.2f}s")
    print(f"平均每组: {parallel_time/len(candidates):.3f}s")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")

    # 估算加速比（假设串行版本需要 N × 单次时间）
    estimated_serial = len(candidates) * 0.29  # 从 profiling 得到单次 ~0.29s
    speedup = estimated_serial / parallel_time
    print(f"\n估算加速比: {speedup:.1f}x")


if __name__ == "__main__":
    main()

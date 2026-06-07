"""V21 批量实验：扫描三类 3D 扰动。

优先级 1：初始 roll 扰动（7 个配置）
优先级 2：侧向脉冲（6 个配置）
优先级 3：随机风（5 个配置，可选）
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from simulate_v21_perturbation import (
    PerturbationScenario,
    V19Params,
    run_simulation_v21,
)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def run_priority1_init_roll():
    """优先级 1：初始 roll 扰动。"""
    print("\n=== 优先级 1：初始 Roll 扰动 ===")
    OUT_DIR.mkdir(exist_ok=True)

    p = V19Params(abd_kp=40.0, abd_kd=4.0, duration=10.0)
    roll_grid = [0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0]

    results = []
    csv_path = OUT_DIR / "v21_init_roll_results.csv"

    started = time.time()
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "init_roll_deg",
                "alternations",
                "simulated_time_s",
                "forward_distance_m",
                "max_roll_deg",
                "max_hip_y_m",
                "failure",
                "success",
            ]
        )

        for roll_deg in roll_grid:
            scenario = PerturbationScenario(init_hip_roll_deg=roll_deg)
            summary = run_simulation_v21(p, scenario, save_prefix=None)

            results.append(
                {
                    "init_roll_deg": roll_deg,
                    "alternations": summary["alternating_touchdowns"],
                    "simulated_time_s": summary["simulated_time"],
                    "forward_distance_m": summary["forward_distance"],
                    "max_roll_deg": summary["max_abs_roll_deg"],
                    "max_hip_y_m": summary["max_abs_hip_y_m"],
                    "failure": summary["failure"],
                    "success": summary["success"],
                }
            )

            writer.writerow(
                [
                    f"{roll_deg:.1f}",
                    summary["alternating_touchdowns"],
                    f"{summary['simulated_time']:.3f}",
                    f"{summary['forward_distance']:.4f}",
                    f"{summary['max_abs_roll_deg']:.2f}",
                    f"{summary['max_abs_hip_y_m']:.4f}",
                    summary["failure"],
                    int(summary["success"]),
                ]
            )
            f.flush()

            print(
                f"  roll={roll_deg:+4.1f}° -> alt={summary['alternating_touchdowns']:2d}, "
                f"t={summary['simulated_time']:5.2f}s, fail={summary['failure']}"
            )

    elapsed = time.time() - started
    print(f"\n优先级 1 完成：{len(roll_grid)} 次仿真，用时 {elapsed:.1f}s")
    print(f"  输出: {csv_path}")

    (OUT_DIR / "v21_init_roll_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return results


def run_priority2_lateral_impulse():
    """优先级 2：侧向脉冲。"""
    print("\n=== 优先级 2：侧向脉冲 ===")
    OUT_DIR.mkdir(exist_ok=True)

    p = V19Params(abd_kp=40.0, abd_kd=4.0, duration=10.0)
    impulse_grid = [0.0, 5.0, 10.0, 15.0, 20.0, -10.0]

    results = []
    csv_path = OUT_DIR / "v21_lateral_impulse_results.csv"

    started = time.time()
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "impulse_n",
                "alternations",
                "simulated_time_s",
                "forward_distance_m",
                "max_roll_deg",
                "max_hip_y_m",
                "failure",
                "success",
            ]
        )

        for impulse_n in impulse_grid:
            scenario = PerturbationScenario(
                lateral_impulse_n=impulse_n,
                impulse_t_s=2.0,
                impulse_duration_s=0.05,
            )
            summary = run_simulation_v21(p, scenario, save_prefix=None)

            results.append(
                {
                    "impulse_n": impulse_n,
                    "alternations": summary["alternating_touchdowns"],
                    "simulated_time_s": summary["simulated_time"],
                    "forward_distance_m": summary["forward_distance"],
                    "max_roll_deg": summary["max_abs_roll_deg"],
                    "max_hip_y_m": summary["max_abs_hip_y_m"],
                    "failure": summary["failure"],
                    "success": summary["success"],
                }
            )

            writer.writerow(
                [
                    f"{impulse_n:.1f}",
                    summary["alternating_touchdowns"],
                    f"{summary['simulated_time']:.3f}",
                    f"{summary['forward_distance']:.4f}",
                    f"{summary['max_abs_roll_deg']:.2f}",
                    f"{summary['max_abs_hip_y_m']:.4f}",
                    summary["failure"],
                    int(summary["success"]),
                ]
            )
            f.flush()

            print(
                f"  impulse={impulse_n:+6.1f}N -> alt={summary['alternating_touchdowns']:2d}, "
                f"t={summary['simulated_time']:5.2f}s, fail={summary['failure']}"
            )

    elapsed = time.time() - started
    print(f"\n优先级 2 完成：{len(impulse_grid)} 次仿真，用时 {elapsed:.1f}s")
    print(f"  输出: {csv_path}")

    (OUT_DIR / "v21_lateral_impulse_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return results


def run_priority3_random_wind():
    """优先级 3：随机风（可选）。"""
    print("\n=== 优先级 3：随机风（可选）===")
    OUT_DIR.mkdir(exist_ok=True)

    p = V19Params(abd_kp=40.0, abd_kd=4.0, duration=10.0)
    wind_grid = [0.0, 1.0, 2.0, 3.0, 5.0]
    n_seeds = 3

    results = []
    csv_path = OUT_DIR / "v21_random_wind_results.csv"

    started = time.time()
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "wind_std_n",
                "seed",
                "alternations",
                "simulated_time_s",
                "forward_distance_m",
                "max_roll_deg",
                "max_hip_y_m",
                "failure",
                "success",
            ]
        )

        for wind_std in wind_grid:
            alt_sum = 0
            time_sum = 0.0
            succ_count = 0
            for seed in range(n_seeds):
                scenario = PerturbationScenario(
                    random_wind_std_n=wind_std,
                    wind_seed=seed,
                )
                summary = run_simulation_v21(p, scenario, save_prefix=None)

                alt_sum += summary["alternating_touchdowns"]
                time_sum += summary["simulated_time"]
                succ_count += int(summary["success"])

                writer.writerow(
                    [
                        f"{wind_std:.1f}",
                        seed,
                        summary["alternating_touchdowns"],
                        f"{summary['simulated_time']:.3f}",
                        f"{summary['forward_distance']:.4f}",
                        f"{summary['max_abs_roll_deg']:.2f}",
                        f"{summary['max_abs_hip_y_m']:.4f}",
                        summary["failure"],
                        int(summary["success"]),
                    ]
                )
                f.flush()

            avg_alt = alt_sum / n_seeds
            avg_time = time_sum / n_seeds
            succ_rate = succ_count / n_seeds

            results.append(
                {
                    "wind_std_n": wind_std,
                    "mean_alternations": avg_alt,
                    "mean_simulated_time_s": avg_time,
                    "success_rate": succ_rate,
                }
            )

            print(
                f"  wind_std={wind_std:4.1f}N -> avg_alt={avg_alt:4.1f}, "
                f"avg_t={avg_time:5.2f}s, succ={succ_rate:.2f}"
            )

    elapsed = time.time() - started
    print(f"\n优先级 3 完成：{len(wind_grid) * n_seeds} 次仿真，用时 {elapsed:.1f}s")
    print(f"  输出: {csv_path}")

    (OUT_DIR / "v21_random_wind_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--priority", type=int, default=0, help="运行指定优先级 (1/2/3)，0=全部"
    )
    args = parser.parse_args()

    overall_start = time.time()

    if args.priority == 0 or args.priority == 1:
        run_priority1_init_roll()

    if args.priority == 0 or args.priority == 2:
        run_priority2_lateral_impulse()

    if args.priority == 0 or args.priority == 3:
        run_priority3_random_wind()

    overall_elapsed = time.time() - overall_start
    print(f"\n总用时：{overall_elapsed:.1f}s ({overall_elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()

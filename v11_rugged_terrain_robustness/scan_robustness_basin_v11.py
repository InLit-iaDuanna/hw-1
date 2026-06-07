"""V11 二维稳定盆地扫描：地形振幅 × 单脉冲幅值。

每格跑 N_SEEDS 个种子取平均；串行执行（PowerShell 并行有 Exit 255 已知问题）。
输出：out/v11_basin_results.csv 与 out/v11_basin_grid.npz
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict

import numpy as np
from simulate_rugged_gait_v11 import (
    OUT_DIR,
    RuggedScenario,
    load_v10_best_params,
    run_rugged_simulation,
)

AMP_GRID = np.linspace(0.0, 0.040, 15)  # 地形振幅 (m)
IMPULSE_GRID = np.linspace(0.0, 80.0, 15)  # 单脉冲幅值 (N)
N_SEEDS = 3
DURATION = 12.0
IMPULSE_T = 4.0
IMPULSE_DURATION = 0.05


def run_grid() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    base_params = load_v10_best_params()
    n_amp = len(AMP_GRID)
    n_imp = len(IMPULSE_GRID)

    success_rate = np.zeros((n_amp, n_imp))
    mean_touchdowns = np.zeros((n_amp, n_imp))
    mean_distance = np.zeros((n_amp, n_imp))
    fail_modes: dict[tuple[int, int], dict[str, int]] = {}

    csv_path = OUT_DIR / "v11_basin_results.csv"
    started = time.time()
    total = n_amp * n_imp * N_SEEDS
    done = 0
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "amp_idx",
                "imp_idx",
                "seed",
                "amplitude_m",
                "impulse_n",
                "success",
                "touchdowns",
                "distance_m",
                "sim_time_s",
                "failure",
                "active_energy_j",
            ]
        )
        for i, amp in enumerate(AMP_GRID):
            for j, imp in enumerate(IMPULSE_GRID):
                fail_count: dict[str, int] = {}
                for k in range(N_SEEDS):
                    scenario = RuggedScenario(
                        terrain_amplitude_m=float(amp),
                        terrain_wavelength_m=1.2,
                        terrain_seed=k,
                        impulse_force_n=float(imp),
                        impulse_t_s=IMPULSE_T,
                        impulse_duration_s=IMPULSE_DURATION,
                        impulse_dir=(1.0, 0.0, 0.0),
                        contact_phase_noise_s=0.0,
                        contact_phase_seed=0,
                    )
                    params = base_params.__class__(
                        **{**asdict(base_params), "duration": DURATION}
                    )
                    _, summary = run_rugged_simulation(
                        params, scenario, save_prefix=None
                    )
                    success_rate[i, j] += float(summary["success"]) / N_SEEDS
                    mean_touchdowns[i, j] += summary["alternating_touchdowns"] / N_SEEDS
                    mean_distance[i, j] += summary["forward_distance"] / N_SEEDS
                    fm = summary["failure"]
                    fail_count[fm] = fail_count.get(fm, 0) + 1
                    writer.writerow(
                        [
                            i,
                            j,
                            k,
                            f"{amp:.5f}",
                            f"{imp:.3f}",
                            int(summary["success"]),
                            summary["alternating_touchdowns"],
                            f"{summary['forward_distance']:.4f}",
                            f"{summary['simulated_time']:.3f}",
                            fm,
                            f"{summary['active_input_energy_j']:.3f}",
                        ]
                    )
                    f.flush()
                    done += 1
                fail_modes[(i, j)] = fail_count
                elapsed = time.time() - started
                eta = elapsed / max(done, 1) * (total - done)
                print(
                    f"[{done:>3}/{total}] amp={amp:.4f} m  imp={imp:.1f} N  "
                    f"succ={success_rate[i, j]:.2f}  td={mean_touchdowns[i, j]:.1f}  "
                    f"d={mean_distance[i, j]:.2f} m  | elapsed={elapsed:.0f}s ETA={eta:.0f}s"
                )

    np.savez(
        OUT_DIR / "v11_basin_grid.npz",
        amp_grid=AMP_GRID,
        impulse_grid=IMPULSE_GRID,
        success_rate=success_rate,
        mean_touchdowns=mean_touchdowns,
        mean_distance=mean_distance,
    )
    (OUT_DIR / "v11_basin_failmodes.json").write_text(
        json.dumps(
            {f"{i},{j}": fc for (i, j), fc in fail_modes.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n完成 {total} 次仿真，用时 {time.time() - started:.0f} s")
    print(f"  CSV:  {csv_path}")
    print(f"  NPZ:  {OUT_DIR / 'v11_basin_grid.npz'}")


def run_phase_noise_sweep() -> None:
    """一维灵敏度：触地相位噪声 σ → 成功率。"""
    OUT_DIR.mkdir(exist_ok=True)
    base_params = load_v10_best_params()
    sigmas = np.array([0.0, 0.005, 0.010, 0.015, 0.020, 0.030, 0.045, 0.060])
    rows = []
    for sigma in sigmas:
        succ = 0
        td_sum = 0
        for k in range(5):
            scenario = RuggedScenario(
                terrain_amplitude_m=0.0,
                impulse_force_n=0.0,
                contact_phase_noise_s=float(sigma),
                contact_phase_seed=k,
            )
            params = base_params.__class__(
                **{**asdict(base_params), "duration": DURATION}
            )
            _, summary = run_rugged_simulation(params, scenario, save_prefix=None)
            succ += int(summary["success"])
            td_sum += summary["alternating_touchdowns"]
        rows.append(
            {
                "sigma_s": float(sigma),
                "success_rate": succ / 5.0,
                "mean_touchdowns": td_sum / 5.0,
            }
        )
        print(f"  sigma={sigma:.3f}s -> succ={succ/5:.2f}, td={td_sum/5:.1f}")
    (OUT_DIR / "v11_phase_noise_sweep.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-noise-only", action="store_true")
    args = parser.parse_args()
    if args.phase_noise_only:
        run_phase_noise_sweep()
    else:
        run_grid()
        run_phase_noise_sweep()

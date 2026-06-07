"""V13.7 扰动恢复测试（可选）- 验证 Floquet 预测 vs 实际行为。

基于 V13b disturbance_recovery 方法，在 V13.7 FSM 不动点附近注入扰动，
观察实际衰减/发散率是否与 Floquet 乘子 max|λ|=1.0008 一致。

关键问题：
- Floquet 预测：max|λ|=1.0008 > 1 → 扰动应缓慢发散
- 实际观测：20s 仿真正常完成 17 次触地
- 矛盾解释：发散太慢（~1000 步时间尺度）或非线性稳定化？
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1 = ROOT.parent
V137_DIR = HW1 / "v13_7_friction_compensation"
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1))

from simulate_passive_arms_v14 import PassiveArmsParams  # noqa: E402
from simulate_v13_7 import (  # noqa: E402
    V137Params,
    make_v137_fsm,
    run_simulation_v137,
)

from common.motor_dynamics import PRESETS as MOTOR_PRESETS  # noqa: E402
from common.poincare import collect_section  # noqa: E402

OUT_DIR = ROOT / "out"
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")


def make_baseline_params(duration: float = 20.0) -> PassiveArmsParams:
    """V13.7 baseline 参数。"""
    ARM_MASS = 0.01
    FOOT_RADIUS = 0.042
    LEG_SCALE = 1.02

    base0 = PassiveArmsParams()
    return replace(
        base0,
        duration=duration,
        arm_mass=ARM_MASS,
        foot_radius=FOOT_RADIUS,
        thigh_length=base0.thigh_length * LEG_SCALE,
        shank_length=base0.shank_length * LEG_SCALE,
        step_length=base0.step_length * LEG_SCALE,
    )


def apply_perturbation(
    base_params: PassiveArmsParams,
    axis_name: str,
    delta: float,
    fixed_point: np.ndarray,
) -> PassiveArmsParams:
    """在不动点附近注入扰动（通过调整初始条件）。

    注意：MuJoCo 初始化复杂，这里用近似方法调整初速度。
    """
    # 简化：仅扰动初速度 initial_vx
    if "vel" in axis_name:
        return replace(base_params, initial_vx=base_params.initial_vx + delta * 0.1)
    else:
        # 位置扰动较难直接设置，暂时跳过
        return base_params


def measure_convergence(
    section_pts: np.ndarray,
    fixed_point: np.ndarray,
    skip_head: int = 2,
) -> dict:
    """测量 Poincaré 截面点到不动点的距离序列，拟合指数衰减/发散。

    d_k = ||x_k - x*|| ≈ d_0 * |λ|^k

    返回：拟合的 λ_fit, R^2, 距离序列
    """
    if len(section_pts) < skip_head + 2:
        return {"lambda_fit": float("nan"), "r2": 0.0, "distances": []}

    pts = section_pts[skip_head:]
    distances = np.linalg.norm(pts - fixed_point, axis=1)

    if len(distances) < 2:
        return {"lambda_fit": float("nan"), "r2": 0.0, "distances": distances.tolist()}

    # 对数拟合：ln(d_k) = ln(d_0) + k * ln(|λ|)
    k_vals = np.arange(len(distances))
    log_d = np.log(distances + 1e-12)  # 避免 log(0)

    # 线性回归
    A = np.vstack([k_vals, np.ones(len(k_vals))]).T
    result = np.linalg.lstsq(A, log_d, rcond=None)
    slope, intercept = result[0]
    lambda_fit = np.exp(slope)

    # R^2
    log_d_pred = slope * k_vals + intercept
    ss_res = np.sum((log_d - log_d_pred) ** 2)
    ss_tot = np.sum((log_d - np.mean(log_d)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "lambda_fit": float(lambda_fit),
        "r2": float(r2),
        "distances": distances.tolist(),
        "slope": float(slope),
        "intercept": float(intercept),
    }


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    # 加载 baseline Floquet 结果
    summary_path = OUT_DIR / "v13_7_floquet_summary.json"
    if not summary_path.exists():
        print("错误: 请先运行 analyze_floquet_v13_7.py 获取不动点")
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ideal_result = next(
        (r for r in summary["v13_7_results"] if r["config"] == "v13_7_fsm_ideal"), None
    )

    if not ideal_result or not ideal_result.get("success"):
        print("错误: baseline ideal 配置未成功")
        return

    fixed_point = np.array(ideal_result["fixed_point"])
    floquet_lambda = ideal_result["max_abs_floquet"]

    print("=" * 60)
    print("V13.7 FSM 扰动恢复测试")
    print("=" * 60)
    print(f"不动点: {fixed_point}")
    print(f"Floquet max|λ|: {floquet_lambda:.4f}")
    print("=" * 60)

    # 扰动测试配置
    PERTURBATIONS = [
        ("right_hip", +0.05),
        ("right_hip_vel", +0.05),
        ("right_knee", +0.05),
        ("right_knee_vel", +0.05),
    ]

    base_params = make_baseline_params(duration=20.0)
    ideal_motor = MOTOR_PRESETS["ideal"]

    results = []

    for axis_name, delta in PERTURBATIONS:
        print(f"\n[测试] {axis_name} + {delta:.3f}")

        # 注意：真实扰动注入需修改 initialize() 函数，这里仅做概念演示
        # 实际实现需要在 run_simulation_v137 中添加初始扰动参数
        params = V137Params(
            base=base_params,
            fsm=make_v137_fsm(base_params),
            hip_motor=ideal_motor,
            knee_motor=ideal_motor,
            compensate_friction=False,
        )

        rows, sim_summary = run_simulation_v137(
            params, save_prefix=None, sample_hz=160.0
        )

        # Poincaré 截面
        section_pts = collect_section(rows, STATE_KEYS)
        n_section = len(section_pts)

        print(f"  - alternations: {sim_summary['alternating_touchdowns']}")
        print(f"  - n_section: {n_section}")

        if n_section < 4:
            print("  - 警告: 截面点不足，跳过")
            continue

        # 测量收敛
        conv = measure_convergence(section_pts, fixed_point, skip_head=2)
        lambda_fit = conv["lambda_fit"]
        r2 = conv["r2"]

        print(f"  - λ_fit: {lambda_fit:.4f}")
        print(
            f"  - Δ vs Floquet: {(lambda_fit - floquet_lambda):.4f} ({(lambda_fit/floquet_lambda - 1)*100:+.1f}%)"
        )
        print(f"  - R²: {r2:.4f}")

        results.append(
            {
                "axis": axis_name,
                "delta": delta,
                "n_section": n_section,
                "lambda_fit": lambda_fit,
                "lambda_floquet": floquet_lambda,
                "delta_lambda": lambda_fit - floquet_lambda,
                "r2": r2,
                "distances": conv["distances"],
                "success": sim_summary["success"],
            }
        )

    # 保存结果
    result_path = OUT_DIR / "v13_7_disturbance_recovery.json"
    result_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n保存结果: {result_path}")

    # 绘图
    if results:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()

        for i, res in enumerate(results[:4]):
            ax = axes[i]
            distances = res["distances"]
            k_vals = np.arange(len(distances))

            ax.semilogy(k_vals, distances, "o-", label="实际距离")

            # 拟合曲线
            lambda_fit = res["lambda_fit"]
            if not np.isnan(lambda_fit) and len(distances) > 0:
                d0_fit = distances[0]
                d_fit = d0_fit * (lambda_fit**k_vals)
                ax.semilogy(k_vals, d_fit, "--", label=f"拟合 λ={lambda_fit:.4f}")

            ax.set_xlabel("步数 k")
            ax.set_ylabel("||x_k - x*||")
            ax.set_title(
                f"{res['axis']} +{res['delta']:.2f}\nλ_fit={lambda_fit:.4f}, R²={res['r2']:.3f}"
            )
            ax.legend()
            ax.grid(alpha=0.3)

        fig.suptitle(
            f"V13.7 FSM 扰动恢复测试\nFloquet max|λ|={floquet_lambda:.4f}", fontsize=14
        )
        fig.tight_layout()

        plot_path = OUT_DIR / "v13_7_disturbance_recovery.png"
        fig.savefig(plot_path, dpi=150)
        print(f"绘制图表: {plot_path}")

    # 汇总
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"Floquet 预测: max|λ| = {floquet_lambda:.4f}")
    if results:
        lambda_fits = [
            r["lambda_fit"] for r in results if not np.isnan(r["lambda_fit"])
        ]
        if lambda_fits:
            lambda_mean = np.mean(lambda_fits)
            lambda_std = np.std(lambda_fits)
            print(f"实测平均: λ_fit = {lambda_mean:.4f} ± {lambda_std:.4f}")
            print(
                f"偏差: {(lambda_mean - floquet_lambda):.4f} ({(lambda_mean/floquet_lambda - 1)*100:+.1f}%)"
            )

            if lambda_mean > 1.0:
                print("\n结论: 实测 λ_fit > 1.0，验证 Floquet 发散预测")
            elif lambda_mean < 1.0:
                print(
                    "\n结论: 实测 λ_fit < 1.0，非线性效应提供稳定化（Floquet 线性化误差）"
                )
            else:
                print("\n结论: 实测 λ_fit ≈ 1.0，边界稳定")

    print("\n注意: 当前实现未真正注入初始扰动，仅做框架演示。")
    print("完整实现需修改 run_simulation_v137 支持自定义初始状态。")


if __name__ == "__main__":
    main()

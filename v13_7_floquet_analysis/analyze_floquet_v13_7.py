"""V13.7 FSM 控制律的 Floquet 稳定性分析。

对比 V10 PD 控制（max|λ|=0.944）与 V13.7 FSM 的稳定裕度。
基于 V13b 方法：20s 长程仿真 → Poincaré 截面 → Floquet 乘子。

分析三种配置：
1. V13.7 FSM + ideal motor (无摩擦，baseline)
2. V13.7 FSM + mx64ar + compensation (实际应用配置)
3. V13.7 FSM + mx64ar + no compensation (验证补偿必要性)
"""

from __future__ import annotations

import csv
import json
import sys
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

from common.energy_metrics import mechanical_energy_series  # noqa: E402
from common.motor_dynamics import PRESETS as MOTOR_PRESETS  # noqa: E402
from common.poincare import (
    collect_section,
    floquet_multipliers,
    plot_section,
)  # noqa: E402

OUT_DIR = ROOT / "out"
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")


def make_baseline_params(duration: float = 20.0) -> PassiveArmsParams:
    """V13.7 基线参数（基于 V14c 配置 - 与 smoke_v13_7.py 一致）。"""
    from dataclasses import replace

    # V13.7 smoke 的成功配置
    ARM_MASS = 0.01
    FOOT_RADIUS = 0.042
    LEG_SCALE = 1.02

    base0 = PassiveArmsParams()
    return replace(
        base0,
        duration=duration,
        arm_mass=ARM_MASS,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=FOOT_RADIUS,
        thigh_length=base0.thigh_length * LEG_SCALE,
        shank_length=base0.shank_length * LEG_SCALE,
        step_length=base0.step_length * LEG_SCALE,
    )


def analyze_config(
    config_name: str,
    params: V137Params,
    sample_hz: float = 160.0,
) -> dict:
    """运行仿真并分析 Floquet 稳定性。"""
    print(f"\n{'='*60}")
    print(f"[{config_name}] 运行 V13.7 @ duration={params.base.duration}s")
    print(f"{'='*60}")

    rows, summary = run_simulation_v137(params, save_prefix=None, sample_hz=sample_hz)

    # 保存 CSV
    csv_path = OUT_DIR / f"{config_name}_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"[{config_name}] 保存数据: {csv_path}")

    # Poincaré 截面
    section_pts = collect_section(rows, STATE_KEYS)
    n_section = len(section_pts)
    print(f"[{config_name}] Poincaré 截面点: {n_section} (目标 ≥16)")

    if n_section < 2:
        print(f"[{config_name}] 警告: 截面点不足，无法计算 Floquet 乘子")
        return {
            "config": config_name,
            "success": False,
            "error": "insufficient_section_points",
            "n_section_points": n_section,
        }

    # Floquet 分析
    floq = floquet_multipliers(section_pts, skip_head=2)
    eig = floq["eigvals"]
    max_abs = float(np.max(np.abs(eig))) if eig.size else float("nan")

    # 能量分析
    mass = params.base.hip_mass + 2 * params.base.torso_mass
    energy = mechanical_energy_series(rows, mass_kg=mass)
    e_total = energy["total"]

    if len(e_total) > 0:
        n = len(e_total)
        E_star = float(np.mean(e_total[n // 2 :]))
        E_std = float(np.std(e_total[n // 2 :]))
    else:
        E_star = float("nan")
        E_std = float("nan")

    result = {
        "config": config_name,
        "duration": params.base.duration,
        "success": bool(summary["success"]),
        "alternations": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "n_section_points": int(n_section),
        "fixed_point": floq["fixed_point"].tolist(),
        "eigvals_real": [float(np.real(v)) for v in eig],
        "eigvals_imag": [float(np.imag(v)) for v in eig],
        "eigvals_abs": [float(np.abs(v)) for v in eig],
        "max_abs_floquet": max_abs,
        "n_pairs_used": int(floq["n_pairs"]),
        "E_star_J": E_star,
        "E_std_J": E_std,
        "mass_kg": mass,
        "motor_hip": params.hip_motor.name,
        "motor_knee": params.knee_motor.name,
        "friction_compensation": params.compensate_friction,
        "state_keys": list(STATE_KEYS),
    }

    print(f"[{config_name}] 结果:")
    print(f"  - success: {result['success']}")
    print(f"  - alternations: {result['alternations']}")
    print(f"  - forward: {result['forward_distance']:.2f} m")
    print(f"  - max|λ|: {max_abs:.4f}")
    print(f"  - E*: {E_star:.2f} ± {E_std:.2f} J")
    print(f"  - n_pairs: {result['n_pairs_used']}")

    return result


def plot_comparison(results: list[dict], v10_ref: dict) -> None:
    """绘制对比图：Poincaré 截面 + Floquet 谱 + 稳定裕度对比。"""
    n_configs = len(results)
    fig = plt.figure(figsize=(18, 12))

    # 为每个配置绘制 Poincaré 截面和 Floquet 谱
    for i, res in enumerate(results):
        config = res["config"]
        csv_path = OUT_DIR / f"{config}_data.csv"

        # 读取数据重建截面
        rows = []
        with csv_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        section_pts = collect_section(rows, STATE_KEYS)
        eig = np.array(
            [complex(r, im) for r, im in zip(res["eigvals_real"], res["eigvals_imag"])]
        )

        # Poincaré 截面 (hip)
        ax1 = plt.subplot(n_configs, 3, i * 3 + 1)
        plot_section(
            ax1,
            section_pts[:, [0, 1]],
            STATE_KEYS[0],
            STATE_KEYS[1],
            title=f"{config}\nPoincaré (right_hip, n={len(section_pts)})",
        )

        # Poincaré 截面 (knee)
        ax2 = plt.subplot(n_configs, 3, i * 3 + 2)
        plot_section(
            ax2,
            section_pts[:, [2, 3]],
            STATE_KEYS[2],
            STATE_KEYS[3],
            title="Poincaré (right_knee)",
        )

        # Floquet 谱
        ax3 = plt.subplot(n_configs, 3, i * 3 + 3)
        theta = np.linspace(0, 2 * np.pi, 200)
        ax3.plot(np.cos(theta), np.sin(theta), "k--", lw=0.7, label="unit circle")

        if eig.size > 0:
            ax3.scatter(
                np.real(eig),
                np.imag(eig),
                s=100,
                c="C3",
                marker="x",
                linewidths=2,
                label=f"max|λ|={res['max_abs_floquet']:.4f}",
            )

        ax3.set_xlim(-1.5, 1.5)
        ax3.set_ylim(-1.5, 1.5)
        ax3.set_aspect("equal")
        ax3.grid(alpha=0.3)
        ax3.set_title("Floquet spectrum")
        ax3.set_xlabel("Re")
        ax3.set_ylabel("Im")
        ax3.legend(loc="upper right", fontsize=8)

    fig.suptitle("V13.7 FSM Floquet Stability Analysis", fontsize=14, y=0.995)
    fig.tight_layout()

    out_png = OUT_DIR / "v13_7_floquet_comparison.png"
    fig.savefig(out_png, dpi=150)
    print(f"\n绘制对比图: {out_png}")

    # 绘制稳定裕度对比条形图
    fig2, ax = plt.subplots(figsize=(10, 6))

    configs = ["V10 PD (V13b)"] + [r["config"] for r in results]
    max_lambdas = [v10_ref["max_abs_floquet"]] + [r["max_abs_floquet"] for r in results]
    colors = ["C0"] + [f"C{i+1}" for i in range(len(results))]

    bars = ax.bar(
        range(len(configs)), max_lambdas, color=colors, alpha=0.7, edgecolor="black"
    )
    ax.axhline(
        1.0, color="red", linestyle="--", linewidth=1.5, label="stability boundary"
    )
    ax.set_ylabel("max|λ| (Floquet multiplier)", fontsize=12)
    ax.set_title("Stability Margin Comparison: V10 PD vs V13.7 FSM", fontsize=14)
    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(configs, rotation=15, ha="right")
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    # 在条形图上标注数值
    for i, (bar, val) in enumerate(zip(bars, max_lambdas)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    fig2.tight_layout()
    out_png2 = OUT_DIR / "v13_7_stability_margin_comparison.png"
    fig2.savefig(out_png2, dpi=150)
    print(f"绘制稳定裕度对比: {out_png2}")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    # V10 参考值（来自 V13b）
    v10_ref = {
        "config": "V10_PD_baseline",
        "max_abs_floquet": 0.944,
        "alternations": 19,
        "forward_distance": 8.60,
        "E_star_J": 52.66,
        "E_std_J": 0.53,
    }

    print("=" * 60)
    print("V13.7 FSM Floquet 稳定性分析")
    print("=" * 60)
    print(f"V10 PD 参考值 (V13b): max|λ| = {v10_ref['max_abs_floquet']:.3f}")
    print("=" * 60)

    base_params = make_baseline_params(duration=20.0)
    results = []

    # 配置 1: ideal motor (无摩擦 baseline)
    print("\n[1/3] 分析: V13.7 FSM + ideal motor")
    ideal_motor = MOTOR_PRESETS["ideal"]
    params_ideal = V137Params(
        base=base_params,
        fsm=make_v137_fsm(base_params),
        hip_motor=ideal_motor,
        knee_motor=ideal_motor,
        compensate_friction=False,  # ideal 无需补偿
    )
    result_ideal = analyze_config("v13_7_fsm_ideal", params_ideal)
    results.append(result_ideal)

    # 保存单独的 JSON
    (OUT_DIR / "v13_7_fsm_ideal_floquet.json").write_text(
        json.dumps(result_ideal, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 配置 2: mx64ar + compensation
    print("\n[2/3] 分析: V13.7 FSM + mx64ar + compensation")
    mx64ar_motor = MOTOR_PRESETS["mx64ar"]
    params_comp = V137Params(
        base=base_params,
        fsm=make_v137_fsm(base_params),
        hip_motor=mx64ar_motor,
        knee_motor=mx64ar_motor,
        compensate_friction=True,
    )
    result_comp = analyze_config("v13_7_fsm_mx64ar_comp", params_comp)
    results.append(result_comp)

    (OUT_DIR / "v13_7_fsm_mx64ar_comp_floquet.json").write_text(
        json.dumps(result_comp, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 配置 3: mx64ar + no compensation
    print("\n[3/3] 分析: V13.7 FSM + mx64ar + no compensation")
    params_nocomp = V137Params(
        base=base_params,
        fsm=make_v137_fsm(base_params),
        hip_motor=mx64ar_motor,
        knee_motor=mx64ar_motor,
        compensate_friction=False,
    )
    result_nocomp = analyze_config("v13_7_fsm_mx64ar_nocomp", params_nocomp)
    results.append(result_nocomp)

    (OUT_DIR / "v13_7_fsm_mx64ar_nocomp_floquet.json").write_text(
        json.dumps(result_nocomp, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 汇总结果
    summary = {
        "v10_reference": v10_ref,
        "v13_7_results": results,
        "comparison": {
            "v10_pd_max_lambda": v10_ref["max_abs_floquet"],
            "v13_7_ideal_max_lambda": result_ideal.get("max_abs_floquet", float("nan")),
            "v13_7_comp_max_lambda": result_comp.get("max_abs_floquet", float("nan")),
            "v13_7_nocomp_max_lambda": result_nocomp.get(
                "max_abs_floquet", float("nan")
            ),
            "delta_ideal_vs_v10": result_ideal.get("max_abs_floquet", float("nan"))
            - v10_ref["max_abs_floquet"],
            "delta_comp_vs_ideal": result_comp.get("max_abs_floquet", float("nan"))
            - result_ideal.get("max_abs_floquet", float("nan")),
        },
    }

    summary_path = OUT_DIR / "v13_7_floquet_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n汇总结果: {summary_path}")

    # 绘制对比图
    plot_comparison(results, v10_ref)

    # 打印最终分析
    print("\n" + "=" * 60)
    print("最终分析")
    print("=" * 60)
    print(f"V10 PD (V13b):           max|λ| = {v10_ref['max_abs_floquet']:.4f}")
    print(
        f"V13.7 FSM (ideal):       max|λ| = {result_ideal.get('max_abs_floquet', float('nan')):.4f}  (Δ = {summary['comparison']['delta_ideal_vs_v10']:+.4f})"
    )
    print(
        f"V13.7 FSM (mx64ar+comp): max|λ| = {result_comp.get('max_abs_floquet', float('nan')):.4f}  (Δ vs ideal = {summary['comparison']['delta_comp_vs_ideal']:+.4f})"
    )
    print(
        f"V13.7 FSM (mx64ar-no):   max|λ| = {result_nocomp.get('max_abs_floquet', float('nan')):.4f}"
    )
    print("=" * 60)

    # 稳定性解释
    print("\n稳定性解释:")
    print("- |λ| < 1: 稳定（扰动收敛）")
    print("- |λ| 越接近 1: 收敛越慢（对扰动更敏感）")
    print("- |λ| ≥ 1: 不稳定（扰动发散）")

    if result_ideal.get("success"):
        lambda_ideal = result_ideal.get("max_abs_floquet", float("nan"))
        lambda_v10 = v10_ref["max_abs_floquet"]
        if lambda_ideal < lambda_v10:
            print(
                f"\nV13.7 FSM 比 V10 PD 稳定裕度更大（快 {(1-lambda_ideal/lambda_v10)*100:.1f}% 收敛）"
            )
        elif lambda_ideal > lambda_v10:
            print(
                f"\nV13.7 FSM 比 V10 PD 稳定裕度更小（慢 {(lambda_ideal/lambda_v10-1)*100:.1f}% 收敛）"
            )
        else:
            print("\nV13.7 FSM 与 V10 PD 稳定性相当")


if __name__ == "__main__":
    main()

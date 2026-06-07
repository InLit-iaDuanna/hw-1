"""V13b 扰动恢复测试。

从极限环不动点 fp = (right_hip, right_hip_vel, right_knee, right_knee_vel) 附近
±10% 偏离启动 V10 baseline 仿真（duration=20s），看：
1) Poincare 序列到 fp 的欧氏距离 d_k 是否衰减；
2) 拟合 d_k = d_0 * |λ_fit|^k 的 |λ_fit| 是否吻合 Floquet 慢模 |λ|=0.944。

学术口径：4D 中 λ_fit 是各轴沿慢模本征向量分量的复合，与 0.944 不严格等价；
但若扰动主要激发慢模，d_k 衰减率应接近 0.944。

输出：
  out/v13b_disturbance_recovery.png       4 子图衰减曲线 + 理论叠加
  out/v13b_disturbance_summary.json       每 case 的 λ_fit / 偏差 / 是否摔倒
  out/v13b_dist_<case>_data.csv           每 case 完整轨迹

不修改 V10 / V13 / V13.5 任何文件。
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1 = ROOT.parent
V10_DIR = HW1 / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1))

from simulate_rolling_foot_gait_v10 import (  # noqa: E402
    MODEL_PATH,
    RollingFootParams,
    actuator_names,
    classify_failure,
    contact_flags,
    control,
    initialize,
    make_row,
    write_model,
)

from common.poincare import collect_section  # noqa: E402

OUT_DIR = ROOT / "out"

# 与 analyze_floquet_v13b.py 完全相同的 baseline。
BASELINE = RollingFootParams(
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
    duration=20.0,
)
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")

# 来自 v13b_floquet_summary.json
FIXED_POINT = np.array(
    [-0.07294169928181025, 0.4990773585192355, 0.0336033674786127, 0.43400209335990386]
)
LAMBDA_SLOW = 0.9439820184605064  # max|λ|
SAMPLE_HZ = 160.0

# qpos/qvel 索引（见 V10 QPOS_KEYS）
IDX = {
    "right_hip": ("qpos", 5),
    "right_hip_vel": ("qvel", 5),
    "right_knee": ("qpos", 6),
    "right_knee_vel": ("qvel", 6),
}


# 4 个 case：每轴一个 +扰动；±10% 与 0.05 取大者，保证可观测。
def perturbation_for(axis: str) -> float:
    fp_val = float(FIXED_POINT[STATE_KEYS.index(axis)])
    return max(0.05, 0.10 * abs(fp_val))


def run_simulation_perturbed(
    params: RollingFootParams,
    axis: str,
    delta: float,
    sample_hz: float = SAMPLE_HZ,
) -> tuple[list[dict], dict]:
    """复刻 V10 run_simulation 的步进逻辑，但在 initialize 后立即覆盖单个分量。"""
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, params)

    # 注入扰动
    arr_name, idx = IDX[axis]
    arr = data.qpos if arr_name == "qpos" else data.qvel
    before = float(arr[idx])
    arr[idx] = before + delta
    after = float(arr[idx])
    mujoco.mj_forward(model, data)

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -params.gait_period
    alternations = 0
    contact_events: list[dict] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    mode = "left_stance"
    sample_stride = max(1, int(round(1.0 / (params.timestep * sample_hz))))

    for step in range(int(params.duration / params.timestep)):
        t = step * params.timestep
        tau = control(params, data, t, support_foot, burst_start_t)
        data.ctrl[:] = tau[:4]
        input_power = (
            float(data.ctrl[0]) * float(data.qvel[2])
            + float(data.ctrl[1]) * float(data.qvel[3])
            + float(data.ctrl[2]) * float(data.qvel[5])
            + float(data.ctrl[3]) * float(data.qvel[6])
        )
        positive_input_energy += max(0.0, input_power) * params.timestep
        net_work += input_power * params.timestep
        mode = str(tau[4])

        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: list[str] = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= params.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > params.min_event_interval
            ):
                if accepted_contact in {"left", "right"}:
                    alternations += 1
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                contact_reported[foot] = True
                contact_events.append({"time": t, "foot": foot})
                break

        if step % sample_stride == 0:
            rows.append(
                make_row(
                    model,
                    data,
                    params,
                    t,
                    left_contact,
                    right_contact,
                    support_foot,
                    mode,
                    tau[:4],
                    input_power,
                    positive_input_energy,
                )
            )

        failure = classify_failure(model, data, params, start_x, t)
        if failure:
            break

    if not rows:
        rows.append(
            make_row(
                model,
                data,
                params,
                0.0,
                False,
                False,
                support_foot,
                mode,
                (0, 0, 0, 0),
                0.0,
                0.0,
            )
        )

    summary = {
        "axis": axis,
        "delta": delta,
        "before": before,
        "after": after,
        "alternating_touchdowns": alternations,
        "forward_distance": max_x - start_x,
        "simulated_time": float(rows[-1]["time"]),
        "failure": failure or "completed",
        "actuator_names": actuator_names(model),
    }
    return rows, summary


def fit_decay_rate(distances: np.ndarray) -> tuple[float, float, int]:
    """对 d_k 拟合 log(d_k) = log(d_0) + k*log(λ_fit)，剔除接近噪声底的尾部。

    返回 (lambda_fit, log_intercept, n_used)。
    """
    d = np.asarray(distances, dtype=float)
    if d.size < 3:
        return float("nan"), float("nan"), int(d.size)
    # 噪声底：用末段 ~25% 估，若 fit 不收敛则回退全段。
    n = len(d)
    tail = d[max(2, int(0.6 * n)) :]
    floor = max(float(np.median(tail)) * 0.5, 1e-6)
    keep = d > floor
    if int(keep.sum()) < 3:
        keep = np.ones_like(d, dtype=bool)
    k = np.arange(n)[keep]
    y = np.log(d[keep])
    A = np.vstack([k, np.ones_like(k, dtype=float)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = sol
    return float(np.exp(slope)), float(intercept), int(keep.sum())


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    cases = []
    for axis in STATE_KEYS:
        delta_mag = perturbation_for(axis)
        cases.append({"axis": axis, "delta": +delta_mag})

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.flatten()

    case_results = []
    for i, case in enumerate(cases):
        axis, delta = case["axis"], case["delta"]
        print(f"[V13b-dist] case {i+1}/4: axis={axis}, delta={delta:+.4f}")
        rows, sim_summary = run_simulation_perturbed(BASELINE, axis, delta)

        csv_path = OUT_DIR / f"v13b_dist_{axis}_data.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

        section_pts = collect_section(rows, STATE_KEYS)
        n_sec = len(section_pts)
        if n_sec == 0:
            distances = np.array([])
        else:
            distances = np.linalg.norm(section_pts - FIXED_POINT[None, :], axis=1)

        lam_fit, log_intercept, n_used = fit_decay_rate(distances)
        rel_err = (
            (lam_fit - LAMBDA_SLOW) / LAMBDA_SLOW * 100.0
            if math.isfinite(lam_fit)
            else float("nan")
        )

        case_results.append(
            {
                "axis": axis,
                "delta": delta,
                "before": sim_summary["before"],
                "after": sim_summary["after"],
                "n_section_points": int(n_sec),
                "alternating_touchdowns": int(sim_summary["alternating_touchdowns"]),
                "failure": sim_summary["failure"],
                "simulated_time": sim_summary["simulated_time"],
                "distances_to_fp": [float(x) for x in distances],
                "lambda_fit": lam_fit,
                "lambda_floquet_slow": LAMBDA_SLOW,
                "rel_error_percent": rel_err,
                "n_points_used_in_fit": n_used,
                "csv": str(csv_path.name),
            }
        )

        ax = axes[i]
        if n_sec > 0:
            k_arr = np.arange(n_sec)
            ax.semilogy(k_arr, distances, "o-", label="experimental d_k", color="C0")
            if math.isfinite(lam_fit) and n_sec >= 2:
                d0 = float(distances[0]) if distances[0] > 0 else 1e-3
                k_th = np.arange(n_sec)
                ax.semilogy(
                    k_th,
                    d0 * np.power(LAMBDA_SLOW, k_th),
                    "--",
                    color="C3",
                    label=f"theory d0·{LAMBDA_SLOW:.3f}^k",
                )
                # 拟合曲线
                ax.semilogy(
                    k_th,
                    np.exp(log_intercept) * np.power(lam_fit, k_th),
                    ":",
                    color="C2",
                    label=f"fit |λ_fit|={lam_fit:.3f}",
                )
        else:
            ax.text(
                0.5,
                0.5,
                "no Poincare points",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        title_extra = (
            f" [{sim_summary['failure']}]"
            if sim_summary["failure"] != "completed"
            else ""
        )
        ax.set_title(
            f"perturb {axis} by {delta:+.3f}{title_extra}\n"
            f"|λ_fit|={lam_fit:.3f}  Δ={rel_err:+.1f}%  n_sec={n_sec}"
        )
        ax.set_xlabel("Poincaré step k")
        ax.set_ylabel("||x_k − fp||  (log)")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    fig.suptitle(
        f"V13b disturbance recovery: ±10% perturbation vs Floquet slow mode |λ|={LAMBDA_SLOW:.3f}",
        fontsize=12,
    )
    fig.tight_layout()
    out_png = OUT_DIR / "v13b_disturbance_recovery.png"
    fig.savefig(out_png, dpi=140)
    print(f"[V13b-dist] -> {out_png}")

    out_json = {
        "fixed_point": FIXED_POINT.tolist(),
        "state_keys": list(STATE_KEYS),
        "lambda_floquet_slow": LAMBDA_SLOW,
        "baseline_params": asdict(BASELINE),
        "cases": case_results,
        "academic_note": (
            "λ_fit 是各分量沿慢模本征向量分量的复合衰减率，与 4D 慢模 |λ|=0.944 "
            "不严格等价；若扰动主要激发慢模则二者应接近。"
        ),
    }
    (OUT_DIR / "v13b_disturbance_summary.json").write_text(
        json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[V13b-dist] -> {OUT_DIR / 'v13b_disturbance_summary.json'}")

    print("\n=== summary ===")
    print(
        f"{'axis':<16} {'delta':>8} {'n_sec':>6} {'lam_fit':>9} {'rel_err':>10} {'failure':>15}"
    )
    for r in case_results:
        lf = r["lambda_fit"]
        print(
            f"{r['axis']:<16} {r['delta']:>+8.4f} {r['n_section_points']:>6d} "
            f"{lf:>9.4f} {r['rel_error_percent']:>+9.2f}% {r['failure']:>15}"
        )


if __name__ == "__main__":
    main()

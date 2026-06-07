from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
V5_OUT = ROOT.parent / "passive-hybrid-compass-v5" / "out"


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    numeric: dict[str, list[float]] = {}
    text: dict[str, list[str]] = {}
    for row in rows:
        for key, value in row.items():
            try:
                numeric.setdefault(key, []).append(float(value))
            except ValueError:
                text.setdefault(key, []).append(value)
    data: dict[str, np.ndarray] = {
        key: np.array(value) for key, value in numeric.items()
    }
    for key, value in text.items():
        data[key] = np.array(value)
    return data


def write_report_text(params: dict, v5_params: dict | None) -> None:
    final_error = params["final_poincare_error"]
    v5_error = v5_params.get("final_speed_error") if v5_params else None
    v5_events = v5_params.get("valid_touchdowns") if v5_params else None
    text = f"""# V6 被动极限环步态作业表达版说明

## 版本定位

V6 是作业交付和仿生 MVE 表达版本。V5 负责证明被动极限环，V6 负责把这个机理转译成更容易理解的带膝机械单元：髋部转轴、左右大腿、小腿、膝关节、膝限位、圆脚端和斜坡。

## 为什么不是贴地滑行

V6 的展示层采用支撑脚锁定和摆动脚离地轨迹。单支撑阶段支撑脚固定在坡面，摆动腿前向屈膝并抬脚越过地面，末段膝关节伸直并触地换腿。因此它不是把脚贴在坡面滑过去，而是在视觉上表达“支撑-摆动-触地-换腿”的步态循环。

## 为什么仍然是被动极限环

不能只靠动画证明极限环。V6 报告中的极限环证据来自 V5 的混合动力学：连续单支撑相、触地事件、非弹性碰撞换腿和 Poincare 截面收敛。MuJoCo 在 V6 中只做结构回放，不作为软接触动力学证明。

V5 证明数据：有效触地事件 {v5_events if v5_events is not None else "见 V5 输出"} 次，最终 Poincare 误差 {v5_error if v5_error is not None else "见 V5 输出"}。

V6 展示数据：连续展示 {params["display_steps"]} 步，视频时长 {params["duration_s"]:.2f} s，参考截面误差末值 {final_error:.4f}。

## 作业建议表述

本设计以被动动态步行为仿生对象，提取“重力补能、惯性摆动、脚地碰撞、交替支撑和周期收敛”作为最小 MVE 功能单元。V5 通过 Poincare 截面收敛证明其被动极限环特征；V6 将该机理转译为带膝机械结构，用 MuJoCo 展示支撑脚锁定、摆动腿屈膝离地和触地换腿过程。

## 和 Creo/实物原型的对应

Creo 装配中建议重点表达髋轴、膝轴、膝限位块、圆脚端和斜坡测试面。低保真原型可用纸板或木板制作两段腿杆和限位块，用手释放或斜坡实验验证“支撑腿滚落 + 摆动腿前摆 + 触地换腿”的运动功能。
"""
    (OUT_DIR / "v6_report_text.md").write_text(text, encoding="utf-8")


def main() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    data = load_csv(OUT_DIR / "v6_mve_gait_data.csv")
    p_ref = load_csv(OUT_DIR / "v6_poincare_reference.csv")
    params = json.loads((OUT_DIR / "v6_params.json").read_text(encoding="utf-8"))
    v5_params_path = V5_OUT / "hybrid_compass_params.json"
    v5_poincare_path = V5_OUT / "hybrid_compass_poincare.csv"
    v5_params = (
        json.loads(v5_params_path.read_text(encoding="utf-8"))
        if v5_params_path.exists()
        else None
    )
    v5_poincare = load_csv(v5_poincare_path) if v5_poincare_path.exists() else p_ref

    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle(
        "V6 被动极限环步态作业表达版：证明层 + 仿生 MVE 展示层",
        fontsize=17,
        fontweight="bold",
    )

    ax = axes[0, 0]
    ax.plot(
        data["hip_x"], data["hip_z"], color="#143642", linewidth=2.0, label="髋部轨迹"
    )
    ax.scatter(
        data["left_foot_x"],
        data["left_foot_z"],
        s=2,
        color="#0f7891",
        alpha=0.25,
        label="左脚轨迹",
    )
    ax.scatter(
        data["right_foot_x"],
        data["right_foot_z"],
        s=2,
        color="#d45132",
        alpha=0.25,
        label="右脚轨迹",
    )
    ax.set_title("机构层：带膝 MVE 步态回放")
    ax.set_xlabel("x / m")
    ax.set_ylabel("z / m")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(
        data["time"], np.rad2deg(data["left_knee"]), color="#0f7891", label="左膝角"
    )
    ax.plot(
        data["time"], np.rad2deg(data["right_knee"]), color="#d45132", label="右膝角"
    )
    ax.plot(
        data["time"],
        data["swing_clearance"] * 100.0,
        color="#907f2e",
        label="摆动脚离地高度 / cm",
    )
    ax.set_title("展示层：前向屈膝与脚端离地")
    ax.set_xlabel("time / s")
    ax.set_ylabel("angle / deg 或 height / cm")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    support_code = np.where(data["support"] == "left", 1.0, -1.0)
    ax.step(
        data["time"],
        support_code,
        where="post",
        color="#62516d",
        linewidth=1.8,
        label="支撑腿切换",
    )
    ax.scatter(
        data["time"][data["contact"] == "both"],
        np.zeros(np.sum(data["contact"] == "both")),
        s=6,
        color="#d45132",
        label="触地换腿窗口",
    )
    ax.set_yticks([-1, 1], ["右腿支撑", "左腿支撑"])
    ax.set_title("步态分相：支撑脚锁定与触地换腿")
    ax.set_xlabel("time / s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    if "omega_stance" in v5_poincare:
        ax.plot(
            v5_poincare["step"],
            v5_poincare["omega_stance"],
            marker="o",
            color="#143642",
            label="V5 碰撞后角速度",
        )
        ax.axhline(
            v5_poincare["fixed_speed"][0],
            color="#d45132",
            linestyle="--",
            label="V5 固定点",
        )
        ax2 = ax.twinx()
        ax2.plot(
            v5_poincare["step"],
            v5_poincare["speed_error"],
            marker="s",
            color="#907f2e",
            label="V5 截面误差",
        )
        ax.set_ylabel("omega / rad/s")
        ax2.set_ylabel("error")
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="best")
    else:
        ax.plot(
            p_ref["step"],
            p_ref["speed"],
            marker="o",
            color="#143642",
            label="参考步间速度",
        )
        ax.plot(
            p_ref["step"], p_ref["error"], marker="s", color="#907f2e", label="参考误差"
        )
        ax.legend()
    ax.set_title("证明层：Poincare 截面收敛")
    ax.set_xlabel("step")
    ax.grid(True, alpha=0.25)

    out = OUT_DIR / "v6_mve_report.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", pad_inches=0.12)
    write_report_text(params, v5_params)
    print(out)
    print(OUT_DIR / "v6_report_text.md")


if __name__ == "__main__":
    main()

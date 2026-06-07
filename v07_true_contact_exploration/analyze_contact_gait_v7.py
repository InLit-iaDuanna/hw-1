from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from simulate_contact_gait_v7 import OUT_DIR


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


def write_report(best: dict) -> None:
    reached_touchdown_goal = best["alternating_touchdowns"] >= 4
    success = reached_touchdown_goal and best["failure"] == "completed"
    status = (
        "达到真实接触连续交替触地目标"
        if success
        else "完成多次真实交替触地，但未形成稳定长时间行走"
    )
    reason = best["failure"]
    text = f"""# V7 真实 MuJoCo 接触探索报告

## 版本定位

V7 是真实接触探索版。它尝试让带膝 MVE 机构在 MuJoCo 中依靠重力、惯性、脚地接触、摩擦、碰撞和膝限位运动。它不替代 V5 的 Poincare 极限环证明，也不替代 V6 的作业展示。

## 结果

- 状态：{status}
- 左右交替触地次数：{best["alternating_touchdowns"]}
- 髋部前进距离：{best["forward_distance"]:.3f} m
- 仿真时长：{best["simulated_time"]:.3f} s
- 失败/结束类型：{reason}
- 最佳参数：坡度 {best["params"]["slope_deg"]} deg，脚半径 {best["params"]["foot_radius"]} m，摩擦 {best["params"]["friction"]}，髋部质量 {best["params"]["hip_mass"]} kg，初始速度 {best["params"]["initial_vx"]} m/s，膝限位 {best["params"]["knee_limit_deg"]} deg。

## 解释

V7 已经捕捉到多次真实脚地接触和左右换腿，但由于最终发生 `{reason}`，不能说真实接触模型已经形成稳定被动极限环。更准确的说法是：V7 展示了从 V5/V6 的理论和回放模型进入真实接触动力学时会遇到参数敏感性，包括跌倒、卡住、穿模或弹飞。最终极限环证明仍来自 V5 的混合动力学和 Poincare 截面收敛。

## 拟解决路径

后续可继续调整质心位置、脚端曲率、膝限位阻尼、坡度和初始释放姿态；也可以在 Creo/实物原型中加入膝限位块和圆弧脚，使接触过程更接近被动步行器的物理约束。
"""
    (OUT_DIR / "v7_report_text.md").write_text(text, encoding="utf-8")


def main() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    scan = load_csv(OUT_DIR / "v7_scan_results.csv")
    data = load_csv(OUT_DIR / "v7_best_attempt_data.csv")
    best = json.loads((OUT_DIR / "v7_best_params.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle(
        "V7 真实 MuJoCo 接触探索：最佳尝试与失败分析", fontsize=17, fontweight="bold"
    )

    ax = axes[0, 0]
    n = min(20, len(scan["score"]))
    order = np.arange(n)
    ax.bar(order, scan["score"][:n], color="#143642")
    ax.set_title("参数扫描评分前 20")
    ax.set_xlabel("rank")
    ax.set_ylabel("score")
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[0, 1]
    ax.plot(data["time"], data["hip_x"], color="#143642", label="髋部 x")
    ax2 = ax.twinx()
    ax2.plot(data["time"], data["hip_clearance"], color="#907f2e", label="髋部离坡面")
    ax.set_title("髋部前进与高度")
    ax.set_xlabel("time / s")
    ax.set_ylabel("x / m")
    ax2.set_ylabel("clearance / m")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2)

    ax = axes[1, 0]
    ax.step(
        data["time"],
        data["left_contact"],
        where="post",
        label="左脚接触",
        color="#0f7891",
    )
    ax.step(
        data["time"],
        -data["right_contact"],
        where="post",
        label="右脚接触",
        color="#d45132",
    )
    ax.set_yticks([-1, 0, 1], ["右脚", "无", "左脚"])
    ax.set_title("真实接触时序")
    ax.set_xlabel("time / s")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    counts: dict[str, int] = {}
    for value in scan["failure"]:
        counts[str(value)] = counts.get(str(value), 0) + 1
    ax.bar(list(counts.keys()), list(counts.values()), color="#62516d")
    ax.set_title("失败/结束类型统计")
    ax.set_ylabel("count")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.25)

    out = OUT_DIR / "v7_contact_report.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", pad_inches=0.12)
    write_report(best)
    print(out)
    print(OUT_DIR / "v7_report_text.md")


if __name__ == "__main__":
    main()

"""量化"V10 hip 力矩饱和占空比"假说。

对 v13_baseline + 已 replay 的成功/失败案例，统计每条轨迹中
|hip_tau| >= 0.95 * hip_torque_limit 的样点占比。

如果成功案例的饱和占比稳定在 0.5-0.7，失败案例显著偏离，则证明：
V10 极限环依赖间歇性 hip 力矩饱和，不是连续 PD 跟踪。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def saturation_stats(data_csv: Path, summary_json: Path) -> dict:
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    tau_limit = float(summary["params"]["hip_torque_limit"])
    threshold = 0.95 * tau_limit

    with data_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n = len(rows)
    if n == 0:
        return {"n": 0}

    sat_left = sum(1 for r in rows if abs(float(r["left_hip_tau"])) >= threshold)
    sat_right = sum(1 for r in rows if abs(float(r["right_hip_tau"])) >= threshold)
    sat_either = sum(
        1
        for r in rows
        if abs(float(r["left_hip_tau"])) >= threshold
        or abs(float(r["right_hip_tau"])) >= threshold
    )
    sat_both = sum(
        1
        for r in rows
        if abs(float(r["left_hip_tau"])) >= threshold
        and abs(float(r["right_hip_tau"])) >= threshold
    )

    mean_abs_left = sum(abs(float(r["left_hip_tau"])) for r in rows) / n
    mean_abs_right = sum(abs(float(r["right_hip_tau"])) for r in rows) / n

    return {
        "tag": data_csv.stem.replace("_data", ""),
        "success": bool(summary["success"]),
        "touchdowns": int(summary["alternating_touchdowns"]),
        "tau_limit": tau_limit,
        "n_samples": n,
        "sat_pct_left": sat_left / n,
        "sat_pct_right": sat_right / n,
        "sat_pct_either": sat_either / n,
        "sat_pct_both": sat_both / n,
        "mean_abs_tau_left": mean_abs_left,
        "mean_abs_tau_right": mean_abs_right,
        "mean_abs_normalized": (mean_abs_left + mean_abs_right) / (2 * tau_limit),
    }


def main() -> None:
    rows = []
    for data_csv in sorted(OUT_DIR.glob("v13_*_data.csv")):
        summary_json = data_csv.with_name(
            data_csv.name.replace("_data.csv", "_summary.json")
        )
        if not summary_json.exists():
            continue
        stats = saturation_stats(data_csv, summary_json)
        rows.append(stats)
        print(
            f"[{stats['tag']:30}] succ={stats['success']!s:5} td={stats['touchdowns']:2} "
            f"tau_lim={stats['tau_limit']:5.1f}  "
            f"sat%={stats['sat_pct_either']*100:5.1f}  "
            f"mean|tau|/lim={stats['mean_abs_normalized']*100:5.1f}%"
        )

    (OUT_DIR / "v13_saturation_diagnosis.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"-> {OUT_DIR / 'v13_saturation_diagnosis.json'}")


if __name__ == "__main__":
    main()

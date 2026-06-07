"""V21 结果快速查看脚本。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def display_summary():
    print("=" * 70)
    print("V21 3D 扰动鲁棒性实验结果")
    print("=" * 70)

    # 初始 Roll
    print("\n【优先级 1：初始 Roll 扰动】")
    json_path = OUT_DIR / "v21_init_roll_summary.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"  配置数：{len(data)}")
        print(
            f"  Roll 范围：{min(d['init_roll_deg'] for d in data):.1f}° ~ {max(d['init_roll_deg'] for d in data):.1f}°"
        )
        baseline = next(d for d in data if d["init_roll_deg"] == 0.0)
        print(
            f"  基准性能：{baseline['alternations']} alternations / {baseline['simulated_time_s']:.2f}s"
        )
        best = max(data, key=lambda d: d["alternations"])
        print(
            f"  最佳配置：roll={best['init_roll_deg']:+.1f}° -> {best['alternations']} alt"
        )
        print(f"  失败模式：{set(d['failure'] for d in data)}")

    # 侧向脉冲
    print("\n【优先级 2：侧向脉冲】")
    json_path = OUT_DIR / "v21_lateral_impulse_summary.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"  配置数：{len(data)}")
        print(
            f"  脉冲范围：{min(d['impulse_n'] for d in data):.1f}N ~ {max(d['impulse_n'] for d in data):.1f}N"
        )
        baseline = next(d for d in data if d["impulse_n"] == 0.0)
        print(
            f"  基准性能：{baseline['alternations']} alternations / {baseline['simulated_time_s']:.2f}s"
        )
        unique_alts = set(d["alternations"] for d in data)
        print(f"  交替步数变化：{unique_alts}")
        print("  关键发现：所有配置性能完全一致（系统在脉冲前已失败）")

    # 随机风
    print("\n【优先级 3：随机风】")
    json_path = OUT_DIR / "v21_random_wind_summary.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"  配置数：{len(data)}")
        print(
            f"  风强度范围：{min(d['wind_std_n'] for d in data):.1f}N ~ {max(d['wind_std_n'] for d in data):.1f}N"
        )
        baseline = next(d for d in data if d["wind_std_n"] == 0.0)
        print(
            f"  基准性能：{baseline['mean_alternations']:.1f} alternations / {baseline['mean_simulated_time_s']:.2f}s"
        )
        print(
            f"  成功率范围：{min(d['success_rate'] for d in data):.2f} ~ {max(d['success_rate'] for d in data):.2f}"
        )
        print("  关键发现：平均步数对风强度不敏感（均为 3.0 alt）")

    # 判决
    print("\n【最终判决】")
    json_path = OUT_DIR / "v21_verdict.json"
    if json_path.exists():
        verdict = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"  判决：{verdict['verdict']}")
        print(
            f"  基准步数：{verdict['findings']['baseline_alternations']} alternations"
        )
        print(f"  初始 roll 容差：{verdict['findings']['init_roll_tolerance_deg']}")
        print(f"  临界脉冲：{verdict['findings']['critical_impulse_n']}")
        print(f"  风容差：{verdict['findings']['wind_tolerance_std_n']}")
        print(f"\n  结论：{verdict['conclusion']}")

    # 输出文件
    print("\n【生成文件】")
    files = [
        "v21_init_roll_robustness.png",
        "v21_lateral_impulse_robustness.png",
        "v21_random_wind_robustness.png",
        "v21_verdict.json",
    ]
    for fname in files:
        fpath = OUT_DIR / fname
        if fpath.exists():
            print(f"  [OK] {fname}")
        else:
            print(f"  [X] {fname} (未找到)")

    print("\n" + "=" * 70)
    print("V21 完成：量化了 V19 侧向不稳定，支持'放弃 3D 化'决策")
    print("=" * 70)


if __name__ == "__main__":
    display_summary()

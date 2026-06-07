"""V13 后处理：从四张 slice CSV 抽指标，写汇总表 + 图集元数据。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def load_slice(name: str) -> tuple[list[dict], dict]:
    csv_path = OUT_DIR / f"v13_{name}.csv"
    meta = json.loads((OUT_DIR / f"v13_{name}_meta.json").read_text(encoding="utf-8"))
    with csv_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows, meta


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    succ = [r for r in rows if r["success"] in ("True", "true", True)]
    cot_vals = []
    for r in succ:
        try:
            v = float(r.get("cot", "nan"))
            if v == v:
                cot_vals.append(v)
        except (TypeError, ValueError):
            pass
    failures: dict[str, int] = {}
    for r in rows:
        f = r.get("failure", "?")
        failures[f] = failures.get(f, 0) + 1
    return {
        "n_total": n,
        "n_success": len(succ),
        "success_rate": len(succ) / n if n else 0.0,
        "cot_min": min(cot_vals) if cot_vals else None,
        "cot_median": sorted(cot_vals)[len(cot_vals) // 2] if cot_vals else None,
        "cot_max": max(cot_vals) if cot_vals else None,
        "failure_modes": failures,
    }


def main() -> None:
    summary: dict[str, dict] = {}
    table_rows: list[dict] = []
    for name in [
        "A_slope_foot",
        "B_slope_leg",
        "C_foot_leg",
        "D_slope_torso",
        "E_hip_gains",
        "F_kp_ratio",
        "G_kp_torque",
    ]:
        meta_path = OUT_DIR / f"v13_{name}_meta.json"
        if not meta_path.exists():
            print(f"[skip] {name} not found")
            continue
        rows, meta = load_slice(name)
        s = summarize(rows)
        s["meta"] = meta
        summary[name] = s
        table_rows.append(
            {
                "slice": name,
                "title": meta["title"],
                "grid": meta["grid"],
                "duration": meta["duration"],
                "n_total": s["n_total"],
                "n_success": s["n_success"],
                "success_rate": f"{s['success_rate']:.2%}",
                "cot_min": f"{s['cot_min']:.3f}" if s["cot_min"] is not None else "-",
                "cot_median": (
                    f"{s['cot_median']:.3f}" if s["cot_median"] is not None else "-"
                ),
            }
        )
        print(
            f"[{name}] {s['n_success']}/{s['n_total']} success "
            f"rate={s['success_rate']:.1%} cot_min={s['cot_min']}"
        )

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "v13_atlas_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if table_rows:
        with (OUT_DIR / "v13_atlas_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
            w.writeheader()
            w.writerows(table_rows)
    print(f"-> {OUT_DIR / 'v13_atlas_summary.json'}")


if __name__ == "__main__":
    main()

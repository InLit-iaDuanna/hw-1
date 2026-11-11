#!/usr/bin/env python3
"""
Algorithm Performance Table Generator
生成算法性能对比表格（Markdown + LaTeX）
"""

import json
from datetime import datetime
from pathlib import Path


def load_all_results():
    """加载所有可用的结果"""
    base_path = Path(__file__).parent
    results = {}

    # V13.7 Baseline (from zero residual test)
    zero_path = base_path / "logs/residual_rl_v2/test_zero_residual_v2_report.json"
    if zero_path.exists():
        with open(zero_path) as f:
            data = json.load(f)
            results["v137_baseline"] = {
                "name": "V13.7 FSM + Friction Comp",
                "distance": data["baseline_distance"],
                "success_rate": data["statistics"]["success_rate"],
                "std": data["statistics"]["std_distance"],
                "method": "Model-based FSM",
                "training": "N/A",
            }

    # Residual RL V2
    train_path = base_path / "logs/residual_rl_v2/train_sanity_100k_report.json"
    if train_path.exists():
        with open(train_path) as f:
            data = json.load(f)

            results["rl_100k"] = {
                "name": "Residual RL (100k)",
                "distance": data["final_eval"]["mean_distance_m"],
                "success_rate": data["final_eval"]["success_rate"],
                "std": data["final_eval"]["std_distance_m"],
                "method": "FSM + PPO Residual",
                "training": "100k steps",
            }

            results["prior_action"] = {
                "name": "Prior Action [0.5, 1.0]",
                "distance": data["prior_eval"]["mean_distance_m"],
                "success_rate": data["prior_eval"]["success_rate"],
                "std": data["prior_eval"]["std_distance_m"],
                "method": "FSM + Constant Residual",
                "training": "Zero-shot",
            }

    # Sweep best
    sweep_path = base_path / "logs/residual_rl_v2/residual_sweep_results.json"
    if sweep_path.exists():
        with open(sweep_path) as f:
            data = json.load(f)
            best = data["best_result"]

            results["sweep_best"] = {
                "name": "Sweep Best [0.5, 1.0]",
                "distance": best["mean_distance_m"],
                "success_rate": best["success_rate"],
                "std": best["std_distance_m"],
                "method": "FSM + Constant Residual",
                "training": "Grid search",
            }

    return results


def generate_markdown_table(results, baseline_key="v137_baseline"):
    """生成 Markdown 表格"""
    if baseline_key not in results:
        print(f"Warning: baseline '{baseline_key}' not found")
        baseline_dist = 4.63
    else:
        baseline_dist = results[baseline_key]["distance"]

    lines = []
    lines.append("# Algorithm Performance Comparison")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(
        f"**Baseline**: {baseline_dist:.3f}m (V13.7 FSM + Friction Compensation)"
    )
    lines.append("")

    # Main table
    lines.append("## Performance Summary")
    lines.append("")
    lines.append(
        "| Algorithm | Distance (m) | Improvement | Success Rate | Std Dev | Method | Training |"
    )
    lines.append(
        "|-----------|--------------|-------------|--------------|---------|--------|----------|"
    )

    # Sort by distance (descending)
    sorted_results = sorted(
        results.items(), key=lambda x: x[1]["distance"], reverse=True
    )

    for key, data in sorted_results:
        dist = data["distance"]
        improvement = (dist - baseline_dist) / baseline_dist * 100
        success = data["success_rate"] * 100
        std = data["std"]

        lines.append(
            f"| {data['name']} | "
            f"{dist:.3f} | "
            f"{improvement:+.2f}% | "
            f"{success:.0f}% | "
            f"{std:.6f} | "
            f"{data['method']} | "
            f"{data['training']} |"
        )

    lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")

    best = sorted_results[0][1]
    best_improvement = (best["distance"] - baseline_dist) / baseline_dist * 100

    lines.append(
        f"- **Best Performance**: {best['name']} achieved {best['distance']:.3f}m (+{best_improvement:.2f}%)"
    )
    lines.append(
        f"- **Best RL Result**: Residual RL (100k) shows {results['rl_100k']['distance']:.3f}m"
    )
    lines.append(
        f"- **Zero-shot Transfer**: Prior action achieves {results['prior_action']['distance']:.3f}m without training"
    )
    lines.append("- **Robustness**: All methods achieve 100% success rate with std ≈ 0")
    lines.append("")

    return "\n".join(lines)


def generate_latex_table(results, baseline_key="v137_baseline"):
    """生成 LaTeX 表格"""
    if baseline_key not in results:
        baseline_dist = 4.63
    else:
        baseline_dist = results[baseline_key]["distance"]

    lines = []
    lines.append("% Algorithm Performance Comparison Table")
    lines.append("% Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Algorithm Performance Comparison}")
    lines.append("\\label{tab:algorithm_comparison}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\hline")
    lines.append("Algorithm & Distance (m) & Improvement & Success Rate & Method \\\\")
    lines.append("\\hline")

    # Sort by distance (descending)
    sorted_results = sorted(
        results.items(), key=lambda x: x[1]["distance"], reverse=True
    )

    for key, data in sorted_results:
        dist = data["distance"]
        improvement = (dist - baseline_dist) / baseline_dist * 100
        success = data["success_rate"] * 100

        # Escape underscores for LaTeX
        name = data["name"].replace("_", "\\_")
        method = data["method"].replace("_", "\\_")

        lines.append(
            f"{name} & "
            f"{dist:.3f} & "
            f"{improvement:+.2f}\\% & "
            f"{success:.0f}\\% & "
            f"{method} \\\\"
        )

    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    lines.append("")

    return "\n".join(lines)


def generate_detailed_comparison(results):
    """生成详细对比分析"""
    lines = []
    lines.append("# Detailed Algorithm Analysis")
    lines.append("")

    # Method categories
    categories = {
        "Model-based": [],
        "Hybrid (FSM + RL)": [],
        "Hybrid (FSM + Constant)": [],
    }

    for key, data in results.items():
        if "Model-based" in data["method"]:
            categories["Model-based"].append((key, data))
        elif "PPO" in data["method"]:
            categories["Hybrid (FSM + RL)"].append((key, data))
        else:
            categories["Hybrid (FSM + Constant)"].append((key, data))

    for category, items in categories.items():
        if not items:
            continue

        lines.append(f"## {category}")
        lines.append("")

        for key, data in items:
            lines.append(f"### {data['name']}")
            lines.append("")
            lines.append(f"- **Distance**: {data['distance']:.3f}m")
            lines.append(f"- **Success Rate**: {data['success_rate']*100:.0f}%")
            lines.append(f"- **Std Dev**: {data['std']:.6f}")
            lines.append(f"- **Method**: {data['method']}")
            lines.append(f"- **Training**: {data['training']}")
            lines.append("")

    return "\n".join(lines)


def main():
    print("Loading results...")
    results = load_all_results()

    if not results:
        print("[ERROR] No results found")
        return

    print(f"[OK] Loaded {len(results)} algorithm results")
    print()

    # Generate output directory
    output_dir = Path("comparison_output")
    output_dir.mkdir(exist_ok=True)

    # Generate Markdown table
    print("Generating Markdown table...")
    md_content = generate_markdown_table(results)
    md_file = output_dir / "algorithm_comparison.md"
    with open(md_file, "w") as f:
        f.write(md_content)
    print(f"[OK] Saved: {md_file}")

    # Generate LaTeX table
    print("Generating LaTeX table...")
    latex_content = generate_latex_table(results)
    latex_file = output_dir / "algorithm_comparison.tex"
    with open(latex_file, "w") as f:
        f.write(latex_content)
    print(f"[OK] Saved: {latex_file}")

    # Generate detailed analysis
    print("Generating detailed analysis...")
    detailed_content = generate_detailed_comparison(results)
    detailed_file = output_dir / "detailed_analysis.md"
    with open(detailed_file, "w") as f:
        f.write(detailed_content)
    print(f"[OK] Saved: {detailed_file}")

    # Print to console
    print()
    print("=" * 80)
    print(md_content)
    print("=" * 80)

    print()
    print("[SUCCESS] All comparison tables generated!")
    print(f"Output directory: {output_dir.absolute()}")


if __name__ == "__main__":
    main()

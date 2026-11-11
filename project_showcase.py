#!/usr/bin/env python3
"""
项目成果展示工具
快速展示项目的关键成果和指标
"""

import json
from datetime import datetime
from pathlib import Path


def show_rl_results():
    """展示RL训练结果"""
    print("=" * 80)
    print("RL TRAINING RESULTS")
    print("=" * 80)
    print()

    # 读取训练报告
    report_path = Path("logs/residual_rl_v2/train_sanity_100k_report.json")
    if report_path.exists():
        with open(report_path) as f:
            data = json.load(f)

        baseline = data["baseline"]["mean_distance_m"]
        final = data["final_eval"]["mean_distance_m"]
        improvement = (final - baseline) / baseline * 100

        print(f"Baseline (V13.7):     {baseline:.3f}m")
        print(f"100k PPO Training:    {final:.3f}m")
        print(f"Improvement:          +{improvement:.2f}%")
        print(f"Success Rate:         {data['final_eval']['success_rate']*100:.0f}%")
        print()

        print("Training Curve:")
        for eval_point in data["eval_history"]:
            ts = eval_point["timestep"]
            dist = eval_point["mean_distance_m"]
            imp = (dist - baseline) / baseline * 100
            print(f"  {ts:6d} steps: {dist:.3f}m ({imp:+.2f}%)")
    else:
        print("[ERROR] Training report not found")
    print()


def show_sweep_results():
    """展示Sweep最佳结果"""
    print("=" * 80)
    print("RESIDUAL SWEEP BEST RESULT")
    print("=" * 80)
    print()

    sweep_path = Path("logs/residual_rl_v2/residual_sweep_results.json")
    if sweep_path.exists():
        with open(sweep_path) as f:
            data = json.load(f)

        best = data["best_result"]
        print(
            f"Best Action:          [{best['left_action']:.1f}, {best['right_action']:.1f}]"
        )
        print(f"Residual Scale:       {best['residual_scale']:.2f}")
        print(f"Distance:             {best['mean_distance_m']:.3f}m")
        print(f"Improvement:          +{best['improvement_pct']:.2f}%")
        print(f"Success Rate:         {best['success_rate']*100:.0f}%")
    else:
        print("[ERROR] Sweep results not found")
    print()


def show_project_stats():
    """展示项目统计"""
    print("=" * 80)
    print("PROJECT STATISTICS")
    print("=" * 80)
    print()

    # 统计文件数量
    root = Path(".")

    py_files = len(list(root.rglob("*.py")))
    readme_files = len(list(root.rglob("README.md")))
    version_dirs = len([d for d in root.glob("v*") if d.is_dir()])
    md_reports = len(
        [
            f
            for f in root.glob("*.md")
            if any(
                keyword in f.name
                for keyword in ["SUMMARY", "REPORT", "COMPLETE", "HEALTH"]
            )
        ]
    )

    print(f"Python Files:         {py_files:,}")
    print(f"README Files:         {readme_files}")
    print(f"Version Directories:  {version_dirs}")
    print(f"Generated Reports:    {md_reports}")
    print()

    # RL训练文件
    rl_dir = root / "rl_training"
    if rl_dir.exists():
        rl_scripts = len(list(rl_dir.glob("*.py")))
        print(f"RL Training Scripts:  {rl_scripts}")

    # 模型文件
    models_dir = root / "models"
    if models_dir.exists():
        model_files = len(list(models_dir.rglob("*.zip")))
        print(f"Trained Models:       {model_files}")

    print()


def show_git_status():
    """展示Git状态"""
    print("=" * 80)
    print("GIT STATUS")
    print("=" * 80)
    print()

    import subprocess

    try:
        # 最近的提交
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("Recent Commits:")
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
            print()

        # 当前状态
        result = subprocess.run(
            ["git", "status", "--short"], capture_output=True, text=True
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.strip().split("\n") if l]
            if lines:
                print(f"Uncommitted Changes: {len(lines)} files")
                for line in lines[:5]:
                    print(f"  {line}")
                if len(lines) > 5:
                    print(f"  ... and {len(lines) - 5} more")
            else:
                print("Working Tree: Clean")
    except Exception as e:
        print(f"[ERROR] Could not get git status: {e}")

    print()


def show_code_quality():
    """展示代码质量报告"""
    print("=" * 80)
    print("CODE QUALITY SUMMARY")
    print("=" * 80)
    print()

    report_path = Path("code_quality_report.json")
    if report_path.exists():
        with open(report_path) as f:
            data = json.load(f)

        stats = data["stats"]
        print(f"Import * Usage:       {stats['import_star']} files")
        print(f"TODO Markers:         {stats['todos']}")
        print(f"Hardcoded Paths:      {stats['hardcoded_paths']} files")
        print(f"Long Functions:       {stats['long_functions']} (>100 lines)")
        print(f"Missing Docstrings:   ~{stats['missing_docstrings']} functions")
        print(f"Requirements.txt:     {stats['requirements']} files")
        print()

        # 计算评分
        issues = (
            stats["import_star"]
            + stats["hardcoded_paths"]
            + stats["long_functions"] // 10
        )

        if issues < 10:
            grade = "A"
        elif issues < 30:
            grade = "B"
        else:
            grade = "C"

        print(f"Code Quality Grade:   {grade}")
    else:
        print("[INFO] Code quality report not found")
        print("Run: python check_code_quality.py")

    print()


def main():
    print()
    print("=" * 80)
    print("PROJECT SHOWCASE - Key Results and Metrics")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    show_rl_results()
    show_sweep_results()
    show_project_stats()
    show_git_status()
    show_code_quality()

    print("=" * 80)
    print("SHOWCASE COMPLETE")
    print("=" * 80)
    print()
    print("Next Steps:")
    print(
        "  1. View visualizations: start analysis_output\\residual_rl_v2_analysis.png"
    )
    print("  2. Read reports: README.md, FINAL_REPORT.md")
    print("  3. Run analysis: python analyze_rl_results.py")
    print()


if __name__ == "__main__":
    main()

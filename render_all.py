#!/usr/bin/env python3
"""
hw-1 批量渲染脚本

功能：
- 并行渲染所有版本的动画
- 支持版本筛选
- 自动检测render脚本
- 进度追踪与错误报告

用法：
    python render_all.py                              # 渲染所有版本
    python render_all.py --versions v10 v13_6 v18     # 渲染指定版本
    python render_all.py --parallel 4                 # 4个并行任务
    python render_all.py --stages 2                   # 只渲染阶段2（机械升级）
    python render_all.py --dry-run                    # 预览不执行
"""

import argparse
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Optional
import json
from datetime import datetime

# 项目根目录
ROOT = Path(__file__).parent.resolve()
VENV_PYTHON = ROOT / ".venv-mujoco" / "Scripts" / "python.exe"

# 版本分组定义
STAGE_DEFINITIONS = {
    1: {
        "name": "理论验证与被动极限环",
        "versions": ["v01_mujoco_compass_gait", "v02_rugged_rimless_limit_cycle",
                     "v03_compass_limit_cycle", "v04_kneed_limit_cycle", "v05_hybrid_compass_proof"]
    },
    2: {
        "name": "机械升级与控制律探索",
        "versions": [
            "v06_mve_gait_homework", "v07_true_contact_exploration",
            "v08_quasi_passive_assisted", "v09_stable_biomimetic_gait",
            "v10_rolling_foot_biomimetic_gait", "v11_rugged_terrain_robustness",
            "v12_energy_cot_analysis",
            "v13b_floquet_long_run", "v13_5_robust_hip_control", "v13_6_event_driven_fsm",
            "v13_6_refactored", "v13_7_floquet_analysis", "v13_7_friction_compensation",
            "v13_7_refactored", "v13_parameter_sensitivity_atlas",
            "v14b_state_machine_hip", "v14c_arm_mass_lightening", "v14_passive_arms",
            "v15_1_sea_direct", "v15_2_strict_sea", "v15_hip_sea_scaffold",
            "v16_motor_dynamics", "v16_refactored", "v17_refactored", "v17_state_estimation"
        ]
    },
    3: {
        "name": "3D化探索",
        "versions": ["v18_3d_lateral_stability", "v19_hip_abduction_active",
                     "v20_step_width_control", "v21_3d_perturbation_robustness"]
    },
    4: {
        "name": "硬件转译与实物验证",
        "versions": ["v22_hardware_design", "v23_system_identification", "v24_sim_to_real"]
    }
}

# 已知的render脚本命名模式
RENDER_SCRIPT_PATTERNS = [
    "render_*.py",
    "*render*.py"
]


def find_render_scripts(version_dir: Path) -> List[Path]:
    """查找版本目录下的render脚本"""
    scripts = []
    for pattern in RENDER_SCRIPT_PATTERNS:
        scripts.extend(version_dir.glob(pattern))

    # 排除不相关的文件
    scripts = [s for s in scripts if "render" in s.name.lower() and s.suffix == ".py"]

    # 优先选择主render脚本
    primary_names = ["render.py", f"render_{version_dir.name}.py"]
    for name in primary_names:
        primary = version_dir / name
        if primary.exists():
            return [primary]

    return sorted(scripts)


def get_all_versions() -> Dict[str, Path]:
    """获取所有版本目录"""
    versions = {}
    for stage, info in STAGE_DEFINITIONS.items():
        for version in info["versions"]:
            version_dir = ROOT / version
            if version_dir.is_dir():
                versions[version] = version_dir
    return versions


def render_version(version: str, version_dir: Path, dry_run: bool = False) -> Dict:
    """渲染单个版本"""
    result = {
        "version": version,
        "status": "unknown",
        "scripts_found": 0,
        "scripts_executed": 0,
        "errors": [],
        "outputs": []
    }

    # 查找render脚本
    scripts = find_render_scripts(version_dir)
    result["scripts_found"] = len(scripts)

    if not scripts:
        result["status"] = "no_script"
        result["errors"].append("未找到render脚本")
        return result

    # 执行所有render脚本
    for script in scripts:
        script_name = script.name

        if dry_run:
            print(f"  [DRY-RUN] 将执行: {script_name}")
            result["scripts_executed"] += 1
            continue

        try:
            print(f"  执行: {script_name}")

            # 运行脚本
            proc = subprocess.run(
                [str(VENV_PYTHON), str(script)],
                cwd=str(version_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if proc.returncode == 0:
                result["scripts_executed"] += 1
                # 查找输出的mp4文件
                out_dir = version_dir / "out"
                if out_dir.exists():
                    mp4_files = list(out_dir.glob("*.mp4"))
                    result["outputs"].extend([str(f.relative_to(ROOT)) for f in mp4_files])
            else:
                result["errors"].append(f"{script_name}: 返回码 {proc.returncode}")
                if proc.stderr:
                    result["errors"].append(f"stderr: {proc.stderr[:200]}")

        except subprocess.TimeoutExpired:
            result["errors"].append(f"{script_name}: 超时（>10分钟）")
        except Exception as e:
            result["errors"].append(f"{script_name}: {type(e).__name__}: {str(e)}")

    # 设置最终状态
    if result["scripts_executed"] == result["scripts_found"]:
        result["status"] = "success"
    elif result["scripts_executed"] > 0:
        result["status"] = "partial"
    else:
        result["status"] = "failed"

    return result


def print_summary(results: List[Dict]):
    """打印汇总报告"""
    print("\n" + "="*80)
    print("渲染汇总")
    print("="*80)

    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    partial = sum(1 for r in results if r["status"] == "partial")
    failed = sum(1 for r in results if r["status"] == "failed")
    no_script = sum(1 for r in results if r["status"] == "no_script")

    print(f"\n总计: {total} 个版本")
    print(f"  ✓ 成功: {success}")
    print(f"  ⚠ 部分成功: {partial}")
    print(f"  ✗ 失败: {failed}")
    print(f"  - 无脚本: {no_script}")

    total_scripts = sum(r["scripts_found"] for r in results)
    executed_scripts = sum(r["scripts_executed"] for r in results)
    print(f"\n脚本执行: {executed_scripts}/{total_scripts}")

    total_outputs = sum(len(r["outputs"]) for r in results)
    print(f"生成视频: {total_outputs} 个")

    # 失败详情
    if failed > 0 or partial > 0:
        print("\n" + "-"*80)
        print("错误详情:")
        print("-"*80)
        for r in results:
            if r["status"] in ["failed", "partial"] and r["errors"]:
                print(f"\n{r['version']}:")
                for error in r["errors"]:
                    print(f"  - {error}")


def save_results(results: List[Dict], output_file: Path):
    """保存结果到JSON"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_versions": len(results),
        "summary": {
            "success": sum(1 for r in results if r["status"] == "success"),
            "partial": sum(1 for r in results if r["status"] == "partial"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "no_script": sum(1 for r in results if r["status"] == "no_script")
        },
        "results": results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n详细报告已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="hw-1 批量渲染脚本")
    parser.add_argument("--versions", nargs="+", metavar="VERSION",
                        help="指定要渲染的版本（如 v10 v13_6）")
    parser.add_argument("--stages", type=int, nargs="+", choices=[1,2,3,4],
                        help="指定要渲染的阶段（1=理论 2=机械 3=3D 4=硬件）")
    parser.add_argument("--parallel", type=int, default=2, metavar="N",
                        help="并行任务数（默认2）")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览不执行")
    parser.add_argument("--output", type=Path, default=ROOT / "render_results.json",
                        help="结果保存路径")

    args = parser.parse_args()

    # 检查Python解释器
    if not VENV_PYTHON.exists():
        print(f"错误: 未找到虚拟环境Python解释器: {VENV_PYTHON}", file=sys.stderr)
        print("请确保已创建 .venv-mujoco 虚拟环境", file=sys.stderr)
        sys.exit(1)

    # 确定要渲染的版本
    all_versions = get_all_versions()

    if args.versions:
        # 用户指定版本
        target_versions = {}
        for v in args.versions:
            # 支持简写 v10 -> v10_rolling_foot_biomimetic_gait
            matched = [k for k in all_versions.keys() if k.startswith(v)]
            if matched:
                for m in matched:
                    target_versions[m] = all_versions[m]
            else:
                print(f"警告: 未找到版本 {v}", file=sys.stderr)
    elif args.stages:
        # 用户指定阶段
        target_versions = {}
        for stage in args.stages:
            for version in STAGE_DEFINITIONS[stage]["versions"]:
                if version in all_versions:
                    target_versions[version] = all_versions[version]
    else:
        # 渲染全部
        target_versions = all_versions

    if not target_versions:
        print("错误: 没有找到要渲染的版本", file=sys.stderr)
        sys.exit(1)

    print(f"准备渲染 {len(target_versions)} 个版本")
    if args.dry_run:
        print("[DRY-RUN 模式 - 不会实际执行]")
    print(f"并行任务数: {args.parallel}")
    print("-"*80)

    # 并行渲染
    results = []
    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(render_version, version, path, args.dry_run): version
            for version, path in target_versions.items()
        }

        for future in as_completed(futures):
            version = futures[future]
            print(f"\n处理: {version}")

            try:
                result = future.result()
                results.append(result)

                # 实时状态
                status_icon = {
                    "success": "✓",
                    "partial": "⚠",
                    "failed": "✗",
                    "no_script": "-"
                }.get(result["status"], "?")

                print(f"  状态: {status_icon} {result['status']}")
                print(f"  脚本: {result['scripts_executed']}/{result['scripts_found']}")
                if result["outputs"]:
                    print(f"  输出: {len(result['outputs'])} 个视频")

            except Exception as e:
                print(f"  错误: {type(e).__name__}: {str(e)}")
                results.append({
                    "version": version,
                    "status": "failed",
                    "errors": [f"{type(e).__name__}: {str(e)}"]
                })

    # 打印汇总
    print_summary(results)

    # 保存结果
    if not args.dry_run:
        save_results(results, args.output)

    # 退出码
    failed_count = sum(1 for r in results if r["status"] == "failed")
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()

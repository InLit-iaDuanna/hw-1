"""
自动化流水线执行脚本（后台运行版本）

此脚本会：
1. 启动阶段1（专家轨迹收集）- 后台运行
2. 等待阶段1完成后，启动阶段2（BC训练）
3. 等待阶段2完成后，启动阶段3（PPO训练）- 后台运行
4. 所有训练完成后，执行阶段4（评估对比）

监控进度并生成中间报告
"""

import time
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime


def check_file_exists(file_path: Path) -> bool:
    """检查文件是否存在"""
    return file_path.exists()


def get_file_size_mb(file_path: Path) -> float:
    """获取文件大小（MB）"""
    if file_path.exists():
        return file_path.stat().st_size / 1024 / 1024
    return 0.0


def run_command_blocking(cmd: list, stage_name: str) -> bool:
    """
    阻塞式运行命令

    Args:
        cmd: 命令列表
        stage_name: 阶段名称

    Returns:
        是否成功
    """
    print(f"\n{'='*80}")
    print(f"开始: {stage_name}")
    print(f"{'='*80}")
    print(f"命令: {' '.join(cmd)}")
    print()

    start_time = time.time()

    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        elapsed = time.time() - start_time

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        print(f"\n[OK] {stage_name} 完成 (耗时: {elapsed/60:.1f}分钟)")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n[ERROR] {stage_name} 失败 (耗时: {elapsed/60:.1f}分钟)")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n[中断] {stage_name} 被用户中断 (耗时: {elapsed/60:.1f}分钟)")
        return False


def monitor_stage(file_to_check: Path, stage_name: str, check_interval: int = 30):
    """
    监控后台任务进度

    Args:
        file_to_check: 用于检测完成的文件
        stage_name: 阶段名称
        check_interval: 检查间隔（秒）
    """
    print(f"\n{'='*80}")
    print(f"监控: {stage_name}")
    print(f"{'='*80}")
    print(f"等待文件生成: {file_to_check}")
    print()

    start_time = time.time()
    last_size = 0

    while not file_to_check.exists():
        elapsed = time.time() - start_time
        print(f"等待中... (已等待 {elapsed/60:.1f} 分钟)", end='\r')
        time.sleep(check_interval)

    # 文件存在后，继续监控大小变化
    print(f"\n文件已生成: {file_to_check}")
    print("监控文件大小变化...")

    stable_count = 0
    while stable_count < 3:  # 连续3次检查大小不变，认为完成
        current_size = get_file_size_mb(file_to_check)

        if current_size == last_size:
            stable_count += 1
        else:
            stable_count = 0

        print(f"文件大小: {current_size:.2f} MB (稳定计数: {stable_count}/3)", end='\r')
        last_size = current_size
        time.sleep(check_interval)

    elapsed = time.time() - start_time
    print(f"\n[OK] {stage_name} 完成 (耗时: {elapsed/60:.1f}分钟)")
    print(f"最终文件大小: {get_file_size_mb(file_to_check):.2f} MB")


def main():
    """主流程"""
    RL_TRAINING_DIR = Path(__file__).resolve().parent

    print("=" * 80)
    print("Imitation Learning + PPO 自动化流水线")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    pipeline_start = time.time()

    # ========== 阶段1: 收集专家轨迹 ==========
    stage1_output = RL_TRAINING_DIR / "v137_expert_trajectories.pkl"

    if not stage1_output.exists():
        print("\n阶段1: 收集V13.7专家轨迹")
        print("注意: 此阶段可能已在后台运行，将监控其进度")
        print()

        # 检查是否需要启动
        response = input("阶段1是否已在后台运行? [Y/n]: ").strip().lower()

        if response in ['n', 'no']:
            # 启动阶段1
            cmd = [
                sys.executable,
                str(RL_TRAINING_DIR / "collect_expert_trajectories.py"),
                "--episodes", "50",
                "--max-steps", "600"
            ]
            if not run_command_blocking(cmd, "阶段1: 收集专家轨迹"):
                print("\n流程终止")
                return
        else:
            # 监控后台任务
            monitor_stage(stage1_output, "阶段1: 收集专家轨迹")
    else:
        print(f"\n[跳过] 阶段1: 专家轨迹已存在 ({get_file_size_mb(stage1_output):.2f} MB)")

    # 加载阶段1统计信息
    stage1_stats_path = RL_TRAINING_DIR / "v137_expert_trajectories.json"
    if stage1_stats_path.exists():
        with open(stage1_stats_path, "r", encoding="utf-8") as f:
            stage1_stats = json.load(f)
        print("\n阶段1统计:")
        print(f"  Episodes: {stage1_stats['num_episodes']}")
        print(f"  Transitions: {stage1_stats['total_transitions']}")
        print(f"  平均距离: {stage1_stats['avg_distance']:.3f}m")
        print(f"  平均触地: {stage1_stats['avg_touchdowns']:.1f}")

    # ========== 阶段2: 行为克隆训练 ==========
    stage2_output = RL_TRAINING_DIR / "best_bc_policy_weights.pth"

    if not stage2_output.exists():
        cmd = [
            sys.executable,
            str(RL_TRAINING_DIR / "train_behavioral_cloning.py"),
            "--epochs", "50",
            "--batch-size", "256",
            "--lr", "0.001"
        ]
        if not run_command_blocking(cmd, "阶段2: 行为克隆训练"):
            print("\n流程终止")
            return
    else:
        print(f"\n[跳过] 阶段2: BC模型已存在 ({get_file_size_mb(stage2_output):.2f} MB)")

    # 加载阶段2统计信息
    stage2_stats_path = RL_TRAINING_DIR / "bc_training_history.json"
    if stage2_stats_path.exists():
        with open(stage2_stats_path, "r", encoding="utf-8") as f:
            stage2_stats = json.load(f)
        print("\n阶段2统计:")
        print(f"  最佳验证损失: {stage2_stats['best_val_loss']:.6f}")
        print(f"  最终训练损失: {stage2_stats['final_train_loss']:.6f}")
        print(f"  训练样本数: {stage2_stats['n_train']}")

    # ========== 阶段3: PPO训练 (后台) ==========
    stage3_output = RL_TRAINING_DIR / "models_bc_warmstart" / "ppo_bc_warmstart_final.zip"

    print("\n" + "="*80)
    print("阶段3: PPO Warm-Start训练")
    print("="*80)
    print("此阶段将在后台运行（预计耗时: 2-4小时，取决于硬件）")
    print("训练参数:")
    print("  - 总步数: 5,000,000")
    print("  - 并行环境: 8")
    print("  - 学习率: 3e-4")
    print()

    response = input("是否启动阶段3训练? [Y/n]: ").strip().lower()

    if response not in ['n', 'no']:
        cmd = [
            sys.executable,
            str(RL_TRAINING_DIR / "train_ppo_with_bc_init.py"),
            "--timesteps", "5000000",
            "--envs", "8",
            "--lr", "0.0003"
        ]

        print(f"\n启动命令: {' '.join(cmd)}")
        print("\n注意:")
        print("  1. 训练将在后台运行")
        print("  2. 可使用 TensorBoard 监控进度:")
        print("     tensorboard --logdir ./logs_bc_warmstart/tensorboard")
        print("  3. 模型将保存到 ./models_bc_warmstart/")
        print()

        # 启动后台进程
        log_file = RL_TRAINING_DIR / "ppo_training.log"
        with open(log_file, "w") as f:
            subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=RL_TRAINING_DIR
            )

        print(f"[OK] PPO训练已在后台启动")
        print(f"日志文件: {log_file}")
        print()
        print("您可以:")
        print("  - 运行此脚本将等待训练完成后执行评估")
        print("  - 或手动中断(Ctrl+C)，稍后运行评估脚本")
        print()

        # 等待训练完成
        try:
            monitor_stage(stage3_output, "阶段3: PPO训练", check_interval=60)
        except KeyboardInterrupt:
            print("\n监控已中断，PPO训练继续在后台运行")
            print("完成后可手动运行评估:")
            print("  python evaluate_and_compare.py")
            return

    else:
        print("[跳过] 阶段3: PPO训练")

    # ========== 阶段4: 评估对比 ==========
    if stage3_output.exists():
        cmd = [
            sys.executable,
            str(RL_TRAINING_DIR / "evaluate_and_compare.py"),
            "--episodes", "20"
        ]
        run_command_blocking(cmd, "阶段4: 模型对比评估")
    else:
        print("\n[跳过] 阶段4: PPO模型尚未生成，无法评估")

    # ========== 完成总结 ==========
    pipeline_elapsed = time.time() - pipeline_start

    print("\n" + "="*80)
    print("流水线执行完毕")
    print("="*80)
    print(f"总耗时: {pipeline_elapsed/3600:.2f} 小时")
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("生成的文件:")
    files_to_check = [
        ("专家轨迹", RL_TRAINING_DIR / "v137_expert_trajectories.pkl"),
        ("BC模型", RL_TRAINING_DIR / "best_bc_policy_weights.pth"),
        ("BC训练曲线", RL_TRAINING_DIR / "bc_training_curve.png"),
        ("PPO模型", stage3_output),
        ("评估结果", RL_TRAINING_DIR / "evaluation_results" / "comparison_results.json"),
    ]

    for name, path in files_to_check:
        if path.exists():
            size = get_file_size_mb(path)
            print(f"  ✓ {name}: {path.name} ({size:.2f} MB)")
        else:
            print(f"  ✗ {name}: 未生成")

    print()


if __name__ == "__main__":
    main()

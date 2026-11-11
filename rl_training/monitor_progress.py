"""
进度监控工具

实时监控Imitation Learning流水线的执行进度
"""

import time
from pathlib import Path
import json
from datetime import datetime


def check_stage_progress():
    """检查各阶段进度"""
    RL_TRAINING_DIR = Path(r"D:\Dunna\Documents\hw-1\rl_training")

    print("=" * 80)
    print("Imitation Learning + PPO 流水线进度监控")
    print("=" * 80)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 阶段1: 专家轨迹收集
    print("[阶段1] 收集V13.7专家轨迹")
    print("-" * 80)

    traj_pkl = RL_TRAINING_DIR / "v137_expert_trajectories.pkl"
    traj_json = RL_TRAINING_DIR / "v137_expert_trajectories.json"

    if traj_pkl.exists():
        size_mb = traj_pkl.stat().st_size / 1024 / 1024
        modified = datetime.fromtimestamp(traj_pkl.stat().st_mtime)
        print(f"  ✓ 轨迹文件已生成")
        print(f"    文件: {traj_pkl.name}")
        print(f"    大小: {size_mb:.2f} MB")
        print(f"    修改时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

        if traj_json.exists():
            with open(traj_json, "r", encoding="utf-8") as f:
                stats = json.load(f)
            print(f"    Episodes: {stats['num_episodes']}")
            print(f"    Transitions: {stats['total_transitions']}")
            print(f"    平均距离: {stats['avg_distance']:.3f}m")
            print(f"    平均触地: {stats['avg_touchdowns']:.1f}")
    else:
        print(f"  ⏳ 等待生成中...")
        print(f"    预期文件: {traj_pkl.name}")

    print()

    # 阶段2: 行为克隆训练
    print("[阶段2] 行为克隆预训练")
    print("-" * 80)

    bc_weights = RL_TRAINING_DIR / "best_bc_policy_weights.pth"
    bc_curve = RL_TRAINING_DIR / "bc_training_curve.png"
    bc_history = RL_TRAINING_DIR / "bc_training_history.json"

    if bc_weights.exists():
        size_mb = bc_weights.stat().st_size / 1024 / 1024
        print(f"  ✓ BC模型已训练完成")
        print(f"    模型文件: {bc_weights.name}")
        print(f"    大小: {size_mb:.2f} MB")

        if bc_history.exists():
            with open(bc_history, "r", encoding="utf-8") as f:
                history = json.load(f)
            print(f"    最佳验证损失: {history['best_val_loss']:.6f}")
            print(f"    最终训练损失: {history['final_train_loss']:.6f}")
            print(f"    训练轮数: {history['num_epochs']}")

        if bc_curve.exists():
            print(f"    训练曲线: {bc_curve.name}")
    else:
        print(f"  ⏳ 等待训练...")
        print(f"    预期文件: {bc_weights.name}")

    print()

    # 阶段3: PPO训练
    print("[阶段3] PPO Warm-Start训练")
    print("-" * 80)

    ppo_model_dir = RL_TRAINING_DIR / "models_bc_warmstart"
    ppo_log_dir = RL_TRAINING_DIR / "logs_bc_warmstart"
    ppo_final = ppo_model_dir / "ppo_bc_warmstart_final.zip"
    checkpoint_dir = ppo_log_dir / "checkpoints"

    if ppo_final.exists():
        size_mb = ppo_final.stat().st_size / 1024 / 1024
        modified = datetime.fromtimestamp(ppo_final.stat().st_mtime)
        print(f"  ✓ PPO训练已完成")
        print(f"    模型文件: {ppo_final.name}")
        print(f"    大小: {size_mb:.2f} MB")
        print(f"    完成时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    elif checkpoint_dir.exists():
        checkpoints = list(checkpoint_dir.glob("*.zip"))
        if checkpoints:
            latest_ckpt = max(checkpoints, key=lambda p: p.stat().st_mtime)
            size_mb = latest_ckpt.stat().st_size / 1024 / 1024
            modified = datetime.fromtimestamp(latest_ckpt.stat().st_mtime)

            # 从文件名提取步数
            import re

            match = re.search(r"(\d+)_steps", latest_ckpt.name)
            if match:
                steps = int(match.group(1))
                progress = steps / 5_000_000 * 100
                print(f"  🔄 PPO训练进行中...")
                print(f"    最新检查点: {latest_ckpt.name}")
                print(f"    训练步数: {steps:,} / 5,000,000 ({progress:.1f}%)")
                print(f"    更新时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"  🔄 PPO训练进行中...")
                print(f"    最新检查点: {latest_ckpt.name}")
        else:
            print(f"  ⏳ 等待训练启动...")
    else:
        print(f"  ⏳ 等待训练启动...")
        print(f"    预期目录: {checkpoint_dir}")

    print()

    # 阶段4: 评估对比
    print("[阶段4] 模型对比评估")
    print("-" * 80)

    eval_dir = RL_TRAINING_DIR / "evaluation_results"
    eval_results = eval_dir / "comparison_results.json"
    eval_plot = eval_dir / "comparison_plot.png"

    if eval_results.exists():
        with open(eval_results, "r", encoding="utf-8") as f:
            results = json.load(f)

        print(f"  ✓ 评估已完成")
        print(f"    结果文件: {eval_results.name}")
        print(f"    评估模型数: {len(results)}")

        for result in results:
            stats = result["statistics"]
            print(f"\n    [{result['model_name']}]")
            print(
                f"      平均奖励: {stats['mean_reward']:.2f} ± {stats['std_reward']:.2f}"
            )
            print(f"      平均距离: {stats['mean_distance']:.3f}m")
            print(f"      成功率: {stats['success_rate']*100:.1f}%")

        if eval_plot.exists():
            print(f"\n    对比图表: {eval_plot.name}")
    else:
        print(f"  ⏳ 等待评估...")
        print(f"    预期文件: {eval_results.name}")

    print()
    print("=" * 80)


def monitor_loop(interval: int = 60):
    """循环监控"""
    print("开始循环监控（按Ctrl+C退出）")
    print()

    try:
        while True:
            check_stage_progress()
            print(f"\n下次检查: {interval}秒后")
            print("按Ctrl+C退出监控")
            print("-" * 80)
            time.sleep(interval)
            print("\n" * 2)

    except KeyboardInterrupt:
        print("\n\n监控已停止")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="监控流水线进度")
    parser.add_argument("--loop", action="store_true", help="循环监控模式")
    parser.add_argument("--interval", type=int, default=60, help="检查间隔（秒）")

    args = parser.parse_args()

    if args.loop:
        monitor_loop(args.interval)
    else:
        check_stage_progress()

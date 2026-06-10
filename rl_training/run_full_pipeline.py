"""
完整的Imitation Learning + PPO微调流程执行脚本

按顺序执行4个阶段：
1. 收集V13.7专家轨迹
2. 行为克隆预训练
3. PPO warm-start训练
4. 对比评估

可选择从任意阶段开始执行
"""

import sys
import subprocess
from pathlib import Path
import argparse


def run_stage(stage_name: str, script_name: str, args: list = None):
    """
    运行单个阶段

    Args:
        stage_name: 阶段名称
        script_name: Python脚本名称
        args: 额外的命令行参数
    """
    print("\n" + "=" * 80)
    print(f"阶段: {stage_name}")
    print("=" * 80)
    print()

    RL_TRAINING_DIR = Path(__file__).resolve().parent
    script_path = RL_TRAINING_DIR / script_name

    if not script_path.exists():
        print(f"[ERROR] 脚本不存在: {script_path}")
        return False

    # 构建命令
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"执行命令: {' '.join(cmd)}")
    print()

    # 执行脚本
    try:
        result = subprocess.run(cmd, check=True)
        print()
        print(f"[OK] {stage_name} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print()
        print(f"[ERROR] {stage_name} 失败: {e}")
        return False
    except KeyboardInterrupt:
        print()
        print(f"[中断] {stage_name} 被用户中断")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="完整的Imitation Learning + PPO微调流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 执行完整流程
  python run_full_pipeline.py

  # 从阶段2开始（假设已有专家轨迹）
  python run_full_pipeline.py --start-from 2

  # 只执行阶段1和2
  python run_full_pipeline.py --end-at 2

  # 自定义参数
  python run_full_pipeline.py --episodes 100 --bc-epochs 100 --ppo-timesteps 10000000
        """
    )

    parser.add_argument("--start-from", type=int, default=1, choices=[1, 2, 3, 4],
                        help="从哪个阶段开始 (1-4)")
    parser.add_argument("--end-at", type=int, default=4, choices=[1, 2, 3, 4],
                        help="在哪个阶段结束 (1-4)")

    # 阶段1参数
    parser.add_argument("--episodes", type=int, default=50,
                        help="收集的专家轨迹episode数")
    parser.add_argument("--max-steps", type=int, default=600,
                        help="每个episode的最大步数")

    # 阶段2参数
    parser.add_argument("--bc-epochs", type=int, default=50,
                        help="行为克隆训练轮数")
    parser.add_argument("--bc-batch-size", type=int, default=256,
                        help="行为克隆批大小")
    parser.add_argument("--bc-lr", type=float, default=1e-3,
                        help="行为克隆学习率")

    # 阶段3参数
    parser.add_argument("--ppo-timesteps", type=int, default=5_000_000,
                        help="PPO训练总步数")
    parser.add_argument("--ppo-envs", type=int, default=8,
                        help="PPO并行环境数")
    parser.add_argument("--ppo-lr", type=float, default=3e-4,
                        help="PPO学习率")

    # 阶段4参数
    parser.add_argument("--eval-episodes", type=int, default=20,
                        help="评估的episode数")

    args = parser.parse_args()

    # 验证阶段范围
    if args.start_from > args.end_at:
        print("[ERROR] start-from 不能大于 end-at")
        return

    print("=" * 80)
    print("Imitation Learning + PPO 微调完整流程")
    print("=" * 80)
    print()
    print(f"执行阶段: {args.start_from} -> {args.end_at}")
    print()

    stages = []

    # 阶段1: 收集专家轨迹
    if args.start_from <= 1 <= args.end_at:
        stages.append({
            "name": "阶段1: 收集V13.7专家轨迹",
            "script": "collect_expert_trajectories.py",
            "args": [
                "--episodes", str(args.episodes),
                "--max-steps", str(args.max_steps),
            ]
        })

    # 阶段2: 行为克隆预训练
    if args.start_from <= 2 <= args.end_at:
        stages.append({
            "name": "阶段2: 行为克隆预训练",
            "script": "train_behavioral_cloning.py",
            "args": [
                "--epochs", str(args.bc_epochs),
                "--batch-size", str(args.bc_batch_size),
                "--lr", str(args.bc_lr),
            ]
        })

    # 阶段3: PPO warm-start训练
    if args.start_from <= 3 <= args.end_at:
        stages.append({
            "name": "阶段3: PPO Warm-Start训练",
            "script": "train_ppo_with_bc_init.py",
            "args": [
                "--timesteps", str(args.ppo_timesteps),
                "--envs", str(args.ppo_envs),
                "--lr", str(args.ppo_lr),
            ]
        })

    # 阶段4: 对比评估
    if args.start_from <= 4 <= args.end_at:
        stages.append({
            "name": "阶段4: 对比评估",
            "script": "evaluate_and_compare.py",
            "args": [
                "--episodes", str(args.eval_episodes),
            ]
        })

    # 执行各阶段
    for i, stage in enumerate(stages, 1):
        success = run_stage(stage["name"], stage["script"], stage["args"])

        if not success:
            print()
            print("=" * 80)
            print(f"流程在 {stage['name']} 失败或中断")
            print("=" * 80)
            return

        # 不是最后一个阶段时，询问是否继续
        if i < len(stages):
            print()
            response = input(f"继续执行下一阶段? [Y/n]: ").strip().lower()
            if response in ['n', 'no']:
                print("流程已停止")
                return

    # 全部完成
    print()
    print("=" * 80)
    print("完整流程执行完毕!")
    print("=" * 80)
    print()
    print("生成的文件:")
    print("  1. v137_expert_trajectories.pkl - 专家轨迹数据")
    print("  2. bc_policy_weights.pth - BC模型权重")
    print("  3. best_bc_policy_weights.pth - 最佳BC模型权重")
    print("  4. bc_training_curve.png - BC训练曲线")
    print("  5. ./models_bc_warmstart/ppo_bc_warmstart_final.zip - BC+PPO最终模型")
    print("  6. ./logs_bc_warmstart/ - PPO训练日志")
    print("  7. ./evaluation_results/ - 对比评估结果")
    print()


if __name__ == "__main__":
    main()

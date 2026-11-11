"""
阶段3：PPO with Behavioral Cloning Warm-Start

将行为克隆预训练的权重加载到PPO policy，然后继续RL训练
使用修正后的reward函数（能量目标 + 交替触地奖励）
"""

import os
import sys
from pathlib import Path

import torch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.policies import ActorCriticPolicy


def make_env(rank, seed=0):
    """
    创建环境实例（多进程安全）

    Args:
        rank: 进程索引
        seed: 随机种子
    """

    def _init():
        from environment import CompassGaitEnv

        env = CompassGaitEnv(
            reward_type="energy_efficient",
            fall_height_threshold=0.2,
            max_steps=1000,
            frame_skip=20,
        )
        env.reset(seed=seed + rank)
        return env

    set_random_seed(seed)
    return _init


def load_bc_weights_into_ppo(ppo_model: PPO, bc_weights_path: str):
    """
    将行为克隆权重加载到PPO policy网络

    Args:
        ppo_model: PPO模型实例
        bc_weights_path: BC权重文件路径
    """
    print(f"加载BC权重: {bc_weights_path}")

    # 加载BC权重
    checkpoint = torch.load(bc_weights_path, map_location=ppo_model.device)
    bc_state_dict = checkpoint["model_state_dict"]

    print(f"BC模型训练信息:")
    print(f"  Epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"  Train Loss: {checkpoint.get('train_loss', 'N/A'):.6f}")
    print(f"  Val Loss: {checkpoint.get('val_loss', 'N/A'):.6f}")
    print()

    # 获取PPO policy的mlp_extractor和action_net
    policy = ppo_model.policy

    # BC网络结构: network.0, network.2, network.4 (Linear层)
    # PPO网络结构: mlp_extractor.policy_net.0, policy_net.2 + action_net

    # 映射BC权重到PPO
    # BC layer 0 -> PPO mlp_extractor.policy_net.0
    policy.mlp_extractor.policy_net[0].weight.data.copy_(
        bc_state_dict["network.0.weight"]
    )
    policy.mlp_extractor.policy_net[0].bias.data.copy_(bc_state_dict["network.0.bias"])

    # BC layer 2 -> PPO mlp_extractor.policy_net.2
    policy.mlp_extractor.policy_net[2].weight.data.copy_(
        bc_state_dict["network.2.weight"]
    )
    policy.mlp_extractor.policy_net[2].bias.data.copy_(bc_state_dict["network.2.bias"])

    # BC layer 4 -> PPO action_net
    policy.action_net.weight.data.copy_(bc_state_dict["network.4.weight"])
    policy.action_net.bias.data.copy_(bc_state_dict["network.4.bias"])

    print("[OK] BC权重已成功加载到PPO policy")
    print()


def train_ppo_with_bc_init(
    bc_weights_path: str = "best_bc_policy_weights.pth",
    total_timesteps: int = 5_000_000,
    num_envs: int = 8,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    checkpoint_freq: int = 50_000,
    log_dir: str = "./logs_bc_warmstart",
    model_dir: str = "./models_bc_warmstart",
):
    """
    使用BC warm-start训练PPO

    Args:
        bc_weights_path: BC权重路径
        total_timesteps: 总训练步数
        num_envs: 并行环境数
        learning_rate: 学习率
        n_steps: 每次更新的步数
        batch_size: 批大小
        checkpoint_freq: 检查点保存频率
        log_dir: TensorBoard日志目录
        model_dir: 模型保存目录
    """
    print("=" * 80)
    print("PPO训练 (BC Warm-Start)")
    print("=" * 80)
    print()

    # 创建目录
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    tensorboard_dir = os.path.join(log_dir, "tensorboard")
    checkpoint_dir = os.path.join(log_dir, "checkpoints")
    os.makedirs(tensorboard_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    print(f"配置:")
    print(f"  总步数: {total_timesteps:,}")
    print(f"  并行环境: {num_envs}")
    print(f"  学习率: {learning_rate}")
    print(f"  Steps per update: {n_steps}")
    print(f"  Batch size: {batch_size}")
    print(f"  检查点频率: {checkpoint_freq:,}")
    print(f"  BC权重: {bc_weights_path}")
    print()

    # 创建向量化环境
    print(f"创建 {num_envs} 个并行环境...")
    env = SubprocVecEnv([make_env(i) for i in range(num_envs)])
    print("[OK] 环境创建完成")
    print()

    # 初始化PPO模型（不加载BC权重）
    print("初始化PPO模型...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        clip_range_vf=None,
        normalize_advantage=True,
        ent_coef=0.01,  # 稍微增加探索
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=False,
        sde_sample_freq=-1,
        target_kl=None,
        tensorboard_log=tensorboard_dir,
        verbose=1,
        device="auto",
        seed=None,
        _init_setup_model=True,
        policy_kwargs=dict(
            net_arch=[dict(pi=[128, 128], vf=[128, 128])]  # 明确指定网络架构
        ),
    )

    print(f"[OK] PPO模型初始化完成 (device: {model.device})")
    print()

    # 加载BC权重到policy
    RL_TRAINING_DIR = Path(__file__).resolve().parent
    bc_weights_full_path = RL_TRAINING_DIR / bc_weights_path

    if bc_weights_full_path.exists():
        load_bc_weights_into_ppo(model, str(bc_weights_full_path))
    else:
        print(f"[WARNING] BC权重文件不存在: {bc_weights_full_path}")
        print("将使用随机初始化的policy训练")
        print()

    # 创建检查点回调
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq // num_envs,
        save_path=checkpoint_dir,
        name_prefix="ppo_bc_warmstart",
        save_replay_buffer=False,
        save_vecnormalize=True,
    )

    print("=" * 80)
    print("开始训练")
    print("=" * 80)
    print(f"TensorBoard: tensorboard --logdir {tensorboard_dir}")
    print()

    # 训练
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=checkpoint_callback,
            log_interval=10,
            tb_log_name="PPO_BC_warmstart",
            reset_num_timesteps=True,
            progress_bar=False,
        )

        print()
        print("=" * 80)
        print("训练完成")
        print("=" * 80)

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("训练被中断")
        print("=" * 80)

    finally:
        # 保存最终模型
        final_model_path = os.path.join(model_dir, "ppo_bc_warmstart_final")
        model.save(final_model_path)
        print(f"最终模型已保存到: {final_model_path}.zip")

        # 清理
        env.close()
        print("环境已关闭")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PPO训练 (BC Warm-Start)")
    parser.add_argument(
        "--bc-weights",
        type=str,
        default="best_bc_policy_weights.pth",
        help="BC权重路径",
    )
    parser.add_argument("--timesteps", type=int, default=5_000_000, help="总训练步数")
    parser.add_argument("--envs", type=int, default=8, help="并行环境数")
    parser.add_argument("--lr", type=float, default=3e-4, help="学习率")
    parser.add_argument(
        "--log-dir", type=str, default="./logs_bc_warmstart", help="日志目录"
    )
    parser.add_argument(
        "--model-dir", type=str, default="./models_bc_warmstart", help="模型保存目录"
    )

    args = parser.parse_args()

    # 设置多进程启动方法（Windows兼容性）
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    train_ppo_with_bc_init(
        bc_weights_path=args.bc_weights,
        total_timesteps=args.timesteps,
        num_envs=args.envs,
        learning_rate=args.lr,
        log_dir=args.log_dir,
        model_dir=args.model_dir,
    )

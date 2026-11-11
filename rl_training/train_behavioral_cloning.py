"""
阶段2：行为克隆预训练

使用收集的V13.7专家轨迹训练MLP策略网络
网络架构与PPO一致，用于warm-start
"""

import json
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset


class ExpertDataset(Dataset):
    """专家轨迹数据集"""

    def __init__(self, trajectories_path: str):
        """
        加载专家轨迹数据

        Args:
            trajectories_path: pickle文件路径
        """
        with open(trajectories_path, "rb") as f:
            data = pickle.load(f)

        self.episodes = data["episodes"]
        self.statistics = data["statistics"]

        # 展开所有transitions
        self.observations = []
        self.actions = []

        for episode in self.episodes:
            for transition in episode.transitions:
                self.observations.append(transition.observation)
                self.actions.append(transition.action)

        self.observations = np.array(self.observations, dtype=np.float32)
        self.actions = np.array(self.actions, dtype=np.float32)

        print("数据集加载完成:")
        print(f"  Episodes: {len(self.episodes)}")
        print(f"  Transitions: {len(self.observations)}")
        print(f"  Observation shape: {self.observations.shape}")
        print(f"  Action shape: {self.actions.shape}")

    def __len__(self):
        return len(self.observations)

    def __getitem__(self, idx):
        return self.observations[idx], self.actions[idx]


class MLPPolicy(nn.Module):
    """
    MLP策略网络（与Stable-Baselines3 PPO架构匹配）

    输入: 20维观测
    输出: 4维动作
    隐藏层: [128, 128]
    """

    def __init__(self, obs_dim: int = 20, action_dim: int = 4, hidden_dim: int = 128):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, action_dim),
        )

        # 初始化权重（与SB3类似）
        self._initialize_weights()

    def _initialize_weights(self):
        """Xavier初始化"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0.0)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        return self.network(obs)


def train_behavioral_cloning(
    trajectories_path: str = "v137_expert_trajectories.pkl",
    save_path: str = "bc_policy_weights.pth",
    num_epochs: int = 50,
    batch_size: int = 256,
    learning_rate: float = 1e-3,
    validation_split: float = 0.2,
    device: str = "auto",
) -> dict:
    """
    训练行为克隆模型

    Args:
        trajectories_path: 专家轨迹数据路径
        save_path: 模型保存路径
        num_epochs: 训练轮数
        batch_size: 批大小
        learning_rate: 学习率
        validation_split: 验证集比例
        device: 设备 ('cuda', 'cpu', 'auto')

    Returns:
        训练历史字典
    """
    print("=" * 80)
    print("行为克隆预训练")
    print("=" * 80)
    print()

    # 设置设备
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")
    print()

    # 加载数据集
    RL_TRAINING_DIR = Path(__file__).resolve().parent
    full_trajectories_path = RL_TRAINING_DIR / trajectories_path

    print(f"加载专家轨迹: {full_trajectories_path}")
    dataset = ExpertDataset(str(full_trajectories_path))
    print()

    # 分割训练集和验证集
    n_total = len(dataset)
    n_val = int(n_total * validation_split)
    n_train = n_total - n_val

    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [n_train, n_val], generator=torch.Generator().manual_seed(42)
    )

    print("数据分割:")
    print(f"  训练集: {n_train} transitions")
    print(f"  验证集: {n_val} transitions")
    print()

    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # Windows兼容性
    )

    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=0
    )

    # 创建模型
    print("创建MLP策略网络...")
    policy = MLPPolicy(obs_dim=20, action_dim=4, hidden_dim=128).to(device)
    print(f"模型参数量: {sum(p.numel() for p in policy.parameters()):,}")
    print()

    # 优化器和损失函数
    optimizer = optim.Adam(policy.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    # 训练循环
    print(f"开始训练 ({num_epochs} epochs)...")
    print("-" * 80)

    train_losses = []
    val_losses = []
    best_val_loss = float("inf")

    for epoch in range(num_epochs):
        # 训练阶段
        policy.train()
        train_loss_sum = 0.0
        train_batches = 0

        for obs_batch, action_batch in train_loader:
            obs_batch = obs_batch.to(device)
            action_batch = action_batch.to(device)

            # 前向传播
            predicted_actions = policy(obs_batch)
            loss = criterion(predicted_actions, action_batch)

            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss_sum += loss.item()
            train_batches += 1

        avg_train_loss = train_loss_sum / train_batches
        train_losses.append(avg_train_loss)

        # 验证阶段
        policy.eval()
        val_loss_sum = 0.0
        val_batches = 0

        with torch.no_grad():
            for obs_batch, action_batch in val_loader:
                obs_batch = obs_batch.to(device)
                action_batch = action_batch.to(device)

                predicted_actions = policy(obs_batch)
                loss = criterion(predicted_actions, action_batch)

                val_loss_sum += loss.item()
                val_batches += 1

        avg_val_loss = val_loss_sum / val_batches
        val_losses.append(avg_val_loss)

        # 打印进度
        print(
            f"Epoch {epoch + 1}/{num_epochs} | "
            f"Train Loss: {avg_train_loss:.6f} | "
            f"Val Loss: {avg_val_loss:.6f}"
        )

        # 保存最佳模型
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_model_path = RL_TRAINING_DIR / f"best_{save_path}"
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": policy.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "train_loss": avg_train_loss,
                    "val_loss": avg_val_loss,
                },
                best_model_path,
            )

    print()
    print("=" * 80)
    print("训练完成")
    print("=" * 80)
    print(f"最佳验证损失: {best_val_loss:.6f}")
    print()

    # 保存最终模型
    final_model_path = RL_TRAINING_DIR / save_path
    torch.save(
        {
            "epoch": num_epochs - 1,
            "model_state_dict": policy.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "train_loss": train_losses[-1],
            "val_loss": val_losses[-1],
            "train_losses": train_losses,
            "val_losses": val_losses,
        },
        final_model_path,
    )

    print(f"模型已保存到: {final_model_path}")
    print(f"最佳模型已保存到: {best_model_path}")
    print()

    # 绘制训练曲线
    plot_path = RL_TRAINING_DIR / "bc_training_curve.png"
    plt.figure(figsize=(10, 6))
    plt.plot(train_losses, label="Train Loss", linewidth=2)
    plt.plot(val_losses, label="Validation Loss", linewidth=2)
    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("MSE Loss", fontsize=12)
    plt.title("Behavioral Cloning Training Curve", fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    print(f"训练曲线已保存到: {plot_path}")
    print()

    # 保存训练历史
    history = {
        "train_losses": [float(x) for x in train_losses],
        "val_losses": [float(x) for x in val_losses],
        "best_val_loss": float(best_val_loss),
        "final_train_loss": float(train_losses[-1]),
        "final_val_loss": float(val_losses[-1]),
        "num_epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "n_train": n_train,
        "n_val": n_val,
    }

    history_path = RL_TRAINING_DIR / "bc_training_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"训练历史已保存到: {history_path}")
    print()

    return history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="行为克隆预训练")
    parser.add_argument(
        "--trajectories",
        type=str,
        default="v137_expert_trajectories.pkl",
        help="专家轨迹数据路径",
    )
    parser.add_argument(
        "--save", type=str, default="bc_policy_weights.pth", help="模型保存路径"
    )
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=256, help="批大小")
    parser.add_argument("--lr", type=float, default=1e-3, help="学习率")
    parser.add_argument("--device", type=str, default="auto", help="设备")

    args = parser.parse_args()

    history = train_behavioral_cloning(
        trajectories_path=args.trajectories,
        save_path=args.save,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        device=args.device,
    )

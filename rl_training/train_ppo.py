"""
PPO Training Script for hw-1 Gait Training Assistant Device
Uses Stable-Baselines3 with parallel environments and TensorBoard logging
"""

import os
import sys
from pathlib import Path

# Ensure this directory is importable (for `environment` module) even from
# spawned subprocesses or a different working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.utils import set_random_seed
import torch


def make_env(rank, seed=0):
    """
    Utility function for multiprocessed env.

    Args:
        rank: Index of the subprocess
        seed: Random seed
    """

    def _init():
        # Import here to avoid issues with multiprocessing
        from environment import CompassGaitEnv

        env = CompassGaitEnv(reward_type="energy_efficient")
        env.reset(seed=seed + rank)
        return env

    set_random_seed(seed)
    return _init


def train_ppo():
    """Train PPO agent for gait training assistance"""

    # Training configuration
    num_envs = 8
    total_timesteps = 2_000_000
    learning_rate = 3e-4
    n_steps = 2048
    batch_size = 64
    checkpoint_freq = 10_000

    # Create directories
    log_dir = "./logs/tensorboard"
    checkpoint_dir = "./logs/checkpoints"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    print(f"Creating {num_envs} parallel environments...")

    # Create vectorized environment with 8 parallel subprocesses
    env = SubprocVecEnv([make_env(i) for i in range(num_envs)])

    print("Initializing PPO agent...")

    # Initialize PPO model
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
        ent_coef=0.0,
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=False,
        sde_sample_freq=-1,
        target_kl=None,
        tensorboard_log=log_dir,
        verbose=1,
        device="auto",
        seed=None,
        _init_setup_model=True,
    )

    print(f"Using device: {model.device}")

    # Create checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq // num_envs,  # Adjust for parallel envs
        save_path=checkpoint_dir,
        name_prefix="ppo_gait_model",
        save_replay_buffer=False,
        save_vecnormalize=True,
    )

    print(f"\nStarting training for {total_timesteps:,} timesteps...")
    print(f"Hyperparameters:")
    print(f"  - Learning rate: {learning_rate}")
    print(f"  - Steps per update: {n_steps}")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Parallel environments: {num_envs}")
    print(f"  - Checkpoint frequency: every {checkpoint_freq:,} steps")
    print(f"  - TensorBoard logs: {log_dir}")
    print(f"  - Checkpoints: {checkpoint_dir}")
    print("\nMonitor training progress with: tensorboard --logdir {log_dir}\n")

    # Train the agent
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=checkpoint_callback,
            log_interval=10,
            tb_log_name="PPO_gait_training",
            reset_num_timesteps=True,
            progress_bar=False,  # Avoid rich dependency
        )

        print("\nTraining completed successfully!")

    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")

    finally:
        # Save final model
        final_model_path = "./models/ppo_gait_final"
        os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
        model.save(final_model_path)
        print(f"Final model saved to: {final_model_path}.zip")

        # Clean up
        env.close()
        print("Environments closed.")


if __name__ == "__main__":
    # Set multiprocessing start method for Windows compatibility
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    train_ppo()

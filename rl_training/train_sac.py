"""
SAC Training Script for hw-1 Gait Training Assistant Device
Soft Actor-Critic: More sample-efficient off-policy alternative to PPO
Uses Stable-Baselines3 with replay buffer and TensorBoard logging
"""

import os
import sys
from pathlib import Path

# Ensure this directory is importable (for `environment` module).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor


def train_sac():
    """Train SAC agent for gait training assistance"""

    # Training configuration
    total_timesteps = 1_000_000  # SAC needs fewer samples than PPO
    learning_rate = 3e-4
    buffer_size = 300_000
    learning_starts = 10_000
    batch_size = 256
    tau = 0.005
    gamma = 0.99
    train_freq = 1
    gradient_steps = 1
    checkpoint_freq = 10_000

    # Create directories
    log_dir = "./logs/tensorboard"
    checkpoint_dir = "./logs/checkpoints_sac"
    eval_log_dir = "./logs/eval_sac"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(eval_log_dir, exist_ok=True)

    print("Creating training environment...")

    # Import here to avoid multiprocessing issues
    from environment import CompassGaitEnv

    # Create training environment
    env = CompassGaitEnv(reward_type="energy_efficient")
    env = Monitor(env)

    print("Creating evaluation environment...")

    # Create separate evaluation environment
    eval_env = CompassGaitEnv(reward_type="energy_efficient")
    eval_env = Monitor(eval_env, eval_log_dir)

    print("Initializing SAC agent...")

    # Initialize SAC model
    model = SAC(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=batch_size,
        tau=tau,
        gamma=gamma,
        train_freq=train_freq,
        gradient_steps=gradient_steps,
        action_noise=None,  # SAC uses entropy regularization instead
        replay_buffer_class=None,
        replay_buffer_kwargs=None,
        optimize_memory_usage=False,
        ent_coef="auto",  # Automatic entropy tuning
        target_update_interval=1,
        target_entropy="auto",
        use_sde=False,
        sde_sample_freq=-1,
        use_sde_at_warmup=False,
        tensorboard_log=log_dir,
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], qf=[256, 256])),
        verbose=1,
        seed=None,
        device="auto",
        _init_setup_model=True,
    )

    print(f"Using device: {model.device}")

    # Create checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq,
        save_path=checkpoint_dir,
        name_prefix="sac_gait_model",
        save_replay_buffer=True,
        save_vecnormalize=True,
    )

    # Create evaluation callback (evaluates policy every N steps)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=checkpoint_dir,
        log_path=eval_log_dir,
        eval_freq=5_000,
        n_eval_episodes=5,
        deterministic=True,
        render=False,
        verbose=1,
    )

    print(f"\nStarting SAC training for {total_timesteps:,} timesteps...")
    print("Hyperparameters:")
    print(f"  - Learning rate: {learning_rate}")
    print(f"  - Replay buffer size: {buffer_size:,}")
    print(f"  - Learning starts: {learning_starts:,}")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Tau (soft update): {tau}")
    print(f"  - Gamma (discount): {gamma}")
    print(f"  - Train frequency: {train_freq} step(s)")
    print(f"  - Gradient steps: {gradient_steps}")
    print(f"  - Checkpoint frequency: every {checkpoint_freq:,} steps")
    print("  - Evaluation frequency: every 5,000 steps")
    print(f"  - TensorBoard logs: {log_dir}")
    print(f"  - Checkpoints: {checkpoint_dir}")
    print("\nSAC Advantages:")
    print("  - Off-policy: reuses past experience via replay buffer")
    print("  - Sample-efficient: typically needs ~50% fewer samples than PPO")
    print("  - Automatic entropy tuning: self-adjusts exploration")
    print("\nMonitor training progress with: tensorboard --logdir {log_dir}\n")

    # Train the agent
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback],
            log_interval=10,
            tb_log_name="SAC_gait_training",
            reset_num_timesteps=True,
            progress_bar=True,
        )

        print("\nTraining completed successfully!")

    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")

    finally:
        # Save final model
        final_model_path = "./models/sac_gait_final"
        os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
        model.save(final_model_path)
        print(f"Final model saved to: {final_model_path}.zip")

        # Save replay buffer
        replay_buffer_path = "./models/sac_gait_replay_buffer"
        model.save_replay_buffer(replay_buffer_path)
        print(f"Replay buffer saved to: {replay_buffer_path}.pkl")

        # Clean up
        env.close()
        eval_env.close()
        print("Environments closed.")


if __name__ == "__main__":
    train_sac()

# Residual RL V2 Codex Session

**Date**: 2026-06-09  
**Status**: Training completed successfully

## Summary

Codex fixed the full `ResidualRLEnvV2` timing bug, validated zero residual identity, swept hip residual directions, and completed a 100k PPO sanity run.

## Key Results

- Zero residual identity: `4.630276m`, `100%` success over 10 episodes.
- Best sweep path: `residual_scale=0.20`, action `[0.50, 1.00]`, torque `[0.100, 0.200]Nm`, distance `4.972583m`, improvement `+7.39%`.
- 100k PPO sanity result: `4.898271m`, `100%` success.

## Important Implementation Notes

- `control_v136()` now receives integer-derived 1kHz time `t = micro_steps * dt`, preserving the validated identity-test loop.
- The default environment remains identity-safe: action `[0, 0]` means zero residual.
- The training script uses a separate prior-guided wrapper to learn small PPO deltas around the sweep-best residual path.

## Artifacts

- Environment: `rl_training/train_residual_rl_v2.py`
- Sweep script: `rl_training/sweep_residual_combinations.py`
- Training script: `rl_training/train_sanity_100k.py`
- Compatibility entry: `rl_training/train_residual_rl_v2_full.py`
- Final model: `models/residual_rl_v2_sanity/ppo_final.zip`
- Best model: `models/residual_rl_v2_sanity/ppo_best.zip`
- JSON reports: `logs/residual_rl_v2/*.json`
- Structured logs: `logs/residual_rl_v2/task*.log`

## Recommended Next Run

Use the trained model as the sanity baseline, then run longer training with the same prior:

```powershell
.\.venv-mujoco\Scripts\python.exe rl_training\train_sanity_100k.py --timesteps 500000 --n-envs 8 --eval-freq 50000 --eval-episodes 10
```

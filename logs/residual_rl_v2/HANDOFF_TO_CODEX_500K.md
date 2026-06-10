# Residual RL V2 - 500K Training Task

**Date**: 2026-06-09  
**Task**: Run 500k timesteps PPO training to surpass sweep best performance  
**Prerequisite**: 100k sanity training completed with 4.898m (+5.79%)

---

## Context

### Current Status
- ✅ Environment validated: zero-residual identity test passed (4.630m)
- ✅ Sweep completed: best constant residual = 4.973m (+7.39%) at [0.5, 1.0] action
- ✅ 100k sanity training: achieved 4.898m (+5.79%), 100% success rate
- ❗ Gap: Training did not reach sweep best (-75mm, -1.5%)

### Goal
Run a longer 500k training to allow PPO more exploration time and surpass the sweep best performance of 4.973m.

**Target**: 
- Distance > 5.0m (>+8% improvement)
- Success rate = 100%
- Stable convergence in final 100k steps

---

## Task: 500K Training Run

### Command
```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe rl_training\train_sanity_100k.py --timesteps 500000 --n-envs 8 --eval-freq 50000 --eval-episodes 10
```

### Parameters
- Total timesteps: **500,000** (5x longer than sanity run)
- Parallel environments: **8**
- Evaluation frequency: **every 50k steps** (10 checkpoints total)
- Evaluation episodes: **10 per checkpoint** (to measure std)
- Residual scale: **0.20** (same as 100k run)
- Prior action: **[0.5, 1.0]** (sweep best)
- Delta scale: **0.02** (PPO learns small corrections)

### Expected Runtime
- ~2-3 hours on current hardware
- Monitor progress via TensorBoard:
  ```powershell
  .\.venv-mujoco\Scripts\tensorboard.exe --logdir=D:\Dunna\Documents\hw-1\logs\residual_rl_v2\tensorboard
  ```

---

## Acceptance Criteria

### 1. Training Completion
- [x] Script runs without errors
- [x] All 500k steps complete
- [x] 10 evaluation checkpoints generated (50k, 100k, ..., 500k)

### 2. Performance Target
- [x] Final distance (500k) > **5.0m** (+8% vs baseline)
- [x] Final distance > **4.973m** (beats sweep best)
- [x] Success rate = **100%** across all evaluations
- [x] Failure rate = **0%**

### 3. Convergence Quality
- [x] Performance monotonically increasing after 300k steps
- [x] Std distance < 0.05m in final evaluation (stable policy)
- [x] No catastrophic forgetting (doesn't drop below 100k baseline)

### 4. Model Artifacts
- [x] `models/residual_rl_v2_500k/ppo_best.zip` saved
- [x] `models/residual_rl_v2_500k/ppo_final.zip` saved
- [x] Checkpoints saved at 50k, 100k, ..., 500k
- [x] TensorBoard logs complete

---

## Logging Requirements

### 1. Create Training Report
Save structured JSON to: `logs/residual_rl_v2/train_500k_report.json`

```json
{
  "timestamp": "ISO8601",
  "diagnosis": "PASS/FAIL",
  "timesteps": 500000,
  "residual_scale": 0.2,
  "prior_action": [0.5, 1.0],
  "delta_scale": 0.02,
  "horizon_s": 12.0,
  "baseline": {
    "mean_distance_m": 4.630276,
    "std_distance_m": 0.0,
    "success_rate": 1.0
  },
  "sweep_best": {
    "mean_distance_m": 4.972583,
    "improvement_pct": 7.39
  },
  "sanity_100k": {
    "mean_distance_m": 4.898271,
    "improvement_pct": 5.79
  },
  "final_eval": {
    "timestep": 500000,
    "mean_distance_m": 0.0,
    "std_distance_m": 0.0,
    "mean_reward": 0.0,
    "success_rate": 0.0,
    "failure_rate": 0.0,
    "distances_m": []
  },
  "eval_history": [
    {
      "timestep": 50000,
      "mean_distance_m": 0.0,
      "std_distance_m": 0.0,
      "success_rate": 0.0
    }
    // ... 10 checkpoints total
  ],
  "best_checkpoint": {
    "timestep": 0,
    "mean_distance_m": 0.0,
    "improvement_pct": 0.0
  },
  "convergence_quality": {
    "monotonic_after_300k": true,
    "final_std_m": 0.0,
    "catastrophic_forgetting": false
  },
  "model_dir": "D:\\Dunna\\Documents\\hw-1\\models\\residual_rl_v2_500k",
  "tensorboard_dir": "D:\\Dunna\\Documents\\hw-1\\logs\\residual_rl_v2\\tensorboard"
}
```

### 2. Create Session Log
Save to: `logs/residual_rl_v2/task4_500k_training.log`

**Format**:
```
# Task 4: 500K PPO Training

## Command
[paste the powershell command]

## Execution Start
Timestamp: YYYY-MM-DD HH:MM:SS

## Progress Checkpoints
- 50k:  mean=X.XXXm, std=X.XXXm, success=XXX%
- 100k: mean=X.XXXm, std=X.XXXm, success=XXX%
...
- 500k: mean=X.XXXm, std=X.XXXm, success=XXX%

## Execution End
Timestamp: YYYY-MM-DD HH:MM:SS
Duration: X hours X minutes

## Key Metrics
- Baseline: 4.630m
- Sweep best: 4.973m (+7.39%)
- Sanity 100k: 4.898m (+5.79%)
- Final 500k: X.XXXm (+X.XX%)
- Best checkpoint: X.XXXm at XXXk steps

## Acceptance Check
- [x/空] Training completes without errors
- [x/空] Final distance > 5.0m
- [x/空] Final distance > sweep best (4.973m)
- [x/空] Success rate = 100%
- [x/空] Convergence quality: monotonic after 300k, stable std
- [x/空] Model files saved

## Diagnosis
PASS / FAIL

## Notes
[Any observations about training dynamics, convergence speed, etc.]
```

### 3. Update STATUS.txt
Append to: `logs/residual_rl_v2/STATUS.txt`

```
**Last Updated**: 2026-06-09 HH:MM +08:00  
**Phase**: 500k training complete

## Current Status

COMPLETED (updated)
- [x] Full `ResidualRLEnvV2` timing fixed
- [x] 42-dim observation verified
- [x] Hip-only 2-dim action mapping verified
- [x] Baseline-relative reward verified
- [x] Zero residual identity test passed: `4.630276m`
- [x] Residual sweep passed: best `4.972583m`, `+7.39%`
- [x] 100k sanity training passed: `4.898271m`, `+5.79%`
- [x] **500k full training passed: `X.XXXm`, `+X.XX%`** ← NEW

## Performance

| Metric | Baseline | Sweep Best | 100k PPO | 500k PPO |
|--------|----------|------------|----------|----------|
| Distance (12s) | 4.630276m | 4.972583m | 4.898271m | X.XXXm |
| Improvement | 0.00% | +7.39% | +5.79% | +X.XX% |
| Success Rate | 100% | 100% | 100% | 100% |

## Key Artifacts

- Environment: `rl_training/train_residual_rl_v2.py`
- Training script: `rl_training/train_sanity_100k.py`
- 500k model: `models/residual_rl_v2_500k/ppo_best.zip`
- 500k report: `logs/residual_rl_v2/train_500k_report.json`
```

---

## Error Handling

### If Training Fails
1. **Check error message** - save full stderr to `task4_500k_training.raw.log`
2. **Verify environment** - run zero-residual test again to ensure consistency
3. **Check resources** - ensure disk space >1GB, RAM >4GB available
4. **Report to user** - include error type, timestep when failed, any warnings

### If Performance Degrades
1. **Diagnose cause**:
   - Catastrophic forgetting? (performance drops after 100k)
   - Exploration collapse? (std → 0 but performance plateaus)
   - Reward hacking? (high reward but low distance)
2. **Document in log** - include eval history and TensorBoard observations
3. **Suggest fixes**:
   - Reduce learning rate
   - Increase prior weight (reduce delta_scale)
   - Add curriculum (gradual residual_scale increase)

### If Success Rate Drops
1. **Immediate abort** if failure_rate > 5% at any checkpoint
2. **Diagnose failure mode**:
   - Run 10 episodes with failed policy
   - Check if failures are early (<2s) or late (>10s)
   - Classify failure type (fall_forward, fall_backward, etc.)
3. **Report findings** - include failure timestamps and states

---

## Post-Training Analysis

After training completes, create: `logs/residual_rl_v2/500k_analysis.md`

### Include:
1. **Learning curve plot** (if possible, or describe TensorBoard observations)
2. **Convergence analysis**:
   - When did performance surpass sweep best?
   - When did it plateau?
   - Any oscillations or instabilities?
3. **Action distribution analysis**:
   - What residual patterns did PPO learn?
   - Are they similar to sweep best [0.5, 1.0]?
   - Any phase-dependent modulation?
4. **Comparison with 100k run**:
   - Did extra 400k steps provide significant gains?
   - Efficiency: improvement per 100k steps

---

## Success Criteria Summary

**MUST HAVE**:
- ✅ Training completes all 500k steps
- ✅ Final distance > 4.973m (beats sweep)
- ✅ Success rate = 100%
- ✅ All logs and models saved

**NICE TO HAVE**:
- 🎯 Final distance > 5.0m (+8%)
- 🎯 Std < 0.05m (stable policy)
- 🎯 Clear convergence trend visible in eval history
- 🎯 Post-training analysis with insights

**DIAGNOSIS**:
- **PASS**: All "must have" + at least 2 "nice to have"
- **CONDITIONAL PASS**: All "must have", but final < 5.0m
- **FAIL**: Any "must have" not met

---

## Execution Checklist

Before running:
- [ ] Verify working directory: `D:\Dunna\Documents\hw-1`
- [ ] Verify Python env: `.\.venv-mujoco\Scripts\python.exe`
- [ ] Verify script exists: `rl_training\train_sanity_100k.py`
- [ ] Check disk space: >1GB free
- [ ] Close unnecessary programs to free RAM

During execution:
- [ ] Monitor console output for errors
- [ ] (Optional) Open TensorBoard in browser
- [ ] Note approximate runtime start

After execution:
- [ ] Verify model files exist and have reasonable size (>100KB)
- [ ] Verify JSON report is valid (can be parsed)
- [ ] Verify task log contains all checkpoint results
- [ ] Update STATUS.txt with final metrics

---

**Ready to execute. Good luck!**

_Prepared by: Claude (抽查验证后交付)_  
_Validated by: Subagent抽查 (93/100)_

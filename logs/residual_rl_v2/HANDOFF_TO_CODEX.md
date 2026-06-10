# ResidualRLEnvV2 Implementation Handoff to Codex

**Date**: 2026-06-08  
**Handoff From**: Claude (Opus 4.8)  
**Handoff To**: Codex (execution agent)  
**Status**: Bug fixed, ready for full implementation

---

## 🎯 Executive Summary

**Objective**: Train Residual RL (PPO on top of V13.7 FSM) to exceed baseline performance (1.05m in 2.5s).

**Current Status**:
- ✅ **Critical bug fixed**: Original V2 environment failed at 4s due to incorrect time parameter in `control_v136()`
- ✅ **Simplified version validated**: `train_residual_rl_v2_simple.py` achieves 4.630m in 12.00s (matches baseline)
- 🔄 **Next phase**: Implement full B+C+A strategy with 42-dim observation, hip-only action, baseline-relative reward

**Expected Outcome**: Residual RL achieves 1.5-2.0m (43-90% improvement over 1.05m baseline)

---

## 📋 Task List for Codex

Execute these tasks **in order**, logging results after each step.

### Phase 1: Environment Implementation (2-3 hours)

**Task 1.1**: Extend `train_residual_rl_v2_simple.py` to add 42-dim observation

```python
# Add to ResidualRLEnvV2Simple class

def _get_phase(self, foot: str) -> int:
    """Compute current phase for given foot (0-3)."""
    t_since_burst = self.steps * self.dt - self.burst_start_t
    gait_period = self.params.base.gait_period
    phase_normalized = (t_since_burst % gait_period) / gait_period
    
    if phase_normalized < 0.25:
        return 0  # stance_early
    elif phase_normalized < 0.5:
        return 1  # stance_late
    elif phase_normalized < 0.75:
        return 2  # swing_thrust
    else:
        return 3  # swing_retract

def _get_obs(self) -> np.ndarray:
    """Build 42-dim observation vector."""
    
    # Original 20 dims (from base environment)
    joint_angles = self.data.qpos[2:8]  # 6 dims
    joint_vels = self.data.qvel[2:8]    # 6 dims
    hip_pos = self.data.qpos[0:2]      # 2 dims
    hip_vel = self.data.qvel[0:2]      # 2 dims
    contacts = self._get_contact_states()  # 4 dims
    
    # NEW: Phase information (8 dims)
    left_phase = self._get_phase("left")
    right_phase = self._get_phase("right")
    left_phase_onehot = np.zeros(4, dtype=np.float32)
    right_phase_onehot = np.zeros(4, dtype=np.float32)
    left_phase_onehot[left_phase] = 1.0
    right_phase_onehot[right_phase] = 1.0
    
    # NEW: Support foot (2 dims)
    support_onehot = np.zeros(2, dtype=np.float32)
    support_onehot[0] = 1.0 if self.support_foot == "left" else 0.0
    support_onehot[1] = 1.0 if self.support_foot == "right" else 0.0
    
    # NEW: Time encodings (2 dims, normalized)
    t = self.steps * self.dt
    t_since_contact = t - self.last_event_t if self.last_event_t >= 0 else 0.0
    t_since_burst = t - self.burst_start_t
    t_since_contact_norm = np.clip(t_since_contact / 1.5, 0.0, 2.0)
    t_since_burst_norm = np.clip(t_since_burst / 1.5, 0.0, 2.0)
    
    # NEW: Energy (2 dims, normalized)
    E_current = _mechanical_energy(self.params.base, self.data)
    E_ref_mean = 53.0  # approximate from Identity Test
    E_current_norm = E_current / E_ref_mean
    E_diff_norm = (E_current - E_ref_mean) / E_ref_mean
    
    # NEW: Base torques (4 dims, normalized)
    # Compute during step, store as self.last_base_torques
    base_torques_norm = self.last_base_torques / 4.0
    
    # NEW: Last residuals (4 dims, normalized)
    # Store during step as self.last_residuals
    last_residuals_norm = self.last_residuals / max(self.residual_scale, 1e-6)
    
    # Concatenate all (total: 42 dims)
    obs = np.concatenate([
        joint_angles,           # 6
        joint_vels,             # 6
        hip_pos,                # 2
        hip_vel,                # 2
        contacts,               # 4
        left_phase_onehot,      # 4
        right_phase_onehot,     # 4
        support_onehot,         # 2
        [t_since_contact_norm], # 1
        [t_since_burst_norm],   # 1
        [E_current_norm],       # 1
        [E_diff_norm],          # 1
        base_torques_norm,      # 4
        last_residuals_norm,    # 4
    ]).astype(np.float32)
    
    return obs

def _get_contact_states(self) -> np.ndarray:
    """Detect foot contact states."""
    foot_geom_names = ["left_heel", "left_toe", "right_heel", "right_toe"]
    foot_geom_ids = [self.model.geom(name).id for name in foot_geom_names]
    contact_states = np.zeros(4, dtype=np.float32)
    
    for i in range(self.data.ncon):
        contact = self.data.contact[i]
        geom1, geom2 = contact.geom1, contact.geom2
        
        for j, foot_geom_id in enumerate(foot_geom_ids):
            if geom1 == foot_geom_id or geom2 == foot_geom_id:
                if np.linalg.norm(contact.frame[:3]) > 0.1:
                    contact_states[j] = 1.0
    
    return contact_states
```

**Acceptance Criteria**:
- `_get_obs()` returns 42-dim array
- All new state variables initialized in `reset()`
- `self.last_base_torques` and `self.last_residuals` updated in `step()`

**Log**: Save to `logs/residual_rl_v2/task1_observation_extension.log`

---

**Task 1.2**: Implement hip-only residual action (2-dim)

```python
# Update in step() method

def step(self, action: np.ndarray):
    """Execute 1ms step with hip-only residual action."""
    
    # ... (existing V13.7 control computation)
    
    # Map 2-dim action to 4-dim residual (hip-only)
    residual = np.zeros(4, dtype=np.float32)
    residual[0] = self.residual_scale * action[0]  # left_hip
    residual[1] = 0.0                              # left_knee (fixed)
    residual[2] = self.residual_scale * action[1]  # right_hip
    residual[3] = 0.0                              # right_knee (fixed)
    
    self.last_residuals = residual.copy()
    
    # Apply: V13.7 base + residual
    tau_total = np.array([l_hip_out, l_knee_out, r_hip_out, r_knee_out]) + residual
    tau_total = np.clip(tau_total, -4.0, 4.0)
    
    self.data.ctrl[:] = tau_total
    
    # ... (rest of step logic)
```

**Acceptance Criteria**:
- Action space: `Box(low=-1.0, high=1.0, shape=(2,))`
- Knee residuals always 0
- Initial `residual_scale = 0.05`

**Log**: Save to `logs/residual_rl_v2/task1_action_mapping.log`

---

**Task 1.3**: Implement baseline-relative reward

```python
def _compute_reward(self, dx: float) -> float:
    """Compute baseline-relative reward.
    
    Args:
        dx: Forward displacement this step
    
    Returns:
        Scalar reward
    """
    # Reference baseline (from zero residual)
    # 4.63m / 12000 steps = 0.000386m per step
    dx_ref = 0.000386
    
    # 1. Forward improvement reward
    forward_reward = 50.0 * (dx - dx_ref)
    
    # 2. Residual cost (penalize large corrections)
    residual_cost = np.sum(self.last_residuals ** 2)
    
    # 3. Smoothness cost (penalize jerky actions)
    if hasattr(self, 'prev_residuals'):
        smooth_cost = np.sum((self.last_residuals - self.prev_residuals) ** 2)
    else:
        smooth_cost = 0.0
    self.prev_residuals = self.last_residuals.copy()
    
    # 4. Energy cost (penalize excess work)
    # Approximate positive work: |tau_residual * qvel|
    work = 0.0
    work += abs(self.last_residuals[0] * self.data.qvel[2])  # left_hip
    work += abs(self.last_residuals[2] * self.data.qvel[5])  # right_hip
    excess_work = work * self.dt
    
    # Combine
    reward = (
        forward_reward
        - 0.02 * residual_cost
        - 0.01 * smooth_cost
        - 0.02 * excess_work
    )
    
    return reward

# In step(), add terminal bonuses:
if truncated:
    # Successfully completed episode
    total_distance = current_x - self.start_x
    expected_distance = 0.000386 * self.max_steps
    final_improvement = total_distance - expected_distance
    reward += 100.0 * final_improvement

if terminated:
    # Failure penalty
    reward -= 50.0
```

**Acceptance Criteria**:
- Zero residual → reward ≈ 0 per step
- Positive residual that improves distance → positive reward
- Negative residual or excess work → negative reward

**Log**: Save to `logs/residual_rl_v2/task1_reward_function.log`

---

### Phase 2: Validation Tests (1-2 hours)

**Task 2.1**: Zero Residual Identity Test

Run `test_zero_residual_v2.py` with new environment.

**Expected Result**:
```
Distance: 4.630 ± 0.05m
Time: 12.00s
Success rate: 100% (10/10)
```

**If fails**: Debug observation/action mapping, ensure no state corruption.

**Log**: Save to `logs/residual_rl_v2/task2_zero_residual_test.log`

---

**Task 2.2**: Residual Sweep

Create `sweep_residual_combinations.py`:

```python
"""Sweep constant and phase-gated residuals to find improvement directions."""

import numpy as np
from train_residual_rl_v2_simple import ResidualRLEnvV2Simple

def test_constant_residual(env, left_hip_res, right_hip_res, n_episodes=5):
    """Test constant residual over multiple episodes."""
    distances = []
    
    for ep in range(n_episodes):
        obs, info = env.reset(seed=ep)
        action = np.array([left_hip_res, right_hip_res], dtype=np.float32)
        
        while True:
            obs, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                distances.append(info['episode_distance'])
                break
    
    return np.mean(distances), np.std(distances)

# Sweep constant residuals
env = ResidualRLEnvV2Simple(residual_scale=0.05, max_steps=12000)

baseline_mean = 4.630
baseline_std = 0.05

results = []

for left_res in [-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]:
    for right_res in [-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]:
        mean_dist, std_dist = test_constant_residual(env, left_res, right_res)
        improvement = (mean_dist - baseline_mean) / baseline_mean * 100
        
        results.append({
            'left_hip': left_res,
            'right_hip': right_res,
            'distance': mean_dist,
            'std': std_dist,
            'improvement_%': improvement,
        })
        
        print(f"[{left_res:+.2f}, {right_res:+.2f}] → {mean_dist:.3f}m ({improvement:+.1f}%)")

# Sort by improvement
results.sort(key=lambda x: x['distance'], reverse=True)

print("\nTop 5 combinations:")
for i, r in enumerate(results[:5]):
    print(f"{i+1}. [{r['left_hip']:+.2f}, {r['right_hip']:+.2f}] → {r['distance']:.3f}m ({r['improvement_%']:+.1f}%)")

# Save results
import json
with open('logs/residual_rl_v2/residual_sweep_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

**Acceptance Criteria**:
- Find at least 1 combination with >+3% improvement
- Document which phase/joint/amplitude works best

**Log**: Save to `logs/residual_rl_v2/task2_residual_sweep.log`

---

### Phase 3: Training (2-3 hours)

**Task 3.1**: 100k Sanity Training

Create `train_sanity_100k.py`:

```python
"""100k sanity training with evaluation every 25k steps."""

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from train_residual_rl_v2_simple import ResidualRLEnvV2Simple

# Create environment
def make_env():
    return ResidualRLEnvV2Simple(residual_scale=0.05, max_steps=500)

env = DummyVecEnv([make_env for _ in range(8)])
eval_env = DummyVecEnv([make_env])

# Callbacks
eval_callback = EvalCallback(
    eval_env,
    eval_freq=25000 // 8,  # Every 25k steps
    n_eval_episodes=5,
    deterministic=True,
    render=False,
)

checkpoint_callback = CheckpointCallback(
    save_freq=25000 // 8,
    save_path='./models/residual_rl_v2_sanity',
    name_prefix='ppo_sanity',
)

# Train PPO
model = PPO(
    'MlpPolicy',
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    verbose=1,
    tensorboard_log='./logs/residual_rl_v2/tensorboard',
)

print("Starting 100k sanity training...")
model.learn(total_timesteps=100000, callback=[eval_callback, checkpoint_callback])

model.save('./models/residual_rl_v2_sanity/ppo_final')
print("Training complete!")

# Final evaluation
from stable_baselines3.common.evaluation import evaluate_policy

mean_reward, std_reward = evaluate_policy(model, eval_env, n_eval_episodes=20, deterministic=True)
print(f"\nFinal evaluation (20 episodes):")
print(f"  Mean reward: {mean_reward:.2f} ± {std_reward:.2f}")
```

**Acceptance Criteria**:
- Training completes without errors
- Distance at 100k > baseline + 2σ (i.e., > 1.15m)
- Failure rate = 0%
- TensorBoard logs show learning progress

**Log**: Save to `logs/residual_rl_v2/task3_100k_training.log`

---

## 📊 Logging Requirements

Each task must generate a **structured log file** with:

```markdown
# Task [X.Y]: [Task Name]

**Start Time**: YYYY-MM-DD HH:MM:SS  
**End Time**: YYYY-MM-DD HH:MM:SS  
**Duration**: [X] minutes  
**Status**: [SUCCESS / FAILED / PARTIAL]

## Execution Steps

1. [Step description]
   - Command: `...`
   - Output: `...`
   - Result: [OK / ERROR]

2. [Step description]
   ...

## Results

[Quantitative results, numbers, comparisons]

## Errors Encountered

[If any, with stack traces]

## Files Modified

- `file1.py` (lines X-Y)
- `file2.py` (lines A-B)

## Files Created

- `new_file1.py`
- `logs/task_X_Y.log`

## Acceptance Criteria Check

- [ ] Criterion 1: [PASS / FAIL]
- [ ] Criterion 2: [PASS / FAIL]
- [ ] Criterion 3: [PASS / FAIL]

## Next Steps

[If partial or failed, what needs fixing]

---
**Logged by**: Codex  
**Reviewed by**: [Human / Claude]
```

---

## 📁 File Structure

After completion, hw-1 should look like:

```
hw-1/
├── rl_training/
│   ├── train_residual_rl_v2_simple.py       (✅ validated)
│   ├── train_residual_rl_v2_full.py         (🔄 to be created)
│   ├── test_zero_residual_v2.py             (🔄 to be updated)
│   ├── sweep_residual_combinations.py       (🔄 to be created)
│   ├── train_sanity_100k.py                 (🔄 to be created)
│   └── evaluate_final_model.py              (🔄 to be created)
│
├── logs/
│   └── residual_rl_v2/
│       ├── HANDOFF_TO_CODEX.md              (this file)
│       ├── SESSION_2026_06_08.md            (today's full log)
│       ├── task1_observation_extension.log
│       ├── task1_action_mapping.log
│       ├── task1_reward_function.log
│       ├── task2_zero_residual_test.log
│       ├── task2_residual_sweep.log
│       ├── task3_100k_training.log
│       ├── residual_sweep_results.json
│       └── tensorboard/
│
├── models/
│   └── residual_rl_v2_sanity/
│       ├── ppo_sanity_25000_steps.zip
│       ├── ppo_sanity_50000_steps.zip
│       ├── ppo_sanity_75000_steps.zip
│       └── ppo_final.zip
│
└── README.md                                 (🔄 to be updated)
```

---

## 🔧 Environment Setup

**Required**:
- Python 3.10
- Virtual environment: `D:\Dunna\Documents\hw-1\.venv-mujoco`
- GPU: RTX 4060 Ti (CUDA available)

**Activate environment**:
```powershell
cd D:\Dunna\Documents\hw-1
.venv-mujoco\Scripts\Activate.ps1
```

**Verify setup**:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")  # Should be True

import mujoco
print(f"MuJoCo version: {mujoco.__version__}")         # Should be 3.3.7

import stable_baselines3
print(f"SB3 version: {stable_baselines3.__version__}") # Should be compatible
```

---

## 🚨 Critical Notes

### DO NOT modify these files:
- `test_v137_identity.py` (reference baseline)
- `train_residual_rl_v2_simple.py` (validated working version)

### Key Bug Fix (MUST preserve):
In `step()`, always use:
```python
t = self.steps * self.dt
tau = control_v136(fsm, self.data, t, self.support_foot, self.burst_start_t, E_current)
```

**NEVER use**:
```python
tau = control_v136(..., self.sim_time, ...)  # ❌ This causes 4s failure!
```

### Debugging Tips:
- If robot fails at 4s: check time parameter in `control_v136()`
- If FSM stops switching: print FSM events with timestamps
- If distance is negative: robot is walking backwards, check reward signs

---

## 📞 Contact & Escalation

**If stuck for >30 minutes on any task**:
1. Save current state to log file
2. Document the error with full stack trace
3. Flag for human review in log: `[BLOCKED - NEEDS REVIEW]`

**Expected total time**: 5-8 hours  
**Expected final result**: PPO model achieving 1.5-2.0m (43-90% improvement)

---

## ✅ Final Checklist

Before marking as complete:

- [ ] All 6 tasks completed and logged
- [ ] Zero residual test passes (4.63m ± 0.05m)
- [ ] Residual sweep finds at least 1 promising direction
- [ ] 100k training completes without errors
- [ ] Final model achieves distance > baseline + 2σ
- [ ] All logs saved to `logs/residual_rl_v2/`
- [ ] README.md updated with new features
- [ ] SESSION_2026_06_08.md created with full context

**Status tracking**: Update in `logs/residual_rl_v2/STATUS.txt`

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-08 23:15  
**Next Review**: After Codex execution

# ResidualRLEnvV2 Implementation Report

## Summary

Created complete ResidualRLEnvV2 training system with all required components:

1. **train_residual_rl_v2.py** - Main training script with ResidualRLEnvV2 environment
2. **test_zero_residual_v2.py** - Zero residual validation test
3. **test_residual_sweep.py** - Constant and phase-gated residual sweep
4. **train_v2_sanity.py** - 100k training sanity check

## Implementation Details

### ResidualRLEnvV2 Environment

**Core Features:**
- Action space: 2D (hip-only control: left_hip, right_hip)
- Observation space: 42D (20 original + 22 new features)
- Inner loop: 5ms per PPO step (200Hz control frequency)
- Episode length: Configurable (500 steps default = 2.5s, 2400 steps = 12s)

**New Observations (22 dimensions):**
- left_phase one-hot (4D): stance_early, stance_late, swing_thrust, swing_retract
- right_phase one-hot (4D): same phases for right leg
- support_foot one-hot (2D): left/right support foot indicator
- time_since_last_contact (1D): normalized by 1.5s, clipped [0,2]
- time_since_burst_start (1D): normalized by 1.5s, clipped [0,2]
- E_current (1D): current mechanical energy / E_ref_mean
- E_diff (1D): (E_current - E_ref) / E_ref_mean
- V13.7 base torques (4D): normalized by 4.0 N·m
- last residuals (4D): normalized by residual_scale

**Action Mapping:**
```python
residual[0] = residual_scale * action[0]  # left_hip
residual[1] = 0.0                          # left_knee (fixed)
residual[2] = residual_scale * action[1]  # right_hip
residual[3] = 0.0                          # right_knee (fixed)
```

**Baseline-Relative Reward:**
```python
reward = (
    50.0 * (dx - dx_ref)          # Forward progress vs baseline
    - 0.02 * residual_cost         # L2 penalty on residuals
    - 0.01 * smooth_cost           # Smoothness penalty
    - 0.02 * excess_work           # Extra energy consumption
)

# Terminal bonuses/penalties:
if truncated: reward += 100.0 * final_improvement
if terminated: reward -= 50.0
```

**Parameters:**
- `residual_scale`: 0.05 (initial value, 5% of max torque)
- `inner_steps`: 5 (200Hz PPO frequency)
- `max_steps`: 500 for training (2.5s episodes), 2400 for testing (12s episodes)

### Test Scripts

**test_zero_residual_v2.py:**
- Validates that action=[0,0] reproduces V13.7 baseline
- Runs 10 episodes with 12s duration
- Expected: ~4.63m average distance
- Saves reference trajectory for comparison

**test_residual_sweep.py:**
- Constant residual sweep: [-0.2, -0.1, 0, 0.1, 0.2] N·m
- Phase-gated strategies:
  - stance_early_left/right
  - swing_thrust_left/right
  - alternating (left stance + right swing)
- Goal: Find at least 1 combination with +3% improvement
- Runs 5 episodes per configuration

**train_v2_sanity.py:**
- 100k timestep training run
- Evaluation every 25k steps (10 episodes each)
- Acceptance criteria:
  - Final distance > baseline + 2σ (>4.83m)
  - Final failure rate = 0%
- Tracks training progression

## Current Status

### ✅ Completed

1. **Environment Implementation**
   - All 42 observation dimensions implemented
   - Hip-only action mapping (2D)
   - Baseline-relative reward function
   - V13.7 controller integration
   - FSM state tracking (support_foot, burst_start_t, phases)
   - Proper parameter initialization (matching test_v137_identity.py)

2. **Test Scripts**
   - Zero residual test script complete
   - Residual sweep test script complete
   - Training sanity check script complete
   - Debug scripts for diagnostics

3. **Code Quality**
   - Proper imports and path handling
   - Docstrings and comments
   - Dataclass-based result recording
   - JSON output for all tests

### ⚠️ Known Issues

**Critical: V2 Environment Stability**

The ResidualRLEnvV2 environment experiences premature termination (~4s instead of 12s):

```
Test Results:
- Episode duration: 4.00s (expected 12.00s)
- Distance: -0.281m (expected ~4.63m)
- Failure reason: "stuck"
- Pattern: Walker moves forward initially (0.334m @ 2s), then falls backwards
```

**Root Cause Analysis:**

1. **Verified Working:**
   - test_v137_identity.py achieves 4.630m in 12.00s ✓
   - V13.7 controller parameters correctly loaded ✓
   - Initial conditions properly set (initial_vx=0.03) ✓
   - Motor models and friction compensation active ✓

2. **Suspected Issues:**
   - FSM state update timing/logic may differ from test_v137_identity
   - Phase calculation in `_get_phase()` may not match V13.6 control_v136 expectations
   - Model file sharing between environment instances (MODEL_PATH collision)
   - Subtle differences in how controller is called per timestep

3. **Evidence:**
   - Debug output shows correct initial motion (hip_vx increases from 0.03 to 0.14)
   - Support foot switches correctly (left → right @ ~1s)
   - Controller torques are being computed and applied
   - Walker achieves partial forward progress before failure

**Debugging Artifacts Created:**
- `debug_v2_env.py` - Basic environment check (shows correct initial behavior)
- `debug_distance.py` - Distance calculation verification
- `debug_failure.py` - Failure detection timing
- `debug_init.py` - Parameter initialization check
- `debug_full_episode.py` - Full 12s episode run
- `compare_v137_v2.py` - Direct comparison between V137Identity and V2

## Files Created

All files in `D:\Dunna\Documents\hw-1\rl_training\`:

1. **train_residual_rl_v2.py** (676 lines)
   - ResidualRLEnvV2 class
   - Training function train_residual_rl_v2()
   - Environment factory make_residual_env_v2()

2. **test_zero_residual_v2.py** (223 lines)
   - Zero residual validation test
   - Statistical analysis
   - JSON report generation

3. **test_residual_sweep.py** (307 lines)
   - Constant residual sweep
   - Phase-gated residual strategies
   - Top-N configuration ranking

4. **train_v2_sanity.py** (256 lines)
   - 100k training with periodic evaluation
   - Custom EvalCallbackV2
   - Progress tracking and diagnosis

5. **Debug scripts** (5 files)
   - Diagnostic tools for troubleshooting

## Next Steps

### Immediate (Required to Pass Tests)

1. **Fix FSM State Management**
   - Compare FSM update logic between test_v137_identity and ResidualRLEnvV2
   - Ensure `_update_fsm_state()` exactly matches V13.7 event detection
   - Verify `candidate_start_t`, `contact_reported`, `last_event_t` are updated correctly

2. **Verify Controller Integration**
   - Add detailed logging to `_compute_v137_base_control()`
   - Compare torque outputs step-by-step with test_v137_identity
   - Ensure friction compensation is applied correctly

3. **Model File Isolation**
   - Consider using instance-specific model paths
   - Or ensure write_model_v137() is only called once per environment lifecycle

### Testing Protocol (Once Fixed)

1. Run `test_zero_residual_v2.py --episodes 10`
   - Must achieve: avg distance 4.6±0.3m, 100% success rate

2. Run `test_residual_sweep.py`
   - Must find: ≥1 configuration with +3% improvement

3. Run `train_v2_sanity.py --timesteps 100000`
   - Must achieve: final distance >4.83m, failure rate 0%

### Training (After Tests Pass)

- Longer training runs (500k-1M timesteps)
- Curriculum learning (gradually increase residual_scale)
- Hyperparameter tuning (learning rate, reward weights)
- Multi-seed evaluation for robustness

## Technical Notes

**Parameter Construction (Critical):**
```python
# Must match test_v137_identity.py exactly
base0 = PassiveArmsParams()
overrides = dict(
    duration=12.0,
    slope_deg=0.0,
    arm_mass=0.01,
    arm_length=0.40,
    arm_damping=0.02,
    arm_stiffness=0.0,
    thigh_length=float(base0.thigh_length * 1.02),
    shank_length=float(base0.shank_length * 1.02),
    step_length=float(base0.step_length * 1.02),
    foot_radius=0.042,
)
base = replace(base0, **overrides)
fsm = make_v137_fsm(base)
motor = MOTOR_PRESETS["mx64ar"]
```

**Baseline Distance Calculation:**
```python
# V13.7 walks 4.63m in 12s
# At 200Hz PPO frequency (5ms per step):
baseline_dx_per_step = 4.63 / 12.0 * 0.005  # = 0.001929 m/step
```

**Energy Reference:**
```python
E_ref = params.fsm.swing_thrust.E_target  # 52.66 J
E_ref_mean = 52.66  # For normalization
```

## Conclusion

The ResidualRLEnvV2 system is **architecturally complete** with all required features implemented:
- ✅ 42D observation space with FSM phase information
- ✅ 2D hip-only action space
- ✅ Baseline-relative reward function
- ✅ Three comprehensive test scripts
- ✅ Proper V13.7 parameter initialization

However, the environment has a **critical stability bug** that causes premature episode termination. The V13.7 controller itself works perfectly (proven by test_v137_identity.py), so the issue is in the integration layer.

**Estimated fix time:** 2-4 hours of debugging to align FSM state management with test_v137_identity.py.

Once fixed, the system should be ready for training with high confidence of meeting the +3% improvement target.

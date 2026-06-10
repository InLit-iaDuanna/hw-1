# Residual RL V2 500k Analysis

## Learning Curve
- 50k: mean=4.769m, std=0.000m, success=100%
- 100k: mean=4.898m, std=0.000m, success=100%
- 150k: mean=4.486m, std=0.000m, success=100%
- 200k: mean=4.954m, std=0.000m, success=100%
- 250k: mean=4.914m, std=0.000m, success=100%
- 300k: mean=4.936m, std=0.000m, success=100%
- 350k: mean=0.150m, std=0.000m, success=0%

## Convergence Analysis
- The policy did not surpass the sweep best during recorded checkpoints.
- Best checkpoint: 4.954m at 200k steps.
- Final checkpoint: 0.150m (-96.75% vs baseline).
- Last-three-checkpoint oscillation: 4.786m.
- Monotonic after 300k: False.
- Stop reason: aborted at 350k because failure_rate=1.000 exceeded the 0.050 threshold.

## Action Distribution Analysis
- Prior action: [0.5, 1.0]; delta scale: 0.02.
- Final actual action mean: [0.5016019940376282, 0.9999768137931824].
- Final actual action std: [0.002573058707639575, 0.0001331123785348609].
- Final actual action range: min=[0.4957326054573059, 0.9988871216773987], max=[0.5050334334373474, 1.0].

## Comparison With 100k Run
- 100k PPO: 4.898m (+5.79%).
- Aborted 350k PPO attempt: 0.150m (-96.75%).
- Extra 400k-step gain: -4.748m.

## Failure Diagnosis
- Final policy failed 10/10 diagnostic episodes at step 750, sim_time=3.747s, distance=0.150m.
- Failure type: `fall_down`; hip_height=0.221m; phase=`L:stance_early|swing_retract`.
- This is a mid-episode collapse, not an immediate startup failure or a late-horizon fall.
- Best saved policy remained stable: 10/10 success over the full 12.0s horizon, distance=4.954m.
- Likely issue: catastrophic policy drift after 300k; the final action stayed near the prior but small state-dependent residual changes destabilized the gait.

## Diagnosis
FAIL

# V14c: arm mass lightening x slice C

V14c tests whether passive arm mass is the root cause of V14b's geometry-edge
instability. It keeps V14b's passive-arm mechanism and V13.6.1 best candidate 6
FSM fixed, then scans `arm_mass` across the V13 slice-C geometry grid.

This is still quasi-passive control: hip and knee use the active FSM controller;
arms and ankle remain passive. Arm-mass reduction is mechanism tuning, not a new
control law. Do not describe V14c as pure passive, robust control, or
sim-to-real ready.

## Files

- `simulate_v14c.py`: V14 passive arms plus V13.6.1 best FSM hip control.
- `scan_v14c_C_foot_leg.py`: 4 x 6 x 6 arm-mass and geometry scan.
- `analyze_v14c.py`: heatmaps and cross-version comparison JSON.
- `render_v14c.py`: offline MP4 renderer for saved single-run CSV outputs.
- `view_v14c.py`: interactive MuJoCo playback for saved single-run CSV outputs.

Generated XML is isolated under `out/v14c_models/` and must not rewrite V10,
V13.6, V14, or V14b model XML files.

## Scan

Fixed controller and mechanism settings:

- `arm_length = 0.40`
- `arm_damping = 0.02`
- `arm_stiffness = 0.0`
- `swing_thrust_k_E = 7.5`
- `swing_thrust_k_PD = 10.0`
- `swing_thrust_tau_max = 4.0`
- `swing_retract_tau_max = 3.0`
- `stance_late_tau_max = 4.0`
- `E_target = 52.66 J`
- Energy effective mass is `hip_mass + 2 * torso_mass`; passive arm mass is not
  folded into the controller energy channel.

Official grid:

- `arm_mass in {0.01, 0.02, 0.03, 0.05}`
- `foot_radius = linspace(0.030, 0.050, 6)`
- `leg_scale = linspace(0.90, 1.10, 6)`
- `duration = 12 s`
- `sample_hz = 40`

## Commands

```powershell
cd D:\Dunna\Documents\hw-1
$env:PYTHONIOENCODING='utf-8'

.\.venv-mujoco\Scripts\python.exe .\v14c_arm_mass_lightening\scan_v14c_C_foot_leg.py --smoke-only
.\.venv-mujoco\Scripts\python.exe .\v14c_arm_mass_lightening\scan_v14c_C_foot_leg.py
.\.venv-mujoco\Scripts\python.exe .\v14c_arm_mass_lightening\analyze_v14c.py
```

## Outputs

- `out/v14c_C_foot_leg.csv`: 144 scan rows with success, contact, phase, energy,
  and torque-saturation diagnostics.
- `out/v14c_C_heatmaps.png`: 2x2 success heatmaps by arm mass, with V13.6.1
  best no-arm and V14b reference domains overlaid.
- `out/v14c_vs_v14b_v1361best.json`: comparison table, success cells, overlap
  relations, monotonicity, `health_check_verdict`, and `primary_verdict`.

## Verdict

The health check is evaluated first:

- `health_check_verdict = v14b_reproduction_passed` if `m=0.05` gives 2, 3, or
  4 successes out of 36.
- `health_check_verdict = v14b_reproduction_failed_must_diagnose` otherwise.

`primary_verdict` is only filled when the health check passes:

- `m=0.01 >= 5/36`: `arm_mass_is_root_cause_v15_unblocked`
- `m=0.01 == 4/36`: `partial_arm_mass_relief_consider_elastic_attachment`
- `m=0.01 == 3/36`: `arm_mass_not_dominant_cause_route_X_failing`
- `m=0.01 < 3/36`: `unexpected_regression_must_diagnose`

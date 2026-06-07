# V11 rugged terrain robustness report

V11 extends V10 with sagittal hfield terrain, single impulse disturbance, and contact-phase noise hooks.
It remains quasi-passive because hip and knee actuators are active; failed runs are robustness boundary evidence.

| Case | Terrain | Impulse | Success | Touchdowns | Distance (m) | Time (s) | Input energy (J) | CoT | Failure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Flat baseline | 0.000 | 0.0 | yes | 12 | 4.56 | 11.99 | 16.22 | 0.060 | completed |
| 1.5 cm terrain | 0.015 | 0.0 | yes | 12 | 4.44 | 11.99 | 15.94 | 0.061 | completed |
| 4 cm + 60 N impulse | 0.040 | 60.0 | no | 7 | 2.13 | 5.21 | 5.94 | 0.047 | fall_down |

Recommended interpretation: flat and mild terrain cases show the inherited V10 controller still walks under small terrain disturbance; the hard case fails after the impulse, so it should be reported as the first robustness boundary rather than a success.

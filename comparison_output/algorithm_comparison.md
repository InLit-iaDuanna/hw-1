# Algorithm Performance Comparison

**Generated**: 2026-06-10 23:46:50
**Baseline**: 4.630m (V13.7 FSM + Friction Compensation)

## Performance Summary

| Algorithm | Distance (m) | Improvement | Success Rate | Std Dev | Method | Training |
|-----------|--------------|-------------|--------------|---------|--------|----------|
| Sweep Best [0.5, 1.0] | 4.973 | +7.40% | 100% | 0.000000 | FSM + Constant Residual | Grid search |
| Prior Action [0.5, 1.0] | 4.973 | +7.40% | 100% | 0.000000 | FSM + Constant Residual | Zero-shot |
| Residual RL (100k) | 4.898 | +5.79% | 100% | 0.000000 | FSM + PPO Residual | 100k steps |
| V13.7 FSM + Friction Comp | 4.630 | +0.00% | 100% | 0.000000 | Model-based FSM | N/A |

## Key Findings

- **Best Performance**: Sweep Best [0.5, 1.0] achieved 4.973m (+7.40%)
- **Best RL Result**: Residual RL (100k) shows 4.898m
- **Zero-shot Transfer**: Prior action achieves 4.973m without training
- **Robustness**: All methods achieve 100% success rate with std ¡Ö 0

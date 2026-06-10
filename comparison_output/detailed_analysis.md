# Detailed Algorithm Analysis

## Model-based

### V13.7 FSM + Friction Comp

- **Distance**: 4.630m
- **Success Rate**: 100%
- **Std Dev**: 0.000000
- **Method**: Model-based FSM
- **Training**: N/A

## Hybrid (FSM + RL)

### Residual RL (100k)

- **Distance**: 4.898m
- **Success Rate**: 100%
- **Std Dev**: 0.000000
- **Method**: FSM + PPO Residual
- **Training**: 100k steps

## Hybrid (FSM + Constant)

### Prior Action [0.5, 1.0]

- **Distance**: 4.973m
- **Success Rate**: 100%
- **Std Dev**: 0.000000
- **Method**: FSM + Constant Residual
- **Training**: Zero-shot

### Sweep Best [0.5, 1.0]

- **Distance**: 4.973m
- **Success Rate**: 100%
- **Std Dev**: 0.000000
- **Method**: FSM + Constant Residual
- **Training**: Grid search

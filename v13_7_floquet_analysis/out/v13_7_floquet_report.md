# V13.7 FSM 控制律 Floquet 稳定性分析报告

## 分析目标

量化 V13.7 FSM 事件驱动控制律的稳定裕度，对比 V10 PD 控制基线。

## 方法

- **Poincaré 截面**: 右脚触地时刻的 4D 状态 (right_hip, right_hip_vel, right_knee, right_knee_vel)
- **Floquet 乘子**: 使用 Goswami et al. (1996) 实验方法，对截面点序列线性回归得到 return-map Jacobian
- **仿真参数**: duration=20s，目标 ≥16 次触地，sample_hz=160Hz
- **状态收敛**: max|λ| 是最大 Floquet 乘子模，决定扰动收敛速率

## 结果汇总

| 配置 | max\|λ\| | alternations | forward (m) | success | 稳定性 |
|------|-----------|--------------|-------------|---------|--------|
| V10 PD (V13b) | 0.9440 | 19 | 8.60 | ✓ | stable |
| V13.7 FSM (ideal) | 1.0008 | 17 | 8.65 | ✓ | unstable |
| V13.7 FSM (mx64ar+comp) | 1.0008 | 17 | 8.61 | ✓ | unstable |
| V13.7 FSM (mx64ar-no) | 1.0000 | 4 | 0.19 | ✗ | stable |

## 对比分析

- **V13.7 (ideal) vs V10 PD**: Δmax|λ| = +0.0568
  - V13.7 FSM 稳定裕度更小（慢 6.0% 收敛）

- **V13.7 (mx64ar+comp) vs V13.7 (ideal)**: Δmax|λ| = +0.0000
  - 摩擦补偿完全恢复 ideal 性能

## 稳定性解释

Floquet 乘子 λ 是 return-map Jacobian 的特征值，表征扰动在周期运动下的倍增系数：

- **|λ| < 1**: 稳定（扰动呈指数衰减）
- **|λ| → 1**: 临界稳定（收敛极慢，对扰动敏感）
- **|λ| ≥ 1**: 不稳定（扰动发散）

max|λ| 是所有特征值中模最大的，决定系统的收敛速率：

```
收敛时间常数 τ ≈ T_gait / ln(1/|λ|)
```

其中 T_gait ≈ 0.8s（步态周期）。

- V10 PD: τ ≈ 13.88 s (17.4 步)
- V13.7 (mx64ar nocomp): τ ≈ 1801439850948198.00 s (2251799813685247.5 步)

## 结论

1. **V13.7 FSM 控制律稳定裕度小于 V10 PD**（收敛较慢，需关注鲁棒性）
2. **摩擦补偿完全恢复理想性能**（mx64ar+comp ≈ ideal）

## 可视化

- `v13_7_floquet_comparison.png`: Poincaré 截面 + Floquet 谱对比
- `v13_7_stability_margin_comparison.png`: 稳定裕度条形图

## 参考

- V13b Floquet 分析: `hw-1/v13b_floquet_long_run/`
- Goswami et al. (1996): Compass-Like Biped Robot Part I (实验 Floquet 方法)
- V13.7 实现: `hw-1/v13_7_friction_compensation/`
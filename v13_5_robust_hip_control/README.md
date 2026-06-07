# V13.5 鲁棒 hip 控制律探索（**否决归档版本**）

**状态**：方案 A、A' 均失败。本目录保留作为负面发现的归档。完整教训和机理推断见 [`v13_5_lessons.md`](v13_5_lessons.md)。

## TL;DR

V13 决策门发现 V10 hip 控制律是 (kp, kd) 平面孤立点。本版本尝试两条修复路径：

| 方案 | 改动 | 结果 |
|---|---|---|
| A | 步周期前馈 EMA 替代静态 gait_period | baseline alpha=0 ✓ 退化等价；alpha≥0.1 在 baseline 上反而摔；V10 失败点全摔 |
| A' | 提高 hip_torque_limit 4→7→20 | 4/36（保持 4）、0/36（提高任一档），完全反直觉 |

A' 反直觉结果迫使重新分析。饱和占空比统计揭示 V10 hip 实为 **bang-bang 隐式饱和供能脉冲**，PD 增益是占空比形状参数而非线性反馈。

正向解决方案是方案 C（Raibert 能量注入），但需要先 V13b 拿到极限环能量目标 E*。

## 运行（仅用于复现负面结果）

```powershell
cd D:\Dunna\Documents\hw-1
# baseline 上 alpha 扫描（应在 alpha=0 时 ✓，其他 ✗）
.\.venv-mujoco\Scripts\python.exe .\v13_5_robust_hip_control\simulate_v13_5.py --alpha 0.0 --save-prefix v13_5_alpha00
.\.venv-mujoco\Scripts\python.exe .\v13_5_robust_hip_control\simulate_v13_5.py --alpha 0.4 --save-prefix v13_5_alpha04

# V10 失败点 (kp=15, kd=2.7) 上 alpha 扫描（全摔）
.\.venv-mujoco\Scripts\python.exe .\v13_5_robust_hip_control\simulate_v13_5.py --alpha 0.2 --hip-kp 15 --hip-kd 2.7 --save-prefix v13_5_F02_a02
```

A' 的 36 点切片 G 在 V13 atlas 里跑：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\scan_atlas_v13.py --slice G_kp_torque --grid 6
```

饱和占空比诊断：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\diagnose_saturation.py
```

## 学术诚信

不能表述 V13.5 为"实现了鲁棒控制"。正确表述：V13.5 揭示 V10 hip 为隐式饱和脉冲驱动，**否决了 PD 调参方向**，确立方案 C 为正向路线。

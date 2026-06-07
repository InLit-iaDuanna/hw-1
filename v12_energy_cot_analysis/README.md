# V12 能量流 / CoT / Floquet 横向分析

V12 不跑新仿真，纯后处理 V07-V11 已有的 `out/*_data.csv` + `*_summary.json`，回答两个问题：
1. 各版本能量怎么走的（机械能时序、每步碰撞损耗、Cost of Transport）
2. 极限环稳不稳（Poincaré 收敛 + 实验 Floquet 乘子，方法见 Goswami 1996）

**对比范围**：V07-V11。V01-V06 是纯运动学 / 无质量模型，CoT 不可直接计算，本版本不混入。

**所有 V08-V11 版本均为准被动**（hip + knee 主动稳定，ankle 被动），不能与文献纯被动 McGeer CoT 直接比较。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\v12_energy_cot_analysis\analyze_energy_cot_v12.py
.\.venv-mujoco\Scripts\python.exe .\v12_energy_cot_analysis\analyze_floquet_v12.py
.\.venv-mujoco\Scripts\python.exe .\v12_energy_cot_analysis\render_report_v12.py
```

## 结果速览

| 版本 | 质量 [kg] | 距离 [m] | 输入能 [J] | CoT | 备注 |
|---|---:|---:|---:|---:|---|
| V07 | 4.50 | 1.10 | — | N/A | 纯被动失败 |
| V08 | 5.00 | 0.26 | 0.07 | 0.006 | 准被动短距离 |
| V09 | 5.05 | 4.43 | 18.30 | **0.083** | 准被动稳态基线 |
| V10 | 5.05 | 4.56 | 16.22 | **0.072** | 滚动足，周期慢但更省 |
| V11 平地 | 5.05 | 4.56 | 16.22 | 0.072 | V10 复现 |
| V11 小幅地形 | 5.05 | 4.44 | 15.94 | 0.073 | 0.015 m 起伏，CoT 几乎不变 |
| V11 大扰动 | 5.05 | 2.13 | — | N/A | 60 N 脉冲失败 |

**关键观察**：V10 的滚动足在更慢的步周期下（0.8 s vs V09 0.45 s）反而 CoT 降低 13%，说明踝部被动滚动确实在做正功（节省髋膝主动维持的能耗）。

## Floquet 乘子（实验估计）

| 版本 | 左脚触地点数 | 使用对数 | max&#124;λ&#124; | 评价 |
|---|---:|---:|---:|---|
| V09 | 11 | 8 | **0.891** | 4D 状态空间下超定，结果可信，稳定（<1）|
| V10 | 7 | 4 | 1.000 | 数据点不足（恰好 = 4D），lstsq 退化为精确插值，谱不可信 |
| V11 平地 | 7 | 4 | 1.000 | 同上 |

V10/V11 想要可信的 Floquet 谱，需要把 `simulate_*` 的 `duration` 从 12 s 拉到至少 20 s（保证 ≥ 10 个左脚触地点）。V12 不重跑，作为 V13/V21 的 follow-up 记录。

## 输出

- `out/v12_energy_cot_table.csv` — 横向表
- `out/v12_mechanical_energy.png` — V09/V10/V11 机械能时序
- `out/v12_collision_loss_per_step.png` — 每步 ΔE 柱状
- `out/v12_cot_comparison.png` — CoT 对比
- `out/v12_floquet_spectrum.png` — 单位圆 + 特征值
- `out/v12_poincare_convergence.png` — 收敛轨迹
- `out/v12_floquet_table.json` — 数值
- `out/v12_report.png` — 拼合总览

## 学术口径

- 报告时务必标注 V07-V11 全部为"含主动稳定的准被动"。
- V10/V11 的 Floquet 数值不可信，应作为"实验 Floquet 方法已就绪、待 V13 增加仿真时长后重算"陈述。
- V11 大扰动失败 CoT 不计算，作为稳定盆地边界的能量证据出现在碰撞损耗图。
- 机械能时序是 hip body 平动近似，不含腿部转动惯量，量级可对比但不可作为绝对值引用。

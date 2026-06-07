# V13b: 长程 Floquet 重算 + 极限环辨识 + 扰动恢复

## 背景

V12 留下的 follow-up：V10/V11 的 baseline 仅 12 s（7 次左脚触地），4D Floquet
退化为精确插值，谱不可信。V13b 把 duration 拉到 20 s，得到 ≥ 16 次触地，让
return-map Jacobian 估计有 lstsq 的真正残差。

学术口径：仍是准被动（hip + knee 主动 PD），不与文献纯被动 McGeer Floquet 直接对照。

## 文件

- `analyze_floquet_v13b.py` — 跑 V10 baseline @ duration=20 s，提取 Poincaré
  截面（4D：right_hip / right_hip_vel / right_knee / right_knee_vel），算
  Floquet 乘子 + 极限环能量 E*。
- `disturbance_recovery_v13b.py` — 在不动点 fp 附近 4 个独立轴上 ±10%（最小 0.05）
  注入扰动后跑 20 s 仿真，看 ‖x_k − fp‖ 衰减曲线是否吻合慢模 |λ|=0.944。
- `render_v13b.py` — 生成扰动恢复与相平面收敛可视化视频（MP4）。
- `out/` — 所有结果（CSV / JSON / PNG / MP4）。

## 关键结果（baseline）

- duration = 20 s，alternations = 19，forward = 8.60 m，success = true
- fp = (-0.0729, 0.4991, 0.0336, 0.4340)
- Floquet 乘子 |λ| = {0.399, 0.399, 0.605, **0.944**}（max 即慢模）
- E* = 52.66 ± 0.53 J（mass = 5.10 kg）

## 扰动恢复结果

每个轴 +0.05（rad 或 rad/s）独立注入，4 case 全部完成 19 次触地（未摔倒），
Poincaré 序列到 fp 的距离用 d_k = d_0 · |λ|^k 拟合：

| axis            | δ      | n_sec | λ_fit  | Δ vs 0.944 | 状态      |
|-----------------|-------:|------:|-------:|-----------:|-----------|
| right_hip       | +0.050 |    19 | 0.9652 |    +2.25 % | completed |
| right_hip_vel   | +0.050 |    19 | 0.9645 |    +2.17 % | completed |
| right_knee      | +0.050 |    19 | 0.9533 |    +0.99 % | completed |
| right_knee_vel  | +0.050 |    19 | 0.9583 |    +1.52 % | completed |

**结论**：4 case 的实验衰减率 λ_fit 与 Floquet 慢模 |λ|=0.944 一致性良好（偏差
≤ +2.25 %，且系统性偏高 1–2 %，方向上表明衰减略慢于 4D 线性预测）。两点局限：

1. 4D 中 λ_fit 是各轴沿慢模本征向量分量的复合衰减率，并非严格等于慢模；这里观察到的轻微偏高可能源于其他模在 19 步内尚未完全衰减，以及极限环本身的 Poincaré 截面噪声底（约 0.4 m，限制了拟合纵深）。
2. ±0.05 全部留在稳定盆地内，未观察到摔倒；要确定盆地边界还需进一步外推幅值（V14 工作，不在 V13b 范围）。

## 为 V13.5 方案 C 提供的接口

- `out/v13b_floquet_summary.json` 含字段 `E_star_J`（52.66 J）+ `mass_kg`（5.10 kg），
  可直接作为方案 C 的能量目标 + 反馈环参考。
- 不动点 fp 在该 JSON 的 `fixed_point` 字段。

## 复现

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv-mujoco\Scripts\python.exe .\v13b_floquet_long_run\analyze_floquet_v13b.py
.\.venv-mujoco\Scripts\python.exe .\v13b_floquet_long_run\disturbance_recovery_v13b.py
.\.venv-mujoco\Scripts\python.exe .\v13b_floquet_long_run\render_v13b.py
```

## 输出产物

### 数据文件
- `out/v13b_floquet_summary.json` — Floquet 分析结果（特征值、极限环能量）
- `out/v13b_disturbance_summary.json` — 扰动恢复汇总（4 case 拟合结果）
- `out/v13b_baseline_20s_data.csv` — baseline 20s 仿真完整轨迹
- `out/v13b_dist_<axis>_data.csv` — 每个扰动 case 的完整轨迹（4 个文件）

### 可视化
- `out/v13b_floquet_report.png` — Poincaré 截面 + Floquet 谱静态图
- `out/v13b_disturbance_recovery.png` — 4 case 衰减曲线对比图
- `out/v13b_perturbation_recovery.mp4` — 扰动恢复步态动画（2x2 布局，20 秒）
- `out/v13b_phase_portrait.mp4` — 相平面轨迹螺旋收敛动画（4 子图）

# V11 崎岖地形与扰动鲁棒性

V11 在 V10 足踝滚动准被动步态基础上，加入不平整地形、单次外力脉冲和触地相位噪声接口，用于评估真实接触步态的鲁棒性边界。它不是纯被动版本；髋部和膝部仍有主动稳定力矩。

## 与 V10 的差异

- 地面从平面扩展为可选 MuJoCo `hfield`，沿前进方向生成小幅起伏。
- 新增髋部单次外力脉冲，用于测试冲击后的恢复能力。
- 新增触地相位噪声接口，用于模拟接触事件判定扰动。
- 保留 V10 的滚动足、被动踝关节和髋膝主动稳定控制律。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\v11_rugged_terrain_robustness\simulate_rugged_gait_v11.py --amplitude 0 --impulse 0 --save-prefix v11_sanity_flat
.\.venv-mujoco\Scripts\python.exe .\v11_rugged_terrain_robustness\simulate_rugged_gait_v11.py --amplitude 0.015 --save-prefix v11_smoke_terrain
.\.venv-mujoco\Scripts\python.exe .\v11_rugged_terrain_robustness\simulate_rugged_gait_v11.py --amplitude 0.04 --impulse 60 --impulse-t 4 --save-prefix v11_smoke_hard
.\.venv-mujoco\Scripts\python.exe .\v11_rugged_terrain_robustness\analyze_rugged_gait_v11.py
```

## 当前结果

| Case | 地形振幅 | 脉冲 | 结果 | 说明 |
|---|---:|---:|---|---|
| `v11_sanity_flat` | 0.000 m | 0 N | 成功 | V10 平地基线复现，约 12 s 内前进 4.56 m |
| `v11_smoke_terrain` | 0.015 m | 0 N | 成功 | 小幅崎岖地形下仍能连续交替触地 |
| `v11_smoke_hard` | 0.040 m | 60 N | 失败 | 约 5.21 s 跌倒，是当前控制律的鲁棒性边界样本 |

## 输出

- `out/v11_*_data.csv`：各场景逐时刻仿真数据。
- `out/v11_*_summary.json`：各场景成功指标、输入能量和失败分类。
- `out/v11_robustness_report.png`：鲁棒性对比报告图。
- `out/v11_report_text.md`：可放入报告中的文字说明。

## 报告表述

V11 应写成“在 V10 准被动滚动足步态基础上的地形与扰动鲁棒性实验”。平地和小扰动成功说明控制律有一定稳定裕度；强扰动失败应作为稳定域边界如实报告，不能修饰为成功，也不能表述为纯被动极限环证明。

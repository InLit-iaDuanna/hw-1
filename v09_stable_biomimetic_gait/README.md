# V9 仿生准被动稳定行走版

V9 在 MuJoCo 真实接触环境中使用带膝 MVE 机构，并加入髋部/膝部主动稳定力矩，实现连续稳定行走。它不是纯被动极限环证明，而是“真实接触 + 准被动补能/稳定”的工程展示版。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\v09_stable_biomimetic_gait\scan_stable_params_v9.py
.\.venv-mujoco\Scripts\python.exe .\v09_stable_biomimetic_gait\render_stable_gait_v9.py
.\.venv-mujoco\Scripts\python.exe .\v09_stable_biomimetic_gait\view_stable_gait_v9.py
```

## 输出

- `out/v9_stable_walk.mp4`：真实接触稳定步态视频。
- `out/v9_stable_walk_data.csv`：状态、接触和输入能量数据。
- `out/v9_best_params.json`：最佳参数和成功指标。
- `out/v9_scan_results.csv`：参数扫描表。

## 报告表述

V9 可以说明“准被动仿生行走在真实 MuJoCo 接触中可以稳定连续运动”，但不能写成“纯被动”。纯被动极限环证明仍应引用 V5。

# V10 足踝滚动仿生步态版

V10 在 V9 稳定真实接触步态的基础上加入踝关节和脚掌滚动接触结构，用于展示“脚跟接触-足底滚动-脚趾离地”的仿生机械转译。它不是纯被动极限环证明；纯被动证明仍引用 V5 的混合动力学与 Poincare 收敛结果。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\scan_rolling_foot_params_v10.py
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\analyze_rolling_foot_gait_v10.py
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\analyze_v10_phase_portrait.py
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\render_rolling_foot_gait_v10.py
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py
```

## 输出

- `out/v10_rolling_foot_walk.mp4`：足踝滚动中文标注动画。
- `out/v10_rolling_foot_walk_data.csv`：仿真数据表。
- `out/v10_rolling_foot_summary.json`：最佳仿真参数、成功指标和能量统计。
- `out/v10_rolling_foot_report.png`：统一 4 格报告图，包含轨迹、触地、关节角和相位图。
- `out/v10_phase_portrait.png`：髋、膝、踝角度-角速度相位图。
- `out/v10_best_params.json`：最佳参数。
- `out/v10_scan_results.csv`：参数扫描表。

## 报告表述

V10 保留髋部和膝部主动稳定力矩，踝关节只使用被动弹簧、阻尼和限位。因此 V10 应表述为“准被动仿生足踝滚动步态展示”，不能表述为纯被动极限环证明。

相位图 `v10_phase_portrait.png` 展示髋、膝、踝关节的角度-角速度周期轨迹，以及左右脚触地截面点。该图用于说明 V10 运动具有重复周期结构；但由于 V10 含髋膝主动稳定，纯被动极限环证明仍应引用 V5。

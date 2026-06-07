# V4 双腿指南针极限环 MuJoCo 版

V4 用两条腿的指南针模型把 V3 的极限环机理转成更像步态的外观。模型包含髋部质量块、左右刚性腿、脚端和斜坡，不使用 actuator。MuJoCo 负责三维回放，Poincare 数据负责说明极限环收敛。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-compass-limit-cycle\simulate_compass_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-compass-limit-cycle\analyze_compass_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-compass-limit-cycle\view_compass_mujoco.py
```

## 输出

- `out/compass_limit_cycle_data.csv`：双腿步态回放数据
- `out/compass_poincare_points.csv`：每一步 Poincare 截面点
- `out/compass_limit_cycle_report.png`：轨迹、相图、左右脚切换和 Poincare 收敛图
- `out/compass_params.json`：参数和验收结果
- `out/report_text.md`：可放入作业报告的文字

## 说明

V3 用 rimless wheel 给出最清楚的数学证明；V4 把同样的被动极限环思想可视化成双腿指南针步态。当前版本已修复摆动腿角度突跳、脚端穿坡面、实时 viewer 卡顿和左右腿视觉穿模问题。

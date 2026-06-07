# 带膝被动极限环步态 V2

这是旧版 `mujoco-compass-gait/` 之外的新版本。旧版保留为 MuJoCo 软接触指南针模型；本版本用于展示更明确的 **被动动态极限环步态**。

核心思路：

- 结构从两条直腿升级为：髋部质量块、左右大腿、左右小腿、膝铰链、膝限位、圆脚端、斜坡。
- 步态由混合动力学事件生成：单支撑滚落、摆动腿屈膝、膝限位伸直、脚地碰撞、左右换腿。
- MuJoCo 只做三维回放，不让软接触求解器决定步态，所以动画不会因为接触求解卡住。
- 没有 actuator，没有腿部电机，也没有髋部平移电机。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-kneed-limit-cycle\simulate_kneed_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-kneed-limit-cycle\analyze_kneed_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-kneed-limit-cycle\render_kneed_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-kneed-limit-cycle\view_kneed_limit_cycle.py
```

## 输出

- `out/kneed_limit_cycle.mp4`：带膝被动步态视频
- `out/kneed_limit_cycle_data.csv`：髋部、腿角、膝角、触地和步态状态数据
- `out/poincare_points.csv`：每一步触地截面的速度、固定点和误差
- `out/kneed_limit_cycle_report.png`：轨迹、腿角、相图、Poincare 收敛
- `out/kneed_limit_cycle_params.json`：参数和验收结果
- `out/report_text.md`：可直接放入作业报告的中文说明

## 作业表述

本版本比指南针模型更进一步：它不只是展示两条腿交替摆动，而是加入膝关节和膝限位，并用 Poincare 截面说明步间状态逐渐收敛到稳定周期。因此它更适合作为“被动动态极限环步态”的展示版本。

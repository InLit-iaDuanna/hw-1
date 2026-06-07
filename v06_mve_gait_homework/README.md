# V6 被动极限环步态作业表达版

V6 是“作业交付版 / 仿生 MVE 表达版”。它不把 MuJoCo 软接触当作极限环证明，而是引用 V5 的混合动力学和 Poincare 截面收敛作为证明层，再用带膝两段腿结构展示更容易理解的仿生机械运动。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-mve-gait-v6\simulate_mve_gait_v6.py
.\.venv-mujoco\Scripts\python.exe .\passive-mve-gait-v6\analyze_mve_gait_v6.py
.\.venv-mujoco\Scripts\python.exe .\passive-mve-gait-v6\render_mve_gait_explainer.py
.\.venv-mujoco\Scripts\python.exe .\passive-mve-gait-v6\view_mve_gait_v6.py
```

## 输出

- `out/v6_mve_gait_explainer.mp4`：带中文标注的 MuJoCo 展示视频。
- `out/v6_mve_report.png`：可放入 PPT 的综合报告图。
- `out/v6_report_text.md`：可直接放入作业报告的中文说明。
- `out/v6_mve_gait_data.csv`：展示层步态数据。
- `out/v6_poincare_reference.csv`：V6 参考截面收敛数据。

## 版本关系

V5 负责证明：连续单支撑相、触地事件、碰撞换腿和 Poincare 截面收敛。V6 负责表达：髋轴、膝轴、膝限位、圆脚端、支撑脚锁定、摆动腿前向屈膝离地和触地换腿。

推荐作业表述：本设计以被动动态步行为仿生对象，提取“重力补能、惯性摆动、脚地碰撞、交替支撑和周期收敛”作为最小 MVE 功能单元。V5 证明被动极限环，V6 将其转译为带膝机械结构并做三维展示。

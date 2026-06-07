# V3 无轮辐被动极限环证明版

这个版本用于说明“被动动态步态为什么会形成稳定极限环”。它不是仿人外观模型，而是经典 rimless wheel 模型：斜坡重力在每一步补能，脚地碰撞损失能量，步间状态最终收敛到 Poincare 固定点。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-rimless-limit-cycle\simulate_rimless_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-rimless-limit-cycle\analyze_rimless_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-rimless-limit-cycle\render_rimless_limit_cycle.py
.\.venv-mujoco\Scripts\python.exe .\passive-rimless-limit-cycle\view_rimless_mujoco.py
```

## 输出

- `out/rimless_limit_cycle.mp4`：由重力/Poincare 步间数据驱动的下坡回放
- `out/rimless_poincare_report.png`：轨迹、相图和 Poincare 收敛证明图
- `out/rimless_limit_cycle_data.csv`：离散步态证明数据
- `out/rimless_poincare_points.csv`：每步碰撞后的 Poincare 截面点
- `out/rimless_params.json`：参数和固定点结果
- `out/report_text.md`：可放入作业报告的文字

## 说明

`view_rimless_mujoco.py` 现在直接启动真实 MuJoCo 重力模型，`nu=0`，没有 actuator。斜坡由 `gravity="0 0 -9.81"` 和倾斜平面共同产生下坡驱动，不再使用匀速假动画。

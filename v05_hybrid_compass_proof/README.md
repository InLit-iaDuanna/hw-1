# V5 真实混合动力学指南针极限环证明版

V5 的目标是证明“被动极限环步态”，不是继续调 MuJoCo 软接触。核心证明来自混合动力学：连续单支撑相、触地事件、非弹性碰撞换腿映射和 Poincare 截面收敛。MuJoCo 只用于回放 V5 计算出的状态。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-hybrid-compass-v5\simulate_hybrid_compass.py
.\.venv-mujoco\Scripts\python.exe .\passive-hybrid-compass-v5\analyze_hybrid_compass.py
.\.venv-mujoco\Scripts\python.exe .\passive-hybrid-compass-v5\render_hybrid_compass_mujoco.py
.\.venv-mujoco\Scripts\python.exe .\passive-hybrid-compass-v5\view_hybrid_compass_mujoco.py
```

## 输出

- `out/hybrid_compass_poincare_report.png`：核心证明图。
- `out/hybrid_compass_data.csv`：连续相和事件状态。
- `out/hybrid_compass_poincare.csv`：每步 Poincare 截面点。
- `out/hybrid_compass_mujoco.mp4`：MuJoCo 三维回放。
- `out/report_text.md`：可放入作业报告的中文说明。

## 说明

当前环境下载 `scipy` 曾超时，因此实现使用 `numpy` RK4 和事件二分。报告中应说明：V5 是降阶混合动力学证明模型，用于展示 Poincare 收敛和无驱动能量平衡，不把 MuJoCo 回放当作真实接触仿真证明。

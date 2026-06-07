# V7 真实 MuJoCo 接触探索版

V7 尝试让带膝 MVE 机构在 MuJoCo 中依靠重力、惯性、脚地接触、摩擦、碰撞和膝限位运动。它是高风险探索版，不替代 V5 的 Poincare 极限环证明，也不替代 V6 的作业展示。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe .\passive-contact-gait-v7\simulate_contact_gait_v7.py
.\.venv-mujoco\Scripts\python.exe .\passive-contact-gait-v7\scan_contact_params_v7.py
.\.venv-mujoco\Scripts\python.exe .\passive-contact-gait-v7\analyze_contact_gait_v7.py
.\.venv-mujoco\Scripts\python.exe .\passive-contact-gait-v7\render_contact_gait_v7.py
.\.venv-mujoco\Scripts\python.exe .\passive-contact-gait-v7\view_contact_gait_v7.py
```

## 输出

- `out/v7_best_attempt.mp4`：最佳真实接触尝试视频。
- `out/v7_scan_results.csv`：参数扫描结果。
- `out/v7_contact_report.png`：接触探索报告图。
- `out/v7_best_params.json`：最佳参数和结果摘要。
- `out/v7_report_text.md`：可放入报告的中文说明。

## 说明

如果 V7 没有完成 4 次以上交替触地，应诚实写成“真实接触探索未稳定成功”。最终极限环证明仍来自 V5，作业展示仍以 V6 为主。

# V14b：passive arms × V13.6 FSM hip

V14b 是一次探索性回流：把 V13.6 的事件驱动 FSM hip 控制律，接回 V14 的被动摆臂机构栅格里测试。

前置条件不是“强通过”。当前 V13.6 在 V13 切片 C 上的结果是 `4/36 = 11.1%`，属于 tier B partial：优于 V13.5 Plan C 的 `0/36`，但仍低于 V10 baseline 的 `6/36 = 16.7%`。因此 V14b 可以作为探索性恢复实验运行，但除非 V14 摆臂栅格决策门通过，否则不能把它描述成主线控制器胜利。

## 文件

- `simulate_passive_arms_v136.py`：V14 被动摆臂模型 + V13.6 FSM hip 控制律。
- `scan_arm_v136_v14b.py`：V14 原始 `7 x 5` 摆臂质量/长度栅格扫描。
- `analyze_v14b_vs_v14.py`：按 `arm_mass` 行对比 V14 的 V10 控制器扫描结果。
- `render_scan_heatmap_v14b.py`：V14 / V14b / 差值热图。
- `render_v14b.py`：离线 MP4 回放渲染。
- `view_v14b.py`：MuJoCo 交互式回放。
- `scan_v14b_C_foot_leg.py`：V14b × V13 切片 C 几何重扫，使用 V13.6 原 phase 参数。
- `scan_v14b_C_foot_leg_v1361best.py`：V14b × V13 切片 C 几何重扫，使用 V13.6.1 best cand 6 phase 参数。
- `out/`：生成的 CSV、JSON、PNG、MP4 产物。

## 摆臂栅格决策门

关键行是 `arm_mass = 0.05 kg`，因为 V14 在 V10 控制律下这一行是 `0/5` 成功。

- `>= 2/5`：V14b 通过。FSM 部分救回 V10 完全失败的机构行，可作为 V14 主线替代候选。
- `= 1/5`：边缘改善。只能报告为 marginal improvement，并另开 arm damping 敏感性计划。
- `= 0/5`：否决。FSM 没有从几何切片恢复迁移到摆臂机构维度。

已完成的摆臂栅格结果：V14b 总计 `14/35 = 40.0%`，关键行 `arm_mass=0.05` 从 V14 的 `0/5` 提升到 V14b 的 `5/5`。

## 复现命令

```powershell
cd D:\Dunna\Documents\hw-1
$env:PYTHONIOENCODING='utf-8'

.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\simulate_passive_arms_v136.py --arm-mass 0.001 --arm-length 0.40 --save-prefix v14b_baseline
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\simulate_passive_arms_v136.py --arm-mass 0.05 --arm-length 0.40 --save-prefix v14b_critical
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\scan_arm_v136_v14b.py
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\analyze_v14b_vs_v14.py
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\render_scan_heatmap_v14b.py
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\render_v14b.py --tag v14b_critical
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\scan_v14b_C_foot_leg.py
.\.venv-mujoco\Scripts\python.exe .\v14b_state_machine_hip\scan_v14b_C_foot_leg_v1361best.py
```

## 学术诚信口径

V14b 推翻的是一个更窄的 V14 结论：在 V10 PD 控制律下，被动摆臂质量达到或超过 `0.05 kg` 会破坏稳定。它没有证明机构层面的极限，也不意味着“摆臂稳定问题已经解决”。

V14b 仍是准被动控制：hip 和 knee 是主动控制，arms 没有 actuator，ankle 仍是被动弹簧阻尼关节。不能称为纯被动行走、鲁棒控制器，也不能称为 sim-to-real ready。即使完整摆臂栅格通过，也不能宣称 3D 准被动行走，因为摆臂只是矢状面 hinge，没有侧向自由度。

当前 `14/35 = 40.0%` 只是在摆臂参数空间 `arm_mass x arm_length` 上的扫描结果。几何参数空间 `foot_radius x leg_scale`，也就是 V13 切片 C，是另一张决策面；在几何空间没有通过前，不能说 V14b 在所有维度都优于 V14。

V14 / V14b 对比必须保持同栅格、同 duration、同 success 判据：`SUCCESS_TIME`、`SUCCESS_TOUCHDOWNS`、`SUCCESS_FORWARD` 全部沿用 V14 / V10，不放宽阈值制造改善。

FSM 能量通道也保持 V13.6 原始标定：`mass_eff = hip_mass + 2 * torso_mass`。被动摆臂质量没有折入 `E_target=52.66 J`；V14b 测的是“未重新标定的 V13.6 FSM 是否能迁移到摆臂机构维度”，不是引入新的 arm-aware energy controller。

V14b × 切片 C 显示，摆臂在几何边缘仍破坏稳定：`8.3% < V13.6 11.1%`。因此 V14b 对 ROADMAP §3.1 的通过结论仅限于 baseline 几何下的摆臂参数空间；几何 + 摆臂双维度尚未通过决策门。

## 切片 C × FSM 参数对照实验总结

| 实验 | 成功率 | 摆臂 | FSM 参数 |
|---|---:|---|---|
| V14b × 切片 C（V13.6 参数） | 3/36 = 8.3% | arm_mass=0.05 | V13.6 原参数 |
| V14b × 切片 C（V13.6.1 best） | 3/36 = 8.3% | arm_mass=0.05 | V13.6.1 best (cand 6) |
| V13.6.1 best × 切片 C（无摆臂参考） | 5/36 = 13.9% | 无 | V13.6.1 best |

V13.6.1 将 `swing_retract_tau_max` 从 `2.0` 提到 `3.0` 的增益，在 V14b 摆臂下被完全抹平：成功率仍是 `8.3%`，与 V13.6 原参数完全一致；成功域也是 V13.6.1 无摆臂成功域的严格子集。

这说明 V14b 在“几何 + 摆臂”双维度上的瓶颈是机构本身，尤其是摆臂力学，而不是 FSM phase 参数。推荐下一支进入 V14c：改摆臂机构，例如更轻、更短，或弹性挂接；不建议继续把主要精力放在 V13.6.2 / V13.7 的 FSM 参数调节上。

最终口径：V14b 通过 ROADMAP §3.1 仅限 baseline 几何下的摆臂参数空间。几何边缘的摆臂稳定性问题尚未解决。

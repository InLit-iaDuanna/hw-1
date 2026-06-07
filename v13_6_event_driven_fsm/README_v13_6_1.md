# V13.6.1 Phase 参数搜索

**状态**：受限 phase 参数搜索与跨切片证据归档已完成。

V13.6.1 延续现有 `v13_6_event_driven_fsm` 的事件驱动 FSM 控制律。它不是新的 V13.5 plan D 分支，也不恢复 phase-local 目标角。目标轨迹继续沿用 V10 的全局 smoothstep；本版本只搜索 phase-local 的力作用参数。

## 目标

V13.6 已经从 plan C 的失败中恢复了一部分：

| 控制律 | 切片 C 成功率 |
|---|---:|
| V10 baseline | 6/36 = 16.7% |
| V13.5 plan C | 0/36 = 0.0% |
| V13.6 FSM | 4/36 = 11.1% |

V13.6.1 的问题是：在保持 FSM 时序结构不变的前提下，独立调 phase 参数，能否把切片 C 成功率推回或超过 V10 水平。

## 改动内容

主脚本：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_phase_params.py
```

本轮搜索的是一个受限的第一阶段参数子集：

| 参数 | 取值 |
|---|---|
| `swing_thrust.k_E` | 4.0, 6.0, 7.5, 9.0, 11.0 |
| `swing_thrust.k_PD` | 0, 5, 10, 15, 20 |
| `swing_thrust.tau_max` | 3, 4, 5 |
| `swing_retract.tau_max` | 1.5, 2, 3 |
| `stance_late.tau_max` | 4, 5, 6 |

保持不变：

- V13.6 FSM 的 phase 定义。
- V10 全局 smoothstep hip target。
- 能量整形只在 `swing_thrust` 激活。
- knee 保持 V10 PD。
- 不修改 V10 / V13 / V13.5 / V13b / V14 / `common/`。

这不是完整的每 phase 全参数搜索。`stance_early`、`stance_late.k_PD`、`swing_retract.k_PD`、所有 `kd`、以及 `E_target` 在本轮中保持固定。

## 诊断指标

每次仿真记录：

- phase duration 占比
- `swing_thrust` 力矩积分
- `A_swing` 均值与饱和率
- 各 phase 的 hip 力矩饱和率与平均绝对力矩
- swing 能量误差均值与标准差
- touchdown 间隔均值与标准差
- failure mode
- 失败时刻左右腿 phase
- cell class：V13.6 成功格、V10-only 成功格、共同失败格

## 输出文件

| 文件 | 内容 |
|---|---|
| `out/v13_6_1_phase_param_candidates.csv` | baseline 几何下的候选 smoke 结果 |
| `out/v13_6_1_C_foot_leg.csv` | 最优候选在切片 C 上的结果 |
| `out/v13_6_1_vs_v10_planC_v136.json` | V10 / plan C / V13.6 / V13.6.1 横向对比 |
| `out/v13_6_1_C_heatmap.png` | best 候选的切片 C 6x6 热图 |
| `out/v13_6_1_geometry_stress_smoke.json` | V10 成功但 V13.6 失败的几何 stress cell |
| `out/v13_6_1_legacy_F02_metadata_smoke.json` | 旧 F(0,2) metadata-only 检查，不作为主证据 |
| `out/v13_6_1_A_slope_step.csv` | V13.6.1 best 与 V13.6 原参数的切片 A 对照 |
| `out/v13_6_1_A_summary.json` | 切片 A 汇总 |
| `out/v13_6_1_A_heatmap.png` | 切片 A 热图 |
| `out/v13_6_1_best_20s_floquet.json` | 若切片 C 达标才生成的可选 20s Floquet 报告 |

## 复现实验

默认短搜索加两个正式切片 C 候选：

```powershell
cd D:\Dunna\Documents\hw-1
$env:PYTHONIOENCODING='utf-8'
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_phase_params.py
```

默认候选列表会先放入已知 V13.6 原参数和邻域探针，再进入完整笛卡尔网格。这样默认 30 个 baseline smoke 候选不会只扫参数空间角落。

开发用 1x1 检查可以使用 `--grid 1`，但任何非 6x6 网格都会标为 `dev_smoke_not_official`，不会与 V10/V13.6 的 6x6 正式基线做比较。

完整 baseline 搜索并取前五个候选跑切片 C：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_phase_params.py --baseline-limit -1 --top-candidates 5
```

复用已有候选 CSV，只重跑切片 C：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_phase_params.py --skip-baseline --top-candidates 5
```

如果 best 候选达到至少 7/36，再运行可选 Floquet：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_phase_params.py --skip-baseline --top-candidates 5 --floquet-if-qualified
```

切片 A 扩展证据：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\scan_v13_6_1_A_slope_step.py
```

注意：脚本名保留为用户指定的 `A_slope_step`，但仓库中 V13 切片 A 的真实定义是 `A_slope_foot = slope_deg x foot_radius`。本实验按 `scan_atlas_v13.SLICES["A_slope_foot"]` 复用，不重新定义切片 A。

## 判定门

| V13.6.1 切片 C 结果 | 决策 |
|---|---|
| `>= 7/36` | 进入 20s baseline + Floquet；只有证据支持时才继续主线 |
| `5-6/36` | partial recovery；继续局部搜索或扩切片 A |
| `<= 4/36` | 不优于 V13.6；停止手工 FSM 调参，考虑 V13.7 imitation/RL |

Floquet 只在 20s run 成功、截面点数至少 16、return-map pair 足够时讨论。谱的口径是“用与 V13b 相同提取方法得到的经验 return-map spectrum”。只有当 `max|lambda| < 0.944` 时，才写“在该提取方法下收敛速度改善”；否则只能写“成功率/稳定域改变，但收敛速度未证明改善”。

旧 F(0,2) kp/kd stress 不作为主证据，因为 V13.6 的 hip 力矩来自 phase 参数，base `hip_kp/hip_kd` 只是兼容字段。主 stress 检查改为 V10 成功但 V13.6 失败的几何格：`foot_radius=0.038, leg_scale=0.90`。

V13.6.1 扫描脚本会把 MuJoCo XML 隔离写入 `out/v13_6_1_models/rolling_foot_walker.xml`，避免污染 V10 的共享模型路径。

## 跨切片证据总览

V13.6.1 的最佳候选为 candidate 6：

| 参数 | 数值 |
|---|---:|
| `swing_thrust_k_E` | 7.5 |
| `swing_thrust_k_PD` | 10.0 |
| `swing_thrust_tau_max` | 4.0 |
| `swing_retract_tau_max` | 3.0 |
| `stance_late_tau_max` | 4.0 |

跨切片结果：

| 控制律 | 切片 C 几何容差 | 切片 A 坡度扰动 |
|---|---:|---:|
| V10 PD | 16.7% (6/36) | 2.8% (1/36) |
| V13.6 FSM 原参数 | 11.1% (4/36) | 5.6% (2/36) |
| V13.6.1 best (cand 6) | 13.9% (5/36) | 11.1% (4/36) |

结构性结论：

1. V13.6.1 在切片 A 上显著优于 V10（+8.3 pp），但在切片 C 上仍低于 V10（-2.8 pp）。
2. 这是 phase-locked FSM 的典型特征：显式时序锁相对坡度/扰动天然更鲁棒，但并不能直接解决几何改变下极限环存在边界的问题。
3. FSM 路线与 V10 PD 在鲁棒性维度上互补，不是替代关系。
4. 切片 A 的成功格集中在轻微下坡区间，`slope_deg in [-1.0, -0.2]`；当 `slope_deg >= 0.2` 时成功数为 0。也就是说，在 V13 切片 A 的 +/-1 deg 微坡范围内，正坡半区仍未通过。这个结论应诚实表述为当前 V13.6.1 控制律与 V13 切片 A 范围下的限制，而不是 V13.6.1 相对 V13.6 的退步。
5. 与摆臂耦合后，V13.6.1 的增益会被抹平：在 `../v14b_state_machine_hip/out/v14b_vs_v10_v136_v1361_C.json` 中，V14b + V13.6.1 best 降到 8.3% (3/36)。这说明 V13.6.1 不能解决摆臂引入的几何边缘失稳。

推荐：面向坡度/扰动的后续升级，例如 V15 SEA 或 V17 传感器闭环，应使用 V13.6.1 best 而不是 V10 PD 作为 FSM baseline。但如果要继续 V14c 摆臂机构改进，V15 启动前应先等待 V14c 完成，避免把两个尚未解决的耦合问题叠在一起。

## 学术口径

V13.6.1 仍然是准被动控制：hip 和 knee 主动，ankle 被动。它不是纯被动行走；除非切片证据和 Floquet 证据都支持，否则也不应称为鲁棒控制器。

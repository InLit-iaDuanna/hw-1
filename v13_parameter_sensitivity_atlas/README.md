# V13 参数敏感性图集 (Parameter Sensitivity Atlas)

V13 是阶段 1（V11-V13）的收口版本，也是 ROADMAP 标注的**决策门**：完成后必须暂停回顾，判断硬件公差是否够宽再进入阶段 2。

V13 不引入新物理，**复用 V10 滚动足准被动模型**（`v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py`），只在外层套参数扫描，产出"在哪片参数区域 V10 控制律仍能稳定走 ≥10 步"的二维切片图集。

## 学术口径

- V13 继承 V10 的 hip/knee 主动稳定，**仍属准被动**，不是纯被动可行域。
- "成功"判据完全沿用 V10：仿真 ≥10 s、≥10 次交替触地、前进 ≥0.8 m、无 NaN/穿透/飞出。
- 参数图集只反映当前控制律（hip_kp/kd 等固定为基线）下的稳定盆地；换控制律图会变。

## 四张切片

| Slice | X | Y | 用途 |
|---|---|---|---|
| A | `slope_deg` ∈ [-1°, 1°] | `foot_radius` ∈ [0.030, 0.050] m | 坡度 × 足曲率 |
| B | `slope_deg` | `leg_scale` ∈ [0.90, 1.10]（thigh+shank 等比） | 坡度 × 整体腿长 |
| C | `foot_radius` | `leg_scale` | 足/腿几何比，slope=0 |
| D | `slope_deg` | `torso_ratio` = m_torso/m_hip ∈ [0.005, 0.050] | 上体质量 |
| E | `hip_kp` ∈ [15, 45] | `hip_kd` ∈ [3, 9] | 控制器增益盆地 |
| F | `hip_kp` | `hip_kd / hip_kp` ∈ [0.10, 0.30] | 验证"阻尼比带"假设（F 反例否定 E 的对角线） |

> 注：原计划 4 张切片（A–D），4×4 smoke 显示宽域成功率 ≤6%，遂改窄域 6×6；随后 E 暴露"对角线伪像"，加 F 正交验证后否定连续盆地假设。详见 [`v13_decision_gate.md`](v13_decision_gate.md)。

每点：12 s 仿真 + V12 的 `cost_of_transport` 计算。

## 运行

```powershell
cd D:\Dunna\Documents\hw-1
# 先跑 4x4 smoke（约 4 张 × 16 点 ≈ 几分钟）
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\scan_atlas_v13.py --grid 4 --duration 12

# 单独某张切片可加 --slice A_slope_foot
# 全量 6x6:
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\scan_atlas_v13.py --grid 6 --duration 12

# 后处理 + 图
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\analyze_atlas_v13.py
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\render_atlas_v13.py
```

## 步态视化（playback / MP4）

`scan_atlas_v13.py` 为节省时间不存逐时刻轨迹。要看某格步态，先 `replay_cell_v13.py` 重跑该格存 CSV，再 view 或 render：

```powershell
# 重跑 baseline 或某切片格
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\replay_cell_v13.py --baseline
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\replay_cell_v13.py --slice C_foot_leg --ix 0 --iy 0
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\replay_cell_v13.py --slice F_kp_ratio --ix 0 --iy 2

# 交互 viewer
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\view_v13.py --tag v13_baseline

# MP4
.\.venv-mujoco\Scripts\python.exe .\v13_parameter_sensitivity_atlas\render_v13.py --tag v13_baseline --label "baseline (success)"
```

已渲染的对比动画：
- `out/v13_baseline.mp4` — baseline 成功步态
- `out/v13_C_foot_leg_0_0.mp4` — stuck 案例（小足曲率 + 短腿）
- `out/v13_F_kp_ratio_0_2.mp4` — fall_down 案例（kp=15, ratio=0.18，走 6 步后倒下）

## 与上一版差异（V12 → V13）

- V12 是无新仿真的横向后处理；V13 重新跑（参数化的）V10 仿真覆盖参数空间。
- V13 的 evaluate(point) 直接复用 V10 `run_simulation`，不复制物理代码。
- common 库使用：`common/energy_metrics.cost_of_transport`。

## 决策门结论（简版）

详见 [`v13_decision_gate.md`](v13_decision_gate.md)。一句话：**不通过原 ROADMAP**——V10 hip 控制律在 (kp, kd) 平面是孤立点 + 共振线，不是连续稳定盆地（F 切片反例）。V14 之前必须插一个 V13.5 控制律重设计版本。

| 切片 | 成功率 |
|---|---:|
| A slope×foot | 1/36 (2.8%) |
| B slope×leg | 4/36 (11.1%) |
| C foot×leg | 6/36 (16.7%) |
| D slope×torso | 5/36 (13.9%) |
| E hip_kp×hip_kd | 4/36 (11.1%) |
| F hip_kp×ratio | 2/36 (5.6%) |

整体 22/216 = 10.2%。

## 已知 follow-up

- Floquet 谱重算：需要 duration ≥ 20 s（V12 留下来的 follow-up），V13 暂不做以控时间预算。
- V13b（可选）：为最佳点重跑 20 s 长程，喂给 `common/poincare.py`。

## 输出

- `out/v13_{slice}.csv`：单切片每点扁平结果
- `out/v13_{slice}_meta.json`：切片元数据（轴范围 / 网格）
- `out/v13_atlas_summary.json` + `.csv`：横向汇总
- `out/v13_atlas_report.png`：拼合热图

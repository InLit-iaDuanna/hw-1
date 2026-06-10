# V1-V24 版本索引

| 版本 | 文件夹 | 定位 | 是否纯被动 | 结论 |
|---|---|---|---|---|
| V1 | `v01_mujoco_compass_gait` | 初始 MuJoCo 指南针步态 | 否 | 接触参数敏感，作为早期探索 |
| V2 | `v02_rugged_rimless_limit_cycle` | Rimless wheel 对照 | 是 | 展示重力补能和碰撞损耗形成周期运动 |
| V3 | `v03_compass_limit_cycle` | 指南针极限环对照 | 是 | 用于解释基础极限环相图和 Poincare 点 |
| V4 | `v04_kneed_limit_cycle` | 带膝极限环对照 | 部分 | 展示带膝趋势，真实接触稳定性不足 |
| V5 | `v05_hybrid_compass_proof` | 混合动力学证明版 | 是 | 作为纯被动极限环证明的主依据 |
| V6 | `v06_mve_gait_homework` | MVE 作业表达版 | 展示层 | 将步态机制转译为最小机械结构 |
| V7 | `v07_true_contact_exploration` | 真实接触纯被动探索 | 是 | 失败和敏感性分析，不声称成功 |
| V8 | `v08_quasi_passive_assisted` | 准被动补能探索 | 否 | 弱补能探索，不能写成纯被动 |
| V9 | `v09_stable_biomimetic_gait` | 准被动稳定行走 | 否 | 真实接触下稳定连续行走 |
| V10 | `v10_rolling_foot_biomimetic_gait` | 足踝滚动仿生扩展 | 否 | 加入被动踝关节和滚动足，提升仿生表达 |
| V11 | `v11_rugged_terrain_robustness` | 地形与扰动鲁棒性 | 否 | 小幅地形成功，强扰动失败边界明确 |
| V12 | `v12_energy_cot_analysis` | 能量与 CoT 分析 | 分析层 | 横向比较能耗、碰撞损耗和 Floquet 指标 |
| V13 | `v13_parameter_sensitivity_atlas` | 参数敏感性图谱 | 分析层 | 给出设计容差、成功率和失败模式边界 |
| V13.5 | `v13_5_robust_hip_control` | hip 控制律重设计探索（**否决归档**） | 否（控制层） | 方案 A 步周期前馈与 A' 提力矩限幅均被实验否决；A' 反直觉结果（提高 τ_limit 反而全摔）+ 饱和占空比量化揭示 V10 hip 实为 bang-bang 隐式饱和脉冲驱动；确立方案 C（能量整形）为下一步路线，先做 V13b 极限环辨识再启动。详见 `v13_5_robust_hip_control/v13_5_lessons.md` |
| V13b | `v13b_floquet_long_run` | 长程极限环辨识（V12 follow-up + V13.5 方案 C 输入） | 否（分析层） | duration 20 s 取 19 次触地，4D Floquet 谱可信：max\|λ\|=0.944（V12 时 4D 退化伪值 0.89），有慢模接近单位圆边界，与 V13 窄盆地吻合；极限环能量目标 E*=52.66±0.53 J（mass=5.1 kg），为方案 C 提供能量反馈目标 |
| V13.6 | `v13_6_event_driven_fsm` | 事件驱动 FSM hip 控制律（V13.5 否决后的修正版本） | 否（准被动） | 4 段 phase（stance_early/late + swing_thrust/retract）+ 每 phase 独立 (k_E, k_PD, τ_max) 三元组，把 V10 隐式 bang-bang 解构成显式时序锁定；baseline 通过（11 td / 4.86 m / CoT 0.072）；切片 C 复扫 4/36=11.1%（vs V10 16.7%, plan C 0%）→ tier B 部分恢复，路线正确但参数未调优；成功格落在中央 (0.038-0.042, 1.0±) 而非 V10 的边角带，证明 FSM 切到了不同的邻近极限环；下一步 V13.6.1 每 phase 独立 grid search 拓宽 |
| V14 | `v14_passive_arms` | 被动摆臂版（机构维度孤立点验证） | 否（准被动） | hip 上挂双臂 hinge 无 actuator；(arm_mass × arm_length) 7×5=35 点扫描，成功 5/35=14.3% **全部集中在 arm_mass=0.001 退化行**，质量 ≥0.05 kg 即破坏 V10 控制律稳定，长度无影响——构成 V13 决策门"V10 是 (kp,kd) 孤立点解"的机构维度独立证据 |
| V14b | `v14b_state_machine_hip` | V13.6 FSM 回流被动摆臂机制 | 否（准被动） | 在 V14 被动摆臂模型上替换为 V13.6 事件驱动 FSM hip 控制律；同一 7×5 摆臂网格成功 14/35=40.0%，关键 arm_mass=0.05 kg 行从 V14 的 0/5 恢复到 5/5，判定为 pass；但 V13.6 前置切片 C 仍只有 11.1%，因此 V14b 是强机构维度恢复信号，不应夸写为已完成通用鲁棒控制 |
| V14c | `v14c_arm_mass_lightening` | arm_mass 减重扫描（验证 V15 解封） | 否（准被动） | V13.6.1 best FSM + 摆臂模型；arm_mass∈{0.01,0.02,0.03,0.05} × 切片 C 6×6 = 144 格；m=0.05 重现 3/36（health_check_passed），m=0.01 升至 5/36 且为 V13.6.1 无摆臂 5 格的**严格子集**；成功率随 arm_mass 单调下降（5→4→4→3）；判定 arm_mass 为根因，V15 hip SEA 解封 |
| V16 | `v16_motor_dynamics` | L1 一阶电机动力学（J_rotor / 摩擦 / 电流饱和）| 否（准被动 + 真实电机）| V14c fork 不依赖 V15；ideal preset 严格还原 V14c (0.0000% 偏差)；mx64ar_full 失败 (forward 0.19 m vs V14c 4.62 m)；τ_C 单因素扫描在固定 mx64 J/b/τ_sat 下**非单调**：成功带 {0, 0.034, ≥0.27} N·m，失败带 [0.013, 0.20] N·m；MX-64 spec τ_C_eff=0.20 落入失败带正中央；ε∈[0.001,0.05] 50× 范围 verdict 不变（物理共振非数值伪影）。primary_verdict=motor_dynamics_breaks_fsm_revisit_control，sub_finding=tau_C_FSM_resonant_coupling_non_monotonic |
| V15.1 | `v15_1_sea_direct` | SEA direct-drive（motor body + series spring，无内环）| 否（准被动 + SEA）| Fork V15.2 拓扑修复两处 bug：(1) `_FsmDataView` 改为喂绝对角度 q_motor+q_link，(2) 去掉 Pratt 内环改为直传。退化测试 k=10000 forward=4.87 m（V14c 4.62 m，5.6% 偏差通过）。切片 C：k=5000 5/36=13.9%=V14c，k=10000 同样 5/36。**k=500 在 best cell 给出 forward=4.92 m（最优）且 spring deflection 1.6 deg**；k=1000 存在共振失败带（类似 V16 τ_C 非单调现象）。primary_verdict=v151_sea_direct_preserves_v14c_stability |
| V13.7 | `v13_7_friction_compensation` | 前馈摩擦补偿 | 否（准被动 + 补偿）| FSM 输出端加 τ_comp = τ_C_eff·sign_smooth(ω_joint) 前馈补偿；mx64ar_full smoke PASS（forward 4.63m, alt_td 10, CoT_mech=0.066）；τ_C 扫描 10/10 全通过，V16 失败带全部修复；verdict=friction_compensation_full_recovery；V17 状态估计启动条件具备 |
| V17 | `v17_state_estimation` | 传感器闭环状态估计 | 否（准被动 + 估计）| 编码器量化(4096 CPR)+Kalman速度滤波+FK hip估计+接触延迟模型；noise_scale=1.0 PASS（fwd 4.67m, alt_td 10, rmse_vx=0.079）；critical noise_scale=3.0；verdict=mx64ar_within_tolerance；阶段 2 (V14-V17) 主线已闭环 |
| V18 | `v18_3d_lateral_stability` | 3D 侧向被动稳定探索 | 探索层（**否定结果**）| roll_k<200 发散，roll_k≥500 等效2D；宽足(0.15m)无效；verdict=lateral_stability_requires_active_control；V21 决策门提前触发 |
| V19 | `v19_hip_abduction_active` | 髋外展主动稳定 | 否（**否定结果**）| 最佳 7 alt/2.97s（目标 10 alt 未达标）；漂移率 5-10× 超过修正能力；verdict=hip_abd_insufficient_for_lateral_stabilization；物理限制：abd 扭矩无法产生侧向 GRF |
| V20 | `v20_step_width_control` | 步宽控制探索 | 否（**未完成**）| 完成基础架构（3D IK + 轨迹规划器），但控制律集成未完成；Smoke Test 失败（0 alt）；verdict=step_width_control_not_verified；综合 V18/V19/V20 否定结果建议跳过 V21 直接进入 V22 硬件设计 |
| V21 | `v21_3d_perturbation_robustness` | 3D 扰动鲁棒性 | **跳过** | 综合 V18/V19/V20 否定结果，直接进入 V22 硬件设计（基于 2D 主线 V13.7+V17）；3D 行走作为未来工作 |
| V22 | `v22_hardware_design` | 硬件设计 v1 | 设计文档 | 基于 V13.7+V17 的 2D 样机设计文档，包含 HARDWARE_SPEC.md、BOM.md（6500-8000元）、CAD_NOTES.md、SIMULATION_MAPPING.md；verdict=design_ready_for_manufacturing |
| V23 | `v23_system_identification` | 系统辨识 | 方法论文档 | 从硬件数据反推物理参数：摩擦系数、转动惯量、弹簧刚度辨识流程；辨识误差目标 <10% |
| V24 | `v24_sim_to_real` | Sim-to-real 迁移策略 | 策略文档 | 域随机化策略（质量±10%、腿长±5%、摩擦1.0-1.6、弹簧刚度±20%、电机延迟0-15ms）；鲁棒控制器设计；首次上机策略；目标随机化环境成功率 >50% |
| **Residual RL V2** | `rl_training/` | PPO on V13.7 强化学习优化 | 否（RL优化层）| **训练完成（2026-06-09）**：Zero residual identity验证通过（baseline 4.630m/10td），Sweep找到最优方向 action=[0.50,1.00] residual=[0.100,0.200]Nm（forward 4.973m，+7.4%），100k PPO sanity训练达到 4.898m（+5.8%），成功率100%。产物：`logs/residual_rl_v2/`, `models/residual_rl_v2_sanity/` |

## 版本依赖树

主线演化路径：

```
V10 (PD baseline, 足踝滚动)
├─ V13 (参数图谱) → V13.5 (三方案否决) → V13.6 (事件驱动 FSM)
│  └─ V13.6.1 (phase 参数精调, 5/36 成功)
│     ├─ V13.7 (前馈摩擦补偿) → V17 (状态估计) → **V22 硬件设计** → V23 系统辨识 → V24 Sim-to-real → V25 实地行走
│     └─ V13b (Floquet 长程辨识)
│
├─ V14 (被动摆臂, 5/35 成功) → V14b (FSM+摆臂, 14/35 成功)
│  └─ V14c (arm_mass 减重扫描, 确认根因)
│     ├─ V16 (L1 电机动力学, 发现 τ_C 共振) → V13.7 (摩擦补偿修复)
│     └─ V15 分支
│        ├─ V15.0 (PEA 失败, 未入表)
│        ├─ V15.1 (SEA direct-drive, k=500 最优) → V15.1L1 (SEA+L1电机, 部分缓冲)
│        └─ V15.2 (Pratt 内环失败, 未入表)
│
└─ 3D 探索分支 (全否定)
   ├─ V18 (侧向被动稳定探索) → verdict: lateral_stability_requires_active_control
   ├─ V19 (髋外展主动稳定) → verdict: hip_abd_insufficient (5-10× 不足)
   └─ V20 (步宽控制探索) → verdict: step_width_control_not_verified (架构完成但未集成)
      └─ **决策**: 跳过 V21，直接进入 V22 硬件设计 (基于 2D 主线)

设计文档分支 (V22-V24):
V22 (硬件设计) → V23 (系统辨识方法论) → V24 (Sim-to-real 策略) → V25 (实地行走, 待硬件完成)
```

**关键节点**：
- V5: 纯被动极限环证明
- V10: 准被动基线 + 足踝滚动
- V13.6/V13.6.1: 事件驱动 FSM 控制律
- V13.7: 前馈摩擦补偿 (修复 V16 电机动力学问题)
- V14c: 摆臂减重扫描 (确认 arm_mass 为根因)
- V17: 状态估计闭环 (阶段 2 主线完成)
- V18-V20: 3D 化三次否定结果
- V22-V24: 硬件设计文档链

## 2026-05-28 Milestone 追加

- **V13.6.1（2026-05-28）**：phase 参数搜索 best cand 6（仅 `swing_retract_tau_max` 2.0→3.0，其余 `swing_thrust_k_E=7.5, swing_thrust_k_PD=10.0, swing_thrust_tau_max=4.0, stance_late_tau_max=4.0`），切片 C 5/36=13.9%（vs V13.6 +2.8 pp，vs V10 -2.8 pp），切片 A 4/36=11.1%（vs V13.6 +5.6 pp，vs V10 +8.3 pp）。verdict=partial_recovery_continue_search。准被动控制（hip+knee 主动 FSM）。XML 已隔离到 `v13_6_event_driven_fsm/out/v13_6_1_models/`，不污染 V10/V13.6 共享 XML。产物：`v13_6_event_driven_fsm/out/v13_6_1_*`。
- **V14b（2026-05-28）**：FSM hip + 被动摆臂。摆臂参数空间 (arm_mass × arm_length) 14/35=40%，关键行 arm_mass=0.05 从 V14 0/5 跃升到 5/5，通过 §3.1 摆臂参数维度。准被动控制。产物：`v14b_state_machine_hip/`。
- **V14b × 切片 C（2026-05-28）**：用 V13.6 原参数 3/36=8.3%；用 V13.6.1 best 仍 3/36=8.3%（成功域是 V13.6.1 无摆臂域的严格子集）。结论：V13.6.1 增益与摆臂耦合后归零，几何 + 摆臂双维度未过 §3.1。产物：`v14b_state_machine_hip/out/v14b_C_*`。
- **V14c（2026-05-28）**：FSM hip + 被动摆臂 + arm_mass 减重扫描。健康检查 m=0.05 重现 3/36 与 V14b 完全一致（health_check_passed）；m=0.01 升至 5/36 且为 V13.6.1 best 无摆臂域 5 格的严格子集（is_subset=true，contains_reference=true）；成功率随 arm_mass 单调下降。primary_verdict=arm_mass_is_root_cause_v15_unblocked。准被动控制。XML 隔离到 `v14c_arm_mass_lightening/out/v14c_models/`，不污染 V10/V14/V14b 模型。产物：`v14c_arm_mass_lightening/out/v14c_*`。

## 2026-05-30 Milestone 追加

- **V16（2026-05-30）**：L1 一阶电机动力学 fork V14c（不依赖 V15，与 V15 并行解耦）。`common/motor_dynamics.py` 提供 MotorParams + L1MotorActuator + PRESETS（mx64ar / ec_i40_53 / ideal）。粘滞摩擦 b·N² 与转子惯量 J_rotor·N² 折到 XML <joint damping/armature>，Python 端只做电流饱和 + 库仑摩擦带 sign_smooth。**L0 退化对照严格通过**：ideal preset alt_td=10/forward=4.617/mech=16.236 与 V14c baseline 完全相等（0.0000%）。**L1 健康检查失败**：mx64ar_full smoke alt_td=4/forward=0.19/fall_down，偏差 96%。**τ_C 单因素扫描非单调**：固定 mx64 J/b/τ_sat 仅扫 τ_C_motor∈{0,…,3.0e-3} N·m，成功带为 τ_C_eff∈{0, 0.034, ≥0.27} N·m，失败带 [0.013, 0.20] N·m。sign_smooth ε∈{0.001, 0.01, 0.05} 50× 范围内 verdict 不变 → 物理共振非数值伪影。**MX-64AR spec τ_C_eff=0.20 落入失败带正中央**。primary_verdict=motor_dynamics_breaks_fsm_revisit_control，sub_finding=tau_C_FSM_resonant_coupling_non_monotonic。V22 选型约束三选一：(a) τ_C_eff<0.013 低摩擦关节，(b) V13.7 摩擦补偿，(c) 选恢复带 ≥0.27 的电机。XML 隔离到 `v16_motor_dynamics/out/v16_models/`。产物：`v16_motor_dynamics/out/{smoke_v16_table.json, scan_v16_tauC_critical.json, v16_verdict.json, v16_smoke_*}`。

## 2026-06-02 Milestone 追加

- **V15.1（2026-06-02）**：SEA direct-drive fork V15.2 拓扑（motor_rotor body + series hinge spring），修复两处 bug：(1) `_FsmDataView.refresh()` 喂绝对角度 (q_motor+q_link) 而非 V15.2 的相对 q_link（后者仅 0.05 deg，FSM 几乎看不到 hip 运动），(2) 去掉 Pratt 内环（Kp=1000, ctrl_limit=30）改为 FSM 扭矩直传 motor joint（ctrl_limit=4 N·m 与 V14c 一致）。**退化测试 k=10000**：success=true, alt_td=11, forward=4.87 m（vs V14c 4.62 m，+5.6%）。**切片 C 6×6 全扫**：k=5000/10000 均 5/36=13.9% 精确复现 V14c；k=1000 4/36=11.1%；k=500 3/36=8.3%。**Best cell (foot=0.042, leg=1.02) 非单调**：k=500 forward=4.92 m（最优，spring deflection 1.6 deg），k=1000 反而 fall_down（类似 V16 τ_C 共振带）。Rotor params: mass=0.01 kg, Iyy=0.004 kg·m², bearing_damp=0.001。primary_verdict=v151_sea_direct_preserves_v14c_stability。产物：`v15_1_sea_direct/out/{smoke_v151_table.json, v151_C_k_geom.csv, v151_scan_status.json, v151_verdict.json}`。
- **V13.7（2026-06-02）**：前馈摩擦补偿 fork V14c + V16 电机动力学。FSM 输出端加 `τ_comp = τ_C_eff·sign_smooth(ω_joint, ε=0.01)` 前馈项精确对消 V16 库仑摩擦扣减。**mx64ar_full smoke PASS**：forward=4.63 m / alt_td=10 / CoT_mech=0.066（vs V16 无补偿 0.19 m/4 td → 完全恢复）。**τ_C 全网格验证**：τ_C_eff∈{0, 0.013, 0.034, 0.10, 0.20, 0.27, 0.68, 1.7, 3.0} × {raw, compensated} = 18 格，补偿版 10/10 全通过（V16 失败带 6 点全部修复）。**ec_i40 也全通过**（τ_C_eff=0.10）。primary_verdict=friction_compensation_full_recovery；V16 升级为 motor_dynamics_compatible_with_friction_compensation；**V17 状态估计启动条件具备**。产物：`v13_7_friction_compensation/out/{smoke_v137_table.json, scan_v137_comp_matrix.json, v137_verdict.json, v137_smoke_mx64ar_full_*.mp4}`。
- **V17（2026-06-02）**：传感器闭环状态估计 fork V13.7 摩擦补偿控制律。编码器量化（4096 CPR）+ Kalman 速度滤波 + FK hip 位置估计 + 确定性接触延迟模型（sensor_lag=0.005 s）。**noise_scale=1.0 (MX-64AR 真实规格) PASS**：forward=4.67 m / alt_td=10 / rmse_vx=0.079 m/s / rmse_hip_x=0.045 m（vs V13.7 真值反馈 4.63 m/10 td，+0.9% 几乎无偏差）。**噪声容限 critical=3.0×**（safety margin 3×，sensor_lag=0.015 s 触发失败）。失败机制：接触延迟 ≥15 ms 打破 FSM 时序导致 phase 混乱跌倒。primary_verdict=mx64ar_within_tolerance。**V22 硬件传感选型约束**：接触开关延迟 <15 ms，编码器分辨率 ≥1024 CPR（4096 best）。**阶段 2 (2D 机械升级 V14-V17) 主线已闭环**。产物：`v17_state_estimation/out/{smoke_v17_table.json, scan_v17_noise.json, v17_verdict.json, v17_noise1_*.mp4}`。
- **V18（2026-06-02）**：3D 侧向被动稳定探索。V10 PD 基础上加 hip_y/hip_roll/hip_abd 侧向自由度（hip_abd 被动弹簧）。**被动侧向稳定不存在**：roll_k<200 N·m/rad → 3° 扰动即发散导致矢状面跌倒；roll_k≥500 等效刚性 2D 约束（无意义）；宽足实验（0.15 m）仅微降 roll 峰值（6.3°→4.4°），不改变结论。primary_verdict=lateral_stability_requires_active_control。**V21 决策门提前触发**：3D 纯被动不收敛 → 确认"矢状面被动 + 冠状面主动"路线，V19 引入最小侧向主动稳定。产物：`v18_3d_lateral_stability/out/{v18_passive_scan.json, v18_verdict.json}`。
- **V19（2026-06-03）**：髋外展主动稳定验证。V18 模型基础上 abd 关节改为电机驱动。测试 6 种控制策略（简单 PD、hip_y 反馈、hip_roll 反馈、联合反馈、向摇摆侧前倾、参数网格）。**最佳结果 7 alternations/2.97 s**（目标 10 alt/12 s 未达标）。根因：侧向漂移率 ~0.05-0.10 m/step，abd 扭矩修正能力 <0.01 m/step（5-10× 不足）。物理限制：abd 关节扭矩产生躯干倾斜但无法产生 net 侧向 GRF（需要脚底位移）。primary_verdict=hip_abd_insufficient_for_lateral_stabilization。**V21 决策门再次确认**：单一髋外展执行器无法稳定 3D 行走 → V20 需引入步宽控制（swing foot 侧向位置规划）。产物：`v19_hip_abduction_active/out/{v19_scan.json, v19_verdict.json}`。
- **V13.6.1（2026-05-28）**：Phase 参数精细调优（**隐藏版本**，文件混在 v13_6 目录中）。在 V13.6 FSM 基础上，独立搜索每个 phase 的力作用参数（swing_thrust.k_E ∈ [4.0, 11.0]、k_PD/tau_max 网格）。目标：恢复或超过 V10 在切片 C 的成功率（16.7%）。实测结果：找到多个候选配置，最佳候选在切片 C 达到 **5/36 = 13.9%**（与 V14c 无摆臂域一致）。V13.6.1 best 域成为 V14b/V14c 的重要对照基线（"V13.6.1 best 无摆臂域"）。文档完整但未独立成版本。产物：`v13_6_event_driven_fsm/{README_v13_6_1.md, out/v13_6_1_*.csv/json/png}`。
- **V15.2（2026-05-30）**：Strict SEA with Pratt 内环（**失败，被 V15.1 替代**）。测试 Pratt 内环位置控制（Kp=1000, motor_limit=30 N·m），但 FSM 输入错误（喂 q_link 相对角度 ~0.05° 而非绝对角度）导致 FSM 误判，且内环与 FSM 冲突。V15.1 修正后成功。教训：SEA 适用扭矩控制模式，不适用 Pratt 内环 + FSM 事件驱动控制器。产物：`v15_2_strict_sea/{README.md, simulate_v152.py}`。
- **V17（2026-06-02）**：传感器闭环状态估计。V13.7 摩擦补偿 FSM + 传感器噪声（编码器量化 4096 CPR、速度高斯噪声、接触延迟 5 ms）+ Kalman 滤波。**验证通过**：noise_scale=1.0（MX-64AR 真实规格）下 success=true, forward=4.67 m, alt_td=10, estimation_rmse_vx=0.079 m/s, rmse_hip_x=0.045 m。噪声容限：2× 安全裕度通过，3× 临界失败。**硬件约束确定**：编码器 ≥4096 CPR、接触延迟 <15 ms（超过会破坏 FSM 时序）。verdict=mx64ar_within_tolerance。**阶段 2（V14-V17）主线闭环**，为 V22 硬件设计提供传感器规格。产物：`v17_state_estimation/{README.md, out/v17_mx64ar_noise1_*.json/mp4/csv, scan_v17_noise.json}`。
- **V18（2026-06-02）**：3D 侧向被动稳定探索（**否定结果**）。V10 矢状面 PD + 3D 自由度（hip_y, hip_roll, hip_abd）+ 被动侧向弹性。测试 roll_k ∈ [0, 1000] N·m/rad + 初始扰动 3° roll + 宽足实验（foot_width 0.04→0.15 m）。**核心发现**：被动侧向稳定不存在。roll_k<200 发散失败，roll_k≥500 勉强通过但等效 2D 刚性约束（侧向自由度被消除）。宽足仅微降 roll 峰值（6.3°→4.4°）但仍失败。失败机制：侧向振荡→耦合矢状面→破坏极限环→跌倒。物理解释：冠状面无重力势能驱动，纯耗散系统无稳定极限环。verdict=lateral_stability_requires_active_control。**V21 决策门提前触发**：3D 化必须引入主动侧向控制→V19。产物：`v18_3d_lateral_stability/{README.md, model_3d.py, out/v18_verdict.json}`。
- **V19（2026-06-03）**：髋外展主动稳定（**否定结果**）。V18 模型基础上将 hip_abd 从被动改为主动电机（6 DOF 控制：左右 hip/knee/abd）。测试 6 种控制策略（简单 PD、hip_y 反馈、hip_roll 反馈、联合反馈、双侧对称、向摆动侧倾）。**最佳结果**：7 alternations / 2.97s（目标 10 alt/12s 未达标）。**核心发现**：髋外展修正能力不足 5-10×。侧向漂移率 ~0.05-0.10 m/step，abd 扭矩修正 <0.01 m/step。物理限制：abd 扭矩→躯干倾斜，但无法产生 net 侧向 GRF（需要脚底位移）。verdict=hip_abd_insufficient_for_lateral_stabilization。**V21 决策门再次确认**：单一髋外展无法稳定 3D 行走→V20 需引入步宽控制（swing foot lateral placement）。产物：`v19_hip_abduction_active/{README.md, model_3d_v19.py, out/v19_verdict.json}`。
- **V22（2026-06-04）**：硬件设计 v1（**设计文档完成**）。基于 V13.7（摩擦补偿 FSM）+ V17（状态估计）的 2D 矢状面准被动行走机器人完整设计文档。包含：HARDWARE_SPEC.md（机械结构、电机选型 Dynamixel MX-64AR×4、传感器 4096 CPR 编码器、控制系统 Raspberry Pi 4B、2D 导轨约束）、BOM.md（物料清单 6500-8000 元、采购优先级、供应商信息）、CAD_NOTES.md（部件设计、装配关系、加工工艺、质量属性验证）、SIMULATION_MAPPING.md（仿真参数→硬件参数映射、校准流程、偏差记录表）。总质量 5.0-6.0 kg，腿长 1.00 m，关键参数与仿真偏差 <5%。verdict=design_ready_for_manufacturing。为 V25 实地行走奠定硬件基础。产物：`v22_hardware_design/{HARDWARE_SPEC.md, BOM.md, CAD_NOTES.md, SIMULATION_MAPPING.md, README.md}`。
- **V23（2026-06-04）**：系统辨识（**方法论文档**）。从硬件测试数据反推物理参数的方法论。包含：摩擦系数辨识（最小二乘法，恒速转动实验）、转动惯量辨识（自由摆动法）、弹簧刚度辨识（静态加载法）。实验流程、数据采集要求、参数修正工作流（辨识→更新仿真→验证→误差<10%通过）。硬件到手后可直接应用，用于修正仿真模型或调整控制器。产物：`v23_system_identification/README.md`。
- **V24（2026-06-04）**：Sim-to-real 迁移策略（**策略文档**）。域随机化和控制迁移设计。Sim-to-real gap 分析（接触模型、摩擦、电机延迟、传感器噪声差异，V16/V17 已建模电机摩擦和传感器噪声）。域随机化策略：质量 ±10%、腿长 ±5%、摩擦系数 1.0-1.6、弹簧刚度 ±20%、电机延迟 0-15ms、地面刚度 0.5-2.0×，生成 100 组配置，目标成功率 >50%。鲁棒控制器设计（自适应增益、参数调度）。首次上机策略（保守参数 70%、人工辅助、渐进式测试、安全监控）。为 V25 实地行走降低首次失败风险。产物：`v24_sim_to_real/README.md`。

## 推荐答辩主线

1. V5 证明被动动态极限环存在。
2. V6 将机制转译为 MVE 机械单元。
3. V10 展示带踝和滚动足的仿生步态结构。
4. V11 说明地形和扰动鲁棒性边界。
5. V12/V13 作为能量效率和参数容差附录。

## 关键输出

| 类型 | 路径 |
|---|---|
| 纯被动证明 | `v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png` |
| MVE 结构表达 | `v06_mve_gait_homework/out/v6_mve_report.png` |
| 足踝滚动动画 | `v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk.mp4` |
| 鲁棒性报告 | `v11_rugged_terrain_robustness/out/v11_robustness_report.png` |
| 能量报告 | `v12_energy_cot_analysis/out/v12_report.png` |
| 参数图谱 | `v13_parameter_sensitivity_atlas/out/v13_atlas_report.png` |
| MATLAB 汇总 | `matlab-v01-v13-gait/out/v01_v13_matlab_summary.csv` |

## 表述边界

“纯被动”只用于 V5 的混合动力学证明和 V2/V3 的理论对照。V8-V11 都包含主动补能或主动稳定，应该写成“准被动仿生步态”或“真实接触工程扩展”。V12/V13 是分析结果，不是新的物理模型。

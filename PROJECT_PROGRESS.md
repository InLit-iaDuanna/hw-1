# 项目进度总览

| 版本 | 定位 | 纯被动 | 动画 | MATLAB | 答辩用途 |
|---|---|---:|---:|---:|---|
| V1 | 初始 MuJoCo 指南针步态 | 否 | 有 | 有 | 早期探索 |
| V2 | Rimless wheel 对照 | 是 | 有 | 有 | 解释重力补能和碰撞损耗 |
| V3 | 指南针极限环对照 | 是 | 有 | 有 | 解释极限环相图 |
| V4 | 带膝极限环对照 | 部分 | 有 | 有 | 带膝趋势对照 |
| V5 | 混合动力学证明版 | 是 | 有 | 有 | 纯被动极限环证明主证据 |
| V6 | MVE 作业表达版 | 展示层 | 有 | 有 | 机械转译和 PPT 主图 |
| V7 | 真实接触纯被动探索 | 是 | 有 | 有 | 失败和敏感性分析 |
| V8 | 准被动补能探索 | 否 | 有 | 有 | 生物式补能讨论 |
| V9 | 准被动稳定行走 | 否 | 有 | 有 | 真实接触稳定行走 |
| V10 | 足踝滚动仿生步态 | 否 | 有 | 有 | 最推荐展示动画和机构升级 |
| V11 | 地形与扰动鲁棒性 | 否 | 可视化脚本 | 有 | 稳定边界和失败样本 |
| V12 | 能量与 CoT 分析 | 分析层 | 无 | 有 | 能耗、效率和 Floquet 附录 |
| V13 | 参数敏感性图谱 | 分析层 | 无 | 有 | 设计容差和参数边界 |
| V13.6 | 事件驱动 FSM hip 控制律 | 否 | 有 (mp4 + phase 报告) | 暂不汇总 | 把 V10 隐式 bang-bang 解构成 4 phase 显式时序；切片 C 4/36=11.1%（V10 16.7%, plan C 0%），tier B 部分恢复 |
| V14 | 被动摆臂（机构孤立点验证） | 否 | 无 | 暂不汇总 | 决策门 §3.1 机构维度证据：V10 控制律下摆臂质量 ≥0.05 kg 即破坏稳定 |
| V14b | V13.6 FSM 回流被动摆臂 | 否 | 有 (critical mp4 + heatmap) | 暂不汇总 | V13.6 FSM 在 V14 摆臂网格中恢复 14/35=40.0%，关键 0.05 kg 行 5/5 通过；仍属探索性准被动结果 |
| V14c | arm_mass 减重扫描 | 否 | 待补 mp4 | 暂不汇总 | 144 格扫描；m=0.05 重现 3/36（health_check_passed），m=0.01 升至 5/36 且 ⊂ V13.6.1 无摆臂域；arm_mass 为根因，V15 hip SEA 解封 |
| V16 | L1 motor dynamics | 否 | 有 (ideal + mx64ar_full mp4) | 暂不汇总 | fork V14c 不依赖 V15；ideal 退化对照严格还原 V14c；mx64ar_full 失败；τ_C 扫描非单调（成功带 {0, 0.034, ≥0.27}，失败带 [0.013, 0.20]）；MX-64 spec τ_C=0.20 落入失败带正中央；verdict=motor_dynamics_breaks_fsm_revisit_control + tau_C_FSM_resonant_coupling_non_monotonic |
| V15.1 | SEA direct-drive（motor body + series spring） | 否 | 有 (k500 + k10000 mp4) | 暂不汇总 | Fork V15.2 修复 _FsmDataView（喂绝对角度）+ 去掉内环（直传 4 N·m）；k=10000/5000 切片 C 5/36=13.9% 精确复现 V14c；best cell k=500 forward=4.92m 优于 V14c（spring defl 1.6 deg）；k=1000 共振失败带；verdict=v151_sea_direct_preserves_v14c_stability |
| V15.1L1 | SEA + L1 电机动力学 | 否 | 无 | 暂不汇总 | V15.1 + V16 合体实验。mx64ar_raw k=500 fwd=3.96m/9td（V16 rigid 0.19m → 20× 改善但未达标）；mx64ar+comp k=500 fwd=4.90m PASS；k=10000+comp 失败（刚性弹簧 + J_eff 耦合不稳定）。verdict=sea_partial_buffering_compensation_still_needed；推荐配置 k=500+V13.7 |
| V13.7 | 前馈摩擦补偿 | 否 | 有 (mp4 × 3 + preview) | 暂不汇总 | FSM 输出端加 τ_C_eff·sign_smooth(ω_joint) 前馈补偿；mx64ar_full smoke PASS（forward 4.63m, alt_td 10, CoT_mech=0.066）；补偿 vs 不补偿对照 mp4；ec_i40 也全通过；verdict=friction_compensation_full_recovery；V16 升级为 motor_dynamics_compatible_with_friction_compensation；V17 状态估计启动条件具备 |
| V17 | 传感器闭环状态估计 | 否 | 有 (noise1 mp4) | 暂不汇总 | 编码器量化(4096 CPR)+Kalman速度滤波+FK hip估计+接触延迟模型；noise_scale=1.0 PASS（fwd 4.67m, alt_td 10, rmse_vx=0.079, rmse_hip_x=0.045m）；critical noise_scale=3.0（safety margin 3×）；verdict=mx64ar_within_tolerance；V22 硬件传感选型约束：接触开关延迟 <15ms |
| V18 | 3D 侧向被动稳定探索 | 探索层 | 无 | 暂不汇总 | V10 PD 基础上加 hip_y/hip_roll/hip_abd 侧向自由度；被动侧向稳定**不存在**：roll_k<200 → 3°扰动即发散导致矢状面跌倒；roll_k≥500 等效刚性约束（=2D）；宽足(0.15m)仅微降 roll 峰值（6.3°→4.4°），不改变结论；verdict=lateral_stability_requires_active_control；V19 必须引入主动髋外展 |
| V19 | 髋外展主动稳定 | 否 | 无 | 暂不汇总 | V18 模型基础上 abd 关节改为电机驱动；测试策略：简单 PD、hip_y 反馈、hip_roll 反馈、联合反馈、向摇摆侧前倾；最佳结果 7 alternations/2.97s（目标 10 alt/12s 未达标）；根因：侧向漂移速率 ~0.05-0.10 m/step，abd 扭矩修正能力 <0.01 m/step（5-10× 不足）；物理限制：abd 扭矩产生躯干倾倒但无法产生 net 侧向 GRF（需脚底位移）；verdict=hip_abd_insufficient_for_lateral_stabilization；V20 需引入步宽控制 |
| V20 | 步宽控制探索 | 否 | 无 | 暂不汇总 | V19 基础上尝试 LIPM 步宽规划（主动落脚点调节）；完成基础架构（3D IK + 轨迹规划器 + 仿真框架），但控制律集成未完成；Smoke Test 失败（~1s 后跌倒，0 alternations）；根因：控制复杂度低估 + V19 基线本身不稳定；verdict=step_width_control_not_verified；综合 V18/V19/V20 否定结果，建议跳过 V21，直接进入 V22 硬件设计（基于 2D 主线 V13.7+V17） |

## 当前最强证据链

1. V5：证明纯被动极限环机制存在。
2. V6：把机制转译为最小 MVE 机械结构。
3. V10：用带踝滚动足展示更接近生物步态的准被动行走。
4. V11：说明在小幅地形下可保持稳定，强扰动下存在明确失败边界。
5. V12：解释能量输入、CoT、碰撞损耗和收敛指标。
6. V13：说明哪些参数区间可行，哪些参数导致跌倒或卡住。

## 下一步建议

V14 决策门已通过：V14c 健康检查 m=0.05 与 V14b 重现一致（3/36），primary_verdict 确认 arm_mass 为根因，monotonicity 满足，m=0.01 为 V13.6.1 无摆臂域的严格子集。V15 hip SEA 由另一窗口推进（V15.0 PEA 已实测打破 V14c FSM，V15.1 spatial tendon / V15.2 motor body 待做）。

**V16 实测（2026-05-30）揭示新约束**：V13.6.1 FSM 在真实电机库仑摩擦下崩溃，τ_C 与 FSM 形成耦合共振（非单调），MX-64AR spec 落入失败带。

**V13.7 实测（2026-06-02）通过**：前馈摩擦补偿 `τ_comp = τ_C_eff·sign_smooth(ω_joint)` 在 FSM 输出端精确对消电机库仑摩擦。mx64ar_full smoke forward=4.63m / alt_td=10（V16 同配置 0.19m/4 → 完全恢复）。τ_C 扫描 10/10 全通过，V16 失败带 6 点全部修复。verdict=motor_dynamics_compatible_with_friction_compensation。

**V17 实测（2026-06-02）通过**：传感器噪声 + 状态估计闭环验证。编码器 4096 CPR 量化 + Kalman 速度滤波 + FK hip 估计 + 确定性接触延迟模型。noise_scale=1.0 (MX-64AR 真实规格) PASS（fwd 4.67m, alt_td 10）。噪声容限 critical=3.0×（safety margin 3×）。失败机制：接触延迟 ≥15ms 打破 FSM 时序。verdict=mx64ar_within_tolerance。**阶段 2 (2D 机械升级 V14-V17) 主线已闭环**。

**V18 实测（2026-06-03）否定结果**：3D 侧向被动稳定探索。roll_k<200 → 躯干滚转发散；roll_k≥500 等效 2D 刚性约束。宽足实验（0.15m）无法改变结论。verdict=lateral_stability_requires_active_control。**确认：矢状面可被动，冠状面需主动**。

**V20 实测（2026-06-03）否定结果**：步宽控制探索。完成基础架构（`model_3d_v20.py` 3D 模型 + `step_width_planner.py` LIPM 规划器 + `simulate_v20.py` 仿真框架），但控制律集成未完成。Smoke Test（k_p=k_d=0 开环）失败：forward 0.94m / sim_time 1.09s / alternations 0 / failure=fall_down。根因：(1) 控制复杂度低估（3D IK + 轨迹规划 + 时序同步），(2) V19 基线本身不稳定（~7 alternations 就失败），难以在其基础上改进。verdict=step_width_control_not_verified。**V21 决策门提前触发**：综合 V18（被动不存在）+ V19（髋外展不足）+ V20（步宽控制未验证）三次否定结果，**建议跳过 V21，直接进入 V22 硬件设计**（基于 2D 主线 V13.7+V17）。3D 行走作为未来工作，在硬件平台上用实测数据驱动算法设计。

**V22 完成（2026-06-04）设计文档**：硬件设计 v1。基于 V13.7（摩擦补偿 FSM）+ V17（状态估计）的 2D 矢状面准被动行走机器人完整设计文档。包含：HARDWARE_SPEC.md（机械结构、电机选型 Dynamixel MX-64AR×4、传感器配置、控制系统 Raspberry Pi 4B）、BOM.md（物料清单 6500-8000 元）、CAD_NOTES.md（部件设计、装配、加工工艺）、SIMULATION_MAPPING.md（仿真参数→硬件参数映射、校准流程）。设计原则：仿真一致性优先、可制造性、可调试性、安全性。2D 约束采用侧向导轨方案。关键参数与仿真偏差 <5%。verdict=design_ready_for_manufacturing。为 V25 实地行走奠定硬件基础。

**V23 完成（2026-06-04）方法论文档**：系统辨识。提供从硬件测试数据反推物理参数的方法论文档。包含：摩擦系数辨识（最小二乘法）、转动惯量辨识（自由摆动法）、弹簧刚度辨识（静态加载法）。实验流程、数据采集要求、参数修正工作流。目标：辨识误差 <10%。硬件到手后可直接应用，用于修正仿真模型或调整控制器参数。

**V24 完成（2026-06-04）策略文档**：Sim-to-real 迁移策略。提供域随机化和控制迁移设计文档。Sim-to-real gap 分析（接触模型、摩擦、电机延迟、传感器噪声差异）。域随机化策略：质量 ±10%、腿长 ±5%、摩擦系数 1.0-1.6、弹簧刚度 ±20%、电机延迟 0-15ms。鲁棒控制器设计（自适应增益、参数调度）。首次上机策略（保守参数、人工辅助、渐进式测试）。目标：随机化环境成功率 >50%。为 V25 实地行走降低首次失败风险。

下一步选项：
- **V25 实地行走**：等待 V22 硬件制作完成后，进行真实地面行走测试（需 2-3 个月制作周期）
- **深度分析**：V18/V19/V20 否定结果的学术价值分析（被动/主动侧向稳定的理论边界）
- **仿真优化**：基于 V22-V24 的设计反馈，改进仿真模型的真实性（接触模型、域随机化）

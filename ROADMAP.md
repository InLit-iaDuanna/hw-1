# 长期路线图

## 当前阶段

V1-V13 已完成 2D 步态研究链条的主要闭环：

- 理论证明：V2/V3/V5
- 机械转译：V6/V10
- 真实接触：V7-V11
- 能量和稳定性分析：V12
- 参数容差：V13

当前最重要的决策点是：在进入 V14 之后，是否继续做 2D 机械要素增强，还是开始准备 3D 和硬件样机。

## 阶段 2：2D 机械升级 V14-V17

| 版本 | 方向 | 目标 |
|---|---|---|
| V14 | 被动摆臂 | V10 PD 下 5/35=14.3%，arm_mass≥0.05 即破坏稳定（窄结论，仅在 V10 PD 下成立） |
| V14b | 被动摆臂 + FSM hip | 摆臂参数空间 14/35=40%（arm_mass=0.05 关键行 5/5），但 V14b × 切片 C 仅 3/36=8.3%，几何边缘摆臂仍破坏稳定 |
| V14c | arm_mass 减重扫描 | 实测：m=0.05 3/36 与 V14b 一致（health_check_passed），m=0.01 升至 5/36 且 ⊂ V13.6.1 best 无摆臂域；arm_mass 为根因，V15 hip SEA 解封 |
| V15 | 弹性肌腱/SEA | V15.0 PEA 失败；**V15.1 SEA direct-drive 成功**：k=5000/10000 复现 V14c 5/36；k=500 best cell forward=4.92 m |
| V16 | 真实电机动力学（实测）| L1 fork V14c 不依赖 V15；ideal 严格还原 V14c；mx64ar_full smoke fall_down；τ_C 扫描非单调 → motor_dynamics_breaks_fsm_revisit_control + tau_C_FSM_resonant_coupling_non_monotonic |
| V17 | 传感器闭环 | 加入 IMU/编码器噪声和状态估计，准备控制器落地 |

## 阶段 3：3D 化 V18-V21

| 版本 | 方向 | 目标 |
|---|---|---|
| V18 | 3D 侧向被动稳定探索 | **完成（否定结果）**：roll_k<200 发散，roll_k≥500 等效 2D。verdict=lateral_stability_requires_active_control |
| V19 | 髋外展辅助 | **完成（否定结果）**：最佳 7 alt/2.97s，漂移率 5-10× 超过 abd 纠正能力。verdict=hip_abd_insufficient_for_lateral_stabilization |
| V20 | 步宽控制 | **完成（否定结果）**：基础架构完成（3D IK + 轨迹规划器），但控制律集成未完成。Smoke Test 失败（1s 后跌倒），基线不稳定。verdict=step_width_control_not_verified，建议跳过 V21 直接进入 V22 硬件设计 |
| V21 | 3D 扰动鲁棒性 | 建立 3D 稳定域和 Floquet 对照（决策门：是否继续 3D 路线或降级为 2D 硬件） |

## 阶段 4：硬件落地 V22-V25

| 版本 | 方向 | 目标 |
|---|---|---|
| V22 | 硬件设计 v1 | **完成（设计文档）**：基于 V13.7+V17 的 2D 样机设计文档，包含硬件规格、BOM、CAD 说明、仿真参数映射。总预算 6500-8000 元，可直接用于制作 |
| V23 | 系统辨识 | **完成（方法论）**：从硬件数据反推物理参数的方法论文档，包括摩擦、惯量、弹簧刚度辨识流程 |
| V24 | Sim-to-real | **完成（策略文档）**：域随机化策略、鲁棒控制器设计、首次上机流程，为硬件迁移做准备 |
| V25 | 实地行走 | **待实施**：需要实际硬件制作完成后进行真实地面行走测试 |

## 决策门

- V13 之后：如果参数容差过窄，优先改机构而不是继续堆控制。
- V14 实测：V10 控制律下任何真实摆臂质量都破坏稳定，与 V13 决策门一致；机械升级不能继续依赖 V10 孤立点控制律。
- **V13.6 实测（2026-05-28）**：事件驱动 FSM 在切片 C 上 4/36=11.1%（V10 16.7%, plan C 0%）→ tier B 部分恢复，路线正确但需 V13.6.1 在每 phase 上独立 grid search。
- **V14b 实测（2026-05-28）**：摆臂参数空间通过 §3.1，几何 + 摆臂双维度未通过（3/36 = 8.3% < V13.6 无摆臂 11.1%）。V13.6.1 best 在无摆臂下相对 V13.6 +2.8 pp 增益与摆臂耦合后归零 → 瓶颈是机构不是控制 → 待决：V14c 改摆臂力学，或跳 V14c 直接 V15。
- **V14c 实测（2026-05-28）**：health_check_verdict=v14b_reproduction_passed（m=0.05 3/36），primary_verdict=arm_mass_is_root_cause_v15_unblocked，monotonicity nonincreasing 满足；m=0.01 success cells = V13.6.1 best 无摆臂域 5 格的严格子集（is_subset=true）。判定瓶颈是摆臂机构而非控制，V15 hip SEA 启动条件具备。
- **V16 实测（2026-05-30）**：L1 一阶电机动力学（mx64ar Dynamixel MX-64AR baseline）fork V14c。L0 退化对照（ideal preset, J=b=τ_C=0）严格还原 V14c (0.0000%)。L1 健康检查（mx64ar_full）失败：forward 0.19 m vs V14c 4.62 m，alt_td 4 vs 10。**τ_C 单因素扫描非单调**：固定 mx64 真实 J_eff=2.8e-3/b_eff=0.05/τ_sat=6.0，仅扫 τ_C_motor∈[0, 3.0e-3] N·m → 成功带 τ_C_eff∈{0, 0.034, ≥0.27} N·m，失败带 [0.013, 0.20] N·m。sign_smooth ε∈[0.001, 0.05] 50× 验证 verdict 不变（物理共振）。MX-64 spec τ_C_eff=0.20 落入失败带正中央。primary_verdict=motor_dynamics_breaks_fsm_revisit_control，sub_finding=tau_C_FSM_resonant_coupling_non_monotonic。V22 选型约束："不可按上界保证选型，必须 FSM 实测"，三选一：(a) τ_C_eff<0.013 低摩擦关节，(b) V13.7 在 control_v136 hip 输出端加 τ_C_compensation=τ_C_eff·sign_smooth(ω_des)，(c) 选恢复带 ≥0.27 的电机。**V17 决策门假设动摇**：V17 状态估计的反真值依赖于稳定控制律，应先做 V13.7 摩擦补偿或换 motor 后再启动 V17。
- **V13.7 实测（2026-06-02）**：前馈摩擦补偿 τ_comp=τ_C_eff·sign_smooth(ω_joint) 加在 FSM 输出端。mx64ar_full smoke PASS（forward 4.63m, alt_td 10，与 V14c 等效）。τ_C 全网格 10/10 通过，失败带 6 点全部恢复。verdict=compensation_eliminates_fail_band。V16 verdict 升级为 motor_dynamics_compatible_with_friction_compensation。**V17 决策门恢复**：V13.7 提供稳定补偿控制律，V17 状态估计可启动。
- V17 之后：如果真实电机模型破坏稳定性，重新选择驱动方案。
- **V18 实测（2026-06-02）**：3D 侧向被动稳定探索。V10 PD + hip_y/hip_roll/hip_abd 自由度。纯被动侧向稳定不存在：roll_k<200 N·m/rad → 3° 扰动即发散（耦合导致矢状面跌倒）；roll_k≥500 等效 2D 约束（无意义）；宽足效果微弱。verdict=lateral_stability_requires_active_control。**V21 决策门提前触发**：3D 纯被动不收敛 → 确认"矢状面被动 + 冠状面主动"路线，V19 引入最小侧向主动稳定。
- **V19 实测（2026-06-03）**：髋外展主动稳定验证。V18 模型基础上 abd 关节改为电机驱动。测试 6 种控制策略（简单 PD、hip_y 反馈、hip_roll 反馈、联合反馈、向摇摆侧前倾、参数网格）。最佳结果 7 alt/2.97s（目标 10 alt/12s 未达标）。根因：侧向漂移率 ~0.05-0.10 m/step，abd 扭矩修正能力 <0.01 m/step（5-10× 不足）。物理限制：abd 关节扭矩产生躯干倾斜但无法产生 net 侧向 GRF（需要脚底位移）。verdict=hip_abd_insufficient_for_lateral_stabilization。**V21 决策门再次确认**：单一髋外展执行器无法稳定 3D 行走 → V20 需引入步宽控制（swing foot 侧向位置规划）或考虑放弃 3D 化路线，直接进入 V22 硬件设计。
- V21 之后：如果 3D 纯被动不收敛，降级为"矢状面被动 + 冠状面主动稳定"的准被动路线。**V18+V19 已确认此降级必要**：被动侧向稳定不存在，髋外展单独不足，需步宽调制或足部侧向位移。

## 公共基础设施

`common/` 已作为跨版本公共库使用，后续版本应优先复用其中的能量、地形、扰动、Poincare 和绘图工具，避免每个版本重复造分析脚本。

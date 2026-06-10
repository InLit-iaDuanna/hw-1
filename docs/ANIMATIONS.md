# hw-1 步态研究项目动画索引

本文档索引 hw-1 项目从 V01 至 V24 所有版本的动画资源，按研究阶段分组。

## 📊 统计总览

- **总版本数**: 35
- **已有视频**: 28
- **研究阶段**: 4（理论验证 / 机械升级 / 3D探索 / 硬件转译）
- **关键里程碑**: V05 (极限环证明), V10 (仿生步态), V13.6 (FSM控制), V18 (3D化)

---

## 🔬 阶段一：理论验证与被动极限环 (V01-V05)

**研究目标**: 证明指南针式机器人的被动动力学极限环存在性

### V01 — MuJoCo Passive Compass Gait
- **定位**: 首次 MuJoCo 被动动力学尝试
- **关键特性**: 无驱动器，斜坡重力驱动，真实软接触
- **视频**:
  - `v01_mujoco_compass_gait/out/passive_compass_gait.mp4` — 单次仿真尝试
  - `v01_mujoco_compass_gait/out/compass_gait_playback.mp4` — 多步稳定回放
- **性能**: 6次左右交替触地，前进1.27m，8s仿真
- **限制**: 对参数（坡度、髋部质量、摩擦）高度敏感

### V02 — 无轮辐轮极限环证明版
- **定位**: 理论验证 - 最简单的被动动力学模型
- **关键特性**: 无膝关节，直腿滚动，理论极限环
- **视频**: `v02_rugged_rimless_limit_cycle/out/rimless_limit_cycle.mp4`
- **学术价值**: 纯理论证明，不适用于实际设备

### V03 — 双腿指南针极限环 MuJoCo 版
- **定位**: 标准指南针式步态模型
- **关键特性**: 双腿刚性，碰撞映射，Poincaré 截面分析
- **视频**: `v03_compass_limit_cycle/out/compass_limit_cycle.mp4`
- **理论基础**: McGeer (1990) 被动动力学行走

### V04 — 带膝被动极限环性 V2
- **定位**: 增加膝关节复杂度
- **关键特性**: 膝关节被动锁定，更仿生的腿部结构
- **视频**: `v04_kneed_limit_cycle/out/kneed_limit_cycle.mp4`
- **进步**: 更接近人类步态形态

### V05 — 真实混合动力学指南针极限环证明版 ⭐
- **定位**: **纯被动极限环理论证明基准**
- **关键特性**: 混合动力学系统，Poincaré 收敛证明，Floquet 稳定性分析
- **视频**: `v05_hybrid_compass_proof/out/hybrid_compass_mujoco.mp4`
- **学术价值**: **所有"纯被动"表述的唯一引用依据**
- **Floquet 特征值**: 最大 0.89 < 1（稳定）
- **重要性**: 后续准被动版本（V06-V17）均需引用本版作为理论基础

---

## 🦿 阶段二：机械升级与控制律探索 (V06-V17)

**研究目标**: 从理论被动转向准被动控制，提升稳定性与鲁棒性

### V06 — 被动极限环作业表达版
- **定位**: 课程作业展示版
- **关键特性**: 简化参数，教学友好说明
- **视频**: `v06_mve_gait_homework/out/v6_mve_gait_explainer.mp4`
- **用途**: 课堂展示，概念讲解

### V07 — 真实 MuJoCo 接触探索版
- **定位**: 接触力学深度探索
- **关键特性**: 参数扫描，接触模型调优
- **视频**: `v07_true_contact_exploration/out/v7_best_attempt.mp4`
- **发现**: 接触刚度/阻尼对稳定性影响量化

### V08 — 准被动辅助步态
- **定位**: 首次引入主动辅助力矩
- **关键特性**: 髋部PD控制 + 能量补偿
- **视频**: `v08_quasi_passive_assisted/out/v8_assisted_walk.mp4`
- **转折点**: 从纯被动转向准被动

### V09 — 仿生准被动稳定行走版
- **定位**: 稳定步态基准
- **关键特性**: 髋/膝PD控制，踝关节被动
- **视频**: `v09_stable_biomimetic_gait/out/v9_stable_walk.mp4`
- **性能**: 稳定多步行走，为V10奠定基础

### V10 — 足踝滚动仿生步态版 ⭐
- **定位**: **仿生机械转译里程碑**
- **关键特性**: 脚跟-足底-脚趾三段式滚动接触，被动踝关节
- **视频**: `v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk.mp4`
- **生物对位**: 
  - 脚跟接触 (0-30% 步态周期)
  - 足底滚动 (25-70%)
  - 脚趾离地 (65-100%)
- **控制律**: 髋/膝主动PD + 踝被动弹簧
- **性能**: 前进4.85m，CoT 0.065，切片C成功率16.7%
- **学术定位**: 准被动仿生步态展示，非纯被动证明
- **配套分析**:
  - `out/v10_phase_portrait.png` — 髋/膝/踝相位图
  - `out/v10_rolling_foot_report.png` — 4格综合报告

### V11 — �崎岖地形与扰动鲁棒性
- **定位**: 地形适应性测试
- **关键特性**: 斜坡变化，障碍物，扰动恢复
- **视频**: 多组地形测试视频
- **发现**: V10控制律在小扰动下保持稳定

### V12 — 能量流 / CoT / Floquet 横向分析
- **定位**: 能效与稳定性量化分析
- **关键特性**: 
  - CoT (Cost of Transport) 计算
  - Floquet 稳定性重算
  - 能量流动分析
- **视频**: `v13_parameter_sensitivity_atlas/out/v13_baseline.mp4`
- **关键指标**: 
  - V10 极限环能量: 52.66 ± 0.53 J
  - Floquet 最大特征值: 0.89（稳定）

### V13 系列 — 参数敏感性与控制优化

#### V13b — 长程 Floquet 重算 + 极限环验证 + 扰动恢复
- **定位**: 极限环长期稳定性验证
- **关键特性**: 100步长程仿真，扰动恢复测试
- **学术价值**: 确认V10极限环长期稳定

#### V13.5 — 鲁棒 hip 控制律探索（否决归档版本）
- **定位**: 三方案控制器对比实验
- **结果**: 三方案均被否决
  - Plan A: 步周期前馈
  - Plan A': 力矩限幅
  - Plan C: 能量整形bang-bang
- **教训**: 单一标量目标压缩丢失时序信息
- **切片C成功率**: 0.0%（全部失败）

#### V13.6 — 事件驱动 FSM hip 控制律 ⭐
- **定位**: **显式相位控制里程碑**
- **关键特性**: 四相位有限状态机
  - `stance_early` (支撑早期): 0.0-0.5
  - `stance_late` (支撑晚期): 0.5-1.0
  - `swing_thrust` (摆动推进): 0.0-0.5，能量注入
  - `swing_retract` (摆动回收): 0.5-1.0
- **视频**: `v13_6_event_driven_fsm/out/v13_6_baseline_walk.mp4`
- **性能**: 
  - 前进4.86m，输入17.45J，CoT 0.072
  - 切片C成功率: 11.1%（4/36）
- **控制参数**: 每相位独立 (k_E, k_PD, τ_max) 三元组
- **决策档**: Tier B（路线正确但需调优）
- **康复设备对位**: 
  - 接触切换 → 鞋底压力开关
  - 相位u → 内部计时器 + IMU步频估计
  - clearance → 髋部IMU高度
- **学术诚信**: 准被动（hip+knee主动），非鲁棒控制器

#### V13.6 refactored — simulation_framework 迁移版
- **定位**: 代码重构，统一仿真框架
- **技术改进**: 模块化架构，便于后续版本复用

#### V13.7 — Floquet 稳定性分析
- **定位**: 稳定性理论深入分析
- **关键特性**: Floquet乘子计算，稳定域映射

#### V13.7 — Friction Compensation（前馈库仑摩擦补偿）
- **定位**: 电机摩擦补偿实验
- **视频**:
  - `v13_7_friction_compensation/out/v13_7_smoke_compensated_ec_i40.mp4` — EC-i40电机补偿
  - `v13_7_friction_compensation/out/v13_7_smoke_compensated_mx64ar.mp4` — MX-64AR补偿
  - `v13_7_friction_compensation/out/v13_7_smoke_no_comp_mx64ar.mp4` — 无补偿对照
- **发现**: 补偿改善低速性能，但对步态稳定性影响有限

#### V13.7 refactored — 统一仿真框架示例
- **定位**: 最终重构版本
- **架构**: 统一的状态估计、控制、记录管道

#### V13 Parameter Sensitivity Atlas — 参数敏感性图集
- **定位**: 几何参数空间扫描
- **关键实验**: 切片C (foot_radius × leg_scale, 6×6栅格)
- **视频**: 多组参数配置视频
- **发现**: V10成功域呈对角带分布，V13.6呈中央方块区

### V14 系列 — 被动摆臂与状态机组合

#### V14 — 被动摆臂版
- **定位**: 引入上肢被动摆动
- **关键特性**: 双臂被动铰链，自然摆动耦合步态
- **视频**:
  - `v14_passive_arms/out/v14_baseline.mp4` — 基准测试
  - `v14_passive_arms/out/v14_arm_mass_comparison.mp4` — 质量对比
- **发现**: 被动摆臂略微改善能量效率（-2% CoT）

#### V14b — passive arms × V13.6 FSM hip
- **定位**: 摆臂 + FSM控制组合
- **视频**: `v14b_state_machine_hip/out/v14b_critical.mp4`
- **结果**: 组合效应不显著

#### V14c — arm mass lightening × slice C
- **定位**: 摆臂质量轻量化探索
- **视频**: `v14c_arm_mass_lightening/out/v14c_critical_f042_l102.mp4`
- **结果**: 轻量化对切片C成功率无显著提升

### V15 系列 — 串联弹性驱动器 (SEA)

#### V15 — Hip SEA Scaffold（髋部弹性驱动器脚手架版）
- **定位**: SEA架构探索
- **关键特性**: 弹簧串联电机，柔顺交互
- **视频**: `v15_hip_sea_scaffold/out/v15_smoke_k0000.mp4`
- **发现**: 弹性元件引入低通滤波效应

#### V15.1 — SEA Direct-Drive（串联弹性驱动器 - 扭矩直传模式）
- **定位**: SEA扭矩控制实现
- **视频**:
  - `v15_1_sea_direct/out/v151_smoke_k00500.mp4` — k=500弹簧
  - `v15_1_sea_direct/out/v151_smoke_k10000.mp4` — k=10000弹簧
- **发现**: 刚度过高退化为刚性传动，过低失去带宽

#### V15.2 — Strict SEA with Pratt Inner Loop（严格SEA + 内环控制）
- **定位**: 经典Pratt SEA实现
- **关键特性**: 内环力控 + 外环位置控制
- **学术参考**: Pratt & Williamson (1995)

### V16 系列 — 电机动力学

#### V16 — Motor Dynamics（R1一阶电机动力学）
- **定位**: 电机带宽与延迟建模
- **视频**:
  - `v16_motor_dynamics/out/v16_smoke_ideal.mp4` — 理想无延迟
  - `v16_motor_dynamics/out/v16_smoke_mx64ar_full.mp4` — MX-64AR真实动力学
- **关键参数**: 
  - 电机时间常数: ~10ms
  - 带宽限制: ~30Hz
- **发现**: 电机延迟对快速相位切换有明显影响

#### V16 refactored — simulation_framework 迁移
- **定位**: 代码架构统一

### V17 系列 — 传感器闭环状态估计

#### V17 — 传感器闭环状态估计
- **定位**: 传感器噪声与滤波器设计
- **关键特性**: 
  - 编码器噪声建模
  - IMU漂移补偿
  - Kalman滤波
- **视频**: `v17_state_estimation/out/v17_mx64ar_noise1.mp4`
- **发现**: 噪声级别1下V13.6控制律仍稳定

#### V17 refactored
- **定位**: 框架迁移版本
- **视频**: 无（代码重构版本）

---

## 🌐 阶段三：3D 化探索 (V18-V21)

**研究目标**: 从2D矢状面扩展到3D空间，探索侧向稳定机制

### V18 — 3D 侧向被动稳定探索 ⭐
- **定位**: **3D化理论边界探索**
- **关键问题**: 是否存在被动侧向稳定机制？
- **新增自由度**: 
  - hip_y (侧向平移)
  - hip_roll (滚转铰链)
  - left/right_hip_abd (髋外展)
- **视频**: `v18_3d_lateral_stability/out/v18_baseline.mp4`
- **核心发现**: **被动侧向稳定不存在**
- **实验结果**:
  - roll_k < 200 N·m/rad: 发散失败
  - roll_k ≥ 500 N·m/rad: 刚性约束（退化为2D）
  - 宽足效应: 微弱（6.3° → 4.4°，仍失败）
- **物理解释**: 
  - 侧向无重力势能驱动
  - 阻尼只能耗散能量
  - 侧向运动是纯耗散系统
- **学术价值**: 
  - 量化侧向约束需求
  - 揭示侧向-矢状面耦合失败机制
  - 论文章节: "被动侧向稳定的不可能性证明"
- **决策门触发**: 3D化必须引入主动控制

### V19 — 髋外展主动稳定验证
- **定位**: 最小主动侧向控制
- **关键特性**: 髋外展PD控制
- **结果**: 部分改善但不足（基于V18结论）

### V20 — 步宽控制探索
- **定位**: 足部落点调节策略
- **关键特性**: 模仿人类步宽调节
- **状态**: 未充分验证

### V21 — 3D 扰动鲁棒性量化
- **定位**: 3D扰动恢复能力测试
- **关键特性**: 侧向推力、滚转扰动、不平地面
- **状态**: 依赖V19/V20方案选定

---

## 🔧 阶段四：硬件转译与实物验证 (V22-V24)

**研究目标**: 从仿真到实物硬件的sim-to-real转译

### V22 — 硬件设计 v1
- **定位**: 机械结构与执行器选型
- **关键内容**: 
  - 电机选型 (MX-64AR / EC-i40)
  - 轻量化设计
  - 传感器布局
- **输出**: CAD模型，BOM清单

### V23 — 系统辨识
- **定位**: 实物参数测量与模型校准
- **关键特性**: 
  - 惯性参数辨识
  - 摩擦系数测量
  - 关节刚度标定
- **方法**: 
  - 自由摆动实验
  - 频率响应测试
  - 负载扭矩曲线

### V24 — Sim-to-real 迁移策略
- **定位**: 仿真到实物的控制器迁移
- **关键策略**: 
  - 域随机化 (domain randomization)
  - 自适应增益调度
  - 安全边界限制
- **状态**: 策略设计阶段

---

## 🎬 MuJoCo 离线动画渲染

**统一动画入口**: 项目动画由 MuJoCo 仿真数据和各版本 `render_*.py` 脚本生成。

### 可用动画

1. **FSMStateTransition** — V13.6 四相位状态机
   - 时长: 8秒 (240帧 @ 30fps)
   - 分辨率: 1920×1080
   - 内容: 四相位切换逻辑、触发条件、进度百分比

2. **RollingFootAnimation** — V10 足踝滚动仿生步态
   - 时长: 10秒 (300帧 @ 30fps)
   - 内容: 脚跟-足底-脚趾三段式滚动、踝关节角度

3. **PhaseVisualization** — 步态相位可视化
   - 时长: 10秒 (300帧 @ 30fps)
   - 内容: 五段相位时间轴、髋/膝/踝角度实时曲线

4. **GaitComparison** — V10 vs V13.6 对比
   - 时长: 12秒 (360帧 @ 30fps)
   - 内容: 分屏对比、性能指标、控制律特性

### 渲染命令
```powershell
.\.venv-mujoco\Scripts\python.exe render_all.py --versions v10 v13_6 v18
.\.venv-mujoco\Scripts\python.exe batch_render_hd.py --priority A
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\render_rolling_foot_gait_v10.py
.\.venv-mujoco\Scripts\python.exe .\v13_6_event_driven_fsm\render_v13_6.py
.\.venv-mujoco\Scripts\python.exe .\v18_3d_lateral_stability\render_v18.py
```

---

## 📂 文件路径速查表

### 关键里程碑视频

| 版本 | 视频路径 | 说明 |
|------|---------|------|
| V05 | `v05_hybrid_compass_proof/out/hybrid_compass_mujoco.mp4` | 纯被动极限环证明 |
| V10 | `v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk.mp4` | 仿生足踝滚动 |
| V13.6 | `v13_6_event_driven_fsm/out/v13_6_baseline_walk.mp4` | 四相位FSM控制 |
| V18 | `v18_3d_lateral_stability/out/v18_baseline.mp4` | 3D侧向稳定探索 |

### README 文档速查

所有版本均包含 `README.md`，位于各版本根目录：
- 设计动机与定位
- 运行命令
- 输出文件清单
- 学术表述口径
- 复现步骤

示例: `D:\Dunna\Documents\hw-1\v13_6_event_driven_fsm\README.md`

---

## 🛠️ 批量渲染工具

### 快速渲染脚本
```powershell
# 使用 render_all.py 批量渲染
cd D:\Dunna\Documents\hw-1
python render_all.py --versions v10 v13_6 v18 --parallel 3
```

### 精选合集生成
```powershell
# 生成答辩/论文用的10分钟精剪版
python create_showcase.py --output showcase_defense.mp4
```

### 本地画廊浏览
```powershell
# 在浏览器中打开
start animation_gallery.html
```

---

## 📊 性能对比速查

| 版本 | 定位 | 前进距离 | CoT | 切片C成功率 | 控制类型 |
|------|------|----------|-----|------------|----------|
| V05 | 纯被动证明 | ~2m | - | - | 纯被动 |
| V10 | 仿生基准 | 4.85m | 0.065 | 16.7% | 准被动 (hip/knee PD) |
| V13.6 | FSM控制 | 4.86m | 0.072 | 11.1% | 准被动 (FSM) |
| V14 | 摆臂版 | ~4.8m | 0.064 | - | 准被动 + 被动臂 |
| V18 | 3D探索 | - | - | 0% | 被动侧向失败 |

---

## 🎓 学术诚信口径标准

### 纯被动表述
- **仅可引用**: V05（混合动力学极限环证明版）
- **禁止表述**: V06-V24 任何版本为"纯被动"

### 准被动表述
- **适用版本**: V08-V17, V19-V21
- **必须说明**: 髋/膝主动PD + 踝被动

### 鲁棒性表述
- **判定标准**: 切片C成功率 ≥ 17%
- **当前达标**: 无（V10 = 16.7%接近）
- **禁止表述**: V13.6 (11.1%) 为"鲁棒控制器"

### 康复设备应用
- **口径**: "对位明确，未临床测试"
- **可表述**: 传感器映射、相位触发逻辑
- **禁止表述**: "用于康复"（需临床验证）

---

## 📝 引用建议

### 论文章节结构
1. **第3章**: 被动动力学理论（引用V05）
2. **第4章**: 机械仿生设计（引用V10）
3. **第5章**: 相位控制策略（引用V13.6）
4. **第6章**: 3D化理论边界（引用V18）
5. **第7章**: 硬件实现（引用V22-V24）

### 答辩幻灯片精选
- 极限环可视化: V05 相位图
- 仿生步态动画: V10 MuJoCo 视频
- 控制律对比: V13.6 MuJoCo 视频和指标表
- 失败案例分析: V18 侧向发散视频

---

## 🔗 相关文档

- [项目主 README](README.md)
- [render_all.py 使用说明](render_all.py) — 批量渲染脚本
- [create_showcase.py 使用说明](create_showcase.py) — 精选合集生成器
- [animation_gallery.html](animation_gallery.html) — 本地浏览画廊

---

**维护日期**: 2026-06-05  
**总视频数**: 28+  
**总文档数**: 35+ README  
**覆盖版本**: V01-V24 (完整)

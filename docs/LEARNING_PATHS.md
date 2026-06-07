# hw-1 项目学习路径

本文档为不同背景的用户提供系统化的学习路径，从入门到精通。

---

## 快速导航

根据你的背景和目标选择学习路径：

| 用户类型 | 推荐路径 | 预计时间 |
|---------|---------|---------|
| 新手用户 | [路径 A：快速上手](#路径-a快速上手30-分钟) | 30 分钟 |
| 控制工程师 | [路径 B：控制律开发](#路径-b控制律开发3-小时) | 3 小时 |
| 理论研究者 | [路径 C：被动步态研究](#路径-c被动步态研究4-小时) | 4 小时 |
| 机械工程师 | [路径 D：硬件设计](#路径-d硬件设计2-小时) | 2 小时 |
| 开发者/贡献者 | [路径 E：项目贡献](#路径-e项目贡献2-小时) | 2 小时 |
| 论文写作者 | [路径 F：论文准备](#路径-f论文准备3-小时) | 3 小时 |

---

## 路径 A：快速上手（30 分钟）

**目标：** 快速理解项目并运行关键版本

**适合人群：** 第一次接触项目的用户

### 第 1 天：环境配置与首次运行（30 分钟）

#### 1. 阅读项目概览（5 分钟）
- [ ] **README.md** — 项目概述
- [ ] **QUICKSTART.md** 第 1 节 — 5 分钟概览

#### 2. 配置环境（5 分钟）
```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate
python -c "import mujoco; print('OK')"
```

#### 3. 运行第一个仿真（10 分钟）
- [ ] **Tutorial 01** — 运行 V13.7 仿真
- [ ] 查看输出文件（CSV + JSON）
- [ ] 理解成功判据

```powershell
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0
```

#### 4. 可视化查看（10 分钟）
- [ ] 打开 **Dashboard**（`dashboard/index.html`）
- [ ] 浏览 Timeline View
- [ ] 查看 V13.7 卡片详情

**完成标志：**
- ✅ 成功运行 V13.7 仿真
- ✅ 理解 forward distance, CoT, alternations 含义
- ✅ 能够在 Dashboard 中找到任意版本

---

## 路径 B：控制律开发（3 小时）

**目标：** 理解控制策略演化，能够开发新控制律

**适合人群：** 控制工程师、机器人学研究者

### 第 1 天：理解基础控制律（1 小时）

#### 1. 理解 PD 基线（15 分钟）
- [ ] 阅读 **v10/README.md**
- [ ] 运行 V10 仿真
- [ ] 查看 `control_v10.py` 中的 PD 控制律

```powershell
python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py --duration 12.0
```

**关键理解：**
- PD 控制律：`τ = kp * (θ_target - θ) + kd * (0 - θ̇)`
- 隐式 bang-bang 行为
- 参数敏感性（V13 揭示成功率仅 16.7%）

#### 2. 理解 FSM 演化（20 分钟）
- [ ] **Tutorial 02** — 理解 FSM 控制律
- [ ] 运行 V13.6 仿真
- [ ] 对比 V10 vs V13.6 性能

```powershell
python v13_6_event_driven_fsm\simulate_v136.py --duration 12.0
```

**关键理解：**
- 4 phase FSM 结构
- 事件驱动状态转换
- 可解释性提升

#### 3. 理解摩擦补偿（25 分钟）
- [ ] 阅读 **v16/README.md** — 电机摩擦分析
- [ ] 阅读 **v13_7/README.md** — 前馈补偿
- [ ] 运行对比实验（有/无补偿）

```powershell
# 无补偿（失败）
python v13_7_friction_compensation\simulate_v13_7.py --no-compensation

# 有补偿（成功）
python v13_7_friction_compensation\simulate_v13_7.py
```

**关键理解：**
- 库仑摩擦非单调共振带
- 前馈补偿：`τ_comp = τ_C * sign(ω)`
- V16 → V13.7 的修复过程

---

### 第 2 天：参数调优与分析（1 小时）

#### 4. 参数敏感性分析（30 分钟）
- [ ] **Tutorial 03** — 参数调优
- [ ] 查看 **Dashboard Heatmap**
- [ ] 手动调整参数并观察效果

```powershell
# 查看 V13 参数图谱
start dashboard\index.html  # → Heatmap View

# 手动调优
cp v13_7_friction_compensation\default_params.yaml my_params.yaml
notepad my_params.yaml  # 修改参数
python v13_7_friction_compensation\simulate_v13_7.py --config my_params.yaml
```

#### 5. 使用参数调优工具（30 分钟）
- [ ] 运行网格搜索
- [ ] 生成热力图

```powershell
cd parameter_tuner
python grid_search_2d.py --param1 foot_radius --param2 leg_length
python visualize_grid_search.py --input results.json
```

---

### 第 3 天：开发新控制律（1 小时）

#### 6. 创建新版本（30 分钟）
- [ ] **Tutorial 05** — 开发者贡献指南
- [ ] 创建 V26 骨架
- [ ] 编写控制律代码
- [ ] 添加单元测试

#### 7. 验证与对比（30 分钟）
- [ ] 运行新控制律仿真
- [ ] 对比 V13.7 vs V26 性能
- [ ] 更新文档

**完成标志：**
- ✅ 理解 PD → FSM → 摩擦补偿的演化
- ✅ 能够调优 FSM 参数
- ✅ 能够开发并测试新控制律

---

## 路径 C：被动步态研究（4 小时）

**目标：** 深入理解被动动态步行理论与实践

**适合人群：** 博士生、理论研究者、论文作者

### 第 1 天：理论基础（1.5 小时）

#### 1. 阅读理论背景（30 分钟）
- [ ] **references/passive_dynamic_walking/论文中文精读翻译笔记.md**
- [ ] 理解关键概念：
  - Passive Dynamic Walking
  - Limit Cycle
  - Hybrid Dynamics
  - Poincaré Section

#### 2. V5 纯被动极限环证明（30 分钟）
- [ ] 阅读 **v05/README.md**
- [ ] 运行 V5 仿真
- [ ] 查看 Poincaré 报告

```powershell
python v05_hybrid_compass_proof\simulate_hybrid_compass.py
python v05_hybrid_compass_proof\analyze_hybrid_compass.py
```

**关键理解：**
- 混合动力学模型
- Poincaré 映射收敛性
- 纯被动极限环存在性证明

#### 3. V2-V4 对照实验（30 分钟）
- [ ] V2: Rimless Wheel 极限环
- [ ] V3: Compass Gait 极限环
- [ ] V4: Kneed Walker 极限环

**理解演化：**
```
Rimless Wheel (最简单) → Compass Gait (加髋) → Kneed Walker (加膝)
```

---

### 第 2 天：能量与稳定性分析（1.5 小时）

#### 4. 能量分析（V12 工具）（45 分钟）
- [ ] **Tutorial 04 第 1 步** — 能量分析
- [ ] 运行 V12 能量分析
- [ ] 计算 CoT 和效率

```powershell
cd v12_energy_cot_analysis
python analyze_energy_v10.py --duration 12.0
```

**关键理解：**
- 能量守恒检查
- 碰撞损耗 vs 摩擦损耗
- CoT 对比（人类 vs 准被动 vs 主动机器人）

#### 5. Floquet 稳定性分析（V13b 工具）（45 分钟）
- [ ] **Tutorial 04 第 2 步** — Floquet 分析
- [ ] 运行长程仿真（60s）
- [ ] 提取 Poincaré 映射
- [ ] 计算 Floquet 乘子

```powershell
cd v13b_floquet_long_run
python run_long_simulation.py --duration 60.0
python extract_poincare_section.py --input out/long_run_trajectory.csv
python compute_floquet_multipliers.py --input out/poincare_data.csv
```

**关键理解：**
- Floquet 乘子的物理意义
- 稳定性判据（|λ| < 1）
- V10 λ_max=0.944 接近边界

---

### 第 3 天：鲁棒性与参数边界（1 小时）

#### 6. 鲁棒性分析（V11）（30 分钟）
- [ ] 阅读 **v11/README.md**
- [ ] 运行地形扰动测试
- [ ] 运行脉冲扰动测试

```powershell
cd v11_rugged_terrain_robustness
python test_terrain_robustness.py
python test_impulse_robustness.py
```

**关键结果：**
- 地形扰动容限：≤ 28.6 mm
- 脉冲扰动容限：≤ 17.1 N

#### 7. 参数敏感性图谱（V13）（30 分钟）
- [ ] 阅读 **v13/README.md**
- [ ] 查看参数图谱
- [ ] 理解成功域与失败带

```powershell
# 查看 Dashboard Heatmap
start dashboard\index.html  # → Heatmap View → V13 Parameter Sweep
```

**关键发现：**
- 成功率：16.7% (6/36)
- 成功域中心：(foot_radius=0.10, leg_length=0.50)
- 孤立点解（非连续域）

---

### 第 4 天：论文图表生成（待续，见路径 F）

**完成标志：**
- ✅ 理解被动步态理论（极限环、Poincaré）
- ✅ 能够进行能量分析和稳定性分析
- ✅ 理解鲁棒性边界和参数敏感性
- ✅ 能够生成论文级别的图表

---

## 路径 D：硬件设计（2 小时）

**目标：** 理解从仿真到硬件的完整设计链条

**适合人群：** 机械工程师、硬件开发者

### 第 1 天：仿真到硬件映射（1 小时）

#### 1. 查看硬件设计文档（20 分钟）
- [ ] **v22_hardware_design/HARDWARE_SPEC.md** — 机械结构
- [ ] **v22_hardware_design/BOM.md** — 物料清单
- [ ] **v22_hardware_design/CAD_NOTES.md** — 设计要点

**关键内容：**
- 机械结构：腿长 0.50m, 髋部 SEA, 膝部弹簧
- 电机选型：MX-64AR (τ_max=6 N·m)
- 传感器：编码器 4096 PPR, 接触开关
- 总预算：6500-8000 元

#### 2. 理解仿真参数映射（20 分钟）
- [ ] **v22_hardware_design/SIMULATION_MAPPING.md**

**映射关系：**

| 仿真参数 | 物理参数 | 映射方法 |
|---------|---------|---------|
| leg_length | 腿长 | 直接对应 |
| foot_radius | 足部半径 | 1:1 缩放 |
| tau_C | 库仑摩擦 | 电机 spec |
| kp_knee | 膝部弹簧 | 实际测量 |

#### 3. 理解电机选型（20 分钟）
- [ ] 阅读 **v16/README.md** — 电机动力学
- [ ] 理解摩擦共振带问题
- [ ] 理解为什么选择 MX-64AR

**关键决策：**
- MX-64AR τ_C=0.20 N·m 落入失败带
- V13.7 前馈补偿完全修复
- 备选：EC-i40 (τ_C=0.01)，但成本 3× 高

---

### 第 2 天：系统辨识与 Sim-to-Real（1 小时）

#### 4. 系统辨识流程（30 分钟）
- [ ] **v23_system_identification/SYSTEM_ID_METHODOLOGY.md**

**辨识内容：**
1. 摩擦参数（τ_C, b_eff）
2. 惯量参数（J_eff）
3. 弹簧刚度（kp_knee）
4. 接触参数（stiffness, damping）

**方法：**
- 摩擦：低速匀速运动，测力矩
- 惯量：自由摆动，拟合周期
- 弹簧：静态加载，测位移

#### 5. Sim-to-Real 策略（30 分钟）
- [ ] **v24_sim_to_real/SIM_TO_REAL_STRATEGY.md**

**策略：**
1. **域随机化**：仿真中加入参数噪声
2. **鲁棒控制**：使用 V17 状态估计
3. **首次上机流程**：
   - 悬吊测试（无地面接触）
   - 单腿测试（固定另一腿）
   - 低速步行（0.5× 正常速度）
   - 全速步行

**安全措施：**
- 急停按钮
- 力矩限制（50% τ_max）
- 侧向导轨约束

---

**完成标志：**
- ✅ 理解仿真参数如何映射到物理硬件
- ✅ 掌握系统辨识方法
- ✅ 了解 Sim-to-Real 策略和安全措施

---

## 路径 E：项目贡献（2 小时）

**目标：** 学会如何贡献代码、文档、测试

**适合人群：** 开发者、想要扩展项目的研究者

### 第 1 天：理解项目架构（30 分钟）

#### 1. 阅读协作约定（10 分钟）
- [ ] **CLAUDE.md** — AI 协作约定
- [ ] **README.md** — 项目结构

#### 2. 理解代码规范（10 分钟）
- [ ] **knowledge_base/best_practices/coding_standards.md**

**关键规范：**
- 命名约定：snake_case, CamelCase
- 类型注解：使用 Type Hints
- Docstring：Google 风格
- 最大行长：100 字符

#### 3. 理解版本控制（10 分钟）
- [ ] **knowledge_base/best_practices/version_control.md**

**关键流程：**
- 功能分支开发
- Commit 规范：`type(scope): subject`
- PR 流程

---

### 第 2 天：创建新版本（1 小时）

#### 4. 跟随开发者教程（45 分钟）
- [ ] **Tutorial 05** — 开发者贡献指南
- [ ] 创建 V26 示例版本
- [ ] 编写控制律
- [ ] 添加单元测试
- [ ] 更新文档

#### 5. 提交 PR（15 分钟）
- [ ] 创建功能分支
- [ ] 提交代码（遵循 commit 规范）
- [ ] 推送并创建 PR

---

### 第 3 天：贡献文档和工具（30 分钟）

#### 6. 更新知识库（15 分钟）
- [ ] 添加 FAQ 条目
- [ ] 更新故障排查指南
- [ ] 补充术语表

#### 7. 改进工具（15 分钟）
- [ ] 优化参数调优脚本
- [ ] 添加可视化工具
- [ ] 更新 Dashboard

**完成标志：**
- ✅ 理解项目架构和代码规范
- ✅ 能够创建新版本并提交 PR
- ✅ 能够贡献文档和工具

---

## 路径 F：论文准备（3 小时）

**目标：** 准备论文所需的所有素材和数据

**适合人群：** 论文作者、答辩准备者

### 第 1 天：理解研究脉络（30 分钟）

#### 1. 阅读版本演化（15 分钟）
- [ ] **VERSIONS.md** — V01-V24 完整索引
- [ ] **VERSION_MILESTONES.md** — 关键里程碑
- [ ] **ROADMAP.md** — 技术路线与决策门

#### 2. 浏览 Dashboard（15 分钟）
- [ ] Timeline View — 理解演化脉络
- [ ] Heatmap View — 记忆关键参数空间
- [ ] Compare View — 版本性能对比

---

### 第 2 天：数据收集与分析（1.5 小时）

#### 3. 运行关键版本（30 分钟）
```powershell
# V5: 纯被动证明
python v05_hybrid_compass_proof\simulate_hybrid_compass.py

# V10: 准被动基线
python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py --duration 12.0

# V13.7: 摩擦补偿
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# V17: 状态估计
python v17_state_estimation\simulate_v17.py --duration 12.0
```

#### 4. 能量与稳定性分析（30 分钟）
- [ ] **Tutorial 04** — 研究者深度教程
- [ ] 运行 V12 能量分析
- [ ] 运行 V13b Floquet 分析
- [ ] 生成能量瀑布图和稳定性演化图

#### 5. 跨版本对比（30 分钟）
```powershell
cd cross_version_analysis
python compare_versions.py --versions v10 v13_6 v13_7 v17
python generate_comparison_table.py --output performance_table.csv
```

---

### 第 3 天：生成论文图表（1 小时）

#### 6. 生成核心图表（30 分钟）

**必备图表：**
1. **能量-性能散点图**（CoT vs Forward distance）
2. **稳定性演化图**（Floquet 乘子 vs 版本）
3. **参数敏感性热力图**（V13 参数图谱）
4. **版本性能雷达图**（多维对比）
5. **技术路线图**（Timeline + 决策门）

**生成脚本：**
```python
# 参考 Tutorial 04 第 4 步
python generate_paper_figures.py --output paper_figures/
```

#### 7. 收集关键数据（30 分钟）

**关键数字记忆：**

| 版本 | Forward (m) | CoT | 关键创新 |
|------|------------|-----|---------|
| V5 | 5.2 | 0.0 | 纯被动极限环证明 |
| V10 | 4.87 | 0.072 | 准被动基线 |
| V13.7 | 4.63 | 0.066 | 摩擦补偿 |
| V17 | 4.58 | 0.068 | 状态估计 |

**否定结果：**
- V18: 3D 侧向被动稳定不存在
- V19: 髋外展不足，漂移率 5-10× 超过修正能力
- V20: 步宽控制未验证

**硬件设计：**
- V22: BOM 6500-8000 元
- V23: 系统辨识方法
- V24: Sim-to-Real 策略

---

### 论文章节建议

#### 第 1 章：引言
**素材：**
- 被动步态理论背景（references/ 笔记）
- 项目动机（README.md）
- 研究问题与贡献（ROADMAP.md 决策门）

#### 第 2 章：方法
**素材：**
- V5 混合动力学模型
- V10 准被动控制律
- V13.6 FSM 架构
- V13.7 摩擦补偿

#### 第 3 章：实验
**素材：**
- V12 能量分析
- V13 参数敏感性
- V13b Floquet 稳定性
- V11 鲁棒性测试

#### 第 4 章：结果
**素材：**
- 跨版本对比表（cross_version_analysis）
- 能量-性能散点图
- 稳定性演化图
- Dashboard 截图

#### 第 5 章：讨论
**素材：**
- V18-V20 否定结果的学术价值
- 2D vs 3D 决策（technical_decisions/why_2d_over_3d.md）
- FSM vs PD 优势（technical_decisions/why_fsm_over_pd.md）

#### 第 6 章：硬件设计
**素材：**
- V22 硬件文档
- V23 系统辨识
- V24 Sim-to-Real 策略

#### 第 7 章：结论与未来工作
**素材：**
- PROJECT_PROGRESS.md（当前状态）
- ROADMAP.md（未来规划）
- V25 实地行走展望

---

**完成标志：**
- ✅ 收集所有关键数据和图表
- ✅ 理解研究脉络和技术决策
- ✅ 准备好论文草稿大纲

---

## 进阶路径：从入门到精通

### Level 1: 入门（已完成路径 A）
- 运行仿真
- 理解基本概念
- 查看可视化

### Level 2: 进阶（已完成路径 B 或 C）
- 理解控制律或理论
- 参数调优
- 能量/稳定性分析

### Level 3: 高级（已完成路径 D 或 E）
- 硬件设计
- 开发新版本
- 系统辨识

### Level 4: 专家（已完成路径 F）
- 论文写作
- 深度研究
- 学术贡献

---

## 推荐学习顺序

### 新手 → 研究者

```
路径 A (30min) → 路径 C (4h) → 路径 F (3h)
```

### 新手 → 开发者

```
路径 A (30min) → 路径 B (3h) → 路径 E (2h)
```

### 新手 → 硬件工程师

```
路径 A (30min) → 路径 B (3h) → 路径 D (2h)
```

---

## 学习资源索引

### 核心文档
- **README.md** — 项目概述
- **QUICKSTART.md** — 快速入门
- **VERSIONS.md** — 版本索引
- **ROADMAP.md** — 技术路线

### 教程
- **Tutorial 01** — 运行第一个仿真（15 分钟）
- **Tutorial 02** — 理解 FSM 控制律（20 分钟）
- **Tutorial 03** — 参数调优（25 分钟）
- **Tutorial 04** — 研究者深度教程（45 分钟）
- **Tutorial 05** — 开发者贡献指南（30 分钟）

### 知识库
- **FAQ** — 常见问题
- **Best Practices** — 最佳实践
- **Technical Decisions** — 技术决策记录
- **Troubleshooting** — 故障排查

### 工具
- **Dashboard** — 可视化看板
- **cross_version_analysis** — 跨版本分析
- **parameter_tuner** — 参数调优工具
- **benchmarks** — 基准测试

---

## 常见问题

### Q1: 我应该从哪个路径开始？

**建议：** 所有人从路径 A 开始（30 分钟快速上手），然后根据背景选择：
- 控制/机器人 → 路径 B
- 理论/博士 → 路径 C
- 机械/硬件 → 路径 D
- 开发/贡献 → 路径 E
- 论文/答辩 → 路径 F

### Q2: 学习路径可以跳过吗？

**不建议跳过路径 A**。其他路径可以根据需要选择，但建议按顺序完成。

### Q3: 学完一个路径需要多久？

**预计时间：**
- 路径 A: 30 分钟
- 路径 B: 3 小时（分 3 天）
- 路径 C: 4 小时（分 4 天）
- 路径 D: 2 小时（分 2 天）
- 路径 E: 2 小时（分 3 天）
- 路径 F: 3 小时（分 3 天）

### Q4: 如何验证学习效果？

**每个路径末尾有"完成标志"**，检查是否达成所有目标。

---

## 反馈与建议

如果你在学习过程中遇到问题或有改进建议：

1. 更新知识库 FAQ
2. 在团队会议中提出
3. 提交 PR 改进学习路径

---

**最后更新**: 2026-06-05

**维护者**: hw-1 项目团队

**下一步**: 选择适合你的学习路径，开始探索！

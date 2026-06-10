# 被动动态步行与 MVE 仿生机构项目

> **🎯 新用户？直接查看 [INDEX.md](INDEX.md) - 5 分钟快速导航！**

## 项目定位

**研究对象**：指南针步态（Compass Gait）极限环的仿生设计与被动动态步行理论  
**应用目标**：脑卒中偏瘫患者步态检测与康复评估医疗系统

本项目从被动动态步行的理论基础出发，通过极限环稳定性分析、准被动控制策略和仿生步态建模，建立**健康步态参考模型**，用于：
1. 对比分析患者步态数据与健康基准的偏差
2. 量化康复训练效果（能量效率、步态稳定性、相位特征）
3. 指导个性化康复方案设计

**为什么选择极限环步态模型？**
- **能量效率基准**：CoT=0.072 接近健康人类步态（0.05），可评估患者能耗异常
- **稳定性指标**：极限环收敛率（λ=0.944）提供步态稳定性量化标准
- **相位特征库**：髋膝踝关节角度-角速度相图，识别异常步态模式
- **参数容差边界**：V13 参数敏感性图谱，定义康复目标范围

**硬件系统（V22-V24）**：
- 利用 IMU、编码器、接触传感器、压力传感器等硬件采集患者步态数据
- 实时对比健康步态基准模型，输出康复评估报告

**核心主线：**  
`V5 纯被动极限环证明` → `V6 MVE 机械转译` → `V9 真实接触稳定行走` → `V10 足踝滚动仿生扩展` → `V11-V13 鲁棒性、能量和参数边界分析` → `V13.7 摩擦补偿` → `V17 传感器闭环` → `Residual RL V2 强化学习优化` → `V22-V24 硬件设计`

---

## 🚀 快速开始

### 第一次使用？（5 分钟）

👉 **[INDEX.md](INDEX.md)** - 项目总导航（推荐起点）

### 想动手实践？（30 分钟）

1. **[QUICKSTART.md](QUICKSTART.md)** — 快速入门指南
2. **[tutorials/](tutorials/)** — 交互式分步教程
3. **[dashboard/index.html](dashboard/index.html)** — 可视化看板（浏览器打开）

### 快速运行示例

```powershell
# 激活环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate

# 运行最成熟版本（V13.7 摩擦补偿）
python v13_7_friction_compensation\simulate_v137.py --duration 12.0

# 运行 Residual RL V2 训练（需 Codex 先完成实现）
python rl_training\train_residual_rl_v2_full.py

# 打开可视化看板
start dashboard\index.html
```

---

## 📚 核心文档

| 文档 | 用途 | 推荐阅读顺序 |
|------|------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | 30 分钟快速入门 | ⭐ 首先阅读 |
| **[VERSION_MILESTONES.md](VERSION_MILESTONES.md)** | 关键版本里程碑（5-8 个必看版本） | ⭐ 快速复习 |
| **[TOOLS_CHEATSHEET.md](TOOLS_CHEATSHEET.md)** | 所有工具命令速查表 | 📌 随时查阅 |
| **[tutorials/README.md](tutorials/README.md)** | 交互式教程索引 | 📖 逐步学习 |
| **[ROADMAP.md](ROADMAP.md)** | 长期规划与决策门 | 理解战略 |
| **[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)** | 版本完成情况 | 了解进度 |
| **[CLAUDE.md](CLAUDE.md)** | 协作约定（给 AI 的） | 开发参考 |

## 目录结构

| 目录 | 说明 |
|---|---|
| `v01_mujoco_compass_gait` | 初始 MuJoCo 指南针步态探索 |
| `v02_rugged_rimless_limit_cycle` | Rimless wheel 极限环对照 |
| `v03_compass_limit_cycle` | 指南针极限环数学/动画对照 |
| `v04_kneed_limit_cycle` | 带膝极限环对照 |
| `v05_hybrid_compass_proof` | 纯被动极限环证明主版本 |
| `v06_mve_gait_homework` | MVE 机械转译与作业表达 |
| `v07_true_contact_exploration` | 真实接触纯被动探索和失败分析 |
| `v08_quasi_passive_assisted` | 准被动髋部补能探索 |
| `v09_stable_biomimetic_gait` | 真实接触准被动稳定行走 |
| `v10_rolling_foot_biomimetic_gait` | 足踝滚动仿生步态 |
| `v11_rugged_terrain_robustness` | 崎岖地形和外力扰动鲁棒性 |
| `v12_energy_cot_analysis` | 能量、CoT、碰撞损耗和 Floquet 分析 |
| `v13_parameter_sensitivity_atlas` | 参数敏感性图谱和设计容差 |
| `v13_6_event_driven_fsm` | 事件驱动 FSM hip 控制律 |
| `v13_7_friction_compensation` | V13.7 摩擦补偿主版本 |
| `v14_passive_arms` | 被动摆臂机构维度验证 |
| `v14b_state_machine_hip` | V13.6 FSM 回流被动摆臂验证 |
| `v14c_arm_mass_lightening` | V14c arm_mass 减重扫描，验证 §3.1 + 解封 V15 |
| `rl_training` | **Residual RL V2 强化学习训练**（PPO on V13.7） |
| `logs/residual_rl_v2` | **RL训练日志、测试结果、TensorBoard记录** |
| `matlab-v01-v13-gait` | V1-V13 MATLAB 数据汇总和报告图 |
| `common` | 跨版本公共分析工具 |
| `render_all.py` / `batch_render_hd.py` | MuJoCo 离线动画批量渲染入口 |

## 环境

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m pip install -r requirements.txt
```

常用查看命令：

```powershell
.\.venv-mujoco\Scripts\python.exe .\v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py
.\.venv-mujoco\Scripts\python.exe .\v11_rugged_terrain_robustness\view_rugged_gait_v11.py
```

MATLAB 汇总：

```matlab
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
run_all_gait_reports
```

## 学术口径

- V5 是纯被动极限环证明依据：无主动驱动，使用混合动力学和 Poincare 收敛说明极限环。
- V8、V9、V10、V11 是准被动或主动稳定展示：含弱补能或髋膝主动稳定，不能写成纯被动。
- V12、V13 是分析层：用于解释能量效率、稳定性边界和参数容差，不是新的步态控制版本。
- **V13.7 + Residual RL V2** 是控制优化层：使用强化学习（PPO）在V13.7基础上学习微调残差，目标提升43-90%性能。

---

## 🤖 Residual RL V2（2026-06 新增）

**目标**：通过强化学习（PPO）在V13.7 FSM控制器基础上学习微调残差，提升步行性能。

### 核心架构

```
V13.7 FSM Controller (1kHz inner loop)
    ↓ 提供基础步态
PPO Residual Layer (200Hz outer loop)
    ↓ 学习微调残差
Improved Gait Performance
```

### 关键特性

- **Observation**: 42维（20基础 + 22相位/FSM信息）
- **Action**: 2维（仅髋关节residual，膝关节固定）
- **Reward**: Baseline-relative improvement
- **预期提升**: 1.05m → 1.5-2.0m（43-90%）

### 快速开始

```powershell
# 激活环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate

# 运行zero residual测试（验证环境）
python rl_training\test_zero_residual_v2.py

# 运行residual sweep（找最优方向）
python rl_training\sweep_residual_combinations.py

# 训练（需Codex先完成实现）
python rl_training\train_residual_rl_v2_full.py

# 查看TensorBoard
tensorboard --logdir=logs/residual_rl_v2/tensorboard
```

### 重要文档

- **实现指南**: `logs/residual_rl_v2/HANDOFF_TO_CODEX.md`
- **Bug修复记录**: `logs/residual_rl_v2/SESSION_2026_06_08.md`
- **Memory记录**: `.claude/projects/memory/residual-rl-v2-fix.md`

### 已知问题（已修复）

⚠️ **Critical Bug Fixed (2026-06-08)**:  
原V2环境在`control_v136()`中错误使用`self.sim_time`而非`steps*dt`作为时间参数，导致4秒时步态失败。简化版`train_residual_rl_v2_simple.py`已修复，达到4.630m baseline。

详见：`logs/residual_rl_v2/SESSION_2026_06_08.md`

## 关键材料

### 可视化看板（推荐）

- **Dashboard**：`dashboard/index.html`（浏览器打开，包含 6 种视图模式）
  - Grid View：所有版本卡片
  - Timeline View：项目演进时间线
  - Compare View：版本对比
  - Trends View：性能趋势图
  - Heatmap View：参数敏感性热力图

### 核心动画与图表

- V5 证明图：`v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png`
- V6 作业表达图：`v06_mve_gait_homework/out/v6_mve_report.png`
- V10 足踝滚动动画：`v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk.mp4`
- V11 鲁棒性图：`v11_rugged_terrain_robustness/out/v11_robustness_report.png`
- V12 能量报告：`v12_energy_cot_analysis/out/v12_report.png`
- V13 参数图谱：`v13_parameter_sensitivity_atlas/out/v13_atlas_report.png`
- V13.7 摩擦补偿动画：`v13_7_friction_compensation/out/v137_walk.mp4`

### 工具与分析

- **跨版本分析**：`cross_version_analysis/`（版本对比、稳定域可视化、能效排行）
- **基准测试**：`benchmarks/`（性能回归检测）
- **CI/CD**：`ci/`（自动化测试、质量检查）
- **参数调优**：`parameter_tuner/`（网格搜索、贝叶斯优化）

完整进度见 `PROJECT_PROGRESS.md`，关键里程碑见 `VERSION_MILESTONES.md`，长期路线见 `ROADMAP.md`。
---

---

## Codex RL Training Result (2026-06-09)

Residual RL V2 is implemented, validated, and trained.

Key results:

- Zero residual identity: `4.630276m`, `100%` success over 10 episodes.
- Best sweep path: `residual_scale=0.20`, action `[0.50, 1.00]`, hip residual torque `[0.100, 0.200]Nm`, distance `4.972583m`, improvement `+7.39%`.
- 100k PPO sanity training: final distance `4.898271m`, success `100%`.

Run commands:

```powershell
.\.venv-mujoco\Scripts\python.exe rl_training\test_zero_residual_v2.py --episodes 10
.\.venv-mujoco\Scripts\python.exe rl_training\sweep_residual_combinations.py --episodes 1 --scales=0.05,0.10,0.15,0.20 --actions=-1.0,-0.5,0.0,0.5,1.0
.\.venv-mujoco\Scripts\python.exe rl_training\train_sanity_100k.py --timesteps 100000 --n-envs 8 --eval-freq 25000 --eval-episodes 5
```

Artifacts:

- Final model: `models/residual_rl_v2_sanity/ppo_final.zip`
- Best model: `models/residual_rl_v2_sanity/ppo_best.zip`
- Logs and JSON reports: `logs/residual_rl_v2/`

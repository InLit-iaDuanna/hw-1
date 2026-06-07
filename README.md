# 被动动态步行与 MVE 仿生机构项目

> **🎯 新用户？直接查看 [INDEX.md](INDEX.md) - 5 分钟快速导航！**

本项目围绕指南针步态、被动动态步行和准被动仿生行走，逐步建立从理论证明、机械转译、真实接触仿真到鲁棒性和参数敏感性的完整研究链条。

**核心主线：**  
`V5 纯被动极限环证明` → `V6 MVE 机械转译` → `V9 真实接触稳定行走` → `V10 足踝滚动仿生扩展` → `V11-V13 鲁棒性、能量和参数边界分析` → `V13.7 摩擦补偿` → `V17 传感器闭环` → `V22-V24 硬件设计`

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
| `v14_passive_arms` | 被动摆臂机构维度验证 |
| `v14b_state_machine_hip` | V13.6 FSM 回流被动摆臂验证 |
| `v14c_arm_mass_lightening` | V14c arm_mass 减重扫描，验证 §3.1 + 解封 V15 |
| `matlab-v01-v13-gait` | V1-V13 MATLAB 数据汇总和报告图 |
| `common` | 跨版本公共分析工具 |
| `compass-gait-remotion` | Remotion 动画讲解材料 |

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

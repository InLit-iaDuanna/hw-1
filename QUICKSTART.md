# hw-1 项目快速入门指南

**目标：30 分钟内理解项目并运行关键版本**

---

## 5 分钟概览

这是一个**被动/准被动动态步行**研究项目，围绕指南针步态模型，从理论证明到硬件设计的完整研究链条。

**核心主线（V01→V25）：**
- V5 证明纯被动极限环存在
- V10 实现足踝滚动仿生步态（最成熟的准被动版本）
- V13.7 添加前馈摩擦补偿，实现电机兼容
- V17 完成传感器闭环状态估计
- V22-V24 完成硬件设计、系统辨识、Sim-to-real 策略文档
- V25 实地行走（待硬件制作完成）

**当前状态（2026-06-04）：** 2D 机械升级主线已闭环（V14-V17），3D 侧向稳定探索完成但结果为否定（V18-V20），硬件设计文档已完成（V22-V24）。

---

## 环境配置（5 分钟）

### 1. 检查虚拟环境

项目已配置 `.venv-mujoco` 虚拟环境，**不要重新创建**。

```powershell
# 进入项目目录
cd D:\Dunna\Documents\hw-1

# 激活虚拟环境
.\.venv-mujoco\Scripts\activate

# 验证环境
python -c "import mujoco; print('MuJoCo version:', mujoco.__version__)"
```

### 2. 安装依赖（如果缺失）

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 最小运行示例（10 分钟）

### V13.7：最推荐的起点版本

**为什么选 V13.7？**
- 包含完整控制链：FSM 控制律 + 电机动力学 + 前馈摩擦补偿
- 代码清晰、注释完整
- 性能稳定（forward 4.63m, 10 alternations, CoT=0.066）
- 是后续硬件设计的基础

#### 运行仿真

```powershell
# 激活环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate

# 运行 12 秒仿真
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# 查看结果（会自动保存到 out/ 目录）
```

**预期输出：**
```
✓ Success: forward 4.63m, alternations 10, CoT_mech=0.066
✓ 生成文件：
  - out/v137_mx64ar_full_compensation_trajectory.csv
  - out/v137_mx64ar_full_compensation_summary.json
```

#### 可视化查看

```powershell
# 查看动画（需要 OpenGL 支持）
python v13_7_friction_compensation\view_v13_7.py
```

---

## 可视化查看（5 分钟）

### 技术路线图 Dashboard

最直观的项目总览方式：

```powershell
# 用浏览器打开
start dashboard\index.html
```

**Dashboard 功能：**
- **Grid View**：所有版本卡片，内联显示关键指标
- **Timeline View**：按阶段分组的时间线
- **Compare View**：版本对比（选择 2-4 个版本）
- **Trends View**：能量效率与性能趋势图
- **Heatmap View**：参数敏感性热力图

**推荐操作：**
1. 切换到 Timeline View，了解项目演进脉络
2. 切换到 Compare View，对比 V10 vs V13.7 vs V17
3. 切换到 Heatmap View，查看 V13 和 V16 的参数空间

### MATLAB 汇总图（V01-V13）

如果安装了 MATLAB：

```matlab
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
run_all_gait_reports
```

输出目录：`matlab-v01-v13-gait\out\`

---

## 常见问题排查

### Q1: 找不到 mujoco 模块

```powershell
# 确认虚拟环境激活
.\.venv-mujoco\Scripts\activate

# 重新安装
pip install mujoco
```

### Q2: 仿真崩溃或报错

**可能原因：**
- XML 模型文件损坏 → 检查 `v13_7_friction_compensation\model_v13_7.xml`
- 参数超出物理边界 → 使用默认参数运行

```powershell
# 使用默认参数
python v13_7_friction_compensation\simulate_v13_7.py
```

### Q3: 可视化窗口无法打开

**原因：** 缺少 OpenGL 支持或 MuJoCo viewer 依赖。

**解决：**
1. 检查显卡驱动更新
2. 或使用渲染脚本生成视频：

```powershell
python v13_7_friction_compensation\render_v13_7.py
```

### Q4: Dashboard 显示异常

**确认浏览器支持：** 推荐使用 Chrome/Edge（需要 JavaScript 支持）

```powershell
# 使用 Chrome 打开
start chrome dashboard\index.html
```

### Q5: 权限问题

如果遇到 PowerShell 执行策略限制：

```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 关键路径高亮

从 V01 到 V24 的"必看版本"清单（按学习路径分组）：

### 🎯 理解被动步态（理论基础）

| 版本 | 5 分钟理解要点 | 位置 |
|------|---------------|------|
| **V2** | Rimless wheel 极限环：证明重力驱动的周期性步态 | `v02_rugged_rimless_limit_cycle/` |
| **V5** | 指南针步态极限环：混合动力学 + Poincaré 收敛证明 | `v05_hybrid_compass_proof/` |

**关键文件：**
- V5 Poincaré 报告：`v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png`

---

### ⚙️ 理解控制律演化（控制策略）

| 版本 | 5 分钟理解要点 | 位置 |
|------|---------------|------|
| **V10** | PD 控制 + 足踝滚动：最早的稳定准被动步态 | `v10_rolling_foot_biomimetic_gait/` |
| **V13.6** | 事件驱动 FSM：将 V10 隐式 bang-bang 显式化为 4 phase | `v13_6_event_driven_fsm/` |
| **V13.7** | 前馈摩擦补偿：解决电机库仑摩擦破坏 FSM 问题 | `v13_7_friction_compensation/` |

**性能对比：**
- V10 成功率：16.7%（切片 C，6/36 格）
- V13.6 成功率：11.1%（4/36），但成功域更集中
- V13.7 摩擦补偿：将 V16 失败带完全修复

---

### 🔩 理解硬件路线（机械升级）

| 版本 | 5 分钟理解要点 | 位置 |
|------|---------------|------|
| **V14c** | 摆臂质量敏感性：arm_mass=0.01 可行，0.05 破坏稳定 | `v14c_arm_mass_lightening/` |
| **V16** | 电机动力学：τ_C 摩擦非单调共振带 [0.013, 0.20] | `v16_motor_dynamics/` |
| **V17** | 状态估计：编码器噪声 + Kalman 滤波 + 接触延迟 | `v17_state_estimation/` |
| **V22** | 硬件设计文档：BOM、CAD、传感器选型、总预算 6500-8000 元 | `v22_hardware_design/` |

**关键发现：**
- V16 揭示 MX-64AR 电机 spec τ_C=0.20 N·m 落入失败带
- V13.7 通过前馈补偿 `τ_comp = τ_C·sign(ω)` 完全修复
- V17 验证 MX-64AR 在 3× 噪声容限下可用

---

### 📊 理解分析工具（数据分析）

| 版本 | 5 分钟理解要点 | 位置 |
|------|---------------|------|
| **V11** | 鲁棒性分析：地形扰动 ≤28.6mm、脉冲扰动 ≤17.1N | `v11_rugged_terrain_robustness/` |
| **V12** | 能量与 CoT：V10 CoT=0.072，V11 CoT=0.091 | `v12_energy_cot_analysis/` |
| **V13** | 参数敏感性图谱：foot_radius × leg_length 6×6 网格 | `v13_parameter_sensitivity_atlas/` |

---

### 🚫 3D 探索（否定结果）

| 版本 | 5 分钟理解要点 | 位置 |
|------|---------------|------|
| **V18** | 3D 侧向被动稳定**不存在**：roll_k<200 发散，≥500 等效 2D | `v18_3d_lateral_stability/` |
| **V19** | 髋外展不足：侧向漂移率 5-10× 超过纠正能力 | `v19_hip_abduction_active/` |
| **V20** | 步宽控制未验证：基础架构完成但控制律未集成 | `v20_step_width_control/` |

**学术价值：** 这些否定结果为"矢状面被动 + 冠状面主动"路线提供理论依据。

---

## 工具速查表

### 仿真与查看

```powershell
# 运行仿真（以 V13.7 为例）
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# 实时查看动画
python v13_7_friction_compensation\view_v13_7.py

# 渲染视频
python v13_7_friction_compensation\render_v13_7.py
```

### Dashboard 可视化

```powershell
# 打开技术路线图
start dashboard\index.html

# 更新 Dashboard 数据
# 编辑 dashboard\data.js 中的 VERSIONS 数组
```

### 跨版本分析工具

```powershell
# 进入跨版本分析目录
cd cross_version_analysis

# 版本性能对比
python compare_versions.py

# 稳定域可视化
python visualize_stability_basins.py

# 能效排行
python energy_efficiency_ranking.py

# 全流程分析
python run_all_analyses.py
```

**输出目录：** `cross_version_analysis/outputs/`

### 基准测试

```powershell
# 进入基准测试目录
cd benchmarks

# 运行所有版本基准
python benchmark_runner.py

# 运行指定版本
python benchmark_runner.py --versions v10 v13_7 v17

# 生成可视化报告
python generate_report.py
```

**输出目录：** `benchmarks/results/`

### CI/CD 自动化

```powershell
# 进入 CI 目录
cd ci

# 运行所有测试
python run_tests.py

# 运行代码质量检查
python run_quality_checks.py

# 运行基准测试（性能回归检测）
python run_benchmarks.py --compare

# 完整 CI 流程
python run_ci.py
```

### MATLAB 汇总（V01-V13）

```matlab
% 在 MATLAB 中运行
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')

% 运行所有报告
run_all_gait_reports

% 或单独生成某版本
generate_v10_report
```

---

## 学习路径建议

### 路径 A：理论研究者（关注被动步态机制）

1. **阅读理论背景**（15 分钟）
   - `references/passive_dynamic_walking/论文中文精读翻译笔记.md`
   - 理解极限环、混合动力学、Poincaré 映射

2. **运行 V5 证明**（10 分钟）
   ```powershell
   python v05_hybrid_compass_proof\simulate_hybrid_compass.py
   python v05_hybrid_compass_proof\analyze_hybrid_compass.py
   ```

3. **查看 V2 对照**（5 分钟）
   - Rimless wheel 作为最简单的被动步态
   - `v02_rugged_rimless_limit_cycle/out/`

4. **理解分析方法**（20 分钟）
   - V12 能量分析
   - V13 参数敏感性
   - `common/` 公共分析库

---

### 路径 B：控制工程师（关注控制律设计）

1. **理解 PD 基线**（10 分钟）
   ```powershell
   python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py
   ```
   - 查看 `control_v10.py` 中的 PD 控制律

2. **理解 FSM 演化**（15 分钟）
   ```powershell
   python v13_6_event_driven_fsm\simulate_v136.py
   ```
   - 查看 `control_v136.py` 中的 4 phase FSM
   - 对比 V10 的隐式 bang-bang

3. **理解摩擦补偿**（15 分钟）
   ```powershell
   python v13_7_friction_compensation\simulate_v13_7.py
   ```
   - 查看前馈补偿实现
   - 对比有/无补偿的性能差异

4. **理解状态估计**（20 分钟）
   ```powershell
   python v17_state_estimation\simulate_v17.py
   ```
   - 编码器量化 + Kalman 滤波
   - 接触延迟模型

---

### 路径 C：机械工程师（关注硬件设计）

1. **查看硬件设计文档**（30 分钟）
   - `v22_hardware_design/HARDWARE_SPEC.md`：机械结构、电机选型
   - `v22_hardware_design/BOM.md`：物料清单
   - `v22_hardware_design/CAD_NOTES.md`：设计要点

2. **理解仿真→硬件映射**（20 分钟）
   - `v22_hardware_design/SIMULATION_MAPPING.md`
   - 仿真参数如何映射到物理参数

3. **系统辨识流程**（20 分钟）
   - `v23_system_identification/SYSTEM_ID_METHODOLOGY.md`
   - 摩擦、惯量、弹簧刚度辨识

4. **Sim-to-real 策略**（20 分钟）
   - `v24_sim_to_real/SIM_TO_REAL_STRATEGY.md`
   - 域随机化、鲁棒控制、首次上机流程

---

### 路径 D：答辩准备（快速复习）

**30 分钟关键路径：**

1. **打开 Dashboard**（5 分钟）
   ```powershell
   start dashboard\index.html
   ```
   - Timeline View：了解演进脉络
   - Heatmap View：记忆关键参数空间

2. **查看关键版本动画**（10 分钟）
   - V5 纯被动极限环：`v05_hybrid_compass_proof/out/*.mp4`
   - V10 足踝滚动：`v10_rolling_foot_biomimetic_gait/out/*.mp4`
   - V13.7 摩擦补偿：`v13_7_friction_compensation/out/*.mp4`

3. **记忆关键数字**（10 分钟）
   - V10 CoT: 0.072
   - V11 扰动容限：地形 ≤28.6mm, 脉冲 ≤17.1N
   - V13 成功率：16.7% (6/36)
   - V13.7 前进距离：4.63m, 10 alternations
   - V16 摩擦失败带：τ_C ∈ [0.013, 0.20] N·m
   - V17 噪声容限：3× safety margin
   - V22 硬件预算：6500-8000 元

4. **复习否定结果**（5 分钟）
   - V18: 3D 被动侧向稳定不存在
   - V19: 髋外展不足，漂移率 5-10× 超过修正能力
   - V20: 步宽控制未验证

---

## 下一步行动

根据你的目标选择：

### 如果你是新接手的研究者
1. 按"路径 A"或"路径 B"完整学习
2. 阅读 `CLAUDE.md`（协作约定）
3. 阅读 `ROADMAP.md`（长期规划）

### 如果你要继续开发
1. 查看 `PROJECT_PROGRESS.md`（当前状态）
2. 查看 `ROADMAP.md` 中的决策门
3. 当前推荐：等待 V22 硬件制作完成后启动 V25

### 如果你要答辩准备
1. 按"路径 D"快速复习
2. 准备 V5 + V10 + V13.7 的演示视频
3. 准备 Dashboard 截图（Timeline + Heatmap）

### 如果你要写论文
1. 查看 `references/passive_dynamic_walking/论文中文精读翻译笔记.md`
2. 使用 `matlab-v01-v13-gait/out/` 中的 MATLAB 图表
3. 引用 V18/V19/V20 否定结果作为理论贡献

---

## 相关文档索引

| 文档 | 用途 | 位置 |
|------|------|------|
| **README.md** | 项目概述 | 根目录 |
| **ROADMAP.md** | 长期规划与决策门 | 根目录 |
| **PROJECT_PROGRESS.md** | 版本完成情况 | 根目录 |
| **CLAUDE.md** | 协作约定（给 AI 的说明） | 根目录 |
| **Dashboard README** | 可视化看板使用说明 | `dashboard/README.md` |
| **Cross-version Analysis** | 跨版本分析工具 | `cross_version_analysis/README.md` |
| **Benchmarks** | 基准测试框架 | `benchmarks/README.md` |
| **CI/CD** | 自动化测试流程 | `ci/README.md` |
| **Common Library** | 公共分析库 | `common/README_new_modules.md` |
| **论文精读笔记** | 理论背景 | `references/passive_dynamic_walking/论文中文精读翻译笔记.md` |

---

## 联系与支持

- **用户**: 段泽琪（工业设计博士，学号 2024211317）
- **项目目录**: `D:\Dunna\Documents\hw-1`
- **Python 环境**: `.venv-mujoco`（Python 3.x + MuJoCo）
- **MATLAB 版本**: R2021a 或更高（用于 V01-V13 数据汇总）

---

**祝你快速上手！如有问题，查看各目录下的 README.md 获取详细说明。**

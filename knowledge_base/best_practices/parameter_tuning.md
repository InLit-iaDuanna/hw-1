# 参数调优策略

本文档提供系统化的参数调优方法和策略。

---

## 参数调优哲学

### 核心原则

1. **理解参数物理意义** — 不盲目调参
2. **从已知稳定点出发** — 降低风险
3. **单变量分析优先** — 解耦影响因素
4. **系统化探索** — 避免遗漏最优区域
5. **记录所有尝试** — 包括失败案例

---

## 参数层次结构

### Level 1: 机械参数（Mechanical）

**影响范围：** 全局（改变系统本质）

| 参数 | 物理意义 | 敏感度 | 调优优先级 |
|------|---------|--------|-----------|
| leg_length | 腿长，影响摆动周期 | ⭐⭐⭐ 高 | P1 |
| foot_radius | 足部滚动半径 | ⭐⭐⭐ 高 | P1 |
| torso_mass | 躯干质量，影响惯性 | ⭐⭐ 中 | P2 |
| leg_mass | 腿质量，影响摆动能量 | ⭐⭐ 中 | P2 |

**调优策略：**
- 先确定 leg_length 和 foot_radius（成功域的基础）
- 再微调质量参数（优化性能）

---

### Level 2: 控制参数（Control）

**影响范围：** 局部（改变控制策略）

| 参数 | 物理意义 | 敏感度 | 调优优先级 |
|------|---------|--------|-----------|
| tau_0, tau_1 | Stance phase 力矩 | ⭐⭐ 中 | P2 |
| tau_2, tau_3 | Swing phase 力矩 | ⭐⭐ 中 | P2 |
| theta_01 | Phase 0→1 切换阈值 | ⭐ 低 | P3 |
| theta_23 | Phase 2→3 切换阈值 | ⭐ 低 | P3 |

**调优策略：**
- 固定机械参数后调整控制参数
- 先调力矩幅值，再调切换阈值

---

### Level 3: 电机参数（Motor）

**影响范围：** 执行器特性

| 参数 | 物理意义 | 敏感度 | 调优优先级 |
|------|---------|--------|-----------|
| tau_C | 库仑摩擦 | ⭐⭐⭐ 高 | P1 |
| compensate_friction | 是否启用补偿 | ⭐⭐⭐ 高 | P1 |
| J_eff | 等效转动惯量 | ⭐ 低 | P3 |
| b_eff | 黏性摩擦系数 | ⭐ 低 | P3 |

**调优策略：**
- tau_C 根据电机 spec 设置
- 优先启用摩擦补偿（V13.7 验证）

---

### Level 4: 环境参数（Environment）

**影响范围：** 外部条件

| 参数 | 物理意义 | 敏感度 | 调优优先级 |
|------|---------|--------|-----------|
| slope_angle | 斜坡角度 | ⭐⭐ 中 | P2 |
| ground_friction | 地面摩擦系数 | ⭐⭐ 中 | P3 |
| timestep | 仿真时间步长 | ⭐ 低 | P3 |

**调优策略：**
- slope_angle 在 0.03-0.08 rad 范围内调整
- timestep 保持 0.001 s（平衡速度和稳定性）

---

## 调优策略

### 策略 1: 单变量扫描（Single Variable Sweep）

**适用场景：** 理解单个参数的影响

**步骤：**

1. 固定所有其他参数为已知稳定值
2. 扫描目标参数（如 foot_radius）
3. 绘制性能曲线
4. 识别最优点和边界

**示例：**

```powershell
# 扫描 foot_radius: 0.08 - 0.12 m，5 档
cd parameter_tuner

python single_var_sweep.py \
    --param foot_radius \
    --range 0.08 0.12 5 \
    --config baseline_params.yaml \
    --output foot_radius_sweep.json

# 可视化
python plot_single_var.py \
    --input foot_radius_sweep.json \
    --output foot_radius_curve.png
```

**预期输出：**

```
foot_radius (m)   Forward (m)   CoT       Success
0.08              1.23          N/A       ❌ (fall)
0.09              3.87          0.078     ✅
0.10              4.63          0.066     ✅
0.11              4.21          0.071     ✅
0.12              2.15          0.095     ⚠️ (边界)
```

**结论：**
- 最优点：foot_radius = 0.10 m
- 成功域：[0.09, 0.11] m
- 边界：< 0.09 或 > 0.11 失败风险高

---

### 策略 2: 网格搜索（Grid Search）

**适用场景：** 探索 2-3 维参数空间

**步骤：**

1. 选择 2-3 个关键参数
2. 定义扫描范围和分辨率
3. 运行所有组合
4. 生成热力图

**示例：**

```powershell
# 2D 网格扫描：foot_radius × leg_length
python parameter_tuner\grid_search_2d.py \
    --param1 foot_radius --range1 0.08 0.12 5 \
    --param2 leg_length --range2 0.45 0.55 5 \
    --output grid_results.json

# 可视化热力图
python parameter_tuner\visualize_grid_search.py \
    --input grid_results.json \
    --output heatmap_2d.png
```

**成本：**
- 5 × 5 = 25 次仿真
- 每次 12s → 总计 ~5 分钟

**输出示例：**

```
leg_length ↑
  0.55 |  ❌  ❌  ❌  ❌  ❌
  0.53 |  ❌  ✅  ✅  ✅  ❌
  0.50 |  ❌  ✅  ✅  ✅  ❌
  0.48 |  ❌  ❌  ✅  ❌  ❌
  0.45 |  ❌  ❌  ❌  ❌  ❌
       +------------------→ foot_radius
       0.08 0.09 0.10 0.11 0.12
```

**结论：**
- 成功域中心：(0.10, 0.50)
- 成功率：9/25 = 36%

---

### 策略 3: 贝叶斯优化（Bayesian Optimization）

**适用场景：** 高维参数空间（>3 维）

**优势：**
- 智能采样，减少仿真次数
- 适合昂贵目标函数（长仿真）

**步骤：**

1. 定义参数边界
2. 定义优化目标（如最小化 CoT）
3. 运行贝叶斯优化（推荐 50-100 次迭代）

**示例：**

```powershell
# 安装 scikit-optimize
pip install scikit-optimize

# 运行贝叶斯优化
python parameter_tuner\bayesian_optimization.py \
    --dimensions 6 \
    --n_calls 100 \
    --objective minimize_cot \
    --output bayesian_results.json
```

**参数空间示例：**

```python
# 在 bayesian_optimization.py 中定义
from skopt.space import Real

dimensions = [
    Real(0.08, 0.12, name='foot_radius'),
    Real(0.45, 0.55, name='leg_length'),
    Real(3.0, 5.0, name='tau_0'),
    Real(3.5, 5.5, name='tau_1'),
    Real(-3.5, -1.5, name='tau_2'),
    Real(1.0, 2.5, name='tau_3'),
]
```

**预期输出：**

```
Iteration 100/100: Best CoT = 0.064
Best parameters:
  foot_radius: 0.102
  leg_length: 0.497
  tau_0: 3.48
  tau_1: 4.12
  tau_2: -2.63
  tau_3: 1.52
```

---

### 策略 4: 遗传算法（Genetic Algorithm）

**适用场景：** 离散参数 + 多目标优化

**优势：**
- 处理非凸问题
- 同时优化多个目标（Pareto 前沿）

**示例：**

```powershell
# 安装 DEAP
pip install deap

# 运行遗传算法
python parameter_tuner\genetic_algorithm.py \
    --population 50 \
    --generations 30 \
    --objectives minimize_cot maximize_robustness \
    --output genetic_results.json
```

**多目标示例：**

```python
# 定义多目标函数
def evaluate(individual):
    cot = simulate_and_get_cot(individual)
    robustness = test_robustness(individual)
    return cot, -robustness  # 最小化 CoT，最大化鲁棒性

# NSGA-II 算法
from deap import algorithms, tools
pop, log = algorithms.eaNSGAII(population, toolbox, ...)
```

---

### 策略 5: 由粗到细（Coarse-to-Fine）

**适用场景：** 参数空间很大，不确定最优区域

**步骤：**

1. **粗扫描**：大范围、稀疏网格（如 10 × 10）
2. **识别成功域**：找到成功点的聚集区域
3. **细扫描**：在成功域内加密（如 5 × 5）
4. **局部优化**：使用梯度或贝叶斯

**示例：**

```powershell
# 第 1 轮：粗扫描
python parameter_tuner\grid_search_2d.py \
    --param1 foot_radius --range1 0.05 0.15 10 \
    --param2 leg_length --range2 0.35 0.65 10 \
    --output coarse_grid.json

# 分析成功域（假设在 [0.09-0.11] × [0.48-0.52]）

# 第 2 轮：细扫描
python parameter_tuner\grid_search_2d.py \
    --param1 foot_radius --range1 0.09 0.11 5 \
    --param2 leg_length --range2 0.48 0.52 5 \
    --output fine_grid.json

# 第 3 轮：局部优化
python parameter_tuner\local_optimization.py \
    --initial 0.10 0.50 \
    --method nelder-mead \
    --output local_optimum.json
```

---

## 参数耦合分析

### 常见耦合关系

#### 耦合 1: leg_length ↔ tau_1

**物理原因：** 腿越长 → 摆动周期越长 → 需要更大推力

**实验：**

```powershell
# 固定 leg_length=0.45, 扫描 tau_1
python single_var_sweep.py --param tau_1 --range 3.0 5.0 5 --config short_leg.yaml

# 固定 leg_length=0.55, 扫描 tau_1
python single_var_sweep.py --param tau_1 --range 3.0 5.0 5 --config long_leg.yaml
```

**预期结果：**
- leg_length=0.45 → 最优 tau_1 ≈ 3.5
- leg_length=0.55 → 最优 tau_1 ≈ 4.5

**结论：** tau_1 需要随 leg_length 调整

---

#### 耦合 2: foot_radius ↔ tau_0

**物理原因：** 足部越大 → 滚动阻力越大 → 需要更大初始推力

**验证：**

```python
# 计算相关系数
import pandas as pd
import numpy as np

df = pd.read_csv('grid_results.csv')
corr = df[['foot_radius', 'tau_0', 'forward_distance']].corr()
print(corr)
```

---

#### 耦合 3: tau_C ↔ compensate_friction

**物理原因：** V16 揭示的非单调共振带

**真值表：**

| tau_C | 补偿 | 结果 | 原因 |
|-------|------|------|------|
| < 0.013 | 关 | ✅ | 摩擦可忽略 |
| 0.013-0.20 | 关 | ❌ | 落入共振带 |
| > 0.27 | 关 | ✅ | 退出共振带 |
| 任意 | 开 | ✅ | 补偿修复 |

**结论：** 必须启用摩擦补偿（V13.7）

---

## 敏感性分析

### 数值梯度法

**目标：** 量化参数对性能的影响

**方法：**

```python
def compute_sensitivity(param_name, base_config, delta=0.01):
    """
    计算参数敏感性 dPerformance/dParam
    """
    # 基线
    perf_base = simulate(base_config)
    
    # +delta
    config_plus = base_config.copy()
    config_plus[param_name] *= (1 + delta)
    perf_plus = simulate(config_plus)
    
    # -delta
    config_minus = base_config.copy()
    config_minus[param_name] *= (1 - delta)
    perf_minus = simulate(config_minus)
    
    # 中心差分
    sensitivity = (perf_plus - perf_minus) / (2 * delta * base_config[param_name])
    
    return sensitivity

# 计算所有参数的敏感性
params = ['foot_radius', 'leg_length', 'tau_0', 'tau_1', 'tau_2', 'tau_3']
sensitivities = {p: compute_sensitivity(p, base_config) for p in params}

# 排序
sorted_params = sorted(sensitivities.items(), key=lambda x: abs(x[1]), reverse=True)
for param, sens in sorted_params:
    print(f"{param}: {sens:.4f}")
```

**输出示例：**

```
foot_radius: -12.3456  (最敏感)
leg_length: -8.9012
tau_1: 3.4567
tau_0: 2.8901
tau_2: -1.2345
tau_3: 0.5678  (最不敏感)
```

---

### 方差分析（ANOVA）

**目标：** 分解各参数对总方差的贡献

**方法：**

```python
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# 准备数据（从网格搜索结果）
X = df[['foot_radius', 'leg_length', 'tau_0', 'tau_1', 'tau_2', 'tau_3']].values
y = df['forward_distance'].values

# 训练随机森林
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)

# 特征重要性
importance = rf.feature_importances_
for param, imp in zip(params, importance):
    print(f"{param}: {imp:.4f}")
```

---

## 调优案例

### 案例 1: V10 → V13.6 调优

**背景：** V10 使用 PD 控制，成功率 16.7%。V13.6 改用 FSM，需要重新调优。

**步骤：**

1. **迁移机械参数**（保持不变）
   ```yaml
   leg_length: 0.50
   foot_radius: 0.10
   torso_mass: 10.0
   ```

2. **初始化 FSM 参数**（根据 V10 的 PD 输出）
   - 分析 V10 的力矩时间序列
   - 识别 4 个 phase 的平均力矩
   - 设置为 FSM 初值

3. **单变量调优**
   - 固定 tau_2, tau_3，扫描 tau_0, tau_1
   - 固定力矩，扫描 theta_01, theta_23

4. **网格搜索微调**
   - 在最优点附近 ±10% 范围内细扫

**结果：**
- 初始成功率：0%（直接迁移失败）
- 调优后成功率：11.1%
- 性能：forward 4.52m, CoT 0.074

---

### 案例 2: V13.7 摩擦补偿调优

**背景：** V16 揭示 MX-64AR 电机 τ_C=0.20 N·m 落入失败带。

**问题：** V13.6 在真实电机下完全失败（forward 0.19m）。

**解决方案：**

1. **启用前馈补偿**
   ```yaml
   motor:
     tau_C: 0.20
     compensate_friction: true  # 关键！
   ```

2. **验证补偿效果**
   ```powershell
   # 无补偿
   python simulate_v13_7.py --no-compensation
   # 结果：forward 0.19m ❌
   
   # 有补偿
   python simulate_v13_7.py
   # 结果：forward 4.63m ✅
   ```

3. **扫描 τ_C 范围**
   - 验证补偿在全范围内有效
   - 确认 0.01-0.30 N·m 均成功

**结果：**
- 完全修复电机动力学问题
- 性能恢复到 V13.6 水平

---

### 案例 3: V14b 摆臂优化

**背景：** V14 引入被动摆臂，V14b 探索质量轻量化。

**目标：** 找到最大允许 arm_mass。

**方法：**

```powershell
# 扫描 arm_mass: 0.01 - 0.10 kg
python v14c_arm_mass_lightening\scan_arm_mass.py \
    --range 0.01 0.10 10 \
    --duration 12.0
```

**结果：**

```
arm_mass (kg)   Success Rate   Forward (m)
0.01            100% (20/20)   4.85
0.02            95% (19/20)    4.72
0.03            75% (15/20)    4.31
0.04            40% (8/20)     3.12
0.05            0% (0/20)      1.23 (fail)
...
```

**结论：**
- 安全上限：arm_mass ≤ 0.03 kg
- 推荐值：arm_mass = 0.01 kg（40% 成功率 vs V13.6 的 11.1%，提升 2.8×）

---

## 调优工具箱

### 工具 1: 参数调优脚本

**位置：** `parameter_tuner/`

```powershell
# 单变量扫描
python single_var_sweep.py --param foot_radius --range 0.08 0.12 5

# 2D 网格搜索
python grid_search_2d.py --param1 foot_radius --param2 leg_length

# 贝叶斯优化
python bayesian_optimization.py --n_calls 100

# 遗传算法
python genetic_algorithm.py --population 50 --generations 30
```

---

### 工具 2: 可视化工具

```powershell
# 单变量曲线
python plot_single_var.py --input sweep_results.json

# 2D 热力图
python visualize_grid_search.py --input grid_results.json

# Pareto 前沿
python plot_pareto_front.py --input multi_objective_results.json
```

---

### 工具 3: Dashboard Heatmap

**位置：** `dashboard/index.html`

**功能：**
- 查看 V13 参数敏感性图谱
- 查看 V16 摩擦共振带
- 交互式探索参数空间

---

## 最佳实践

### ✅ 推荐做法

1. **理解物理意义**
   - 不要盲目调参
   - 每个参数都应该有物理解释

2. **从已知稳定点出发**
   - 复制默认参数
   - 逐步修改

3. **单变量分析优先**
   - 理解独立影响
   - 再考虑耦合

4. **记录所有尝试**
   - 包括失败案例
   - 避免重复探索

5. **使用自动化工具**
   - 参数扫描脚本
   - 减少手工劳动

---

### ❌ 避免做法

1. **同时调整多个参数**
   - 无法解耦影响
   - 难以复现

2. **忽略失败案例**
   - 失败边界同样重要
   - 可能揭示物理机制

3. **过度追求性能**
   - 牺牲鲁棒性
   - 陷入局部最优

4. **不验证鲁棒性**
   - 单次成功不代表稳定
   - 需要多次测试

---

## 相关资源

- **仿真工作流**: [simulation_workflow.md](simulation_workflow.md)
- **FAQ 参数问题**: [../faq/parameters.md](../faq/parameters.md)
- **V13 敏感性图谱**: `v13_parameter_sensitivity_atlas/README.md`
- **V16 摩擦分析**: `v16_motor_dynamics/README.md`
- **参数调优工具**: `parameter_tuner/README.md`

---

**最后更新**: 2026-06-05

# Parameter Space Explorer

参数空间探索和可视化工具集，用于系统化地理解参数对系统行为的影响并发现最优参数区域。

## 功能特性

### 1. 采样策略 (`space_sampler.py`)
- **网格采样**：均匀覆盖参数空间
- **随机采样**：Monte Carlo 方法
- **拉丁超立方采样 (LHS)**：高效空间填充
- **Sobol 序列**：低差异序列，适合灵敏度分析
- **自适应采样**：关注有趣区域

### 2. 响应曲面 (`response_surface.py`)
- **高斯过程回归 (GPR)**：适合小样本，提供不确定性估计
- **多项式拟合**：简单快速，可解释性强
- **径向基函数 (RBF)**：适合复杂非线性
- **集成模型**：多模型平均

### 3. 灵敏度分析 (`sensitivity_analyzer.py`)
- **Sobol 指数**：全局灵敏度，一阶和总阶效应
- **Morris 方法**：快速参数筛选
- **偏相关分析**：线性和秩相关
- **交互矩阵**：二阶参数交互

### 4. 自动优化 (`optimizer.py`)
- **贝叶斯优化**：高效黑盒优化，适合昂贵目标函数
- **遗传算法**：全局搜索，适合多峰问题
- **Nelder-Mead**：梯度自由优化
- **多目标优化**：NSGA-II，Pareto 前沿

### 5. 可视化 (`visualizer.py`)
- **2D 切片图**：固定其他参数
- **3D 响应曲面**：两参数变化
- **等高线图**：平面投影
- **Pareto 前沿**：多目标优化结果
- **灵敏度排行**：条形图
- **交互热图**：参数间交互强度
- **优化历史**：收敛过程
- **参数分布**：采样覆盖度

## 安装依赖

```bash
pip install numpy scipy scikit-learn matplotlib seaborn SALib pymoo joblib
```

## 快速开始

### 基本用法

```python
from parameter_explorer import ParameterRange, ParameterExplorer

# 1. 定义参数范围
param_ranges = [
    ParameterRange("hip_kp", 10.0, 50.0),
    ParameterRange("hip_kd", 1.0, 10.0),
    ParameterRange("knee_kp", 5.0, 30.0),
    ParameterRange("knee_kd", 0.5, 5.0),
]

# 2. 定义目标函数
def objective_func(params):
    """运行仿真并返回性能指标（如前进距离）。"""
    # 这里调用你的仿真代码
    # result = run_simulation(**params)
    # return result['forward_distance']
    pass

# 3. 创建探索器
explorer = ParameterExplorer(
    param_ranges=param_ranges,
    output_dir="exploration_results",
    objective_func=objective_func,
    verbose=True
)

# 4. 初始采样
explorer.initial_sampling(method="lhs", n_samples=50, seed=42)

# 5. 拟合响应曲面
explorer.fit_response_surface(method="gp")

# 6. 灵敏度分析
sensitivity = explorer.sensitivity_analysis(method="morris", n_samples=20)

# 7. 参数优化
best = explorer.optimize(method="bayesian", n_iterations=50)

# 8. 可视化
explorer.visualize_2d_slices()
explorer.visualize_3d_surface("hip_kp", "hip_kd")

# 9. 生成报告
explorer.generate_report()
```

### 多目标优化示例

```python
# 定义多个目标函数
def distance_objective(params):
    # 最大化前进距离
    return run_simulation(**params)['forward_distance']

def energy_objective(params):
    # 最小化能耗（返回负值以转为最大化）
    return -run_simulation(**params)['energy_cost']

# 多目标优化
pareto = explorer.multi_objective_optimize(
    objective_funcs=[distance_objective, energy_objective],
    objective_names=["Distance (m)", "Energy Efficiency"],
    maximize=[True, True],  # 两者都最大化
    n_generations=100,
    population_size=100
)

# Pareto 前沿将自动可视化
```

## 应用场景

### 1. V13.7 FSM 相位时长优化

探索 FSM 各相位时长对步态稳定性的影响：

```python
param_ranges = [
    ParameterRange("stance_early_duration", 0.1, 0.3),
    ParameterRange("stance_late_duration", 0.15, 0.35),
    ParameterRange("swing_thrust_duration", 0.1, 0.25),
    ParameterRange("swing_retract_duration", 0.1, 0.25),
]

def fsm_objective(params):
    # 运行 V13.7 仿真
    from v13_7_refactored.simulate_v137_refactored import run_simulation
    result = run_simulation(params)
    return result['forward_distance']

explorer = ParameterExplorer(param_ranges, "v137_fsm_exploration", fsm_objective)
explorer.initial_sampling(method="lhs", n_samples=100)
explorer.sensitivity_analysis(method="sobol", n_samples=512, calc_second_order=True)
best = explorer.optimize(method="bayesian", n_iterations=50)
```

### 2. V10 PD 增益调优

优化 PD 控制器增益：

```python
param_ranges = [
    ParameterRange("hip_kp", 10.0, 50.0, log_scale=False),
    ParameterRange("hip_kd", 1.0, 10.0, log_scale=False),
    ParameterRange("knee_kp", 5.0, 30.0, log_scale=False),
    ParameterRange("knee_kd", 0.5, 5.0, log_scale=False),
]

def pd_objective(params):
    from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import run_simulation
    result = run_simulation(params)
    return result['score']

explorer = ParameterExplorer(param_ranges, "v10_pd_exploration", pd_objective)
# 快速筛选重要参数
sensitivity = explorer.sensitivity_analysis(method="morris", n_samples=20)
# 只优化重要参数
important_params = [name for name, score in sensitivity['ranked_params'][:2]]
```

### 3. 多目标：距离 + CoT

同时最大化前进距离和最小化能耗：

```python
def distance_func(params):
    result = run_simulation(params)
    return result['forward_distance']

def cot_func(params):
    result = run_simulation(params)
    # CoT 越小越好，取负数转为最大化
    return -result['cost_of_transport']

pareto = explorer.multi_objective_optimize(
    objective_funcs=[distance_func, cot_func],
    objective_names=["Distance", "Efficiency"],
    maximize=[True, True],
    n_generations=100
)

# 从 Pareto 前沿中选择折中解
pareto_objectives = pareto['pareto_objectives']
# 找到距离和效率的加权和最大的解
weights = [0.6, 0.4]  # 60% 距离，40% 效率
scores = pareto_objectives @ weights
best_idx = np.argmax(scores)
best_solution = pareto['pareto_params'][best_idx]
```

## 工作流程

```
1. 初始采样
   ├─ 网格采样（低维）
   ├─ LHS 采样（中维）
   └─ Sobol 采样（高维/灵敏度分析）
   
2. 响应曲面拟合
   ├─ 高斯过程（小样本）
   ├─ 多项式（平滑响应）
   └─ RBF（复杂非线性）
   
3. 灵敏度分析
   ├─ Morris 筛选（快速识别重要参数）
   └─ Sobol 分析（详细量化影响）
   
4. 优化
   ├─ 贝叶斯优化（样本效率高）
   ├─ 遗传算法（全局搜索）
   └─ 多目标优化（Pareto 前沿）
   
5. 可视化与报告
   ├─ 2D 切片
   ├─ 3D 曲面
   ├─ 等高线图
   ├─ 灵敏度排行
   └─ Pareto 前沿
```

## 输出文件

所有结果保存在指定的 `output_dir`：

```
exploration_results/
├── initial_sampling.json          # 初始采样数据
├── param_distribution_lhs.png     # 参数分布直方图
├── sensitivity_morris.json        # Morris 灵敏度分析结果
├── sensitivity_morris.png         # 灵敏度条形图
├── sensitivity_sobol.json         # Sobol 灵敏度分析结果
├── sensitivity_sobol.png          # Sobol 灵敏度条形图
├── interaction_heatmap.png        # 参数交互热图
├── optimization_bayesian.json     # 贝叶斯优化结果
├── optimization_bayesian.png      # 优化历史
├── slice_2d_hip_kp.png           # 2D 切片图（每个参数）
├── surface_3d_hip_kp_hip_kd.png  # 3D 响应曲面
├── contour_hip_kp_hip_kd.png     # 等高线图
├── pareto_front.png              # Pareto 前沿（多目标）
└── exploration_report.txt         # 文本报告
```

## 最佳实践

### 采样策略选择

- **低维 (D ≤ 3)**：网格采样，全面覆盖
- **中维 (3 < D ≤ 10)**：LHS，均衡覆盖
- **高维 (D > 10)**：Sobol 或 Morris 筛选后降维
- **灵敏度分析**：Sobol 序列

### 响应曲面选择

- **小样本 (n < 50)**：高斯过程
- **平滑响应**：二次多项式
- **复杂非线性**：RBF 或集成模型
- **不确定性重要**：高斯过程

### 优化方法选择

- **昂贵目标函数**：贝叶斯优化（样本效率高）
- **多峰问题**：遗传算法（全局搜索）
- **快速评估**：Nelder-Mead（收敛快）
- **多个目标**：NSGA-II（Pareto 前沿）

### 计算资源考虑

- 并行评估：使用 `joblib.Parallel` 包装目标函数
- 代理模型：用响应曲面替代仿真（粗筛后精调）
- 自适应采样：先 Morris 筛选，再优化重要参数

## API 参考

详见各模块的 docstring：

- `space_sampler.py`: 采样方法
- `response_surface.py`: 响应曲面拟合
- `sensitivity_analyzer.py`: 灵敏度分析
- `optimizer.py`: 优化算法
- `visualizer.py`: 可视化工具
- `run_exploration.py`: 主流程接口

## 注意事项

1. **目标函数**：必须接受参数字典，返回标量值
2. **参数范围**：确保边界合理，避免仿真失败
3. **归一化**：内部自动处理，无需手动归一化
4. **多目标**：pymoo 库需要单独安装 `pip install pymoo`
5. **并行化**：目标函数需要线程安全

## 示例项目

完整示例见 `examples/` 目录（TODO）：

- `example_v137_fsm.py`: V13.7 FSM 相位优化
- `example_v10_pd.py`: V10 PD 增益调优
- `example_multiobjective.py`: 多目标优化示例

## 参考文献

- Sobol 灵敏度分析: Saltelli et al. (2008)
- Morris 方法: Morris (1991)
- 贝叶斯优化: Snoek et al. (2012)
- NSGA-II: Deb et al. (2002)

## 作者

hw-1 项目组

## 许可

MIT License

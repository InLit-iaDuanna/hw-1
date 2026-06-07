# 自动参数优化工具集

自动搜索最优控制参数，替代手动试错。

## 目录结构

```
auto_optimization/
├── optimizers/
│   ├── bayesian_optimizer.py    # 贝叶斯优化（推荐）
│   ├── genetic_algorithm.py     # 遗传算法
│   ├── grid_search.py           # 网格搜索
│   ├── random_search.py         # 随机搜索
│   └── cma_es.py                # CMA-ES
├── objectives/
│   ├── objective_functions.py   # 目标函数定义
│   └── multi_objective.py       # 多目标优化
├── constraints/
│   ├── parameter_bounds.py      # 参数边界
│   └── physical_constraints.py  # 物理约束
├── configs/
│   ├── v137_fsm_timing.yaml     # V13.7 FSM 时长优化配置
│   └── v10_pd_tuning.yaml       # V10 PD 增益优化配置
├── run_optimization.py          # 主流程
├── compare_optimizers.py        # 对比不同算法
└── README.md
```

## 安装依赖

```powershell
# 激活虚拟环境
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\Activate.ps1

# 安装优化库
pip install scikit-optimize  # 贝叶斯优化
pip install deap             # 遗传算法
pip install cma              # CMA-ES
pip install pyyaml           # YAML 配置解析
pip install matplotlib       # 结果可视化
```

## 快速开始

### 1. 运行单个优化器

```powershell
# 贝叶斯优化 V13.7 FSM 时长参数
python auto_optimization/run_optimization.py `
    --config auto_optimization/configs/v137_fsm_timing.yaml `
    --optimizer bayesian

# 遗传算法优化 V10 PD 增益
python auto_optimization/run_optimization.py `
    --config auto_optimization/configs/v10_pd_tuning.yaml `
    --optimizer genetic

# 其他优化器选项：random, grid, cmaes
```

### 2. 对比多个优化器

```powershell
# 在同一问题上对比贝叶斯、遗传、随机搜索
python auto_optimization/compare_optimizers.py `
    --config auto_optimization/configs/v137_fsm_timing.yaml `
    --budget 50

# 自动生成收敛曲线和性能对比图
```

## 配置文件格式

YAML 配置示例：

```yaml
version: "v13_7_refactored"  # 版本目录名

# 参数定义
parameters:
  - name: "stance_early_duration"
    type: "continuous"  # continuous | integer | categorical | log_uniform
    bounds: [0.10, 0.30]
    default: 0.20
    description: "支撑早期相位时长 (s)"
  
  - name: "swing_thrust_duration"
    type: "continuous"
    bounds: [0.05, 0.20]
    default: 0.12

# 目标函数
objective:
  type: "maximize_distance"  # maximize_distance | minimize_cot | combined

# 或组合目标：
# objective:
#   type: "combined"
#   distance_weight: 0.7
#   cot_weight: -0.3  # 负值表示最小化
#   mass: 10.0

# 优化器配置
optimizer: "bayesian"
budget: 50  # 最大评估次数
n_initial_points: 10
```

## 优化器对比

| 优化器 | 适用场景 | 样本效率 | 并行性 | 推荐度 |
|--------|----------|----------|--------|--------|
| **贝叶斯优化** | 仿真耗时（>5s），连续参数 | 高 | 中 | ⭐⭐⭐⭐⭐ |
| **遗传算法** | 离散/混合参数，多峰函数 | 中 | 高 | ⭐⭐⭐⭐ |
| **CMA-ES** | 高维连续优化（10-100 维） | 高 | 中 | ⭐⭐⭐⭐ |
| **随机搜索** | 基线方法，快速测试 | 低 | 高 | ⭐⭐ |
| **网格搜索** | 2-3 维低维问题 | 低 | 高 | ⭐⭐ |

### 贝叶斯优化（推荐）

**优点**：
- 样本高效：每次评估利用历史信息
- 自动权衡探索与利用
- 适合耗时仿真

**适用**：
- V13.7 FSM 相位时长（4 维）
- V10 PD 增益（2-4 维）
- 评估预算有限（30-100 次）

### 遗传算法

**优点**：
- 全局搜索能力强
- 适合离散参数
- 易并行化

**适用**：
- 混合参数空间
- 多峰目标函数
- 可并行评估

## 应用示例

### 示例 1：V13.7 FSM 相位时长优化

**问题**：V13.7 使用 4 相位 FSM（支撑早/晚期、摆动推进/回收），手动调整耗时。

**解决**：

1. 创建配置 `configs/v137_fsm_timing.yaml`
2. 运行贝叶斯优化：
   ```powershell
   python auto_optimization/run_optimization.py `
       --config auto_optimization/configs/v137_fsm_timing.yaml `
       --optimizer bayesian
   ```
3. 50 次评估后找到最优时长组合
4. 结果保存到 `results/bayesian_<timestamp>.json`

**预期**：
- 评估次数：50 次（约 10-15 分钟）
- 前进距离提升：10-20%

### 示例 2：V10 PD 增益调优

**问题**：髋/膝 PD 增益需要满足稳定性和能效平衡。

**解决**：

1. 使用组合目标（70% 距离 + 30% CoT）
2. 运行优化：
   ```powershell
   python auto_optimization/run_optimization.py `
       --config auto_optimization/configs/v10_pd_tuning.yaml `
       --optimizer bayesian
   ```

**预期**：
- 找到 Pareto 最优增益
- CoT 降低 15-25%

## 结果分析

### 查看结果

```python
import json
from pathlib import Path

# 加载结果
result_path = Path("auto_optimization/results/bayesian_<timestamp>.json")
with open(result_path) as f:
    result = json.load(f)

print(f"最优参数: {result['best_params']}")
print(f"最优值: {result['best_value']}")

# 收敛曲线
import matplotlib.pyplot as plt
plt.plot(result['convergence_curve'])
plt.xlabel('Evaluation')
plt.ylabel('Best Value')
plt.title('Convergence Curve')
plt.show()
```

### 对比结果

运行 `compare_optimizers.py` 自动生成：

1. 收敛曲线对比图
2. 最终性能柱状图
3. 汇总表（最优值、评估次数、运行时间）

## 扩展

### 添加新优化问题

1. 创建配置文件 `configs/my_problem.yaml`
2. 定义参数空间和目标函数
3. 运行优化

### 自定义目标函数

```python
from auto_optimization.objectives.objective_functions import ObjectiveFunction

class MyObjective(ObjectiveFunction):
    def evaluate(self, result: dict) -> float:
        # 自定义评估逻辑
        return custom_score
    
    @property
    def name(self) -> str:
        return "my_objective"
```

### 添加物理约束

```python
from auto_optimization.constraints.physical_constraints import Constraint

class MyConstraint(Constraint):
    def check(self, params: dict) -> tuple[bool, str]:
        # 自定义约束检查
        if constraint_satisfied:
            return True, "约束满足"
        else:
            return False, "约束违反"
```

## 常见问题

### Q: 优化器找到的参数仿真失败？

A: 添加物理约束或缩小参数边界，确保搜索空间内所有参数都可行。

### Q: 收敛太慢？

A: 
- 贝叶斯优化：增加 `n_initial_points`（更多探索）
- 遗传算法：增大 `population_size`
- 考虑缩小搜索范围

### Q: 如何并行评估？

A: 修改评估函数支持批量评估，或使用支持并行的优化器（如遗传算法）。

### Q: 多目标优化（距离 vs CoT）？

A: 使用 `combined` 目标或 `multi_objective.py` 中的 Pareto 优化。

## 参考文献

- 贝叶斯优化：Brochu et al. (2010) "A Tutorial on Bayesian Optimization"
- 遗传算法：DEAP 文档 https://deap.readthedocs.io
- CMA-ES：Hansen (2016) "The CMA Evolution Strategy"

## 联系

问题和建议：hw-1 项目维护者

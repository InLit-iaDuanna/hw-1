# 快速开始指南

## 安装

### 1. 激活虚拟环境

```powershell
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
cd D:\Dunna\Documents\hw-1
pip install -r auto_optimization/requirements.txt
```

## 验证安装

运行测试套件：

```powershell
python auto_optimization/test_optimizers.py
```

预期输出：
```
============================================================
运行优化器测试套件
============================================================

测试参数空间...
  [PASS] 测试通过

测试目标函数...
  [PASS] 测试通过

测试随机搜索...
  [PASS] 测试通过

============================================================
所有测试通过！
============================================================
```

## 第一个优化任务

### 示例：简单演示

```powershell
python auto_optimization/example_usage.py
```

这将运行一个简单的优化示例，演示：
- 贝叶斯优化基本用法
- 遗传算法基本用法
- 多个优化器性能对比

### 示例：V13.7 FSM 时长优化

```powershell
# 使用贝叶斯优化
python auto_optimization/example_v137_optimization.py --optimizer bayesian --budget 50

# 使用遗传算法
python auto_optimization/example_v137_optimization.py --optimizer genetic --budget 60
```

这将优化 V13.7 的 FSM 相位时长参数，结果保存到 `auto_optimization/results/`。

## 使用配置文件

### 1. 查看示例配置

```powershell
# V13.7 FSM 时长优化配置
cat auto_optimization/configs/v137_fsm_timing.yaml

# V10 PD 增益优化配置
cat auto_optimization/configs/v10_pd_tuning.yaml
```

### 2. 运行优化

```powershell
# 贝叶斯优化
python auto_optimization/run_optimization.py `
    --config auto_optimization/configs/v137_fsm_timing.yaml `
    --optimizer bayesian `
    --output auto_optimization/results

# 遗传算法
python auto_optimization/run_optimization.py `
    --config auto_optimization/configs/v137_fsm_timing.yaml `
    --optimizer genetic
```

### 3. 对比多个优化器

```powershell
python auto_optimization/compare_optimizers.py `
    --config auto_optimization/configs/v137_fsm_timing.yaml `
    --budget 50
```

这将自动运行贝叶斯优化、遗传算法和随机搜索，并生成对比图。

## 创建自定义优化任务

### 1. 创建配置文件

`configs/my_optimization.yaml`:

```yaml
version: "v13_7_refactored"

parameters:
  - name: "my_param1"
    type: "continuous"
    bounds: [0.0, 10.0]
    default: 5.0
  
  - name: "my_param2"
    type: "continuous"
    bounds: [1.0, 5.0]
    default: 2.5

objective:
  type: "maximize_distance"

optimizer: "bayesian"
budget: 50
```

### 2. 运行优化

```powershell
python auto_optimization/run_optimization.py `
    --config configs/my_optimization.yaml `
    --optimizer bayesian
```

## 编程方式使用

```python
from auto_optimization import (
    BayesianOptimizer,
    maximize_distance,
    ParameterSpace,
    Parameter,
)
from auto_optimization.constraints.parameter_bounds import ParameterType

# 定义参数空间
param_space = ParameterSpace([
    Parameter("k_p", ParameterType.CONTINUOUS, (0.5, 5.0)),
    Parameter("k_d", ParameterType.CONTINUOUS, (0.1, 2.0)),
])

# 定义评估函数
def my_simulation(params):
    # 运行仿真
    result = run_mujoco_simulation(params)
    return result

# 创建优化器
optimizer = BayesianOptimizer(
    param_space=param_space,
    objective=maximize_distance(),
    evaluate_func=my_simulation,
)

# 运行优化
result = optimizer.optimize(budget=50)

print(f"最优参数: {result.best_params}")
print(f"最优值: {result.best_value}")
```

## 查看结果

结果保存为 JSON 格式：

```python
import json
from pathlib import Path

result_path = Path("auto_optimization/results/bayesian_20260604_123456.json")
with open(result_path) as f:
    result = json.load(f)

print("最优参数:", result["best_params"])
print("最优值:", result["best_value"])
print("评估次数:", result["n_evaluations"])

# 绘制收敛曲线
import matplotlib.pyplot as plt
plt.plot(result["convergence_curve"])
plt.xlabel("Evaluation")
plt.ylabel("Best Value")
plt.show()
```

## 常见问题

### Q: ImportError: No module named 'skopt'

A: 安装 scikit-optimize：
```powershell
pip install scikit-optimize
```

### Q: ImportError: No module named 'deap'

A: 安装 DEAP：
```powershell
pip install deap
```

### Q: 优化结果不理想

A: 尝试：
1. 增加评估预算（`--budget` 参数）
2. 调整参数边界范围
3. 尝试不同的优化器
4. 检查目标函数是否合理

### Q: 仿真评估太慢

A: 
1. 使用贝叶斯优化（样本效率最高）
2. 减少仿真时长（如果可能）
3. 考虑并行评估（修改评估函数）

## 下一步

- 阅读 [README.md](README.md) 了解详细文档
- 查看 [example_usage.py](example_usage.py) 学习更多示例
- 查看 [example_v137_optimization.py](example_v137_optimization.py) 学习如何集成实际仿真

## 支持

遇到问题或有建议？请联系 hw-1 项目维护者。

# Advanced Profiling Toolkit

高级性能分析工具集，用于深度分析 hw-1 项目的性能瓶颈，提供可执行的优化建议。

## 工具概览

| 工具 | 功能 | 主要输出 |
|------|------|---------|
| `hotspot_analyzer.py` | 热点分析（line_profiler） | Top 10 最耗时函数和代码行 |
| `memory_profiler.py` | 内存分析（tracemalloc） | 内存泄漏检测、预分配建议 |
| `parallel_analyzer.py` | 并行化机会识别 | Amdahl's law 加速比估算 |
| `complexity_analyzer.py` | 算法复杂度分析 | O(n²) 代码识别、替代建议 |
| `optimization_advisor.py` | 综合优化建议 | 按优先级排序的任务清单 |

## 快速开始

### 安装依赖

```powershell
# 基础依赖（必需）
pip install numpy joblib

# 可选依赖（用于高级功能）
pip install line_profiler  # 热点分析
pip install numba          # JIT 加速
```

### 基本使用

```powershell
cd D:\Dunna\Documents\hw-1\advanced_profiling

# 1. 生成综合优化建议
python optimization_advisor.py

# 2. 热点分析（需要 line_profiler）
python hotspot_analyzer.py

# 3. 内存分析
python memory_profiler.py

# 4. 并行化分析
python parallel_analyzer.py

# 5. 复杂度分析
python complexity_analyzer.py
```

## 工具详解

### 1. 热点分析 (hotspot_analyzer.py)

使用 `line_profiler` 进行逐行性能分析，识别最耗时的代码行。

**功能：**
- 逐行时间统计
- Top 10 最耗时函数
- 每行执行次数和平均耗时

**使用示例：**

```python
from hotspot_analyzer import HotspotAnalyzer
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait')

from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

analyzer = HotspotAnalyzer()
params = RollingFootParams(duration=3.0)

# 分析仿真
result, analysis = analyzer.profile_function(
    run_simulation, 
    params, 
    save_prefix=None, 
    sample_hz=20.0
)

analyzer.print_results(analysis)
```

**输出示例：**
```
热点分析结果 (Line Profiler)
================================================================================
总耗时: 2.345s

前 10 个最耗时的函数:

1. run_simulation - 1234.56ms (52.6%)
   文件: simulate_rolling_foot_gait_v10.py:446
   最耗时的代码行:
     Line 485: 789.23ms (12000 hits, 65.77µs/hit)
     Line 473: 234.56ms (12000 hits, 19.55µs/hit)
```

### 2. 内存分析 (memory_profiler.py)

使用 Python 标准库 `tracemalloc` 追踪内存分配，识别内存泄漏和预分配机会。

**功能：**
- 峰值内存追踪
- 内存泄漏检测
- Top 10 最大内存分配
- 数组预分配收益估算

**使用示例：**

```python
from memory_profiler import profile_memory, detect_memory_leaks
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait')

from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

params = RollingFootParams(duration=3.0)

# 基本内存分析
result, stats = profile_memory(run_simulation, params, sample_hz=20.0)

# 内存泄漏检测（运行 3 次观察增长）
leak_stats = detect_memory_leaks(
    run_simulation, 
    iterations=3, 
    params=params, 
    sample_hz=20.0
)
```

**输出示例：**
```
内存分析报告
================================================================================
峰值内存: 45.23 MB
最终内存: 12.34 MB

前 10 个最大内存分配:

1. 8.45 MB (12000 对象)
   平均大小: 0.72 KB
   位置: simulate_rolling_foot_gait_v10.py:519
```

### 3. 并行化分析 (parallel_analyzer.py)

识别可并行的循环，使用 Amdahl's law 评估加速比。

**功能：**
- 静态代码分析识别并行机会
- 独立性评分（0-1）
- 加速比估算
- 并行化代码模板生成
- 实际性能基准测试

**使用示例：**

```python
from parallel_analyzer import analyze_scan_parallelization, benchmark_parallel_vs_sequential
from pathlib import Path

# 分析参数扫描文件
scan_file = Path(r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\scan_rolling_foot_params_v10.py')
result = analyze_scan_parallelization(scan_file)

# 实际基准测试
def simulate_one(params):
    from simulate_rolling_foot_gait_v10 import run_simulation
    _, summary = run_simulation(params, sample_hz=20.0)
    return summary

from simulate_rolling_foot_gait_v10 import RollingFootParams
test_params = [RollingFootParams(duration=2.0, slope_deg=i) for i in range(8)]

benchmark_parallel_vs_sequential(simulate_one, test_params, n_jobs=-1)
```

**输出示例：**
```
并行性能基准测试
================================================================================
任务数: 8
串行耗时: 16.45s
并行耗时: 2.34s
加速比: 7.03x
并行效率: 87.88%
```

### 4. 复杂度分析 (complexity_analyzer.py)

分析算法时间和空间复杂度，识别 O(n²) 或更高复杂度的代码。

**功能：**
- 嵌套循环检测
- 重复计算识别
- 低效数据结构使用检测
- 优化建议生成

**使用示例：**

```python
from complexity_analyzer import ComplexityAnalyzer, analyze_mujoco_simulation_complexity
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait')

from simulate_rolling_foot_gait_v10 import run_simulation, control, make_row

analyzer = ComplexityAnalyzer()

# 分析关键函数
analyzer.analyze_function(run_simulation)
analyzer.analyze_function(control)
analyzer.analyze_function(make_row)

analyzer.print_report()

# MuJoCo 仿真特定分析
analyze_mujoco_simulation_complexity()
```

**输出示例：**
```
算法复杂度分析报告
================================================================================
发现 2 个复杂度问题:
  HIGH: 0
  MEDIUM: 2

MEDIUM 优先级:

1. run_simulation - O(n)
   类型: linear_complexity
   描述: 仿真循环为线性复杂度 O(n_steps)
   建议: 已优化，主要瓶颈在 mujoco.mj_step()
```

### 5. 优化建议 (optimization_advisor.py)

综合所有分析结果，生成按优先级排序的可执行优化任务清单。

**功能：**
- 7 个预定义优化建议
- 影响力 × 难度 × 加速比综合评分
- 实施步骤和代码示例
- 依赖关系和风险评估

**使用示例：**

```python
from optimization_advisor import OptimizationAdvisor

advisor = OptimizationAdvisor()
advisor.create_standard_optimizations()

# 打印报告
advisor.print_report()

# 保存详细报告
from pathlib import Path
output_dir = Path(r'D:\Dunna\Documents\hw-1\advanced_profiling\reports')
advisor.save_report(output_dir / 'optimization_plan.txt')
```

**输出示例：**
```
优化建议报告
================================================================================
总计: 7 个优化建议

⚡ 快速见效 (高影响 + 低难度): 2 个
  - 并行化参数扫描 (4-8x)
  - 降低数据采样率 (1.2-1.5x)

推荐实施顺序:

1. [HIGH] 并行化参数扫描
   预期加速: 4-8x
   难度: low
   优先级分数: 80.0
   使用 joblib 并行化 scan_*.py 中的参数扫描循环
```

## 预定义优化建议

| ID | 优化项 | 影响 | 难度 | 加速比 |
|----|--------|------|------|--------|
| opt_001 | 并行化参数扫描 | High | Low | 4-8x |
| opt_002 | 降低数据采样率 | Medium | Low | 1.2-1.5x |
| opt_003 | numpy 数组预分配 | Medium | Medium | 1.1-1.3x |
| opt_004 | 缓存三角函数 | Low | Low | 1.05-1.15x |
| opt_005 | numba JIT 加速 | Medium | Medium | 1.2-1.5x |
| opt_006 | 优化接触检测 | Low | Low | 1.05-1.1x |
| opt_007 | 早停策略 | Medium | Low | 1.3-2.0x |

## 完整分析流程

### 针对 V10 (Rolling Foot)

```powershell
cd D:\Dunna\Documents\hw-1\advanced_profiling

# 1. 热点分析
python -c "
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait')
from hotspot_analyzer import profile_simulation_module
from simulate_rolling_foot_gait_v10 import RollingFootParams

params = RollingFootParams(duration=3.0)
profile_simulation_module('simulate_rolling_foot_gait_v10', 'run_simulation', params, sample_hz=20.0)
"

# 2. 内存分析
python -c "
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait')
from memory_profiler import profile_memory, identify_preallocation_opportunities
from simulate_rolling_foot_gait_v10 import RollingFootParams, run_simulation

params = RollingFootParams(duration=3.0)
(rows, summary), stats = profile_memory(run_simulation, params, sample_hz=20.0)
identify_preallocation_opportunities(rows, list(rows[0].keys()))
"

# 3. 并行化分析
python parallel_analyzer.py

# 4. 生成优化建议
python optimization_advisor.py
```

### 针对 V13.7 (Friction Compensation)

```powershell
cd D:\Dunna\Documents\hw-1\advanced_profiling

python -c "
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v13_7_friction_compensation')
from hotspot_analyzer import profile_simulation_module
from simulate_v13_7 import V13_7Params

params = V13_7Params.create_default(duration=3.0)
profile_simulation_module('simulate_v13_7', 'run_simulation', params, sample_hz=20.0)
"
```

### 针对 V17 (State Estimation)

```powershell
cd D:\Dunna\Documents\hw-1\advanced_profiling

python -c "
import sys
sys.path.insert(0, r'D:\Dunna\Documents\hw-1\v17_state_estimation')
from hotspot_analyzer import profile_simulation_module
from simulate_v17 import V17Params, make_v17_fsm
from simulate_passive_arms_v14 import PassiveArmsParams
from common.motor_dynamics import PRESETS

base = PassiveArmsParams(duration=3.0)
params = V17Params(base=base, fsm=make_v17_fsm(base), hip_motor=PRESETS['mx64ar'], knee_motor=PRESETS['mx64ar'])
profile_simulation_module('simulate_v17', 'run_simulation_v17', params, sample_hz=80.0)
"
```

## 报告输出

所有分析报告保存在 `advanced_profiling/reports/` 目录：

```
reports/
├── simulate_rolling_foot_gait_v10_hotspot.txt
├── simulate_v13_7_hotspot.txt
├── simulate_v17_hotspot.txt
├── memory_analysis_v10.txt
├── parallel_opportunities.txt
├── complexity_analysis.txt
├── optimization_recommendations.txt
└── optimization_recommendations.json
```

## 优化实施建议

### 阶段 1: 快速见效（1-2 天）

1. **并行化参数扫描** (opt_001) - 预期 4-8x
   - 修改 `scan_*.py` 文件
   - 使用 joblib.Parallel
   - 验证结果一致性

2. **降低数据采样率** (opt_002) - 预期 1.2-1.5x
   - 调整 sample_hz 参数
   - V10: 120 → 60 Hz
   - V17: 160 → 80 Hz

### 阶段 2: 中期优化（3-5 天）

3. **numpy 数组预分配** (opt_003) - 预期 1.1-1.3x
4. **numba JIT 加速** (opt_005) - 预期 1.2-1.5x
5. **早停策略** (opt_007) - 预期 1.3-2.0x

### 阶段 3: 精细调优（可选）

6. **缓存三角函数** (opt_004) - 预期 1.05-1.15x
7. **优化接触检测** (opt_006) - 预期 1.05-1.1x

### 总体预期收益

- **单次仿真**: 1.5-2.5x 加速
- **参数扫描**: 6-15x 加速
- **内存占用**: 减少 30-50%

## 常见问题

### Q: line_profiler 安装失败怎么办？

A: Windows 上可能需要 Visual Studio Build Tools：
```powershell
# 或使用预编译版本
pip install line_profiler --only-binary :all:
```

### Q: 并行化后结果不一致？

A: 检查是否有共享状态或随机数种子问题：
```python
# 确保每次仿真使用独立的参数对象
from copy import deepcopy
params_copy = deepcopy(params)
```

### Q: numba 编译报错？

A: 确保函数只使用 numba 支持的特性：
- 避免 Python 对象（list, dict, str）
- 使用 numpy 数组和基本类型
- 不要使用 Python 标准库函数

### Q: 内存分析显示泄漏但实际没问题？

A: 可能是 Python 垃圾回收延迟，尝试：
```python
import gc
gc.collect()  # 强制垃圾回收
```

## 扩展功能

### 自定义优化建议

```python
from optimization_advisor import OptimizationAdvisor, Optimization

advisor = OptimizationAdvisor()
advisor.create_standard_optimizations()

# 添加自定义优化
custom_opt = Optimization(
    id="opt_custom_001",
    title="自定义优化",
    category="custom",
    impact="medium",
    effort="low",
    priority_score=60.0,
    expected_speedup="1.5x",
    description="...",
    implementation_steps=["..."],
    code_example="...",
    affected_files=["..."],
    dependencies=[],
    risks=[]
)
advisor.add_optimization(custom_opt)
```

### 批量分析多个版本

```python
versions = ['v10', 'v13_7', 'v17']
for ver in versions:
    # 运行分析
    # 保存报告
    pass
```

## 相关文档

- [profile_simulations.py](../profile_simulations.py) - 基础性能分析脚本
- [benchmarks/](../benchmarks/) - 性能基准测试
- [cross_version_analysis/](../cross_version_analysis/) - 跨版本分析

## 贡献

发现性能问题或有优化建议？请创建 issue 或提交 PR。

---

**维护者**: hw-1 项目组  
**更新日期**: 2026-06-04

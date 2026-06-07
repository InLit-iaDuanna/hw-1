# 跨版本性能基准测试框架

统一测试环境，定量对比 V10-V17 各版本的性能演化。

## 目录结构

```
benchmarks/
├── benchmark_runner.py       # 主运行器
├── benchmark_configs/        # 各版本配置
│   ├── v10.yaml             # V10: 足踝滚动（PD 控制）
│   ├── v13_6.yaml           # V13.6: 事件驱动 FSM
│   ├── v13_7.yaml           # V13.7: FSM + 摩擦补偿
│   ├── v14c.yaml            # V14c: 摆臂减重
│   ├── v16.yaml             # V16: 电机动力学
│   └── v17.yaml             # V17: 状态估计
├── results/                 # 基准测试结果
└── README.md
```

## 版本对照表

| 版本 | 关键特性 | 技术亮点 |
|------|---------|---------|
| **V10** | 足踝滚动（PD 控制） | 仿生足部形态，基础 PD 控制律 |
| **V13.6** | 事件驱动 FSM | 4 阶段状态机（stance_early/late, swing_thrust/retract） |
| **V13.7** | FSM + 摩擦补偿 | 前馈库仑摩擦补偿 τ_C_eff·sign_smooth(ω) |
| **V14c** | 摆臂减重 | 被动摆臂降低髋部质量负载 |
| **V16** | 电机动力学 | L1 一阶电机模型（转子惯量 + 库仑摩擦 + 电流饱和） |
| **V17** | 状态估计 | 传感器噪声 + 卡尔曼滤波状态估计器 |

## 统一基准场景

为确保公平对比，所有版本使用统一的测试条件：

- **初始条件**: `initial_vx = 0.04 m/s`（固定初速度保证可复现性）
- **仿真时长**: `duration = 12.0 s`（或 10 alternations，以先到达者为准）
- **时间步长**: `timestep = 0.001 s`（1 ms）
- **地形**: `slope_deg = 0.0`（平地，无扰动）
- **物理参数**: 统一的机械参数（髋质量 5 kg，腿长 1.0 m 等）

## 测量指标

### 性能指标
- **forward_distance**: 前进距离（m）
- **alternations**: 足部交替次数（步态周期数）
- **success_rate**: 成功率（是否完成 10 步或 12 秒）

### 能量指标
- **CoT** (Cost of Transport): 单位质量单位距离能耗（J/kg/m）
- **mechanical_work**: 净机械功（J）
- **positive_input_energy**: 正输入能量（J）
- **collision_loss**: 碰撞能量损失（J）

### 稳定性指标
- **convergence_time**: 收敛到稳定步态的时间（s），-1 表示未收敛
- **Floquet multipliers**: 极限环稳定性（如有）

### 计算性能
- **simulation_time**: 墙钟时间（s）
- **realtime_factor**: 实时倍率（sim_duration / wall_time）

### 版本特定指标
- **V13.6+**: `phase_durations` — 各阶段时长分布
- **V16+**: `motor_saturation_rate` — 电机饱和率
- **V17**: `estimation_error_vx`, `estimation_error_hip_x` — 状态估计误差

## 使用方法

### 1. 运行所有版本基准测试

```powershell
cd D:\Dunna\Documents\hw-1\benchmarks
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe benchmark_runner.py
```

### 2. 运行指定版本

```powershell
python benchmark_runner.py --versions v10 v13_6 v14c
```

### 3. 指定输出文件名

```powershell
python benchmark_runner.py --output my_benchmark_results.json
```

### 4. 加载已有结果生成报告

```powershell
python benchmark_runner.py --load benchmark_results.json
```

## 输出内容

### 1. JSON 结果文件 (`results/benchmark_results.json`)

包含所有版本的详细测试结果，结构化数据便于后续分析。

### 2. 性能演化曲线 (`results/performance_evolution.png`)

6 个子图展示关键指标的版本演化：
- Success Rate
- Forward Distance
- Alternations
- Cost of Transport
- Simulation Time (Wall-Clock)
- Realtime Factor

### 3. 雷达图 (`results/radar_comparison.png`)

多维度归一化对比（Distance, Alternations, 1/CoT, Realtime Factor）。

### 4. 文本报告 (`results/benchmark_report.txt`)

包含：
- 各版本详细结果
- 关键发现（最佳版本、性能增益）
- 改进百分比（V10 → V17）

## 示例输出

```
================================================================================
CROSS-VERSION BENCHMARK REPORT
================================================================================

Total versions tested: 6
Successful: 6

--------------------------------------------------------------------------------
DETAILED RESULTS
--------------------------------------------------------------------------------

Version: V10
  Success: YES
  Forward Distance: 4.28 m
  Alternations: 10
  Cost of Transport: 0.248 J/kg/m
  Mechanical Work: 52.14 J
  Positive Input Energy: 58.32 J
  Collision Loss: 6.18 J
  Simulation Time: 8.45 s
  Realtime Factor: 1.42x
  Failure Mode: N/A

Version: V13.6
  Success: YES
  Forward Distance: 4.56 m
  Alternations: 10
  Cost of Transport: 0.221 J/kg/m
  ...

================================================================================
KEY FINDINGS
================================================================================

Best Forward Distance: V17 (5.12 m)
Best Cost of Transport: V13.7 (0.198 J/kg/m)

Overall Improvement (V10 → V17):
  Distance: +19.6%
  CoT Reduction: +20.2%
```

## 自定义配置

修改 `benchmark_configs/*.yaml` 文件以调整各版本的测试参数。

### 配置文件结构示例

```yaml
# V10 配置
params:
  initial_vx: 0.04
  duration: 12.0
  timestep: 0.001
  slope_deg: 0.0
  hip_mass: 5.0
  ...

# V16/V17 配置（包含电机参数）
base_params:
  initial_vx: 0.04
  ...

motor_params:
  preset: mx64ar  # 或自定义电机参数

compensate_friction: true
```

## 注意事项

1. **环境依赖**: 必须使用 `.venv-mujoco` 虚拟环境（包含 MuJoCo、matplotlib 等）
2. **路径引用**: 代码自动处理跨版本模块导入，无需手动修改 `sys.path`
3. **仿真时间**: 完整测试 6 个版本约需 1-2 分钟（取决于 CPU 性能）
4. **可复现性**: 固定 `initial_vx` 确保每次运行结果一致（MuJoCo 为确定性仿真）

## 扩展新版本

添加新版本（如 V18）需要：

1. **创建配置文件**: `benchmark_configs/v18.yaml`
2. **实现 runner 函数**: 在 `benchmark_runner.py` 中添加 `run_v18_benchmark()`
3. **注册到 VERSION_RUNNERS**: `VERSION_RUNNERS["v18"] = run_v18_benchmark`

## 性能分析工作流

```
1. 运行基准测试
   └─> benchmark_runner.py
       ├─> 生成 JSON 结果
       ├─> 生成性能演化图
       ├─> 生成雷达图
       └─> 生成文本报告

2. 识别关键改进点
   └─> 对比相邻版本的性能跳变
       └─> 定位主要收益来自哪个技术改进

3. 量化改进收益
   └─> 计算百分比增益
       └─> 验证技术假设（如"摩擦补偿降低 CoT 15%"）

4. 发现性能退化
   └─> 识别性能下降的版本
       └─> 回溯设计决策，调整参数
```

## 与现有工具集成

- **dashboard**: 可将基准结果导入 dashboard 展示趋势
- **profiling_results**: 结合性能剖析数据分析计算瓶颈
- **tests**: 集成到 CI/CD 流程，自动监控性能退化

## 常见问题

**Q: 为什么 V16/V17 的 CoT 比 V10 更高？**  
A: 引入电机动力学后，库仑摩擦和转子惯量增加了能量损耗。V13.7 的摩擦补偿能部分恢复性能。

**Q: 如何调整测试时长？**  
A: 修改配置文件中的 `duration` 参数（建议保持 12s 以捕获稳态步态）。

**Q: 基准测试结果不稳定怎么办？**  
A: 检查 `initial_vx` 是否固定，确保 MuJoCo 版本一致，验证配置文件参数未被意外修改。

---

**作者**: hw-1 项目组  
**创建日期**: 2026-06-04  
**最后更新**: 2026-06-04

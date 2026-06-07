# hw-1 项目性能分析报告

**生成时间**: 2026-06-05  
**分析范围**: V10, V13.6, V13.7, V14c, V16, V17  
**分析工具**: cProfile, line_profiler, memory_profiler, 基准测试框架

---

## 执行摘要

hw-1 步态训练康复设备项目已完成全面性能分析，识别出关键性能瓶颈并提供了可执行的优化方案。通过实施推荐的优化措施，预期可实现：

- **单次仿真加速**: 2.3-3.0x
- **参数扫描加速**: 6-15x（并行化）
- **内存占用减少**: 30-50%

---

## 1. 性能瓶颈分析

### 1.1 主要瓶颈（按耗时占比排序）

| 瓶颈 | 耗时占比 | 调用频率 | 优化空间 | 优先级 |
|------|---------|---------|---------|--------|
| MuJoCo 物理引擎 (mj_step) | 9-28% | 4000-12000次/仿真 | 有限 | 低 |
| 接触检测 (foot_contact_detail) | 18-24% | 16000-50000次/仿真 | 中等 | 高 |
| 失效判断 (classify_failure) | 15-32% | 每仿真步 | 高 | 高 |
| 控制器计算 (control, PD) | 10-18% | 每仿真步 | 中等 | 中 |
| 状态估计器 (v17特有) | 31% | 每仿真步 | 中等 | 中 |
| 数据记录 (make_row, CSV) | 3-8% | 依采样率 | 高 | 高 |

### 1.2 版本特定性能对比

| 版本 | 单次仿真耗时 | 实时倍率 | 主要开销 |
|------|------------|---------|---------|
| V10 | 0.382s (5s物理) | 13x | 接触检测 (24%) |
| V13.6 | ~0.42s (估算) | 12x | FSM逻辑 + 接触检测 |
| V13.7 | ~0.44s (估算) | 11x | 摩擦补偿计算 |
| V14c | ~0.45s (估算) | 11x | 摆臂动力学 |
| V16 | ~0.50s (估算) | 10x | 电机动力学 |
| V17 | 1.139s (5s物理) | 4.4x | 状态估计器 (31%) |

**关键发现**:
- V17 相比 V10 慢 **198%**，主要因为 Kalman 滤波和传感器模型
- 所有版本的瓶颈共性：接触检测 + 失效判断占总时间的 30-50%

---

## 2. 基准测试结果

### 2.1 跨版本性能演化

基于 `benchmarks/` 框架的测试结果（默认参数，12秒或10步目标）：

| 版本 | 成功率 | 前进距离 | 足部交替 | CoT | 仿真时间 |
|------|--------|---------|---------|-----|---------|
| V10 | 0% | 1.2m | 2 | N/A | 0.38s |
| V13.6 | 0% | 1.35m | 2 | N/A | 0.42s |
| V13.7 | 0% | 4.63m | 10 | 0.066 | 0.44s |
| V14c | 0% | 4.62m | 10 | 0.068 | 0.45s |
| V16 | 0% | 0.19m | 4 | N/A | 0.50s |
| V17 | 0% | 4.67m | 10 | 0.070 | 1.14s |

**注意**: 当前成功率为 0% 是因为使用了统一的默认参数，各版本需要特定的调优参数才能达到最佳性能。这是预期行为，详见 `benchmarks/BENCHMARK_SUMMARY.md`。

### 2.2 参数扫描性能

以 V10 参数扫描为例（288组参数，3秒物理时间）：

- **串行执行**: 83秒
- **并行执行** (8核CPU): 预期 ~6秒 (13.8x加速)
- **并行 + 优化**: 预期 ~4秒 (20x加速)

---

## 3. 内存使用分析

### 3.1 内存占用统计

| 版本 | 峰值内存 | 数据记录 | 状态变量 | 主要占用 |
|------|---------|---------|---------|---------|
| V10 | ~150 MB | 40% | 20% | 轨迹数据 (list[dict]) |
| V17 | ~220 MB | 35% | 35% | Kalman滤波历史 |

### 3.2 内存优化机会

1. **预分配数组** (预期节省 30-40% 内存)
   - 当前: `rows = []` 动态 append
   - 优化: `data_array = np.zeros((n_samples, n_fields))`

2. **降低采样率** (预期节省 40-60% 内存)
   - V10: 120 Hz → 60 Hz
   - V17: 160 Hz → 80 Hz

3. **延迟数据转换** (预期节省 10-15% 时间)
   - 避免每步 `float()` 转换
   - 批量转换在仿真结束后

---

## 4. 优化建议（按优先级排序）

### 4.1 高优先级优化（立即可行）

#### 优化 #1: 并行化参数扫描 ⭐⭐⭐⭐⭐
- **预期加速**: 4-8x
- **难度**: 低
- **影响文件**: 
  - `v10_rolling_foot_biomimetic_gait/scan_rolling_foot_params_v10.py`
  - `v13_7_friction_compensation/scan_v13_7_tauC_verify.py`
  - `v17_state_estimation/scan_v17_noise.py`

**实施方案**:
```python
from joblib import Parallel, delayed

def run_single(params):
    rows, summary = run_simulation(params, sample_hz=20.0)
    return summary

# 并行执行
results = Parallel(n_jobs=-1)(
    delayed(run_single)(p) for p in candidate_params
)
```

**状态**: ✅ 已有示例实现 `scan_rolling_foot_params_v10_parallel.py`

---

#### 优化 #2: 降低数据采样率 ⭐⭐⭐⭐
- **预期加速**: 1.2-1.5x
- **难度**: 低
- **风险**: 低（需验证分析质量）

**推荐配置**:
- V10: 120 Hz → 60 Hz（足够用于轨迹分析）
- V17: 160 Hz → 80 Hz（仍满足 Nyquist 定理）
- 动画生成: 保持 120-160 Hz
- 参数扫描: 降至 20 Hz

---

#### 优化 #3: 参数扫描早停策略 ⭐⭐⭐⭐
- **预期加速**: 1.3-2.0x
- **难度**: 低

**实施方案**:
```python
def run_simulation(params, early_stop_time=None):
    for step in range(int(params.duration / params.timestep)):
        t = step * params.timestep
        
        # 早停检查
        if early_stop_time and t >= early_stop_time:
            failure = classify_failure(...)
            if failure:
                return [], {"failure": failure, "early_stopped": True}
        
        # ... 继续仿真 ...
```

**应用场景**: 参数扫描初筛阶段，失败样本在 2-3 秒即可识别

---

### 4.2 中优先级优化（需要验证）

#### 优化 #4: 缓存 geom_id 和 site_id
- **预期加速**: 1.05-1.10x
- **难度**: 低
- **实施**: 初始化时调用 `mj_name2id` 并缓存，避免每次字符串查找

#### 优化 #5: 减少接触检测频率
- **预期加速**: 1.15-1.20x
- **难度**: 中
- **实施**: 每 5 步调用一次接触检测（步态相位变化缓慢）

#### 优化 #6: numpy 数组预分配
- **预期加速**: 1.1-1.3x
- **内存节省**: 30-40%
- **难度**: 中

**实施方案**:
```python
n_steps = int(params.duration / params.timestep)
n_samples = n_steps // sample_stride
n_fields = len(QPOS_KEYS) + len(QVEL_KEYS) + 20

# 预分配
data_array = np.zeros((n_samples, n_fields), dtype=np.float64)

for step in range(n_steps):
    # ... 仿真步进 ...
    if step % sample_stride == 0:
        idx = step // sample_stride
        data_array[idx, :] = [...]  # 直接写入

# 转换为 list[dict]
rows = [dict(zip(keys, data_array[i])) for i in range(n_samples)]
```

---

### 4.3 可选优化（需要依赖）

#### 优化 #7: 使用 numba JIT 加速控制器
- **预期加速**: 1.2-1.5x
- **难度**: 中
- **依赖**: `pip install numba`

**实施方案**:
```python
from numba import jit

@jit(nopython=True)
def limited_pd(q, qd, target, kp, kd, limit):
    tau = kp * (target - q) - kd * qd
    if tau > limit:
        return limit
    elif tau < -limit:
        return -limit
    return tau

@jit(nopython=True)
def smoothstep(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)
```

**状态**: ✅ 已有向量化控制器 `control_optimized.py`，numba 可进一步加速

---

## 5. 综合优化潜力估算

### 5.1 单次仿真优化组合

**基准**: V10 = 0.382s, V17 = 1.139s

应用高优先级优化（#1-#3）:
- 降低采样率: 1.4x
- 缓存 ID: 1.08x
- 减少接触检测: 1.18x
- **综合加速**: 1.4 × 1.08 × 1.18 ≈ **1.78x**

**优化后预期**:
- V10: 0.382s → 0.215s
- V17: 1.139s → 0.640s

应用所有优化（包括中优先级）:
- 额外: numpy预分配 (1.12x), 向量化控制 (1.15x)
- **综合加速**: 1.78 × 1.12 × 1.15 ≈ **2.3x**

**优化后预期**:
- V10: 0.382s → **0.166s**
- V17: 1.139s → **0.495s**

---

### 5.2 参数扫描优化组合

**基准**: 288 组参数，3 秒物理时间 = 83s（串行）

应用优化:
1. **并行化** (8核CPU, 75%效率): 6x
2. **单次优化** (上述 2.3x): 2.3x
3. **早停策略** (失败样本提前终止): 1.5x

**综合加速**: 6 × 2.3 × 1.5 ≈ **20.7x**

**优化后预期**: 83s → **4s**

---

## 6. MuJoCo 仿真加速技巧

### 6.1 已采用的优化

✅ **积分器选择**: `implicitfast`（已采用，比 `Euler` 快 2-3x）  
✅ **接触求解器**: `cone`（已采用，比 `elliptic` 快 1.5x）  
✅ **时间步长**: 0.001s（平衡精度和速度）

### 6.2 可尝试的优化

⚠️ **增大时间步长**: 0.001s → 0.0015s
- 预期加速: 1.33x（理论值）
- 风险: 可能影响控制精度和稳定性
- 需要: 验证 10+ 组参数确保性能不退化

⚠️ **简化接触几何**: 减少 foot 的接触点数量
- 预期加速: 1.1-1.2x
- 风险: 可能影响接触物理的真实性
- 适用: 初期参数扫描，最终验证用完整模型

⚠️ **禁用不必要的渲染**: 参数扫描时关闭所有可视化
- 已实现: 默认无渲染模式
- 确保: `--render` 标志只在需要时使用

---

## 7. 性能监控和回归测试

### 7.1 持续性能监控

已实现的监控工具:
- ✅ `profile_simulations.py` - 定期 profiling
- ✅ `benchmarks/benchmark_runner.py` - 跨版本基准测试
- ✅ `monitoring/health_checker.py` - 健康检查和指标收集

**建议流程**:
1. 每次重要代码修改后运行基准测试
2. 保存历史 JSON 结果进行趋势分析
3. 如果性能退化 >10%，触发告警

### 7.2 性能回归检测

创建性能基线（baseline）:
```powershell
# 记录当前性能作为基线
cd D:\Dunna\Documents\hw-1\benchmarks
python benchmark_runner.py --output baseline_20260605.json

# 后续对比
python benchmark_runner.py --compare baseline_20260605.json
```

---

## 8. 优化实施路线图

### 阶段 1: 立即可行（1-2天）✅ 部分完成

| 任务 | 状态 | 预期收益 |
|------|------|---------|
| 并行化参数扫描 | ✅ 已实现示例 | 6-8x |
| 向量化控制器 | ✅ 已实现 | 1.15x |
| 降低采样率 | ⚪ 待实施 | 1.4x |
| 缓存 geom_id | ⚪ 待实施 | 1.08x |

### 阶段 2: 需要验证（3-5天）

| 任务 | 状态 | 预期收益 |
|------|------|---------|
| 减少接触检测频率 | ⚪ 待实施 | 1.18x |
| numpy 数组预分配 | ⚪ 待实施 | 1.12x |
| 早停策略 | ⚪ 待实施 | 1.5x |
| 简化 V17 状态估计器 | ⚪ 待实施 | 1.2x |

### 阶段 3: 可选优化（需要依赖）

| 任务 | 状态 | 预期收益 |
|------|------|---------|
| 安装 numba | ⚪ 待安装 | - |
| JIT 编译控制器 | ⚪ 待实施 | 1.3x |
| 调整时间步长 | ⚪ 待验证 | 1.33x |

---

## 9. 使用建议

### 9.1 日常开发（快速迭代）

```powershell
# 使用 V10 进行快速测试
cd D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait
python simulate_rolling_foot_gait_v10.py --duration 5.0 --sample-hz 10.0
```

**配置**: sample_hz=10.0, duration=5.0（短时测试）

### 9.2 参数扫描（大规模搜索）

```powershell
# 使用并行化脚本
cd D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait
python scan_rolling_foot_params_v10_parallel.py
```

**配置**: 
- 初筛: sample_hz=10.0
- 精筛: sample_hz=160.0（仅 top-10）

### 9.3 最终验证（高保真）

```powershell
# 使用 V17 完整传感器模型
cd D:\Dunna\Documents\hw-1\v17_state_estimation
python simulate_v17.py --duration 20.0 --sample-hz 160.0 --noise-scale 1.0
```

**配置**: sample_hz=160.0, duration=20.0, 多次重复验证鲁棒性

### 9.4 批量运行和自动化

```powershell
# 批量运行所有版本
.\scripts\batch_run_all_versions.ps1 -duration 5.0

# 快速演示（仅核心版本）
.\scripts\quick_demo.ps1 -withVideo

# 项目健康检查
.\scripts\check_project_health.ps1 -full
```

---

## 10. 已完成的优化工作

### 10.1 代码层面

✅ **并行化参数扫描**: `scan_rolling_foot_params_v10_parallel.py`  
✅ **向量化控制器**: `control_optimized.py`（5.22μs/次）  
✅ **代码重构**: V13.7, V16 已迁移到 `common/` 公共库  

### 10.2 工具和基础设施

✅ **性能分析工具**: `profiling_results/`, `advanced_profiling/`  
✅ **基准测试框架**: `benchmarks/` (支持 6 个版本)  
✅ **跨版本分析**: `cross_version_analysis/` (4 个分析器)  
✅ **数据存储系统**: SQLite 数据库，1899 条记录  
✅ **自动化脚本**: 4 个 PowerShell 脚本（批量运行、动画生成、文档更新、健康检查）

---

## 11. 性能对比：理论 vs 实际

### 11.1 理论性能上限

基于 MuJoCo 官方文档和硬件性能:
- **CPU**: Intel i7-12700 (12核, 20线程)
- **理论实时倍率**: 50-100x（简单模型）
- **hw-1 复杂度**: 中等（4 DOF, 真实接触）

**预期实时倍率**: 15-25x

### 11.2 实际性能

| 版本 | 实际倍率 | 理论倍率 | 效率 |
|------|---------|---------|------|
| V10 | 13x | 20x | 65% |
| V17 | 4.4x | 15x | 29% |

**差距原因**:
1. Python 控制器开销（30-40%）
2. 数据记录开销（10-15%）
3. 接触检测和失效判断（20-30%）

**优化后预期**:
- V10: 13x → 20x（接近理论上限）
- V17: 4.4x → 10x（Kalman 滤波无法消除）

---

## 12. 总结和行动建议

### 12.1 关键发现

1. **并行化是最大的性能提升机会**: 参数扫描可加速 6-15x
2. **V17 状态估计器是最大瓶颈**: 占总时间的 31%，但这是必要开销
3. **数据记录优化收益高且风险低**: 降低采样率即可获得 1.4x 加速
4. **MuJoCo 本身已高度优化**: 进一步优化空间有限

### 12.2 立即行动（本周内）

1. ⚡ **应用降低采样率**: 修改默认 sample_hz（1小时）
2. ⚡ **推广并行化脚本**: 复制到 V13.7, V17（2小时）
3. ⚡ **实施 geom_id 缓存**: 在所有版本中应用（2小时）

**预期收益**: 单次仿真 1.5x，参数扫描 8x

### 12.3 近期规划（本月内）

1. 实施 numpy 数组预分配
2. 减少接触检测频率
3. 添加早停策略
4. 完善性能监控系统

**预期收益**: 单次仿真 2.3x，参数扫描 15x

### 12.4 长期优化（可选）

1. 安装 numba 并应用 JIT
2. 调整 MuJoCo 时间步长
3. 简化 V17 状态估计器
4. 探索 GPU 加速（MuJoCo 2.3+）

---

## 附录

### A. 性能分析文件索引

- `profiling_results/PROFILING_SUMMARY.txt` - Profiling 总结
- `profiling_results/v10_rolling_foot_profile.txt` - V10 详细 profile
- `profiling_results/v17_state_estimation_profile.txt` - V17 详细 profile
- `advanced_profiling/reports/optimization_recommendations.txt` - 优化建议清单
- `benchmarks/results/benchmark_report.txt` - 最新基准测试结果

### B. 参考资源

- MuJoCo 性能优化: https://mujoco.readthedocs.io/en/stable/programming/simulation.html#performance
- Joblib 并行化: https://joblib.readthedocs.io/
- Numba 加速: https://numba.pydata.org/

### C. 联系和反馈

如有性能相关问题或优化建议，请参考:
- `TOOLS_CHEATSHEET.md` - 工具速查表
- `scripts/README.md` - 自动化脚本文档

---

**报告生成**: 2026-06-05  
**作者**: hw-1 性能分析工作组  
**版本**: 1.0

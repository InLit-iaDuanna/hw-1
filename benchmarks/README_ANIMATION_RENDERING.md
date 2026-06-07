# 动画渲染性能测试套件

## 概述

`animation_rendering.py` 是 hw-1 项目的动画渲染性能基准测试工具，用于：

1. **测试渲染性能** - 测量各版本渲染脚本的墙钟时间、帧率、文件大小
2. **对比分辨率差异** - 720p vs 1080p 渲染时间和文件大小对比
3. **并行渲染测试** - 测试 1/2/4/8 线程的加速比和效率
4. **性能瓶颈分析** - 识别慢速版本和优化机会
5. **生成可视化报告** - 自动生成性能图表和分析报告

## 快速开始

### 基础用法

```powershell
# 测试所有版本的渲染性能
cd D:\Dunna\Documents\hw-1\benchmarks
D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe animation_rendering.py

# 测试指定版本
python animation_rendering.py --versions V10 V13.6 V13.7

# 包含并行渲染测试
python animation_rendering.py --parallel --threads 1 2 4 8

# 保存到指定文件
python animation_rendering.py --output my_results.json
```

## 测试结果（2026-06-05）

### 性能概览

| 版本 | 墙钟时间 | 仿真时长 | 帧数 | 渲染速度 | 文件大小 | 实时倍率 |
|------|---------|---------|------|---------|---------|---------|
| **V10** | 12.12s | 4.00s | 240 | 19.8 fps | 0.69 MB | 0.33x |
| **V13.6** | 12.62s | 11.99s | 719 | 57.0 fps | 0.79 MB | 0.95x |
| **V13.7** | 12.25s | 11.99s | 719 | 58.7 fps | 0.84 MB | 0.98x |
| **V14** | 12.65s | 4.00s | 240 | 19.0 fps | 0.71 MB | 0.32x |
| **V16** | 12.14s | 3.55s | 212 | 17.5 fps | 0.83 MB | 0.29x |
| **V17** | 12.10s | 11.99s | 719 | 59.4 fps | 0.71 MB | 0.99x |

**平均性能**: 12.31s 墙钟时间, 38.6 fps 渲染速度, 0.76 MB 文件大小

### 关键发现

1. **渲染时间与仿真时长无关**
   - 短动画（4s）和长动画（12s）的墙钟时间几乎相同（~12s）
   - **结论**: 初始化开销（加载模型、创建渲染器）占主导地位
   - **影响**: 短动画的效率极低（仅 0.3x 实时倍率）

2. **渲染速度差异巨大**
   - 快速版本：V13.6/V13.7/V17 达到 ~57-59 fps
   - 慢速版本：V10/V14/V16 仅 ~17-20 fps
   - **原因**: 长动画有更多帧来分摊初始化成本

3. **并行渲染效率**
   - 2 线程：1.73x 加速比，86.6% 效率
   - 4 线程：2.34x 加速比，58.4% 效率
   - **瓶颈**: Python GIL 限制，进程池比线程池更优

4. **文件大小一致**
   - 所有版本文件大小在 0.69-0.84 MB 范围内
   - 差异主要来自帧数（240 vs 719 帧）
   - 压缩比稳定（~1KB/帧）

## 性能瓶颈分析

### 慢速版本（V10, V14, V16）

**特征**:
- 仿真时长短（3.5-4s）
- 渲染速度低（17-20 fps）
- 墙钟时间与长动画版本相同（~12s）

**瓶颈**:
1. **初始化开销** (~8-9s)
   - MuJoCo 模型加载
   - 渲染器创建（Renderer 对象）
   - CSV 数据读取和解析
   - 字体加载（msyh.ttc）

2. **帧处理效率低**
   - 每帧 `np.interp` 插值开销
   - PIL/ImageDraw 文本渲染
   - 图像数据复制和转换

### 快速版本（V13.6, V13.7, V17）

**优势**:
- 仿真时长长（12s）
- 更多帧数（719 帧）分摊初始化成本
- 实际渲染速度接近实时（0.95-0.99x）

**效率**: 
- 初始化 ~8-9s，实际渲染 ~3-4s
- 每帧处理时间 ~4-6ms（包含所有开销）

## 优化建议

### 1. 减少初始化开销（高优先级）

**问题**: 每次渲染都重新加载模型和创建渲染器

**解决方案**:
```python
# 批量渲染模式 - 复用渲染器对象
def batch_render(scenarios: list[dict]):
    model = mujoco.MjModel.from_xml_path(MODEL_PATH)
    renderer = mujoco.Renderer(model, height=720, width=1280)  # 复用
    font = ImageFont.truetype(FONT, 20)  # 缓存字体
    
    for scenario in scenarios:
        render_single_scenario(model, renderer, font, scenario)
```

**预期收益**: 减少 70% 墙钟时间（对于短动画）

### 2. 优化帧处理循环（中优先级）

**问题**: 每帧调用 `np.interp` 进行插值

**解决方案**:
```python
# 预计算所有帧的插值数据
frame_times = np.linspace(0, duration, num_frames)
qpos_interpolated = np.array([
    [np.interp(t, data["time"], data[key]) for key in QPOS_KEYS]
    for t in frame_times
])

# 渲染循环只需索引
for idx, qpos in enumerate(qpos_interpolated):
    sim_data.qpos[:] = qpos
    # ...
```

**预期收益**: 减少 20-30% 帧处理时间

### 3. 并行渲染（中优先级）

**当前问题**: ProcessPoolExecutor 效率仅 58%（4线程）

**改进方案**:
```python
# 使用进程池而非线程池（避免 GIL）
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(render_version, versions)
```

**预期收益**: 4 线程达到 3.0x+ 加速比

### 4. 分辨率/帧率权衡（低优先级）

**当前配置**: 720p @ 60fps

**备选方案**:
- **预览模式**: 480p @ 30fps（文件大小减少 70%）
- **演示模式**: 720p @ 60fps（当前）
- **高清模式**: 1080p @ 60fps（需测试）

### 5. 针对短动画的特殊处理

**问题**: V10/V14/V16 仿真时长仅 3.5-4s，效率极低

**建议**:
```python
# 方案 A: 延长仿真时长（如果步态稳定）
params.duration = 12.0  # 从 4s 延长到 12s

# 方案 B: 批量渲染多个初始条件
scenarios = [
    {"initial_vx": 0.03, "slope": 0.0},
    {"initial_vx": 0.04, "slope": 0.0},
    {"initial_vx": 0.05, "slope": 0.0},
]
batch_render(scenarios)  # 一次初始化，渲染3个场景
```

## 输出文件

### 1. JSON 结果文件
**路径**: `results/animation_rendering_benchmark.json`

包含所有测试的原始数据，可用于后续分析和可视化。

### 2. 性能图表
**路径**: `results/rendering_performance.png`

6 个子图展示：
- 墙钟时间对比
- 文件大小对比
- 渲染速度对比
- 实时倍率对比
- 渲染效率对比
- 并行加速比曲线

### 3. 性能报告
**路径**: `results/PERFORMANCE_REPORT.md`

详细的文本报告，包含：
- 每个版本的详细指标
- 关键发现和统计分析
- 并行渲染性能分析
- 优化建议

## 扩展测试

### 测试不同分辨率

```python
# 修改 benchmark_single_render 函数
def benchmark_single_render(version: str, resolution: str = "720p"):
    if resolution == "1080p":
        renderer = mujoco.Renderer(model, height=1080, width=1920)
    elif resolution == "480p":
        renderer = mujoco.Renderer(model, height=480, width=854)
    # ...
```

### 测试不同帧率

```python
# 修改渲染脚本中的 fps 参数
fps = 30  # 从 60 降低到 30
frames = []
for idx in range(max(1, int(duration * fps))):
    t = idx / fps
    # ...
```

### 性能剖析（Profiling）

```powershell
# 使用 cProfile 分析单个渲染脚本
python -m cProfile -o render_v10.prof render_rolling_foot_gait_v10.py

# 分析结果
python -c "
import pstats
p = pstats.Stats('render_v10.prof')
p.sort_stats('cumulative').print_stats(20)
"
```

## 与现有工具集成

### 与 benchmark_runner.py 的关系

- **benchmark_runner.py**: 测试仿真性能（CoT、步态稳定性、能量效率）
- **animation_rendering.py**: 测试渲染性能（墙钟时间、帧率、文件大小）

两者互补，共同构成完整的性能测试框架。

### 与 CI/CD 集成

```yaml
# .github/workflows/performance.yml
- name: Run rendering benchmark
  run: |
    python benchmarks/animation_rendering.py --versions V10 V13.6 V17
    
- name: Upload results
  uses: actions/upload-artifact@v2
  with:
    name: rendering-performance
    path: benchmarks/results/
```

## 常见问题

### Q: 为什么并行渲染效率不高（58%）？

A: Python 的 GIL（全局解释器锁）限制了多线程性能。虽然使用了 `ProcessPoolExecutor`，但进程间通信和序列化开销较大。建议使用 2 线程（效率 86%）而非 4 线程。

### Q: 为什么墙钟时间与仿真时长无关？

A: 初始化开销（加载模型、创建渲染器、读取数据）占主导地位（~8-9s），实际渲染只占 ~3-4s。对于短动画，这种固定开销尤其明显。

### Q: 如何提升短动画的渲染效率？

A: 三个方案：
1. 延长仿真时长（如果步态稳定）
2. 批量渲染多个场景（复用初始化）
3. 预计算渲染器和模型（实现渲染服务）

### Q: 测试结果不稳定怎么办？

A: 渲染性能受系统负载影响。建议：
- 关闭其他高负载程序
- 多次运行取平均值
- 监控 CPU/内存使用率

## 参考资料

- [MuJoCo Rendering Documentation](https://mujoco.readthedocs.io/en/stable/programming/visualization.html)
- [imageio Performance Tips](https://imageio.readthedocs.io/en/stable/reference/userapi.html#imageio.mimsave)
- [PIL/Pillow Optimization Guide](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#performance)

---

**作者**: hw-1 项目组  
**创建日期**: 2026-06-05  
**最后更新**: 2026-06-05

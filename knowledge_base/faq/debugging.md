# FAQ：调试问题

## 跌倒诊断

### Q1: 仿真跌倒了怎么办？

**快速诊断流程**：

1. **检查跌倒类型**
   ```python
   # 检查躯干高度
   if data.qpos[1] < 0.5:  # hip_y < 0.5m
       print("躯干触地跌倒")
   
   # 检查躯干倾角
   hip_angle = data.qpos[2]
   if abs(hip_angle) > np.pi/3:  # > 60度
       print("躯干过度倾斜")
   
   # 检查是否失去接触
   if data.ncon == 0:
       print("双脚离地")
   ```

2. **回溯跌倒前状态**
   ```python
   # 保存跌倒前 10 步的状态
   history_buffer = deque(maxlen=10)
   for step in range(n_steps):
       history_buffer.append({
           'time': data.time,
           'qpos': data.qpos.copy(),
           'qvel': data.qvel.copy(),
           'ctrl': data.ctrl.copy(),
       })
       mujoco.mj_step(model, data)
       
       if is_fallen(data):
           print("跌倒前状态：")
           for i, state in enumerate(history_buffer):
               print(f"  -{len(history_buffer)-i} steps: t={state['time']:.3f}")
           break
   ```

3. **检查关键指标**
   - 触地速度过大？（> 2.0 m/s）
   - 摆腿角速度过大？（> 10 rad/s）
   - 控制力矩饱和？（达到 `ctrlrange` 上限）
   - FSM 相位混乱？（频繁切换）

**常见跌倒原因及解决方案**：

| 跌倒类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 向前扑倒 | 推蹬力矩过大 | 降低 swing_thrust 参数 |
| 向后跌倒 | 推蹬不足/触地速度过小 | 提高能量补偿 |
| 侧向跌倒 | 侧向稳定性不足 | 检查 3D 模型约束（V18 发现纯被动侧向不稳定）|
| 双脚离地 | swing 相位力矩过大 | 检查 FSM 相位切换逻辑 |
| 膝盖屈曲 | stance 腿支撑力不足 | 提高 knee 刚度 |

### Q2: 如何可视化中间过程？

**1. 实时数据叠加**（基于 MuJoCo viewer）

```python
import mujoco
import mujoco.viewer

# 自定义渲染回调
def render_callback(model, data, viewer):
    # 显示关键信息
    info_lines = [
        f"Time: {data.time:.2f}s",
        f"Forward: {data.qpos[0]:.2f}m",
        f"Touchdowns: {touchdown_count}",
        f"Phase: {fsm.current_phase}",
        f"Energy: {calculate_energy(data):.1f}J",
    ]
    
    # MuJoCo 2.3+ 支持文本叠加
    # 需要自行实现或使用第三方工具

# 启动 viewer
with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        render_callback(model, data, viewer)
        mujoco.mj_step(model, data)
        viewer.sync()
```

**2. 记录关键事件**

```python
# V13.6 FSM 事件日志
class FSMLogger:
    def __init__(self):
        self.events = []
    
    def log_transition(self, time, from_phase, to_phase, trigger):
        self.events.append({
            'time': time,
            'from': from_phase,
            'to': to_phase,
            'trigger': trigger,
        })
    
    def save(self, filename):
        df = pd.DataFrame(self.events)
        df.to_csv(filename, index=False)
        print(f"Logged {len(self.events)} FSM transitions")

# 使用
logger = FSMLogger()
for step in simulation:
    if fsm.phase_changed:
        logger.log_transition(
            data.time,
            fsm.previous_phase,
            fsm.current_phase,
            fsm.trigger_event
        )
logger.save("fsm_log.csv")
```

**3. 能量流动可视化**（V12 标准）

```python
from common.energy_metrics import EnergyAnalyzer

analyzer = EnergyAnalyzer(model)
energy_data = analyzer.analyze_trajectory(trajectory)

# 绘制能量流动
fig, axes = plt.subplots(3, 1, figsize=(10, 8))

# 机械能
axes[0].plot(energy_data['time'], energy_data['kinetic'], label='Kinetic')
axes[0].plot(energy_data['time'], energy_data['potential'], label='Potential')
axes[0].plot(energy_data['time'], energy_data['total'], label='Total', linewidth=2)
axes[0].set_ylabel('Energy (J)')
axes[0].legend()
axes[0].grid(True)

# 功率
axes[1].plot(energy_data['time'], energy_data['power_input'], label='Input')
axes[1].plot(energy_data['time'], energy_data['power_dissipation'], label='Dissipation')
axes[1].set_ylabel('Power (W)')
axes[1].legend()
axes[1].grid(True)

# 碰撞损耗
axes[2].scatter(energy_data['collision_times'], 
                energy_data['collision_losses'], 
                c='red', marker='x')
axes[2].set_ylabel('Collision Loss (J)')
axes[2].set_xlabel('Time (s)')
axes[2].grid(True)

plt.tight_layout()
plt.savefig("energy_flow.png", dpi=150)
```

**4. Poincaré 截面可视化**（V5/V13b 标准）

```python
from common.poincare import PoincareSectionAnalyzer

# 提取 Poincaré 点（heel strike 时刻）
poincare_analyzer = PoincareSectionAnalyzer(
    event='heel_strike',
    state_dims=['hip_angle', 'hip_velocity']
)

poincare_points = poincare_analyzer.extract_points(trajectory)

# 绘制相图
plt.figure(figsize=(8, 6))
plt.plot(poincare_points[:, 0], poincare_points[:, 1], 'o-')
plt.plot(poincare_points[-1, 0], poincare_points[-1, 1], 'ro', 
         markersize=10, label='Final state')
plt.xlabel('Hip angle (rad)')
plt.ylabel('Hip velocity (rad/s)')
plt.title('Poincaré Section (Heel Strike)')
plt.legend()
plt.grid(True)
plt.savefig("poincare_section.png", dpi=150)

# 检查收敛
convergence = np.linalg.norm(np.diff(poincare_points, axis=0), axis=1)
print(f"Convergence rate: {convergence[-1]:.6f}")
if convergence[-1] < 1e-4:
    print("✓ Limit cycle converged")
```

### Q3: 如何定位性能瓶颈？

**1. 基础性能分析**

```python
import time

# 测量仿真速度
n_steps = 1000
start_time = time.time()

for _ in range(n_steps):
    mujoco.mj_step(model, data)

elapsed = time.time() - start_time
realtime_ratio = (n_steps * model.opt.timestep) / elapsed

print(f"Simulation speed: {realtime_ratio:.2f}× realtime")
print(f"Steps per second: {n_steps / elapsed:.0f}")
```

**2. 分段计时**

```python
import time

timings = {
    'control': 0.0,
    'physics': 0.0,
    'render': 0.0,
    'logging': 0.0,
}

for step in range(n_steps):
    # 控制律计算
    t0 = time.perf_counter()
    control_signal = controller.compute(data)
    timings['control'] += time.perf_counter() - t0
    
    # 物理仿真
    t0 = time.perf_counter()
    data.ctrl[:] = control_signal
    mujoco.mj_step(model, data)
    timings['physics'] += time.perf_counter() - t0
    
    # 渲染（如果需要）
    if step % render_interval == 0:
        t0 = time.perf_counter()
        viewer.render()
        timings['render'] += time.perf_counter() - t0
    
    # 数据记录
    t0 = time.perf_counter()
    trajectory.append(data.qpos.copy())
    timings['logging'] += time.perf_counter() - t0

# 分析
total_time = sum(timings.values())
for key, value in timings.items():
    percentage = (value / total_time) * 100
    print(f"{key}: {value:.3f}s ({percentage:.1f}%)")
```

**3. 使用 Python profiler**

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 运行仿真
result = simulate_gait(model, data, duration=5.0)

profiler.disable()

# 输出结果
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 显示前 20 个最耗时的函数
```

**常见瓶颈及优化**：

| 瓶颈 | 占比 | 优化方法 |
|------|------|---------|
| 物理仿真 | 40-60% | 降低 solver iterations / 提高 timestep |
| 渲染 | 20-40% | 降低渲染频率 / 关闭不必要的可视化标志 |
| 控制律计算 | 5-15% | 向量化计算 / 预计算查找表 |
| 数据记录 | 5-10% | 减少记录频率 / 使用 numpy preallocate |

### Q4: 如何保存调试现场？

**完整现场快照**：

```python
import pickle
import hashlib
from datetime import datetime

def save_debug_snapshot(model, data, controller, metadata=None):
    """保存完整调试现场"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    snapshot = {
        # 模型
        'model_xml': model.savexml(),
        'model_hash': hashlib.md5(model.savexml().encode()).hexdigest(),
        
        # 状态
        'qpos': data.qpos.copy(),
        'qvel': data.qvel.copy(),
        'ctrl': data.ctrl.copy(),
        'time': data.time,
        
        # 控制器
        'controller_state': controller.get_state(),
        
        # 环境信息
        'mujoco_version': mujoco.__version__,
        'numpy_version': np.__version__,
        'timestamp': timestamp,
        
        # 自定义元数据
        'metadata': metadata or {},
    }
    
    filename = f"debug_snapshot_{timestamp}.pkl"
    with open(filename, 'wb') as f:
        pickle.dump(snapshot, f)
    
    print(f"Debug snapshot saved: {filename}")
    return filename

# 使用
if is_fallen(data):
    save_debug_snapshot(model, data, fsm_controller, metadata={
        'reason': 'forward fall',
        'step': step,
        'touchdown_count': touchdown_count,
    })
```

**加载并重现**：

```python
def load_and_replay_snapshot(filename):
    """加载快照并重现"""
    with open(filename, 'rb') as f:
        snapshot = pickle.load(f)
    
    # 重建模型
    model = mujoco.MjModel.from_xml_string(snapshot['model_xml'])
    data = mujoco.MjData(model)
    
    # 恢复状态
    data.qpos[:] = snapshot['qpos']
    data.qvel[:] = snapshot['qvel']
    data.ctrl[:] = snapshot['ctrl']
    data.time = snapshot['time']
    
    # 恢复控制器
    controller = FSMController(model)
    controller.set_state(snapshot['controller_state'])
    
    print(f"Snapshot loaded: {filename}")
    print(f"  Time: {data.time:.3f}s")
    print(f"  MuJoCo version: {snapshot['mujoco_version']}")
    
    return model, data, controller

# 重现并继续仿真
model, data, controller = load_and_replay_snapshot("debug_snapshot_20260604_143022.pkl")

# 单步调试或继续运行
with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        ctrl = controller.compute(data)
        data.ctrl[:] = ctrl
        mujoco.mj_step(model, data)
        viewer.sync()
```

### Q5: 如何对比两个版本的差异？

**自动化对比工具**：

```python
def compare_versions(version_a, version_b, test_case):
    """对比两个版本在同一测试用例下的表现"""
    
    # 运行版本 A
    result_a = run_simulation(
        model=load_model(f"v{version_a}_model.xml"),
        params=test_case['params'],
        duration=test_case['duration'],
    )
    
    # 运行版本 B
    result_b = run_simulation(
        model=load_model(f"v{version_b}_model.xml"),
        params=test_case['params'],
        duration=test_case['duration'],
    )
    
    # 对比关键指标
    comparison = {
        'forward_distance': {
            'A': result_a['forward'],
            'B': result_b['forward'],
            'diff': result_b['forward'] - result_a['forward'],
            'diff_pct': ((result_b['forward'] / result_a['forward']) - 1) * 100,
        },
        'alt_touchdowns': {
            'A': result_a['alt_td'],
            'B': result_b['alt_td'],
            'diff': result_b['alt_td'] - result_a['alt_td'],
        },
        'CoT': {
            'A': result_a['cot'],
            'B': result_b['cot'],
            'diff': result_b['cot'] - result_a['cot'],
            'diff_pct': ((result_b['cot'] / result_a['cot']) - 1) * 100,
        },
    }
    
    # 打印对比
    print(f"\n=== Version Comparison: V{version_a} vs V{version_b} ===")
    for metric, values in comparison.items():
        print(f"\n{metric}:")
        print(f"  V{version_a}: {values['A']:.3f}")
        print(f"  V{version_b}: {values['B']:.3f}")
        print(f"  Diff: {values['diff']:.3f} ({values.get('diff_pct', 0):.1f}%)")
    
    return comparison

# 使用示例：对比 V14c 和 V13.6.1
comparison = compare_versions(
    version_a='14c',
    version_b='13_6_1',
    test_case={
        'params': {'foot_length': 0.04, 'leg_length': 1.0},
        'duration': 5.0,
    }
)
```

**V16 退化测试模式**（验证新特性不破坏原有功能）：

```python
def degradation_test(new_version, baseline_version='14c'):
    """退化测试：验证新版本在退化配置下是否还原基线版本"""
    
    # V16 示例：ideal motor 应该精确还原 V14c
    result_new = run_simulation(
        model=load_model(f"v{new_version}_model.xml"),
        motor_params=MotorParams.ideal(),  # J=b=tau_C=0
        params=baseline_params,
    )
    
    result_baseline = run_simulation(
        model=load_model(f"v{baseline_version}_model.xml"),
        params=baseline_params,
    )
    
    # 计算偏差
    deviation = abs(result_new['forward'] - result_baseline['forward'])
    deviation_pct = (deviation / result_baseline['forward']) * 100
    
    print(f"\n=== Degradation Test: V{new_version} (ideal) vs V{baseline_version} ===")
    print(f"Baseline forward: {result_baseline['forward']:.3f} m")
    print(f"New version forward: {result_new['forward']:.3f} m")
    print(f"Deviation: {deviation:.4f} m ({deviation_pct:.2f}%)")
    
    # V16 标准：偏差 < 0.01%
    if deviation_pct < 0.01:
        print("✓ PASS: Degradation test passed")
        return True
    else:
        print("✗ FAIL: Degradation test failed")
        return False
```

### Q6: 如何调试 FSM 状态机？

**FSM 状态追踪**：

```python
class FSMDebugger:
    def __init__(self, fsm):
        self.fsm = fsm
        self.state_history = []
        self.transition_count = {}
    
    def log_state(self, time, data):
        """记录当前状态"""
        state = {
            'time': time,
            'phase': self.fsm.current_phase,
            'phase_time': self.fsm.phase_elapsed_time,
            'trigger_signals': {
                'contact_left': data.contact_force_left > 10.0,
                'contact_right': data.contact_force_right > 10.0,
                'knee_angle': data.qpos[self.fsm.knee_idx],
                'hip_angle': data.qpos[self.fsm.hip_idx],
            },
            'output': {
                'tau_hip': data.ctrl[0],
                'tau_knee': data.ctrl[1],
            }
        }
        self.state_history.append(state)
    
    def check_anomalies(self):
        """检查异常模式"""
        anomalies = []
        
        # 检查相位持续时间异常
        phase_durations = {}
        for i in range(1, len(self.state_history)):
            prev = self.state_history[i-1]
            curr = self.state_history[i]
            
            if curr['phase'] != prev['phase']:
                duration = curr['time'] - prev['time']
                phase = prev['phase']
                
                if phase not in phase_durations:
                    phase_durations[phase] = []
                phase_durations[phase].append(duration)
        
        # 检查异常短/长相位
        for phase, durations in phase_durations.items():
            mean_duration = np.mean(durations)
            for d in durations:
                if d < 0.02:  # 异常短 < 20 ms
                    anomalies.append(f"Phase {phase} too short: {d:.3f}s")
                if d > 0.5:  # 异常长 > 500 ms
                    anomalies.append(f"Phase {phase} too long: {d:.3f}s")
        
        # 检查频繁切换
        for i in range(10, len(self.state_history)):
            window = self.state_history[i-10:i]
            transitions = sum(1 for j in range(1, len(window)) 
                            if window[j]['phase'] != window[j-1]['phase'])
            if transitions > 5:  # 10 步内切换 > 5 次
                anomalies.append(f"Frequent transitions at t={window[-1]['time']:.3f}s")
        
        return anomalies
    
    def visualize(self, filename='fsm_debug.png'):
        """可视化 FSM 状态演化"""
        times = [s['time'] for s in self.state_history]
        phases = [s['phase'] for s in self.state_history]
        tau_hip = [s['output']['tau_hip'] for s in self.state_history]
        
        # 相位到数值的映射
        phase_map = {
            'stance_early': 0,
            'stance_late': 1,
            'swing_thrust': 2,
            'swing_retract': 3,
        }
        phase_values = [phase_map.get(p, -1) for p in phases]
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        
        # 相位变化
        axes[0].plot(times, phase_values, linewidth=2)
        axes[0].set_yticks(list(phase_map.values()))
        axes[0].set_yticklabels(list(phase_map.keys()))
        axes[0].set_ylabel('FSM Phase')
        axes[0].grid(True)
        
        # 控制输出
        axes[1].plot(times, tau_hip, label='Hip torque')
        axes[1].set_ylabel('Torque (N·m)')
        axes[1].set_xlabel('Time (s)')
        axes[1].legend()
        axes[1].grid(True)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        print(f"FSM debug plot saved: {filename}")

# 使用
debugger = FSMDebugger(fsm_controller)

for step in range(n_steps):
    debugger.log_state(data.time, data)
    # ... 执行仿真 ...

# 检查异常
anomalies = debugger.check_anomalies()
if anomalies:
    print("⚠ FSM Anomalies detected:")
    for a in anomalies:
        print(f"  - {a}")

# 可视化
debugger.visualize()
```

### Q7: 参数扫描失败了一部分，如何恢复？

**断点续传机制**：

```python
import os
import json

def parameter_sweep_with_resume(param_grid, output_dir, resume=True):
    """支持断点续传的参数扫描"""
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载已完成的任务
    progress_file = os.path.join(output_dir, 'progress.json')
    if resume and os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            completed = set(json.load(f)['completed'])
        print(f"Resuming: {len(completed)} tasks already completed")
    else:
        completed = set()
    
    # 生成任务列表
    tasks = []
    for i, params in enumerate(param_grid):
        task_id = f"task_{i:04d}"
        if task_id not in completed:
            tasks.append((task_id, params))
    
    print(f"Total tasks: {len(param_grid)}")
    print(f"Remaining: {len(tasks)}")
    
    # 执行扫描
    results = {}
    for task_id, params in tasks:
        try:
            print(f"Running {task_id}: {params}")
            result = run_simulation(params)
            
            # 保存结果
            result_file = os.path.join(output_dir, f"{task_id}.json")
            with open(result_file, 'w') as f:
                json.dump({
                    'params': params,
                    'result': result,
                }, f, indent=2)
            
            # 更新进度
            completed.add(task_id)
            with open(progress_file, 'w') as f:
                json.dump({'completed': list(completed)}, f)
            
            results[task_id] = result
            
        except Exception as e:
            print(f"✗ {task_id} failed: {e}")
            # 记录失败但继续
            with open(os.path.join(output_dir, f"{task_id}_error.txt"), 'w') as f:
                f.write(str(e))
    
    print(f"\nSweep completed: {len(completed)}/{len(param_grid)} tasks")
    return results

# 使用
results = parameter_sweep_with_resume(
    param_grid=generate_grid(),
    output_dir='v13_sweep_output',
    resume=True  # 如果中断，第二次运行时自动续传
)
```

### Q8: 如何远程监控长时间仿真？

**简单日志输出**：

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    filename=f'simulation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 在仿真循环中记录关键事件
for i, params in enumerate(param_grid):
    logging.info(f"Starting task {i+1}/{len(param_grid)}: {params}")
    
    try:
        result = run_simulation(params)
        logging.info(f"  Result: forward={result['forward']:.2f}m, alt_td={result['alt_td']}")
    except Exception as e:
        logging.error(f"  Failed: {e}")
    
    # 定期输出进度
    if (i + 1) % 10 == 0:
        elapsed = time.time() - start_time
        eta = elapsed / (i + 1) * (len(param_grid) - i - 1)
        logging.info(f"Progress: {i+1}/{len(param_grid)} ({elapsed/60:.1f}min elapsed, ETA {eta/60:.1f}min)")
```

**使用 tqdm 进度条**：

```python
from tqdm import tqdm

results = []
for params in tqdm(param_grid, desc="Parameter sweep"):
    result = run_simulation(params)
    results.append(result)
    
    # 更新 postfix 显示统计
    success_count = sum(1 for r in results if r['success'])
    tqdm.write(f"Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
```

---

**相关资源**：
- [常见错误](../troubleshooting/common_errors.md)
- [仿真相关问题](simulation.md)
- [仿真工作流最佳实践](../best_practices/simulation_workflow.md)

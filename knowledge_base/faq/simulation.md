# FAQ：仿真相关问题

## 基础问题

### Q1: 为什么仿真出现 NaN？

**常见原因**：

1. **接触参数不合理**
   - `solimp`/`solref` 设置导致接触刚度过大或过小
   - **解决方案**：参考 V10 stable baseline：`solimp="0 0.95 0.001"`, `solref="0.005 1"`

2. **初始状态不稳定**
   - 初始姿态导致瞬间大接触力
   - **解决方案**：先从静态平衡态启动，或用 `mj_forward()` 检查初始状态合理性

3. **时间步长过大**
   - 快速动态下积分发散
   - **解决方案**：降低 `timestep`（V10 使用 0.001 s）

4. **执行器力矩饱和失效**
   - 控制律输出超出物理极限导致数值爆炸
   - **解决方案**：检查 `<motor ctrlrange>` 和 `<actuator>` 的 `forcerange`

**诊断流程**：

```python
# 1. 检查数据中何时出现 NaN
import numpy as np
nan_idx = np.where(np.isnan(data.qpos))[0]
if len(nan_idx) > 0:
    print(f"First NaN at step {nan_idx[0]}, time {nan_idx[0] * model.opt.timestep}")

# 2. 检查接触力
for i in range(data.ncon):
    contact = data.contact[i]
    if contact.dist < -0.01:  # 过度穿透
        print(f"Deep penetration at contact {i}: {contact.dist}")
```

### Q2: 如何判断仿真是否稳定？

**稳定性指标**：

1. **位移指标**：`forward_distance > 3.0 m`（至少 6-8 个步态周期）
2. **步数指标**：`alternating_touchdowns ≥ 10`（V17 标准）
3. **能量指标**：机械能变化 `< 10%`（V12 标准）
4. **Floquet 指标**：最大特征值模 `|λ_max| < 1.0`（V13b 标准：0.944）

**快速判断**：

```python
# V17 smoke test 标准
success = (
    alt_td >= 10 and
    forward_distance > 3.0 and
    not data.ncon == 0  # 保持接触
)
```

**注意事项**：
- 短期稳定（< 5 步）不代表长期稳定
- V13 实验表明窄参数盆地下，即使通过 smoke test 也可能在 20 步后失败
- 关键场景下建议运行 20 s（V13b 标准）

### Q3: 如何调整仿真时间步长？

**V10 baseline 设置**：

```xml
<option timestep="0.001" iterations="50" solver="Newton" tolerance="1e-10"/>
```

**调整原则**：

1. **降低 timestep**（提高精度但降低速度）：
   - 快速动态（碰撞瞬间、高速摆动）
   - 刚性接触
   - 出现数值不稳定时

2. **提高 timestep**（提高速度但可能降低精度）：
   - 慢速运动
   - 柔顺接触
   - 参数扫描需要快速验证时

**经验值**：
- 标准仿真：0.001 s
- 高精度分析：0.0005 s
- 快速扫描：0.002 s（需验证稳定性）

**验证方法**：

```python
# 对比不同 timestep 下的结果
timesteps = [0.0005, 0.001, 0.002]
results = []
for dt in timesteps:
    model.opt.timestep = dt
    result = run_simulation(model, data, duration=5.0)
    results.append(result)

# 检查差异
for i in range(1, len(results)):
    diff = abs(results[i]['forward'] - results[0]['forward'])
    print(f"dt={timesteps[i]}: diff={diff:.3f} m")
```

### Q4: 仿真速度太慢怎么办？

**优化策略**：

1. **降低渲染频率**
   ```python
   render_interval = 10  # 每 10 步渲染一次
   if step % render_interval == 0:
       viewer.render()
   ```

2. **关闭不必要的可视化**
   ```python
   viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
   viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = False
   ```

3. **使用批量仿真**（无 GUI）
   ```python
   # 参数扫描时使用
   for params in param_grid:
       result = simulate_headless(model, data, params)
       results.append(result)
   ```

4. **减少 solver iterations**（谨慎使用）
   ```xml
   <option iterations="30" tolerance="1e-8"/>
   ```

**性能基准**（V17）：
- 实时比：1:5 到 1:10（仿真 1 秒需要 5-10 秒真实时间）
- 批量扫描：36 格需要 ~10-15 分钟

### Q5: 如何正确设置初始状态？

**推荐流程**：

1. **从静态平衡态开始**
   ```python
   # 设置直立姿态
   data.qpos[0] = 0.0  # hip_x
   data.qpos[1] = 0.95  # hip_y (略高于腿长)
   data.qpos[2] = 0.1   # hip_angle (微前倾)
   data.qpos[3] = -0.2  # stance_leg
   data.qpos[4] = 0.2   # swing_leg
   
   # 清零速度
   data.qvel[:] = 0.0
   
   # 稳定几步
   for _ in range(100):
       mujoco.mj_step(model, data)
   ```

2. **从已知极限环状态开始**（V13b）
   ```python
   # 加载 V13b 辨识的极限环状态
   limit_cycle_state = np.load("v13b_limit_cycle_state.npy")
   data.qpos[:] = limit_cycle_state[:len(data.qpos)]
   data.qvel[:] = limit_cycle_state[len(data.qpos):]
   ```

3. **添加小扰动测试鲁棒性**（V11）
   ```python
   # 初始扰动
   data.qvel[0] += np.random.uniform(-0.1, 0.1)  # 水平速度扰动
   ```

### Q6: 接触检测不准确怎么办？

**常见问题**：

1. **脚底穿透地面**
   - 检查 `<geom>` 的 `condim`/`friction`
   - 参考 V10：`condim="3" friction="1.0 0.005 0.0001"`

2. **虚假接触**
   - 检查碰撞几何体的 `margin` 参数
   - 使用 `data.contact[i].dist` 检查接触距离

3. **接触力震荡**
   - 调整 `solref` 参数（阻尼比）
   - V10 使用 `solref="0.005 1"` 提供临界阻尼

**诊断工具**：

```python
# 可视化接触信息
for i in range(data.ncon):
    contact = data.contact[i]
    print(f"Contact {i}:")
    print(f"  Geom1: {model.geom(contact.geom1).name}")
    print(f"  Geom2: {model.geom(contact.geom2).name}")
    print(f"  Distance: {contact.dist:.6f}")
    print(f"  Normal force: {contact.frame[0]:.3f}")
```

### Q7: 如何保存和重放仿真结果？

**保存轨迹数据**：

```python
# V10/V17 标准格式
trajectory = {
    'time': time_history,
    'qpos': qpos_history,
    'qvel': qvel_history,
    'ctrl': ctrl_history,
    'contact': contact_history,
    'metadata': {
        'model_file': model_file,
        'duration': duration,
        'timestep': model.opt.timestep,
    }
}
np.savez_compressed(f"trajectory_{timestamp}.npz", **trajectory)
```

**重放仿真**：

```python
# 加载数据
data_file = np.load("trajectory_20260604_143022.npz")

# 重放
for i in range(len(data_file['time'])):
    data.qpos[:] = data_file['qpos'][i]
    data.qvel[:] = data_file['qvel'][i]
    mujoco.mj_forward(model, data)
    viewer.render()
```

### Q8: 仿真结果不可复现怎么办？

**确保可复现性**：

1. **固定随机种子**
   ```python
   np.random.seed(42)
   ```

2. **记录完整环境**
   ```python
   metadata = {
       'mujoco_version': mujoco.__version__,
       'numpy_version': np.__version__,
       'model_hash': hashlib.md5(model_xml.encode()).hexdigest(),
       'timestamp': datetime.now().isoformat(),
   }
   ```

3. **使用相同的求解器设置**
   - V10 baseline: Newton solver, 50 iterations, tol=1e-10

4. **版本隔离 XML 模型**（V14c 教训）
   - 每个版本的模型放在 `v{XX}/out/v{XX}_models/`
   - 不共享 XML，避免版本间污染

### Q9: 如何可视化中间计算过程？

**常用可视化**：

1. **实时状态显示**
   ```python
   # 在 viewer 上叠加文本
   info_text = f"Time: {data.time:.2f}s\n"
   info_text += f"Forward: {data.qpos[0]:.2f}m\n"
   info_text += f"Phase: {fsm.current_phase}\n"
   info_text += f"Energy: {energy:.2f}J"
   # MuJoCo viewer 需要自定义渲染
   ```

2. **FSM 状态变化**（V13.6）
   ```python
   # 记录相位切换
   phase_history = []
   for step in range(n_steps):
       if fsm.phase_changed:
           phase_history.append((data.time, fsm.current_phase))
   ```

3. **能量流动**（V12）
   ```python
   from common.energy_metrics import calculate_energy_flow
   energy_flow = calculate_energy_flow(trajectory)
   plt.plot(energy_flow['time'], energy_flow['kinetic'], label='Kinetic')
   plt.plot(energy_flow['time'], energy_flow['potential'], label='Potential')
   ```

### Q10: 如何判断是模型问题还是控制问题？

**诊断流程**：

1. **测试退化场景**
   ```python
   # 关闭控制器，测试纯物理
   data.ctrl[:] = 0.0
   # 如果仍然 NaN → 模型问题
   ```

2. **测试 ideal 配置**（V16 方法）
   ```python
   # 使用理想电机参数（无摩擦、无惯量）
   motor_params = MotorParams.ideal()
   # 如果通过 → 真实电机动力学破坏稳定
   ```

3. **对比已知稳定版本**
   ```python
   # 用 V10 baseline 控制律测试新模型
   # 用新控制律测试 V10 baseline 模型
   # 定位变更点
   ```

4. **检查 Floquet 稳定性**（V13b）
   ```python
   # 长程仿真 20s
   # 计算 Floquet multipliers
   # |λ_max| > 1.0 → 本质不稳定
   ```

---

**相关资源**：
- [调试问题](../troubleshooting/common_errors.md)
- [参数设置问题](parameters.md)
- [仿真工作流最佳实践](../best_practices/simulation_workflow.md)

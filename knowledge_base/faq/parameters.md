# FAQ：参数设置问题

## PD 控制参数

### Q1: 如何选择合适的 PD 增益？

**V10 baseline 参考值**：
- Hip: `kp=40.0`, `kd=3.0`
- Knee: `kp=50.0`, `kd=4.0`

**调整原则**：

1. **从低增益开始**
   - 初始值：`kp=10.0`, `kd=1.0`
   - 逐步提高直到响应足够快

2. **比例增益 (kp)**
   - 过小：响应慢，跟踪误差大
   - 过大：震荡，甚至不稳定
   - 调整步长：5-10

3. **微分增益 (kd)**
   - 通常为 `kp` 的 5-10%
   - 提供阻尼，抑制震荡
   - 对速度噪声敏感

**V13 发现的问题**：
- V10 PD 参数是**孤立点解**
- 切片 C (6×6 几何网格) 成功率仅 16.7%
- 任何真实摆臂质量 (≥0.05 kg) 都破坏稳定（V14）

**推荐替代方案**：
- **V13.6 事件驱动 FSM**：每个相位独立调参
- **V13.7 摩擦补偿**：前馈补偿电机摩擦

### Q2: FSM 相位时长如何确定？

**V13.6 四相位设计**：

```python
phases = {
    'stance_early': {
        'entry': 'heel_strike',
        'exit': 'foot_flat',
        'typical_duration': 0.05  # s
    },
    'stance_late': {
        'entry': 'foot_flat',
        'exit': 'heel_off',
        'typical_duration': 0.15  # s
    },
    'swing_thrust': {
        'entry': 'toe_off',
        'exit': 'mid_swing',
        'typical_duration': 0.10  # s
    },
    'swing_retract': {
        'entry': 'mid_swing',
        'exit': 'heel_strike',
        'typical_duration': 0.10  # s
    }
}
```

**确定方法**：

1. **从人体步态数据反推**
   - 正常步态周期：0.4-0.5 s/step
   - Stance/Swing 比例：60/40

2. **从仿真观测获取**
   ```python
   # 运行 V10 baseline，记录相位时长
   phase_durations = []
   for event in fsm_events:
       duration = event['exit_time'] - event['entry_time']
       phase_durations.append(duration)
   
   print(f"Average stance: {np.mean(stance_durations):.3f}s")
   print(f"Average swing: {np.mean(swing_durations):.3f}s")
   ```

3. **通过实验调优**（V13.6.1）
   - 不同质量/腿长下相位时长会变化
   - 使用自适应 FSM：基于传感器事件触发，而非固定时长

**关键发现**（V13.6）：
- 事件驱动优于时间驱动
- 相位切换依赖传感器信号（接触力、关节角度）
- 失败相位自动降级保证安全

### Q3: 质量参数的合理范围？

**V10 baseline 质量配置**：

```python
masses = {
    'torso': 40.0,      # kg (躯干+头)
    'thigh': 6.0,       # kg (大腿)
    'shank': 3.5,       # kg (小腿)
    'foot': 1.0,        # kg (脚)
    'total': 57.0       # kg (单侧)
}
```

**合理范围**（基于人体测量学）：

| 部件 | 范围 | 占体重比例 |
|-----|------|----------|
| 躯干 | 30-50 kg | 50-60% |
| 大腿 | 5-8 kg | 10-12% |
| 小腿 | 2.5-4.5 kg | 5-7% |
| 脚 | 0.8-1.5 kg | 1-2% |
| 总质量 | 50-70 kg | 100% |

**V13 参数敏感性发现**：

1. **几何参数更敏感**
   - 足长：0.038-0.042 m（窄窗口）
   - 腿长：1.00-1.02 m
   - 质量：5.0-5.2 kg（相对宽松）

2. **质量影响机制**
   - 改变转动惯量 → 摆动频率
   - 改变势能 → 碰撞速度
   - V14c：arm_mass ≥0.05 kg 破坏 V10 稳定

**设计容差建议**（V22 硬件）：
- 目标质量：5.1 kg
- 允许偏差：±5%（基于 V13 盆地宽度）
- 关键部件（足）：±2%

### Q4: 腿长和足长如何设置？

**V10 baseline 几何参数**：

```python
geometry = {
    'leg_length': 1.00,    # m (髋到踝)
    'foot_length': 0.04,   # m (跟到趾)
    'foot_radius': 0.04,   # m (圆弧足半径)
    'thigh_shank_ratio': 0.5,  # 大腿:小腿
}
```

**设计原则**：

1. **腿长选择**
   - 基于目标用户身高：`leg_length ≈ 0.53 × height`
   - V10: 1.00 m 对应 ~1.75 m 身高
   - V13 验证：0.98-1.02 m 均可稳定

2. **足长选择**
   - **极其敏感**：V13 发现 0.038-0.042 m 窄窗口
   - 影响机制：改变 COP (Center of Pressure) 位置
   - 过长：触地冲击大
   - 过短：推蹬不足

3. **足半径选择**（V10 滚动足）
   - 模拟人足跟-足底-脚趾滚动
   - 圆弧半径 = 足长
   - 实现平滑触地过渡

**V13 切片 C 扫描结果**：

```
foot_length: [0.038, 0.039, 0.040, 0.041, 0.042, 0.043] m
leg_length: [0.98, 0.99, 1.00, 1.01, 1.02, 1.03] m
success_rate: 6/36 = 16.7%
```

成功格落在：
- foot=0.040-0.042 m
- leg=1.00-1.02 m

### Q5: 接触参数如何调整？

**V10 稳定接触配置**：

```xml
<geom name="foot" type="sphere" size="0.04"
      friction="1.0 0.005 0.0001"
      condim="3"
      solimp="0 0.95 0.001"
      solref="0.005 1"/>
```

**参数说明**：

1. **friction (摩擦系数)**
   - 第一个值：滑动摩擦系数 (1.0)
   - 第二个值：扭转摩擦 (0.005)
   - 第三个值：滚动摩擦 (0.0001)
   - V13 验证：0.8-1.2 均稳定

2. **solimp (接触刚度/阻尼)**
   - `solimp="0 0.95 0.001"`
   - 中间值 0.95：接触刚度参数
   - 过高：震荡
   - 过低：穿透

3. **solref (接触动力学时间尺度)**
   - `solref="0.005 1"`
   - 第一个值：时间常数 (s)
   - 第二个值：阻尼比 (1.0 = 临界阻尼)

**调整建议**：
- 先用 V10 baseline 值
- 出现震荡 → 提高 solref 阻尼比
- 出现穿透 → 降低 solref 时间常数或提高 solimp

### Q6: 电机参数如何设置？

**V17 验证的 MX-64AR 参数**：

```python
motor_params = {
    'J_rotor': 2.8e-3,      # kg·m² (转子惯量)
    'b_viscous': 0.05,      # N·m·s/rad (粘滞摩擦)
    'tau_coulomb': 0.20,    # N·m (库仑摩擦)
    'tau_max': 6.0,         # N·m (最大扭矩)
    'gear_ratio': 1.0,      # 直驱
}
```

**V16 关键发现**：

- **库仑摩擦非单调影响**：
  - `tau_C ∈ [0.013, 0.20] N·m` → 失败带
  - `tau_C = 0` 或 `≥0.27 N·m` → 成功带
  - MX-64AR spec (0.20 N·m) 落入失败带

- **解决方案**（V13.7）：
  ```python
  # 前馈摩擦补偿
  tau_comp = tau_C_eff * sign_smooth(omega_joint, epsilon=0.01)
  tau_motor = tau_fsm + tau_comp
  ```

**选型约束**（V22 硬件）：
1. 选择低摩擦电机（`tau_C < 0.013 N·m`），或
2. 使用摩擦补偿（V13.7），或
3. 选择恢复带电机（`tau_C ≥ 0.27 N·m`）

### Q7: 如何设置 SEA 弹簧刚度？

**V15.1 SEA direct-drive 验证结果**：

```python
spring_stiffness_tests = {
    'k=500 N·m/rad': {
        'success_rate': '3/36 (8.3%)',
        'best_cell_forward': '4.92 m',  # 最优
        'deflection': '1.6 deg',
        'comment': '柔顺，但存在共振'
    },
    'k=1000 N·m/rad': {
        'success_rate': '4/36 (11.1%)',
        'comment': '共振失败带（类似 V16 tau_C）'
    },
    'k=5000 N·m/rad': {
        'success_rate': '5/36 (13.9%)',
        'comment': '精确复现 V14c'
    },
    'k=10000 N·m/rad': {
        'success_rate': '5/36 (13.9%)',
        'comment': '接近刚性'
    }
}
```

**选择原则**：

1. **过软** (k < 500)
   - 偏转角大 → 控制延迟
   - 能量存储多 → 安全风险

2. **适中** (k = 500-1000)
   - 偏转角 1-2 度
   - 最佳能量回收
   - 需避开共振带

3. **过硬** (k > 5000)
   - 接近刚性驱动
   - 失去柔顺优势

**V22 硬件推荐**：
- 目标刚度：500-1000 N·m/rad
- 偏转角：< 2 度
- 需实测避开共振带

### Q8: 传感器噪声参数如何设置？

**V17 验证的传感器规格**：

```python
sensor_noise = {
    'encoder': {
        'resolution': 4096,  # CPR (MX-64AR)
        'quantization': 2*np.pi / 4096,  # rad
        'gaussian_noise': 0.001,  # rad (标准差)
    },
    'velocity': {
        'gaussian_noise': 0.05,  # rad/s (标准差)
        'method': 'Kalman filter',
    },
    'contact': {
        'delay': 0.005,  # s (5 ms)
        'false_positive_rate': 0.01,
    }
}
```

**噪声容限**（V17 扫描结果）：

| noise_scale | forward | alt_td | rmse_vx | 结果 |
|------------|---------|--------|---------|------|
| 1.0× | 4.67 m | 10 | 0.079 m/s | PASS |
| 2.0× | 4.52 m | 10 | 0.158 m/s | PASS |
| 3.0× | 0.83 m | 2 | - | FAIL |

**硬件选型约束**（V22）：
- 编码器分辨率：≥ 4096 CPR（最佳），≥ 1024 CPR（最低）
- 接触延迟：< 15 ms（超过会破坏 FSM 时序）
- IMU 采样率：≥ 200 Hz

### Q9: 如何设置初始速度？

**推荐方法**：

1. **从静止启动**（V10 标准）
   ```python
   data.qvel[:] = 0.0
   # FSM 自动启动步态
   ```

2. **给初始推动**
   ```python
   data.qvel[0] = 0.5  # m/s (水平速度)
   # 模拟人为推动
   ```

3. **从极限环状态启动**（V13b）
   ```python
   # 加载稳态
   limit_cycle = np.load("v13b_limit_cycle.npy")
   data.qpos[:] = limit_cycle[:nq]
   data.qvel[:] = limit_cycle[nq:]
   ```

**注意事项**：
- 初始速度过大 → 触地冲击大 → 可能跌倒
- 初始速度过小 → 需要多步才能进入稳态
- V11 鲁棒性测试：速度扰动 ±0.1 m/s 仍稳定

### Q10: 参数扫描网格如何设计？

**V13 标准网格设计**：

```python
# 切片 C：几何参数 6×6 网格
param_grid = {
    'foot_length': np.linspace(0.038, 0.043, 6),  # m
    'leg_length': np.linspace(0.98, 1.03, 6),     # m
}
# 总共 36 格

# 切片 A：控制参数 6×6 网格
param_grid = {
    'kp': np.linspace(30, 55, 6),
    'kd': np.linspace(2.0, 4.5, 6),
}
```

**设计原则**：

1. **覆盖已知稳定点**
   - 中心点：V10 baseline
   - 范围：±10-20%

2. **分辨率选择**
   - 粗扫：5-6 点（快速验证）
   - 细扫：10-20 点（精确边界）

3. **维度选择**
   - 单因素：1D 扫描（理解趋势）
   - 双因素：2D 网格（找盆地）
   - 多因素：采样/优化（高维诅咒）

**计算成本**（V13 经验）：
- 6×6 网格：36 格 × 5s 仿真 = ~3-5 分钟
- 10×10 网格：100 格 × 5s = ~8-15 分钟
- 可并行化（如果有多核）

---

**相关资源**：
- [参数调优最佳实践](../best_practices/parameter_tuning.md)
- [仿真相关问题](simulation.md)
- [技术决策：为什么选择 FSM 而非纯 PD](../technical_decisions/why_fsm_over_pd.md)

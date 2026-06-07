# 仿真工作流最佳实践

本文档描述从参数设置到结果分析的完整仿真工作流程。

---

## 标准工作流

### 第 1 步：环境准备

```powershell
# 激活虚拟环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate

# 验证环境
python -c "import mujoco; print('MuJoCo version:', mujoco.__version__)"
```

---

### 第 2 步：选择基线版本

**根据研究目标选择起点：**

| 研究目标 | 推荐版本 | 原因 |
|---------|---------|------|
| 理解被动步态理论 | V5 | 纯被动极限环证明 |
| 开发新控制律 | V10 | PD 基线，性能稳定 |
| 集成电机模型 | V13.7 | 含摩擦补偿，电机兼容 |
| 添加传感器 | V17 | 含状态估计，真实传感器 |
| 硬件设计 | V22 | 完整硬件文档 |

---

### 第 3 步：配置参数

#### 3.1 复制默认参数

```powershell
# 以 V13.7 为例
cp v13_7_friction_compensation\default_params.yaml my_experiment\params.yaml
```

#### 3.2 编辑参数文件

```yaml
# my_experiment/params.yaml
mechanical:
  leg_length: 0.50      # 腿长 (m)
  foot_radius: 0.10     # 足部半径 (m)
  torso_mass: 10.0      # 躯干质量 (kg)
  leg_mass: 3.2         # 腿质量 (kg)

control:
  tau_0: 3.5            # Phase 0 力矩 (N·m)
  tau_1: 4.0            # Phase 1 力矩 (N·m)
  tau_2: -2.5           # Phase 2 力矩 (N·m)
  tau_3: 1.5            # Phase 3 力矩 (N·m)
  theta_01: 0.05        # Phase 0→1 阈值 (rad)
  theta_23: -0.1        # Phase 2→3 阈值 (rad)

motor:
  tau_C: 0.20           # 库仑摩擦 (N·m)
  compensate_friction: true

environment:
  slope_angle: 0.05     # 斜坡角度 (rad，约 2.86°)
  gravity: 9.81         # 重力加速度 (m/s²)
  timestep: 0.001       # 时间步长 (s)
```

#### 3.3 参数合理性检查

**机械参数范围：**
- leg_length: 0.35-0.65 m（超出范围易失败）
- foot_radius: 0.07-0.13 m（太小不稳定，太大阻力大）
- torso_mass: 8.0-12.0 kg（影响惯性和能量）

**控制参数范围：**
- tau_0, tau_1: 2.0-5.0 N·m（正力矩，推进）
- tau_2: -3.0 到 -1.5 N·m（负力矩，前摆）
- tau_3: 1.0-2.0 N·m（正力矩，减速）

**环境参数范围：**
- slope_angle: 0.03-0.08 rad（1.7°-4.6°）
- timestep: 0.0005-0.002 s（太大不稳定，太小慢）

---

### 第 4 步：运行仿真

#### 4.1 快速验证（短时间）

```powershell
# 运行 6 秒快速测试
python v13_7_friction_compensation\simulate_v13_7.py \
    --config my_experiment\params.yaml \
    --duration 6.0 \
    --save-prefix quick_test
```

**判断标准：**
- ✅ 成功：forward > 2.0 m, alternations ≥ 5
- ❌ 失败：跌倒、卡住、NaN

#### 4.2 完整验证（长时间）

```powershell
# 运行 12 秒完整测试
python v13_7_friction_compensation\simulate_v13_7.py \
    --config my_experiment\params.yaml \
    --duration 12.0 \
    --save-prefix full_test
```

**判断标准：**
- ✅ 成功：forward > 4.0 m, alternations ≥ 10
- ⚠️ 边界：forward 2.0-4.0 m（需要调优）
- ❌ 失败：forward < 2.0 m

#### 4.3 鲁棒性测试

```powershell
# 运行多次不同随机种子
for seed in 1 2 3 4 5; do
    python v13_7_friction_compensation\simulate_v13_7.py \
        --config my_experiment\params.yaml \
        --duration 12.0 \
        --seed $seed \
        --save-prefix robustness_$seed
done
```

**统计成功率：**
- 5/5 成功 → 鲁棒配置
- 3-4/5 成功 → 边界配置
- 0-2/5 成功 → 不稳定配置

---

### 第 5 步：结果分析

#### 5.1 查看摘要

```powershell
# 查看 JSON 摘要
cat v13_7_friction_compensation\out\full_test_summary.json
```

**关键指标：**
```json
{
  "success": true,
  "forward_distance": 4.63,      // 前进距离 (m)
  "alternating_touchdowns": 10,  // 交替触地次数
  "cot_mechanical": 0.066,       // 能量成本
  "max_hip_torque": 3.91,        // 最大力矩 (N·m)
  "sim_duration": 12.0           // 仿真时长 (s)
}
```

#### 5.2 可视化轨迹

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取轨迹
df = pd.read_csv('v13_7_friction_compensation/out/full_test_trajectory.csv')

# 创建多子图
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

# 1. 髋部位置
axes[0].plot(df['time'], df['hip_x'], 'b-')
axes[0].set_ylabel('Hip X (m)')
axes[0].grid(True)

# 2. 髋关节角度
axes[1].plot(df['time'], df['hip_angle'], 'g-')
axes[1].set_ylabel('Hip Angle (rad)')
axes[1].grid(True)

# 3. 接触状态
axes[2].plot(df['time'], df['left_foot_contact'], 'r-', label='Left')
axes[2].plot(df['time'], df['right_foot_contact'], 'b-', label='Right')
axes[2].set_ylabel('Contact')
axes[2].legend()
axes[2].grid(True)

# 4. 髋关节力矩
axes[3].plot(df['time'], df['hip_torque'], 'k-')
axes[3].set_xlabel('Time (s)')
axes[3].set_ylabel('Torque (N·m)')
axes[3].grid(True)

plt.tight_layout()
plt.savefig('my_experiment/trajectory_analysis.png', dpi=150)
plt.show()
```

#### 5.3 计算步态指标

```python
import numpy as np

# 步频（steps per second）
step_frequency = df['alternating_touchdowns'].iloc[-1] / df['time'].iloc[-1]
print(f"Step frequency: {step_frequency:.2f} Hz")

# 平均速度
avg_velocity = df['forward_distance'].iloc[-1] / df['time'].iloc[-1]
print(f"Average velocity: {avg_velocity:.3f} m/s")

# 步长（stride length）
stride_length = df['forward_distance'].iloc[-1] / (df['alternating_touchdowns'].iloc[-1] / 2)
print(f"Stride length: {stride_length:.3f} m")

# CoT
cot = df['cot_mechanical'].iloc[-1]
print(f"CoT: {cot:.4f}")
```

---

### 第 6 步：对比分析

#### 6.1 版本对比

```powershell
# 运行基线版本（V10）
python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py \
    --duration 12.0 \
    --save-prefix v10_baseline

# 运行改进版本（V13.7）
python v13_7_friction_compensation\simulate_v13_7.py \
    --duration 12.0 \
    --save-prefix v13_7_improved
```

#### 6.2 生成对比表

```python
import json

# 读取两个摘要
with open('v10_baseline_summary.json') as f:
    v10 = json.load(f)
with open('v13_7_improved_summary.json') as f:
    v13_7 = json.load(f)

# 对比表
print("| Metric | V10 | V13.7 | Improvement |")
print("|--------|-----|-------|-------------|")
print(f"| Forward (m) | {v10['forward_distance']:.2f} | {v13_7['forward_distance']:.2f} | {(v13_7['forward_distance']/v10['forward_distance']-1)*100:.1f}% |")
print(f"| CoT | {v10['cot_mechanical']:.4f} | {v13_7['cot_mechanical']:.4f} | {(v13_7['cot_mechanical']/v10['cot_mechanical']-1)*100:.1f}% |")
print(f"| Max Torque (N·m) | {v10['max_hip_torque']:.2f} | {v13_7['max_hip_torque']:.2f} | {(v13_7['max_hip_torque']/v10['max_hip_torque']-1)*100:.1f}% |")
```

---

### 第 7 步：记录与归档

#### 7.1 创建实验记录

```markdown
# Experiment Log: my_experiment

**日期**: 2026-06-05
**目标**: 测试增大足部半径对稳定性的影响
**基线**: V13.7 default parameters

## 参数变化
- foot_radius: 0.10 → 0.12 m (+20%)

## 结果
- Forward distance: 4.63 → 4.21 m (-9.1%)
- CoT: 0.066 → 0.071 (+7.6%)
- Success: Yes

## 结论
增大足部半径提高滚动阻力，降低效率。
推荐保持 foot_radius ≈ 0.10 m。

## 下一步
测试减小足部半径 (0.08 m)
```

#### 7.2 保存实验数据

```powershell
# 创建实验目录
mkdir my_experiment\results

# 归档所有输出
cp v13_7_friction_compensation\out\full_test_* my_experiment\results\
cp my_experiment\params.yaml my_experiment\results\
cp my_experiment\trajectory_analysis.png my_experiment\results\
```

---

## 常见工作流变体

### 工作流 A：参数扫描

**目标：** 系统化探索参数空间

```powershell
# 使用参数调优工具
cd parameter_tuner

# 2D 网格扫描
python grid_search_2d.py \
    --param1 foot_radius --range1 0.08 0.12 5 \
    --param2 leg_length --range2 0.45 0.55 5 \
    --output results_grid.json

# 可视化
python visualize_grid_search.py \
    --input results_grid.json \
    --output heatmap_grid.png
```

---

### 工作流 B：鲁棒性分析

**目标：** 评估对扰动的容忍度

```powershell
# 使用 V11 鲁棒性测试工具
cd v11_rugged_terrain_robustness

# 地形扰动扫描
python test_terrain_robustness.py \
    --config ..\my_experiment\params.yaml \
    --perturbation_range 0 30 10

# 脉冲扰动扫描
python test_impulse_robustness.py \
    --config ..\my_experiment\params.yaml \
    --impulse_range 0 20 10
```

---

### 工作流 C：能量分析

**目标：** 详细分析能量流动

```powershell
# 使用 V12 能量分析工具
cd v12_energy_cot_analysis

# 运行能量分析
python analyze_energy.py \
    --config ..\my_experiment\params.yaml \
    --duration 12.0

# 生成能量报告
python generate_energy_report.py \
    --input out\energy_trajectory.csv \
    --output out\energy_report.png
```

---

### 工作流 D：长程稳定性

**目标：** 评估长时间步态稳定性

```powershell
# 运行长程仿真（60 秒）
python v13_7_friction_compensation\simulate_v13_7.py \
    --config my_experiment\params.yaml \
    --duration 60.0 \
    --save-prefix long_run

# 分析 Floquet 乘子（需要 V13b 工具）
python v13b_floquet_long_run\compute_floquet.py \
    --input v13_7_friction_compensation\out\long_run_trajectory.csv
```

---

## 故障排查

### 问题 1：仿真出现 NaN

**症状：** 轨迹 CSV 中出现 NaN 值

**原因：**
1. 时间步长太大 → 数值不稳定
2. 参数超出物理边界 → 力矩过大
3. 接触求解失败 → 接触参数不合理

**解决方案：**
```yaml
# 1. 减小时间步长
environment:
  timestep: 0.0005  # 从 0.001 减半

# 2. 检查力矩饱和
motor:
  tau_sat: 10.0  # 添加饱和限制

# 3. 调整接触参数
contact:
  stiffness: 5000   # 降低刚度
  damping: 100      # 增加阻尼
```

---

### 问题 2：机器人立即跌倒

**症状：** forward < 0.5 m, alternations < 3

**诊断步骤：**

```powershell
# 1. 查看可视化
python v13_7_friction_compensation\view_v13_7.py \
    --config my_experiment\params.yaml

# 2. 检查初始状态
python diagnostics\check_initial_state.py \
    --config my_experiment\params.yaml

# 3. 慢速回放
python v13_7_friction_compensation\view_v13_7.py \
    --config my_experiment\params.yaml \
    --slow-motion 0.1
```

**常见原因：**
- 初始姿态不稳定
- 控制力矩过小或过大
- 斜坡角度不合理

---

### 问题 3：性能不稳定

**症状：** 多次运行结果差异大

**原因：** 对初始条件敏感（接近稳定边界）

**解决方案：**
1. 增加鲁棒性（调整控制增益）
2. 使用 V14b 摆臂机构（提高 2.8×）
3. 降低性能要求，远离稳定边界

---

## 最佳实践总结

### ✅ 推荐做法

1. **始终从已知稳定配置出发**
   - 复制默认参数，逐步修改
   - 每次只改一个参数
   
2. **快速迭代**
   - 先用 6s 快速测试
   - 成功后再用 12s 完整测试
   
3. **可视化优先**
   - 数字指标 + 轨迹图 + 动画
   - 理解失败的物理原因
   
4. **版本控制**
   - 每个实验独立目录
   - 保留参数文件和结果
   
5. **系统化探索**
   - 使用参数扫描工具
   - 记录成功域和失败带

---

### ❌ 避免做法

1. **盲目调参**
   - 同时改多个参数
   - 不记录哪个配置有效
   
2. **忽略失败信息**
   - 只看成功案例
   - 不分析失败原因
   
3. **过度追求性能**
   - 牺牲鲁棒性换取微小提升
   - 陷入局部最优
   
4. **跳过可视化**
   - 只看数字指标
   - 错过物理洞察

---

## 相关资源

- **参数调优策略**: [best_practices/parameter_tuning.md](parameter_tuning.md)
- **代码规范**: [best_practices/coding_standards.md](coding_standards.md)
- **FAQ 仿真问题**: [../faq/simulation.md](../faq/simulation.md)
- **FAQ 参数问题**: [../faq/parameters.md](../faq/parameters.md)
- **故障排查**: [../troubleshooting/common_errors.md](../troubleshooting/common_errors.md)

---

**最后更新**: 2026-06-05

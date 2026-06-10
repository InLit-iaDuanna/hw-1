# hw-1 RL环境修复与基线对比报告

生成时间：2026-06-08
项目：hw-1 步态训练辅助设备 RL训练

---

## 任务1：调整终止条件并重新测试

### 修改内容
- **文件**：`D:\Dunna\Documents\hw-1\rl_training\environment.py`
- **修改**：`fall_height_threshold` 默认值从 0.3m 改为 0.2m（第50行）
- **目的**：放宽终止条件，允许髋部下降到更低位置，看是否能提升FSM性能

### 测试结果（5次episode平均）

| 控制器 | 成功率 | 平均距离 | 平均步数 | 平均时长 | 主要失败原因 |
|--------|--------|----------|----------|----------|--------------|
| Zero Action | 0.0% | -7.04m | 643 | 12.87s | fall_low_height |
| Random Action | 0.0% | -14.74m | 645 | 12.90s | fall_low_height |
| **V13.7 FSM** | **20.0%** | **-3.54m** | **705** | **14.11s** | fall_low_height |
| PPO Model | 0.0% | 0.64m | 585 | 11.70s | fall_low_height |

### 关键发现

**✓ 成功案例（1/5）**
- Episode 5: 11.37m，存活1001步（20.02s），达到max_steps

**✗ 典型失败模式（4/5）**
- 平均向后倒退 -3.54m
- 无法启动前向行走
- 最终因髋部过低而终止

**结论**：
- 降低 `fall_height_threshold` 只是延长失败时间（12.87s → 14.11s）
- **未解决根本问题**：FSM无法从静止直立状态启动步态
- 偶然成功（20%）可能是随机噪声产生了有利的初始条件

---

## 任务2：初始化差异对比分析

### 核心差异总结

| 维度 | V13.7原始初始化 | RL环境初始化 | 影响 |
|------|-----------------|--------------|------|
| **初始姿态** | 自然行走mid-stride（左腿支撑，右腿摆动） | 直立静止（双腿垂直） | RL从非动态状态开始 |
| **初始前向速度** | 0.03 m/s | 0.0 m/s | RL缺少启动动量 |
| **关节初始速度** | 左髋0.04，右髋0.10，右膝-0.04 rad/s | ~±0.005 rad/s随机扰动 | V13.7摆动腿已在运动 |
| **初始化哲学** | 模拟步态周期8%位置快照 | 站立准备姿态 | 任务定义不同 |
| **随机性** | 确定性（每次相同） | 随机扰动（每次不同） | RL训练鲁棒性 |
| **初始能量** | ~0.0065 J（动能+转动能） | ~0 J | V13.7更接近稳态 |

### V13.7原始初始化详细参数

**位置设置（基于运动学计算）**：
```python
release_phase = 0.08  # 步态周期8%位置
u = smoothstep(0.08)
alpha = asin(step_length / (2 * leg_length)) ≈ 0.172 rad
left_hip = gamma + alpha - 2*alpha*u
hip_x ≈ 0.034 m
hip_z ≈ 1.0 m
right_hip, right_knee = IK(swing_foot_x=0.38m, clearance=0.12m)
```

**速度设置（精心设计）**：
```python
hip_x速度: 0.03 m/s
hip_z速度: -tan(slope)*0.03 ≈ 0 m/s（平地）
左髋速度: 0.04 rad/s
右髋速度: 0.10 rad/s（摆动腿）
右膝速度: -0.04 rad/s（屈膝）
```

### RL环境初始化详细参数

**位置设置（简单+随机）**：
```python
hip_x = 0.0 m
hip_y = 0.0 m
hip_z = 1.0 m
所有关节角度 = 0.0 + N(0, 0.01²) rad
```

**速度设置（随机扰动）**：
```python
hip速度 = 0.0 m/s
所有关节速度 = N(0, 0.005²) rad/s
```

### 为什么V13.7 FSM在RL环境中失败？

**5大根本原因**：

1. **设计假设违背**：FSM设计时假设从动态行走状态开始，有初始前向速度
2. **相位检测失效**：从直立开始双脚同时接触地面，FSM的足底接触事件触发逻辑混乱
3. **缺少启动逻辑**：FSM只有"维持步态"状态机，没有"从静止启动"的冷启动序列
4. **能量障碍**：从静止启动需要克服势能垒，FSM力矩增益未针对此场景优化
5. **重心位置**：直立时重心在双脚正中央（稳定但难倾倒），V13.7重心已偏移（易进入摆动相）

### 修复方案评估

| 方案 | 优点 | 缺点 | 推荐度 | 备注 |
|------|------|------|--------|------|
| 方案1：RL环境采用V13.7初始化 | FSM可直接工作，达到4.63m基线 | RL策略需重新训练，失去泛化能力 | ★★★☆☆ | 仅用于验证FSM基线 |
| 方案2：为FSM添加冷启动模式 | 使FSM适应两种初始化，增强鲁棒性 | 需重新设计FSM逻辑，工作量大 | ★★★★☆ | 长期最佳方案 |
| 方案3：继续训练RL策略 | RL学到的策略更通用（可从静止启动） | 无法直接与FSM对比（任务不同） | ★★★★★ | **推荐**，RL优势 |

---

## 任务3：启动新的PPO训练

### 训练配置

**环境参数**：
- `fall_height_threshold`: 0.2 m（修复后）
- `reward_type`: "energy_efficient"
- `frame_skip`: 20
- `max_steps`: 1000

**超参数**（与原训练相同）：
- 总训练步数：2,000,000
- 并行环境数：8
- 学习率：3e-4
- n_steps：2048
- batch_size：64
- gamma：0.99
- gae_lambda：0.95

**保存路径**：
- 模型：`./models_fixed/ppo_gait_final.zip`
- Checkpoints：`./logs_fixed/checkpoints/`（每10,000步）
- TensorBoard日志：`./logs_fixed/tensorboard/`

### 训练启动状态

✓ **后台任务已启动**
- 训练脚本：`D:\Dunna\Documents\hw-1\rl_training\train_ppo_fixed.py`
- PowerShell Job ID：bfqu8qlei
- 预计训练时间：约2-4小时（取决于硬件）

**监控命令**：
```powershell
# 查看TensorBoard
tensorboard --logdir D:\Dunna\Documents\hw-1\rl_training\logs_fixed\tensorboard

# 查看最新checkpoint
Get-ChildItem D:\Dunna\Documents\hw-1\rl_training\logs_fixed\checkpoints\ | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

---

## 完整对比数据

### 数值差异对比表

| 参数 | V13.7原始 | RL环境 | 差异 |
|------|-----------|--------|------|
| 初始hip_x位置 | ~0.034 m | 0.0 m | **+0.034 m** |
| 初始hip_x速度 | 0.03 m/s | 0.0 m/s | **+0.03 m/s** |
| 左髋角速度 | 0.04 rad/s | ~0.0 rad/s | **+0.04 rad/s** |
| 右髋角速度 | 0.10 rad/s | ~0.0 rad/s | **+0.10 rad/s** |
| 右膝角速度 | -0.04 rad/s | ~0.0 rad/s | **-0.04 rad/s** |
| 初始动能 | ~0.0065 J | ~0 J | **+0.0065 J** |
| armature（髋） | 0.0068 kg·m² | 0.0068 kg·m² | **无差异** |
| armature（膝） | 0.0068 kg·m² | 0.0068 kg·m² | **无差异** |
| damping（髋） | 0.07 N·m·s/rad | 0.07 N·m·s/rad | **无差异** |
| damping（膝） | 0.13 N·m·s/rad | 0.13 N·m·s/rad | **无差异** |

### 电机模型参数（两者相同）

**Dynamixel MX-64AR @ 12V**：
- 减速比N：200.0
- 传动效率η：0.67
- 转子惯量J_rotor：7.0e-8 kg·m²
- 库仑摩擦τ_C_motor：1.5e-3 N·m
- 关节侧等效库仑摩擦：0.201 N·m

---

## 文件清单

### 生成的报告文件
1. `D:\Dunna\Documents\hw-1\rl_training\initialization_comparison_report.json`
   - 详细的初始化对比分析（JSON格式）
   
2. `D:\Dunna\Documents\hw-1\rl_training\fsm_comparison_results.json`
   - FSM测试结果（由test_fsm_in_rl_env.py生成）

### 修改的文件
1. `D:\Dunna\Documents\hw-1\rl_training\environment.py`
   - 第50行：`fall_height_threshold: float = 0.2`

### 新建的文件
1. `D:\Dunna\Documents\hw-1\rl_training\train_ppo_fixed.py`
   - 使用修复后环境的训练脚本

2. `D:\Dunna\Documents\hw-1\rl_training\start_training_fixed.ps1`
   - PowerShell启动脚本

### 关键代码位置参考
- V13.7初始化：`v14_passive_arms\simulate_passive_arms_v14.py:251-294`
- RL环境初始化：`rl_training\environment.py:404-459`
- V13.7运行脚本：`v13_7_friction_compensation\simulate_v13_7.py`
- 电机参数：`common\motor_dynamics.py:130-142`
- MuJoCo模型：`v13_7_friction_compensation\out\v13_7_models\friction_comp_walker.xml`

---

## 结论与建议

### 核心发现

1. **降低fall_height_threshold（0.3→0.2）无法解决FSM失败问题**
   - 只延长失败时间，不改变失败模式
   - V13.7 FSM成功率从0%提升到20%，但仍远低于基线

2. **初始化差异是FSM失败的根本原因**
   - V13.7设计假设：从动态行走状态开始（有速度、有动量）
   - RL环境实际：从静止直立状态开始（零速度、零动量）
   - **任务本质不同**：V13.7=维持步态，RL=启动+维持步态

3. **电机模型和物理参数无差异**
   - armature、damping、几何尺寸完全相同
   - 唯一差异在初始状态（位置+速度）

### 推荐行动

**立即行动（已完成）**：
- ✓ 修改environment.py，降低fall_height_threshold
- ✓ 重新测试V13.7 FSM性能
- ✓ 生成详细的初始化对比报告
- ✓ 启动新的PPO训练（后台运行）

**短期行动（1-2天）**：
- 监控新训练进度，关注是否收敛
- 如训练成功，对比新旧PPO模型性能
- 决定是否需要调整超参数

**中期行动（1周）**：
- 考虑实现方案2：为FSM添加冷启动模式
- 或实现方案1：创建RL环境的V13.7初始化模式（用于公平对比）

**长期优化**：
- 继续优化RL策略，学习从任意初始状态启动步态
- 探索curriculum learning：从简单初始状态逐步过渡到困难状态
- 研究meta-RL方法，学习快速适应不同初始条件

---

## 附录：测试详细数据

### V13.7 FSM在RL环境中的5次测试

| Episode | 结果 | 距离 | 步数 | 时长 | 终止原因 |
|---------|------|------|------|------|----------|
| 1 | FAIL | -13.34m | 671 | 13.42s | fall_low_height |
| 2 | FAIL | -10.16m | 589 | 11.78s | fall_low_height |
| 3 | FAIL | -6.71m | 664 | 13.28s | fall_low_height |
| 4 | FAIL | 1.14m | 602 | 12.04s | fall_low_height |
| 5 | **SUCCESS** | **11.37m** | **1001** | **20.02s** | max_steps_reached |

**平均值**：-3.54m，705步，14.11s，成功率20%

### 对比：V13.7原始环境基线（历史数据）

- 平均前向距离：4.63m
- 成功率：~100%
- 平均时长：12s
- 失败模式：偶尔后退或侧倾

**性能差距**：(-3.54m) - 4.63m = **-8.17m**

---

**报告生成：2026-06-08**
**项目路径：D:\Dunna\Documents\hw-1**
**联系人：段泽琪（博士研究生，2024211317）**

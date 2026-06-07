# Tutorial 03：参数调优

**目标：** 25 分钟内掌握参数敏感性分析和调优方法。

**难度：** ⭐⭐⭐ 高级

**前置要求：** 完成 Tutorial 01 和 02

---

## 学习目标

完成本教程后，你将能够：

- ✅ 理解关键参数及其物理意义
- ✅ 使用 Dashboard Heatmap 查看参数敏感性
- ✅ 手动调整参数并观察效果
- ✅ 使用批量扫描工具探索参数空间
- ✅ 理解成功域和失败带

---

## 第 1 步：关键参数解释（5 分钟）

### V13.7 的参数层次

```
1. 机械参数（Mechanical）
   ├── leg_length: 腿长 (m)
   ├── foot_radius: 足部半径 (m)
   ├── torso_mass: 躯干质量 (kg)
   └── leg_mass: 腿部质量 (kg)

2. 控制参数（Control）
   ├── tau_0, tau_1, tau_2, tau_3: FSM 各 phase 力矩 (N·m)
   ├── theta_01, theta_23: Phase 切换阈值 (rad)
   └── compensate_friction: 是否启用摩擦补偿

3. 电机参数（Motor）
   ├── tau_C: 库仑摩擦 (N·m)
   ├── J_eff: 等效转动惯量 (kg·m²)
   ├── b_eff: 黏性摩擦系数 (N·m·s/rad)
   └── tau_sat: 饱和力矩 (N·m)

4. 环境参数（Environment）
   ├── slope_angle: 斜坡角度 (rad)
   ├── ground_friction: 地面摩擦系数
   └── gravity: 重力加速度 (m/s²)
```

### 最敏感的 3 个参数

根据 V13 参数敏感性分析：

| 参数 | 影响 | 调整范围 | 推荐值 |
|------|------|----------|--------|
| **foot_radius** | 足部滚动半径，影响接触动力学 | 0.05-0.15 m | 0.10 m |
| **leg_length** | 腿长，影响摆动周期和步长 | 0.35-0.65 m | 0.50 m |
| **tau_C** | 电机摩擦，V16 揭示非单调共振 | 0-0.30 N·m | <0.013 或 ≥0.27 |

**为什么这些参数敏感？**

1. **foot_radius**：太小（<0.05）→ 接触不稳定；太大（>0.15）→ 滚动阻力大
2. **leg_length**：太短（<0.35）→ 步长小、效率低；太长（>0.65）→ 摆动慢、不稳定
3. **tau_C**：存在"失败带"[0.013, 0.20]，与 FSM 频率共振

---

##第 2 步：使用 Dashboard Heatmap（5 分钟）

### 打开 Heatmap View

```powershell
# 打开 Dashboard
start dashboard\index.html

# 或用浏览器直接打开
start chrome dashboard\index.html
```

在 Dashboard 中：
1. 点击顶部 **"Heatmap View"** 标签
2. 选择 **"V13 Parameter Sweep"** 数据集

---

### 解读 V13 Heatmap

**坐标轴：**
- X 轴：foot_radius（0.05 - 0.15 m，6 档）
- Y 轴：leg_length（0.35 - 0.65 m，6 档）
- 颜色：绿色 = 成功，红色 = 失败

**关键发现：**

```
leg_length ↑
  0.65 |  ❌  ❌  ❌  ❌  ❌  ❌
  0.59 |  ❌  ❌  ❌  ❌  ❌  ❌
  0.53 |  ❌  ✅  ✅  ✅  ❌  ❌
  0.47 |  ❌  ✅  ✅  ✅  ✅  ❌
  0.41 |  ❌  ❌  ✅  ✅  ❌  ❌
  0.35 |  ❌  ❌  ❌  ❌  ❌  ❌
       +---------------------------→ foot_radius
       0.05 0.07 0.09 0.11 0.13 0.15
```

**成功域：**
- 中心区域：foot_radius ≈ 0.09-0.11 m, leg_length ≈ 0.47-0.53 m
- 成功率：6/36 = 16.7%

**边界失败原因：**
- 左边界（foot_radius < 0.07）：接触不稳定，滑动
- 右边界（foot_radius > 0.13）：滚动阻力大，能量不足
- 上边界（leg_length > 0.59）：摆动周期长，相位不匹配
- 下边界（leg_length < 0.41）：步长小，前进慢

---

### 对比 V13.6 Heatmap

切换到 **"V13.6 FSM Controller"** 数据集：

```
V13.6 成功域（同参数空间）：
  0.65 |  ❌  ❌  ❌  ❌  ❌  ❌
  0.59 |  ❌  ❌  ❌  ❌  ❌  ❌
  0.53 |  ❌  ❌  ✅  ✅  ❌  ❌
  0.47 |  ❌  ❌  ✅  ✅  ❌  ❌
  0.41 |  ❌  ❌  ❌  ❌  ❌  ❌
  0.35 |  ❌  ❌  ❌  ❌  ❌  ❌
       +---------------------------→ foot_radius
```

**对比发现：**
- V10 成功率：16.7%（外围分散）
- V13.6 成功率：11.1%（中央集中）
- **V13.6 的成功域更窄但更集中** → 需要独立调优

---

### 查看 V16 摩擦共振带

切换到 **"V16 Friction Resonance"** 数据集：

**X 轴：** τ_C（0 - 0.30 N·m，10 档）

```
✅ 成功带：τ_C ∈ {0, 0.034, ≥0.27} N·m
❌ 失败带：τ_C ∈ [0.013, 0.20] N·m
⚠️ MX-64AR spec：τ_C = 0.20 N·m（落入失败带正中央！）
```

**非单调原因：** τ_C 与 FSM 切换频率形成共振耦合。

---

##第 3 步：手动调优实践（8 分钟）

### 实验 1：调整 foot_radius

创建自定义参数文件：

```powershell
# 复制默认配置
cp v13_7_friction_compensation\default_params.yaml v13_7_friction_compensation\custom_params.yaml

# 编辑参数
notepad v13_7_friction_compensation\custom_params.yaml
```

修改 `custom_params.yaml`：

```yaml
# 实验 1a：减小足部半径
mechanical:
  foot_radius: 0.06  # 默认 0.10 → 0.06
  leg_length: 0.50
  # ... 其他保持不变
```

运行仿真：

```powershell
python v13_7_friction_compensation\simulate_v13_7.py --config custom_params.yaml --duration 12.0
```

**预期结果：** 失败（forward < 1.0 m），原因：接触不稳定。

---

再试试增大：

```yaml
# 实验 1b：增大足部半径
mechanical:
  foot_radius: 0.14  # 0.10 → 0.14
```

**预期结果：** 失败或性能下降，原因：滚动阻力增大。

---

### 实验 2：调整 FSM 力矩

```yaml
# 实验 2：增加 Phase 1 力矩
control:
  tau_0: 3.5
  tau_1: 5.0  # 默认 4.0 → 5.0（增强 stance late）
  tau_2: -2.5
  tau_3: 1.5
```

**问题：**
- Forward distance 变化了多少？
- CoT 是增加还是减少？

---

### 实验 3：测试摩擦容限

```yaml
# 实验 3a：低摩擦（成功带）
motor:
  tau_C: 0.01  # 0.20 → 0.01
```

**预期：** 成功，且性能可能优于 0.20。

```yaml
# 实验 3b：高摩擦无补偿（失败带）
motor:
  tau_C: 0.15  # 落入失败带
  compensate_friction: false  # 关闭补偿
```

**预期：** 失败（forward < 1.0 m）。

```yaml
# 实验 3c：高摩擦有补偿
motor:
  tau_C: 0.15
  compensate_friction: true  # 启用补偿
```

**预期：** 成功，补偿修复失败。

---

## 第 4 步：批量扫描工具（5 分钟）

### 使用参数调优工具

项目提供了批量扫描工具：

```powershell
# 进入参数调优目录
cd parameter_tuner

# 运行 2D 网格扫描
python grid_search_2d.py --param1 foot_radius --param2 leg_length --output results_custom.json
```

**默认扫描范围：**
- foot_radius: [0.08, 0.09, 0.10, 0.11, 0.12]
- leg_length: [0.45, 0.47, 0.50, 0.53, 0.55]
- 总共：5 × 5 = 25 次仿真

**输出：**
```
Running grid search: 25 simulations
[█████████████████████] 100% (25/25)

Results saved to: results_custom.json
Success rate: 12/25 = 48.0%
Best configuration:
  foot_radius: 0.10
  leg_length: 0.50
  forward_distance: 4.63 m
  CoT: 0.066
```

---

### 可视化扫描结果

```powershell
# 生成热力图
python visualize_grid_search.py --input results_custom.json --output heatmap_custom.png
```

打开生成的 `heatmap_custom.png` 查看。

---

### 自定义扫描范围

编辑 `grid_search_2d.py`：

```python
# 在文件顶部修改范围
PARAM1_RANGE = [0.08, 0.09, 0.10, 0.11, 0.12]  # foot_radius
PARAM2_RANGE = [0.45, 0.50, 0.55]              # leg_length（减少到 3 档）

# 或使用命令行参数
python grid_search_2d.py \
    --param1 foot_radius --range1 0.08 0.12 5 \
    --param2 leg_length --range2 0.45 0.55 3
```

---

## 第 5 步：理解成功域和失败带（2 分钟）

### 成功域定义

**成功判据（V13.7）：**
```python
success = (
    forward_distance > 4.0 and
    alternations >= 10 and
    sim_time >= 11.0 and
    failure_reason == None
)
```

**成功域：** 参数空间中所有满足成功判据的点的集合。

---

### 失败带类型

| 失败类型 | 原因 | 典型参数 |
|----------|------|----------|
| **fall_down** | 机械不稳定，摔倒 | foot_radius < 0.07 |
| **stuck** | 卡住不动，无法前进 | leg_length > 0.60 |
| **energy_insufficient** | 能量不足，停止 | tau_0 < 2.0 |
| **contact_loss** | 接触丢失，飞行 | ground_friction < 0.5 |
| **resonance** | 参数共振 | tau_C ∈ [0.013, 0.20] |

---

### V16 非单调失败带（特殊案例）

```
τ_C (N·m)    状态
  0.00       ✅ 成功（无摩擦）
  0.01       ✅ 成功（摩擦可忽略）
  0.034      ✅ 成功（边界）
  ↓
  0.05       ❌ 失败（进入共振带）
  0.10       ❌ 失败
  0.15       ❌ 失败
  0.20       ❌ 失败（MX-64AR spec）
  ↓
  0.27       ✅ 成功（退出共振带）
  0.30       ✅ 成功
```

**关键洞察：** "更小的摩擦不总是更好"，存在非单调的共振带。

---

## 练习任务

### 任务 1：重现 V13 最佳点

根据 Dashboard Heatmap，V13 的最佳配置是：
- foot_radius = 0.10 m
- leg_length = 0.50 m

验证这是否也是 V13.7 的最佳点：

```powershell
# 使用默认参数运行
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0
```

记录 CoT 和 forward distance。

---

### 任务 2：探索边界

在最佳点附近进行微调：

```yaml
# 配置 A：foot_radius + 10%
mechanical:
  foot_radius: 0.11  # 0.10 → 0.11

# 配置 B：leg_length + 5%
mechanical:
  leg_length: 0.525  # 0.50 → 0.525
```

运行两个配置，对比性能。

**问题：** 哪个参数对性能的影响更大？

---

### 任务 3：测试摩擦补偿的鲁棒性

固定 foot_radius=0.10, leg_length=0.50，扫描 τ_C：

```powershell
# 使用批量工具
python parameter_tuner\scan_tau_c.py --range 0.0 0.30 10 --compensation true
```

生成 τ_C vs forward_distance 曲线。

**问题：**
- 有补偿时，哪些 τ_C 值仍然失败？
- 无补偿时，失败带是否与 V16 一致？

---

### 任务 4：设计自己的参数空间

假设你要设计一个"更高、更快"的机器人：

```yaml
# 目标：增加步长和速度
mechanical:
  leg_length: 0.60  # 增加 20%
  foot_radius: 0.12  # 增大足部

control:
  tau_1: 5.0  # 增强 stance 推力
```

**问题：**
- 这个配置能成功吗？
- 如果失败，失败原因是什么？
- 如何调整使其成功？

---

## 高级技巧

### 技巧 1：使用 Bayesian Optimization

对于高维参数空间，网格搜索成本过高。可以使用贝叶斯优化：

```powershell
# 需要安装 scikit-optimize
pip install scikit-optimize

# 运行贝叶斯优化（10 维参数）
python parameter_tuner\bayesian_optimization.py --n_calls 100
```

**优势：** 智能采样，100 次迭代通常能找到接近最优解。

---

### 技巧 2：多目标优化

同时优化 CoT 和 robustness：

```python
# 定义多目标函数
def objective(params):
    forward_dist, cot, robustness = simulate(params)
    # Pareto 前沿优化
    return (-forward_dist, cot, -robustness)
```

使用 NSGA-II 或 MOEA/D 算法。

---

### 技巧 3：敏感性分析

计算参数梯度：

```python
# 数值梯度
def sensitivity(param_name, base_value):
    delta = 0.01 * base_value
    
    result_plus = simulate({param_name: base_value + delta})
    result_minus = simulate({param_name: base_value - delta})
    
    gradient = (result_plus - result_minus) / (2 * delta)
    return gradient
```

梯度越大 → 参数越敏感。

---

## 调优策略总结

### 策略 1：由粗到细

1. **粗扫描**：大范围、稀疏网格（如 10 × 10）
2. **找到成功域**：识别成功点的聚集区域
3. **细扫描**：在成功域内加密（如 5 × 5）
4. **局部优化**：使用梯度下降或贝叶斯优化

---

### 策略 2：单因素分析

1. **固定所有参数**，只变化一个
2. **绘制性能曲线**：param vs CoT
3. **识别单调性**：递增、递减、非单调
4. **确定安全范围**

---

### 策略 3：相关性分析

某些参数可能耦合：

```
leg_length ↑  →  摆动周期 ↑  →  需要 tau_1 ↑
foot_radius ↑  →  滚动阻力 ↑  →  需要 tau_0 ↑
```

使用相关性矩阵识别耦合，联合调优。

---

## 故障排查

### 问题 1：所有配置都失败

**可能原因：**
1. 基础配置有问题（如模型文件损坏）
2. 环境参数不合理（如 slope_angle = 0）

**解决：** 先用默认参数验证，确认能成功后再调整。

---

### 问题 2：扫描结果不稳定

**可能原因：** 随机初始化或数值误差。

**解决：** 每个配置运行 3-5 次，取平均值。

---

### 问题 3：找不到成功域

**可能原因：** 扫描范围太窄或偏离最优区域。

**解决：** 扩大范围，使用对数刻度扫描（如 [0.01, 0.1, 1.0, 10.0]）。

---

## 小结

恭喜！你现在掌握了：

- ✅ 关键参数的物理意义
- ✅ 使用 Dashboard Heatmap 分析敏感性
- ✅ 手动调优和批量扫描
- ✅ 成功域和失败带的概念
- ✅ 非单调共振带（V16 摩擦）

---

## 下一步

- **运行跨版本分析**：`cross_version_analysis/compare_versions.py`
- **阅读 V13 README**：`v13_parameter_sensitivity_atlas/README.md`
- **设计自己的机器人**：应用调优技巧到新配置

---

**关键资源：**
- Dashboard Heatmap：`dashboard/index.html`
- 参数调优工具：`parameter_tuner/`
- V13 敏感性图谱：`v13_parameter_sensitivity_atlas/out/`
- V16 摩擦分析：`v16_motor_dynamics/README.md`

---

**调优的本质：** 在高维参数空间中寻找成功域，并理解边界的物理机制。祝你探索愉快！

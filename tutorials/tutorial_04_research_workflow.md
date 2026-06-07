# Tutorial 04：研究者深度教程

**目标：** 45 分钟内掌握能量分析、稳定性分析和跨版本对比方法

**难度：** ⭐⭐⭐⭐ 研究级

**前置要求：** 完成 Tutorial 01-03，理解被动步态理论

**适合人群：** 博士生、研究者、论文作者

---

## 学习目标

完成本教程后，你将能够：

- ✅ 使用 V12 工具进行详细能量分析
- ✅ 使用 V13b 工具计算 Floquet 稳定性
- ✅ 使用跨版本分析工具对比多个版本
- ✅ 生成论文级别的可视化图表
- ✅ 理解极限环理论与仿真的对应关系

---

## 第 1 步：能量分析（V12 工具）（15 分钟）

### 1.1 理解能量流动

**被动/准被动步态的能量平衡：**

```
重力势能输入 = 碰撞损耗 + 摩擦损耗 + 动能变化
```

**关键概念：**
- **Active Input Energy**：主动控制输入的机械功
- **Gravitational Input**：重力势能下降（斜坡行走）
- **Collision Loss**：脚跟触地时的碰撞损耗
- **Friction Dissipation**：滚动摩擦和空气阻力
- **CoT (Cost of Transport)**：归一化能量成本

---

### 1.2 运行能量分析

```powershell
# 进入 V12 目录
cd v12_energy_cot_analysis

# 运行 V10 能量分析
python analyze_energy_v10.py --duration 12.0 --save-prefix v10_energy

# 运行 V13.7 能量分析
python analyze_energy_v137.py --duration 12.0 --save-prefix v137_energy
```

**输出文件：**
- `out/v10_energy_trajectory.csv` — 时间序列能量数据
- `out/v10_energy_summary.json` — 能量摘要

---

### 1.3 查看能量摘要

```powershell
cat out\v10_energy_summary.json
```

**示例输出：**

```json
{
  "active_input_energy_j": 18.24,
  "gravitational_input_j": 12.36,
  "collision_loss_j": 8.91,
  "friction_dissipation_j": 2.13,
  "kinetic_energy_final_j": 5.42,
  "potential_energy_final_j": 14.14,
  "cot_mechanical": 0.072,
  "efficiency_passive_like": 0.678
}
```

**关键指标解释：**
- `cot_mechanical = 0.072` → 每千克每米消耗 0.072 J
- `efficiency_passive_like = 67.8%` → 重力势能转化效率

---

### 1.4 可视化能量流动

```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 读取轨迹
df = pd.read_csv('out/v10_energy_trajectory.csv')

# 创建能量瀑布图
fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

# 1. 总能量守恒检查
total_energy = df['kinetic_energy'] + df['potential_energy']
axes[0].plot(df['time'], total_energy, 'k-', linewidth=2, label='Total Energy')
axes[0].axhline(total_energy.iloc[0], color='r', linestyle='--', alpha=0.5, label='Initial')
axes[0].set_ylabel('Total Energy (J)')
axes[0].legend()
axes[0].grid(True)
axes[0].set_title('V10 Energy Analysis')

# 2. 动能与势能
axes[1].plot(df['time'], df['kinetic_energy'], 'b-', label='Kinetic')
axes[1].plot(df['time'], df['potential_energy'], 'g-', label='Potential')
axes[1].set_ylabel('Energy (J)')
axes[1].legend()
axes[1].grid(True)

# 3. 累积能量输入与损耗
axes[2].plot(df['time'], df['cumulative_active_input'], 'r-', label='Active Input')
axes[2].plot(df['time'], df['cumulative_collision_loss'], 'orange', label='Collision Loss')
axes[2].plot(df['time'], df['cumulative_friction_loss'], 'purple', label='Friction Loss')
axes[2].set_xlabel('Time (s)')
axes[2].set_ylabel('Cumulative Energy (J)')
axes[2].legend()
axes[2].grid(True)

plt.tight_layout()
plt.savefig('out/v10_energy_waterfall.png', dpi=300)
plt.show()
```

---

### 1.5 计算 CoT

**公式：**

```
CoT = E_input / (m × g × d)
```

其中：
- E_input：主动输入能量 (J)
- m：总质量 (kg)
- g：重力加速度 (m/s²)
- d：前进距离 (m)

**对比：**

| 系统 | CoT | 说明 |
|------|-----|------|
| 人类步行 | 0.05 | 极高效率 |
| V5 纯被动 | 0.0 | 无主动输入（理想斜坡） |
| V10 准被动 | 0.072 | 优秀准被动 |
| V13.7 | 0.066 | 摩擦补偿改进 |
| Atlas 机器人 | 1.5-2.0 | 典型主动机器人 |

---

## 第 2 步：Floquet 稳定性分析（V13b 工具）（15 分钟）

### 2.1 理解 Floquet 理论

**极限环稳定性：**

周期轨道的稳定性由 **Floquet 乘子** 决定：

```
λ₁, λ₂, ..., λₙ (特征值)
```

**稳定性判据：**
- 所有 |λᵢ| < 1 → 稳定极限环
- 存在 |λᵢ| > 1 → 不稳定
- |λᵢ| = 1 → 临界（边界）

**物理意义：**
- λ 越小 → 扰动衰减越快
- λ 接近 1 → 扰动衰减慢，鲁棒性差

---

### 2.2 运行长程仿真

```powershell
# 进入 V13b 目录
cd v13b_floquet_long_run

# 运行 60 秒长程仿真
python run_long_simulation.py --duration 60.0 --save-prefix long_run
```

**目的：** 收集足够多的步态周期用于统计分析

---

### 2.3 提取 Poincaré 映射

```powershell
# 提取 Heel Strike 时刻的状态
python extract_poincare_section.py \
    --input out/long_run_trajectory.csv \
    --event heel_strike \
    --output out/poincare_data.csv
```

**输出：**

```csv
cycle,hip_angle,hip_velocity,left_knee,right_knee
0,0.0523,1.234,0.102,0.087
1,0.0519,1.229,0.105,0.084
2,0.0521,1.232,0.103,0.086
...
```

---

### 2.4 计算 Floquet 乘子

```python
import pandas as pd
import numpy as np
from scipy.linalg import eig

# 读取 Poincaré 数据
df = pd.read_csv('out/poincare_data.csv')

# 提取状态向量
states = df[['hip_angle', 'hip_velocity', 'left_knee', 'right_knee']].values

# 计算平均周期
n_cycles = len(states)
print(f"Total cycles: {n_cycles}")

# 线性化 Poincaré 映射：x_{n+1} = A @ x_n
# 使用最小二乘拟合
X = states[:-1]  # x_n
Y = states[1:]   # x_{n+1}

# 求解 A
A = np.linalg.lstsq(X, Y, rcond=None)[0].T

# 计算特征值（Floquet 乘子）
eigenvalues, eigenvectors = eig(A)
floquet_multipliers = np.abs(eigenvalues)

print("\nFloquet Multipliers:")
for i, fm in enumerate(sorted(floquet_multipliers, reverse=True)):
    print(f"  λ_{i+1} = {fm:.4f}")

# 稳定性判断
max_multiplier = np.max(floquet_multipliers)
if max_multiplier < 0.95:
    print(f"\n✅ Stable limit cycle (λ_max = {max_multiplier:.4f})")
elif max_multiplier < 1.0:
    print(f"\n⚠️  Marginally stable (λ_max = {max_multiplier:.4f})")
else:
    print(f"\n❌ Unstable (λ_max = {max_multiplier:.4f})")
```

**V10 预期输出：**

```
Total cycles: 50

Floquet Multipliers:
  λ_1 = 0.9441
  λ_2 = 0.6732
  λ_3 = 0.3421
  λ_4 = 0.1234

✅ Stable limit cycle (λ_max = 0.9441)
```

---

### 2.5 可视化 Poincaré 收敛

```python
import matplotlib.pyplot as plt

# 绘制状态收敛
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

variables = ['hip_angle', 'hip_velocity', 'left_knee', 'right_knee']
titles = ['Hip Angle (rad)', 'Hip Velocity (rad/s)', 'Left Knee (rad)', 'Right Knee (rad)']

for ax, var, title in zip(axes.flat, variables, titles):
    ax.plot(df['cycle'], df[var], 'o-', markersize=4)
    ax.axhline(df[var].mean(), color='r', linestyle='--', alpha=0.5, label='Mean')
    ax.set_xlabel('Cycle')
    ax.set_ylabel(title)
    ax.legend()
    ax.grid(True)

plt.suptitle('Poincaré Section Convergence (V10)', fontsize=14)
plt.tight_layout()
plt.savefig('out/poincare_convergence.png', dpi=300)
plt.show()
```

---

## 第 3 步：跨版本对比分析（10 分钟）

### 3.1 运行跨版本分析工具

```powershell
# 进入跨版本分析目录
cd cross_version_analysis

# 对比 V10, V13.6, V13.7
python compare_versions.py \
    --versions v10 v13_6 v13_7 \
    --metrics forward cot alternations \
    --output out/comparison_report.png
```

---

### 3.2 生成性能对比表

```powershell
python generate_comparison_table.py \
    --versions v10 v13_6 v13_7 v17 \
    --output out/performance_table.csv
```

**输出：**

```csv
Version,Forward (m),CoT,Alternations,Max Torque (N·m),Success Rate (%)
V10,4.87,0.072,10,4.23,16.7
V13.6,4.52,0.074,10,3.95,11.1
V13.7,4.63,0.066,10,3.91,100.0
V17,4.58,0.068,10,3.87,95.0
```

---

### 3.3 绘制雷达图

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 读取对比表
df = pd.read_csv('out/performance_table.csv')

# 归一化指标（0-1）
metrics = ['Forward (m)', 'CoT', 'Alternations', 'Success Rate (%)']
normalized = df.copy()

for metric in metrics:
    if metric == 'CoT':
        # CoT 越小越好
        normalized[metric] = 1 - (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())
    else:
        # 其他越大越好
        normalized[metric] = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())

# 绘制雷达图
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
angles += angles[:1]

colors = ['b', 'g', 'r', 'purple']
for i, version in enumerate(df['Version']):
    values = normalized.iloc[i][metrics].tolist()
    values += values[:1]
    ax.plot(angles, values, 'o-', linewidth=2, label=version, color=colors[i])
    ax.fill(angles, values, alpha=0.1, color=colors[i])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(metrics)
ax.set_ylim(0, 1)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
ax.set_title('Version Performance Radar Chart', pad=20)

plt.tight_layout()
plt.savefig('out/radar_chart.png', dpi=300)
plt.show()
```

---

### 3.4 稳定域可视化

```powershell
# 可视化 V10 vs V13.6 的稳定域
python visualize_stability_basins.py \
    --version1 v10 \
    --version2 v13_6 \
    --output out/stability_comparison.png
```

---

## 第 4 步：生成论文级图表（5 分钟）

### 4.1 能量-距离曲线

```python
import matplotlib.pyplot as plt
import numpy as np

# 模拟不同版本的能量-距离数据
versions = ['V5\n(Passive)', 'V10\n(Quasi-Passive)', 'V13.7\n(+Compensation)', 'V17\n(+Estimation)']
cot = [0.0, 0.072, 0.066, 0.068]
forward = [5.2, 4.87, 4.63, 4.58]
colors = ['green', 'blue', 'red', 'purple']

fig, ax = plt.subplots(figsize=(10, 6))

for v, c, f, col in zip(versions, cot, forward, colors):
    ax.scatter(f, c, s=200, c=col, alpha=0.7, edgecolors='black', linewidth=2, label=v)

# 添加参考线
ax.axhline(0.05, color='gray', linestyle='--', alpha=0.5, label='Human Walking')
ax.axhline(1.5, color='gray', linestyle=':', alpha=0.5, label='Typical Robot')

ax.set_xlabel('Forward Distance (m)', fontsize=14)
ax.set_ylabel('Cost of Transport (CoT)', fontsize=14)
ax.set_title('Energy Efficiency vs Performance', fontsize=16)
ax.legend(fontsize=12)
ax.grid(True, alpha=0.3)
ax.set_ylim(-0.05, 2.0)

plt.tight_layout()
plt.savefig('out/paper_figure_energy.png', dpi=300, bbox_inches='tight')
plt.show()
```

---

### 4.2 稳定性演化图

```python
# Floquet 乘子演化
versions = ['V5', 'V10', 'V13.6', 'V13.7', 'V17']
lambda_max = [0.912, 0.944, 0.891, 0.873, 0.856]

fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(versions, lambda_max, 'o-', linewidth=2, markersize=10, color='blue')
ax.axhline(1.0, color='r', linestyle='--', linewidth=2, label='Stability Boundary')
ax.axhline(0.95, color='orange', linestyle=':', linewidth=1, label='Marginal Stability')

ax.set_xlabel('Version', fontsize=14)
ax.set_ylabel('Maximum Floquet Multiplier', fontsize=14)
ax.set_title('Limit Cycle Stability Evolution', fontsize=16)
ax.legend(fontsize=12)
ax.grid(True, alpha=0.3)
ax.set_ylim(0.8, 1.1)

plt.tight_layout()
plt.savefig('out/paper_figure_stability.png', dpi=300, bbox_inches='tight')
plt.show()
```

---

## 练习任务

### 任务 1: 分析 V14b 摆臂的能量贡献

**问题：** V14b 引入被动摆臂后，CoT 是否改善？

**步骤：**
1. 运行 V14b 能量分析
2. 对比 V13.6（无摆臂）vs V14b（有摆臂）
3. 分析摆臂的动能贡献

```powershell
cd v12_energy_cot_analysis
python analyze_energy_v14b.py --duration 12.0
```

---

### 任务 2: 验证 V17 状态估计不影响稳定性

**问题：** 加入传感器噪声后，Floquet 乘子是否变化？

**步骤：**
1. 运行 V13.7（理想传感器）长程仿真
2. 运行 V17（真实传感器）长程仿真
3. 对比 Floquet 乘子

---

### 任务 3: 绘制参数空间与稳定域

**问题：** foot_radius vs leg_length 的成功域边界对应什么 Floquet 乘子？

**步骤：**
1. 扫描参数空间（5×5 网格）
2. 对每个成功配置计算 Floquet 乘子
3. 绘制 3D 图：(foot_radius, leg_length, λ_max)

---

## 高级技巧

### 技巧 1: 批量分析脚本

```python
# batch_analysis.py
import subprocess
import json

versions = ['v10', 'v13_6', 'v13_7', 'v17']
results = {}

for version in versions:
    print(f"Analyzing {version}...")
    
    # 运行仿真
    subprocess.run([
        'python', f'{version}/simulate_{version}.py',
        '--duration', '12.0',
        '--save-prefix', f'batch_{version}'
    ])
    
    # 读取结果
    with open(f'{version}/out/batch_{version}_summary.json') as f:
        results[version] = json.load(f)

# 保存汇总
with open('batch_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

---

### 技巧 2: 自动生成 LaTeX 表格

```python
import pandas as pd

df = pd.read_csv('out/performance_table.csv')

# 生成 LaTeX 表格
latex = df.to_latex(index=False, float_format="%.2f", caption="Version Performance Comparison", label="tab:comparison")

with open('out/table_for_paper.tex', 'w') as f:
    f.write(latex)

print("LaTeX table saved to out/table_for_paper.tex")
```

---

### 技巧 3: 交互式 Jupyter Notebook

```python
# 在 Jupyter 中运行
import ipywidgets as widgets
from IPython.display import display

def analyze_version(version):
    # 动态加载数据
    df = pd.read_csv(f'{version}/out/trajectory.csv')
    plt.figure(figsize=(10, 4))
    plt.plot(df['time'], df['hip_x'])
    plt.title(f'{version} Hip Trajectory')
    plt.show()

version_selector = widgets.Dropdown(
    options=['v10', 'v13_6', 'v13_7', 'v17'],
    description='Version:',
)

widgets.interact(analyze_version, version=version_selector)
```

---

## 论文写作建议

### 章节 1: 能量效率

**推荐图表：**
- 能量瀑布图（Waterfall chart）
- CoT vs Forward distance scatter plot
- 与人类/其他机器人的对比条形图

**关键论述：**
- V13.7 CoT=0.066 接近人类步行（0.05）
- 准被动设计的能效优势（vs 主动机器人 CoT~1.5）
- 摩擦补偿的能量贡献（V13.6 → V13.7）

---

### 章节 2: 稳定性分析

**推荐图表：**
- Poincaré section 收敛图
- Floquet 乘子演化图
- 参数空间稳定域热力图

**关键论述：**
- V10 λ_max=0.944 接近稳定边界
- V17 传感器噪声不影响稳定性（λ_max 仅增加 1.7%）
- 理论预测与仿真一致性

---

### 章节 3: 版本演化

**推荐图表：**
- Timeline 演化图
- 雷达图（多维性能对比）
- 技术路线图（Decision tree）

**关键论述：**
- V01-V25 系统化迭代过程
- 否定结果的学术价值（V18-V20）
- 从理论到硬件的完整链条

---

## 相关资源

- **V12 能量分析**: `v12_energy_cot_analysis/README.md`
- **V13b Floquet 分析**: `v13b_floquet_long_run/README.md`
- **跨版本分析工具**: `cross_version_analysis/README.md`
- **Dashboard**: `dashboard/index.html`
- **论文精读笔记**: `references/passive_dynamic_walking/论文中文精读翻译笔记.md`

---

**最后更新**: 2026-06-05

**下一步**: 查看 Tutorial 05（开发者贡献指南）或开始撰写论文。

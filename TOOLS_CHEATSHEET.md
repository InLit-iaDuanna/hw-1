# hw-1 工具速查表

**所有关键命令的快速参考，按工具类型分类。**

---

## 🚀 环境与基础

### 激活虚拟环境

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate
```

### 验证环境

```powershell
# Python 版本
python --version

# MuJoCo 版本
python -c "import mujoco; print('MuJoCo:', mujoco.__version__)"

# 依赖检查
pip list | Select-String "mujoco|numpy|matplotlib"
```

### 安装依赖

```powershell
pip install -r requirements.txt
```

---

## 🎬 仿真运行

### V13.7（最推荐）

```powershell
# 基础运行
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# 禁用摩擦补偿（对比实验）
python v13_7_friction_compensation\simulate_v13_7.py --no-compensation

# 自定义电机
python v13_7_friction_compensation\simulate_v13_7.py --motor ec_i40

# 保存结果
python v13_7_friction_compensation\simulate_v13_7.py --save-prefix my_test
```

### V10（足踝滚动基线）

```powershell
python v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_gait_v10.py --duration 12.0
```

### V13.6（FSM 控制）

```powershell
python v13_6_event_driven_fsm\simulate_v136.py --duration 12.0
```

### V17（状态估计）

```powershell
# 默认噪声
python v17_state_estimation\simulate_v17.py --duration 12.0

# 3× 噪声（critical）
python v17_state_estimation\simulate_v17.py --noise-scale 3.0
```

---

## 👁️ 可视化查看

### 实时查看（MuJoCo Viewer）

```powershell
# V13.7
python v13_7_friction_compensation\view_v13_7.py

# V10
python v10_rolling_foot_biomimetic_gait\view_rolling_foot_gait_v10.py

# V13.6
python v13_6_event_driven_fsm\view_v136.py
```

**操作提示：**
- 鼠标左键：旋转
- 鼠标右键：平移
- 滚轮：缩放
- 空格：暂停/播放
- ESC：退出

---

### 渲染视频

```powershell
# V13.7
python v13_7_friction_compensation\render_v13_7.py

# 输出：v13_7_friction_compensation\out\v137_walk.mp4
```

---

## 📊 Dashboard 可视化

### 打开 Dashboard

```powershell
# 用默认浏览器打开
start dashboard\index.html

# 用 Chrome 打开
start chrome dashboard\index.html
```

### Dashboard 视图模式

- **Grid View**：卡片网格，内联显示关键指标
- **Timeline View**：按 Phase 分组的时间线
- **Compare View**：版本对比（选择 2-4 个版本）
- **Trends View**：能量效率与性能趋势图
- **Heatmap View**：参数敏感性热力图

### 更新 Dashboard

```powershell
# 编辑数据文件
notepad dashboard\data.js

# 查找对应版本，修改 status/findings 等字段
```

---

## 🔬 跨版本分析工具

### 位置

```powershell
cd cross_version_analysis
```

### 版本性能对比

```powershell
# 对比所有版本
python compare_versions.py

# 对比指定版本
python compare_versions.py --versions v10 v13_6 v13_7 v17

# 生成 Markdown 报告
python compare_versions.py --output comparison_report.md
```

### 稳定域可视化

```powershell
# 可视化参数空间
python visualize_stability_basins.py

# 指定版本
python visualize_stability_basins.py --version v13
```

### 能效排行

```powershell
# 按 CoT 排序
python energy_efficiency_ranking.py

# 生成图表
python energy_efficiency_ranking.py --plot
```

### 全流程分析

```powershell
# 运行所有分析（一键生成）
python run_all_analyses.py

# 输出目录：outputs/
```

---

## ⚡ 基准测试（Benchmarks）

### 位置

```powershell
cd benchmarks
```

### 运行基准测试

```powershell
# 所有版本
python benchmark_runner.py

# 指定版本
python benchmark_runner.py --versions v10 v13_7 v17

# 自定义输出文件
python benchmark_runner.py --output results_custom.json

# 从已有结果生成报告
python generate_report.py --input results_20260604.json
```

### 性能回归检测

```powershell
# 与上次结果对比
python benchmark_runner.py --compare

# 自定义回归阈值（默认 10%）
python benchmark_runner.py --compare --threshold 5
```

---

## 🧪 CI/CD 自动化

### 位置

```powershell
cd ci
```

### 运行测试

```powershell
# 所有测试（带覆盖率）
python run_tests.py

# 并行运行（加速）
python run_tests.py --parallel

# 只运行单元测试
python run_tests.py --unit-only

# 只运行回归测试
python run_tests.py --regression-only
```

### 代码质量检查

```powershell
# 所有质量检查
python run_quality_checks.py

# 自动修复格式问题
python run_quality_checks.py --fix

# 只运行特定工具
python run_quality_checks.py --tools black flake8

# 严格模式（任何警告都报错）
python run_quality_checks.py --strict
```

### 完整 CI 流程

```powershell
# 运行完整 CI
python run_ci.py

# 快速模式（跳过慢速测试）
python run_ci.py --fast

# 自动修复代码问题
python run_ci.py --fix

# 跳过基准测试
python run_ci.py --skip-benchmarks

# 生成文档
python run_ci.py --docs
```

---

## 🎛️ 参数调优

### 位置

```powershell
cd parameter_tuner
```

### 2D 网格搜索

```powershell
# 默认参数（foot_radius × leg_length）
python grid_search_2d.py

# 自定义参数
python grid_search_2d.py --param1 foot_radius --param2 leg_length

# 自定义范围
python grid_search_2d.py \
    --param1 foot_radius --range1 0.08 0.12 5 \
    --param2 leg_length --range2 0.45 0.55 3

# 保存结果
python grid_search_2d.py --output results_custom.json
```

### 可视化搜索结果

```powershell
# 生成热力图
python visualize_grid_search.py --input results_custom.json

# 保存图片
python visualize_grid_search.py --input results_custom.json --output heatmap.png
```

### 摩擦参数扫描

```powershell
# 扫描 τ_C（库仑摩擦）
python scan_tau_c.py --range 0.0 0.30 10

# 有补偿
python scan_tau_c.py --range 0.0 0.30 10 --compensation true

# 无补偿
python scan_tau_c.py --range 0.0 0.30 10 --compensation false
```

### 贝叶斯优化

```powershell
# 需要先安装 scikit-optimize
pip install scikit-optimize

# 运行优化（100 次迭代）
python bayesian_optimization.py --n_calls 100

# 自定义参数
python bayesian_optimization.py --n_calls 100 --params foot_radius leg_length tau_0 tau_1
```

---

## 📈 MATLAB 汇总（V01-V13）

### 运行 MATLAB 脚本

```matlab
% 在 MATLAB 中执行
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')

% 运行所有报告
run_all_gait_reports

% 或单独生成
generate_v10_report
generate_v13_report
```

### Python → MATLAB 数据转换

```powershell
cd matlab-v01-v13-gait

# 自动化工作流（Python + MATLAB）
python export_python_to_mat.py
# 然后在 MATLAB 中运行 run_all_gait_reports
```

---

## 🔍 搜索与查找

### 查找文件

```powershell
# 查找所有 simulate_*.py
Get-ChildItem -Recurse -Filter "simulate_*.py" | Select-Object FullName

# 查找特定版本的文件
Get-ChildItem -Path v13_7_friction_compensation -Recurse

# 查找 README
Get-ChildItem -Recurse -Filter "README.md" | Select-Object FullName
```

### 搜索内容

```powershell
# 搜索 "control_v136"
Select-String -Path *.py -Pattern "control_v136" -Recurse

# 搜索 "CoT" 在所有 JSON 文件中
Select-String -Path */out/*.json -Pattern "CoT" -Recurse
```

---

## 📝 查看结果

### JSON 摘要

```powershell
# 查看 V13.7 结果
notepad v13_7_friction_compensation\out\v137_mx64ar_full_compensation_summary.json

# 快速提取关键指标（PowerShell）
$json = Get-Content v13_7_friction_compensation\out\v137_mx64ar_full_compensation_summary.json | ConvertFrom-Json
Write-Host "Success: $($json.success)"
Write-Host "Forward: $($json.forward_distance) m"
Write-Host "CoT: $($json.cot_mechanical)"
```

### CSV 轨迹

```powershell
# 查看 CSV
notepad v13_7_friction_compensation\out\v137_mx64ar_full_compensation_trajectory.csv

# 用 Excel 打开
start excel v13_7_friction_compensation\out\v137_mx64ar_full_compensation_trajectory.csv
```

### Python 快速分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('v13_7_friction_compensation/out/v137_mx64ar_full_compensation_trajectory.csv')

# 绘制髋部轨迹
plt.plot(df['time'], df['hip_x'])
plt.xlabel('Time (s)')
plt.ylabel('Hip X (m)')
plt.title('Hip Position')
plt.grid(True)
plt.show()
```

---

## 🛠️ 故障排查

### 重置环境

```powershell
# 删除虚拟环境
Remove-Item -Recurse -Force .venv-mujoco

# 重新创建
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\activate
pip install -r requirements.txt
```

### 清理输出

```powershell
# 清理所有 out/ 目录（谨慎！）
Get-ChildItem -Recurse -Directory -Filter "out" | Remove-Item -Recurse -Confirm

# 清理特定版本
Remove-Item -Recurse v13_7_friction_compensation\out\*
```

### 检查文件完整性

```powershell
# 检查关键文件是否存在
Test-Path v13_7_friction_compensation\model_v13_7.xml
Test-Path v13_7_friction_compensation\simulate_v13_7.py
Test-Path dashboard\index.html
```

### Git 恢复文件

```powershell
# 恢复单个文件
git checkout v13_7_friction_compensation\model_v13_7.xml

# 恢复整个目录
git checkout v13_7_friction_compensation/
```

---

## 📚 文档快速访问

### 核心文档

```powershell
# QUICKSTART（快速入门）
notepad QUICKSTART.md

# VERSION_MILESTONES（版本里程碑）
notepad VERSION_MILESTONES.md

# ROADMAP（长期规划）
notepad ROADMAP.md

# PROJECT_PROGRESS（进度总览）
notepad PROJECT_PROGRESS.md
```

### 版本文档

```powershell
# V13.7 README
notepad v13_7_friction_compensation\README.md

# V16 README
notepad v16_motor_dynamics\README.md

# V22 硬件规格
notepad v22_hardware_design\HARDWARE_SPEC.md
```

### 教程

```powershell
# 教程索引
notepad tutorials\README.md

# Tutorial 01
notepad tutorials\tutorial_01_run_first_simulation.md

# Tutorial 02
notepad tutorials\tutorial_02_understand_fsm_control.md

# Tutorial 03
notepad tutorials\tutorial_03_parameter_tuning.md
```

---

## ⌨️ 常用快捷方式

### PowerShell 别名（可选）

在 PowerShell 配置文件中添加：

```powershell
# 编辑配置文件
notepad $PROFILE

# 添加以下内容：
function hw1 { cd D:\Dunna\Documents\hw-1 }
function hw1-activate { cd D:\Dunna\Documents\hw-1; .\.venv-mujoco\Scripts\activate }
function hw1-dashboard { start chrome D:\Dunna\Documents\hw-1\dashboard\index.html }
function hw1-v137 { cd D:\Dunna\Documents\hw-1; .\.venv-mujoco\Scripts\python.exe v13_7_friction_compensation\simulate_v13_7.py --duration 12.0 }
```

使用：

```powershell
# 进入项目并激活环境
hw1-activate

# 打开 Dashboard
hw1-dashboard

# 运行 V13.7
hw1-v137
```

---

## 🎯 快速任务清单

### 新用户上手（30 分钟）

```powershell
# 1. 激活环境
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\activate

# 2. 运行 V13.7
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0

# 3. 打开 Dashboard
start dashboard\index.html

# 4. 查看教程
notepad tutorials\tutorial_01_run_first_simulation.md
```

---

### 答辩准备（1 小时）

```powershell
# 1. 打开 Dashboard
start dashboard\index.html
# → 截图 Timeline + Heatmap

# 2. 查看关键动画
ls v05_hybrid_compass_proof\out\*.mp4
ls v10_rolling_foot_biomimetic_gait\out\*.mp4
ls v13_7_friction_compensation\out\*.mp4

# 3. 复习关键数字
notepad VERSION_MILESTONES.md

# 4. 准备对比实验
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0
python v13_7_friction_compensation\simulate_v13_7.py --no-compensation --duration 12.0
```

---

### 开发工作流

```powershell
# 1. 激活环境
hw1-activate

# 2. 运行测试（确保环境干净）
cd ci
python run_tests.py --fast

# 3. 开发...

# 4. 提交前完整检查
python run_ci.py

# 5. 更新 Dashboard
notepad dashboard\data.js
```

---

## 🔗 相关资源

- **QUICKSTART.md**：30 分钟快速入门
- **VERSION_MILESTONES.md**：关键版本里程碑
- **tutorials/README.md**：交互式教程索引
- **dashboard/README.md**：Dashboard 使用说明
- **cross_version_analysis/README.md**：跨版本分析工具
- **benchmarks/README.md**：基准测试框架
- **ci/README.md**：CI/CD 自动化

---

**提示：** 此速查表适合打印或保存为书签，快速查找常用命令。

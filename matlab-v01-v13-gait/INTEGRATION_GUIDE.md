# Python → MATLAB Data Integration

## 概览

简化的 Python → MATLAB 数据流，自动导出仿真数据并生成报告图。

## 快速开始

### 一键运行（推荐）

```powershell
cd D:\Dunna\Documents\hw-1\matlab-v01-v13-gait
.\sync_and_analyze.ps1
```

这会自动完成：
1. 从 Python 仿真输出导出 .mat 文件
2. 在 MATLAB 中生成标准报告图

### 分步运行

**仅导出 Python 数据：**

```powershell
.\sync_data.ps1           # 导出所有版本
.\sync_data.ps1 v10       # 仅导出 v10
```

**仅生成 MATLAB 报告：**

```powershell
.\run_matlab_analysis.ps1
```

或在 MATLAB 中手动运行：

```matlab
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
run_matlab_analysis_batch
```

## 文件结构

```
matlab-v01-v13-gait/
├── python_to_matlab_exporter.py        # Python 导出工具
├── load_python_data.m                   # MATLAB 数据加载器
├── generate_matlab_report_from_python.m # MATLAB 报告生成
├── sync_data.ps1                        # PowerShell: 导出数据
├── run_matlab_analysis.ps1              # PowerShell: 运行 MATLAB
├── sync_and_analyze.ps1                 # PowerShell: 完整流程
├── run_matlab_analysis_batch.m          # MATLAB: 批量处理
├── python_exports/                      # Python 导出的 .mat 文件
│   ├── v01/v01_python_export.mat
│   ├── v10/v10_python_export.mat
│   └── ...
└── out/                                 # MATLAB 报告输出
    ├── v01/v01_python_report.png
    ├── v10/v10_python_report.png
    └── ...
```

## 数据格式

### Python 导出的 .mat 文件结构

```matlab
version        % 版本 ID (字符串)
title          % 版本标题 (字符串)
data           % 结构体，包含所有时间序列数据
  .time        % 时间向量 (nx1)
  .hip_x       % 髋部 x 坐标 (nx1)
  .hip_z       % 髋部 z 坐标 (nx1)
  .left_hip    % 左髋角度 (nx1)
  .right_hip   % 右髋角度 (nx1)
  .left_contact  % 左脚接触 (nx1)
  .right_contact % 右脚接触 (nx1)
  ...          % 其他列
params         % 仿真参数 (结构体)
column_names   % 列名列表 (cell array)
n_rows         % 行数
n_cols         % 列数
duration_s     % 仿真时长 (秒)
forward_distance_m % 前进距离 (米)
left_touchdowns    % 左脚触地次数
right_touchdowns   % 右脚触地次数
```

### 在 MATLAB 中使用

```matlab
% 加载数据
[T, metadata] = load_python_data('python_exports/v10/v10_python_export.mat');

% 访问时间序列
plot(T.time, T.hip_x);
xlabel('time / s');
ylabel('hip x / m');

% 访问元数据
disp(metadata.version);
disp(metadata.params);
fprintf('Duration: %.2f s\n', metadata.duration_s);
fprintf('Distance: %.2f m\n', metadata.forward_distance_m);

% 生成报告
generate_matlab_report_from_python('v10', ...
    'python_exports/v10/v10_python_export.mat', ...
    'out/v10');
```

## 报告类型

工具自动识别数据类型并生成相应报告：

### 1. 时间序列报告 (V01-V11)
- 髋部前进轨迹
- 左右脚接触时序
- 关节角度变化
- 相位图

### 2. 能量汇总报告 (V12)
- Cost of Transport
- 主动输入能量
- 前进距离
- 触地次数

### 3. 参数敏感性报告 (V13)
- 成功率分布
- 成功运行数量
- CoT 范围统计

## 前置依赖

### Python 依赖

```powershell
pip install scipy
```

`scipy` 用于生成 MATLAB 兼容的 .mat 文件。

### MATLAB 依赖

- MATLAB R2020a 或更高版本（推荐 R2023b+）
- 无需额外工具箱

## 故障排查

### Python 导出失败

**问题：** `scipy not installed`

```powershell
# 使用项目虚拟环境
.venv-mujoco\Scripts\pip install scipy

# 或使用系统 Python
pip install scipy
```

**问题：** `No CSV data found`

确保已运行仿真脚本生成输出文件：

```powershell
cd D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait
python simulate_rolling_foot_gait_v10.py
```

### MATLAB 报告生成失败

**问题：** `MATLAB not found`

手动在 MATLAB 中运行：

```matlab
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
run_matlab_analysis_batch
```

**问题：** `File not found`

确保先运行 `sync_data.ps1` 导出数据。

## 高级用法

### 单独导出特定版本

```python
python python_to_matlab_exporter.py --version v10
```

### 在 MATLAB 中自定义报告

```matlab
% 加载数据
[T, meta] = load_python_data('python_exports/v10/v10_python_export.mat');

% 自定义绘图
figure;
subplot(2,1,1);
plot(T.time, T.hip_x);
title(sprintf('%s: Hip Trajectory', meta.version));

subplot(2,1,2);
plot(T.time, rad2deg(T.left_hip), 'DisplayName', 'left');
hold on;
plot(T.time, rad2deg(T.right_hip), 'DisplayName', 'right');
legend;
title('Hip Angles');
```

### Python 中直接调用

```python
from matlab_v01_v13_gait.python_to_matlab_exporter import export_version
from pathlib import Path

repo_root = Path("D:/Dunna/Documents/hw-1")
output_dir = Path("D:/Dunna/Documents/hw-1/matlab-v01-v13-gait/python_exports")

export_version(
    version_id="v10",
    version_dir=repo_root / "v10_rolling_foot_biomimetic_gait",
    output_dir=output_dir,
    version_title="V10 rolling-foot biomimetic gait"
)
```

## 与现有工作流对比

### 旧工作流（手动）
1. 在 Python 中运行仿真
2. 手动检查 CSV 位置
3. 在 MATLAB 中手动指定路径
4. 运行 `run_vXX_report.m`
5. 检查输出是否正确

### 新工作流（自动）
1. 运行 `sync_and_analyze.ps1`
2. 完成

节省时间：约 80%

## 参考

- 原有 MATLAB 脚本：`gait_version_configs.m`, `run_single_gait_report.m`
- Python 仿真脚本：各版本目录中的 `simulate_*.py`
- 输出规范：CSV 时间序列 + JSON 参数汇总

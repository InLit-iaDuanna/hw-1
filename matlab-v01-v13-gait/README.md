# MATLAB V1-V13 Gait Data Package

这个文件夹统一读取 V1-V13 的仿真和分析数据，并导出 MATLAB 表格、`.mat` 数据包和报告图。

## 快速开始（推荐：自动化工作流）

### 一键运行 Python → MATLAB 完整流程

```powershell
cd D:\Dunna\Documents\hw-1\matlab-v01-v13-gait
.\sync_and_analyze.ps1
```

自动完成：
1. 从 Python 仿真结果导出 .mat 文件
2. 在 MATLAB 中生成标准报告图

详细文档见：[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

### 仅导出 Python 数据

```powershell
.\sync_data.ps1           # 导出所有版本
.\sync_data.ps1 v10       # 仅导出 v10
```

### 仅生成 MATLAB 报告

```powershell
.\run_matlab_analysis.ps1
```

## 传统工作流（手动运行）

如果需要手动控制每个步骤，可使用原有 MATLAB 脚本：

```matlab
cd('D:\Dunna\Documents\hw-1\matlab-v01-v13-gait')
run_all_gait_reports
```

单独运行：

```matlab
run_v11_report
run_v12_report
run_v13_report
```

## 输出

每个版本会在 `out/vXX/` 下生成：

- `vXX_data_table.csv`：MATLAB 读取后的数据表副本。
- `vXX_data.mat`：MATLAB 原生数据包，包含 `T`、`cfg` 和 `paramsText`。
- `vXX_report.png`：报告图。
- `vXX_python_export.mat`：Python 导出的原始数据（新）。
- `vXX_python_report.png`：基于 Python 导出数据的报告图（新）。

V1-V11 使用统一 4 格步态报告图。V12 使用能量/CoT 汇总图。V13 使用参数敏感性图谱汇总图。

## 工具说明

### Python 工具

- `python_to_matlab_exporter.py`：自动从 Python CSV/JSON 导出 .mat 文件
- `sync_data.ps1`：PowerShell 脚本，批量导出所有版本

### MATLAB 工具

- `load_python_data.m`：加载 Python 导出的 .mat 文件
- `generate_matlab_report_from_python.m`：从 Python 数据生成报告
- `run_matlab_analysis_batch.m`：批量处理所有版本
- `run_matlab_analysis.ps1`：PowerShell 脚本，自动调用 MATLAB

### 完整流程

- `sync_and_analyze.ps1`：一键运行完整 Python → MATLAB 流程

## 口径

V5 是纯被动极限环证明依据。V8-V11 含主动补能或主动稳定，只能写作准被动或工程扩展。V12/V13 是分析层，不是新的物理步态模型。

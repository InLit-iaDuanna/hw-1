# Analysis Pipeline for hw-1 Gait Simulation Project

标准化的实验数据分析管道，从原始仿真数据到最终报告的自动化流程。

## 目录结构

```
analysis_pipeline/
├── pipeline_config.yaml      # 管道配置文件
├── data_loader.py            # 数据加载模块
├── preprocessor.py           # 数据预处理模块
├── feature_extractor.py      # 特征提取模块
├── statistical_analyzer.py   # 统计分析模块
├── visualizer.py             # 可视化模块
├── report_generator.py       # 报告生成模块
├── run_pipeline.py           # 主运行脚本
└── README.md                 # 本文件
```

## 功能特性

### 1. 数据预处理
- **异常值检测**: IQR、Z-score、Isolation Forest
- **噪声滤波**: Savitzky-Golay、Butterworth、中值滤波
- **缺失数据插值**: 线性、三次样条、B样条
- **时间对齐**: 重采样到统一时间网格

### 2. 特征提取
- **步态周期特征**: 周期长度、步长、步频、接触比例、左右对称性
- **能量特征**: CoT、机械功、输入能量、功率统计
- **稳定性特征**: 收敛率、极限环半径、相位裕度
- **接触特征**: 接触时间、力峰值、地面间隙
- **运动学特征**: 髋关节行程、膝关节屈曲、速度峰值

### 3. 统计分析
- **显著性检验**: t-test、Mann-Whitney U、ANOVA
- **效应量**: Cohen's d、Eta-squared、Rank-biserial correlation
- **置信区间**: 95%置信区间计算
- **敏感性分析**: Pearson/Spearman 相关性、参数扫描

### 4. 自动可视化
- **时间序列图**: 关节角度、速度、力矩、功率
- **相位图**: 状态空间轨迹、Poincaré 映射
- **对比图**: 柱状图、箱线图、小提琴图
- **统计图**: 相关性热图、敏感性热图

### 5. 报告生成
- **Markdown**: 带嵌入图表的 Markdown 报告
- **HTML**: 交互式网页报告
- **LaTeX**: 论文用表格

## 快速开始

### 安装依赖

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m pip install pyyaml
```

### 配置管道

编辑 `pipeline_config.yaml` 指定数据源、分析步骤和输出格式。

### 运行完整管道

```powershell
# 分析所有配置的版本
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\run_pipeline.py

# 分析指定版本
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\run_pipeline.py --versions v09_stable v10_rolling

# 指定输出目录
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\run_pipeline.py --output ./my_analysis_results
```

### 单独运行模块

```powershell
# 测试数据加载
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\data_loader.py

# 测试预处理
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\preprocessor.py

# 测试特征提取
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\feature_extractor.py

# 测试统计分析
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\statistical_analyzer.py

# 测试可视化
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\visualizer.py

# 测试报告生成
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\report_generator.py
```

## 配置说明

### 数据源配置

在 `pipeline_config.yaml` 中添加新版本：

```yaml
data_sources:
  v12_energy:
    path: "D:/Dunna/Documents/hw-1/v12_energy_cot_analysis/out/v12_data.csv"
    label: "V12 能量分析"
    version: "v12"
    type: "analysis"
```

### 预处理配置

```yaml
preprocessing:
  outlier_detection:
    method: "iqr"  # iqr, zscore, isolation_forest
    iqr_factor: 1.5

  filtering:
    enabled: true
    method: "savgol"  # savgol, butterworth, median
    window_length: 11
    polyorder: 3

  interpolation:
    method: "cubic"  # linear, cubic, spline
    fill_gaps: true
```

### 特征选择

在 `feature_extraction` 中启用/禁用特征类别：

```yaml
feature_extraction:
  gait_cycle:
    - period_length
    - stride_length
    - duty_factor
  
  energy:
    - cost_of_transport
    - mechanical_work
```

### 统计分析配置

```yaml
statistical_analysis:
  significance_tests:
    - t_test
    - mann_whitney
  
  confidence_level: 0.95
  
  comparison_groups:
    - ["v09_stable", "v10_rolling"]
    - ["v11_flat", "v11_terrain"]
```

## 输出结构

```
reports/
├── analysis_report.md        # Markdown 报告
├── analysis_report.html      # HTML 报告
├── features_table.tex        # LaTeX 表格
└── figures/                  # 图表目录
    ├── v09_stable_gait_cycle.png
    ├── v09_stable_phase.png
    ├── v10_rolling_gait_cycle.png
    ├── v10_rolling_phase.png
    ├── feature_comparison.png
    └── correlation_heatmap.png
```

## 典型工作流

### 1. 版本对比分析

```powershell
# 对比 V09 和 V10
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\run_pipeline.py `
    --versions v09_stable v10_rolling `
    --output ./reports/v09_v10_comparison
```

### 2. 参数扫描分析

如果有多个参数变体数据，配置为不同版本并运行敏感性分析。

### 3. 批量处理

```powershell
# 分析所有 V11 变体
.\.venv-mujoco\Scripts\python.exe .\analysis_pipeline\run_pipeline.py `
    --versions v11_flat v11_terrain v11_hard
```

## Python API 使用

```python
from pathlib import Path
from run_pipeline import AnalysisPipeline

# 初始化管道
config_path = Path("analysis_pipeline/pipeline_config.yaml")
pipeline = AnalysisPipeline(config_path)

# 运行完整流程
results = pipeline.run_full_pipeline(["v09_stable", "v10_rolling"])

# 访问结果
features = results["features"]
for version, feat in features.items():
    print(f"{version}: CoT = {feat.cost_of_transport:.4f}")
```

## 自定义扩展

### 添加新特征

在 `feature_extractor.py` 中添加新方法：

```python
def extract_my_custom_feature(self, gait_data: GaitData) -> dict[str, Any]:
    features = {}
    # 自定义特征计算
    features["my_metric"] = calculate_something(gait_data)
    return features
```

然后在 `extract_all_features()` 中调用。

### 添加新可视化

在 `visualizer.py` 中添加新绘图方法：

```python
def plot_my_custom_chart(self, data, output_path):
    fig, ax = plt.subplots()
    # 自定义绘图
    plt.savefig(output_path, dpi=self.figure_dpi)
    plt.close()
```

### 添加新统计检验

在 `statistical_analyzer.py` 中添加新方法：

```python
def my_statistical_test(self, group1, group2):
    # 自定义统计检验
    statistic, p_value = my_test(group1, group2)
    return StatisticalTest(...)
```

## 常见问题

### Q: 数据文件找不到？
A: 检查 `pipeline_config.yaml` 中的路径是否正确，使用绝对路径。

### Q: 缺少某些特征？
A: 确保原始 CSV 包含必要的列（time, joint angles, contacts, torques）。

### Q: 图表中文乱码？
A: 安装 SimHei 字体或修改 `visualizer.py` 中的字体设置。

### Q: 内存不足？
A: 对大数据集启用缓存和分批处理，或降低采样率。

## 性能优化

- **并行处理**: 配置 `execution.parallel: true`
- **缓存中间结果**: 启用 `execution.cache_intermediate: true`
- **降采样**: 在预处理中启用 `time_alignment` 并设置合理的 `resample_frequency`

## 参考文献

管道设计参考了以下最佳实践：
- 步态分析: Winter DA. *Biomechanics and Motor Control of Human Movement*
- 统计方法: Cohen J. *Statistical Power Analysis for the Behavioral Sciences*
- 信号处理: Oppenheim AV, Schafer RW. *Discrete-Time Signal Processing*

## 许可

本代码为 hw-1 项目内部工具，仅供学术研究使用。

## 更新日志

- **2026-06-04**: 初始版本发布，支持 V09-V11 数据分析

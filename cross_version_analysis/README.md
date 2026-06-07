# 跨版本分析工具集

对比和可视化 HW-1 项目 V01-V24 的性能演化。

## 工具清单

### 1. `version_comparator.py` - 版本性能对比
**功能:**
- 扫描各版本目录，提取关键指标（前向距离、交替步数、CoT、成功率）
- 生成版本对比表格 CSV
- 绘制性能演化趋势图
- 生成版本时间线

**输出:**
- `version_comparison.csv` - 完整对比表格
- `forward_distance_trend.png` - 前向距离演化
- `cot_trend.png` - 运输成本趋势
- `success_rate_trend.png` - 稳定性趋势
- `version_timeline.png` - 版本里程碑时间线

**用法:**
```powershell
cd D:\Dunna\Documents\hw-1\cross_version_analysis
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" version_comparator.py
```

---

### 2. `stability_domain_visualizer.py` - 稳定域可视化
**功能:**
- 读取 V13 参数敏感度图集数据（7 个切片）
- 生成 2D 稳定域热图（成功/失败 + CoT 分布）
- 生成 3D 稳定域表面图
- 绘制各切片成功率对比
- 参数相关性热图

**输出:**
- `v13_stability_*.png` - 各切片 2D 稳定域（8 张）
- `v13_stability_3d_*.png` - 3D 稳定域表面（4 张）
- `v13_slice_success_rates.png` - 切片成功率对比
- `v13_parameter_correlation.png` - 参数相关性热图

**用法:**
```powershell
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" stability_domain_visualizer.py
```

---

### 3. `energy_efficiency_ranking.py` - 能量效率排行
**功能:**
- 统计各版本 CoT（Cost of Transport）
- 生成能效排行榜（从低到高）
- 绘制 CoT 演化趋势（带关键里程碑注释）
- V13 各切片 CoT 分布箱线图
- Top 5 版本综合性能雷达图

**输出:**
- `energy_efficiency_ranking.csv` - 排行表格
- `cot_ranking.png` - 能效排行榜
- `cot_evolution_annotated.png` - CoT 演化趋势
- `v13_cot_distribution.png` - V13 CoT 箱线图
- `top5_performance_radar.png` - Top 5 雷达图

**用法:**
```powershell
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" energy_efficiency_ranking.py
```

---

### 4. `generate_comprehensive_report.py` - 综合报告生成器
**功能:**
- 依次运行以上 3 个工具
- 汇总所有分析结果
- 生成 HTML 综合报告（包含所有图表）

**输出:**
- `comprehensive_report.html` - 完整 HTML 报告（可直接浏览器打开）

**用法:**
```powershell
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" generate_comprehensive_report.py
```

**推荐:** 直接运行此工具，一次性生成所有分析内容。

---

## 快速开始

### 方法 1: 一键生成完整报告
```powershell
cd D:\Dunna\Documents\hw-1\cross_version_analysis
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" generate_comprehensive_report.py
```

生成后在浏览器中打开 `out/comprehensive_report.html`。

### 方法 2: 单独运行某个工具
```powershell
# 仅对比版本性能
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" version_comparator.py

# 仅可视化稳定域
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" stability_domain_visualizer.py

# 仅分析能效排行
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" energy_efficiency_ranking.py
```

---

## 输出目录结构

```
cross_version_analysis/
├── out/                              # 所有输出文件
│   ├── comprehensive_report.html     # HTML 综合报告 ⭐
│   ├── version_comparison.csv        # 版本对比表格
│   ├── energy_efficiency_ranking.csv # 能效排行表
│   ├── version_timeline.png          # 版本时间线
│   ├── forward_distance_trend.png    # 前向距离趋势
│   ├── cot_trend.png                 # CoT 趋势
│   ├── success_rate_trend.png        # 成功率趋势
│   ├── v13_stability_*.png           # V13 2D 稳定域（8 张）
│   ├── v13_stability_3d_*.png        # V13 3D 稳定域（4 张）
│   ├── v13_slice_success_rates.png   # 切片成功率对比
│   ├── v13_parameter_correlation.png # 参数相关性
│   ├── cot_ranking.png               # 能效排行榜
│   ├── cot_evolution_annotated.png   # CoT 演化
│   ├── v13_cot_distribution.png      # V13 CoT 分布
│   └── top5_performance_radar.png    # Top 5 雷达图
├── version_comparator.py
├── stability_domain_visualizer.py
├── energy_efficiency_ranking.py
├── generate_comprehensive_report.py
└── README.md
```

---

## 依赖项

所有工具使用项目现有依赖（无需额外安装）:
- `matplotlib` - 绘图
- `pandas` - 数据处理
- `numpy` - 数值计算
- `common/plot_styles.py` - 统一画图风格

---

## 数据源

### 主要数据来源
1. **V13 参数敏感度图集**: `v13_parameter_sensitivity_atlas/out/*.csv`
   - 7 个参数切片（A-G）
   - 每个切片 36-64 个参数组合
   - 包含 success, cot, forward_distance, alternating_touchdowns 等指标

2. **各版本 out 目录**: `v*/out/*summary*.json` / `*.csv`
   - 仿真结果摘要
   - 关键性能指标

3. **手动汇总数据**: 基于项目记忆和 README 的版本里程碑

### 数据提取规则
- 优先读取 JSON/CSV 实测数据
- 无数据时使用估算值（标注为估算）
- V13 取所有切片的汇总统计

---

## 适用场景

### 论文答辩
- 展示完整开发历程和迭代逻辑
- 用 `version_timeline.png` 介绍版本演化
- 用稳定域图展示参数调优过程

### 博士论文
- HTML 报告包含所有关键图表
- CSV 表格可直接引用数据
- 能效排行支撑优化效果论证

### 项目总结
- 一键生成完整分析
- 识别最优版本和关键突破点
- 为后续工作提供基线对比

---

## 自定义扩展

### 添加新版本
工具会自动扫描 `v01_*` ~ `v24_*` 目录，新版本无需修改代码。

### 调整版本里程碑
编辑 `version_comparator.py` 中的 `VERSION_MILESTONES` 字典。

### 自定义图表样式
修改 `common/plot_styles.py` 的 `PALETTE` 和 `set_style()`。

### 增加新的分析维度
参考现有工具结构，添加新的 `*_analyzer.py`，在 `generate_comprehensive_report.py` 中集成。

---

## 注意事项

1. **运行时间**: 完整报告生成约 10-30 秒（取决于数据量）
2. **数据完整性**: 如果某些版本缺少数据，会跳过并打印警告
3. **V13 依赖**: 稳定域可视化依赖 V13 的 CSV 输出，确保已运行过 `scan_atlas_v13.py`
4. **中文字体**: 图表使用 Microsoft YaHei，Windows 系统默认支持

---

## 故障排查

### 问题: 图表中文乱码
**解决**: `common/plot_styles.py` 已配置中文字体，Windows 默认支持。如仍有问题，检查系统字体。

### 问题: 找不到 V13 数据
**解决**: 先运行 V13 的扫描脚本生成数据：
```powershell
cd D:\Dunna\Documents\hw-1\v13_parameter_sensitivity_atlas
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe" scan_atlas_v13.py --grid 6
```

### 问题: 某个版本数据缺失
**解决**: 工具会自动跳过缺失数据的版本，不影响其他版本的分析。可手动补充估算值到 `ENERGY_ESTIMATES` 字典。

---

## 更新日志

- **2026-06-04**: 初始版本，实现 3 个核心工具 + 综合报告生成器

---

## 作者

段泽琪 | 工业设计博士 | 2024211317

# 学术论文图表使用指南

本文档提供 hw-1 项目学术论文图表的索引、使用说明和学术规范。

## 图表清单

### 核心图表（投稿必需）

| 图号 | 文件名 | 标题 | 数据来源 | 学术用途 |
|------|--------|------|----------|----------|
| 图1 | `fig1_version_evolution` | 版本演化时间线 | V01-V25里程碑 | 展示研究进程和技术路线 |
| 图2 | `fig2_stability_domain` | 参数空间稳定域 | V13切片C数据 | 量化设计容差和参数耦合 |
| 图3 | `fig3_energy_analysis` | 能量效率对比 | V10-V17 CoT | 证明滚动足效率优势 |
| 图4 | `fig4_phase_portrait` | 相位肖像与极限环 | V10仿真轨迹 | 验证周期性步态 |
| 图5 | `fig5_hardware_specs` | V22硬件设计 | 硬件设计文档 | 展示工程可行性 |

### 补充图表（支撑材料）

| 图号 | 文件名 | 标题 | 数据来源 | 学术用途 |
|------|--------|------|----------|----------|
| 图6 | `fig6_friction_compensation` | 摩擦补偿效果 | V16/V13.7对比 | 证明补偿策略有效性 |
| 图7 | `fig7_state_estimation` | 状态估计鲁棒性 | V17噪声扫描 | 验证传感器容限 |
| 图8 | `fig8_3d_failure_analysis` | 3D失败证据 | V18/V19/V20 | 理论边界和否定结果 |
| 图9 | `fig9_poincare_convergence` | Poincaré收敛 | V13b长程辨识 | 量化极限环稳定性 |

## 输出格式

### 格式规格

- **PDF**: 适用于LaTeX论文插图（推荐）
  - 分辨率：矢量格式（无损缩放）
  - 文件大小：50-300 KB
  - 字体：内嵌Type 1字体

- **PNG**: 适用于Word文档或网页展示
  - 分辨率：300 DPI
  - 文件大小：200-800 KB
  - 透明背景：否

- **SVG**: 适用于后期编辑（Inkscape/Illustrator）
  - 分辨率：矢量格式
  - 可编辑性：完全保留元素结构

### 文件位置

```
paper_figures/
├── output/
│   ├── fig1_version_evolution.pdf   ← LaTeX插图用
│   ├── fig1_version_evolution.png   ← Word文档用
│   ├── fig1_version_evolution.svg   ← 编辑源文件
│   └── ...（共27个文件，9图×3格式）
└── latex_snippets.tex               ← LaTeX代码复制粘贴
```

## LaTeX 集成

### 方法1：直接复制代码片段

```bash
# 打开 latex_snippets.tex，复制相应图表的 \begin{figure}...\end{figure} 代码块
```

### 方法2：在LaTeX文档中引用

```latex
\documentclass{article}
\usepackage{graphicx}

\begin{document}

% 引用图1
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\textwidth]{paper_figures/output/fig1_version_evolution.pdf}
  \caption{版本演化时间线...}
  \label{fig:version_evolution}
\end{figure}

% 正文中引用
如图~\ref{fig:version_evolution}所示，项目经历了V01至V25的演进...

\end{document}
```

### 调整图表尺寸

```latex
% 全宽
\includegraphics[width=\textwidth]{...}

% 85%文本宽度
\includegraphics[width=0.85\textwidth]{...}

% 固定宽度
\includegraphics[width=12cm]{...}

% 按高度缩放
\includegraphics[height=8cm]{...}
```

## 学术规范

### 颜色盲友好配色

所有图表使用 Wong (2011) 色盲友好调色板：

- **成功/稳定**：#2a7a3b（深绿）
- **警告/边界**：#d68b00（橙色）
- **失败/不稳定**：#b3331b（深红）
- **中性/对照**：#3a3a3a（深灰）
- **左腿**：#0c789f（蓝色）
- **右腿**：#b34a36（棕红）

### 字体要求

- **主标题**：12pt，加粗
- **坐标轴标签**：11pt，常规
- **图例/标注**：9pt，常规
- **字体族**：Sans-serif（Helvetica/Arial），LaTeX兼容

### 分辨率标准

符合IEEE/Springer/Elsevier投稿要求：

- **线条图**：300-600 DPI（本系统默认300 DPI）
- **照片/渲染**：300 DPI
- **网页预览**：150 DPI即可

### 坐标轴规范

- **物理量**：使用斜体符号（$q$, $\dot{q}$, $\tau$）
- **单位**：使用直立字体和方括号（[m], [rad], [N·m]）
- **示例**：`xlabel='Hip Angle $q_{hip}$ [rad]'`

### 图例位置

- **避免遮挡数据**：优先放置于空白区域
- **推荐位置**：upper right, lower left, outside right
- **半透明背景**：`framealpha=0.9`

## 数据溯源

### 真实数据 vs 合成数据

| 图表 | 数据类型 | 数据源 | 备注 |
|------|----------|--------|------|
| 图1 | 真实 | `VERSIONS.md` + 各版本README | 手工整理的里程碑 |
| 图2 | 真实 | `v13_parameter_sensitivity_atlas/out/v13_C_foot_leg.csv` | 6×6=36格参数扫描 |
| 图3 | 部分合成 | V10-V17数据（部分版本未记录CoT） | 需补充V12分析结果 |
| 图4 | 合成 | 基于V10物理参数的典型轨迹 | 可替换为真实CSV |
| 图5 | 真实 | `v22_hardware_design/HARDWARE_SPEC.md` | 硬件设计文档 |
| 图6 | 真实 | `v16_motor_dynamics/` + `v13_7_friction_compensation/` | τ_C扫描结果 |
| 图7 | 真实 | `v17_state_estimation/out/scan_v17_noise.json` | 噪声扫描 |
| 图8 | 真实 | V18/V19/V20 verdict.json | 失败判定结果 |
| 图9 | 真实 | `v13b_floquet_long_run/` | Floquet谱和Poincaré点 |

### 数据更新流程

当实验数据更新后：

```bash
cd D:\Dunna\Documents\hw-1\paper_figures

# 1. 更新数据源（修改 generators/fig_*.py 中的数据读取路径）
# 2. 重新生成单个图表
python generators/fig_stability_domain.py

# 3. 批量重新生成所有图表
python generate_all_figures.py
```

## 投稿检查清单

### 图表质量

- [ ] 所有图表为300 DPI或矢量格式
- [ ] 字体大小适中（不小于8pt）
- [ ] 颜色对比度足够（色盲友好）
- [ ] 坐标轴标签清晰（包含单位）
- [ ] 图例不遮挡数据
- [ ] 误差棒或置信区间已标注

### 学术诚信

- [ ] 所有数据来源已注明
- [ ] 合成数据已标注"示意图"或"典型案例"
- [ ] 未夸大实验结果（成功率、性能指标）
- [ ] 否定结果已如实展示（V18/V19/V20）

### LaTeX集成

- [ ] PDF文件已嵌入字体
- [ ] 图表标题准确描述内容
- [ ] 图表编号连续（图1-图9）
- [ ] 正文引用完整（所有图表至少被引用一次）

## 故障排查

### 问题1：生成失败，提示找不到数据文件

**原因**：数据路径硬编码，项目移动后失效

**解决**：
```python
# 修改 generators/fig_*.py 中的 ROOT 路径
ROOT = Path(__file__).resolve().parents[2]  # 定位到项目根目录
```

### 问题2：字体警告（Font not found）

**原因**：系统缺少指定字体，matplotlib使用回退字体

**解决**：
- 忽略警告（使用DejaVu Sans回退，不影响投稿）
- 或安装Helvetica字体：`sudo apt install msttcorefonts`

### 问题3：PDF文件过大（>1 MB）

**原因**：嵌入了高分辨率位图或未压缩

**解决**：
```python
# 在 savefig 时添加压缩选项
fig.savefig('output.pdf', dpi=300, bbox_inches='tight',
            metadata={'Creator': 'matplotlib', 'Compress': True})
```

### 问题4：LaTeX编译报错（Unknown graphics extension）

**原因**：LaTeX不支持PNG/SVG，仅支持PDF/EPS

**解决**：
```latex
% 使用 PDF 格式
\includegraphics{paper_figures/output/fig1_version_evolution.pdf}

% 或使用 graphicx + epstopdf 包
\usepackage{epstopdf}
```

## 版本历史

- **v1.0** (2026-06-04): 初始系统，5核心图表（合成数据）
- **v2.0** (2026-06-05): 增强系统，9图表，集成真实数据，添加摩擦补偿/状态估计/3D失败分析

## 联系方式

技术问题或数据更新请求：
- 项目主页：`D:\\Dunna\\Documents\\hw-1\\README.md`
- 数据文档：`D:\\Dunna\\Documents\\hw-1\\VERSIONS.md`
- 硬件设计：`D:\\Dunna\\Documents\\hw-1\\v22_hardware_design\\`

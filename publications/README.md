# HW-1 学术发表材料包

为 hw-1 准被动双足机器人项目准备的完整学术发表材料。

## 项目概述

**研究主题**：基于事件驱动有限状态机的准被动双足步态控制  
**技术路线**：V01-V24 迭代开发（2D 被动步态 → 准被动控制 → 硬件设计）  
**关键创新**：
- V13.7 FSM 摩擦补偿控制律
- V17 传感器闭环状态估计
- V18-V20 侧向稳定性否定结果的学术价值
- V22 2D 硬件样机设计

## 目录结构

```
publications/
├── paper_draft/              # 论文草稿
│   ├── main.tex              # 主文档
│   ├── sections/             # 各章节
│   │   ├── abstract.tex
│   │   ├── introduction.tex
│   │   ├── related_work.tex
│   │   ├── methodology.tex
│   │   ├── results.tex
│   │   ├── discussion.tex
│   │   └── conclusion.tex
│   ├── figures/              # 论文图表（从 paper_figures/ 选取）
│   └── references.bib        # 参考文献
├── poster/                   # 会议海报
│   ├── poster_template.pptx  # PowerPoint 海报模板
│   └── poster_figures/       # 海报专用图
├── defense_slides/           # 答辩材料
│   ├── defense.pptx          # 答辩 PPT
│   └── slide_notes.md        # 演讲稿
├── supplementary/            # 补充材料
│   ├── video_demos/          # 演示视频索引
│   ├── code_listings/        # 关键代码清单
│   └── data_tables/          # 完整数据表
└── README.md                 # 本文件
```

## 使用指南

### 1. 论文草稿（LaTeX）

```bash
cd paper_draft
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

或使用 Overleaf 在线编译：上传 `paper_draft/` 整个文件夹。

**论文结构**：
- Abstract（中英文）250 字
- Introduction（2 页）：研究背景、动机、贡献
- Related Work（1.5 页）：被动步态、准被动控制、硬件设计
- Methodology（4 页）：V01-V24 技术路线、FSM 控制律、状态估计
- Results（3 页）：关键实验结果（V13.7/V17/V22）
- Discussion（1.5 页）：V18-V20 否定结果的学术价值
- Conclusion（0.5 页）：总结与展望

**目标期刊**：
- IEEE Transactions on Robotics（SCI 一区）
- Autonomous Robots（SCI 二区）
- Robotica（SCI 三区）

### 2. 会议海报

打开 `poster/poster_template.pptx`，尺寸为 A0（841×1189mm）。

**海报布局**（3 列）：
- **左列**：研究背景、问题定义、版本演化时间线
- **中列**：核心方法（FSM 相位图、摩擦补偿）、关键结果（稳定域、能量效率）
- **右列**：硬件设计、否定结果分析、结论与展望
- **底部**：参考文献、致谢、联系方式、二维码（链接到项目视频）

**适用会议**：
- ICRA（IEEE International Conference on Robotics and Automation）
- IROS（IEEE/RSJ International Conference on Intelligent Robots and Systems）
- Humanoids（IEEE-RAS International Conference on Humanoid Robots）

### 3. 答辩 PPT

打开 `defense_slides/defense.pptx`，时长 18 分钟（含 2 分钟提问）。

**PPT 结构**（18 页）：
1. 标题页（1 页，30 秒）
2. 研究问题与目标（2 页，3 分钟）
3. 技术路线（5 页，5 分钟）：V01→V24 演化
4. 关键突破（3 页，3 分钟）：V13.7 摩擦补偿
5. 否定结果分析（2 页，2 分钟）：V18-V20 学术价值
6. 硬件设计（3 页，3 分钟）：V22 样机
7. 总结与展望（2 页，2 分钟）

配合演讲稿 `slide_notes.md` 使用。

### 4. 补充材料

**视频演示索引** (`supplementary/video_demos/video_index.md`)：
- 指向 `out/` 目录中的关键 .mp4 文件
- 每个视频附带描述、时长、关键帧截图

**代码清单** (`supplementary/code_listings/`)：
- FSM 控制律核心算法（Python）
- 摩擦补偿函数
- 状态估计 Kalman 滤波器

**数据表** (`supplementary/data_tables/`)：
- 完整参数扫描结果（CSV）
- 各版本性能对比表（Excel）
- 硬件规格参数表

## 关键图表清单

以下图表已从 `paper_figures/output/` 和各版本 `out/` 目录中筛选，可直接用于论文：

### 论文主图（必选）

1. **版本演化时间线** (`fig1_version_evolution.pdf`)
   - 展示 V01-V24 开发历程
   - 用于 Introduction

2. **FSM 相位图** (`v13_6_event_driven_fsm/out/v13_6_baseline_report.png`)
   - 4 阶段事件驱动控制
   - 用于 Methodology

3. **稳定域热图** (`fig2_stability_domain.pdf`)
   - 参数敏感性分析
   - 用于 Results

4. **能量效率对比** (`fig3_energy_analysis.pdf`)
   - CoT 对比、机械能分解
   - 用于 Results

5. **硬件设计图** (`fig5_hardware_specs.pdf`)
   - V22 机械结构、质量分布
   - 用于 Methodology

### 补充图表（可选）

6. **Floquet 稳定性分析** (`v13_7_floquet_analysis/out/v13_7_stability_margin_comparison.png`)
7. **Poincaré 截面收敛** (`v12_energy_cot_analysis/out/v12_poincare_convergence.png`)
8. **摩擦补偿对比** (`v13_7_friction_compensation/out/`)
9. **状态估计噪声鲁棒性** (`v17_state_estimation/out/`)
10. **侧向稳定性探索** (`v18_3d_lateral_stability/`, V18-V20 否定结果）

## 参考文献

已整理在 `paper_draft/references.bib`，包含：

**经典被动步态**：
- McGeer (1990): Passive Dynamic Walking
- Goswami et al. (1996, 1998): Compass-Like Biped Robot
- Collins et al. (2001): 3D Passive-Dynamic Walking Robot

**准被动控制**：
- Collins et al. (2005): Efficient Bipedal Robots Based on Passive-Dynamic Walkers
- Spong & Bullo (2005): Controlled Symmetries and Passive Walking

**硬件实现**：
- Wisse et al. (2007): Ankle Springs Instead of Arc-Shaped Feet
- Hobbelen & Wisse (2008): Limit Cycle Walking

**状态估计**：
- Bloesch et al. (2013): State Estimation for Legged Robots

## 投稿策略

### 期刊论文（长期目标）

**首选**：IEEE Transactions on Robotics（TRO）
- 截稿类型：Regular Paper（12-16 页）
- 审稿周期：6-9 个月
- 重点突出：V13.7 FSM 控制律创新、V18-V20 否定结果的理论贡献

**备选**：Autonomous Robots
- 截稿类型：Original Research Article（8-12 页）
- 审稿周期：3-6 个月
- 重点突出：完整开发流程、硬件验证

### 会议论文（短期目标）

**首选**：ICRA 2027（2026 年 9 月截稿）
- 论文长度：6 页 + 2 页 references
- 突出：快速原型迭代、硬件设计

**备选**：Humanoids 2026（2026 年 6 月截稿）
- 论文长度：6 页
- 突出：仿生步态、2D→3D 探索

## 时间规划

| 里程碑 | 截止日期 | 交付物 |
|--------|---------|--------|
| 论文初稿完成 | 2026-07-15 | main.tex 初稿 |
| 内部审阅 | 2026-08-01 | 导师反馈第一轮 |
| 论文修订 | 2026-08-15 | 第二版草稿 |
| 会议投稿（Humanoids） | 2026-06-30 | 6 页短文 |
| 海报打印 | 答辩前 2 周 | A0 海报 PDF |
| 答辩 PPT 定稿 | 答辩前 1 周 | defense.pptx |
| 期刊投稿（ICRA/TRO） | 2026-09-15 | 完整论文包 |

## 联系方式

**项目负责人**：段泽琪  
**单位**：工业设计博士（学号 2024211317）  
**邮箱**：[待填写]  
**项目仓库**：D:\Dunna\Documents\hw-1

## 许可与引用

如需引用本项目，建议格式（待论文发表后更新）：

```bibtex
@article{duan2026quasipassive,
  title={Event-Driven Finite State Machine Control for Quasi-Passive Biped Walking with Friction Compensation},
  author={Duan, Zeqi and [Co-authors]},
  journal={[Journal Name]},
  year={2026},
  note={In preparation}
}
```

## 更新日志

- **2026-06-04**：初始发表材料包创建
  - 论文草稿框架（LaTeX）
  - 海报模板（PowerPoint）
  - 答辩 PPT 大纲
  - 补充材料索引

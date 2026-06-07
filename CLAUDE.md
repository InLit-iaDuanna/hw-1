# 项目说明（给新会话的快速上手文档）

## 这是什么

围绕**指南针模型 (Compass Gait)** 的**被动 / 准被动动态步行**研究项目。
按 V01 → V25 长程迭代，最终落地 3D 准被动行走 + 物理样机。

- 工作目录：`D:\Dunna\Documents\hw-1`
- 平台：Windows 11 + PowerShell（注意：不是 bash，所有命令必须用 PowerShell 语法）
- Python 环境：`.venv-mujoco/`（已存在的 venv，不要重建）
- 主要工具栈：MuJoCo (Python) + MATLAB 对照 + Remotion (动画解说)

## 关键文档（必读）

读取顺序：
1. **`README.md`** — 项目概述、目录结构、运行命令
2. **`VERSIONS.md`** — V01-V10 已完成版本的定位与结论
3. **`ROADMAP.md`** — V11-V25 长程规划，含阶段、决策门、基础设施
4. **本文件** — 协作约定与避坑要点

## 当前状态（截至 2026-05-26）

- ✅ V01-V10 已完成，主线收口于 V10（足踝滚动仿生）
- ✅ 根目录已配齐 `README.md` / `VERSIONS.md` / `ROADMAP.md` / `.gitignore` / `requirements.txt`
- ✅ V11 已完成：完整 225 格盆地扫描 + 相位噪声扫描，稳定边界 amp ≤ 28.6 mm / imp ≤ 17.1 N（详见 v11 README）
- ✅ V12 已完成：V07-V11 横向能量 / CoT / 实验 Floquet 对比，纯后处理无新仿真
- ✅ `common/` 公共库已创建：`terrain.py` / `disturbance.py` / `poincare.py` / `energy_metrics.py` / `plot_styles.py` / `benchmark.py`
- ⏳ 下一步：V13 `parameter_sensitivity_atlas`（系统化参数扫描，出可行参数图集）
- ⏳ 用户已确认四项长程约束：**三线均衡 / 长期研究 / 必须 3D / 会做硬件**

## 主线脉络（一句话版）

V5 证明纯被动极限环存在 → V6 转译为 MVE 机械结构 → V7 真实接触下失败 → V8/V9 引入弱补能恢复稳定 → V10 加被动踝关节实现脚跟-足底-脚趾滚动 → V11 量化崎岖地形/脉冲容差 → V12 横向能量与 Floquet 对比 → V13+ 参数图集、3D、硬件。

## 命名与目录约定

- 版本目录格式：`v{两位数}_{snake_case_名称}`，例：`v11_rugged_terrain_robustness`
- 每版四类脚本统一命名：`simulate_*.py` / `analyze_*.py` / `view_*.py` / `render_*.py`
- 每版必含 `README.md` 和 `requirements.txt`（即使内容相同，保持一致性）
- 渲染产物放各版本的 `out/` 子目录（已被跟踪的旧产物保留，不再新增入库）

## 学术诚信红线（重要）

报告口径分四档，**绝不能错配**：

| 标签 | 适用 | 判定标准 |
|---|---|---|
| 纯被动 | V5 | 重力是唯一输入，无任何执行器 |
| 准被动 | V8/V9/V10 | 弱主动补能或主动稳定 |
| 3D 准被动（仅冠状面主动） | V19+（拟） | 矢状面被动，仅冠状面闭环 |
| 主动稳定 | V19+ 主动方案 | 完整反馈控制律 |

V7（失败/敏感性）和 V11（扰动盆地边界）的失败结果**如实报告**，不要粉饰为成功。
任何含主动力的版本，README 第一行必须明确标注"非纯被动"。

## 协作约定（与用户工作时遵守）

- **PowerShell 语法**：用 `$null` 不用 `/dev/null`；用 `$env:VAR` 不用 `$VAR`；行续接用反引号
- **优先用专用工具**：Read/Edit/Write/Glob/Grep 优于 PowerShell；只在 shell 操作时才用 PowerShell
- **回答简洁**：用户偏好直接结论，不要长篇预设性文档（除非明确要求）
- **不主动改 git**：发现 `.idea/` 等已跟踪问题时**只建议不执行** `git rm --cached`
- **不擅自删除产物**：`outputs/` 和各 `v0X/out/` 已跟踪的文件是作业交付物，保留
- **重大决策先问用户**：长程方向、版本顺序变更、删除/重构等先用 AskUserQuestion 确认

## 已知陷阱

1. **PowerShell 在并行调用时偶发 Exit 255**：单独串行调用即可恢复
2. **`Get-ChildItem -Recurse` 不要直接对项目根跑**：会扫到 `node_modules` 和 `.venv-mujoco`，输出几百 MB；用 `-Path src/...` 限制范围
3. **`compass-gait-remotion` 是独立子项目**：有自己的 `package.json` 和 `node_modules`，不要和 Python 主线混合
4. **MATLAB 对照在 `matlab-v01-v13-gait/`**：跟 Python 主线版本号对应但不严格同步
5. **`.venv-mujoco/` 已存在**：直接用 `.\.venv-mujoco\Scripts\python.exe`，不要重新建 venv

## 跨版本基础设施（V11 起需要）

`common/` 库已创建，当前按以下规划继续扩展（详见 ROADMAP.md）：

```
common/
  poincare.py          # Poincaré 截面分析
  energy_metrics.py    # CoT、机械能流
  disturbance.py       # 扰动注入
  terrain.py           # 地形生成
  plot_styles.py       # 统一画图风格
  benchmark.py         # 跨版本基准场景
```

新版本应 `import common.xxx` 而不是复制工具代码，保证分析口径跨版本一致。

## 决策门（不要跳过）

- **V13 完成后** — 重评估硬件可行性，必要时回退优化机构
- **V17 完成后** — 重评估驱动方案，电机模型若打破 V9/V10 稳定性需重选
- **V21 完成后** — 3D 不收敛则降级为"3D 准被动 + 冠状面主动"

到达这些节点时，提醒用户暂停、回顾 ROADMAP.md。

## 联系点（用户偏好）

- 中文回答，技术术语保留英文
- 用户是研究者/工程师视角，能看懂动力学和控制术语
- 输出建议时给"推荐选项 + 主要 trade-off"，不要列十条让用户自己选
- 每完成一个版本提醒更新 `VERSIONS.md` 横向对比表

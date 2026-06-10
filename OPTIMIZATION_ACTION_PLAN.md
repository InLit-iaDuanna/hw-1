# 项目优化行动清单
**日期**: 2026-06-09  
**审查基准**: PROJECT_AUDIT_REPORT.md

---

## ✅ 已完成的紧急修复（P0）

### 1. 更新 CLAUDE.md 到当前状态
- ✅ 将"截至 2026-05-26"更新为"2026-06-09"
- ✅ 更新当前状态：V01-V24 已完成（V21跳过）
- ✅ 添加 Residual RL V2 完成状态
- ✅ 重写主线脉络，包含完整演进路径
- ✅ 标注下一步为 V25（待硬件制作）

**文件**: `CLAUDE.md` 第 21-33 行  
**影响**: 新会话和 AI assistant 现在能获得准确的项目状态

### 2. 更新 ROADMAP.md 阶段状态
- ✅ 将"当前阶段 V1-V13"更新为"所有主线版本已完成"
- ✅ 阶段 2（V14-V17）标记为"已完成 2026-05-28 至 2026-06-02"
- ✅ 阶段 3（V18-V20）标记为"三次否定结果"，V21 标记为"已跳过"
- ✅ 阶段 4（V22-V24）标记为"文档完成 2026-06-04"
- ✅ 补充 Residual RL V2 部分

**文件**: `ROADMAP.md` 第 3-42 行  
**影响**: 文档状态一致性恢复

### 3. 补充 RL 训练依赖
- ✅ 创建 `requirements-rl.txt`
- ✅ 包含 gymnasium, stable-baselines3, tensorboard, torch

**文件**: `requirements-rl.txt`（新建）  
**影响**: 解决 RL 训练脚本缺失依赖声明的问题

---

## 🔄 进行中的任务

### 4. 自动生成缺失的 requirements.txt（21个版本）
**状态**: Workflow 运行中（`generate-missing-requirements`）

**目标**:
- 扫描所有 v* 目录，确认缺失列表
- 分析每个版本的 Python 导入，推断依赖
- 生成 requirements.txt 文件内容

**预计输出**:
- 仿真版本：full 模板（mujoco, numpy, matplotlib, imageio）
- 分析版本：analysis-only 模板（numpy, matplotlib, scipy）
- 设计文档版本：跳过（不需要 Python 依赖）
- 重构目录：建议删除而非补充

**下一步**: 等待 workflow 完成，审查生成的内容，批量写入文件

---

## ⏳ 待执行的优化（按优先级）

### P1: 结构清理（2天）

#### 5.1 处理 refactored 目录
**目标**: 调查并清理 3 个 refactored 目录

**需要决策**:
- `v13_6_refactored` - 是否是 V13.6 的实验分支？
- `v13_7_refactored` - 是否是 V13.7 的实验分支？
- `v16_refactored` - 是否是 V16 的实验分支？

**方案**:
- [ ] 检查 refactored 目录内容
- [ ] 对比主版本差异
- [ ] 决策：合并/删除/移至 `_archive/`

**预计影响**: 减少目录混乱，提高项目可理解性

#### 5.2 补充 VERSIONS.md - Residual RL V2 条目
**目标**: 在版本表格中添加 RL V2 完整条目

**内容**:
```markdown
| Residual RL V2 | `rl_training/` | PPO on V13.7 | 否（RL优化层）| 100k训练完成：baseline 4.63m → best 4.90m（+5.8%），zero residual identity验证通过，sweep找到最优方向[0.50,1.00] |
```

**文件**: `VERSIONS.md` 第 35 行之后插入

#### 5.3 标准化目录命名
**发现**: 11个目录不符合 `v{两位数}_{snake_case}` 规范

**违规列表**:
- v13b / v13_5 / v13_6 / v13_7（下划线混用）
- v14b / v14c（应为 v14_b / v14_c？）
- v15_1 / v15_2（数字混用）
- v13_6_refactored / v13_7_refactored / v16_refactored（临时目录）

**方案 A（推荐）**: 保持现有命名
- ✅ 不破坏现有引用和 import
- ❌ 不符合原定规范
- ✅ 成本低

**方案 B**: 重命名为规范格式
- ✅ 符合规范
- ❌ 破坏跨版本 import
- ❌ 需要更新所有文档引用
- ❌ 成本高

**建议**: 采用方案 A，新版本严格遵守规范

---

### P2: 代码重构（1周）

#### 6.1 提取公共工具到 common/
**目标**: 消除 V10-V17 的重复代码（估计 3000+ 行）

**迁移清单**:

**common/ik_utils.py**（新建）:
```python
def leg_ik_front_knee(dx, dz, leg_length)
def smoothstep(x, edge0, edge1)
def ramp_height(x, x0, x1)
```

**common/failure_classifier.py**（新建）:
```python
def classify_failure(qpos, qvel, nq, hip_z_threshold=0.3)
def make_row(...)  # 数据记录
```

**common/xml_templates.py**（新建）:
```python
class CompassGaitTemplate:
    def build_model_xml(self, params)
```

**common/contact_utils.py**（新建）:
```python
def foot_contact_detail(...)
def contact_flags(...)
def initialize(...)  # 初始化函数
```

**预计收益**:
- 减少重复代码 3000+ 行
- 统一修复 bug（不需要在 6 个版本分别修复）
- 打破版本链式依赖

**风险**:
- 可能破坏现有版本的运行
- 需要大量测试验证

**建议**: 逐步迁移，每迁移一个工具函数就测试相关版本

#### 6.2 打破版本链式依赖
**当前**: V17 → V16 → V14c → V14 → V13.6 → V10（6层）

**目标**: V17 → common/ ← V10（扁平化）

**策略**:
- [ ] 删除所有 `sys.path.insert(0, '../v10_...')` 
- [ ] 替换为 `from common import ...`
- [ ] 验证每个版本独立运行

**预计影响**: 修改 V10 不再影响后续 6 个版本

---

### P2: 依赖统一（2天）

#### 7.1 解决版本冲突
**发现的冲突**:
- numpy: `>=1.24.0` vs `>=2.0.0`（大版本冲突）
- mujoco: `>=2.3.0` vs `>=3.3.7`（大版本冲突）

**统一方案**:
```
numpy==2.2.6           # 统一到 2.x（当前最新）
mujoco==3.3.7          # 统一到最新稳定版
matplotlib>=3.7.0
scipy>=1.11.0
gymnasium>=0.29.1      # 补充 RL 依赖
stable-baselines3>=2.3.2
tensorboard>=2.15.0
torch>=2.0.0
```

**执行**:
- [ ] 更新根目录 `requirements.txt`
- [ ] 更新所有子目录 `requirements.txt`
- [ ] 测试环境兼容性

#### 7.2 完善依赖文件结构
**当前结构**:
```
requirements.txt
requirements-analysis.txt
requirements-viz.txt
requirements-rl.txt  ← 新增
```

**缺失但被引用**:
- requirements-opt.txt（优化工具）
- requirements-ui.txt（UI工具）

**建议**:
- [ ] 补充 requirements-opt.txt
- [ ] 补充 requirements-ui.txt（如果有 UI）
- [ ] 或删除文档中的错误引用

---

### P3: 路径可移植性（1天）

#### 8.1 替换硬编码路径（59个文件）
**问题**: 59个文件包含 `D:\Dunna\Documents\hw-1`

**关键文件**:
- data_versioning/*.py（5个文件）
- rl_training/monitor_progress.py
- virtual_constraints/simulate_vc.py
- check_ppt_bounds.py
- batch_render_hd.py

**替换策略**:
```python
# 旧代码
project_root = r'D:\Dunna\Documents\hw-1'

# 新代码
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
```

**自动化脚本**:
```python
# scripts/fix_hardcoded_paths.py
import re
from pathlib import Path

pattern = r"['\"]D:\\Dunna\\Documents\\hw-1['\"]"
replacement = "Path(__file__).resolve().parent.parent"
```

**执行**:
- [ ] 编写自动化替换脚本
- [ ] 对 59 个文件执行替换
- [ ] 验证路径解析正确性

---

### P3: 代码质量改进（1周）

#### 9.1 修复 common/ 库的 bugs（8个）
**Critical bugs**:
1. `common/disturbance.py:40` - apply_impulse 在 body_id < 0 时力遗留
2. `common/poincare.py:79` - floquet_multipliers 未检查欠定系统
3. `common/simulation_runner.py:169` - 早停检测延迟一步
4. `common/model_loader.py:72` - tmp_path 可能未定义

**建议**: 逐个修复，每修复一个写单元测试

#### 9.2 修复控制器 bugs（7个）
**Critical bugs**:
1. `V17 state_estimator.py:119` - 速度有限差分可能返回 NaN
2. `V13.6 simulate_v13_6.py:222` - Phase variable u 可能为负
3. `V13.7 simulate_v13_7.py:211` - 摩擦补偿可能超过饱和限

**建议**: V13.7 是主线控制律，优先修复其 bugs

#### 9.3 重构过长函数
**code smells**:
- `common/energy_metrics.py:114-354` - EnergyAnalyzer 240行
- `V13.6 simulate_v13_6.py:356-415` - 主循环 60行
- `V17 state_estimator.py:200-241` - update() 40行

**建议**: 拆分为多个小函数，遵循单一职责原则

---

### P3: 数据完整性（1天）

#### 10.1 补充缺失的 JSON 摘要
**缺失的文件**:
- `v11_rugged_terrain_robustness/out/v11_robustness_boundary.json`
  - 应包含：amp_max=28.6mm, imp_max=17.1N
- `v13_parameter_sensitivity_atlas/out/v13_C_foot_leg_meta.json`
  - 应包含：切片C汇总，success_rate=16.7%
- `logs/residual_rl_v2/sanity_100k_final_eval.json`
  - 应包含：final_distance=4.898271m

**执行**:
- [ ] 生成 V11 边界值 JSON
- [ ] 生成 V13 切片汇总 JSON
- [ ] 生成 RL V2 评估 JSON

#### 10.2 清理未归档的 out/ 文件
**问题**: 20+ 个 staged 文件未在文档中引用

**策略**:
- [ ] 列出所有 `git ls-files '*/out/*'`
- [ ] 交叉比对 VERSIONS.md 引用
- [ ] 决策：添加到 .gitignore 或在文档中引用

---

## 📊 优化进度追踪

| 任务 | 优先级 | 状态 | 预计时间 | 负责人 |
|------|-------|------|---------|-------|
| 更新 CLAUDE.md | P0 | ✅ 完成 | - | Claude |
| 更新 ROADMAP.md | P0 | ✅ 完成 | - | Claude |
| 补充 requirements-rl.txt | P0 | ✅ 完成 | - | Claude |
| 生成缺失 requirements.txt | P1 | 🔄 进行中 | 30分钟 | Workflow |
| 处理 refactored 目录 | P1 | ⏳ 待执行 | 2小时 | 需用户决策 |
| 补充 Residual RL V2 到 VERSIONS.md | P1 | ⏳ 待执行 | 15分钟 | - |
| 提取公共工具到 common/ | P2 | ⏳ 待执行 | 3天 | - |
| 打破版本链式依赖 | P2 | ⏳ 待执行 | 2天 | - |
| 统一依赖版本 | P2 | ⏳ 待执行 | 1天 | - |
| 替换硬编码路径 | P3 | ⏳ 待执行 | 1天 | - |
| 修复 common/ bugs | P3 | ⏳ 待执行 | 2天 | - |
| 修复控制器 bugs | P3 | ⏳ 待执行 | 2天 | - |
| 补充缺失 JSON | P3 | ⏳ 待执行 | 4小时 | - |

**总预计时间**: 2-3周（如果并行执行部分任务可缩短到1-2周）

---

## 🎯 快速胜利（Quick Wins）

以下是可以在 1 小时内完成的小任务：

1. ✅ **更新 CLAUDE.md**（5分钟）- 已完成
2. ✅ **补充 requirements-rl.txt**（5分钟）- 已完成
3. ⏳ **补充 VERSIONS.md - RL V2 条目**（10分钟）
4. ⏳ **生成 V11 边界值 JSON**（15分钟）
5. ⏳ **生成 V13 切片汇总 JSON**（15分钟）
6. ⏳ **修复 common/disturbance.py:40 bug**（10分钟）
7. ⏳ **检查 refactored 目录内容**（15分钟）

---

## 🤔 需要用户决策的问题

### 问题 1: refactored 目录处理
**选项**:
- A. 删除（如果是临时实验）
- B. 合并到主版本（如果包含有用改进）
- C. 移至 `_archive/`（保留但不混淆）

**建议**: 先检查内容再决策

### 问题 2: 目录重命名
**选项**:
- A. 保持现有命名（不破坏引用，成本低）
- B. 重命名为规范格式（符合规范，成本高）

**建议**: 方案 A

### 问题 3: 代码重构范围
**选项**:
- A. 仅提取明显重复的工具函数
- B. 全面重构 V10-V17 使用 common/ 库

**建议**: 方案 A（渐进式）

### 问题 4: 硬编码路径修复优先级
**选项**:
- A. 立即修复所有 59 个文件
- B. 仅修复关键文件（data_versioning, rl_training）

**建议**: 方案 B（优先修复影响大的）

---

## 📈 预期收益

### 短期收益（完成 P0-P1）
- ✅ 文档一致性恢复，新会话获得准确状态
- ✅ RL 训练依赖声明完整
- ⏳ 所有版本都有 requirements.txt，可复现环境
- ⏳ 项目结构清晰，无临时目录混淆

### 中期收益（完成 P2）
- 代码重复减少 3000+ 行
- 版本间独立性提高，修改 V10 不影响后续版本
- 依赖版本统一，无冲突

### 长期收益（完成 P3）
- 项目可移植性提高，可在任何机器运行
- 代码质量提高，bug 减少
- 数据完整性提高，所有声称结果都有数据支撑

---

## 🔄 下次审查计划

**触发条件**:
- 完成 5 个新版本后
- 重大重构完成后
- 每季度一次（如果无新版本）

**审查范围**:
- 运行相同的 6 阶段质量审查 workflow
- 对比改进前后的指标
- 验证优化措施的效果

---

**行动清单生成**: 2026-06-09  
**基于**: PROJECT_AUDIT_REPORT.md  
**下次更新**: 待 P1 任务完成后

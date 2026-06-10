# Codex 提示词 - P2/P3 代码重构任务

## 📋 任务概览

基于项目深度审查结果（见 `PROJECT_AUDIT_REPORT.md`），执行 P2-P3 优化任务：
- **P2**: 代码重构（消除重复，打破依赖链，统一依赖版本）
- **P3**: 路径修复和剩余 bug 修复

**预计时长**: 2-3 周  
**风险等级**: 中高（涉及跨版本代码修改）  
**建议策略**: 渐进式，每完成一步就测试

---

## 🎯 P2 任务清单

### Task 1: 提取 V10-V17 公共代码到 common/

**背景**:
- V10-V17 存在约 3,000+ 行重复代码
- 工具函数如 `smoothstep`, `ramp_height`, `leg_ik_front_knee`, `classify_failure` 等在多个版本中复制
- 形成 6 层依赖链：V17→V16→V14c→V14→V13.6→V10

**目标**:
- 将重复工具函数提取到 `common/` 新模块
- 消除跨版本 `sys.path.insert` 导入
- 打破依赖链，使每个版本独立

---

#### 📝 Codex 提示词 1.1 - 提取 IK 工具函数

```
【任务】提取逆运动学（IK）工具函数到 common/ik_utils.py

【背景】
根据代码审查报告（PROJECT_AUDIT_REPORT.md），以下函数在 V10-V17 的 8 个版本中重复定义：
- leg_ik_front_knee(dx, dz, leg_length)
- smoothstep(x, edge0, edge1)  
- ramp_height(x, x0, x1)

【具体任务】
1. 创建 `common/ik_utils.py` 文件
2. 从 `v10_rolling_foot_biomimetic_gait/simulate_v10.py` 中提取这 3 个函数作为参考实现
3. 添加完整的 docstrings（包含参数、返回值、示例）
4. 添加类型提示（type hints）
5. 在文件顶部添加模块说明
6. 导出到 `common/__init__.py`

【代码规范】
- 函数签名保持与 V10 版本完全一致（向后兼容）
- 使用 NumPy 数组作为输入/输出类型
- 添加输入验证（如检查 leg_length > 0）
- 参考 `common/controllers.py` 的代码风格

【测试要求】
创建 `tests/unit/test_ik_utils.py`，包含：
- 测试 smoothstep 的边界条件（x < edge0, x > edge1, x = edge0/edge1）
- 测试 leg_ik_front_knee 的膝盖角度限制
- 测试 ramp_height 的平滑过渡

【输出】
1. 完整的 common/ik_utils.py 文件
2. 更新后的 common/__init__.py（添加导出）
3. tests/unit/test_ik_utils.py 测试文件
4. 简短说明（100 字内）

【参考文件】
- v10_rolling_foot_biomimetic_gait/simulate_v10.py（行号约 150-200）
- common/controllers.py（代码风格参考）
- PROJECT_AUDIT_REPORT.md（第 149-180 行，重复代码分析）
```

---

#### 📝 Codex 提示词 1.2 - 提取失败分类函数

```
【任务】提取失败分类函数到 common/failure_classifier.py

【背景】
`classify_failure` 函数在 V10/V11/V14/V15/V16/V17 中几乎相同，仅参数名略有不同。
该函数用于判断行走失败的原因（hip 高度过低、速度异常、姿态倒下等）。

【具体任务】
1. 创建 `common/failure_classifier.py` 文件
2. 定义统一的失败分类函数：
   ```python
   def classify_failure(
       qpos: np.ndarray,
       qvel: np.ndarray, 
       nq: int,
       hip_z_threshold: float = 0.3,
       vel_threshold: float = 5.0
   ) -> str:
       """
       分类行走失败原因
       
       Returns:
           'stuck': 髋关节几乎静止
           'fall_down': 髋关节高度过低
           'posture_collapse': 速度异常或姿态崩溃
           'success': 未检测到失败
       """
   ```
3. 适配不同版本的 qpos 布局（V14+ 可能包含摆臂关节）
4. 添加可选的数据记录函数 `make_row(...)`（如果多个版本都使用）

【代码规范】
- 使用枚举类型定义失败模式（推荐但不强制）
- 函数应该是纯函数（无副作用）
- 添加详细的 docstring 说明阈值含义

【测试要求】
创建 `tests/unit/test_failure_classifier.py`：
- 模拟 'stuck' 场景（qvel 全为 0）
- 模拟 'fall_down' 场景（qpos[hip_z_index] < threshold）
- 测试不同 nq 布局的兼容性

【注意事项】
- V14/V16/V17 的 qpos 布局可能与 V10 不同（有摆臂关节）
- 需要参数化 hip_z 在 qpos 中的索引位置
- 或者函数接受 hip_z 作为独立参数（推荐）

【输出】
1. common/failure_classifier.py
2. tests/unit/test_failure_classifier.py
3. 迁移指南：如何从旧版本调用新函数（示例代码）

【参考文件】
- v10_rolling_foot_biomimetic_gait/simulate_v10.py（classify_failure 定义）
- v14_passive_arms/simulate_v14.py（摆臂版本的 qpos 布局）
- PROJECT_AUDIT_REPORT.md（第 149-157 行）
```

---

#### 📝 Codex 提示词 1.3 - 重构 V10 使用 common/ 库（试点）

```
【任务】将 V10 重构为使用 common/ 库（作为试点版本）

【背景】
V10 是主线基准版本，被 V11-V17 依赖。将 V10 重构后，可以验证：
1. common/ 库的功能完整性
2. 对现有行为的影响
3. 为后续版本重构提供模板

【具体任务】
1. 修改 `v10_rolling_foot_biomimetic_gait/simulate_v10.py`：
   - 删除本地定义的 `smoothstep`, `ramp_height`, `leg_ik_front_knee`
   - 改为：`from common.ik_utils import smoothstep, ramp_height, leg_ik_front_knee`
   - 删除本地定义的 `classify_failure`（如果有）
   - 改为：`from common.failure_classifier import classify_failure`

2. 运行 V10 的完整测试：
   ```bash
   .\.venv-mujoco\Scripts\python.exe v10_rolling_foot_biomimetic_gait\simulate_v10.py --duration 12.0
   ```

3. 验证输出与原版本一致：
   - forward distance 误差 < 1%
   - alternating touchdowns 数量相同
   - 不产生新的警告或错误

【测试策略】
- 在修改前保存原始输出：`v10_baseline_before_refactor.json`
- 修改后运行相同参数，比对结果
- 如果有差异，分析原因（浮点误差 vs 逻辑错误）

【回退计划】
如果测试失败：
1. 保留修改在 git 分支 `refactor/v10-common-lib`
2. 回到 main 分支
3. 报告失败原因和观察到的差异

【输出】
1. 修改后的 simulate_v10.py
2. 对比报告（JSON 格式）：
   ```json
   {
     "version": "v10",
     "before": {"forward": 4.62, "alt_td": 10},
     "after": {"forward": 4.623, "alt_td": 10},
     "diff_percent": 0.065,
     "status": "pass"
   }
   ```
3. 发现的问题（如果有）

【参考文件】
- v10_rolling_foot_biomimetic_gait/simulate_v10.py
- common/ik_utils.py（刚创建的）
- common/failure_classifier.py（刚创建的）
```

---

#### 📝 Codex 提示词 1.4 - 批量重构 V11-V17

```
【任务】将 V11-V17 批量重构为使用 common/ 库

【前提条件】
- V10 重构已通过测试（Codex 提示词 1.3 完成）
- common/ik_utils.py 和 common/failure_classifier.py 已验证

【具体任务】
逐个重构以下版本（按依赖顺序）：
1. V11 (依赖 V10)
2. V13.6 (依赖 V10)
3. V14 (依赖 V10)
4. V14b (依赖 V13.6)
5. V14c (依赖 V14)
6. V16 (依赖 V14c)
7. V17 (依赖 V16)

【每个版本的步骤】
1. 删除 `sys.path.insert(0, '../v10_...')` 类似的跨版本导入
2. 删除本地重复定义的工具函数
3. 改为：`from common.ik_utils import ...`
4. 运行该版本的 smoke test
5. 记录对比结果

【自动化脚本】
创建 `scripts/refactor_versions.py`：
```python
#!/usr/bin/env python3
"""
批量重构 V11-V17 使用 common/ 库

Usage:
    python scripts/refactor_versions.py --version v11 --test
    python scripts/refactor_versions.py --all --test
"""
```

【测试策略】
- 每个版本修改后立即运行 smoke test
- 保存 before/after 对比
- 如果某个版本失败，暂停并报告
- 不要继续后续版本（避免级联错误）

【输出】
1. 所有修改后的 simulate_*.py 文件
2. 批量对比报告：
   ```json
   {
     "v11": {"status": "pass", "diff": 0.12},
     "v13_6": {"status": "pass", "diff": 0.05},
     "v14": {"status": "pass", "diff": 0.08},
     ...
   }
   ```
3. scripts/refactor_versions.py（自动化脚本）

【风险控制】
- 在 git 分支 `refactor/v11-v17-common-lib` 工作
- 每个版本一个 commit
- 如果多个版本失败，考虑调整 common/ 库而非强行修改各版本

【参考文件】
- PROJECT_AUDIT_REPORT.md（第 149-180 行，依赖链）
- OPTIMIZATION_ACTION_PLAN.md（P2 任务细节）
```

---

### Task 2: 统一依赖版本

#### 📝 Codex 提示词 2.1 - 解决依赖版本冲突

```
【任务】统一所有 requirements.txt 的依赖版本

【背景】
审查发现依赖版本冲突：
- numpy: `>=1.24.0` vs `>=2.0.0`（大版本冲突）
- mujoco: `>=2.3.0` vs `>=3.3.7`（大版本冲突）

【目标版本】（基于根目录 requirements.txt）
```
numpy==2.2.6
mujoco==3.3.7
matplotlib>=3.7.0
scipy>=1.11.0
imageio>=2.31.0
imageio-ffmpeg>=0.4.9
pillow>=10.0.0
gymnasium>=0.29.1
stable-baselines3>=2.3.2
tensorboard>=2.15.0
torch>=2.0.0
```

【具体任务】
1. 读取所有 requirements.txt 文件（37 个版本 + 根目录）
2. 检测版本冲突
3. 统一为上述目标版本
4. 保留版本特定的依赖（如果有）

【自动化脚本】
创建 `scripts/unify_requirements.py`：
```python
#!/usr/bin/env python3
"""
统一所有 requirements.txt 的依赖版本

Usage:
    python scripts/unify_requirements.py --check  # 检查冲突
    python scripts/unify_requirements.py --fix    # 修复冲突
"""
```

【验证步骤】
1. 在干净的虚拟环境中测试：
   ```bash
   python -m venv test_env
   test_env\Scripts\activate
   pip install -r requirements.txt
   ```
2. 运行 V10 smoke test（作为兼容性验证）
3. 运行 V17 smoke test（最新版本验证）
4. 运行 RL 训练 test（验证 RL 依赖）

【输出】
1. 修改后的所有 requirements.txt
2. 冲突报告：
   ```json
   {
     "conflicts_found": 2,
     "packages": ["numpy", "mujoco"],
     "resolutions": {
       "numpy": "2.2.6",
       "mujoco": "3.3.7"
     }
   }
   ```
3. scripts/unify_requirements.py

【注意事项】
- 不要修改 requirements-rl.txt（已经正确）
- 保留注释和空行
- V22-V24 设计文档版本可能只需 minimal 依赖

【参考文件】
- PROJECT_AUDIT_REPORT.md（第 221-233 行，依赖冲突列表）
- OPTIMIZATION_ACTION_PLAN.md（P2 Task 7.1）
```

---

## 🎯 P3 任务清单

### Task 3: 替换硬编码路径

#### 📝 Codex 提示词 3.1 - 自动替换硬编码路径

```
【任务】自动替换 59 个文件中的硬编码绝对路径

【背景】
审查发现 59 个文件包含硬编码路径：
```
D:\Dunna\Documents\hw-1
```
这导致项目无法在其他机器/目录运行。

【目标】
替换为相对路径或 pathlib 动态解析：
```python
# 旧代码
project_root = r'D:\Dunna\Documents\hw-1'

# 新代码
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
```

【关键文件列表】（优先级排序）
1. data_versioning/*.py（5 个文件）- 高优先级
2. rl_training/monitor_progress.py - 高优先级
3. virtual_constraints/simulate_vc.py - 中优先级
4. check_ppt_bounds.py - 低优先级
5. batch_render_hd.py - 低优先级（注释中的示例路径）
6. 其他 54 个文件 - 批量处理

【自动化脚本】
创建 `scripts/fix_hardcoded_paths.py`：
```python
#!/usr/bin/env python3
"""
自动替换硬编码路径

Usage:
    python scripts/fix_hardcoded_paths.py --check  # 检查所有硬编码路径
    python scripts/fix_hardcoded_paths.py --fix    # 自动替换
    python scripts/fix_hardcoded_paths.py --file <path>  # 单文件修复
"""
import re
from pathlib import Path

def find_hardcoded_paths(file_path):
    """查找文件中的硬编码路径"""
    pattern = r"['\"]D:\\Dunna\\Documents\\hw-1['\"]"
    # 或者 forward slash 版本
    pattern2 = r"['\"]D:/Dunna/Documents/hw-1['\"]"
    
def replace_with_pathlib(file_path):
    """替换为 pathlib 相对路径"""
    # 计算相对于文件的深度
    # 生成适当的 .parent.parent... 链
    
def generate_report():
    """生成修复报告"""
```

【替换策略】
1. **Python 文件**：
   - 在文件顶部添加：`from pathlib import Path`
   - 添加：`PROJECT_ROOT = Path(__file__).resolve().parent.parent`（根据深度调整）
   - 替换所有硬编码路径为：`PROJECT_ROOT / 'subdir'`

2. **注释/文档中的路径**：
   - 保留作为示例，但添加注释：`# 示例路径，请根据实际情况修改`

3. **PowerShell 脚本**：
   - 使用：`$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot`

【测试验证】
修复后测试关键脚本：
```bash
# 测试数据版本控制工具
python data_versioning/data_differ.py

# 测试 RL 监控
python rl_training/monitor_progress.py

# 测试虚拟约束
python virtual_constraints/simulate_vc.py
```

【输出】
1. 修改后的 59 个文件
2. 修复报告：
   ```json
   {
     "total_files": 59,
     "fixed": 59,
     "failed": 0,
     "skipped": 0,
     "files_by_priority": {
       "high": ["data_versioning/...", "rl_training/..."],
       "medium": [...],
       "low": [...]
     }
   }
   ```
3. scripts/fix_hardcoded_paths.py

【注意事项】
- 不要修改 .gitignore 或其他配置文件中的占位符路径
- 谨慎处理字符串拼接（可能是用户输入路径）
- 确保 Windows 和 Linux 路径分隔符兼容（pathlib 自动处理）

【参考文件】
- PROJECT_AUDIT_REPORT.md（第 241-257 行，59 个文件列表）
- OPTIMIZATION_ACTION_PLAN.md（P3 Task 8.1）
```

---

### Task 4: 修复剩余 bugs

#### 📝 Codex 提示词 4.1 - 修复剩余 4 个 minor bugs

```
【任务】修复 common/ 库中剩余的 4 个 minor bugs

【背景】
4 个 critical bugs 已修复，还有 4 个 minor bugs 待处理：
1. common/energy_metrics.py:261-301 - 功率计算逻辑分散
2. common/plot_styles.py:166-225 - 绘图函数过长（60+ 行）
3. common/terrain.py:86-92 - 使用断言进行参数验证
4. common/controllers.py:151-152 - ValueError 而非类型签名明确可选

【具体任务】

**Bug 1: 功率计算逻辑重构**
```python
# 位置：common/energy_metrics.py
# 问题：功率计算分散在 _compute_power 和 EnergyStats.update
# 修复：统一到一个函数，避免重复逻辑
```

**Bug 2: 绘图函数拆分**
```python
# 位置：common/plot_styles.py:166-225
# 问题：plot_robustness_heatmap 函数 60 行，职责过重
# 修复：拆分为：
#   - _prepare_heatmap_data(...)
#   - _configure_heatmap_axes(...)
#   - plot_robustness_heatmap(...) <- 调用上述函数
```

**Bug 3: 参数验证改为显式检查**
```python
# 位置：common/terrain.py:86-92
# 问题：assert 在 Python -O 模式下被禁用
# 修复：改为 if + raise ValueError
assert height.shape == (nrow, ncol), "..."
# 改为
if height.shape != (nrow, ncol):
    raise ValueError(f"Expected shape {(nrow, ncol)}, got {height.shape}")
```

**Bug 4: 类型签名明确可选参数**
```python
# 位置：common/controllers.py:151-152
# 问题：target 未提供时抛出 ValueError，但类型签名未标记 Optional
# 修复：
def compute_torque(self, q, dq, target: float | None = None) -> float:
    if target is None:
        raise ValueError("PDController requires target position")
```

【测试要求】
1. 所有修改保持向后兼容
2. 运行现有测试套件：
   ```bash
   pytest tests/unit/test_energy_metrics.py
   pytest tests/unit/test_plot_styles.py
   pytest tests/unit/test_terrain.py
   pytest tests/unit/test_controllers.py
   ```
3. 如果测试不存在，创建最小测试覆盖

【输出】
1. 修改后的 4 个文件
2. 新增或更新的测试文件
3. 修复说明（每个 bug 50 字内）

【参考文件】
- PROJECT_AUDIT_REPORT.md（第 105-146 行，代码质量分析）
- EXECUTION_REPORT.md（已修复的 4 个 critical bugs 作为参考）
```

---

## 📊 执行顺序建议

### 第一周（P2 高风险任务）
```
Day 1-2: Task 1.1, 1.2（提取公共工具到 common/）
Day 3:   Task 1.3（V10 试点重构 + 测试）
Day 4-5: Task 1.4（V11-V17 批量重构）
```

### 第二周（P2 低风险 + P3）
```
Day 6:   Task 2.1（统一依赖版本）
Day 7-8: Task 3.1（替换硬编码路径）
Day 9:   Task 4.1（修复剩余 bugs）
Day 10:  全面测试 + 文档更新
```

---

## 🛡️ 风险控制策略

### Git 分支策略
```bash
# 为每个主任务创建独立分支
git checkout -b refactor/p2-extract-common    # Task 1
git checkout -b refactor/p2-unify-deps        # Task 2
git checkout -b refactor/p3-fix-paths         # Task 3
git checkout -b refactor/p3-fix-bugs          # Task 4

# 每个任务完成后 merge 到 develop 分支
# 全部测试通过后再 merge 到 main
```

### 测试验证 Checklist
```
□ V10 smoke test 通过（baseline）
□ V17 smoke test 通过（最新版本）
□ RL training test 通过（依赖验证）
□ 单元测试全部通过
□ 集成测试无回归
□ 文档示例代码可运行
```

### 回退计划
- 每个任务保留 before/after 对比数据
- 如果某步失败，回退到上一个 stable commit
- 不要继续下一任务直到当前任务测试通过

---

## 📝 最终交付物

### 代码修改
1. common/ 新增模块：ik_utils.py, failure_classifier.py
2. V10-V17 重构后的 simulate_*.py
3. 所有 requirements.txt 统一版本
4. 59 个文件的路径修复
5. 4 个 minor bugs 修复

### 自动化脚本
1. scripts/refactor_versions.py
2. scripts/unify_requirements.py
3. scripts/fix_hardcoded_paths.py

### 测试和报告
1. 新增单元测试（至少 6 个文件）
2. before/after 对比报告（所有修改版本）
3. 依赖冲突解决报告
4. 路径修复报告

### 文档更新
1. 更新 CLAUDE.md（如果有流程变化）
2. 创建 REFACTORING_GUIDE.md（迁移指南）
3. 更新各版本 README（如果导入方式变化）

---

## 🎯 成功标准

### 定量指标
- [ ] 代码重复减少 > 2500 行（目标 3000+）
- [ ] 依赖版本冲突数：2 → 0
- [ ] 硬编码路径数：59 → 0
- [ ] Minor bugs：4 → 0
- [ ] 单元测试覆盖率 > 70%

### 定性指标
- [ ] 所有版本独立可运行（无跨版本依赖）
- [ ] 项目可在任意目录运行（可移植性）
- [ ] 依赖环境统一可复现
- [ ] 代码可维护性显著提升

---

## 💡 给 Codex 的额外建议

### 编码风格
- 遵循项目现有的代码风格（参考 common/controllers.py）
- 所有新函数添加 type hints
- 所有修改保持向后兼容

### 测试策略
- 先写测试再重构（TDD 风格）
- 每个重构步骤后立即运行测试
- 失败时立即停止，不要继续下一步

### 沟通
- 每完成一个 Task，提供简短总结（200 字内）
- 如果遇到意外问题，立即报告，不要强行推进
- 提供 before/after 对比数据（数值）

### 时间管理
- 每个 Task 设置时间上限
- 如果超时，评估是否需要调整策略
- 不要在一个问题上卡太久

---

## 📚 参考文档索引

- **PROJECT_AUDIT_REPORT.md**: 完整审查结果和问题列表
- **OPTIMIZATION_ACTION_PLAN.md**: P2-P3 详细行动计划
- **EXECUTION_REPORT.md**: 已完成的 P0-P1 任务参考
- **FINAL_SUMMARY.md**: 项目整体状态和下一步建议

---

**最后提醒**: 这是大规模重构，风险较高。建议采用**渐进式策略**：
1. 先完成 Task 1.1-1.3（提取工具 + V10 试点）
2. 测试通过后再继续
3. 每个阶段都可以暂停评估
4. 不追求一次性完成所有任务

Good luck! 🚀

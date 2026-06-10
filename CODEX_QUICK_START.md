# Codex 快速启动指南

## 🚀 如何使用这些提示词

### 方式 1: 逐个任务执行（推荐）

直接复制粘贴到 Codex 对话中：

```
第一天：
1. 复制 "Codex 提示词 1.1 - 提取 IK 工具函数"
2. 粘贴到 Codex
3. 等待完成并测试
4. 继续 "Codex 提示词 1.2"

第二天：
5. "Codex 提示词 1.3 - 重构 V10"（关键试点）
6. 充分测试后才进行下一步

第三-四天：
7. "Codex 提示词 1.4 - 批量重构 V11-V17"
...
```

---

### 方式 2: 批量模式（适合 Codex 专家）

创建一个主控提示词：

```
【Meta 任务】执行 P2-P3 完整重构

我有一份详细的重构计划（见 CODEX_PROMPTS_P2_P3.md），包含：
- P2: 代码重构（4 个子任务）
- P3: 路径和 bug 修复（2 个子任务）

请按以下顺序执行：
1. Task 1.1-1.2: 提取公共工具
2. Task 1.3: V10 试点（关键验证点）
3. Task 1.4: 批量重构 V11-V17
4. Task 2.1: 统一依赖版本
5. Task 3.1: 替换硬编码路径
6. Task 4.1: 修复剩余 bugs

每完成一个任务：
- 运行测试验证
- 生成 before/after 对比
- 如果失败，停止并报告

重要约束：
- Task 1.3 必须测试通过才能继续 1.4
- 所有修改保持向后兼容
- 在独立 git 分支工作

参考文档：CODEX_PROMPTS_P2_P3.md（完整提示词）
```

---

## 📋 任务检查清单

打印或复制到笔记中，跟踪进度：

```
P2 - 代码重构
□ Task 1.1: 提取 IK 工具函数
  □ 创建 common/ik_utils.py
  □ 编写测试
  □ 通过测试

□ Task 1.2: 提取失败分类函数
  □ 创建 common/failure_classifier.py
  □ 编写测试
  □ 通过测试

□ Task 1.3: V10 试点重构 ⭐ 关键里程碑
  □ 修改 simulate_v10.py
  □ 运行 smoke test
  □ 对比 before/after（误差 < 1%）
  □ 如果失败，分析原因并调整

□ Task 1.4: 批量重构 V11-V17
  □ V11 重构 + 测试
  □ V13.6 重构 + 测试
  □ V14 重构 + 测试
  □ V14b 重构 + 测试
  □ V14c 重构 + 测试
  □ V16 重构 + 测试
  □ V17 重构 + 测试
  □ 生成批量对比报告

□ Task 2.1: 统一依赖版本
  □ 创建 unify_requirements.py
  □ 检测冲突
  □ 修复所有 requirements.txt
  □ 测试环境兼容性

P3 - 路径和 Bug 修复
□ Task 3.1: 替换硬编码路径
  □ 创建 fix_hardcoded_paths.py
  □ 修复高优先级文件（5个）
  □ 批量修复剩余 54 个
  □ 测试关键脚本

□ Task 4.1: 修复剩余 bugs
  □ Bug 1: 功率计算逻辑
  □ Bug 2: 绘图函数拆分
  □ Bug 3: 参数验证
  □ Bug 4: 类型签名

最终验证
□ 所有单元测试通过
□ V10/V17 smoke test 通过
□ RL training test 通过
□ 生成最终报告
```

---

## 🎯 关键验证点

### Checkpoint 1: Task 1.3 完成后（Day 3）

**停止并验证**：
```bash
# 运行 V10 完整测试
.\.venv-mujoco\Scripts\python.exe v10_rolling_foot_biomimetic_gait\simulate_v10.py --duration 12.0

# 检查输出
# forward distance 应该与原版误差 < 1%
# alt_td 应该相同

# 如果通过，继续 Task 1.4
# 如果失败，调查原因：
# - common/ik_utils.py 实现是否与原版完全一致？
# - 是否有遗漏的依赖？
# - 浮点误差累积？
```

### Checkpoint 2: Task 1.4 完成后（Day 5）

**停止并验证**：
```bash
# 运行多个版本测试
python scripts/refactor_versions.py --test-all

# 检查对比报告
# 所有版本误差应 < 5%
# 如果某版本失败，单独调查
```

### Checkpoint 3: Task 2.1 完成后（Day 6）

**停止并验证**：
```bash
# 测试环境安装
python -m venv test_env
test_env\Scripts\activate
pip install -r requirements.txt

# 快速验证
python -c "import mujoco; import numpy; print(f'MuJoCo {mujoco.__version__}, NumPy {numpy.__version__}')"
# 应输出：MuJoCo 3.3.7, NumPy 2.2.6
```

---

## ⚠️ 常见问题预案

### 问题 1: V10 测试失败（误差 > 1%）

**可能原因**：
- common/ik_utils.py 实现与原版有细微差异
- 浮点数计算顺序不同导致误差累积

**解决方案**：
1. 逐函数对比：单独测试 smoothstep, leg_ik_front_knee
2. 添加数值容差：允许浮点误差 1e-6
3. 如果仍失败，保留 V10 原实现，仅重构 V11+

---

### 问题 2: 批量重构时某版本失败

**可能原因**：
- 该版本的 qpos 布局不同（如 V14 有摆臂）
- 函数调用方式有版本特定的差异

**解决方案**：
1. 跳过该版本，继续其他版本
2. 单独分析失败版本的差异
3. 可能需要为该版本保留特殊实现

---

### 问题 3: 依赖统一后环境冲突

**可能原因**：
- numpy 2.x 与某些旧代码不兼容
- mujoco 3.x API 变化

**解决方案**：
1. 回退到保守版本（numpy 1.26, mujoco 3.1）
2. 修改不兼容的代码
3. 分阶段升级（先 numpy，后 mujoco）

---

## 💾 备份和回退

### 开始前备份
```bash
# 创建完整备份
git checkout -b backup/before-p2-p3-refactor
git push origin backup/before-p2-p3-refactor

# 在工作分支开始
git checkout -b refactor/p2-p3-main
```

### 如果需要回退
```bash
# 回退到备份点
git checkout main
git reset --hard backup/before-p2-p3-refactor

# 或者回退单个任务
git revert <commit-hash>
```

---

## 📊 进度报告模板

每天结束时，填写进度报告：

```markdown
## P2-P3 重构进度报告 - Day X

### 今日完成
- ✅ Task 1.1: 提取 IK 工具函数
- ✅ Task 1.2: 提取失败分类函数
- 🔄 Task 1.3: V10 试点重构（测试中）

### 测试结果
- common/ik_utils.py: 10/10 测试通过
- common/failure_classifier.py: 8/8 测试通过
- V10 smoke test: forward 4.623m（原版 4.62m，误差 0.065%）✅

### 遇到的问题
- 无

### 明日计划
- 完成 Task 1.3 最终验证
- 开始 Task 1.4（V11 重构）

### 风险评估
- 🟢 低风险：V10 试点成功，可以继续批量重构
```

---

## 🎓 给 Codex 的提示技巧

### 如何提高成功率

**1. 分段执行**
❌ 不好：
```
"重构 V10-V17 所有版本"
```

✅ 好：
```
"先重构 V10，测试通过后我会告诉你继续"
```

**2. 提供上下文**
❌ 不好：
```
"创建 common/ik_utils.py"
```

✅ 好：
```
"根据 CODEX_PROMPTS_P2_P3.md 中的提示词 1.1，创建 common/ik_utils.py。
参考 v10_rolling_foot_biomimetic_gait/simulate_v10.py 第 150-200 行的实现。"
```

**3. 明确成功标准**
❌ 不好：
```
"测试一下"
```

✅ 好：
```
"运行 V10 smoke test，要求：
1. forward distance 误差 < 1%
2. alt_td 数量相同
3. 无警告或错误输出"
```

---

## 📞 需要人工介入的情况

立即停止 Codex，寻求帮助：

1. ❌ **连续 3 个版本测试失败**
   - 可能 common/ 库设计有问题
   - 需要重新评估策略

2. ❌ **依赖统一导致环境完全无法安装**
   - 可能版本选择不当
   - 需要调整目标版本

3. ❌ **V10 试点失败且无法找到原因**
   - 不要继续批量重构
   - 需要深入调试

4. ❌ **Git 分支混乱或合并冲突**
   - 停止编码，先解决 git 问题

---

## 🎯 最终目标检查

完成所有任务后，验证：

```bash
# 1. 代码重复检查
git diff backup/before-p2-p3-refactor --stat
# 应该看到 V10-V17 文件行数显著减少

# 2. 依赖统一检查
grep -r "numpy==" */requirements.txt | sort -u
# 应该只看到一个版本号

# 3. 路径硬编码检查
grep -r "D:\\Dunna\\Documents\\hw-1" *.py
# 应该无结果或仅在注释中

# 4. 测试覆盖率
pytest --cov=common --cov-report=html
# 应该 > 70%

# 5. 最终验证
python -m pytest tests/
.\.venv-mujoco\Scripts\python.exe v10_rolling_foot_biomimetic_gait\simulate_v10.py
.\.venv-mujoco\Scripts\python.exe v17_state_estimation\simulate_v17.py
python rl_training/test_zero_residual_v2.py
# 全部通过 ✅
```

---

## 📚 完成后的文档更新

记得更新：

1. **CLAUDE.md** - 如果导入方式改变
2. **OPTIMIZATION_SUMMARY.md** - 添加 P2-P3 完成状态
3. **VERSIONS.md** - 如果版本行为有变化
4. 创建 **REFACTORING_GUIDE.md** - 记录重构决策和经验

---

**准备好了吗？**

1. ✅ 阅读完 `CODEX_PROMPTS_P2_P3.md`
2. ✅ 打印或保存检查清单
3. ✅ 创建 git 备份分支
4. ✅ 准备好测试环境

**开始执行**：复制第一个提示词（1.1）到 Codex！

祝顺利！有问题随时暂停。🚀

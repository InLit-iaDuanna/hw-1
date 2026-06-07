# 版本控制规范

本文档描述 hw-1 项目的版本控制、分支管理和 commit 规范。

---

## 版本命名规范

### 主版本号（V01-V25）

**格式：** `vXX_descriptive_name`

**示例：**
- `v10_rolling_foot_biomimetic_gait` — 主版本 10
- `v13_6_event_driven_fsm` — 主版本 13，子版本 6
- `v13_7_friction_compensation` — 主版本 13，子版本 7

**命名原则：**
1. 使用两位数字（`v01`, `v10`, `v25`）
2. 描述性名称使用小写下划线分隔
3. 名称体现核心技术特征

---

### 子版本号（V13.1, V13.6, V13.7）

**用途：** 在主版本基础上的增量改进

**示例：**
- `v13_parameter_sensitivity_atlas` — V13 主版本
- `v13_6_event_driven_fsm` — V13.6 子版本（FSM 控制）
- `v13_7_friction_compensation` — V13.7 子版本（摩擦补偿）
- `v13b_floquet_long_run` — V13b 子版本（长程分析）

**子版本标识：**
- 数字：`v13_6`, `v13_7`（重大改进）
- 字母：`v13b`, `v14c`（分析或探索性版本）

---

### 特殊版本标记

**Refactored 版本：**
```
v13_6_refactored/          # V13.6 重构版（代码整理）
v13_7_refactored/          # V13.7 重构版
v16_refactored/            # V16 重构版
v17_refactored/            # V17 重构版
```

**用途：** 代码清理、模块化、文档完善，功能不变。

---

## 目录结构规范

### 标准版本目录

```
vXX_descriptive_name/
├── README.md              # 版本说明文档（必须）
├── model_vXX.xml          # MuJoCo 模型文件
├── simulate_vXX.py        # 主仿真脚本
├── view_vXX.py            # 可视化脚本（可选）
├── control_vXX.py         # 控制律模块（可选）
├── analyze_vXX.py         # 分析脚本（可选）
├── render_vXX.py          # 渲染脚本（可选）
├── params_vXX.yaml        # 默认参数文件（可选）
├── out/                   # 输出目录
│   ├── *.csv              # 轨迹数据
│   ├── *.json             # 摘要数据
│   ├── *.png              # 图表
│   └── *.mp4              # 视频
└── tests/                 # 单元测试（可选）
    └── test_vXX.py
```

---

### README.md 必备内容

每个版本的 README.md 必须包含：

```markdown
# VXX: 版本名称

## 版本定位（1 句话）
简洁描述本版本的核心贡献。

## 关键创新
- 创新点 1
- 创新点 2
- 创新点 3

## 技术路线
从哪个版本演化而来，做了哪些改进。

## 运行方法
```powershell
# 快速运行命令
python vXX_name\simulate_vXX.py --duration 12.0
```

## 成功判据
- 量化指标（forward, CoT, alternations）
- 成功/失败阈值

## 关键结果
- 主要实验数据
- 性能对比

## 已知问题
- 当前版本的局限
- 未来改进方向

## 相关资源
- 依赖版本
- 参考文献
- 相关文档
```

---

## Git 分支策略

### 主分支（main）

**用途：** 稳定版本，可随时运行

**保护规则：**
- 禁止直接 push
- 需要通过 PR（Pull Request）
- 必须通过 CI 测试

---

### 开发分支（dev）

**用途：** 日常开发，集成新功能

**合并策略：**
- 定期从 main 拉取
- 完成阶段性开发后 PR 到 main

---

### 功能分支（feature/*）

**命名格式：** `feature/vXX-description`

**示例：**
```bash
feature/v13_7-friction-compensation
feature/v14b-arm-mass-sweep
feature/v17-kalman-filter
```

**工作流：**
1. 从 dev 创建功能分支
2. 开发新功能
3. 测试通过后 PR 到 dev
4. 删除功能分支

---

### 实验分支（experiment/*）

**命名格式：** `experiment/description`

**示例：**
```bash
experiment/3d-lateral-stability
experiment/sea-stiffness-sweep
```

**用途：**
- 探索性研究
- 不确定是否并入主线
- 可能产生否定结果

**保留策略：**
- 保留 3 个月
- 写入实验日志后可删除

---

## Commit 规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | feat(v13_7): add friction compensation |
| `fix` | Bug 修复 | fix(v10): correct PD gain calculation |
| `docs` | 文档更新 | docs: update V13.6 README |
| `refactor` | 代码重构 | refactor(v16): extract motor model class |
| `test` | 测试相关 | test(v17): add Kalman filter unit tests |
| `perf` | 性能优化 | perf(common): optimize trajectory saving |
| `chore` | 构建/工具 | chore: update .gitignore |
| `style` | 代码格式 | style(v13_6): apply black formatter |

---

### Scope 范围

**版本号：** `v10`, `v13_6`, `v17`

**模块：** `common`, `dashboard`, `ci`, `knowledge_base`

**示例：**
```bash
feat(v13_7): add friction compensation module
fix(common): correct CoT calculation for negative work
docs(knowledge_base): add parameter tuning guide
test(ci): add benchmark regression test
```

---

### Subject 主题

**规则：**
1. 使用祈使句（"add", "fix", "update"，不用 "added", "fixed"）
2. 首字母小写
3. 不超过 50 字符
4. 不加句号

**示例：**
```bash
✅ feat(v13_7): add friction compensation
❌ feat(v13_7): Added friction compensation.
❌ feat(v13_7): Friction compensation was added
```

---

### Body 正文（可选）

**用途：**
- 详细解释修改原因
- 说明技术细节
- 对比修改前后

**格式：**
- 每行不超过 72 字符
- 与 subject 空一行

**示例：**
```
feat(v13_7): add friction compensation

V16 revealed that MX-64AR motor friction (tau_C=0.20 N·m) falls
into the failure band [0.013, 0.20]. This commit adds feedforward
friction compensation to recover stability.

Key changes:
- Add compensate_friction flag to config
- Implement sign_smooth() for velocity sign estimation
- Update control_v137() to include compensation term

Result: forward distance recovers from 0.19m to 4.63m.
```

---

### Footer 页脚（可选）

**用途：**
- 关联 Issue
- 标记 Breaking Change

**示例：**
```
feat(v13_6): refactor FSM to event-driven architecture

BREAKING CHANGE: FSM parameters changed from (kp, kd) to (tau_0-3, theta_01, theta_23).
Users must update config files.

Closes #42
```

---

## 完整 Commit 示例

### 示例 1: 新功能

```bash
git commit -m "feat(v13_7): add friction compensation

V16 revealed MX-64AR friction falls into failure band.
This commit adds feedforward compensation to fix the issue.

- Add compensate_friction config flag
- Implement sign_smooth() for smooth sign function
- Update control_v137() with compensation term

Result: forward 0.19m → 4.63m (24× improvement)

Refs: V16 motor dynamics analysis"
```

---

### 示例 2: Bug 修复

```bash
git commit -m "fix(v10): correct knee spring rest angle

The knee spring rest angle was set to 0 rad, causing
hyperextension. Changed to -0.1 rad (slightly bent).

Impact: success rate improves from 12% to 16.7%."
```

---

### 示例 3: 文档更新

```bash
git commit -m "docs(tutorials): add tutorial 04 for researchers

Add tutorial_04_research_workflow.md covering:
- Energy analysis with V12 tools
- Floquet stability with V13b tools
- Cross-version comparison

Target audience: PhD students and researchers."
```

---

### 示例 4: 重构

```bash
git commit -m "refactor(v13_6): extract FSM logic to separate module

Split 500-line simulate_v136.py into:
- control_v136.py (FSM logic)
- simulate_v136.py (simulation loop)
- analyze_v136.py (post-processing)

No functional changes. All tests pass."
```

---

## 标签（Tags）规范

### 里程碑标签

**格式：** `milestone-vXX`

**示例：**
```bash
git tag -a milestone-v05 -m "V5: Pure passive limit cycle proof"
git tag -a milestone-v10 -m "V10: Stable quasi-passive gait baseline"
git tag -a milestone-v13_7 -m "V13.7: Friction compensation complete"
git tag -a milestone-v17 -m "V17: State estimation integration complete"
git tag -a milestone-v22 -m "V22: Hardware design documentation complete"

git push origin --tags
```

---

### 发布标签

**格式：** `release-YYYY-MM-DD`

**示例：**
```bash
git tag -a release-2026-06-04 -m "Release: V01-V24 complete, ready for hardware"
git push origin release-2026-06-04
```

---

## 工作流示例

### 场景 1: 开发新版本 V26

```bash
# 1. 创建功能分支
git checkout dev
git pull origin dev
git checkout -b feature/v26-compliance-control

# 2. 创建版本目录
mkdir v26_compliance_control
cp v17_refactored/README_template.md v26_compliance_control/README.md

# 3. 开发（多次 commit）
git add v26_compliance_control/
git commit -m "feat(v26): add compliance control skeleton"

git add v26_compliance_control/control_v26.py
git commit -m "feat(v26): implement impedance control law"

git add v26_compliance_control/simulate_v26.py
git commit -m "feat(v26): add simulation script with compliance"

# 4. 测试
python v26_compliance_control/simulate_v26.py
git add tests/test_v26.py
git commit -m "test(v26): add unit tests for compliance controller"

# 5. 更新文档
git add v26_compliance_control/README.md
git commit -m "docs(v26): complete README with results"

# 6. PR 到 dev
git push origin feature/v26-compliance-control
# 在 GitHub/GitLab 创建 PR: feature/v26 → dev

# 7. 合并后删除分支
git checkout dev
git pull origin dev
git branch -d feature/v26-compliance-control
```

---

### 场景 2: 修复 V10 Bug

```bash
# 1. 创建 bugfix 分支
git checkout dev
git checkout -b fix/v10-knee-spring

# 2. 修复 bug
# 编辑 v10_rolling_foot_biomimetic_gait/model_v10.xml
git add v10_rolling_foot_biomimetic_gait/model_v10.xml
git commit -m "fix(v10): correct knee spring rest angle

Changed from 0 rad to -0.1 rad to prevent hyperextension.
Success rate improves from 12% to 16.7%."

# 3. 测试
python v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py

# 4. PR 并合并
git push origin fix/v10-knee-spring
# PR: fix/v10 → dev → main
```

---

### 场景 3: 更新知识库

```bash
# 1. 直接在 dev 分支
git checkout dev

# 2. 更新文档
git add knowledge_base/faq/simulation.md
git commit -m "docs(knowledge_base): add Q10 about NaN in trajectory"

git add knowledge_base/troubleshooting/common_errors.md
git commit -m "docs(knowledge_base): add troubleshooting for XML parsing error"

# 3. 推送
git push origin dev
```

---

## .gitignore 规范

### 项目 .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
.venv-*/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 仿真输出（部分忽略）
*/out/*.csv          # 忽略大体积轨迹
*/out/*.mp4          # 忽略大体积视频
!*/out/*.json        # 保留摘要 JSON
!*/out/*_report.png  # 保留报告图

# 临时文件
*.tmp
*.log
*.bak

# 操作系统
.DS_Store
Thumbs.db

# 数据文件
*.h5
*.hdf5
*.pkl
*.pickle

# MATLAB
*.asv
*.m~

# 大文件（使用 Git LFS）
*.zip
*.tar.gz
*.rar
```

---

## 最佳实践

### ✅ 推荐做法

1. **频繁 commit**
   - 每个独立功能一个 commit
   - 便于回退和 code review

2. **语义化 commit message**
   - 遵循 type(scope): subject 格式
   - 便于生成 CHANGELOG

3. **功能分支开发**
   - 避免污染主分支
   - 方便并行开发

4. **PR 前自测**
   - 运行所有测试
   - 更新相关文档

5. **保持 commit 历史清晰**
   - 使用 rebase 而非 merge（feature 分支）
   - 避免无意义的 merge commit

---

### ❌ 避免做法

1. **直接 push 到 main**
   - 绕过 CI 检查
   - 可能破坏稳定版本

2. **大而全的 commit**
   - 难以 review
   - 难以定位问题

3. **无意义的 commit message**
   - "fix bug", "update", "test"
   - 无法理解修改内容

4. **忘记更新文档**
   - 代码和文档不同步
   - 增加协作成本

5. **忽略 .gitignore**
   - 提交大文件
   - 污染仓库历史

---

## 相关资源

- **Git 官方文档**: https://git-scm.com/doc
- **Conventional Commits**: https://www.conventionalcommits.org/
- **项目 ROADMAP**: `../ROADMAP.md`
- **项目 README**: `../README.md`

---

**最后更新**: 2026-06-05

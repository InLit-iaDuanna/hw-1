# Common 库使用分析与改进建议

## 执行总结

**发现的核心问题**：V18/V19/V20（3D 阶段）**零复用** common/ 库，导致严重的代码重复。

## common/ 库功能清单

已实现 8 个模块：
1. **energy_metrics.py** — CoT、机械能、碰撞损耗
2. **motor_dynamics.py** — L1 电机模型、预设参数库
3. **poincare.py** — Poincaré 截面、Floquet 分析
4. **disturbance.py** — 扰动注入（脉冲、噪声）
5. **terrain.py** — 崎岖地形生成
6. **plot_styles.py** — 统一绘图风格
7. **benchmark.py** — 基准场景（占位）
8. **__init__.py** — 统一导出

## 使用情况统计

### V11-V17（2D 阶段）✅
- **复用率**：9/9 版本使用 common/ = **100%**
- 符合 ROADMAP 预期

### V18-V20（3D 阶段）❌
- **复用率**：0/3 = **0%**
- **重复造轮子**：
  - `_smoothstep`：重复 4 次
  - `_lpd` / `_limited_pd`（PD 控制）：重复 3 次
  - `_jaddr` / `_get_joint_adr`：重复 3 次
  - `_contacts`（触地检测）：重复 3 次
- **缺失分析**：无能量分析（CoT、机械能）→ 无法评估 3D 能效

## 改进建议（优先级排序）

### 🔴 高优先级（立即修复）

1. **新增 `common/control_utils.py`**
   ```python
   def smoothstep(u: float) -> float
   def limited_pd(q, qd, target, kp, kd, limit) -> float
   def ramp_height(x: float, gamma: float) -> float
   ```
   受益：V18/V19/V20（消除 10+ 处重复）

2. **新增 `common/mujoco_utils.py`**
   ```python
   def get_joint_address(model, name: str) -> tuple[int, int]
   def get_contact_flags(model, data, ...) -> tuple[bool, bool]
   ```
   受益：V18/V19/V20（消除 6 处重复）

3. **新增 `common/ik_solvers.py`**
   ```python
   def solve_2d_leg_ik(...) -> tuple[float, float] | None
   def solve_3d_leg_ik(...) -> tuple[float, float, float] | None
   ```
   受益：V18/V19/V20 + V22 硬件版本

4. **V20 重构示范** — 使用新 common/ 工具，减少 ~50 行代码

### 🟡 中优先级（V21+ 准备）

5. **扩展 `energy_metrics.py`** — 支持 3D 能量分析
6. **新增 `common/fsm_phases.py`** — FSM 相位管理（已在 V13.6-V17 重复定义）
7. **更新 `terrain.py`** — 支持 3D 侧向地形

### 🟢 低优先级（维护性）

8. **`benchmark.py` 填充** — 完善场景库
9. **`disturbance.py` 扩展** — 增加 3D 扰动类型

## 根因分析

**V18-V20 未使用 common/ 的原因**：
1. 架构断层：V18 从头编写 3D 模型，未继承 V10-V17 结构
2. 时间压力：快速验证，缺少重构时间
3. 功能缺口：common/ 缺少 3D 特定工具

## 推荐行动

**立即**（V21 前）：
- 创建 3 个新模块（control_utils, mujoco_utils, ik_solvers）
- 重构 V20 作为模板

**长期收益**：
- 减少 50-100 行/版本重复代码
- 统一数值方法（避免实现差异 bug）
- 加速 V22+ 硬件迭代

---

详细分析见 subagent 完整报告。

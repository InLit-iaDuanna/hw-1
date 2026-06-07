# MuJoCo-FEA Integration Framework

完整的 MuJoCo 仿真 → 有限元分析 → 设计验证集成框架，用于 hw-1 步态训练辅助设备的机械设计迭代。

---

## 目录

1. [框架概述](#框架概述)
2. [模块架构](#模块架构)
3. [快速开始](#快速开始)
4. [详细工作流](#详细工作流)
5. [应用场景](#应用场景)
6. [高级功能](#高级功能)
7. [故障排查](#故障排查)

---

## 框架概述

### 设计目标

从 MuJoCo 动力学仿真中提取接触载荷，自动生成 FEA 边界条件，完成应力分析并验证机械设计是否满足强度、刚度、疲劳寿命等约束条件。

### 核心流程

```
MuJoCo 仿真 CSV
    ↓
[1] 提取接触力时程 (extract_contact_forces.py)
    ↓
接触力数据 JSON
    ↓
[2] 生成 FEA 边界条件 (generate_fea_boundary_conditions.py)
    ↓
Abaqus .inp 文件
    ↓
[3] 运行 FEA 分析 (Abaqus/Explicit or Standard)
    ↓
ODB 结果文件
    ↓
[4] 解析应力结果 (parse_fea_results.py)
    ↓
设计度量 JSON
    ↓
[5] 验证设计约束 (design_constraint_validator.py)
    ↓
通过/失败判定 + 改进建议
```

---

## 模块架构

### 核心模块

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `extract_contact_forces.py` | 从 MuJoCo CSV 提取接触力 | 仿真 CSV 文件 | 接触力 JSON |
| `generate_fea_boundary_conditions.py` | 生成 FEA 边界条件 | 接触力 JSON | Abaqus .inp / JSON BC |
| `parse_fea_results.py` | 解析 FEA 应力结果 | Abaqus ODB/JSON | 应力分析报告 |
| `design_constraint_validator.py` | 设计约束验证 | FEA 结果 + MuJoCo 数据 | 验证报告 |
| `workflow_example.py` | 完整工作流编排 | 版本号 + 材料 | 端到端设计报告 |

### 辅助模块

- `build_heel_strike_model.py` — 生成 Abaqus 轴对称足部冲击模型
- `build_tpu_model.py` — 生成双层材料模型（刚性核心 + TPU 缓冲层）
- `postprocess_odb.py` — Abaqus Python 后处理脚本
- `impact_conditions.py` — V10 冲击条件提取（遗留，已被 extract_contact_forces.py 替代）

---

## 快速开始

### 先决条件

- Python 3.10+ with `numpy`
- Abaqus 2020+ (CAE + Solver)
- hw-1 项目已完成至少一个版本的 MuJoCo 仿真（例如 v10）

### 安装

```powershell
# 进入 fea_heel_strike 目录
cd D:\Dunna\Documents\hw-1\fea_heel_strike

# 确保 Python 环境有 numpy
python -c "import numpy; print(numpy.__version__)"
```

### 最简单运行方式：完整工作流

```powershell
# 完整工作流（跳过 FEA 执行，使用已有结果）
python workflow_example.py --version v10 --material PLA --skip-fea

# 如果 Abaqus 可用且想重新运行 FEA
python workflow_example.py --version v10 --material PLA --run-all
```

**输出**：
- `out/workflow_v10/contact_forces.json` — 提取的接触力
- `out/workflow_v10/boundary_conditions.json` — FEA 边界条件
- `out/workflow_v10/validation_report.json` — 设计验证报告

---

## 详细工作流

### Step 1: 提取接触力

从任何 hw-1 版本的 MuJoCo 仿真 CSV 中提取接触力峰值和时间历程。

#### 用法

```powershell
# 从版本目录自动提取（推荐）
python extract_contact_forces.py --version v10 --event heel_strike --foot left

# 从特定 CSV 提取
python extract_contact_forces.py --csv D:\path\to\sim_data.csv --event heel_strike

# 提取完整时间历程（用于动态 FEA）
python extract_contact_forces.py --csv sim_data.csv --history --start-time 2.5 --duration 0.01
```

#### 输出示例

```json
{
  "version": "v10_rolling_foot_biomimetic_gait",
  "event_type": "heel_strike",
  "num_events": 4,
  "events": [
    {
      "time": 2.145,
      "force_normal_N": 385.2,
      "velocity_z_m_s": -0.762
    }
  ],
  "statistics": {
    "peak_force_avg_N": 380.5,
    "velocity_z_avg_m_s": -0.758
  }
}
```

#### 支持的事件类型

- `heel_strike` — 足跟触地峰值力（用于冲击分析）
- `toe_off` — 脚趾离地瞬间（用于推进相分析）
- `steady_contact` — 稳定接触期（用于静态应力分析）

---

### Step 2: 生成 FEA 边界条件

将接触力数据转换为 Abaqus 可用的边界条件格式。

#### 用法

```powershell
# 从接触力 JSON 生成 BC
python generate_fea_boundary_conditions.py --contact-data out/v10_contact_forces.json --output-format all

# 从版本自动提取并生成（一步完成）
python generate_fea_boundary_conditions.py --version v10 --bc-type initial_velocity

# 生成时变载荷（用于隐式动力学）
python generate_fea_boundary_conditions.py --contact-data contact_history.json --bc-type force_history
```

#### 边界条件类型

| BC 类型 | 适用场景 | FEA 方法 | 输出格式 |
|---------|---------|----------|---------|
| `initial_velocity` | 冲击分析（默认） | Abaqus/Explicit | `*INITIAL CONDITIONS, TYPE=VELOCITY` |
| `force_history` | 动态加载 | Abaqus/Standard 或 Explicit | `*AMPLITUDE` 定义 |
| `quasi_static` | 峰值应力静态分析 | Abaqus/Standard | `*CLOAD` 静态载荷 |

#### 输出文件

- `initial_velocity_bc.json` — BC 规格（通用格式）
- `initial_velocity_bc_initial.inp` — Abaqus 初始条件片段
- `initial_velocity_bc.py` — Python 脚本（可集成到模型生成器）

---

### Step 3: 运行 FEA 分析

#### 方法 A：手动运行（推荐用于调试）

```powershell
cd out

# 生成模型（在 Abaqus/CAE 中）
abaqus cae noGUI=..\build_heel_strike_model.py

# 提交求解
abaqus job=Job_HeelStrike cpus=4 interactive

# 后处理
abaqus python ..\postprocess_odb.py Job_HeelStrike.odb
```

#### 方法 B：通过工作流自动化

```powershell
python workflow_example.py --version v10 --material PLA --step 3
```

#### 材料选择

修改 `build_heel_strike_model.py` 第 312 行附近：

```python
# PLA (默认)
E = 3500e6  # Pa
nu = 0.36
yield_stress = 60e6

# AL6061-T6
E = 69e9
nu = 0.33
yield_stress = 276e6

# TPU-95A (使用 build_tpu_model.py)
```

---

### Step 4: 解析 FEA 结果

从 Abaqus 输出中提取设计相关指标。

#### 用法

```powershell
# 解析单个材料结果
python parse_fea_results.py --json-results out/heel_strike_results.json

# 材料对比（基于弹性缩放估算）
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials

# 指定材料列表
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials --materials PLA AL6061-T6 TPU-95A
```

#### 提取的设计度量

- **峰值应力**: von Mises 等效应力（MPa）
- **安全系数**: SF_yield = σ_yield / σ_peak
- **塑性变形**: PEEQ（等效塑性应变）
- **接触压力**: 峰值接触力和接触时间
- **能量平衡**: 应变能、塑性耗散、动能

#### 输出示例

```json
{
  "material": "PLA",
  "peak_von_mises_MPa": 60.42,
  "safety_factor_yield": 0.99,
  "peak_PEEQ": 0.0175,
  "pass_fail_status": "FAIL",
  "failure_mode": "Yield stress exceeded"
}
```

---

### Step 5: 设计约束验证

综合 MuJoCo 性能和 FEA 应力结果，验证设计是否满足所有约束。

#### 用法

```powershell
# 完整验证（使用默认设计要求）
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json

# 自定义安全系数要求
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json --min-sf 2.0

# 使用自定义设计要求配置
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json --config my_requirements.json
```

#### 验证项

| 类别 | 检查项 | 约束条件 |
|------|--------|----------|
| **结构强度** | 屈服安全系数 | SF_yield ≥ 1.5 |
|  | 塑性变形 | PEEQ < 0.01 |
| **性能** | 步行速度 | 0.3-1.2 m/s |
|  | 步态稳定性 | 不摔倒 |
| **疲劳寿命** | 循环寿命 | ≥ 100,000 步 |
| **制造** | 材料兼容性 | 3D 打印/CNC/注塑 |
|  | 成本 | < $500/leg |

#### 验证报告示例

```
=======================================================================
  DESIGN VALIDATION REPORT: v10 (PLA)
=======================================================================

OVERALL STATUS: ✗ FAIL
  Checks passed: 6/9 (66.7%)

----------------------------------------------------------------------
VALIDATION CHECKS:
----------------------------------------------------------------------

✗ 🔴 Safety Factor (Yield)
   Requirement: SF >= 1.5
   Measured: 0.99
   ⚠ Ensures no permanent deformation under normal loads

✓ 🟡 Fatigue Life
   Requirement: >= 100000 cycles
   Measured: infinite
   Stress below endurance limit (24.0 MPa) - infinite life

----------------------------------------------------------------------
RECOMMENDATIONS:
----------------------------------------------------------------------
⚠ CRITICAL ISSUES DETECTED - Design requires modification:
  • Safety Factor (Yield): Ensures no permanent deformation under normal loads
Consider upgrading to AL6061-T6 for higher strength
Alternative: Add TPU damping layer to reduce peak stress
Alternative: Increase heel radius to distribute contact load
```

---

## 应用场景

### 场景 1: V10 足部接触峰值应力分析

**目标**: 验证 V10 rolling foot 在 heel-strike 时是否会导致结构失效。

```powershell
# 完整工作流
python workflow_example.py --version v10 --material PLA --skip-fea --compare-materials

# 输出
# - PLA: SF=0.99 → FAIL
# - AL6061-T6: SF=4.57 → PASS
# - TPU-95A: SF=0.14 → FAIL (too soft, large deformation)
```

**结论**: PLA 不满足安全系数要求，建议改用铝合金或增加 TPU 缓冲层。

---

### 场景 2: V22 硬件设计材料验证

**目标**: 为 V22 实体硬件选择合适材料，确保满足 SF≥1.5 且重量最轻。

```powershell
# Step 1: 从 V19（最新稳定版本）提取接触力
python extract_contact_forces.py --version v19 --event heel_strike

# Step 2: 生成边界条件
python generate_fea_boundary_conditions.py --version v19 --bc-type initial_velocity

# Step 3: 对比多种材料（如果有 Abaqus，分别运行每种材料）
# 或使用弹性缩放估算
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials

# Step 4: 验证
python design_constraint_validator.py --version v19 --fea-results out/heel_strike_results.json --min-sf 1.5

# 输出排序（按 SF 排序）
# 1. AL6061-T6: SF=4.57, mass=0.35kg → 推荐
# 2. PETG: SF=2.1, mass=0.16kg
# 3. PLA: SF=0.99 → 不合格
```

**决策**: 使用 AL6061-T6（CNC 加工）或 PETG（3D 打印原型）。

---

### 场景 3: 不同步态参数的影响分析

**目标**: 研究步行速度、摩擦系数对接触力的影响。

```powershell
# 运行 V10 的多种参数变体（需要先生成这些仿真）
python extract_contact_forces.py --version v10_speed_0.5 --output out/v10_speed05_forces.json
python extract_contact_forces.py --version v10_speed_1.0 --output out/v10_speed10_forces.json

# 对比峰值力
python -c "
import json
with open('out/v10_speed05_forces.json') as f:
    d05 = json.load(f)
with open('out/v10_speed10_forces.json') as f:
    d10 = json.load(f)
print(f'Speed 0.5 m/s: {d05[\"statistics\"][\"peak_force_avg_N\"]} N')
print(f'Speed 1.0 m/s: {d10[\"statistics\"][\"peak_force_avg_N\"]} N')
"
```

---

### 场景 4: 疲劳寿命估算

**目标**: 估算设备在 100,000 步循环载荷下的疲劳寿命。

```powershell
# 运行验证（包含疲劳检查）
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json

# 查看疲劳寿命检查
# - 如果应力 < 疲劳极限 → 无限寿命
# - 否则使用 Basquin 方程估算循环次数
```

**输出**:
```
✓ Fatigue Life
   Requirement: >= 100000 cycles
   Measured: infinite
   Stress below endurance limit (24.0 MPa) - infinite life
```

---

## 高级功能

### 时变载荷分析（隐式动力学）

如果需要完整接触力时程（而非仅初速度）：

```powershell
# 提取时间历程
python extract_contact_forces.py --csv v10_sim.csv --history --start-time 2.5 --duration 0.01

# 生成 *AMPLITUDE 定义
python generate_fea_boundary_conditions.py --contact-data contact_history.json --bc-type force_history

# 在 Abaqus 中使用 *DYNAMIC, EXPLICIT 或 *DYNAMIC（隐式）
```

### 材料参数敏感性分析

修改 `parse_fea_results.py` 中的 `MATERIALS` 字典添加新材料：

```python
MATERIALS["Custom_Composite"] = MaterialProperties(
    name="Custom_Composite",
    elastic_modulus_Pa=15e9,
    poisson_ratio=0.30,
    yield_stress_Pa=150e6,
    density_kg_m3=1600,
)
```

### 自定义设计约束

创建 `custom_requirements.json`:

```json
{
  "min_safety_factor_yield": 2.0,
  "min_safety_factor_ultimate": 3.0,
  "max_plastic_deformation": 0.005,
  "target_gait_cycles": 200000,
  "max_device_mass_kg": 2.0
}
```

运行验证:
```powershell
python design_constraint_validator.py --version v10 --fea-results out/results.json --config custom_requirements.json
```

---

## 故障排查

### 问题 1: "No CSV files found in out/"

**原因**: 版本目录中未运行 MuJoCo 仿真或 CSV 文件位置不对。

**解决**:
```powershell
# 检查 CSV 是否存在
ls D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\out\*.csv

# 如果不存在，运行 MuJoCo 仿真
cd D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait
python simulate.py
```

---

### 问题 2: "No contact force data found"

**原因**: CSV 中缺少接触力列或列名不匹配。

**解决**:
- 检查 CSV 列名（`extract_contact_forces.py` 支持多种命名约定）
- 确保仿真启用了接触力传感器或接触检测
- 如果是旧版本 CSV，手动指定列名

---

### 问题 3: Abaqus 求解失败

**常见原因**:
- 材料过软（如 TPU）导致大变形 → 增加几何非线性
- 网格过粗 → 减小单元尺寸
- 时间步过大 → 减小 `timePeriod` 或启用自动时间步

**调试**:
```powershell
# 查看 Abaqus 日志
cat out\Job_HeelStrike.msg
cat out\Job_HeelStrike.sta

# 检查收敛性
abaqus viewer odb=out\Job_HeelStrike.odb
```

---

### 问题 4: 材料对比结果不准确

**原因**: `compare_materials()` 使用弹性缩放估算，仅对线弹性材料粗略有效。

**解决**: 对每种材料分别运行完整 FEA 分析以获得精确结果。

```powershell
# 为每种材料运行 FEA
for material in PLA AL6061-T6 PETG; do
    # 修改 build_heel_strike_model.py 中的材料参数
    # 运行 FEA
    # 保存结果
done
```

---

## 输出文件索引

| 文件 | 生成模块 | 内容 |
|------|---------|------|
| `out/contact_forces.json` | extract_contact_forces.py | 接触力峰值和统计 |
| `out/bc/initial_velocity_bc.json` | generate_fea_boundary_conditions.py | 边界条件规格 |
| `out/bc/initial_velocity_bc_initial.inp` | generate_fea_boundary_conditions.py | Abaqus IC 片段 |
| `out/Job_HeelStrike.inp` | build_heel_strike_model.py | Abaqus 输入文件 |
| `out/Job_HeelStrike.odb` | Abaqus Solver | 结果数据库 |
| `out/heel_strike_results.json` | postprocess_odb.py | 应力结果摘要 |
| `out/design_validation_report.json` | parse_fea_results.py | 材料对比报告 |
| `out/v10_validation_report.json` | design_constraint_validator.py | 设计验证报告 |

---

## 参考资料

### 相关文档

- `README.md` — fea_heel_strike 目录概览
- `D:\Dunna\Documents\hw-1\README.md` — hw-1 项目主文档
- Abaqus 文档: Analysis User's Guide → Explicit Dynamic Analysis

### 材料数据来源

- PLA: 3D 打印常用 PLA 数据表
- AL6061-T6: MMPDS-01 (Metallic Materials Properties)
- TPU-95A: Manufacturer datasheet (Shore 95A thermoplastic polyurethane)

### 理论基础

- **von Mises 应力**: 延性材料屈服判据
- **安全系数**: SF = σ_allowable / σ_actual
- **疲劳寿命**: Basquin 方程 N = (S_f / S_a)^(1/b)

---

## 更新日志

- **2026-06-04**: 创建完整集成框架，包含 5 个核心模块和端到端工作流
- **2026-06-03**: 添加 TPU 双层材料模型支持
- **2026-06-02**: 初始 heel-strike 冲击分析实现

---

## 联系方式

如有问题或改进建议，请参考：
- hw-1 项目主 README
- 内存文件: `project-hw1-rehab-device.md`, `project-hw1-compass-gait.md`

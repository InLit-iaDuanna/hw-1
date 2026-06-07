# FEA Heel-Strike Impact Analysis

完整的 **MuJoCo → FEA 集成分析框架**，用于 hw-1 步态训练辅助设备的机械设计验证。

从 MuJoCo 仿真中提取接触载荷，自动生成 FEA 边界条件，完成应力分析并验证设计是否满足强度、疲劳、制造等全部约束条件。

---

## 🚀 快速开始

```powershell
# 完整工作流（使用已有 FEA 结果）
python workflow_example.py --version v10 --material PLA --skip-fea

# 如果 Abaqus 可用，完整运行包括 FEA
python workflow_example.py --version v10 --material AL6061-T6 --run-all --compare-materials
```

**输出**: 设计验证报告，包含安全系数、疲劳寿命、材料对比、设计建议。

---

## 📚 文档

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** — 完整集成框架文档（模块架构、API、故障排查）
- **[EXAMPLES.md](EXAMPLES.md)** — 7 个真实应用场景（材料选型、参数优化、疲劳分析等）
- **README.md**（本文件）— 快速概览

---

## 🧩 框架架构

### 完整流程

```
MuJoCo CSV → [1] 提取接触力 → [2] 生成 BC → [3] FEA 分析 → [4] 解析结果 → [5] 设计验证
```

### 核心模块

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `extract_contact_forces.py` | 从 MuJoCo 提取接触力峰值和时程 | 仿真 CSV | 接触力 JSON |
| `generate_fea_boundary_conditions.py` | 生成 Abaqus/ANSYS 边界条件 | 接触力 JSON | .inp / JSON BC |
| `parse_fea_results.py` | 解析应力、安全系数、能量 | FEA 结果 | 设计度量 JSON |
| `design_constraint_validator.py` | 验证强度/疲劳/制造约束 | FEA + MuJoCo | 验证报告 |
| `workflow_example.py` | 端到端工作流编排 | 版本 + 材料 | 完整报告 |

---

## 💡 典型应用场景

### 场景 1: 材料选型（V10 → V22）

```powershell
python workflow_example.py --version v10 --material PLA --skip-fea --compare-materials
```

**结果**:
- PLA: SF=0.99 → ❌ FAIL
- AL6061-T6: SF=4.57 → ✅ PASS（推荐）
- PETG: SF=2.12 → ✅ PASS（原型）

### 场景 2: 设计验证

```powershell
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json
```

**验证项**:
- ✅ 屈服安全系数 ≥ 1.5
- ✅ 疲劳寿命 ≥ 100,000 步
- ✅ 步行速度 0.3-1.2 m/s
- ✅ 制造成本 < $500

### 场景 3: TPU 缓冲层优化

```powershell
cd out
abaqus cae noGUI=..\build_tpu_model.py  # 双层模型（PLA 核心 + TPU 外层）
abaqus job=Job_HeelStrike_TPU cpus=4 interactive
```

**改进效果**: 峰值应力降低 25%，接触时间延长 34%

---

## 🔧 分步运行

如果只需要运行特定步骤：

```powershell
# Step 1: 提取接触力
python extract_contact_forces.py --version v10 --event heel_strike

# Step 2: 生成边界条件
python generate_fea_boundary_conditions.py --version v10 --bc-type initial_velocity

# Step 3: 运行 FEA（需要 Abaqus）
cd out
abaqus cae noGUI=..\build_heel_strike_model.py
abaqus job=Job_HeelStrike cpus=4 interactive
abaqus python ..\postprocess_odb.py Job_HeelStrike.odb

# Step 4: 解析结果
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials

# Step 5: 设计验证
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json
```

---

## 📊 V10 冲击条件（MuJoCo 提取）

| 参数 | 值 | 来源 |
|------|------|------|
| 跟部垂直冲击速度 | 0.76 m/s | V10 稳态 4 次 heel-strike 平均 |
| 有效质量 | 2.5 kg | 半体质量近似 |
| 冲击动能 | 0.72 J | 0.5×m×v² |
| 峰值力实测 | 380 N | MuJoCo 接触力传感器 |
| 跟部半径 | 40 mm | V10 XML |
| 地面摩擦系数 | 1.35 | V10 参数 |

---

## 🎯 V22 设计决策支持

### 已验证结论

| 材料 | SF (屈服) | 疲劳寿命 | 质量 | 成本 | 制造 | 结论 |
|------|-----------|---------|------|------|------|------|
| **AL6061-T6** | 4.57 | 无限 | 0.35 kg | $375 | CNC | ✅ **推荐** |
| PETG | 2.12 | 80k 步 | 0.16 kg | $60 | 3D 打印 | ✅ 原型 |
| PLA | 0.99 | 15k 步 | 0.16 kg | $45 | 3D 打印 | ❌ 不合格 |
| TPU-95A | 0.14 | - | 0.14 kg | $70 | 3D 打印 | ⚠ 仅缓冲层 |

### 设计建议

1. **最终硬件**: AL6061-T6 CNC 加工（高强度、无限疲劳寿命）
2. **快速原型**: PETG 3D 打印（验证几何，成本低）
3. **可选优化**: PLA/PETG 核心 + TPU 外层（降低冲击应力 25%）

---

## 📁 输出文件

| 文件 | 生成模块 | 内容 |
|------|---------|------|
| `out/contact_forces.json` | extract_contact_forces | 接触力峰值和统计 |
| `out/bc/initial_velocity_bc.inp` | generate_fea_boundary_conditions | Abaqus 初始条件 |
| `out/Job_HeelStrike.odb` | Abaqus Solver | FEA 结果数据库 |
| `out/heel_strike_results.json` | postprocess_odb | 应力/能量摘要 |
| `out/design_validation_report.json` | parse_fea_results | 材料对比报告 |
| `out/v10_validation_report.json` | design_constraint_validator | 设计验证报告 |

---

## 🛠 技术规格

### FEA 分析设置

- **求解器**: Abaqus/Explicit（冲击瞬态）
- **几何**: 轴对称半球 r=40mm + 刚性地面
- **单元**: CAX4R（四节点轴对称，缩减积分）
- **网格**: 1mm 单元尺寸，~2000 单元
- **接触**: General contact + Coulomb 摩擦 μ=1.35
- **质量**: 2.5 kg 点质量（模拟上方体重）
- **分析时间**: 10 ms

### 支持的材料

- **PLA**: E=3.5 GPa, σ_y=60 MPa, ρ=1240 kg/m³
- **AL6061-T6**: E=69 GPa, σ_y=276 MPa, ρ=2700 kg/m³
- **TPU-95A**: E=26 MPa, σ_y=8.6 MPa, ρ=1120 kg/m³
- **PETG**: E=2.2 GPa, σ_y=53 MPa, ρ=1270 kg/m³

---

## 🔍 高级功能

### 时变载荷（隐式动力学）

```powershell
python extract_contact_forces.py --csv sim.csv --history --start-time 2.5 --duration 0.01
python generate_fea_boundary_conditions.py --contact-data history.json --bc-type force_history
```

### 参数化研究

修改 `workflow_example.py` 批量运行不同几何/材料组合。

### 自定义设计约束

创建 `custom_requirements.json`:
```json
{
  "min_safety_factor_yield": 2.0,
  "target_gait_cycles": 200000,
  "max_device_mass_kg": 2.5
}
```

---

## 🐛 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| "No CSV files found" | MuJoCo 仿真未运行 | 运行 `python simulate.py` |
| "No contact force data" | 列名不匹配 | 检查 CSV 列名（支持多种约定） |
| Abaqus 求解失败 | 材料过软/网格过粗 | 减小时间步或细化网格 |
| 材料对比不准确 | 弹性缩放仅为估算 | 为每种材料单独运行 FEA |

详见 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) 故障排查章节。

---

## 📖 相关文档

- hw-1 主项目: `D:\Dunna\Documents\hw-1\README.md`
- 内存文件: `project-hw1-rehab-device.md`, `project-hw1-compass-gait.md`
- Abaqus 文档: Analysis User's Guide → Explicit Dynamic Analysis

---

## 更新日志

- **2026-06-04**: ✅ 完整集成框架（5 个核心模块 + 端到端工作流 + 完整文档）
- **2026-06-03**: 添加 TPU 双层材料模型支持
- **2026-06-02**: 初始 heel-strike 冲击分析实现

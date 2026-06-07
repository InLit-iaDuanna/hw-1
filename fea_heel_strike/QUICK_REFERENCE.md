# MuJoCo-FEA Quick Reference

快速参考卡片 — 最常用的命令和工作流。

---

## 一键完整工作流

```powershell
# 完整验证（使用已有 FEA 结果）
cd D:\Dunna\Documents\hw-1\fea_heel_strike
python workflow_example.py --version v10 --material PLA --skip-fea

# 包含材料对比
python workflow_example.py --version v10 --material PLA --skip-fea --compare-materials

# 完整运行（需要 Abaqus）
python workflow_example.py --version v10 --material AL6061-T6 --run-all
```

---

## 单步命令

### 1. 提取接触力

```powershell
# 从版本目录自动提取
python extract_contact_forces.py --version v10 --event heel_strike

# 从特定 CSV 文件
python extract_contact_forces.py --csv D:\path\to\sim_data.csv --event heel_strike

# 提取时间历程（用于动态 FEA）
python extract_contact_forces.py --csv sim_data.csv --history --start-time 2.5 --duration 0.01
```

### 2. 生成边界条件

```powershell
# 从接触力 JSON 生成
python generate_fea_boundary_conditions.py --contact-data out/v10_contact.json --output-format all

# 从版本自动提取并生成（一步完成）
python generate_fea_boundary_conditions.py --version v10 --bc-type initial_velocity

# 生成时变载荷
python generate_fea_boundary_conditions.py --contact-data history.json --bc-type force_history
```

### 3. 运行 FEA

```powershell
cd out

# 生成模型
abaqus cae noGUI=..\build_heel_strike_model.py

# 运行求解
abaqus job=Job_HeelStrike cpus=4 interactive

# 后处理
abaqus python ..\postprocess_odb.py Job_HeelStrike.odb

cd ..
```

### 4. 解析结果

```powershell
# 解析单个结果
python parse_fea_results.py --json-results out/heel_strike_results.json

# 材料对比
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials

# 指定材料
python parse_fea_results.py --json-results out/heel_strike_results.json --compare-materials --materials PLA AL6061-T6
```

### 5. 设计验证

```powershell
# 标准验证
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json

# 自定义安全系数
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json --min-sf 2.0

# 使用自定义配置
python design_constraint_validator.py --version v10 --fea-results out/heel_strike_results.json --config requirements.json
```

---

## 测试

```powershell
# 运行集成测试
python test_integration.py
```

---

## 输出文件位置

| 文件 | 位置 |
|------|------|
| 接触力 | `out/contact_forces.json` |
| 边界条件 | `out/bc/initial_velocity_bc.json` |
| FEA 输入 | `out/Job_HeelStrike.inp` |
| FEA 结果 | `out/Job_HeelStrike.odb` |
| 应力摘要 | `out/heel_strike_results.json` |
| 材料对比 | `out/design_validation_report.json` |
| 验证报告 | `out/v10_validation_report.json` |

---

## 调试命令

```powershell
# 查看 CSV 列名
Get-Content D:\Dunna\Documents\hw-1\v10*\out\*.csv -TotalCount 1

# 检查 FEA 收敛
Get-Content out\Job_HeelStrike.sta -Tail 20

# 可视化结果
abaqus viewer odb=out\Job_HeelStrike.odb

# JSON 美化
python -m json.tool out/contact_forces.json
```

---

## 常见参数

### 边界条件类型
- `initial_velocity` — 冲击分析（Explicit）
- `force_history` — 动态加载（Implicit/Explicit）
- `quasi_static` — 静态峰值应力

### 事件类型
- `heel_strike` — 足跟触地
- `toe_off` — 脚趾离地
- `steady_contact` — 稳定接触期

### 材料选项
- `PLA` — 3D 打印原型
- `AL6061-T6` — CNC 加工生产
- `PETG` — 3D 打印改进强度
- `TPU-95A` — 缓冲层（仅与其他材料组合）

---

## 设计决策矩阵

| 材料 | 强度 | 疲劳 | 重量 | 成本 | 制造 | 推荐用途 |
|------|------|------|------|------|------|---------|
| **AL6061-T6** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | CNC | 最终硬件 |
| **PETG** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 3D打印 | 验证原型 |
| **PLA** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 3D打印 | 概念验证 |
| **TPU-95A** | ⭐ | - | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 3D打印 | 仅缓冲层 |

---

## 故障排查快速索引

| 错误 | 原因 | 解决 |
|------|------|------|
| "No CSV files found" | 未运行 MuJoCo 仿真 | `cd v10*; python simulate.py` |
| "No contact force data" | 列名不匹配 | 检查 CSV 列名 |
| Abaqus 不收敛 | 材料过软/网格粗 | 减小时间步或细化网格 |
| 材料对比不准 | 弹性估算误差 | 为每种材料单独运行 FEA |

---

## 版本信息

- **框架版本**: 1.0 (2026-06-04)
- **Python**: 3.10+
- **依赖**: numpy
- **FEA**: Abaqus 2020+

---

## 文档链接

- **[README.md](README.md)** — 主文档
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** — 详细集成指南
- **[EXAMPLES.md](EXAMPLES.md)** — 应用示例
- **QUICK_REFERENCE.md**（本文件）— 快速参考

---

## 支持

详见：
- hw-1 项目: `D:\Dunna\Documents\hw-1\README.md`
- 内存: `project-hw1-rehab-device.md`, `project-hw1-compass-gait.md`

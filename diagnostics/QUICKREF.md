# hw-1 诊断系统快速参考

## 命令行工具

### 交互式诊断向导
```bash
python -m diagnostics.diagnostic_wizard
```
自动分析文件、交互式问答、搜索知识库

### 系统健康检查
```bash
# 基础检查
python -m diagnostics.health_checker

# 包含 smoke test
python -m diagnostics.health_checker --smoke-test

# 导出报告
python -m diagnostics.health_checker --export health_report.json
```

### 运行测试
```bash
python diagnostics/test_diagnostics.py
```

### 查看演示
```bash
python diagnostics/demo.py
```

## Python API 快速使用

### 检测错误
```python
from diagnostics import ErrorDetector

detector = ErrorDetector()

# 从仿真结果检测
result = {"success": False, "failure": "fall_down", "forward": 0.5}
errors = detector.detect_from_data(result)

# 从 JSON 文件检测
errors = detector.detect_from_json("v10/out/result.json")

# 从时间序列检测
import numpy as np
errors = detector.detect_from_timeseries(qpos=qpos_array)
```

### 查询解决方案
```python
from diagnostics import SolutionDatabase

db = SolutionDatabase()

# 获取特定错误
entry = db.get("simulation_nan")
print(entry.format())

# 搜索关键词
results = db.search("motor")

# 推荐解决方案
recommendations = db.recommend_solutions(["fall_down", "simulation_nan"])
```

### 综合分析
```python
from diagnostics import ErrorDetector, SolutionDatabase

detector = ErrorDetector()
db = SolutionDatabase()

# 分析仿真结果
result = {...}
report = detector.analyze_simulation_result(result)

if report["has_errors"]:
    for error_info in report["errors"]:
        entry = db.get(error_info["type"])
        print(f"错误: {entry.error_type}")
        print(f"解决方案: {entry.solutions[0].action}")
```

## 知识库内容 (17 个错误)

### 仿真错误 (simulation_errors)
1. **simulation_nan** - NaN/积分错误 → 减小 dt, 检查初始高度
2. **fall_down** - 机器人摔倒 → 提高扭矩, FSM 调优, 摩擦补偿
3. **fly_away** - 机器人飞走 → 修复穿透, 降低 swing thrust
4. **penetration** - 穿透地面 → 提高接触刚度
5. **no_alternation** - 无法交替 → 提高 swing_thrust_k_E

### 参数错误 (parameter_errors)
6. **invalid_timestep** - 无效时间步长
7. **invalid_initial_height** - 初始高度错误
8. **motor_friction_failure_band** - 电机摩擦在失败带 [0.013, 0.20] N·m (V16)
9. **arm_mass_too_heavy** - 摆臂过重 (>= 0.05 kg, V14)

### 环境错误 (environment_errors)
10. **mujoco_not_found** - MuJoCo 未安装
11. **model_file_not_found** - 模型文件不存在
12. **common_import_error** - common 库导入失败

### 数据错误 (data_errors)
13. **csv_corrupted** - CSV 文件损坏
14. **json_schema_mismatch** - JSON 格式不匹配

### 性能错误 (performance_errors)
15. **simulation_too_slow** - 仿真速度过慢

### 拓扑错误 (topology_errors)
16. **pea_breaks_fsm** - PEA 并联弹性破坏 FSM (V15.0)
17. **sea_pratt_loop_conflict** - SEA Pratt 内环冲突 (V15.2)

## 常见场景速查

### 场景 1: 仿真出现 NaN
**原因**: timestep 过大、初始条件不稳定、接触参数问题
**解决**: 
- 减小 dt: `model.opt.timestep = 0.001`
- 检查初始高度: `data.qpos[hip_y_idx] = 0.95`
- 提高接触刚度: `solimp='0.9 0.95 0.001'`

### 场景 2: 机器人摔倒
**原因**: 髋关节扭矩不足、FSM 未调优、摆臂过重、电机摩擦
**解决**:
- 提高扭矩: `stance_late_tau_max = 4.0`
- 减轻摆臂: `arm_mass = 0.01` (V14c)
- 摩擦补偿: `tau_comp = tau_C * sign_smooth(qd)` (V13.7)

### 场景 3: V16 电机摩擦失败
**原因**: tau_C 在失败带 [0.013, 0.20] N·m
**解决**:
- 应用前馈补偿 (V13.7)
- 选择低摩擦电机 (tau_C < 0.013)

### 场景 4: V14 摆臂导致不稳定
**原因**: arm_mass >= 0.05 kg 与 FSM 耦合
**解决**:
- 减重: `arm_mass = 0.01 kg`
- 使用 V14b FSM 控制

### 场景 5: V15 PEA 失败
**原因**: 并联弹性直接影响关节，破坏 FSM
**解决**:
- 改用 V15.1 SEA 串联拓扑
- 移除 PEA: 设置 `k = 0`

## 集成到仿真脚本

```python
# 在 simulate_*.py 失败时自动诊断
from diagnostics import ErrorDetector, SolutionDatabase

detector = ErrorDetector()
db = SolutionDatabase()

result = run_simulation(...)

if not result["success"]:
    report = detector.analyze_simulation_result(result)
    if report["has_errors"]:
        entry = db.get(report["primary_error"])
        print(f"自动诊断: {entry.error_type}")
        print(f"建议: {entry.solutions[0].action}")
```

## 文件结构

```
diagnostics/
├── __init__.py                  # 包初始化
├── error_detector.py            # 错误检测引擎
├── solution_database.py         # 解决方案知识库
├── diagnostic_wizard.py         # 交互式诊断向导
├── health_checker.py            # 系统健康检查
├── common_issues.yaml           # 常见问题数据库 (17 个)
├── test_diagnostics.py          # 测试套件
├── demo.py                      # 演示脚本
└── README.md                    # 完整文档
```

## 参考资料

- 完整文档: `diagnostics/README.md`
- V15.0 PEA 分析: `.claude/analysis/v15_0_pea_failure_analysis.md`
- V16 电机动力学: `v16_motor_dynamics/README.md`
- V14c 摆臂减重: `v14c_arm_mass_lightening/README.md`
- V13.7 摩擦补偿: `v13_7_friction_compensation/README.md`
- Common 库: `common/README.md`

## 扩展知识库

编辑 `common_issues.yaml` 添加新错误:

```yaml
simulation_errors:
  - error_type: "new_error"
    symptoms: ["symptom 1", "symptom 2"]
    causes: ["cause 1"]
    solutions:
      - action: "Solution"
        details: "Details"
        code: "code_example()"
    references: ["docs"]
    severity: "high"
```

---

版本: v1.0.0 | 更新: 2026-06-04

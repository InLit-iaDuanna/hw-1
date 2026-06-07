# hw-1 智能错误诊断系统

自动检测、分类和诊断 hw-1 项目常见问题，提供解决方案推荐。

## 功能特性

- **错误检测**: 自动分析日志、JSON 输出、时间序列数据，识别常见错误模式
- **解决方案知识库**: 收录 15+ 常见问题及验证过的解决方案
- **交互式诊断向导**: 引导用户逐步定位问题
- **系统健康检查**: 验证环境配置、依赖包、项目结构

## 快速开始

### 1. 交互式诊断向导

最简单的使用方式，适合不确定问题根因的情况：

```bash
cd D:\Dunna\Documents\hw-1
python -m diagnostics.diagnostic_wizard
```

按提示选择诊断模式：
- **自动诊断**: 分析仿真输出 JSON 文件
- **交互式诊断**: 回答问题逐步定位
- **搜索知识库**: 按关键词搜索已知问题
- **分析文件**: 检查特定日志或数据文件

### 2. 系统健康检查

检查环境配置是否正确：

```bash
python -m diagnostics.health_checker
```

运行完整检查（包含 smoke test）：

```bash
python -m diagnostics.health_checker --smoke-test --duration 2.0
```

导出健康检查报告：

```bash
python -m diagnostics.health_checker --export health_report.json
```

### 3. Python API 使用

#### 检测错误

```python
from diagnostics import ErrorDetector

detector = ErrorDetector()

# 从 JSON 文件检测
errors = detector.detect_from_json("v10/out/result.json")
for error_type, severity in errors:
    print(f"{error_type} (严重性: {severity})")

# 从时间序列数据检测
import numpy as np
qpos = np.load("qpos_data.npy")
errors = detector.detect_from_timeseries(qpos=qpos)
```

#### 查询解决方案

```python
from diagnostics import SolutionDatabase

db = SolutionDatabase()

# 获取特定错误的解决方案
entry = db.get("simulation_nan")
print(entry.format())

# 搜索关键词
results = db.search("fall")
for entry in results:
    print(f"- {entry.error_type}")
    for solution in entry.solutions[:2]:
        print(f"  方案: {solution.action}")
```

#### 综合分析

```python
from diagnostics import ErrorDetector, SolutionDatabase

detector = ErrorDetector()
db = SolutionDatabase()

# 分析仿真结果
result = {
    "success": False,
    "failure": "fall_down",
    "forward": 0.5,
    "alternation_count": 2
}

report = detector.analyze_simulation_result(result)

if report["has_errors"]:
    print(f"检测到 {report['error_count']} 个错误")
    
    # 获取解决方案
    for error_info in report["errors"]:
        error_type = error_info["type"]
        entry = db.get(error_type)
        
        if entry:
            print(f"\n[{error_type}]")
            for i, sol in enumerate(entry.solutions[:2], 1):
                print(f"  方案 {i}: {sol.action}")
                print(f"         {sol.details}")
```

## 知识库内容

### 仿真错误 (simulation_errors)

1. **simulation_nan**: NaN / 数值积分错误
   - 原因: timestep 过大、初始条件不稳定、接触参数问题
   - 解决: 减小 dt、检查初始高度、提高接触刚度

2. **fall_down**: 机器人摔倒
   - 原因: 髋关节扭矩不足、FSM 参数未调优、摆臂过重、电机摩擦在失败带
   - 解决: 提高 stance_late_tau_max、减轻摆臂、应用摩擦补偿 (V13.7)

3. **fly_away**: 机器人飞走 / 爆炸
   - 原因: 穿透导致爆炸性接触力、swing thrust 过大
   - 解决: 修复接触穿透、降低 swing_thrust_tau_max

4. **penetration**: 穿透地面
   - 原因: 接触刚度过低、timestep 过大
   - 解决: 提高 solimp 参数、减小 dt

5. **no_alternation**: 无法交替步态
   - 原因: swing retraction 时序错误、膝关节锁死、swing thrust 不足
   - 解决: 提高 swing_thrust_k_E、检查膝关节自由度、验证 FSM 相位切换

### 参数错误 (parameter_errors)

6. **invalid_timestep**: 无效时间步长
7. **invalid_initial_height**: 初始高度错误
8. **motor_friction_failure_band**: 电机摩擦在失败带 [0.013, 0.20] N·m (V16)
9. **arm_mass_too_heavy**: 摆臂质量过重 (>= 0.05 kg, V14)

### 环境错误 (environment_errors)

10. **mujoco_not_found**: MuJoCo 未安装
11. **model_file_not_found**: 模型文件不存在
12. **common_import_error**: common 库导入失败

### 数据错误 (data_errors)

13. **csv_corrupted**: CSV 文件损坏
14. **json_schema_mismatch**: JSON 格式不匹配

### 性能错误 (performance_errors)

15. **simulation_too_slow**: 仿真速度过慢

### 拓扑错误 (topology_errors)

16. **pea_breaks_fsm**: PEA 并联弹性破坏 FSM (V15.0)
17. **sea_pratt_loop_conflict**: SEA Pratt 内环与 FSM 冲突 (V15.2)

## 常见使用场景

### 场景 1: 仿真出现 NaN

```bash
# 自动诊断
python -m diagnostics.diagnostic_wizard
# 选择 "1. 自动诊断"
# 输入结果文件路径: v10/out/v10_result.json
```

诊断系统会：
1. 检测到 `simulation_nan` 错误
2. 列出 4 个可能原因
3. 提供 4 个解决方案（减小 dt、检查初始高度、提高接触刚度、限制控制扭矩）
4. 显示参考文档位置

### 场景 2: V14 摆臂导致摔倒

```python
from diagnostics import SolutionDatabase

db = SolutionDatabase()
entry = db.get("arm_mass_too_heavy")

print(entry.format())
# 输出:
#   可能原因:
#     - arm inertia couples with hip FSM
#     - control law not designed for arm dynamics
#   
#   解决方案:
#     方案 1: Reduce arm mass
#       详情: 降至 0.01 kg 或更轻
#       代码: <inertial mass='0.01' .../>
```

### 场景 3: V16 电机摩擦失败

诊断系统会识别出 `motor_friction_failure_band` 并推荐：
- **方案 1**: 应用前馈摩擦补偿 (V13.7)
- **方案 2**: 选择 tau_C < 0.013 或 >= 0.27 的电机

### 场景 4: 新环境配置检查

```bash
# 运行健康检查
python -m diagnostics.health_checker --smoke-test

# 输出:
# ======================================================================
# hw-1 系统健康检查
# ======================================================================
# 
# ✓ Python 版本: 当前版本: 3.11, 最低要求: 3.10
# ✓ 包: mujoco: 已安装
# ✓ 包: numpy: 已安装
# ✓ 目录: common/: 存在
# ✓ 模块: common/model_loader.py: 存在
# ...
# 
# ======================================================================
# Smoke Test
# ======================================================================
# 运行仿真: duration=1.0s, dt=0.002, steps=500
# ✓ 仿真成功完成 500 步
```

## 目录结构

```
diagnostics/
├── __init__.py                  # 包初始化
├── error_detector.py            # 错误检测引擎
├── solution_database.py         # 解决方案知识库
├── diagnostic_wizard.py         # 交互式诊断向导
├── health_checker.py            # 系统健康检查
├── common_issues.yaml           # 常见问题数据库 (15+ 问题)
└── README.md                    # 本文件
```

## 与现有工具集成

### 集成到仿真脚本

在仿真脚本失败时自动调用诊断：

```python
# 在 simulate_*.py 中
from diagnostics import ErrorDetector, SolutionDatabase

detector = ErrorDetector()
db = SolutionDatabase()

# 仿真运行
result = run_simulation(...)

if not result["success"]:
    # 自动诊断
    report = detector.analyze_simulation_result(result)
    
    if report["has_errors"]:
        print(f"\n自动诊断: 检测到 {report['primary_error']}")
        
        # 显示解决方案
        entry = db.get(report["primary_error"])
        if entry and entry.solutions:
            print(f"建议尝试: {entry.solutions[0].action}")
            print(f"详情: {entry.solutions[0].details}")
```

### 集成到 CI 流程

在 CI 中运行健康检查：

```yaml
# .github/workflows/ci.yml
- name: Health Check
  run: |
    python -m diagnostics.health_checker --smoke-test --export health_report.json
  
- name: Upload Health Report
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: health-report
    path: health_report.json
```

## 扩展知识库

### 添加新的错误类型

编辑 `common_issues.yaml`：

```yaml
simulation_errors:
  - error_type: "new_error_type"
    symptoms:
      - "symptom description 1"
      - "symptom description 2"
    causes:
      - "possible cause 1"
      - "possible cause 2"
    solutions:
      - action: "Solution action"
        details: "Detailed description"
        code: "example_code()"
    references:
      - "Documentation reference"
    severity: "high"
```

重新加载知识库即可立即使用。

### 添加新的错误检测签名

编辑 `error_detector.py`：

```python
ERROR_SIGNATURES.append(
    ErrorSignature(
        "new_error_type",
        patterns=[
            r"pattern1",
            r"pattern2"
        ],
        data_checks=[
            ("field_name", lambda x: x > threshold)
        ],
        severity="high"
    )
)
```

## 已知限制

1. **错误检测基于模式匹配**: 无法识别所有边界情况，特别是复杂的多因素耦合问题
2. **解决方案通用性**: 某些解决方案需要根据具体版本调整参数
3. **自动修复**: 当前版本不支持自动应用修复（需要手动修改代码）

## 贡献指南

如发现新的常见问题或改进建议：

1. 记录错误症状、根因、解决方案
2. 添加到 `common_issues.yaml`
3. 在至少 2 个版本中验证解决方案有效
4. 更新文档和测试用例

## 参考资料

- **V15.0 PEA failure analysis**: `.claude/analysis/v15_0_pea_failure_analysis.md`
- **V16 motor dynamics**: `v16_motor_dynamics/README.md`
- **V14c arm mass reduction**: `v14c_arm_mass_lightening/README.md`
- **V13.7 friction compensation**: `v13_7_friction_compensation/README.md`
- **Common library**: `common/README.md`

## 版本历史

- **v1.0.0** (2026-06-04): 初始发布
  - 错误检测引擎
  - 15+ 常见问题知识库
  - 交互式诊断向导
  - 系统健康检查

## License

与 hw-1 项目相同。

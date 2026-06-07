# Tutorial 05：开发者贡献指南

**目标：** 30 分钟内学会如何扩展项目、添加新版本、贡献代码

**难度：** ⭐⭐⭐ 高级

**前置要求：** 完成 Tutorial 01-02，熟悉 Python 和 MuJoCo

**适合人群：** 开发者、想要扩展项目的研究者

---

## 学习目标

完成本教程后，你将能够：

- ✅ 创建新版本目录和文件
- ✅ 编写符合项目规范的代码
- ✅ 添加单元测试
- ✅ 更新文档和 Dashboard
- ✅ 提交代码并创建 PR

---

## 第 1 步：创建新版本骨架（5 分钟）

### 1.1 确定版本号

**版本命名规则：**
- 主版本：V01-V25（两位数字）
- 子版本：V13.6, V13.7（小数点）
- 分析版本：V13b（字母后缀）

**示例场景：** 假设我们要创建 V26，添加柔顺控制（Compliance Control）

**版本号：** `v26_compliance_control`

---

### 1.2 创建目录结构

```powershell
# 创建版本目录
mkdir v26_compliance_control
cd v26_compliance_control

# 创建标准文件
New-Item -ItemType File README.md
New-Item -ItemType File model_v26.xml
New-Item -ItemType File simulate_v26.py
New-Item -ItemType File control_v26.py
New-Item -ItemType File view_v26.py
New-Item -ItemType Directory out
New-Item -ItemType Directory tests
```

**最终结构：**

```
v26_compliance_control/
├── README.md
├── model_v26.xml
├── simulate_v26.py
├── control_v26.py
├── view_v26.py
├── out/
└── tests/
    └── test_v26.py
```

---

### 1.3 从模板复制

```powershell
# 复制 V17 作为模板（最完整版本）
cp ..\v17_refactored\README_template.md README.md
cp ..\v17_refactored\model_v17.xml model_v26.xml
cp ..\v17_refactored\simulate_v17.py simulate_v26.py
cp ..\v17_refactored\control_v17.py control_v26.py
```

---

## 第 2 步：编写控制律（10 分钟）

### 2.1 定义控制律接口

**位置：** `control_v26.py`

```python
"""
V26 Compliance Control Law

Adds impedance control on top of V13.7 FSM baseline.
"""

import numpy as np
from typing import Dict, Tuple

def control_v26(
    hip_angle: float,
    hip_velocity: float,
    left_foot_contact: int,
    right_foot_contact: int,
    phase: int,
    params: Dict
) -> Tuple[float, int]:
    """
    V26 Compliance control law.
    
    Args:
        hip_angle: Hip joint angle (rad)
        hip_velocity: Hip joint velocity (rad/s)
        left_foot_contact: Left foot contact state (0/1)
        right_foot_contact: Right foot contact state (0/1)
        phase: Current FSM phase (0-3)
        params: Parameter dictionary
    
    Returns:
        tau_desired: Desired hip torque (N·m)
        new_phase: Updated FSM phase
    """
    # 1. FSM 基础控制律（继承 V13.7）
    tau_fsm, new_phase = _fsm_control(
        hip_angle, hip_velocity, left_foot_contact, phase, params
    )
    
    # 2. 柔顺性调整（新增）
    tau_compliance = _compliance_adjustment(
        hip_angle, hip_velocity, params
    )
    
    # 3. 组合
    tau_desired = tau_fsm + tau_compliance
    
    # 4. 摩擦补偿（继承 V13.7）
    if params.get('compensate_friction', False):
        tau_comp = params['tau_C'] * _sign_smooth(hip_velocity)
        tau_desired += tau_comp
    
    # 5. 饱和限制
    tau_sat = params.get('tau_sat', 10.0)
    tau_desired = np.clip(tau_desired, -tau_sat, tau_sat)
    
    return tau_desired, new_phase


def _fsm_control(hip_angle, hip_velocity, left_foot_contact, phase, params):
    """FSM 基础控制律（继承 V13.6）"""
    # 状态转换
    new_phase = _update_phase(phase, hip_angle, left_foot_contact, params)
    
    # 查表获取目标力矩
    tau_table = [
        params['tau_0'],  # Phase 0
        params['tau_1'],  # Phase 1
        params['tau_2'],  # Phase 2
        params['tau_3'],  # Phase 3
    ]
    tau_fsm = tau_table[new_phase]
    
    return tau_fsm, new_phase


def _compliance_adjustment(hip_angle, hip_velocity, params):
    """
    柔顺性调整（新增核心功能）
    
    实现阻抗控制：τ_c = K_v * (v_desired - v_actual)
    """
    # 虚拟阻尼
    K_v = params.get('compliance_damping', 0.5)  # N·m·s/rad
    
    # 期望速度（根据当前角度动态调整）
    v_desired = _compute_desired_velocity(hip_angle, params)
    
    # 阻抗力矩
    tau_compliance = K_v * (v_desired - hip_velocity)
    
    return tau_compliance


def _compute_desired_velocity(hip_angle, params):
    """根据当前角度计算期望速度（简化模型）"""
    # 简化为线性模型
    v_nominal = params.get('nominal_velocity', 1.0)  # rad/s
    k_angle = params.get('angle_feedback_gain', 0.1)
    
    v_desired = v_nominal - k_angle * hip_angle
    return v_desired


def _update_phase(phase, hip_angle, left_foot_contact, params):
    """Phase 转换逻辑（继承 V13.6）"""
    if phase == 0:
        if hip_angle > params['theta_01']:
            return 1
    elif phase == 1:
        if left_foot_contact == 0:
            return 2
    elif phase == 2:
        if hip_angle < params['theta_23']:
            return 3
    elif phase == 3:
        if left_foot_contact == 1:
            return 0
    return phase


def _sign_smooth(x, epsilon=0.01):
    """平滑 sign 函数（继承 V13.7）"""
    return np.tanh(x / epsilon)
```

---

### 2.2 编写仿真脚本

**位置：** `simulate_v26.py`

```python
"""
V26 Compliance Control Simulation
"""

import mujoco
import numpy as np
import argparse
import json
from pathlib import Path
from control_v26 import control_v26

def run_simulation(duration=12.0, save_prefix='v26'):
    """运行 V26 仿真"""
    # 1. 加载模型
    model_path = Path(__file__).parent / 'model_v26.xml'
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    
    # 2. 参数配置
    params = {
        'tau_0': 3.5,
        'tau_1': 4.0,
        'tau_2': -2.5,
        'tau_3': 1.5,
        'theta_01': 0.05,
        'theta_23': -0.1,
        'tau_C': 0.20,
        'compensate_friction': True,
        'tau_sat': 10.0,
        # V26 新增参数
        'compliance_damping': 0.5,
        'nominal_velocity': 1.0,
        'angle_feedback_gain': 0.1,
    }
    
    # 3. 初始化
    phase = 0
    trajectory = []
    
    # 4. 仿真循环
    n_steps = int(duration / model.opt.timestep)
    for step in range(n_steps):
        # 读取传感器
        hip_angle = data.qpos[0]
        hip_velocity = data.qvel[0]
        left_foot_contact = int(data.contact[0].dist < 0.001)
        right_foot_contact = int(data.contact[1].dist < 0.001)
        
        # 控制律
        tau, phase = control_v26(
            hip_angle, hip_velocity, 
            left_foot_contact, right_foot_contact,
            phase, params
        )
        
        # 施加控制
        data.ctrl[0] = tau
        
        # 仿真步进
        mujoco.mj_step(model, data)
        
        # 记录轨迹
        if step % 10 == 0:
            trajectory.append({
                'time': data.time,
                'hip_x': data.qpos[1],
                'hip_angle': hip_angle,
                'hip_velocity': hip_velocity,
                'hip_torque': tau,
                'phase': phase,
            })
    
    # 5. 保存结果
    output_dir = Path(__file__).parent / 'out'
    output_dir.mkdir(exist_ok=True)
    
    # 保存轨迹
    import pandas as pd
    df = pd.DataFrame(trajectory)
    df.to_csv(output_dir / f'{save_prefix}_trajectory.csv', index=False)
    
    # 保存摘要
    summary = {
        'success': df['hip_x'].iloc[-1] > 4.0,
        'forward_distance': df['hip_x'].iloc[-1],
        'sim_duration': duration,
    }
    with open(output_dir / f'{save_prefix}_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Simulation complete: forward={summary['forward_distance']:.2f}m")
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=12.0)
    parser.add_argument('--save-prefix', type=str, default='v26')
    args = parser.parse_args()
    
    run_simulation(args.duration, args.save_prefix)
```

---

## 第 3 步：添加测试（5 分钟）

### 3.1 编写单元测试

**位置：** `tests/test_v26.py`

```python
"""
Unit tests for V26 Compliance Control
"""

import pytest
import numpy as np
from control_v26 import control_v26, _compliance_adjustment

def test_control_v26_basic():
    """测试基础控制律调用"""
    params = {
        'tau_0': 3.5, 'tau_1': 4.0, 'tau_2': -2.5, 'tau_3': 1.5,
        'theta_01': 0.05, 'theta_23': -0.1,
        'tau_C': 0.20, 'compensate_friction': True,
        'compliance_damping': 0.5,
        'nominal_velocity': 1.0,
        'angle_feedback_gain': 0.1,
    }
    
    tau, phase = control_v26(
        hip_angle=0.0,
        hip_velocity=0.5,
        left_foot_contact=1,
        right_foot_contact=0,
        phase=0,
        params=params
    )
    
    assert isinstance(tau, (float, np.floating))
    assert phase in [0, 1, 2, 3]
    assert -10.0 <= tau <= 10.0  # 饱和限制


def test_compliance_adjustment():
    """测试柔顺性调整"""
    params = {
        'compliance_damping': 0.5,
        'nominal_velocity': 1.0,
        'angle_feedback_gain': 0.1,
    }
    
    tau_c = _compliance_adjustment(
        hip_angle=0.1,
        hip_velocity=0.8,
        params=params
    )
    
    # 期望速度：1.0 - 0.1 * 0.1 = 0.99
    # 阻抗力矩：0.5 * (0.99 - 0.8) = 0.095
    assert abs(tau_c - 0.095) < 0.01


def test_phase_transitions():
    """测试 phase 转换"""
    params = {
        'tau_0': 3.5, 'tau_1': 4.0, 'tau_2': -2.5, 'tau_3': 1.5,
        'theta_01': 0.05, 'theta_23': -0.1,
        'tau_C': 0.20, 'compensate_friction': False,
        'compliance_damping': 0.5,
    }
    
    # Phase 0 → 1 (hip_angle > theta_01)
    _, phase = control_v26(0.06, 0.5, 1, 0, 0, params)
    assert phase == 1
    
    # Phase 2 → 3 (hip_angle < theta_23)
    _, phase = control_v26(-0.15, 0.5, 0, 1, 2, params)
    assert phase == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

### 3.2 运行测试

```powershell
# 安装 pytest（如果未安装）
pip install pytest

# 运行测试
cd v26_compliance_control
pytest tests/test_v26.py -v
```

**预期输出：**

```
tests/test_v26.py::test_control_v26_basic PASSED
tests/test_v26.py::test_compliance_adjustment PASSED
tests/test_v26.py::test_phase_transitions PASSED

=============== 3 passed in 0.12s ===============
```

---

## 第 4 步：更新文档（5 分钟）

### 4.1 编写 README.md

**位置：** `v26_compliance_control/README.md`

```markdown
# V26: Compliance Control

## 版本定位（1 句话）

在 V13.7 FSM + 摩擦补偿基础上，添加阻抗控制提供柔顺性。

## 关键创新

- **阻抗控制**：虚拟阻尼器吸收冲击，提高交互安全性
- **自适应速度调节**：根据髋角度动态调整期望速度
- **向后兼容**：保留 V13.7 的 FSM 和摩擦补偿

## 技术路线

```
V13.7 (FSM + Friction Comp)
   ↓
V26 (+ Compliance Control)
```

## 运行方法

```powershell
cd v26_compliance_control

# 运行仿真
python simulate_v26.py --duration 12.0

# 可视化
python view_v26.py
```

## 成功判据

- Forward distance > 4.0 m
- Alternations ≥ 10
- 无跌倒或卡住

## 关键结果

| 指标 | V13.7 | V26 | 改进 |
|------|-------|-----|------|
| Forward (m) | 4.63 | 4.58 | -1.1% |
| CoT | 0.066 | 0.068 | +3.0% |
| 交互力峰值 (N) | 45.2 | 32.1 | -29.0% ⭐ |

**关键发现：**
- 柔顺性略微降低能效（+3% CoT）
- 显著降低交互力峰值（-29%）→ 提高安全性
- 权衡：性能 vs 安全性

## 已知问题

- 柔顺性参数（K_v）需要手动调优
- 与 V17 状态估计集成待验证

## 相关资源

- 继承版本：V13.7
- 测试脚本：`tests/test_v26.py`
- 参数文件：内嵌在 `simulate_v26.py`
```

---

### 4.2 更新项目 VERSIONS.md

**位置：** `D:\Dunna\Documents\hw-1\VERSIONS.md`

在文件末尾添加：

```markdown
## V26: Compliance Control

**定位：** 柔顺控制，提高交互安全性

**时间：** 2026-06-05

**技术路线：** V13.7 → V26

**关键创新：**
- 阻抗控制（虚拟阻尼器）
- 自适应速度调节

**关键结果：**
- Forward: 4.58 m
- CoT: 0.068
- 交互力峰值降低 29%

**学术价值：** 探索准被动步态的柔顺性-能效权衡
```

---

## 第 5 步：更新 Dashboard（3 分钟）

### 5.1 编辑 Dashboard 数据

**位置：** `dashboard/data.js`

在 `VERSIONS` 数组中添加：

```javascript
{
  id: 'v26',
  name: 'V26: Compliance Control',
  phase: 'Hardware Path',
  date: '2026-06-05',
  status: 'completed',
  description: '在 V13.7 基础上添加阻抗控制，提高交互安全性',
  metrics: {
    forward: 4.58,
    cot: 0.068,
    alternations: 10,
    successRate: 95.0
  },
  highlights: [
    '交互力峰值降低 29%',
    '虚拟阻尼器吸收冲击',
    '柔顺性-能效权衡分析'
  ],
  dependencies: ['v13_7'],
  tags: ['compliance', 'safety', 'impedance-control']
}
```

---

### 5.2 验证 Dashboard

```powershell
# 打开 Dashboard
start dashboard\index.html

# 检查 V26 卡片是否显示
```

---

## 第 6 步：提交代码（2 分钟）

### 6.1 创建功能分支

```powershell
# 切换到 dev 分支
git checkout dev
git pull origin dev

# 创建功能分支
git checkout -b feature/v26-compliance-control
```

---

### 6.2 提交代码

```powershell
# 添加所有文件
git add v26_compliance_control/
git add dashboard/data.js
git add VERSIONS.md

# 提交（遵循 commit 规范）
git commit -m "feat(v26): add compliance control

Adds impedance control on top of V13.7 FSM baseline.

Key features:
- Virtual damper for compliance
- Adaptive velocity adjustment
- Reduces interaction force peak by 29%

Trade-off: CoT increases by 3% for improved safety.

Closes #123"
```

---

### 6.3 推送并创建 PR

```powershell
# 推送到远程
git push origin feature/v26-compliance-control

# 在 GitHub/GitLab 创建 PR
# Title: feat(v26): add compliance control
# Description: 详细说明变更内容
# Reviewers: 项目维护者
```

---

## 代码规范检查清单

### ✅ 代码质量

- [ ] 遵循 PEP 8 命名规范
- [ ] 所有函数有 docstring
- [ ] 类型注解（Type hints）
- [ ] 无硬编码常量（使用 params 字典）
- [ ] 异常处理（try-except）

---

### ✅ 测试覆盖

- [ ] 单元测试覆盖核心函数
- [ ] 测试 edge cases（边界条件）
- [ ] 测试通过（pytest 无错误）

---

### ✅ 文档完整

- [ ] README.md 包含所有必备章节
- [ ] 代码注释清晰
- [ ] 更新 VERSIONS.md
- [ ] 更新 Dashboard

---

### ✅ 版本控制

- [ ] 使用功能分支开发
- [ ] Commit message 符合规范
- [ ] 提交前运行测试
- [ ] PR 描述清晰

---

## 常见问题

### Q1: 如何选择基础版本？

**推荐：**
- 开发新控制律 → 从 V13.7 开始
- 添加传感器 → 从 V17 开始
- 机械结构改进 → 从 V14b 开始

---

### Q2: 如何处理依赖？

**原则：** 最小化依赖，复用 common 模块

```python
# 推荐
from common.analysis import compute_cot
from common.visualization import plot_trajectory

# 避免
import v10.control_v10  # 跨版本依赖
```

---

### Q3: 什么时候需要创建子版本（如 V26.1）？

**场景：**
- 修复 V26 的 bug → V26.1
- 小幅改进（如参数调优）→ V26.2
- 分析性扩展 → V26b

**主版本：** 新功能、新技术路线 → V27

---

## 高级主题

### 主题 1: 添加 CLI 参数

```python
# simulate_v26.py
parser.add_argument('--compliance-damping', type=float, default=0.5)
parser.add_argument('--no-compliance', action='store_true')
args = parser.parse_args()

params['compliance_damping'] = args.compliance_damping
if args.no_compliance:
    params['compliance_damping'] = 0.0
```

---

### 主题 2: 集成 CI/CD

**位置：** `ci/test_v26.yaml`

```yaml
name: Test V26
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run V26 tests
        run: pytest v26_compliance_control/tests/ -v
      - name: Run V26 simulation
        run: python v26_compliance_control/simulate_v26.py --duration 6.0
```

---

### 主题 3: 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

run_simulation(duration=12.0)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(10)
```

---

## 相关资源

- **代码规范**: `knowledge_base/best_practices/coding_standards.md`
- **版本控制规范**: `knowledge_base/best_practices/version_control.md`
- **项目 ROADMAP**: `ROADMAP.md`
- **项目 CLAUDE.md**: 协作约定

---

**最后更新**: 2026-06-05

**下一步**: 查看 Tutorial 06（交互式 Jupyter Notebook）或贡献你的第一个 PR！

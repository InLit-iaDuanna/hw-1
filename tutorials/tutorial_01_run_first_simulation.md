# Tutorial 01：运行第一个仿真

**目标：** 15 分钟内运行 V13.7 仿真并理解输出结果。

**难度：** ⭐ 入门

**前置要求：** 无

---

## 学习目标

完成本教程后，你将能够：

- ✅ 激活项目虚拟环境
- ✅ 运行完整的步态仿真
- ✅ 理解输出文件（CSV 和 JSON）
- ✅ 查看可视化动画
- ✅ 判断仿真成功或失败

---

## 第 1 步：激活虚拟环境（2 分钟）

打开 PowerShell，进入项目目录：

```powershell
# 进入项目根目录
cd D:\Dunna\Documents\hw-1

# 激活虚拟环境
.\.venv-mujoco\Scripts\activate

# 你应该看到命令提示符前面出现 (.venv-mujoco)
```

**验证环境：**

```powershell
# 检查 Python 版本
python --version
# 应该显示：Python 3.x.x

# 检查 MuJoCo 安装
python -c "import mujoco; print('MuJoCo version:', mujoco.__version__)"
# 应该显示：MuJoCo version: 3.x.x
```

**如果出错：** 查看 QUICKSTART.md 的"常见问题排查"部分。

---

## 第 2 步：运行 V13.7 仿真（5 分钟）

**为什么选 V13.7？**

V13.7 是项目中最成熟的版本：
- 包含完整控制链（FSM + 电机动力学 + 摩擦补偿）
- 代码清晰、注释完整
- 性能稳定（是 V22 硬件设计的基础）

**运行仿真：**

```powershell
# 运行 12 秒仿真（默认参数）
python v13_7_friction_compensation\simulate_v13_7.py --duration 12.0
```

**你会看到：**

```
=== V13.7 Simulation: mx64ar_full with compensation ===
Running 12.0s simulation...
Progress: [████████████████████████████████] 100%

✓ Simulation completed successfully!
  Forward distance: 4.63 m
  Alternations: 10
  CoT_mech: 0.066
  Max hip torque: 3.91 N·m

Saved results:
  - v13_7_friction_compensation\out\v137_mx64ar_full_compensation_trajectory.csv
  - v13_7_friction_compensation\out\v137_mx64ar_full_compensation_summary.json
```

**仿真过程：**
- 初始化：机器人站立在斜坡上
- 0-2s：初始步态建立
- 2-10s：稳定行走
- 10-12s：结束

**成功判据：**
- ✅ Forward distance > 4.0 m
- ✅ Alternations ≥ 10（左右脚交替至少 10 次）
- ✅ 无跌倒或卡住

---

## 第 3 步：查看输出文件（3 分钟）

### 3.1 查看 JSON 摘要

```powershell
# 打开 JSON 文件（可用记事本或 VS Code）
notepad v13_7_friction_compensation\out\v137_mx64ar_full_compensation_summary.json
```

**关键字段：**

```json
{
  "success": true,                    // 仿真是否成功
  "forward_distance": 4.63,           // 前进距离 (m)
  "alternating_touchdowns": 10,       // 交替触地次数
  "active_input_energy_j": 16.83,     // 主动输入能量 (J)
  "coulomb_dissipation_j": 4.43,      // 摩擦耗散 (J)
  "cot_mechanical": 0.066,            // 机械能量传输成本
  "max_hip_torque": 3.91,             // 最大髋关节力矩 (N·m)
  "sim_duration": 12.0                // 仿真时长 (s)
}
```

**理解 CoT（Cost of Transport）：**

CoT = 能量输入 / (质量 × 重力 × 距离)

- V13.7: CoT = 0.066（优秀）
- 人类步行: CoT ≈ 0.05
- 典型双足机器人: CoT ≈ 0.5-2.0

---

### 3.2 查看 CSV 轨迹

```powershell
# 用 Excel 或文本编辑器打开
notepad v13_7_friction_compensation\out\v137_mx64ar_full_compensation_trajectory.csv
```

**列说明：**

| 列名 | 含义 | 单位 |
|------|------|------|
| `time` | 仿真时间 | s |
| `hip_x` | 髋部 X 位置 | m |
| `hip_z` | 髋部 Z 位置 | m |
| `hip_angle` | 髋关节角度 | rad |
| `left_knee` | 左膝关节角度 | rad |
| `right_knee` | 右膝关节角度 | rad |
| `left_foot_contact` | 左脚接触状态 | 0/1 |
| `right_foot_contact` | 右脚接触状态 | 0/1 |
| `hip_torque` | 髋关节力矩 | N·m |
| `phase` | FSM 状态 | 0-3 |

**用 Python 快速绘图：**

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('v13_7_friction_compensation/out/v137_mx64ar_full_compensation_trajectory.csv')

# 绘制髋部轨迹
plt.figure(figsize=(10, 4))
plt.plot(df['time'], df['hip_x'], label='Hip X')
plt.xlabel('Time (s)')
plt.ylabel('Position (m)')
plt.title('Hip Position over Time')
plt.legend()
plt.grid(True)
plt.show()
```

---

## 第 4 步：可视化动画（3 分钟）

### 4.1 实时查看（需要 OpenGL）

```powershell
# 启动 MuJoCo viewer
python v13_7_friction_compensation\view_v13_7.py
```

**操作提示：**
- 鼠标左键拖动：旋转视角
- 鼠标右键拖动：平移视角
- 鼠标滚轮：缩放
- 空格键：暂停/播放
- ESC：退出

**观察要点：**
1. **脚跟-足底-脚趾滚动**：注意足部的滚动接触
2. **髋关节力矩**：观察髋部的主动驱动
3. **膝关节被动**：膝盖仅靠弹簧约束，无主动驱动
4. **周期性步态**：每一步的运动应该基本一致

---

### 4.2 渲染视频（如果实时查看不可用）

```powershell
# 渲染为 MP4 视频
python v13_7_friction_compensation\render_v13_7.py

# 视频保存在：
# v13_7_friction_compensation\out\v137_walk.mp4
```

用任何视频播放器打开查看。

---

## 第 5 步：理解失败案例（2 分钟）

尝试运行**不带摩擦补偿**的版本：

```powershell
# 禁用摩擦补偿
python v13_7_friction_compensation\simulate_v13_7.py --no-compensation
```

**预期结果：**

```
✗ Simulation FAILED!
  Forward distance: 0.19 m
  Alternations: 4
  Failure reason: fall_down

The robot fell due to motor friction breaking FSM timing.
```

**为什么会失败？**

1. **电机库仑摩擦 τ_C**：电机在换向时有静态摩擦
2. **FSM 时序敏感**：V13.6 的 4 phase FSM 依赖精确的力矩输出
3. **共振耦合**：τ_C = 0.20 N·m（MX-64AR spec）落入"失败带"

**解决方案：**

V13.7 通过前馈补偿 `τ_comp = τ_C × sign(ω)` 对消摩擦，恢复稳定。

---

## 练习任务

### 任务 1：修改仿真时长

```powershell
# 运行 24 秒仿真（更长）
python v13_7_friction_compensation\simulate_v13_7.py --duration 24.0
```

**问题：**
- Alternations 是多少？（应该是 20）
- Forward distance 是多少？（应该约为 9.2 m）

---

### 任务 2：对比不同电机

```powershell
# 使用 EC-i40 电机（更低摩擦）
python v13_7_friction_compensation\simulate_v13_7.py --motor ec_i40
```

**问题：**
- EC-i40 的 CoT 是多少？
- 与 MX-64AR 相比性能如何？

---

### 任务 3：查看 Dashboard

```powershell
# 打开 Dashboard
start dashboard\index.html
```

**操作：**
1. 找到 V13.7 卡片
2. 点击卡片查看详情面板
3. 切换到 Compare View，对比 V13.6 vs V13.7

**问题：**
- V13.6 没有摩擦补偿时的成功率是多少？
- V13.7 补偿后性能提升了多少？

---

## 故障排查

### 问题 1：找不到模块

**错误：** `ModuleNotFoundError: No module named 'mujoco'`

**解决：**
```powershell
# 确认虚拟环境激活
.\.venv-mujoco\Scripts\activate

# 重新安装依赖
pip install -r requirements.txt
```

---

### 问题 2：仿真立即崩溃

**错误：** `mujoco.FatalError: XML parsing error`

**原因：** 模型文件损坏或路径错误

**解决：**
```powershell
# 检查模型文件是否存在
ls v13_7_friction_compensation\model_v13_7.xml

# 如果文件丢失，从 Git 恢复
git checkout v13_7_friction_compensation\model_v13_7.xml
```

---

### 问题 3：Viewer 无法打开

**错误：** 黑屏或窗口立即关闭

**解决：**
1. 更新显卡驱动
2. 或使用渲染脚本生成视频：
   ```powershell
   python v13_7_friction_compensation\render_v13_7.py
   ```

---

## 小结

恭喜！你已经完成了第一个教程。你现在能够：

- ✅ 运行 V13.7 仿真
- ✅ 理解输出文件格式
- ✅ 查看可视化动画
- ✅ 判断仿真成功或失败
- ✅ 理解摩擦补偿的作用

---

## 下一步

继续学习：

- **Tutorial 02**：理解 FSM 控制律（深入了解 4 phase 状态机）
- **Tutorial 03**：参数调优（学习如何调整参数）

或者：

- 查看 **QUICKSTART.md** 中的"学习路径建议"
- 打开 **Dashboard** 浏览所有版本
- 阅读 **v13_7_friction_compensation/README.md** 了解技术细节

---

**有问题？** 查看 QUICKSTART.md 的"常见问题排查"部分。

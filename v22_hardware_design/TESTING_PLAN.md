# V22 硬件测试计划（Testing Plan）

**版本**: v1.0
**日期**: 2026-06-05
**适用于**: 2D 矢状面准被动行走机器人 hw-1
**配套文档**: HARDWARE_SPEC.md / MANUFACTURING_GUIDE.md / SIMULATION_MAPPING.md

> 本测试计划定义从硬件首次上电到完成 V25 验收行走的全流程测试方案，
> 采用分阶段递进策略，确保每阶段失败可定位、可回退、可改进。

---

## 0. 测试理念与原则

### 0.1 三大原则

```
┌────────────────────────────────────────────────────────┐
│ 原则 1: 安全优先（Safety First）                        │
│   人在环测试至 V25 完成；急停始终 <0.5 s 可达           │
│                                                          │
│ 原则 2: 渐进验证（Incremental Validation）              │
│   一次只验证一个变量；前阶段通过后才进入下一阶段          │
│                                                          │
│ 原则 3: 数据闭环（Data Loop）                           │
│   每次测试记录数据，每周与仿真比对，发现偏差立即归因      │
└────────────────────────────────────────────────────────┘
```

### 0.2 测试阶段一览

| 阶段 | 名称 | 周期 | 关键验收 |
|------|------|------|----------|
| T0 | 装配后静态检查 | 1 天 | 所有连接紧固、关节顺滑 |
| T1 | 首次上电 | 0.5 天 | 4 电机识别、电压/电流正常 |
| T2 | 单关节控制 | 1 天 | 位置/速度/扭矩三模式可控 |
| T3 | 单腿协调控制 | 2 天 | 髋膝同步动作，悬空摆动 |
| T4 | 静态站立 | 1 天 | 双腿支撑，重力作用下不倒 |
| T5 | 单步行走 | 3 天 | 一次跨步成功，无跌倒 |
| T6 | 连续步态 | 5 天 | 3 步以上交替触地 |
| T7 | 鲁棒性测试 | 5 天 | 抗扰动、抗电池电压变化 |
| T8 | V25 验收 | 3 天 | 5 m 连续行走 + 视频 |

**总测试周期**: 约 3-4 周（兼职）/ 2 周（全职）

---

## 1. T0 - 装配后静态检查

### 1.1 目标

确认硬件装配质量符合规格，发现任何机械问题（断电状态下）。

### 1.2 检查清单

**机械连接**:

```
关节顺滑度（手动转动，无电机扭矩）
[ ] 左髋: 阻力 < 0.05 N·m
[ ] 左膝: 阻力 < 0.05 N·m + 扭簧回复力
[ ] 左踝: 阻力 < 0.05 N·m + 扭簧回复力
[ ] 右髋: 阻力 < 0.05 N·m
[ ] 右膝: 阻力 < 0.05 N·m + 扭簧回复力
[ ] 右踝: 阻力 < 0.05 N·m + 扭簧回复力

紧固检查（用手晃动）
[ ] 髋部质量块与导轨滑块无松动
[ ] 大腿管与髋 horn 无晃动
[ ] 小腿管与膝 horn 无晃动
[ ] 脚底与踝关节轴无晃动
[ ] 躯干管与髋部无松动

弹簧零位（无外力时位置）
[ ] 膝关节伸直 0° ±2°
[ ] 踝关节中立 0° ±2°

走线检查
[ ] 所有线缆有扎带固定，间距 ≤80 mm
[ ] 关节运动到极限时，线缆不被拉伸
[ ] 接头处无外露金属，绝缘良好
```

**质量与几何**:

```
全机称重（电子秤）
[ ] 总质量 5.0-6.0 kg（含电池）
[ ] 髋部组件 5.4-5.7 kg（>90% 占比）

腿长测量（卷尺）
[ ] 髋轴心到地面 0.99-1.01 m
[ ] 大腿（髋到膝）0.485-0.495 m
[ ] 小腿（膝到踝）0.505-0.515 m

对称性
[ ] 左右腿长偏差 <2 mm
[ ] 双腿张开角度（自然下垂）<2°
```

### 1.3 异常处理

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 关节阻力 >0.1 N·m | 轴承未装正 / 螺丝过紧 | 拆开重装 |
| 总质量偏离 >10% | 配重错装 | 增减铅块 |
| 腿长偏差 >5 mm | 切割误差 | 重新加工或软件补偿 |
| 弹簧零位偏差 >5° | 钩端方向错误 | 重新装扭簧 |

### 1.4 验收标准

**通过 T0**: 所有清单项打勾，无机械问题，可进入 T1 上电。

---

## 2. T1 - 首次上电

### 2.1 安全前置条件

```
[ ] 机器人放置在软垫上（非导轨上）
[ ] 急停按钮已接入回路并测试有效
[ ] 灭火器在身边（LiPo 电池起火风险）
[ ] 戴防护眼镜（首次通电以防异常）
[ ] 工作区域 1 m 内无人
```

### 2.2 上电步骤

**Step 1: 不接电机的控制器测试（5 分钟）**

```bash
# 单独给树莓派供电（USB-C 充电器）
# 验证系统启动、SSH 可达

ssh duanzeqi@hw1-rpi.local
sudo systemctl status
# 检查无服务 failed
```

**Step 2: 接入 LiPo 但保持急停按下（2 分钟）**

```
1. 装入 LiPo 电池（电压检查 11.1-12.6V）
2. 主开关 ON，急停按钮 ON（断开）
3. 此时电机不通电，但 INA219 应显示电池电压
   验证：python3 -c "from board import I2C; ..."
4. 用万用表确认 XT60 端电压（11.1V ±0.2V）
```

**Step 3: 释放急停（电机通电瞬间）**

```
观察 30 秒：
[ ] 4 个电机有自检指示灯（如有）
[ ] 无异响、冒烟、异味
[ ] 无电机突然抽动
[ ] 总电流 <1 A（待机）
```

**Step 4: Dynamixel 通信验证**

```bash
cd ~/hw1
python3 -c "
from dynamixel_sdk import *
PORT = '/dev/ttyUSB0'
BAUD = 1000000
ph = PortHandler(PORT); ph.openPort(); ph.setBaudRate(BAUD)
pa = PacketHandler(2.0)

for dxl_id in [1, 2, 3, 4]:
    model_num, comm, err = pa.ping(ph, dxl_id)
    print(f'ID {dxl_id}: model={model_num}, comm={comm}, err={err}')
"

# 期望输出：
# ID 1: model=311, comm=0, err=0  (左髋)
# ID 2: model=311, comm=0, err=0  (左膝)
# ID 3: model=311, comm=0, err=0  (右髋)
# ID 4: model=311, comm=0, err=0  (右膝)
```

**Step 5: 读取所有电机状态**

```python
# 读取位置、速度、电流、温度、电压
for dxl_id in [1, 2, 3, 4]:
    pos, _, _ = pa.read4ByteTxRx(ph, dxl_id, 132)
    vel, _, _ = pa.read4ByteTxRx(ph, dxl_id, 128)
    cur, _, _ = pa.read2ByteTxRx(ph, dxl_id, 126)
    tmp, _, _ = pa.read1ByteTxRx(ph, dxl_id, 146)
    vol, _, _ = pa.read2ByteTxRx(ph, dxl_id, 144)
    print(f'ID{dxl_id}: pos={pos}, vel={vel}, '
          f'cur={cur*0.00269:.3f}A, '
          f'temp={tmp}°C, '
          f'vol={vol*0.1:.1f}V')

# 期望:
# - 位置在合理范围（不是 0 也不是 ±2147483648）
# - 速度 = 0
# - 电流 = 0 ±5 mA
# - 温度 25-35°C（室温）
# - 电压 11.0-12.5V（与电池一致）
```

### 2.3 验收标准

**通过 T1**:
- 4 个电机全部识别成功
- 状态读取无错误（comm=0, err=0）
- 温度 <40°C，电压稳定
- 无异常物理现象

**失败处理**:

| 现象 | 诊断 | 解决 |
|------|------|------|
| ID 不识别 | 菊花链断 / ID 重复 / 波特率错 | 用 Wizard 单独重设 |
| 电流非零 | 电机有内部故障 | 退货 / 联系售后 |
| 温度高 | 电机内部短路 | 立即断电 |
| 电压跌落 | 电池容量不足 | 换电池或充电 |

---

## 3. T2 - 单关节控制

### 3.1 目标

逐个验证电机的位置、速度、扭矩三种控制模式。

### 3.2 测试矩阵

| 模式 | 关节 | 输入 | 期望响应 | 容许误差 |
|------|------|------|----------|----------|
| 位置 | 左髋 | -45°→+45° | 阶跃响应 <0.3 s | 终值 ±1° |
| 位置 | 左膝 | 0°→+30° | 阶跃响应 <0.3 s | 终值 ±1° |
| 位置 | 右髋 | -45°→+45° | 阶跃响应 <0.3 s | 终值 ±1° |
| 位置 | 右膝 | 0°→+30° | 阶跃响应 <0.3 s | 终值 ±1° |
| 速度 | 左髋 | ω=π rad/s | 稳定速度 | ±0.1 rad/s |
| 速度 | 左膝 | ω=π/2 rad/s | 稳定速度 | ±0.1 rad/s |
| 扭矩 | 左髋 | τ=1 N·m | 静态保持力矩 | 见标定 |
| 扭矩 | 左膝 | τ=1 N·m | 静态保持力矩 | 见标定 |

### 3.3 测试脚本

```python
# tests/T2_single_joint.py
import time
from dynamixel_sdk import *
import numpy as np
import csv

class JointTest:
    def __init__(self, dxl_id):
        self.id = dxl_id
        self.ph = PortHandler('/dev/ttyUSB0')
        self.ph.openPort()
        self.ph.setBaudRate(1000000)
        self.pa = PacketHandler(2.0)

    def test_position_step(self, target_deg, log_file):
        """位置阶跃响应测试"""
        # 设置位置控制模式 (3)
        self.pa.write1ByteTxRx(self.ph, self.id, 11, 3)
        # 启用扭矩
        self.pa.write1ByteTxRx(self.ph, self.id, 64, 1)

        # 转换角度到位置值
        target_raw = int((target_deg + 180) / 360 * 4096)

        with open(log_file, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['t', 'pos_deg', 'vel'])

            t0 = time.perf_counter()
            self.pa.write4ByteTxRx(self.ph, self.id, 116, target_raw)

            for _ in range(2000):
                pos, _, _ = self.pa.read4ByteTxRx(self.ph, self.id, 132)
                vel, _, _ = self.pa.read4ByteTxRx(self.ph, self.id, 128)
                t = time.perf_counter() - t0
                pos_deg = (pos / 4096) * 360 - 180
                w.writerow([t, pos_deg, vel])
                if abs(pos_deg - target_deg) < 1.0 and t > 0.5:
                    break
                time.sleep(0.001)

        # 关闭扭矩
        self.pa.write1ByteTxRx(self.ph, self.id, 64, 0)

    def test_torque_static(self, tau_target):
        """静态扭矩输出测试 - 需配合外部测力计"""
        # 电流模式 (5)
        self.pa.write1ByteTxRx(self.ph, self.id, 11, 5)
        self.pa.write1ByteTxRx(self.ph, self.id, 64, 1)

        current_a = tau_target / 0.058  # Kt = 0.058
        current_raw = int(current_a / 4.5 * 2047)
        self.pa.write2ByteTxRx(self.ph, self.id, 102, current_raw)

        time.sleep(2.0)  # 等用户用测力计读数
        input("按 Enter 关闭扭矩...")
        self.pa.write1ByteTxRx(self.ph, self.id, 64, 0)


if __name__ == '__main__':
    for joint_id in [1, 2, 3, 4]:
        print(f"测试关节 ID {joint_id}")
        t = JointTest(joint_id)
        # 位置阶跃
        t.test_position_step(0, f'logs/T2_id{joint_id}_pos0.csv')
        time.sleep(1)
        t.test_position_step(45 if joint_id in [1,3] else 30,
                              f'logs/T2_id{joint_id}_pos1.csv')
```

### 3.4 数据分析

```python
# analysis/T2_analyze.py
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def analyze(csv_file, target_deg):
    df = pd.read_csv(csv_file)

    # 上升时间（10%-90%）
    pos = df['pos_deg'].values
    initial = pos[0]
    final = pos[-1]
    band = (final - initial) * 0.8
    t10 = df.loc[pos > initial + band*0.125, 't'].iloc[0]
    t90 = df.loc[pos > initial + band, 't'].iloc[0]
    rise_time = t90 - t10

    # 稳态误差
    ss_error = abs(pos[-50:].mean() - target_deg)

    # 超调
    overshoot = max(0, pos.max() - target_deg) / abs(target_deg - initial) * 100

    print(f"上升时间: {rise_time*1000:.1f} ms")
    print(f"稳态误差: {ss_error:.2f}°")
    print(f"超调量: {overshoot:.1f}%")

    plt.plot(df['t'], df['pos_deg'])
    plt.axhline(target_deg, color='r', linestyle='--')
    plt.xlabel('Time (s)'); plt.ylabel('Position (deg)')
    plt.show()
```

### 3.5 验收标准

**通过 T2**:

```
位置控制:
  上升时间 < 0.3 s
  稳态误差 < 1°
  超调 < 10%

速度控制:
  稳态速度误差 < 5%
  无明显震荡

扭矩控制:
  实测扭矩 / 命令扭矩 ∈ [0.85, 1.10]
  （V13.7 摩擦补偿后误差应 <10%）
```

---

## 4. T3 - 单腿协调控制

### 4.1 目标

验证单条腿的多关节同步动作，模拟摆动相位。

### 4.2 测试场景

**Scenario A: 髋膝同步摆动（悬空）**

```python
# 模拟 swing 相位的摆动轨迹
def swing_trajectory(t):
    # 仿照 V13.7 仿真目标
    hip_target = 20 - 42 * (t / 0.4)   # +20° → -22°
    knee_target = 28 * np.sin(np.pi * t / 0.4)  # 0 → 28° → 0
    return hip_target, knee_target

# 持续 0.4 s 的摆动
for t in np.arange(0, 0.4, 0.001):
    hip_t, knee_t = swing_trajectory(t)
    set_position(hip_id=1, deg=hip_t)
    set_position(knee_id=2, deg=knee_t)
    time.sleep(0.001)
```

**Scenario B: 支撑相位姿态保持**

```python
# 大腿垂直、膝微弯，模拟 stance
set_position(hip_id=1, deg=0)
set_position(knee_id=2, deg=2)  # stance_knee_deg

# 在 horn 上施加 100 g 砝码模拟侧向扰动
# 测量位置抖动
```

### 4.3 验收标准

```
[ ] 摆动轨迹跟踪误差 RMS < 3°
[ ] 髋膝相位差与仿真一致（用 cross-correlation）
[ ] 支撑相位下扰动后 0.2 s 内回稳
[ ] 单腿连续摆动 100 次，电机温度 <50°C
```

---

## 5. T4 - 静态站立

### 5.1 目标

双腿支撑下，机器人在重力作用下保持站立姿态。

### 5.2 测试方法

**配置**:

```
- 装入导轨滑块
- 急停按钮处于待用状态
- 髋部用尼龙绳悬挂（保险绳，留 100 mm 余量）
- 软垫铺设在脚下
```

**步骤**:

```
1. 启用所有电机扭矩，目标位置：
   - 左髋 = 0°, 左膝 = 2°
   - 右髋 = 0°, 右膝 = 2°
2. 缓慢释放保险绳张力，让机器人承重
3. 观察 30 秒
4. 记录关节位置漂移
```

**关键观察**:

```
[ ] 关节位置在 5° 以内保持
[ ] 总电流 <2 A（4 个电机均分负载）
[ ] 电机温度上升 <10°C / 分钟
[ ] 髋部高度变化 <5 mm（通过卷尺测量）
[ ] 无电机过载报错
```

### 5.3 异常处理

| 现象 | 原因 | 解决 |
|------|------|------|
| 关节漂移 >10° | PD 增益不足 | k_P 提高 50% |
| 一侧电流 >3 A | 重心偏移 | 调整髋部配重对称 |
| 温度快速上升 | 持续大扭矩 | 降低 tau_max 或检查机械摩擦 |

---

## 6. T5 - 单步行走

### 6.1 目标

完成一次完整的步态周期（左腿支撑→右腿摆动→落地）。

### 6.2 风险评估

```
风险级别: 中-高
潜在事故:
- 摆动腿打到障碍 → 机械损坏
- 落地点错误 → 失稳跌倒
- 电机响应延迟 → 错过相位

缓解措施:
- 保险绳张紧（仅在真正失稳时承力）
- 软垫铺满 1 m × 2 m
- 急停按钮手按（不离开机器 1 m 范围）
- 视频录制（用于事后分析）
```

### 6.3 渐进式测试

**Step 1: 半挂载支撑（保险绳承一半重）**

```
- 保险绳张力 ≈ 25-30 N（机器人 50% 重量）
- 启动 V13.7 FSM 控制器
- 命令：单步触发（按按钮）
- 观察：摆动腿能否抬起到正确高度
```

**Step 2: 全挂载支撑后释放（"降落")**

```
- 保险绳张力 = 全重（不接触地）
- 启动 FSM
- 缓慢降低保险绳，让脚底触地
- 观察：能否在触地后维持平衡
```

**Step 3: 自主单步**

```
- 保险绳松弛（待命）
- 用手轻推髋部前向 0.05 m/s
- FSM 自主响应
- 期望：完成一次摆动 + 触地
```

### 6.4 数据采集

每次单步测试记录:

```python
# 记录文件: T5_step_YYYY-MM-DD_HH-MM.csv
columns = [
    't',                    # 时间 (s)
    'phase',                # FSM 相位
    'l_hip_pos', 'l_hip_vel',
    'l_knee_pos', 'l_knee_vel',
    'r_hip_pos', 'r_hip_vel',
    'r_knee_pos', 'r_knee_vel',
    'l_contact', 'r_contact',
    'tau_l_hip', 'tau_l_knee',
    'tau_r_hip', 'tau_r_knee',
    'imu_pitch', 'imu_roll',
    'battery_voltage',
    'battery_current'
]
# 采样率：100 Hz，运行 5-10 秒
```

### 6.5 验收标准

**通过 T5**:

```
[ ] 摆动腿能完整抬起（膝弯曲 ≥ 25°）
[ ] 摆动腿落地点在前方 0.25-0.45 m
[ ] 落地后 0.5 s 内未跌倒
[ ] FSM 状态机按预期切换（4 个相位都触发过）
[ ] 控制扭矩未饱和（峰值 < 3.8 N·m）
[ ] 峰值电流 < 4 A
```

---

## 7. T6 - 连续步态

### 7.1 目标

实现 ≥3 步的连续交替触地，验证步态周期稳定性。

### 7.2 测试递进

```
Day 1: 3 步连续（短距离）
Day 2: 5 步连续（约 2 m）
Day 3: 10 步连续（约 4 m）
Day 4: 20 步连续（>5 m）
Day 5: 极限测试（最远距离）
```

### 7.3 性能指标

```python
# 每次测试计算的指标
metrics = {
    'total_steps': 12,
    'distance_m': 4.8,
    'avg_step_length_m': 0.40,
    'avg_step_time_s': 0.78,
    'avg_speed_m_s': 0.31,
    'std_step_length_m': 0.025,    # 步长标准差
    'std_step_time_s': 0.015,      # 步频稳定性
    'failure_step': None,          # 何时失败（None=未失败）
    'cot': 0.085,                  # 运输代价
}
```

### 7.4 与仿真比对

```
仿真预期（V13.7）:
  步长 0.40 ± 0.02 m
  步频 1.25 Hz
  速度 0.30 m/s
  CoT  0.08

允许偏差:
  步长偏差 <15%
  步频偏差 <10%
  速度偏差 <20%
  CoT < 0.15（实测受机械摩擦影响）
```

### 7.5 验收标准

```
[ ] 连续 ≥10 步无人工干预
[ ] 步长 / 步频 标准差 <10%
[ ] 至少 3 次重复实验都成功
[ ] 实测速度 0.25-0.35 m/s
[ ] 录制 30 秒以上行走视频
```

---

## 8. T7 - 鲁棒性测试

### 8.1 测试矩阵

| 扰动类型 | 强度 | 方向 | 验收 |
|---------|------|------|------|
| 推力扰动 | 5 N | 前向 | 不跌倒 |
| 推力扰动 | 5 N | 后向 | 不跌倒 |
| 推力扰动 | 3 N | 侧向 | 不跌倒（导轨吸收） |
| 地面起伏 | ±5 mm | 前进路径 | 不卡顿 |
| 电池电压 | 10.8V (低) | - | 仍能行走 |
| 电池电压 | 12.4V (高) | - | 不抖动 |
| 通信延迟 | +5 ms | - | 仍稳定 |
| 控制周期 | 500 Hz (减半) | - | 退化 <30% |

### 8.2 测试方法

**推力扰动**（人工）:

```
1. 机器人正常行走中
2. 用 5 N 弹簧秤推动髋部
3. 持续 0.2 s 后释放
4. 观察后续 3 步表现
5. 记录恢复时间
```

**地面起伏**（被动）:

```
1. 在导轨下铺设 5 mm 厚胶皮（局部 0.2 m 长）
2. 让机器人路过
3. 观察过坎时是否卡顿、跌倒
```

**电池电压模拟**:

```
1. 用可调直流电源替代 LiPo（11.1V ±10%）
2. 在不同电压下运行
3. 检查控制律稳定性
```

### 8.3 验收标准

```
[ ] 5 N 前向扰动后能在 5 步内恢复
[ ] 通过 5 mm 起伏不跌倒
[ ] 电池电压 10.5-12.6V 都可正常行走
[ ] 故意降低控制周期到 500 Hz，行走仍可持续 5 步以上
```

---

## 9. T8 - V25 验收测试

### 9.1 验收目标（与博士论文/项目里程碑对齐）

```
核心验收（必须达成）:
[ ] 连续行走 ≥5 m
[ ] 交替步数 ≥10 次
[ ] 行走速度 ≈0.3 m/s
[ ] 录制完整行走视频（4K, 30 fps, 含侧视角）
[ ] 与仿真预测对比图（步长/步频/角度轨迹）

加分项:
[ ] CoT 实测 <0.1
[ ] 系统辨识参数与仿真偏差 <10%
[ ] 通过 T7 的所有鲁棒性测试
```

### 9.2 视频录制规范

```
角度:
  侧视图: 主机位，距离 3 m，高度 1 m
  前视图: 副机位，距离 4 m，高度 0.5 m
  顶视图: 手机俯拍（可选）

参数:
  分辨率: 3840×2160 (4K)
  帧率: 60 fps（便于后期慢动作）
  曝光: 手动 1/250 s（避免运动模糊）

后期处理:
  - 添加时间戳水印
  - 同步显示仿真画面（左右分屏）
  - 标注步数和距离
```

### 9.3 数据完整性检查

```
原始数据 (raw/):
[ ] 所有控制器状态 CSV (≥10 个)
[ ] IMU 原始数据
[ ] 电流/电压日志
[ ] 视频文件 ≥3 个

分析结果 (analysis/):
[ ] 步长/步频统计图
[ ] 关节轨迹与仿真对比图
[ ] CoT 计算与误差分析
[ ] 失败案例归因报告

文档 (docs/):
[ ] V25 验收报告 (Markdown)
[ ] 测试日志汇总
[ ] 系统辨识参数表
```

---

## 10. 性能验收标准（汇总）

### 10.1 关键性能指标（KPI）

| 指标 | 仿真值 | 验收阈值 | 来源 |
|------|--------|----------|------|
| 行走距离 | ∞ | ≥5 m | V13.7 验证 |
| 步长 | 0.40 m | 0.34-0.46 m | ±15% |
| 步频 | 1.25 Hz | 1.13-1.38 Hz | ±10% |
| 速度 | 0.30 m/s | 0.24-0.36 m/s | ±20% |
| CoT | 0.08 | <0.15 | 含摩擦损耗 |
| 跌倒率 | 0% | <10% | 10 次试验 |
| 控制频率 | 1000 Hz | ≥500 Hz | 软件保证 |
| 接触延迟 | 0 ms | <15 ms | V17 要求 |

### 10.2 安全验收

```
[ ] 急停响应时间 <500 ms
[ ] 跌倒检测触发 <100 ms
[ ] 过流保护工作（>5 A 切断）
[ ] 过温保护工作（>70°C 降扭）
[ ] 低电压保护工作（<9.5V 报警）
```

### 10.3 文档验收

```
[ ] 测试日志完整（每个 Tx 阶段都有）
[ ] 异常事件复盘表
[ ] 与仿真比对表（含偏差解释）
[ ] 系统辨识修正后的仿真参数
```

---

## 11. 安全注意事项

### 11.1 始终遵守的安全规则

```
1. 通电前检查清单（每次都做）
   [ ] 电池电压正常
   [ ] 急停按钮可达
   [ ] 工作区域无障碍
   [ ] 视频/数据记录开启

2. 测试中
   - 始终保持手在急停按钮 <0.5 m 内
   - 不戴耳机（要听到电机异常声响）
   - 戴防护眼镜（特别是首次/换部件后）
   - 不单独测试（至少有 1 个观察员）

3. 出现异常
   - 第一反应：按急停
   - 第二反应：物理隔离（断电池）
   - 第三反应：拍照记录现场
   - 第四反应：写复盘报告

4. LiPo 电池安全
   - 充电时人不离开
   - 防火袋存储
   - 不过充（>4.20V/cell）
   - 不过放（<3.30V/cell）
   - 损坏立即报废（鼓包/破皮）
```

### 11.2 电机安全阈值

```python
# safety_monitor.py 必须运行的监控
class SafetyMonitor:
    def __init__(self):
        self.thresholds = {
            'max_current': 4.0,    # A，超过即停
            'max_temp': 65,         # °C，超过降扭矩
            'min_voltage': 10.0,    # V，低电报警
            'max_pitch': 45,        # ° IMU，超过急停
            'max_step_time': 1.5,   # s，超过认为卡死
        }

    def check(self, state):
        violations = []
        if state['current'] > self.thresholds['max_current']:
            violations.append('OVERCURRENT')
        if state['temp'] > self.thresholds['max_temp']:
            violations.append('OVERTEMP')
        if state['voltage'] < self.thresholds['min_voltage']:
            violations.append('UNDERVOLTAGE')
        if abs(state['imu_pitch']) > self.thresholds['max_pitch']:
            violations.append('FALL')

        if violations:
            self.emergency_stop(violations)
            return False
        return True

    def emergency_stop(self, reasons):
        print(f"!!! EMERGENCY STOP: {reasons}")
        # 立即关闭所有电机扭矩
        for dxl_id in [1, 2, 3, 4]:
            ph.write1ByteTxRx(dxl_id, 64, 0)
```

### 11.3 应急响应预案

**场景 A: 机器人跌倒**

```
1. 按急停按钮（如未自动触发）
2. 不立即扶起 - 先观察姿态（拍照）
3. 切断 LiPo 电池
4. 检查机械损坏（关节/管路/线缆）
5. 视情况：可继续 / 需修理 / 需停工
6. 写跌倒报告（时间、相位、推测原因）
```

**场景 B: 电机冒烟/异味**

```
1. 立即按急停 + 切断主电源
2. 远离机器人（防 LiPo 起火）
3. 观察 5 分钟（看是否复燃）
4. 准备好灭火器（沙土或专用 LiPo 灭火）
5. 待冷却后排查故障电机
6. 故障电机送修或更换
```

**场景 C: LiPo 电池起火**

```
1. 立即用沙土或专用灭火器扑灭（禁用水）
2. 把电池移到室外通风处（用钳子）
3. 浸入盐水 24 小时彻底放电
4. 联系当地危废处理
5. 排查原因（过充/短路/物理损伤）
```

---

## 12. 测试记录模板

### 12.1 单次测试记录表

```markdown
# 测试记录 - T_X_YYYYMMDD

## 基本信息
- 测试 ID: T5-001
- 日期: 2026-XX-XX HH:MM
- 测试员: 段泽琪
- 观察员: ___
- 环境温度: 22°C
- 电池电压（开始）: 12.4V
- 电池电压（结束）: 11.8V

## 测试目标
[ ] T5: 完成一次单步行走

## 测试参数
- FSM 增益: k_PD=30, k_E=7.5
- tau_max: 4.0 N·m
- 控制频率: 1000 Hz
- 摩擦补偿 tau_C_eff: 0.20

## 测试过程
HH:MM 启动控制器
HH:MM 触发单步
HH:MM 观察到 ___

## 数据记录
- 原始 CSV: ~/hw1/logs/T5_001_raw.csv
- 视频: ~/hw1/videos/T5_001.mp4
- 截图: ~/hw1/photos/T5_001_*.jpg

## 关键测量
| 指标 | 仿真预测 | 实测 | 偏差 |
|------|---------|------|------|
| 步长 | 0.40 m | 0.36 m | -10% |
| 步时 | 0.80 s | 0.85 s | +6% |
| 峰值扭矩 | 3.5 N·m | 3.2 N·m | -9% |

## 结论
[x] 通过 / [ ] 失败 / [ ] 部分通过

## 后续行动
1. ...
```

### 12.2 阶段总结模板

```markdown
# 测试阶段 T_X 总结

## 累计测试次数
- 成功: __ / 总 __
- 成功率: __%

## 关键发现
1. ...

## 与仿真偏差
| 指标 | 仿真 | 实测均值 | 标准差 |
|------|------|----------|--------|
| ...  |      |          |        |

## 改进建议
1. （硬件层）...
2. （控制层）...
3. （仿真层 - 反馈给 V23/V24）...

## 下阶段进入条件
[ ] T_X 已达标
[ ] 安全检查通过
[ ] 备件库存充足
```

---

## 13. 测试进度跟踪表

```
项目启动日期: ___________

阶段     | 计划开始 | 实际开始 | 计划完成 | 实际完成 | 状态
---------|----------|----------|----------|----------|------
T0       | Day 1    | ___      | Day 1    | ___      | 待开始
T1       | Day 2    | ___      | Day 2    | ___      | 待开始
T2       | Day 3    | ___      | Day 3    | ___      | 待开始
T3       | Day 4    | ___      | Day 5    | ___      | 待开始
T4       | Day 6    | ___      | Day 6    | ___      | 待开始
T5       | Day 7    | ___      | Day 9    | ___      | 待开始
T6       | Day 10   | ___      | Day 14   | ___      | 待开始
T7       | Day 15   | ___      | Day 19   | ___      | 待开始
T8       | Day 20   | ___      | Day 22   | ___      | 待开始

总计: 22 天（不含周末）
```

---

## 14. 与系统辨识 V23 的衔接

测试中采集的数据应直接用于 V23 系统辨识：

```
T2 数据 → 摩擦系数辨识（identify_friction.py）
          库仑摩擦 τ_C 实测值
          粘滞摩擦 b 实测值

T3 数据 → 转动惯量辨识（identify_inertia.py）
          自由摆动衰减率
          各部件等效转动惯量

T5/T6 数据 → 接触模型辨识
            接触刚度等效值
            摩擦系数（地面）实测

T8 数据 → 综合参数验证
          所有仿真参数的实测值
          为 V24 域随机化提供依据
```

数据交付格式（V23 使用）:

```
v23_system_identification/data/
├── T2_friction/
│   ├── joint1_omega_tau.csv
│   ├── joint2_omega_tau.csv
│   ├── joint3_omega_tau.csv
│   └── joint4_omega_tau.csv
├── T3_inertia/
│   ├── leg_swing_decay.csv
│   └── ...
├── T5_T6_walking/
│   ├── step_001.csv
│   ├── step_002.csv
│   └── ...
└── T8_validation/
    └── full_run_5m.csv
```

---

## 15. 文件版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2026-06-05 | 初版完成 |

---

## 16. 参考文档

- HARDWARE_SPEC.md - 硬件规格书
- MANUFACTURING_GUIDE.md - 制作指南（配套）
- SIMULATION_MAPPING.md - 仿真参数映射
- ../v13_7_friction_compensation/README.md
- ../v17_state_estimation/README.md
- ../v23_system_identification/README.md
- ../v24_sim_to_real/README.md


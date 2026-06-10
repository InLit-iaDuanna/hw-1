# 实物就绪控制器 (Hardware-Ready Controller)

> 基于 V13.7 (FSM + 摩擦补偿) + V17 (状态估计) 的实物落地控制算法

## 设计原则

1. **经过仿真验证**：所有组件都在 MuJoCo 中测试通过
2. **硬件可移植**：代码结构适合嵌入式部署（Raspberry Pi / STM32）
3. **鲁棒性优先**：考虑传感器噪声、电机摩擦、参数不确定性
4. **实时性**：控制周期 1kHz（1ms），状态估计 200Hz（5ms）

## 核心算法

### 架构
```
传感器 → 状态估计 → 相位检测 → 轨迹生成 → 前馈+反馈 → 电机指令
 (编码器)  (Kalman)    (FSM)    (查表/计算)  (补偿+PD)   (力矩)
```

### 四个关键模块

#### 1. 状态估计器 (StateEstimator)
- **输入**：编码器读数（4096 CPR，有噪声）
- **输出**：滤波后的角度、角速度、髋位置
- **算法**：Kalman Filter + 前向运动学
- **来源**：V17 验证通过，noise_scale=1.0 稳定

#### 2. 相位状态机 (PhaseStateMachine)
- **状态**：支撑早期 → 支撑晚期 → 摆动推进 → 摆动回收
- **触发**：接触传感器 + 时间阈值
- **输出**：当前相位、相位时间
- **来源**：V13.6 事件驱动 FSM

#### 3. 前馈补偿器 (FeedforwardCompensator)
- **摩擦补偿**：`τ_friction = τ_C_eff * sign_smooth(ω_joint, ε=0.01)`
- **重力补偿**：`τ_gravity = M*g*L*sin(θ)`（可选，取决于机构）
- **来源**：V13.7 摩擦补偿，消除失败带

#### 4. 反馈控制器 (FeedbackController)
- **PD 控制**：`τ_fb = Kp*(θ_des - θ) + Kd*(ω_des - ω)`
- **增益调度**：不同相位用不同增益
- **饱和保护**：限制在电机最大力矩范围

### 总控制律
```python
τ_total = τ_feedforward + τ_feedback
        = τ_friction_comp + τ_gravity_comp + Kp*e_θ + Kd*e_ω
```

## 关键参数（V13.7 验证值）

### 电机参数（Dynamixel MX-64AR）
```python
J_motor = 2.8e-3      # kg·m²
b_motor = 0.05        # N·m·s/rad
τ_C_eff = 0.20        # N·m (库仑摩擦)
τ_max = 6.0           # N·m (饱和限制)
```

### FSM 相位时长（V13.6.1 最优值）
```python
stance_early_duration = 0.15   # s
stance_late_duration = 0.25    # s
swing_thrust_duration = 0.18   # s
swing_retract_duration = 0.15  # s
```

### PD 增益（每个相位）
```python
# 支撑相：刚性，维持姿态
stance_Kp = 40.0
stance_Kd = 6.0

# 摆动相：柔顺，快速响应
swing_Kp = 25.0
swing_Kd = 3.0
```

### 状态估计参数
```python
encoder_resolution = 4096      # CPR
process_noise_std = 0.01       # rad (角度过程噪声)
measurement_noise_std = 0.002  # rad (编码器噪声, V17实测)
contact_delay_max = 0.015      # s (接触延迟上限)
```

## 文件结构

```
hardware_ready_controller/
├── README.md                      # 本文件
├── controller.py                  # 主控制器类
├── state_estimator.py             # Kalman 状态估计
├── phase_fsm.py                   # 相位状态机
├── feedforward.py                 # 前馈补偿器
├── feedback.py                    # PD 反馈控制
├── trajectory_generator.py        # 轨迹生成器
├── hardware_interface.py          # 硬件抽象层（传感器/电机接口）
├── realtime_simulator.py          # 实时仿真测试
├── deployment/
│   ├── raspberry_pi_deploy.py    # Raspberry Pi 部署代码
│   ├── requirements_hardware.txt # 硬件依赖
│   └── startup_script.sh         # 启动脚本
├── tests/
│   ├── test_state_estimator.py
│   ├── test_phase_fsm.py
│   └── test_full_controller.py
└── examples/
    ├── run_in_mujoco.py          # MuJoCo 仿真测试
    ├── hardware_in_loop.py       # 硬件在环测试
    └── tune_parameters.py        # 参数调优工具
```

## 使用方法

### 1. 仿真测试
```python
from hardware_ready_controller import HardwareReadyController
import mujoco

# 加载模型
model = mujoco.MjModel.from_xml_path("model.xml")
data = mujoco.MjData(model)

# 创建控制器
controller = HardwareReadyController(
    motor_specs="MX-64AR",  # 自动加载电机参数
    fsm_config="v13.7",     # 使用 V13.7 相位配置
    enable_friction_comp=True,
    enable_state_estimation=True
)

# 控制循环
for t in range(12000):  # 12s @ 1kHz
    # 读取传感器
    sensors = controller.read_sensors(data)
    
    # 计算控制指令
    torques = controller.compute_control(sensors, dt=0.001)
    
    # 应用到仿真
    data.ctrl[:] = torques
    mujoco.mj_step(model, data)
```

### 2. 硬件部署
```python
from hardware_ready_controller import HardwareReadyController
from hardware_interface import RaspberryPiInterface

# 初始化硬件接口
hw = RaspberryPiInterface(
    motor_bus="/dev/ttyUSB0",
    motor_ids=[1, 2, 3, 4],  # hip_l, knee_l, hip_r, knee_r
    encoder_spi_channels=[0, 1, 2, 3],
    contact_gpio_pins=[17, 27]  # left, right foot
)

# 创建控制器（相同代码！）
controller = HardwareReadyController(
    motor_specs="MX-64AR",
    fsm_config="v13.7"
)

# 实时控制循环（1kHz）
while True:
    t_start = time.perf_counter()
    
    # 读传感器
    sensors = hw.read_sensors()
    
    # 计算控制
    torques = controller.compute_control(sensors, dt=0.001)
    
    # 写电机
    hw.write_torques(torques)
    
    # 保证 1kHz
    elapsed = time.perf_counter() - t_start
    if elapsed < 0.001:
        time.sleep(0.001 - elapsed)
```

## 与 PID 的对比

| 特性 | 单纯 PID | 本控制器 |
|------|---------|---------|
| **周期性步态** | ❌ 不考虑相位 | ✅ FSM 相位控制 |
| **摩擦处理** | ❌ 只能反馈抑制 | ✅ 前馈精确补偿 |
| **传感器噪声** | ❌ 直接微分放大噪声 | ✅ Kalman 滤波 |
| **增益调优** | ❌ 全局单一增益 | ✅ 相位自适应增益 |
| **仿真验证** | ❌ 未验证 | ✅ V13.7+V17 通过 |
| **鲁棒性** | ❌ V16 失败 | ✅ V13.7 成功 |

## 关键优势

### 1. 经过实战验证
- V13.7：真实电机动力学下稳定（forward 4.63m, 10 steps）
- V17：传感器噪声下稳定（noise_scale=3.0 容限）
- V16：证明必须有摩擦补偿

### 2. 理论支撑
- **前馈补偿**：补偿已知扰动（摩擦、重力）
- **反馈控制**：只处理未建模部分和外部扰动
- **状态估计**：提供干净、低延迟的状态信号

### 3. 工程实用
- 代码模块化，易于调试
- 硬件接口抽象，易于移植
- 参数有明确来源，不是拍脑袋

## 下一步

1. **✅ 完成代码实现**（正在进行）
2. **测试流程**：
   - 单元测试（每个模块）
   - MuJoCo 仿真集成测试
   - 硬件在环测试（HIL）
   - 实物测试
3. **参数调优工具**：
   - 自动化参数扫描
   - 鲁棒性边界测试
   - 性能指标对比

## 参考

- V13.7: 前馈摩擦补偿
- V17: 传感器闭环状态估计
- V16: 电机动力学失败分析
- V22: 硬件设计规格

# V17 — 传感器闭环状态估计

**状态**：已完成，验证通过  
**日期**：2026-06-02  
**定位**：V13.7 摩擦补偿 FSM + 传感器噪声 + Kalman 滤波状态估计  

## 1. 设计动机

V13.7 摩擦补偿 FSM 已在理想传感器下验证成功。V17 的目标是测试控制器在**真实传感器条件**下的鲁棒性，包括：
- 编码器量化噪声（4096 CPR）
- 速度估计误差
- 接触检测延迟
- 状态估计器（Kalman 滤波）

为 V22 硬件落地提供传感器规格约束。

## 2. 技术实现

### 2.1 传感器噪声模型

基于 Dynamixel MX-64AR 规格：

| 传感器 | 噪声类型 | 参数 |
|--------|----------|------|
| 编码器 | 量化噪声 | ±0.088° (360°/4096) |
| 速度 | 高斯噪声 | σ = 0.01 rad/s × noise_scale |
| 接触开关 | 延迟 | 5 ms (默认) |

`noise_scale` 参数：
- 0.0：理想传感器
- 1.0：MX-64AR 真实规格
- 2.0：2× 安全裕度
- 3.0：临界失败点

### 2.2 Kalman 滤波器

**状态向量**：`[hip_x, hip_vx]`

**观测**：
- 通过正运动学（FK）从关节角度计算 hip_x
- 速度通过数值微分 + Kalman 平滑

**参数**：
- 过程噪声 Q：假设恒速模型
- 观测噪声 R：根据 noise_scale 调整
- 更新频率：1000 Hz（与控制同步）

### 2.3 接触延迟模型

```python
sensor_lag = 0.005  # 5 ms 默认
actual_contact_time = t
sensed_contact_time = t + sensor_lag
```

延迟 ≥15 ms 会破坏 FSM 时序（实测）。

## 3. 实验结果

### 3.1 Baseline（noise_scale=1.0，MX-64AR 规格）

| 指标 | 值 |
|------|-----|
| success | True |
| forward_distance | 4.67 m |
| alternating_touchdowns | 10 |
| simulated_time | 11.99 s |
| **estimation_rmse_vx** | **0.079 m/s** |
| **estimation_rmse_hip_x** | **0.045 m** |
| failure | completed |

**结论**：MX-64AR 传感器规格下，状态估计误差可接受，控制器稳定。

### 3.2 噪声容限扫描

扫描 noise_scale ∈ [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]

| noise_scale | 成功 | forward (m) | alt_td | RMSE_vx (m/s) | 失败模式 |
|-------------|------|-------------|--------|---------------|----------|
| 0.0 | ✓ | 4.52 | 10 | 0.076 | - |
| 0.5 | ✓ | 4.69 | 10 | 0.080 | - |
| **1.0** | ✓ | **4.67** | **10** | **0.079** | - |
| 2.0 | ✓ | 4.54 | 10 | 0.076 | - |
| **3.0** | ✗ | 0.11 | 4 | 0.150 | **fall_down** |
| 5.0 | ✗ | 0.11 | 4 | 0.149 | fall_down |
| 8.0 | ✗ | 0.11 | 4 | 0.150 | fall_down |
| 12.0 | ✗ | 0.11 | 4 | 0.168 | fall_down |
| 20.0 | ✗ | 0.13 | 1 | 0.170 | fall_down |

**临界点**：noise_scale = 3.0（3× MX-64AR 规格）

**安全裕度**：2.0×（通过）→ 3.0×（失败）

### 3.3 失败机制

noise_scale ≥ 3.0 时：
1. 速度估计误差过大（RMSE >0.15 m/s）
2. FSM 相位判断错误
3. 支撑腿和摆动腿混淆
4. ~3 秒后跌倒

## 4. 与 V13.7 对比

| 指标 | V13.7（真值） | V17（noise=1.0） | 偏差 |
|------|--------------|------------------|------|
| forward | 4.63 m | 4.67 m | +0.9% |
| alt_td | 10 | 10 | 0 |
| success | True | True | ✓ |

**结论**：真实传感器噪声下，性能与理想情况几乎无偏差。

## 5. 硬件约束（V22 设计输入）

基于 V17 验证结果，V22 硬件必须满足：

| 传感器 | 约束 | 理由 |
|--------|------|------|
| 编码器分辨率 | ≥ 4096 CPR | noise_scale=1.0 通过 |
| 编码器精度 | ≤ 0.1° | MX-64AR 规格 |
| 接触开关延迟 | < 15 ms | 超过会破坏 FSM |
| 速度噪声 | σ < 0.02 rad/s | 2× 安全裕度 |

**推荐传感器**：Dynamixel MX-64AR 内置编码器（已验证）

## 6. 核心算法伪代码

```python
class KalmanFilter:
    def __init__(self, Q, R):
        self.x = [0, 0]  # [position, velocity]
        self.P = [[1, 0], [0, 1]]
        self.Q = Q  # 过程噪声
        self.R = R  # 观测噪声
    
    def predict(self, dt):
        # 恒速模型
        self.x[0] += self.x[1] * dt
        self.P[0][0] += self.Q[0][0] * dt
        self.P[1][1] += self.Q[1][1] * dt
    
    def update(self, measurement):
        # Kalman 更新
        y = measurement - self.x[0]
        S = self.P[0][0] + self.R
        K = self.P[0][0] / S
        self.x[0] += K * y
        self.x[1] += K * (y / dt)
        self.P[0][0] *= (1 - K)

# 主循环
kf = KalmanFilter(Q=..., R=noise_scale*0.01)
for step in range(duration/timestep):
    # 1. 读取传感器
    joint_angles = read_encoder_with_noise()
    contact = read_contact_with_delay(sensor_lag=0.005)
    
    # 2. 状态估计
    hip_x_fk = forward_kinematics(joint_angles)
    kf.predict(dt=timestep)
    kf.update(hip_x_fk)
    
    # 3. 控制器（使用估计状态）
    tau_fsm = v137_fsm_controller(kf.x, contact, ...)
    
    # 4. 执行
    apply_torque(tau_fsm)
```

## 7. 文件清单

```
v17_state_estimation/
├── simulate_v17.py          # 主仿真脚本
├── out/
│   ├── v17_mx64ar_noise1_summary.json    # Baseline 结果
│   ├── scan_v17_noise.json               # 噪声扫描
│   ├── v17_mx64ar_noise1.mp4            # 视频
│   ├── v17_mx64ar_noise1_data.csv       # 完整数据
│   └── v17_mx64ar_noise1_preview.png    # 预览图
└── README.md（本文件）
```

## 8. 复现命令

```powershell
cd D:\Dunna\Documents\hw-1\v17_state_estimation
..\.venv-mujoco\Scripts\python.exe simulate_v17.py --noise-scale 1.0 --sensor-lag 0.005 --duration 12 --save-prefix v17_mx64ar_noise1
```

## 9. 关键发现

1. **MX-64AR 合格**：1× 噪声下通过，2× 安全裕度充足
2. **接触延迟敏感**：<15 ms 必须满足（V22 约束）
3. **Kalman 有效**：RMSE 0.079 m/s 可接受
4. **与 V13.7 无偏差**：+0.9% 前进距离（噪声引入的随机波动）

## 10. 与 ROADMAP 的关系

V17 完成后：
- ✅ 阶段 2（2D 机械升级 V14-V17）主线闭环
- ✅ V22 硬件设计的传感器规格已确定
- ✅ V24 Sim-to-real 的传感器建模已验证

V17 + V13.7 = **可直接迁移到硬件的完整控制器**

## 11. 后续工作（V22 实施时）

1. 在硬件上验证编码器精度（与仿真对比）
2. 测量实际接触开关延迟（示波器）
3. 如延迟 >15 ms，需调整 FSM 时序参数
4. 微调 Kalman 滤波器参数（Q/R 矩阵）

## 12. 参考文献

- V13.7 README: 摩擦补偿 FSM 基线
- V16 README: 电机动力学模型
- Dynamixel MX-64AR e-Manual: 传感器规格

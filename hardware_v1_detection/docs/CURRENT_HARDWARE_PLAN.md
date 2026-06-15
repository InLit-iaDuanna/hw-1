# 当前硬件方案与工作总结

更新时间：2026-06-15

## 1. 当前目标

当前项目正在做的是 **Hardware V1.1 无线 IMU 步态采集原型**。

核心目标不是先做完整临床算法，而是先验证这条硬件链路是否可靠：

```text
BMI160 IMU -> ESP32-C3 远端节点 -> ESP-NOW -> ESP32-S3 腰部 hub -> USB -> PC demo-app
```

当前已经验证的是 **单 C3 + 单 BMI160**，默认映射为 `left_foot`。  
S3 作为腰部主控和电脑入口，PC 只需要连接 S3 的串口。

## 2. 为什么从 V1 改到 V1.1

最初 V1 方案是假设 6 个 BMI160 和 1 个 BMX055 都通过 TCA9548A I2C mux 接到 ESP32-S3：

```text
6x BMI160 + 1x BMX055 -> TCA9548A -> ESP32-S3 -> USB -> PC
```

但实际佩戴时，S3 在腰部，脚、小腿、大腿传感器分布在腿部，全部拉线到腰部不现实。  
所以当前切到 V1.1：

```text
每个远端 IMU 由一个 ESP32-C3 本地采集，再无线发给腰部 S3
```

这能避免长线 I2C，也更接近后续可穿戴形态。

## 3. 当前硬件连接

### ESP32-C3 + BMI160

当前只接了一个 C3 节点：

| BMI160 引脚 | ESP32-C3 连接 | 说明 |
|---|---|---|
| `VIN` / `3.3V` | `3.3V` | 传感器供电 |
| `GND` | `GND` | 共地 |
| `SDA` | `GPIO4` | I2C data |
| `SCL` | `GPIO5` | I2C clock |
| `CS` | `3.3V` | 选择 I2C 模式 |
| `SAO` | `GND` | BMI160 地址为 `0x68` |
| `INT1` / `INT2` | 不接 | 当前轮询读取，不用中断 |

### ESP32-S3

S3 当前只需要：

- USB 连接电脑
- 运行 hub 固件
- 通过 ESP-NOW 接收 C3 数据
- 通过 USB 串口输出二进制帧给 PC

当前 S3 不要求接 TCA9548A，也不要求接其它 IMU。

## 4. 当前固件行为

### C3 节点

工程目录：

```text
hardware_v1_detection/firmware_esp32c3_node/
```

当前行为：

- I2C 读取 1 个 BMI160
- 默认节点 `node_id = 1`
- 默认映射为 `left_foot`
- I2C 默认 `SDA=GPIO4`、`SCL=GPIO5`
- 采样率当前按 V1.1 测试使用 `100Hz`
- 通过 ESP-NOW channel `1` 发给 S3
- 无线包中包含：
  - `node_id`
  - `c3_seq`
  - `c3_ts_us`
  - IMU6 raw：`ax, ay, az, gx, gy, gz`
  - C3 芯片内部温度 `temp_c`

温度读取已改成 **1Hz 缓存**，避免每个 IMU 包都读温度影响链路。

### S3 hub

工程目录：

```text
hardware_v1_detection/firmware_esp32s3/
```

当前行为：

- 通过 ESP-NOW 接收 C3 数据
- 将 `node_id=1` 映射到聚合帧的 `left_foot`
- S3 仍以 `200Hz` 向 PC 输出聚合 sample frame
- 保持原来的 `type=0x01` 兼容帧：
  - payload 为 `45 x int16`
  - 结构为 `6 x BMI160 IMU6 + 1 x BMX055 IMU9`
- 新增 `type=0x11` node debug frame：
  - 保存 C3 原始节点包
  - 包含 `age_ms`
  - 包含 C3 温度 `temp_c`

当前只有 `left_foot` 有真实数据，其它通道 fail 是预期现象。

## 5. PC 软件

### 串口采集

入口：

```text
hardware_v1_detection/pc_receiver/serial_capture.py
```

运行命令：

```powershell
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM7 --duration 60 --output hardware_v1_sessions
```

注意：

- `COM7` 是 S3，PC 采集和 demo 都选它
- `COM5` 是 C3 调试口，不作为 demo 输入

采集输出：

```text
hardware_v1_sessions/session_YYYYMMDD_HHMMSS/
```

包含：

- `raw.csv`
- `scaled.csv`
- `raw.npz`
- `node_raw.csv`
- `session_summary.json`

其中 `node_raw.csv` 已增加 `temp_c` 列。  
`session_summary.json` 已增加：

- `node_temp_c_last`
- `node_temp_c_max`

### demo-app

入口：

```text
hardware_v1_detection/demo_app/app.py
```

运行命令：

```powershell
.\.venv-mujoco\Scripts\python.exe hardware_v1_detection\demo_app\app.py
```

使用方式：

1. 打开 demo-app
2. 选择 `COM7`
3. 点击 `Start`
4. 晃动 C3/BMI160
5. 看 `left_foot` 波形是否实时变化
6. 看右侧 `C3 TEMP` 是否显示温度
7. 看 `C3 LINK` 是否显示 node、age、seq

## 6. 当前已经验证的结果

当前单节点链路已经跑通：

- `left_foot` 波形实时变化
- S3 聚合帧稳定输出 `200Hz`
- PC parser CRC 正常
- demo-app 能看到 C3 温度

最近一次 10 秒验证结果大致为：

```text
mcu_frame_rate_hz = 200.0
crc_errors = 0
dropped_frames = 0
left_foot_fail = 0
node_age_ms_p95 = 4.0 ms
node_temp_c_last ≈ 70-73 C
```

说明：

- C3 内部芯片温度约 70°C 左右
- 这是芯片内部温度，不等于外壳/皮肤接触温度
- 当前不能裸板贴皮肤
- 后续需要外壳、隔热层或空气间隙

## 7. 当前方案边界

当前系统输出的是 **工程原型采集数据**，不是临床结论。

目前已经有：

- 原始 IMU raw 数据
- 简单单位换算
- C3 节点链路质量统计
- C3 温度显示
- demo 实时波形

目前还没有完成：

- 多 C3 节点同步
- 全腿 6 IMU 姿态解算
- 传感器安装方向标定
- 稳定 heel-strike / toe-off 检测
- 左右步态对称性临床指标
- FSR 足底压力

## 8. 核心算法路线

算法不从仿真直接搬临床结论。当前路线是分层做：

```text
L0 raw 采集
L1 标定和坐标对齐
L2 姿态解算
L3 gait event 检测
L4 步态指标和临床解释
```

V1.1 现在主要完成的是 L0：

- 稳定采集
- 稳定传输
- 能保存
- 能实时显示
- 能监测节点温度和链路状态

后续真正影响临床产出的关键是 L2/L3：

- 大腿、小腿、足部 IMU 姿态要对齐到人体坐标
- 膝关节角 = 大腿 pitch - 小腿 pitch
- 髋关节角 = 大腿 pitch - 骨盆 pitch
- 无 FSR 时 heel-strike/toe-off 只能先用 IMU 估计
- 如果 IMU 事件检测不稳，再加 FSR 做足底事件真值

## 9. 下一步建议

### Step 1：固定当前单节点版本

先保留当前稳定状态，做 60 秒记录：

```powershell
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM7 --duration 60 --output hardware_v1_sessions
```

验收重点：

- `crc_errors = 0`
- `dropped_frames = 0`
- `left_foot_fail = 0`
- `node_age_ms_p95 <= 50`
- `node_temp_c_max` 不持续异常升高

### Step 2：做第二个 C3 节点

建议下一个节点做 `right_foot`：

```text
node_id = 2 -> right_foot
```

目的：

- 验证多 C3 ESP-NOW 是否稳定
- 验证两个脚同时运动时 PC 端是否能区分
- 开始为左右 gait event 做准备

### Step 3：再上小腿和大腿

推荐顺序：

```text
left_foot/right_foot
-> left_shank/right_shank
-> left_thigh/right_thigh
-> pelvis
```

全套目标仍然是：

```text
6 x BMI160 + 1 x BMX055
```

### Step 4：最后再加 FSR

FSR 不是当前第一优先级。  
当前先用 IMU 验证事件检测，如果 heel-strike/toe-off 不稳定，再加：

```text
FSR -> ADS1115 -> C3 或 S3
```

FSR 的作用是给足底事件提供真值，不是替代 IMU 姿态链路。

## 10. 当前判断

当前方向是正确的：

- S3 放腰部作为 hub
- C3 放在腿部/脚部作为远端采集节点
- ESP-NOW 传 IMU raw
- PC 端做解析、保存、实时显示和后续算法

现在不建议回去继续做纯仿真。  
更应该继续把硬件链路扩到两个脚，再逐步上小腿和大腿。仿真可以作为算法参考，但当前项目的风险点已经转移到：

1. 无线多节点稳定性
2. IMU 安装方向标定
3. 无 FSR 条件下 gait event 检测
4. 节点温度和佩戴安全


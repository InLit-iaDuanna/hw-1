# 脑卒中步态检测系统

## 项目概述

基于6轴IMU传感器（加速度计+陀螺仪）和压力鞋垫的可穿戴步态检测系统，用于脑卒中患者康复评估和训练指导。

**核心理念：**
将V01-V24被动动态步行仿真研究成果（V10足踝滚动、V13.7能量效率、V11鲁棒性边界）作为**健康步态基准模型**，对比患者实测数据，量化康复评估指标。

## 系统架构

```
仿真研究层 (V01-V24)
    ↓ 提供健康步态特征库
传感器层 (ESP32 + IMU)
    ↓ 蓝牙/串口
数据采集层 (Python)
    ↓ 预处理
步态分析层 (复用common/)
    ↓ 特征提取 + 对比基准
诊断引擎 (规则+ML)
    ↓ 建议生成
用户界面 (PyQt5)
```

## 技术栈

### 硬件
- **主控**: ESP32-DevKitC
- **IMU**: MPU6050 × 4 (双侧大腿+小腿)
- **压力传感器**: FSR402 × 16 (双脚各8点)
- **电源**: 18650锂电 3.7V
- **通信**: 蓝牙SPP / USB串口

### 软件
- **嵌入式**: Arduino C++ (ESP32)
- **后端**: Python 3.10+
  - numpy, scipy (信号处理)
  - pandas (数据管理)
  - scikit-learn (异常检测)
- **前端**: PyQt5 / PySide6
- **健康基准来源**:
  - V10 足踝滚动仿生步态（步长、步频、ROM）
  - V13.7 能量效率基准（CoT=0.072）
  - V11 鲁棒性边界（地形容差28.6mm）
  - V17 状态估计算法（Kalman滤波）
- **复用分析模块**:
  - `common/poincare_analyzer.py` - 步态周期检测
  - `common/energy_metrics.py` - 能量效率计算
  - `common/phase_portrait_visualizer.py` - 相位可视化
  - `analysis/baseline_extractor.py` - 健康基准提取
  - `diagnosis/stroke_gait_classifier.py` - 步态分类器

## 目录结构

```
gait_medical_system/
├── hardware/               # ESP32固件代码
│   ├── esp32_main/         # Arduino项目
│   │   ├── esp32_main.ino  # 主程序
│   │   ├── imu_handler.h   # IMU驱动
│   │   └── pressure_handler.h # 压力传感器驱动
│   └── README.md
├── data_acquisition/       # 数据采集
│   ├── bluetooth_receiver.py  # 蓝牙数据接收
│   ├── serial_receiver.py     # 串口数据接收
│   └── data_logger.py         # 数据记录
├── analysis/               # 步态分析
│   ├── preprocess.py       # 信号预处理
│   ├── gait_cycle_detector.py  # 步态周期检测
│   ├── joint_angle_estimator.py # 关节角度估计
│   ├── symmetry_analyzer.py     # 对称性分析
│   └── pressure_analyzer.py     # 压力分布分析
├── diagnosis/              # 诊断引擎
│   ├── rule_engine.py      # 专家规则
│   ├── ml_detector.py      # 机器学习异常检测
│   └── recommendation.py   # 建议生成
├── gui/                    # 用户界面
│   ├── main_window.py      # 主窗口
│   ├── realtime_plot.py    # 实时波形
│   └── report_viewer.py    # 报告查看
├── models/                 # 训练好的ML模型
├── config/                 # 配置文件
│   ├── sensor_config.yaml  # 传感器参数
│   └── diagnosis_rules.yaml # 诊断规则
├── data/                   # 数据存储
│   ├── raw/                # 原始传感器数据
│   ├── processed/          # 处理后数据
│   └── reports/            # 诊断报告
├── tests/                  # 单元测试
└── docs/                   # 文档
    ├── hardware_setup.md   # 硬件组装指南
    ├── calibration.md      # 传感器标定
    └── user_manual.md      # 用户手册
```

## 快速开始

### 1. 硬件准备

参见 `docs/hardware_setup.md`

### 2. 环境配置

```powershell
cd D:\Dunna\Documents\hw-1\gait_medical_system

# 创建虚拟环境
python -m venv .venv-medical
.\.venv-medical\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 运行数据采集

```powershell
# 串口模式（开发调试）
python data_acquisition/serial_receiver.py --port COM5 --duration 60

# 蓝牙模式（实际使用）
python data_acquisition/bluetooth_receiver.py --device "GaitSensor_01"
```

### 4. 运行分析

```powershell
# 离线分析
python analysis/analyze_gait.py --input data/raw/patient_001.csv

# 实时监控（GUI）
python gui/main_window.py
```

## 核心功能

### 步态参数
- ✅ 步长 (stride length)
- ✅ 步频 (cadence)
- ✅ 步态周期 (gait cycle)
- ✅ 摆动/支撑相比例
- ✅ 关节角度范围 (ROM)

### 对称性分析
- ✅ Robinson对称性指数
- ✅ 左右步态参数对比
- ✅ 负重分布不对称

### 异常检测
- ✅ 偏瘫步态 (hemiplegic gait)
- ✅ 足下垂 (foot drop)
- ✅ 画圈步态 (circumduction)
- ✅ 膝过伸 (knee hyperextension)

### 康复建议
- ✅ 基于规则的建议生成
- ✅ 个性化训练方案
- ✅ 进度追踪

## 预期性能

| 指标 | 目标 |
|------|------|
| 步态周期检测准确率 | >95% |
| 对称性指数误差 | <5% |
| 实时处理延迟 | <100ms |
| 电池续航 | >4小时 |

## 开发进度

- [x] 项目结构创建
- [ ] ESP32固件开发
- [ ] 数据采集模块
- [ ] 信号预处理
- [ ] 步态分析算法
- [ ] 诊断规则引擎
- [ ] GUI界面
- [ ] 集成测试
- [ ] 用户测试

## 与V01-V24仿真研究的关系

本医疗检测系统是hw-1项目仿真研究的**应用转化**：

| 仿真版本 | 医疗应用 |
|---------|----------|
| V10 足踝滚动仿生步态 | 健康步态运动学基准（步长1.05m、步频60步/分、ROM标准值）|
| V13.7 摩擦补偿FSM | 能量效率目标（CoT=0.072），评估患者能耗 |
| V11 鲁棒性边界 | 跌倒风险评估（地形容差28.6mm、扰动容差17.1N）|
| V17 状态估计 | 传感器数据处理算法（编码器量化、Kalman滤波）|
| V12 稳定性分析 | Floquet稳定性指标，评估步态稳定域 |

**核心逻辑：**
- 仿真研究定义"什么是健康步态"（理论基准）
- 医疗系统测量"患者步态偏离多少"（实测对比）
- 量化偏差 → 康复建议

## 参考资料

- 健康基准来源: `v10_rolling_foot_biomimetic_gait/`, `v13_7_friction_compensation/`
- 传感器算法: `v17_state_estimation/`
- 公共分析工具: `common/`
- 鲁棒性边界: `v11_rugged_terrain_robustness/`

## License

MIT License

## 联系

项目目录: `D:\Dunna\Documents\hw-1\gait_medical_system`

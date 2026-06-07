# MuJoCo Passive Compass Gait

这是一个用于作业的真实被动动力学尝试：两条刚性腿通过髋部铰链连接，脚端与斜坡接触，系统不使用腿部电机或髋部平移电机，主要依靠重力、惯性和脚地碰撞运动。

## 安装

```powershell
cd D:\Dunna\Documents\hw-1
C:\Users\duanj\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv-mujoco
.\.venv-mujoco\Scripts\activate
pip install -r .\mujoco-compass-gait\requirements.txt
```

## 运行

```powershell
.\.venv-mujoco\Scripts\activate
cd D:\Dunna\Documents\hw-1\mujoco-compass-gait
python simulate_compass_gait.py --scan --duration 8
python analyze_results.py
python render_compass_gait.py
python view_compass_gait.py
python render_compass_gait_playback.py
```

说明：MuJoCo 官方 Viewer 没有中文语言包/中文补丁，界面菜单保持英文。中文说明、参数和报告文字已整理在本 README 与 `out/report_text.md` 中。

`view_compass_gait.py` 是稳定的多步混合步态回放，用于课堂展示“连续走几步”。`simulate_compass_gait.py` 和 `render_compass_gait.py` 保留真实 soft-contact 动力学尝试，用于说明真实被动动力学对接触和参数非常敏感。

## 输出

- `out/passive_compass_gait.mp4`：仿真视频
- `out/compass_gait_playback.mp4`：稳定多步回放视频
- `out/passive_compass_gait_data.csv`：状态数据
- `out/passive_compass_gait_report.png`：轨迹、角度、触地和相图报告
- `out/best_params.json`：最佳参数和验收结果
- `out/scan_results.csv`：参数扫描记录
- `out/report_text.md`：可直接放入作业报告的中文说明

## 最佳参数

当前扫描得到的最佳结果：

```text
坡度 slope_deg: 4.5 deg
髋部质量 hip_mass: 4.5 kg
脚端半径 foot_radius: 0.05 m
摩擦系数 friction: 0.9
关节阻尼 joint_damping: 0.012
初始髋部速度 hip_vx: 0.26 m/s
初始摆动腿角速度 swing_omega: 0.65 rad/s
```

验收结果：

```text
无 actuator: 是
有效左右交替触地: 6 次
前进距离: 约 1.27 m
仿真时长: 8 s
是否跌倒: 否
```

## 作业报告表述

本仿真采用 MuJoCo 建立指南针式双腿机构的被动动力学模型。模型由髋部质量体、左右两条刚性腿、脚端球形接触体和固定斜坡组成，不设置腿部驱动器或髋部平移驱动器。系统通过重力势能、脚地接触和碰撞损失之间的耦合形成步态，用于验证指南针式 MVE 机构在真实动力学条件下的支撑腿/摆动腿切换和周期步态趋势。

如果连续多步行走不稳定，报告中应说明：被动动态步态对斜坡角、髋部质量、脚端半径、摩擦和初始速度高度敏感，后续优化路径是扩大参数搜索并加入更接近论文模型的碰撞映射或圆弧足结构。

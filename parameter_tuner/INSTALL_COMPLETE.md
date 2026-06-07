# Parameter Tuner 安装完成报告

## 安装概览

✅ **安装状态**: 完成
📅 **安装时间**: 2026-06-04
🎯 **主要版本**: V13.7 (FSM + 摩擦补偿)
🔧 **Python 环境**: .venv-mujoco

---

## 已安装组件

### 核心模块
- ✅ `app.py` - Streamlit 主入口
- ✅ `version_adapter.py` - 版本适配器 (统一接口)
- ✅ `run_tuner.ps1` - 启动脚本

### 页面模块
- ✅ `pages/1_参数编辑器.py` - 交互式参数调整
- ✅ `pages/2_仿真运行器.py` - 一键运行仿真
- ✅ `pages/3_结果可视化.py` - 轨迹/角度/能量图表

### 依赖包
- ✅ streamlit >= 1.28.0
- ✅ plotly >= 5.17.0
- ✅ pyyaml >= 6.0
- ✅ pandas >= 2.0.0 (已有)
- ✅ numpy >= 1.24.0 (已有)

### 文档
- ✅ `README.md` - 项目说明
- ✅ `USAGE.md` - 详细使用指南
- ✅ `requirements.txt` - 依赖清单

---

## 快速启动

### 1. 启动应用

```powershell
cd D:\Dunna\Documents\hw-1
.\parameter_tuner\run_tuner.ps1
```

浏览器会自动打开 http://localhost:8501

### 2. 基本使用流程

1. **选择版本** - 侧边栏选择 V13.7
2. **编辑参数** - 调整髋/膝 Kp/Kd, 质量, 几何参数
3. **运行仿真** - 点击 "运行仿真" 按钮
4. **查看结果** - 轨迹图、关节角度、能量分析
5. **保存配置** - 导出 YAML 供后续使用

---

## 功能特性

### 参数编辑器
- 🎚️ **滑块调整**: 实时调整所有参数
- 📦 **参数分类**: 机械/控制/电机/仿真
- ⚡ **电机预设**: MX-64AR / Maxon EC-i / 理想电机
- 🔄 **摩擦补偿**: V13.7/V17 支持开关
- 💾 **导入/导出**: YAML 格式

### 仿真运行器
- ▶️ **一键运行**: 自动配置并执行仿真
- 📊 **实时进度**: 进度条 + 详细日志
- 📝 **参数摘要**: 运行前预览关键参数
- 📜 **历史记录**: 最近 10 次运行查询

### 结果可视化
- 🚶 **轨迹图**: X-Z 平面运动轨迹
- 🦵 **关节角度**: 髋/膝角度时间曲线
- ⚡ **能量分析**: 机械能/输入能量/效率
- 📈 **相位平面**: 角度 vs 角速度
- 📊 **统计信息**: 速度/距离/着地次数

---

## 支持的版本

| 版本 | 状态 | 特性 |
|------|------|------|
| **V13.7** | ✅ 完整 | FSM + 摩擦补偿 (主线) |
| **V10** | ✅ 完整 | 滚动足被动步态 |
| V13.6 | ⚠️ 基础 | 事件驱动FSM |
| V14 | ⚠️ 基础 | 被动摆臂 |
| V16 | ⚠️ 基础 | L1电机动力学 |
| V17 | ⚠️ 基础 | 状态估计 |

**说明**: 
- ✅ 完整 = 所有参数规格已定义
- ⚠️ 基础 = 可运行但参数界面简化

---

## 典型使用场景

### 场景 1: 快速调试 PD 增益

```
1. 进入参数编辑器
2. 调整 hip_kp: 30.0 → 35.0
3. 调整 hip_kd: 6.0 → 7.0
4. 设置 duration=5.0 (快速测试)
5. 运行仿真
6. 查看是否稳定行走
```

### 场景 2: 测试不同电机

```
1. 参数编辑器 → 电机参数
2. 选择 "Maxon EC-i 40"
3. 启用摩擦补偿
4. 运行仿真
5. 对比 MX-64AR 的结果
```

### 场景 3: 优化步态周期

```
1. 调整 gait_period: 0.80 → 0.70
2. 同步调整 swing_* 参数
3. 运行 duration=15.0 观察多步态
4. 在结果可视化查看关节轨迹周期性
```

---

## 项目目录结构

```
hw-1/
├── parameter_tuner/
│   ├── app.py                      # 主入口
│   ├── version_adapter.py          # 版本适配器
│   ├── run_tuner.ps1              # 启动脚本
│   ├── requirements.txt           # 依赖
│   ├── README.md                  # 项目说明
│   ├── USAGE.md                   # 使用指南
│   ├── pages/
│   │   ├── 1_参数编辑器.py
│   │   ├── 2_仿真运行器.py
│   │   └── 3_结果可视化.py
│   └── temp/                      # 临时文件（自动创建）
│
├── v13_7_friction_compensation/
│   ├── simulate_v13_7.py          # V13.7 仿真脚本
│   └── out/                       # 仿真结果输出
│
├── v10_rolling_foot_biomimetic_gait/
│   ├── simulate_rolling_foot_gait_v10.py
│   └── out/
│
└── .venv-mujoco/                  # Python 环境
    └── Scripts/
        ├── python.exe
        └── streamlit.exe
```

---

## 扩展指南

### 添加新版本支持

编辑 `version_adapter.py`:

```python
class V20Adapter(VersionAdapter):
    def __init__(self):
        super().__init__("V20")
    
    def get_default_params(self):
        from v20_xxx.simulate_v20 import V20Params
        return V20Params()
    
    def get_param_specs(self) -> dict:
        return {
            "mechanical": {...},
            "control": {...},
            "simulation": {...}
        }
    
    # ... 其他必需方法
```

注册到 `_ADAPTERS`:
```python
_ADAPTERS = {
    "V13.7": V137Adapter,
    "V10": V10Adapter,
    "V20": V20Adapter,  # 新增
}
```

### 自定义参数范围

修改 `get_param_specs()` 中的 min/max/step:

```python
"hip_kp": {
    "label": "髋关节 Kp",
    "min": 10.0,    # 修改
    "max": 80.0,    # 修改
    "step": 2.0,    # 修改
}
```

---

## 常见问题

### Q: 启动时端口被占用

```powershell
# 修改端口
.\.venv-mujoco\Scripts\streamlit.exe run parameter_tuner\app.py --server.port 8502
```

### Q: 仿真失败 "倾倒"

**原因**: 参数超出稳定域  
**解决**: 
1. 重置为默认值
2. 增加 hip_kp/kd
3. 减少初始速度

### Q: 如何批量运行

对于参数扫描，使用原始脚本更高效:
```powershell
.\.venv-mujoco\Scripts\python.exe v13_7_friction_compensation\scan_v13_7_tauC_verify.py
```

Tuner 适合交互式单点调试。

---

## 性能建议

1. **快速迭代**: duration=5.0, sample_hz=80
2. **精细测试**: duration=15.0, sample_hz=160
3. **定期清理**: 删除 `out/` 中的旧结果

---

## 技术架构

```
用户界面 (Streamlit)
    ↓
版本适配器 (VersionAdapter)
    ↓
参数对象 (V137Params, RollingFootParams, ...)
    ↓
仿真脚本 (simulate_v13_7.py, ...)
    ↓
MuJoCo 引擎
    ↓
结果文件 (CSV + JSON)
    ↓
可视化 (Plotly)
```

---

## 下一步

✅ **立即使用**: `.\parameter_tuner\run_tuner.ps1`

📚 **深入学习**: 阅读 `USAGE.md` 了解详细功能

🔧 **定制开发**: 参考 `version_adapter.py` 添加新版本

🐛 **问题反馈**: 项目根目录提交 Issue

---

**安装完成! 开始探索吧 🚀**

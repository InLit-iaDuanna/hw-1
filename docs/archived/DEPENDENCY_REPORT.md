# hw-1 项目依赖分析报告

分析日期: 1780629575.50228

## 统计信息

- requirements.txt 文件数量: 24
- 唯一依赖包数量: 23
- 代码中实际导入数量: 153
- 检测到的版本冲突: 6

## 发现的 requirements.txt 文件

- `auto_optimization\requirements.txt`
- `data_storage\requirements.txt`
- `data_versioning\requirements.txt`
- `parameter_explorer\requirements.txt`
- `parameter_tuner\requirements.txt`
- `requirements-core.txt`
- `requirements.txt`
- `v01_mujoco_compass_gait\requirements.txt`
- `v05_hybrid_compass_proof\requirements.txt`
- `v06_mve_gait_homework\requirements.txt`
- `v07_true_contact_exploration\requirements.txt`
- `v08_quasi_passive_assisted\requirements.txt`
- `v09_stable_biomimetic_gait\requirements.txt`
- `v10_rolling_foot_biomimetic_gait\requirements.txt`
- `v11_rugged_terrain_robustness\requirements.txt`
- `v12_energy_cot_analysis\requirements.txt`
- `v13_6_event_driven_fsm\requirements.txt`
- `v13_parameter_sensitivity_atlas\requirements.txt`
- `v14_passive_arms\requirements.txt`
- `v14c_arm_mass_lightening\requirements.txt`
- `v15_1_sea_direct\requirements.txt`
- `v15_2_strict_sea\requirements.txt`
- `v15_hip_sea_scaffold\requirements.txt`
- `v16_motor_dynamics\requirements.txt`

## 所有依赖及其版本

| 包名 | 版本规范 | 出现次数 |
|------|----------|----------|
| cma | >=3.2.2              # CMA-ES | 1 |
| deap | >=1.3.1             # 遗传算法 | 1 |
| imageio | , ==2.37.2, >=2.37.2 | 14 |
| imageio-ffmpeg | , ==0.6.0, >=0.6.0 | 13 |
| joblib | >=1.3.0 | 1 |
| matplotlib | , ==3.10.7, >=3.10.7, >=3.5.0       # 绘图, >=3.7.0 | 18 |
| mujoco | , ==3.3.7, >=2.3.0           # MuJoCo 仿真, >=3.0, >=3.1, >=3.3.7 | 19 |
| numpy | , ==2.2.6, >=1.21.0           # 数值计算, >=1.24.0, >=2.2.6 | 22 |
| pandas | >=2.0.0 | 3 |
| pillow |  | 9 |
| plotly | >=5.17.0 | 2 |
| pymoo | >=0.6.0 | 1 |
| pytest | >=7.4.0 | 1 |
| pytest-cov | >=4.1.0 | 1 |
| pytest-timeout | >=2.1.0  # 超时控制 | 1 |
| pytest-xdist | >=3.3.0  # 并行测试 | 1 |
| pyyaml | >=6.0, >=6.0             # YAML 配置解析 | 3 |
| salib | >=1.4.7 | 0 |
| scikit-learn | >=1.3.0 | 1 |
| scikit-optimize | >=0.9.0  # 贝叶斯优化 | 1 |
| scipy | , >=1.10.0 | 4 |
| seaborn | >=0.12.0 | 1 |
| streamlit | >=1.28.0 | 1 |

## 版本冲突

以下包存在多个不同的版本规范:

### pyyaml

- `>=6.0`
- `>=6.0             # YAML 配置解析`

**建议**: 统一使用 `>=6.0             # YAML 配置解析`

### numpy

- `==2.2.6`
- `>=1.21.0           # 数值计算`
- `>=1.24.0`
- `>=2.2.6`

**建议**: 统一使用 `==2.2.6`

### matplotlib

- `==3.10.7`
- `>=3.10.7`
- `>=3.5.0       # 绘图`
- `>=3.7.0`

**建议**: 统一使用 `==3.10.7`

### mujoco

- `==3.3.7`
- `>=2.3.0           # MuJoCo 仿真`
- `>=3.0`
- `>=3.1`
- `>=3.3.7`

**建议**: 统一使用 `==3.3.7`

### imageio

- `==2.37.2`
- `>=2.37.2`

**建议**: 统一使用 `==2.37.2`

### imageio-ffmpeg

- `==0.6.0`
- `>=0.6.0`

**建议**: 统一使用 `==0.6.0`

## 依赖分类

### 核心仿真依赖

- imageio==2.37.2
- imageio-ffmpeg==0.6.0
- mujoco==3.3.7
- numpy==2.2.6
- scipy>=1.10.0

### 可视化依赖

- matplotlib==3.10.7
- pillow
- plotly>=5.17.0
- seaborn>=0.12.0

### 数据分析依赖

- pandas>=2.0.0
- pyyaml>=6.0             # YAML 配置解析

### 优化工具依赖

- cma>=3.2.2              # CMA-ES
- deap>=1.3.1             # 遗传算法
- joblib>=1.3.0
- pymoo>=0.6.0
- salib>=1.4.7
- scikit-learn>=1.3.0
- scikit-optimize>=0.9.0  # 贝叶斯优化

### UI工具依赖

- streamlit>=1.28.0

### 开发/测试依赖

- pytest>=7.4.0
- pytest-cov>=4.1.0
- pytest-timeout>=2.1.0  # 超时控制
- pytest-xdist>=3.3.0  # 并行测试

### 未使用的依赖 (可能可以移除)

以下包在 requirements.txt 中声明，但在代码中未找到导入:

- pytest-cov
- pytest-timeout
- pytest-xdist
- scikit-optimize

### 外部系统依赖

以下依赖来自外部系统（不通过 pip 安装）:

- abaqus (Abaqus CAE)
- abaqusConstants (Abaqus CAE)
- odbAccess (Abaqus CAE)

## 优化建议

### 1. 统一版本管理

- 在项目根目录维护主 `requirements.txt`
- 子项目使用 `-r ../requirements.txt` 引用
- 仅在子项目有特殊需求时添加额外依赖

### 2. 分离依赖类型

- `requirements.txt`: 核心生产依赖
- `requirements-dev.txt`: 开发和测试工具
- `requirements-viz.txt`: 可视化工具（可选）
- `requirements-analysis.txt`: 数据分析工具（可选）
- `requirements-opt.txt`: 参数优化工具（可选）

### 3. 固定关键版本

建议为以下关键包固定版本（使用 `==`）:

- `mujoco`: 仿真引擎核心
- `numpy`: 数值计算基础
- 其他包可使用 `>=` 允许小版本更新

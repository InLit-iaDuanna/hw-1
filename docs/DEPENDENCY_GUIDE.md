# 依赖管理指南

> 合并自：DEPENDENCY_MANAGEMENT_GUIDE.md, DEPENDENCY_MIGRATION_GUIDE.md, DEPENDENCY_QUICK_REFERENCE.md, DEPENDENCY_REPORT.md

## 概述

本项目使用 Python 虚拟环境管理依赖，主要依赖包括：
- **MuJoCo** - 物理仿真引擎
- **NumPy/SciPy** - 数值计算
- **Matplotlib** - 可视化
- **OpenCV** - 视频渲染

## 快速开始

```powershell
# 激活虚拟环境
.\.venv-mujoco\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 验证安装
python -c "import mujoco; print(mujoco.__version__)"
```

## 核心依赖

### 仿真核心
- `mujoco >= 3.0.0` - 物理引擎
- `numpy >= 1.24.0` - 数组计算
- `scipy >= 1.10.0` - 科学计算

### 可视化
- `matplotlib >= 3.7.0` - 绘图
- `opencv-python >= 4.8.0` - 视频处理

### 分析工具
- `pandas >= 2.0.0` - 数据分析
- `scikit-learn >= 1.3.0` - 机器学习（参数优化）

### 开发工具
- `pytest >= 7.4.0` - 测试框架
- `black >= 23.0.0` - 代码格式化
- `ruff >= 0.1.0` - Linter

## 依赖更新

```powershell
# 检查过时的包
pip list --outdated

# 更新单个包
pip install --upgrade mujoco

# 更新所有包（谨慎）
pip install --upgrade -r requirements.txt
```

## 故障排查

### MuJoCo 安装失败

**问题：** `ERROR: Could not find a version that satisfies the requirement mujoco`

**解决：**
```powershell
# 确保 Python 版本 >= 3.8
python --version

# 升级 pip
python -m pip install --upgrade pip

# 重试安装
pip install mujoco
```

### OpenGL 错误

**问题：** `GLEW initialization error`

**解决：** 更新显卡驱动或使用 CPU 渲染模式

### 依赖冲突

**问题：** 版本冲突

**解决：**
```powershell
# 重建虚拟环境
Remove-Item -Recurse -Force .venv-mujoco
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\activate
pip install -r requirements.txt
```

## 参考资料

- [MuJoCo 官方文档](https://mujoco.readthedocs.io/)
- [requirements.txt](../requirements.txt) - 完整依赖列表

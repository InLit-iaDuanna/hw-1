# hw-1 依赖管理快速参考

## 快速安装

```powershell
# 标准安装（推荐）
pip install -r requirements-analysis.txt

# 最小安装
pip install -r requirements-core.txt

# 完整安装
pip install -r requirements-analysis.txt -r requirements-opt.txt -r requirements-ui.txt
```

## 依赖文件速查

| 文件 | 包含 | 用途 | 何时使用 |
|------|------|------|---------|
| `requirements-core.txt` | 5 个核心包 | 仿真运行 | 最小安装 |
| `requirements-viz.txt` | +4 个可视化包 | 图表生成 | 需要可视化 |
| `requirements-analysis.txt` | +2 个分析包 | 数据处理 | **推荐标准安装** |
| `requirements-opt.txt` | +7 个优化包 | 参数优化 | 使用 auto_optimization/ |
| `requirements-ui.txt` | +1 个 UI 包 | Web 界面 | 使用 parameter_tuner/ |
| `requirements-dev.txt` | +4 个测试包 | 开发测试 | 开发者 |

## 核心包版本

```
mujoco==3.3.7
numpy==2.2.6
matplotlib==3.10.7
scipy>=1.10.0
```

## 常用命令

```powershell
# 查看已安装包
pip list

# 检查版本
pip show numpy mujoco matplotlib

# 验证导入
python -c "import mujoco, numpy, matplotlib; print('OK')"

# 重新分析依赖
python analyze_dependencies.py

# 生成依赖图
python generate_dependency_graph.py
```

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| 导入 mujoco 失败 | 安装 VC++ Redistributable |
| numpy 版本冲突 | `pip install numpy==2.2.6` |
| 中文显示方框 | 设置 matplotlib 中文字体 |
| pytest 找不到模块 | 在项目根目录运行 |

## 文档路径

- 📘 完整指南: `DEPENDENCY_MANAGEMENT_GUIDE.md`
- 🔄 迁移指南: `DEPENDENCY_MIGRATION_GUIDE.md`
- 📊 分析报告: `DEPENDENCY_REPORT.md`
- 📝 完成总结: `DEPENDENCY_OPTIMIZATION_SUMMARY.md`
- 📈 依赖关系图: `DEPENDENCY_GRAPH.png`
- 📉 版本矩阵: `DEPENDENCY_VERSION_MATRIX.png`

## 使用场景

| 我要... | 安装命令 |
|---------|---------|
| 运行 v01-v16 仿真 | `pip install -r requirements-viz.txt` |
| 使用优化工具 | `pip install -r requirements-opt.txt` |
| 使用参数调节器 | `pip install -r requirements-ui.txt` |
| 进行数据分析 | `pip install -r requirements-analysis.txt` |
| 运行测试 | `pip install -r requirements-dev.txt` |

---

**提示**: 大多数用户推荐使用 `requirements-analysis.txt`

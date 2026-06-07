# hw-1 依赖管理迁移指南

## 概述

本项目已从单一 `requirements.txt` 迁移到模块化依赖管理结构。本指南帮助您平滑过渡到新的依赖管理方式。

## 变更内容

### 旧结构（已废弃）
```
hw-1/
├── requirements.txt                         # 混合所有依赖
├── v01_mujoco_compass_gait/requirements.txt # 各版本重复依赖
├── v05_hybrid_compass_proof/requirements.txt
├── ...（23 个 requirements.txt 文件）
```

### 新结构（推荐）
```
hw-1/
├── requirements.txt                  # 向后兼容入口（引用 analysis）
├── requirements-core.txt             # 核心仿真依赖
├── requirements-viz.txt              # 可视化依赖
├── requirements-analysis.txt         # 数据分析依赖
├── requirements-opt.txt              # 参数优化依赖
├── requirements-ui.txt               # UI 工具依赖
└── requirements-dev.txt              # 开发测试依赖
```

## 迁移步骤

### 步骤 1: 备份当前环境

```powershell
# 导出当前已安装的包
pip freeze > requirements-backup-$(Get-Date -Format 'yyyyMMdd').txt
```

### 步骤 2: 清理虚拟环境（可选但推荐）

```powershell
# 方案 A: 重建虚拟环境（推荐）
deactivate
Remove-Item -Recurse -Force .venv-mujoco
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1

# 方案 B: 清理现有环境
pip freeze | ForEach-Object { pip uninstall -y $_.Split('==')[0] }
```

### 步骤 3: 安装新依赖

根据您的使用场景选择：

#### 场景 A: 标准用户（仿真 + 可视化 + 分析）

```powershell
pip install -r requirements-analysis.txt
```

#### 场景 B: 最小安装（仅运行仿真）

```powershell
pip install -r requirements-core.txt
```

#### 场景 C: 完整安装（包含优化和 UI 工具）

```powershell
pip install -r requirements-analysis.txt
pip install -r requirements-opt.txt
pip install -r requirements-ui.txt
```

#### 场景 D: 开发者（包含测试工具）

```powershell
pip install -r requirements-analysis.txt
pip install -r requirements-dev.txt
```

### 步骤 4: 验证安装

```powershell
# 验证核心包
python -c "import mujoco; print(f'MuJoCo: {mujoco.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import matplotlib; print(f'Matplotlib: {matplotlib.__version__}')"

# 运行简单测试
python -c "import mujoco; import numpy as np; print('所有核心包导入成功')"
```

### 步骤 5: 测试现有脚本

```powershell
# 测试一个仿真脚本
cd v01_mujoco_compass_gait
python simulate_compass_gait.py

# 或测试其他版本
cd ..\v10_rolling_foot_biomimetic_gait
python simulate_rolling_foot_gait_v10.py
```

## 迁移对照表

### 使用场景映射

| 旧方式 | 新方式 | 说明 |
|--------|--------|------|
| `pip install -r requirements.txt` | `pip install -r requirements-analysis.txt` | 标准安装 |
| `pip install -r v01_*/requirements.txt` | `pip install -r requirements-viz.txt` | 版本脚本 |
| 手动安装 optimization 包 | `pip install -r requirements-opt.txt` | 优化工具 |
| 手动安装 streamlit | `pip install -r requirements-ui.txt` | UI 工具 |
| 手动安装 pytest | `pip install -r requirements-dev.txt` | 测试工具 |

### 依赖包映射

| 包名 | 旧版本规范 | 新版本规范 | 文件位置 |
|------|-----------|-----------|---------|
| mujoco | `>=3.3.7`, `>=3.0`, `==3.3.7` | `==3.3.7` | requirements-core.txt |
| numpy | `>=2.2.6`, `>=1.24.0`, `==2.2.6` | `==2.2.6` | requirements-core.txt |
| matplotlib | `>=3.10.7`, `>=3.7.0`, `==3.10.7` | `==3.10.7` | requirements-viz.txt |
| scipy | 无版本, `>=1.10.0` | `>=1.10.0` | requirements-core.txt |
| pandas | `>=2.0.0` | `>=2.0.0` | requirements-analysis.txt |
| streamlit | `>=1.28.0` | `>=1.28.0` | requirements-ui.txt |
| pytest | `>=7.4.0` | `>=7.4.0` | requirements-dev.txt |

## 常见问题

### Q1: 是否需要删除子目录的 requirements.txt？

**A**: 不需要删除，但不应再使用它们。这些文件保留以供参考，但已过时。

```powershell
# ❌ 不推荐：在子目录安装
cd v01_mujoco_compass_gait
pip install -r requirements.txt

# ✅ 推荐：在项目根目录统一安装
cd D:\Dunna\Documents\hw-1
pip install -r requirements-analysis.txt
```

### Q2: 旧的 requirements.txt 还能用吗？

**A**: 可以，但它现在只是引用 `requirements-analysis.txt` 的入口，为了向后兼容保留。

```powershell
# 以下两者等效
pip install -r requirements.txt
pip install -r requirements-analysis.txt
```

### Q3: 如何知道我需要哪些依赖文件？

**A**: 根据使用的功能决定：

| 你需要... | 安装文件 |
|----------|---------|
| 仅运行仿真（无图表） | requirements-core.txt |
| 运行仿真 + 查看图表 | requirements-viz.txt |
| 运行仿真 + 图表 + 数据处理 | requirements-analysis.txt |
| 使用 auto_optimization/ | requirements-opt.txt |
| 使用 parameter_tuner/ | requirements-ui.txt |
| 运行测试套件 | requirements-dev.txt |

**大多数用户推荐**: `requirements-analysis.txt`

### Q4: 安装后包版本不一致怎么办？

**A**: 检查并统一版本：

```powershell
# 检查已安装版本
pip show numpy mujoco matplotlib

# 如果版本不对，强制安装指定版本
pip install --force-reinstall numpy==2.2.6 mujoco==3.3.7
```

### Q5: 能否混合使用多个依赖文件？

**A**: 可以，依赖文件之间有引用关系：

```powershell
# 这是安全的（opt 已引用 analysis）
pip install -r requirements-opt.txt

# 这也是安全的（显式安装多个）
pip install -r requirements-analysis.txt -r requirements-ui.txt
```

### Q6: 如何在 CI/CD 中使用新依赖？

**A**: 根据 CI 任务选择：

```yaml
# GitHub Actions 示例
jobs:
  test:
    steps:
      - name: Install dependencies
        run: |
          pip install -r requirements-analysis.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest

  simulation:
    steps:
      - name: Install minimal dependencies
        run: pip install -r requirements-core.txt
      - name: Run simulation
        run: python simulate.py
```

## 回滚方案

如果新依赖结构出现问题，可以回滚：

```powershell
# 方案 1: 使用备份恢复
pip install -r requirements-backup-yyyyMMdd.txt

# 方案 2: 使用旧的统一依赖（如果保留了旧版本）
git checkout HEAD~1 requirements.txt
pip install -r requirements.txt
```

## 优势对比

### 旧结构的问题

- ❌ 23 个 requirements.txt 文件，版本不一致
- ❌ 每次安装所有依赖，包括不需要的
- ❌ 版本冲突频繁（numpy, mujoco, matplotlib）
- ❌ 无法按需安装（优化工具、UI 工具）
- ❌ 难以维护和更新

### 新结构的优势

- ✅ 统一版本管理，无冲突
- ✅ 按需安装，最小化依赖
- ✅ 层级清晰，易于理解
- ✅ 便于维护和更新
- ✅ 文档完善（DEPENDENCY_MANAGEMENT_GUIDE.md）

## 检查清单

迁移完成后，请检查以下项目：

- [ ] 核心依赖已安装（`python -c "import mujoco, numpy, scipy"`）
- [ ] 可视化工具正常（`python -c "import matplotlib.pyplot as plt"`）
- [ ] 至少一个仿真脚本运行成功
- [ ] 如使用优化工具，已安装 requirements-opt.txt
- [ ] 如使用 parameter_tuner，已安装 requirements-ui.txt
- [ ] 开发环境已安装 requirements-dev.txt
- [ ] 删除或备份 requirements-backup 文件

## 后续维护

### 添加新依赖

```powershell
# 1. 确定依赖类别
# 2. 编辑对应的 requirements-*.txt 文件
# 3. 重新分析
python analyze_dependencies.py

# 4. 更新文档
# 5. 提交到版本控制
git add requirements-*.txt DEPENDENCY_REPORT.md
git commit -m "chore: add new dependency"
```

### 定期审计

```powershell
# 每月运行依赖分析
python analyze_dependencies.py

# 检查过期包
pip list --outdated

# 检查安全漏洞（如已安装 safety）
safety check
```

## 获取帮助

- 📄 详细文档: [DEPENDENCY_MANAGEMENT_GUIDE.md](DEPENDENCY_MANAGEMENT_GUIDE.md)
- 📊 依赖分析: [DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md)
- 🔧 分析工具: `python analyze_dependencies.py`
- 📈 依赖关系图: [DEPENDENCY_GRAPH.png](DEPENDENCY_GRAPH.png)

---

**迁移日期**: 2026-06-05  
**维护者**: hw-1 项目组

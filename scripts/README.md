# hw-1 自动化脚本文档

本目录包含用于 hw-1 项目的自动化脚本，用于批量运行、动画生成、文档更新和项目健康检查。

---

## 📋 脚本清单

| 脚本 | 用途 | 耗时 | 频率 |
|------|------|------|------|
| `batch_run_all_versions.ps1` | 批量运行所有版本的仿真 | 5-20分钟 | 按需 |
| `generate_all_animations.ps1` | 批量生成动画视频 | 10-30分钟 | 按需 |
| `update_all_docs.ps1` | 更新所有文档和报告 | 2-5分钟 | 每周 |
| `check_project_health.ps1` | 项目健康检查 | 1-5分钟 | 每天 |
| `quick_demo.ps1` | 快速演示关键版本 | 3-10分钟 | 演示前 |
| `search_kb.ps1` | 知识库搜索 | <1分钟 | 按需 |

---

## 🚀 快速开始

### 1. 批量运行所有版本

快速测试所有版本是否正常工作：

```powershell
# 快速模式：只运行核心版本 (V10, V13.6, V13.7, V17)
.\scripts\batch_run_all_versions.ps1 -quick

# 运行所有版本
.\scripts\batch_run_all_versions.ps1

# 运行指定版本
.\scripts\batch_run_all_versions.ps1 -versions v10,v13.7,v17

# 并行执行（实验性）
.\scripts\batch_run_all_versions.ps1 -parallel

# 自定义仿真时长
.\scripts\batch_run_all_versions.ps1 -duration 10.0
```

**输出**:
- `batch_results/batch_run_YYYYMMDD_HHMMSS.log` - 执行日志
- `batch_results/batch_run_YYYYMMDD_HHMMSS_summary.json` - 结果摘要
- `batch_results/<version>_YYYYMMDD_HHMMSS.json` - 各版本结果

**使用场景**:
- ✅ 回归测试：代码修改后验证所有版本
- ✅ 性能对比：收集跨版本性能数据
- ✅ 参数验证：验证新参数在所有版本上的表现

---

### 2. 生成动画视频

为演示和汇报生成高质量动画：

```powershell
# 生成所有版本的动画（标准质量）
.\scripts\generate_all_animations.ps1 -withVideo

# 高质量模式（1920x1080 @ 60fps）
.\scripts\generate_all_animations.ps1 -withVideo -highQuality

# 生成指定版本
.\scripts\generate_all_animations.ps1 -versions v10,v17 -withVideo

# 自定义分辨率
.\scripts\generate_all_animations.ps1 -withVideo -width 1280 -height 720 -fps 30
```

**输出**:
- `animations/<version>_YYYYMMDD_HHMMSS.mp4` - 动画视频
- `animations/generation_YYYYMMDD_HHMMSS.log` - 生成日志

**使用场景**:
- 🎬 论文和报告：生成演示视频
- 🎬 技术汇报：展示关键版本效果
- 🎬 调试可视化：观察步态细节

**注意**: 视频生成需要较长时间和大量存储空间（每个视频 50-200 MB）

---

### 3. 更新文档和报告

自动更新项目文档：

```powershell
# 完整更新
.\scripts\update_all_docs.ps1

# 跳过基准测试（节省时间）
.\scripts\update_all_docs.ps1 -skipBenchmarks

# 跳过跨版本分析
.\scripts\update_all_docs.ps1 -skipAnalysis

# 强制更新所有文档
.\scripts\update_all_docs.ps1 -force
```

**更新内容**:
1. 基准测试报告 (`benchmarks/results/`)
2. 跨版本分析 (`cross_version_analysis/reports/`)
3. 版本文档检查 (各 `v**/README.md`)
4. 主文档检查 (`VERSIONS.md`, `PROJECT_PROGRESS.md`)
5. 数据存储统计 (`data_storage/`)
6. 文档索引生成 (`docs/DOCUMENTATION_INDEX.md`)

**使用场景**:
- 📝 定期维护：每周运行一次
- 📝 重大更新后：新版本完成后更新文档
- 📝 演示准备：确保所有报告最新

---

### 4. 项目健康检查

检查项目整体状态：

```powershell
# 快速检查
.\scripts\check_project_health.ps1 -quick

# 完整检查（运行所有测试）
.\scripts\check_project_health.ps1 -full

# 自动修复问题
.\scripts\check_project_health.ps1 -fix
```

**检查项**:
1. ✅ 环境配置（Python 虚拟环境、依赖）
2. ✅ 测试覆盖率（pytest 测试套件）
3. ✅ 文档完整性（README、版本文档）
4. ✅ 代码质量（linter 配置、代码规范）
5. ✅ 数据完整性（数据库、版本数据）
6. ✅ 版本输出数据（核心版本是否有数据）
7. ✅ 自动化脚本（脚本完整性）

**健康评分**:
- **80-100%**: 优秀 ✓
- **60-79%**: 良好 ⚠
- **40-59%**: 需要改进 ⚠⚠
- **0-39%**: 需要紧急修复 ✗

**输出**:
- `health_check_YYYYMMDD_HHMMSS.txt` - 详细报告

**使用场景**:
- 🏥 每日检查：确保项目处于健康状态
- 🏥 代码审查：提交前检查
- 🏥 问题排查：识别潜在问题

---

### 5. 快速演示

运行关键版本进行快速演示：

```powershell
# 标准演示（V10, V13.7, V17）
.\scripts\quick_demo.ps1

# 完整演示（所有版本）
.\scripts\quick_demo.ps1 -fullDemo

# 生成演示视频
.\scripts\quick_demo.ps1 -withVideo

# 完整演示 + 视频
.\scripts\quick_demo.ps1 -fullDemo -withVideo
```

**演示版本**:
- **V10**: 足踝滚动基线（PD 控制）
- **V13.7**: 摩擦补偿（FSM + 前馈补偿）
- **V17**: 状态估计（传感器噪声 + Kalman 滤波）

**输出**:
- `demo_output/<version>_demo_YYYYMMDD_HHMMSS.json` - 仿真结果
- `demo_output/<version>_demo_YYYYMMDD_HHMMSS.mp4` - 演示视频（如果使用 -withVideo）

**使用场景**:
- 🎯 技术演示：向导师或同事展示项目
- 🎯 功能验证：快速验证关键功能
- 🎯 新人入门：帮助新成员理解项目

---

### 6. 知识库搜索

在知识库中搜索关键词：

```powershell
# 基本搜索
.\scripts\search_kb.ps1 -keyword "FSM"

# 搜索并显示上下文（前后各2行）
.\scripts\search_kb.ps1 -keyword "friction" -context 2

# 区分大小写
.\scripts\search_kb.ps1 -keyword "CoT" -caseSensitive
```

**搜索范围**: `knowledge_base/*.md`

**使用场景**:
- 🔍 快速查找：在知识库中查找技术细节
- 🔍 概念查询：了解特定概念的定义
- 🔍 故障排查：查找已知问题的解决方案

---

## 📊 典型工作流

### 工作流 1: 开发新版本后

```powershell
# 1. 运行新版本验证
cd D:\Dunna\Documents\hw-1\v<new_version>
python simulate_v<new_version>.py

# 2. 批量运行所有版本进行回归测试
.\scripts\batch_run_all_versions.ps1 -quick

# 3. 更新文档
.\scripts\update_all_docs.ps1

# 4. 健康检查
.\scripts\check_project_health.ps1
```

---

### 工作流 2: 准备演示或汇报

```powershell
# 1. 生成演示动画
.\scripts\generate_all_animations.ps1 -versions v10,v13.7,v17 -withVideo -highQuality

# 2. 运行快速演示验证
.\scripts\quick_demo.ps1 -withVideo

# 3. 更新所有文档和报告
.\scripts\update_all_docs.ps1 -force

# 4. 检查项目健康
.\scripts\check_project_health.ps1 -full
```

---

### 工作流 3: 每周维护

```powershell
# 1. 完整健康检查
.\scripts\check_project_health.ps1 -full

# 2. 更新文档
.\scripts\update_all_docs.ps1

# 3. 运行基准测试
cd benchmarks
python benchmark_runner.py

# 4. 清理临时文件（可选）
.\cleanup_temp.ps1
```

---

### 工作流 4: 参数调优

```powershell
# 1. 运行参数扫描（使用并行化）
cd v10_rolling_foot_biomimetic_gait
python scan_rolling_foot_params_v10_parallel.py

# 2. 分析结果并选择最佳参数
python analyze_scan_results.py

# 3. 验证最佳参数
.\scripts\batch_run_all_versions.ps1 -versions v10 -duration 20.0

# 4. 生成演示视频
.\scripts\generate_all_animations.ps1 -versions v10 -withVideo
```

---

## ⚙️ 配置和自定义

### 修改默认路径

所有脚本默认使用以下路径：

```powershell
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"
```

如需修改，编辑各脚本的顶部配置变量。

### 添加新版本

在 `batch_run_all_versions.ps1` 中添加新版本：

```powershell
$allVersions = @{
    "v<new>" = @{
        dir = "v<new>_<name>"
        script = "simulate_v<new>.py"
        description = "版本描述"
        priority = 1  # 1=核心版本, 2=次要版本
    }
}
```

### 调整性能参数

根据机器性能调整并行度：

```powershell
# batch_run_all_versions.ps1
$jobs = Start-Job -ThrottleLimit 4  # 限制并发数

# 或在 Python 中
Parallel(n_jobs=4)  # 使用 4 个核心
```

---

## 🐛 故障排查

### 问题 1: 脚本执行策略错误

**错误**: `无法加载文件 *.ps1，因为在此系统上禁止运行脚本`

**解决**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 问题 2: Python 虚拟环境不存在

**错误**: `Python 虚拟环境不存在: .venv-mujoco`

**解决**:
```powershell
cd D:\Dunna\Documents\hw-1
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### 问题 3: 脚本找不到版本

**错误**: `脚本不存在: v10_rolling_foot_biomimetic_gait/simulate_*.py`

**解决**: 检查版本目录和脚本名称是否正确：
```powershell
ls D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\*.py
```

---

### 问题 4: 内存不足

**错误**: 批量运行时系统内存不足

**解决**:
1. 使用 `-quick` 模式只运行核心版本
2. 减少并行度：不使用 `-parallel` 标志
3. 降低仿真时长：`-duration 3.0`
4. 分批运行：`-versions v10,v13.7`

---

### 问题 5: 视频生成失败

**错误**: 动画生成时 FFmpeg 或渲染错误

**解决**:
1. 确保安装了 `imageio-ffmpeg`: `pip install imageio-ffmpeg`
2. 检查 MuJoCo 渲染器：确保使用 `egl` 或 `osmesa`
3. 降低分辨率：`-width 640 -height 480`
4. 检查磁盘空间：视频生成需要大量空间

---

## 📚 相关文档

- [PERFORMANCE_REPORT.md](../PERFORMANCE_REPORT.md) - 性能分析报告
- [OPTIMIZATION_COMPLETE.md](../OPTIMIZATION_COMPLETE.md) - 优化完成报告
- [TOOLS_CHEATSHEET.md](../TOOLS_CHEATSHEET.md) - 工具速查表
- [benchmarks/README.md](../benchmarks/README.md) - 基准测试框架
- [advanced_profiling/README.md](../advanced_profiling/README.md) - 高级性能分析

---

## 🔧 维护和扩展

### 添加新脚本

创建新脚本时，请遵循以下规范：

1. **文件命名**: 使用下划线分隔的小写名称（例如 `new_automation_script.ps1`）
2. **参数处理**: 使用 `param()` 定义参数，提供默认值和帮助文本
3. **日志记录**: 实现 `Write-Log` 函数，输出到控制台和文件
4. **错误处理**: 使用 `try-catch`，`$ErrorActionPreference = "Continue"`
5. **输出格式**: 使用彩色输出区分状态（Green=成功，Red=失败，Yellow=警告）
6. **文档**: 在本 README 中添加使用说明

### 脚本模板

```powershell
# Script Name
# Script Description

param(
    [Parameter(Mandatory=$false)]
    [string]$param1 = "default_value"
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"

function Write-Log {
    param([string]$message, [string]$level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$level] $message"
}

# 主逻辑
Write-Log "脚本开始" "INFO"

try {
    # ... 实现逻辑 ...
    Write-Log "脚本完成" "SUCCESS"
}
catch {
    Write-Log "脚本失败: $_" "ERROR"
}
```

---

## 📞 联系和反馈

如有问题或建议，请参考：
- 项目主 README: `D:\Dunna\Documents\hw-1\README.md`
- 快速入门指南: `D:\Dunna\Documents\hw-1\QUICKSTART.md`
- 工具速查表: `D:\Dunna\Documents\hw-1\TOOLS_CHEATSHEET.md`

---

**文档版本**: 1.0  
**最后更新**: 2026-06-05  
**维护者**: hw-1 项目组

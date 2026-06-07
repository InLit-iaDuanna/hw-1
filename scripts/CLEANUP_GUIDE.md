# hw-1 项目清理脚本使用指南

本指南说明如何使用 hw-1 项目的磁盘清理和分析工具。

---

## 📋 脚本总览

| 脚本 | 用途 | 风险级别 |
|------|------|---------|
| `cleanup_temp_files.ps1` | 清理缓存和临时文件 | 🟢 安全 |
| `deep_cleanup.ps1` | 清理大型可重建文件 | 🟡 谨慎 |
| `analyze_disk_usage.ps1` | 分析磁盘使用情况 | 🟢 安全（只读） |

---

## 🧹 1. 安全清理（推荐定期执行）

### cleanup_temp_files.ps1

**清理内容**:
- Python 缓存 (__pycache__, *.pyc) - ~173 MB
- 测试缓存 (.pytest_cache, .mypy_cache, .ruff_cache) - ~14 MB
- 覆盖率报告 (htmlcov) - ~1 MB
- 临时文件 (*.tmp, *.log)

**特点**: 所有文件会自动重建，零风险

### 使用方法

```powershell
# 1. 预览模式（推荐首次使用）
.\scripts\cleanup_temp_files.ps1 -DryRun

# 2. 实际执行清理
.\scripts\cleanup_temp_files.ps1

# 3. 详细输出模式
.\scripts\cleanup_temp_files.ps1 -Verbose

# 4. 跳过特定类型
.\scripts\cleanup_temp_files.ps1 -SkipPycache      # 跳过 Python 缓存
.\scripts\cleanup_temp_files.ps1 -SkipTestCache    # 跳过测试缓存
.\scripts\cleanup_temp_files.ps1 -SkipModelCache   # 跳过模型缓存
```

### 预期效果

- 节省磁盘空间: ~188 MB
- 执行时间: < 30 秒
- 风险: 无

---

## 🗑️ 2. 深度清理（仅在磁盘空间紧张时使用）

### deep_cleanup.ps1

**清理内容**:
- Node.js 模块 (node_modules) - ~599 MB
- Python 虚拟环境 (.venv-mujoco, .venv-codex) - ~1,092 MB
- 离线轮子包 (wheelhouse) - ~5 MB

**特点**: 可重建，但需要重新下载和安装

### 使用方法

```powershell
# 1. 预览模式（强烈推荐）
.\scripts\deep_cleanup.ps1 -DryRun

# 2. 交互式确认删除
.\scripts\deep_cleanup.ps1 -Confirm

# 3. 仅删除 node_modules
.\scripts\deep_cleanup.ps1 -NodeModulesOnly -Confirm

# 4. 仅删除虚拟环境
.\scripts\deep_cleanup.ps1 -VenvOnly -Confirm

# 5. 仅删除 wheelhouse
.\scripts\deep_cleanup.ps1 -WheelhouseOnly -Confirm

# 6. 全部删除（跳过确认，危险！）
.\scripts\deep_cleanup.ps1 -Confirm -Force
```

### 恢复方法

删除后可以通过以下命令恢复：

```powershell
# 恢复 Node.js 依赖
cd compass-gait-remotion
npm install

# 恢复 Python 虚拟环境
.\scripts\setup_env.ps1
# 或手动：
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt

# 恢复 wheelhouse
pip download -r requirements.txt -d wheelhouse
```

### 预期效果

- 节省磁盘空间: 599 MB (node_modules) + 1,092 MB (venv) = ~1.7 GB
- 重建时间: 5-15 分钟
- 风险: 低（需要联网重建）

---

## 📊 3. 磁盘分析（诊断工具）

### analyze_disk_usage.ps1

**功能**:
- 分析目录大小和文件分布
- 识别大文件
- 查找重复文件
- 统计缓存占用
- 分析版本目录

**特点**: 只读操作，不删除任何文件

### 使用方法

```powershell
# 1. 基础分析
.\scripts\analyze_disk_usage.ps1

# 2. 分析版本目录（v01-v25）
.\scripts\analyze_disk_usage.ps1 -AnalyzeVersions

# 3. 查找大文件（>10MB）
.\scripts\analyze_disk_usage.ps1 -FindLargeFiles

# 4. 查找大文件（自定义大小）
.\scripts\analyze_disk_usage.ps1 -FindLargeFiles -MinSizeMB 5

# 5. 查找重复文件（慢，可能需要几分钟）
.\scripts\analyze_disk_usage.ps1 -FindDuplicates

# 6. 完整分析并导出 CSV
.\scripts\analyze_disk_usage.ps1 -AnalyzeVersions -FindLargeFiles -FindDuplicates -ExportCSV

# 7. 快速分析版本目录
.\scripts\analyze_disk_usage.ps1 -AnalyzeVersions -ExportCSV
```

### 输出文件

启用 `-ExportCSV` 后会生成：

- `version_analysis.csv` - 版本目录分析
- `large_files.csv` - 大文件列表
- `duplicate_files.csv` - 重复文件列表

---

## 📅 推荐清理计划

### 每周维护

```powershell
# 快速缓存清理
.\scripts\cleanup_temp_files.ps1
```

**预期**: 节省 50-200 MB

### 每月维护

```powershell
# 1. 分析磁盘使用
.\scripts\analyze_disk_usage.ps1 -AnalyzeVersions

# 2. 清理缓存
.\scripts\cleanup_temp_files.ps1

# 3. 根据分析结果决定是否深度清理
```

### 磁盘空间紧急时

```powershell
# 1. 先清理缓存（安全）
.\scripts\cleanup_temp_files.ps1

# 2. 如果还不够，清理 node_modules
.\scripts\deep_cleanup.ps1 -NodeModulesOnly -Confirm

# 3. 最后手段：清理虚拟环境
.\scripts\deep_cleanup.ps1 -VenvOnly -Confirm
```

---

## ⚠️ 注意事项

### 不要删除的文件/目录

1. **ABAQUS 仿真结果** (`fea_heel_strike/out/*.odb`)
   - 运行成本高，难以重现
   - 大小: ~38 MB

2. **论文图表** (`paper_figures/`)
   - 已用于发表的图表
   - 大小: ~9 MB

3. **演示文稿** (`presentations/`)
   - 答辩和会议材料
   - 大小: ~12 MB

4. **最新版本输出** (v19-v25)
   - 当前研究的关键数据
   - 需要手动评估

### 常见问题

**Q: 删除 __pycache__ 会影响性能吗？**  
A: 会略微影响首次运行速度（需要重新编译），但影响很小（< 1 秒）。

**Q: 删除虚拟环境后如何恢复？**  
A: 运行 `.\scripts\setup_env.ps1` 或手动创建虚拟环境并安装依赖。

**Q: node_modules 可以安全删除吗？**  
A: 可以，运行 `npm install` 即可恢复，但需要 2-5 分钟和网络连接。

**Q: 如何查看当前磁盘占用？**  
A: 运行 `.\scripts\analyze_disk_usage.ps1` 查看详细分析。

**Q: 清理脚本会删除源代码吗？**  
A: 不会。所有脚本只删除缓存、依赖包和可重建的文件，不会触碰源代码。

---

## 🔧 故障排除

### 权限错误

如果遇到权限错误：

```powershell
# 以管理员身份运行 PowerShell
# 或使用 -Force 参数（谨慎）
.\scripts\cleanup_temp_files.ps1 -Force
```

### 脚本执行被阻止

```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 然后运行脚本
.\scripts\cleanup_temp_files.ps1
```

### 删除失败

某些文件可能被占用，尝试：

1. 关闭 IDE (VS Code, PyCharm)
2. 停止 Python 进程
3. 关闭 Node.js 开发服务器
4. 重试删除

---

## 📈 磁盘优化建议

### 当前状态（2026-06-05）

- **总大小**: 1,982.93 MB (~1.94 GB)
- **可安全清理**: ~188 MB (缓存)
- **可谨慎清理**: ~1,697 MB (依赖包)
- **关键数据**: ~98 MB (仿真结果、论文图表)

### 优化目标

| 目标 | 操作 | 预期大小 |
|------|------|---------|
| 🎯 轻量级 | 清理所有可重建文件 | ~300 MB |
| 🎯 标准 | 保留虚拟环境，清理缓存 | ~1.8 GB |
| 🎯 完整 | 保持现状 | ~2.0 GB |

---

## 📚 相关文档

- **磁盘分析报告**: `DISK_ANALYSIS_REPORT.md`
- **项目文档**: `README.md`
- **环境搭建**: `scripts/setup_env.ps1`

---

**最后更新**: 2026-06-05  
**作者**: Claude Code Analysis Agent

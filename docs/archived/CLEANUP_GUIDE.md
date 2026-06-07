# hw-1 项目清理快速指南

本指南提供三种清理级别，按需选择。

## 📋 清理级别

### Level 1: 安全清理（推荐，零风险）

**清理内容**：Python 缓存、测试缓存、临时文件
**预期收益**：~170 MB
**执行时间**：< 1 分钟
**风险级别**：✅ 无风险

```powershell
# 预览
.\cleanup_temp.ps1 -DryRun

# 执行
.\cleanup_temp.ps1
```

### Level 2: 版本归档（需确认，低风险）

**清理内容**：失败探索版本、refactored 版本、旧环境
**预期收益**：项目结构更清晰，便于导航
**执行时间**：2-3 分钟
**风险级别**：⚠️ 低风险（可恢复）

```powershell
# 预览
.\archive_old_versions.ps1 -DryRun

# 执行
.\archive_old_versions.ps1
```

**归档清单**：
- V7, V18-V20（失败探索）
- V13.6/V13.7/V16 refactored 版本
- .venv-codex 旧环境
- 中期汇报 PPT

### Level 3: 数据压缩（可选，需交互确认）

**清理内容**：大于 1MB 的 CSV 扫描数据
**预期收益**：80-100 MB（压缩后）
**执行时间**：5-10 分钟
**风险级别**：⚠️ 中风险（数据访问变慢）

```powershell
# 预览
.\compress_large_data.ps1 -DryRun

# 执行（压缩 > 1MB 的 CSV）
.\compress_large_data.ps1

# 自定义阈值（压缩 > 2MB 的 CSV）
.\compress_large_data.ps1 -Threshold 2.0
```

## 🎯 推荐执行流程

### 快速清理（5 分钟）

```powershell
# 1. 清理临时文件
.\cleanup_temp.ps1

# 2. 检查 git 状态
git status

# 完成！
```

### 完整清理（15 分钟）

```powershell
# 1. 清理临时文件
.\cleanup_temp.ps1

# 2. 归档旧版本
.\archive_old_versions.ps1

# 3. 删除他人文件（手动确认）
Remove-Item "2024211325王瀚乔第十三周.zip" -ErrorAction SilentlyContinue

# 4. 压缩大型数据（可选）
.\compress_large_data.ps1

# 5. 检查结果
git status
```

## 📊 预期效果

| 操作 | 空间节省 | 时间成本 | 风险 |
|------|---------|---------|------|
| 安全清理 | ~170 MB | 1 分钟 | 无 |
| 版本归档 | 结构优化 | 3 分钟 | 低 |
| 数据压缩 | ~90 MB | 10 分钟 | 中 |
| **总计** | **~260 MB** | **15 分钟** | **低** |

## ❓ 常见问题

### Q: 清理后能恢复吗？
A: 
- 临时文件（Level 1）：可重新生成，无需恢复
- 归档文件（Level 2）：在 `archives/` 目录，随时可移回
- 压缩数据（Level 3）：解压 ZIP 即可恢复

### Q: 会影响 git 历史吗？
A: 不会。所有操作仅影响工作目录，不修改 git 历史。

### Q: 哪些文件不会被清理？
A: 
- 所有源代码（.py, .m）
- 所有模型文件（.xml）
- 核心数据文件（< 1MB CSV, .mat）
- 视频和图像（.mp4, .png）
- 文档（.md, README）
- 配置文件（.toml, .yaml）

### Q: 清理后项目还能运行吗？
A: 是的。所有清理操作不影响代码运行，Python 会自动重新生成缓存。

### Q: 我只想清理某一个版本的数据？
A: 手动操作：
```powershell
# 清理单个版本的 __pycache__
Remove-Item "D:\Dunna\Documents\hw-1\v13_7_floquet_analysis\__pycache__" -Recurse -Force

# 压缩单个版本的 CSV
Compress-Archive -Path "D:\Dunna\Documents\hw-1\v13_7_floquet_analysis\out\*.csv" `
                 -DestinationPath "v13_7_data.zip"
```

## 🔧 维护建议

### 每周例行（1 分钟）
```powershell
.\cleanup_temp.ps1
```

### 版本完成后（3 分钟）
- 如果版本被否定或替代，运行 `.\archive_old_versions.ps1`
- 更新 `VERSIONS.md` 标注归档位置

### 项目结束前（15 分钟）
- 运行完整清理流程
- 压缩所有大型数据
- 创建项目归档备份

## 🚨 注意事项

**不要手动删除这些目录**：
- `.venv-mujoco` - 当前使用的虚拟环境
- `common/` - 公共工具库
- `v05/` ~ `v17/` - 主线版本（V5-V17）
- `v22/` ~ `v24/` - 设计文档
- `out/` - 共享输出目录
- `.git/` - Git 仓库

**可以安全删除**（但建议先归档）：
- `.venv-codex` - 旧环境
- `2024211325王瀚乔第十三周.zip` - 他人文件
- `htmlcov/` - 覆盖率报告（可重新生成）

## 📚 完整文档

详细分析和策略请参阅：
- `CLEANUP_REPORT.md` - 完整清理报告和分析

---

**最后更新**: 2026-06-04
**脚本版本**: v1.0

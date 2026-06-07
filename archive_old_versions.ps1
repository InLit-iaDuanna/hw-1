# archive_old_versions.ps1
# 归档 hw-1 项目中的旧版本和失败探索
# 用法:
#   .\archive_old_versions.ps1           # 执行归档
#   .\archive_old_versions.ps1 -DryRun   # 预览将要归档的内容

param(
    [switch]$DryRun = $false
)

$projectRoot = "D:\Dunna\Documents\hw-1"
$archiveRoot = "$projectRoot\archives"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "hw-1 项目版本归档工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN 模式] 仅预览，不会移动任何文件" -ForegroundColor Yellow
    Write-Host ""
}

# 归档分类
$categories = @{
    "failed_explorations" = @{
        "description" = "失败探索和否定结果"
        "items" = @(
            @{
                "path" = "v07_true_contact_exploration"
                "reason" = "V7 - 真实接触纯被动探索失败"
            },
            @{
                "path" = "v15_2_strict_sea"
                "reason" = "V15.2 - Pratt 内环失败，被 V15.1 替代"
            },
            @{
                "path" = "v18_3d_lateral_stability"
                "reason" = "V18 - 3D 侧向被动稳定否定结果"
            },
            @{
                "path" = "v19_hip_abduction_active"
                "reason" = "V19 - 髋外展主动稳定不足（否定结果）"
            },
            @{
                "path" = "v20_step_width_control"
                "reason" = "V20 - 步宽控制未完成"
            }
        )
    }
    "refactored_versions" = @{
        "description" = "重构版本（已被正式版替代）"
        "items" = @(
            @{
                "path" = "v13_6_refactored"
                "reason" = "V13.6 重构版 - 被正式版替代"
            },
            @{
                "path" = "v13_7_refactored"
                "reason" = "V13.7 重构版 - 被正式版替代"
            },
            @{
                "path" = "v16_refactored"
                "reason" = "V16 重构版 - 未在 VERSIONS.md 中记录"
            }
        )
    }
    "obsolete_envs" = @{
        "description" = "过时的虚拟环境"
        "items" = @(
            @{
                "path" = ".venv-codex"
                "reason" = "旧的开发环境，已被 .venv-mujoco 替代"
            }
        )
    }
    "old_reports" = @{
        "description" = "旧的报告文件"
        "items" = @(
            @{
                "path" = "midterm_report.pptx"
                "reason" = "中期汇报 PPT"
            },
            @{
                "path" = "中期汇报.pptx"
                "reason" = "中期汇报 PPT（中文版）"
            }
        )
    }
}

# 特殊处理：需要删除而非归档的文件
$filesToDelete = @(
    @{
        "path" = "2024211325王瀚乔第十三周.zip"
        "reason" = "他人作业文件，应删除"
    },
    @{
        "path" = "final_evidence_index.csv"
        "reason" = "临时索引文件"
    }
)

function New-ArchiveStructure {
    if (-not $DryRun) {
        if (-not (Test-Path $archiveRoot)) {
            New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
            Write-Host "[创建] 归档根目录: $archiveRoot" -ForegroundColor Green
        }

        foreach ($category in $categories.Keys) {
            $categoryPath = "$archiveRoot\$category"
            if (-not (Test-Path $categoryPath)) {
                New-Item -ItemType Directory -Path $categoryPath -Force | Out-Null
                Write-Host "[创建] 归档分类: $category" -ForegroundColor Green
            }
        }

        # 创建归档说明文件
        $readmePath = "$archiveRoot\README.md"
        if (-not (Test-Path $readmePath)) {
            $readmeContent = @"
# 归档目录说明

本目录存放已归档的旧版本、失败探索和过时文件。

归档时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## 目录结构

- **failed_explorations/** - 失败探索和否定结果的版本
- **refactored_versions/** - 被正式版替代的重构版本
- **obsolete_envs/** - 过时的虚拟环境
- **old_reports/** - 旧的报告和演示文件

## 归档原则

1. 归档而非删除 - 保留历史价值
2. 主线版本不归档 - V5-V17 主线保持活跃
3. 失败也有价值 - 否定结果对研究同样重要
4. 可恢复 - 需要时可以从归档中恢复

## 恢复方法

如需恢复某个归档版本到项目根目录：

``````powershell
Move-Item "archives\failed_explorations\v07_true_contact_exploration" ".\"
``````

## 注意事项

- 归档文件不再包含在日常搜索路径中
- .gitignore 可能需要更新以排除归档目录
- 大型数据文件建议压缩后归档
"@
            Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8
            Write-Host "[创建] 归档说明文件: README.md" -ForegroundColor Green
        }

        Write-Host ""
    }
}

function Move-ToArchive {
    param(
        [string]$ItemPath,
        [string]$Category,
        [string]$Reason
    )

    $fullPath = "$projectRoot\$ItemPath"
    $destinationPath = "$archiveRoot\$Category\$ItemPath"

    if (Test-Path $fullPath) {
        $itemType = if ((Get-Item $fullPath).PSIsContainer) { "目录" } else { "文件" }
        $size = 0

        if ((Get-Item $fullPath).PSIsContainer) {
            $size = (Get-ChildItem -Path $fullPath -Recurse -File -ErrorAction SilentlyContinue |
                     Measure-Object -Property Length -Sum).Sum
        } else {
            $size = (Get-Item $fullPath).Length
        }

        $sizeMB = [math]::Round($size / 1MB, 2)

        Write-Host "[$itemType] $ItemPath" -ForegroundColor Green
        Write-Host "  原因: $Reason" -ForegroundColor Gray
        Write-Host "  大小: $sizeMB MB" -ForegroundColor Gray
        Write-Host "  目标: archives\$Category\$ItemPath" -ForegroundColor Gray

        if (-not $DryRun) {
            try {
                # 确保目标目录存在
                $destinationDir = Split-Path -Path $destinationPath -Parent
                if (-not (Test-Path $destinationDir)) {
                    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
                }

                Move-Item -Path $fullPath -Destination $destinationPath -Force -ErrorAction Stop
                Write-Host "  状态: 已归档" -ForegroundColor Green
            } catch {
                Write-Host "  状态: 归档失败 - $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "  状态: [预览] 将被归档" -ForegroundColor Yellow
        }

        $script:totalSize += $size
        $script:totalCount++
    } else {
        Write-Host "[未找到] $ItemPath" -ForegroundColor DarkGray
        Write-Host "  原因: $Reason" -ForegroundColor Gray
        Write-Host "  状态: 路径不存在，跳过" -ForegroundColor DarkGray
    }

    Write-Host ""
}

function Remove-ObsoleteFile {
    param(
        [string]$FilePath,
        [string]$Reason
    )

    $fullPath = "$projectRoot\$FilePath"

    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        $sizeMB = [math]::Round($size / 1MB, 2)

        Write-Host "[待删除文件] $FilePath" -ForegroundColor Yellow
        Write-Host "  原因: $Reason" -ForegroundColor Gray
        Write-Host "  大小: $sizeMB MB" -ForegroundColor Gray

        if (-not $DryRun) {
            Write-Host "  确认删除此文件？(Y/N): " -ForegroundColor Red -NoNewline
            $confirmation = Read-Host

            if ($confirmation -eq 'Y' -or $confirmation -eq 'y') {
                try {
                    Remove-Item -Path $fullPath -Force -ErrorAction Stop
                    Write-Host "  状态: 已删除" -ForegroundColor Green
                    $script:deletedSize += $size
                    $script:deletedCount++
                } catch {
                    Write-Host "  状态: 删除失败 - $($_.Exception.Message)" -ForegroundColor Red
                }
            } else {
                Write-Host "  状态: 用户取消，保留文件" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  状态: [预览] 将提示删除" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[未找到] $FilePath" -ForegroundColor DarkGray
        Write-Host "  状态: 文件不存在，跳过" -ForegroundColor DarkGray
    }

    Write-Host ""
}

# 统计变量
$totalSize = 0
$totalCount = 0
$deletedSize = 0
$deletedCount = 0

# 创建归档结构
Write-Host "=== 准备归档环境 ===" -ForegroundColor Cyan
Write-Host ""
New-ArchiveStructure

# 执行归档
foreach ($category in $categories.Keys) {
    $categoryInfo = $categories[$category]
    Write-Host "=== $($categoryInfo.description) ===" -ForegroundColor Cyan
    Write-Host ""

    foreach ($item in $categoryInfo.items) {
        Move-ToArchive -ItemPath $item.path -Category $category -Reason $item.reason
    }
}

# 处理待删除文件
if ($filesToDelete.Count -gt 0) {
    Write-Host "=== 待删除文件（非归档） ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "以下文件建议删除而非归档：" -ForegroundColor Yellow
    Write-Host ""

    foreach ($file in $filesToDelete) {
        Remove-ObsoleteFile -FilePath $file.path -Reason $file.reason
    }
}

# 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "归档统计" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
$totalSizeGB = [math]::Round($totalSize / 1GB, 3)

Write-Host "归档项数: $totalCount" -ForegroundColor Green
Write-Host "归档大小: $totalSizeMB MB ($totalSizeGB GB)" -ForegroundColor Green

if ($deletedCount -gt 0) {
    $deletedSizeMB = [math]::Round($deletedSize / 1MB, 2)
    Write-Host "删除项数: $deletedCount" -ForegroundColor Yellow
    Write-Host "删除大小: $deletedSizeMB MB" -ForegroundColor Yellow
}

Write-Host ""

if ($DryRun) {
    Write-Host "这是预览模式，未移动或删除任何文件。" -ForegroundColor Yellow
    Write-Host "要执行归档，请运行: .\archive_old_versions.ps1" -ForegroundColor Yellow
} else {
    Write-Host "归档完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "归档位置: $archiveRoot" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "建议操作：" -ForegroundColor Cyan
    Write-Host "1. 检查归档目录确认文件正确移动" -ForegroundColor Gray
    Write-Host "2. 运行 'git status' 检查变更" -ForegroundColor Gray
    Write-Host "3. 更新项目文档（如 VERSIONS.md）标注归档版本" -ForegroundColor Gray
    Write-Host "4. 如需要，在 .gitignore 中添加 archives/ 目录" -ForegroundColor Gray
}

Write-Host ""

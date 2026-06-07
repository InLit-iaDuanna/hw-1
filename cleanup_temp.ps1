# cleanup_temp.ps1
# 安全清理 hw-1 项目的临时文件和缓存
# 用法:
#   .\cleanup_temp.ps1           # 执行清理
#   .\cleanup_temp.ps1 -DryRun   # 预览将要清理的内容

param(
    [switch]$DryRun = $false
)

$projectRoot = "D:\Dunna\Documents\hw-1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "hw-1 项目临时文件清理工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN 模式] 仅预览，不会删除任何文件" -ForegroundColor Yellow
    Write-Host ""
}

# 统计变量
$totalSize = 0
$totalCount = 0

function Remove-ItemSafe {
    param(
        [string]$Path,
        [string]$Description
    )

    if (Test-Path $Path) {
        $items = Get-ChildItem -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
        $size = ($items | Where-Object { -not $_.PSIsContainer } | Measure-Object -Property Length -Sum).Sum
        $count = ($items | Measure-Object).Count

        if ($null -eq $size) { $size = 0 }

        $sizeMB = [math]::Round($size / 1MB, 2)

        Write-Host "[$Description]" -ForegroundColor Green
        Write-Host "  路径: $Path" -ForegroundColor Gray
        Write-Host "  项数: $count" -ForegroundColor Gray
        Write-Host "  大小: $sizeMB MB" -ForegroundColor Gray

        if (-not $DryRun) {
            try {
                Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
                Write-Host "  状态: 已删除" -ForegroundColor Green
            } catch {
                Write-Host "  状态: 删除失败 - $($_.Exception.Message)" -ForegroundColor Red
                return
            }
        } else {
            Write-Host "  状态: [预览] 将被删除" -ForegroundColor Yellow
        }

        $script:totalSize += $size
        $script:totalCount += $count
        Write-Host ""
    }
}

function Remove-FilesByPattern {
    param(
        [string]$Pattern,
        [string]$Description,
        [string[]]$Exclude = @()
    )

    Write-Host "[$Description]" -ForegroundColor Green
    Write-Host "  模式: $Pattern" -ForegroundColor Gray

    $files = Get-ChildItem -Path $projectRoot -Recurse -Include $Pattern -Force -ErrorAction SilentlyContinue |
             Where-Object {
                 $keep = $true
                 foreach ($ex in $Exclude) {
                     if ($_.FullName -like $ex) {
                         $keep = $false
                         break
                     }
                 }
                 $keep
             }

    $count = ($files | Measure-Object).Count
    $size = ($files | Measure-Object -Property Length -Sum).Sum

    if ($null -eq $size) { $size = 0 }
    $sizeMB = [math]::Round($size / 1MB, 2)

    Write-Host "  找到: $count 个文件" -ForegroundColor Gray
    Write-Host "  大小: $sizeMB MB" -ForegroundColor Gray

    if ($count -gt 0) {
        if (-not $DryRun) {
            $deleted = 0
            $failed = 0
            foreach ($file in $files) {
                try {
                    Remove-Item -Path $file.FullName -Force -ErrorAction Stop
                    $deleted++
                } catch {
                    $failed++
                }
            }
            Write-Host "  状态: 已删除 $deleted 个, 失败 $failed 个" -ForegroundColor Green
        } else {
            Write-Host "  状态: [预览] 将被删除" -ForegroundColor Yellow
        }

        $script:totalSize += $size
        $script:totalCount += $count
    } else {
        Write-Host "  状态: 未找到文件" -ForegroundColor Gray
    }

    Write-Host ""
}

Write-Host "开始扫描..." -ForegroundColor Cyan
Write-Host ""

# 1. 清理 Python __pycache__ 目录
Write-Host "=== 清理 Python 缓存目录 ===" -ForegroundColor Cyan
Write-Host ""

$pycacheDirs = Get-ChildItem -Path $projectRoot -Recurse -Directory -Include __pycache__ -Force -ErrorAction SilentlyContinue

$pycacheCount = ($pycacheDirs | Measure-Object).Count
Write-Host "[Python __pycache__ 目录]" -ForegroundColor Green
Write-Host "  找到: $pycacheCount 个目录" -ForegroundColor Gray

if ($pycacheCount -gt 0) {
    $pycacheSize = 0
    foreach ($dir in $pycacheDirs) {
        $dirSize = (Get-ChildItem -Path $dir.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($null -ne $dirSize) {
            $pycacheSize += $dirSize
        }
    }

    $pycacheSizeMB = [math]::Round($pycacheSize / 1MB, 2)
    Write-Host "  大小: $pycacheSizeMB MB" -ForegroundColor Gray

    if (-not $DryRun) {
        $deleted = 0
        $failed = 0
        foreach ($dir in $pycacheDirs) {
            try {
                Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction Stop
                $deleted++
            } catch {
                $failed++
            }
        }
        Write-Host "  状态: 已删除 $deleted 个, 失败 $failed 个" -ForegroundColor Green
    } else {
        Write-Host "  状态: [预览] 将被删除" -ForegroundColor Yellow
    }

    $script:totalSize += $pycacheSize
    $script:totalCount += $pycacheCount
} else {
    Write-Host "  状态: 未找到目录" -ForegroundColor Gray
}

Write-Host ""

# 2. 清理 linter 和测试缓存
Write-Host "=== 清理 Linter 和测试缓存 ===" -ForegroundColor Cyan
Write-Host ""

Remove-ItemSafe -Path "$projectRoot\.mypy_cache" -Description "Mypy 类型检查缓存"
Remove-ItemSafe -Path "$projectRoot\.pytest_cache" -Description "Pytest 测试缓存"
Remove-ItemSafe -Path "$projectRoot\.ruff_cache" -Description "Ruff Linter 缓存"
Remove-ItemSafe -Path "$projectRoot\htmlcov" -Description "Coverage HTML 报告"

# 3. 清理覆盖率数据
Write-Host "=== 清理覆盖率数据 ===" -ForegroundColor Cyan
Write-Host ""

Remove-FilesByPattern -Pattern ".coverage" -Description "Coverage 数据文件"

# 4. 清理 Python 编译文件
Write-Host "=== 清理 Python 编译文件 ===" -ForegroundColor Cyan
Write-Host ""

Remove-FilesByPattern -Pattern "*.pyc" -Description "Python 字节码文件 (.pyc)"
Remove-FilesByPattern -Pattern "*.pyo" -Description "Python 优化字节码文件 (.pyo)"

# 5. 清理临时文件
Write-Host "=== 清理临时文件 ===" -ForegroundColor Cyan
Write-Host ""

# 排除 git 目录中的 .log 文件
Remove-FilesByPattern -Pattern "*.log" -Description "日志文件 (.log)" -Exclude @("*\.git\*")
Remove-FilesByPattern -Pattern "*.tmp" -Description "临时文件 (.tmp)"

# 6. 清理编辑器临时文件
Write-Host "=== 清理编辑器临时文件 ===" -ForegroundColor Cyan
Write-Host ""

Remove-FilesByPattern -Pattern "~$*" -Description "Office 临时文件 (~$*)"
Remove-FilesByPattern -Pattern "*.swp" -Description "Vim swap 文件 (.swp)"
Remove-FilesByPattern -Pattern "*.swo" -Description "Vim swap 文件 (.swo)"
Remove-FilesByPattern -Pattern "*.bak" -Description "备份文件 (.bak)"

# 7. 清理 OS 临时文件
Write-Host "=== 清理操作系统临时文件 ===" -ForegroundColor Cyan
Write-Host ""

Remove-FilesByPattern -Pattern "Thumbs.db" -Description "Windows 缩略图缓存"
Remove-FilesByPattern -Pattern "desktop.ini" -Description "Windows 文件夹配置"
Remove-FilesByPattern -Pattern ".DS_Store" -Description "macOS 文件夹配置"

# 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "清理统计" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
$totalSizeGB = [math]::Round($totalSize / 1GB, 3)

Write-Host "总项数: $totalCount" -ForegroundColor Green
Write-Host "总大小: $totalSizeMB MB ($totalSizeGB GB)" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Host "这是预览模式，未删除任何文件。" -ForegroundColor Yellow
    Write-Host "要执行清理，请运行: .\cleanup_temp.ps1" -ForegroundColor Yellow
} else {
    Write-Host "清理完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "建议运行 'git status' 检查是否有意外的文件变更。" -ForegroundColor Cyan
}

Write-Host ""

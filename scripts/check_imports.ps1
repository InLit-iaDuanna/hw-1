# check_imports.ps1
# 检查 hw-1 项目导入语句一致性
# 使用方法: .\scripts\check_imports.ps1

param(
    [switch]$Verbose = $false,
    [switch]$ShowFiles = $false
)

$projectRoot = "D:\Dunna\Documents\hw-1"
$issues = @()

Write-Host "🔍 开始检查 hw-1 项目导入语句一致性..." -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. 检查 from __future__ import annotations
# ============================================================================
Write-Host "🔮 检查 'from __future__ import annotations' 使用情况..." -ForegroundColor Yellow

$pyFiles = Get-ChildItem -Path $projectRoot -Filter "*.py" -Recurse | Where-Object {
    $_.FullName -notmatch '\\.venv-|\\\..*cache|\\wheelhouse' -and
    $_.FullName -match '\\v\d+'
}

$withFuture = @()
$withoutFuture = @()

foreach ($file in $pyFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match 'from __future__ import annotations') {
        $withFuture += $file
    } else {
        $withoutFuture += $file
    }
}

Write-Host "  ✓ 使用 future annotations: $($withFuture.Count) / $($pyFiles.Count) ($([math]::Round($withFuture.Count / $pyFiles.Count * 100, 1))%)" -ForegroundColor Green

if ($withoutFuture.Count -gt 0) {
    Write-Host "  ⚠️  未使用 future annotations: $($withoutFuture.Count)" -ForegroundColor Yellow

    if ($ShowFiles) {
        Write-Host ""
        Write-Host "  文件列表:" -ForegroundColor Gray
        $withoutFuture | Select-Object -First 20 | ForEach-Object {
            Write-Host "    - $($_.FullName.Replace("$projectRoot\", ''))" -ForegroundColor Gray
        }
        if ($withoutFuture.Count -gt 20) {
            Write-Host "    ... 及其他 $($withoutFuture.Count - 20) 个文件" -ForegroundColor Gray
        }
    }
}

# ============================================================================
# 2. 检查导入顺序
# ============================================================================
Write-Host ""
Write-Host "📋 检查导入顺序（PEP 8）..." -ForegroundColor Yellow

$importOrderIssues = 0

foreach ($file in $pyFiles | Select-Object -First 30) {
    $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue
    $inImportSection = $false
    $lastImportType = 0  # 0=future, 1=stdlib, 2=third-party, 3=local

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]

        if ($line -match '^(from|import)\s+') {
            $currentType = 0

            if ($line -match '^from __future__') {
                $currentType = 0
            } elseif ($line -match '^(from|import)\s+(argparse|csv|json|math|sys|os|pathlib|dataclasses|typing|itertools|collections)') {
                $currentType = 1
            } elseif ($line -match '^(from|import)\s+(mujoco|numpy|matplotlib|scipy)') {
                $currentType = 2
            } elseif ($line -match '^from (common|v\d+)') {
                $currentType = 3
            }

            if ($currentType < $lastImportType -and $currentType -ne 3) {
                $importOrderIssues++
                $issues += [PSCustomObject]@{
                    Type = "导入顺序"
                    Path = $file.FullName.Replace("$projectRoot\", "")
                    Issue = "导入顺序不符合 PEP 8（行 $($i+1)）"
                    Line = $line.Trim()
                }
                break
            }

            $lastImportType = $currentType
        }
    }
}

if ($importOrderIssues -eq 0) {
    Write-Host "  ✓ 所有采样文件导入顺序符合 PEP 8" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  发现 $importOrderIssues 个导入顺序问题" -ForegroundColor Yellow
}

# ============================================================================
# 3. 检查 common/ 库使用情况
# ============================================================================
Write-Host ""
Write-Host "📦 检查 common/ 库使用情况..." -ForegroundColor Yellow

$versionDirs = Get-ChildItem -Path $projectRoot -Directory | Where-Object { $_.Name -match '^v\d+' } | Sort-Object Name

$usingCommon = @()
$notUsingCommon = @()

foreach ($dir in $versionDirs) {
    $dirPyFiles = Get-ChildItem -Path $dir.FullName -Filter "*.py" -File
    $usesCommon = $false

    foreach ($file in $dirPyFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match 'from common|import common') {
            $usesCommon = $true
            break
        }
    }

    if ($usesCommon) {
        $usingCommon += $dir.Name
    } else {
        $notUsingCommon += $dir.Name
    }
}

Write-Host "  ✓ 使用 common/ 库: $($usingCommon.Count) 个版本" -ForegroundColor Green
Write-Host "  ⚠️  未使用 common/ 库: $($notUsingCommon.Count) 个版本" -ForegroundColor Yellow

if ($ShowFiles) {
    Write-Host ""
    Write-Host "  使用 common/ 的版本:" -ForegroundColor Gray
    $usingCommon | ForEach-Object { Write-Host "    ✓ $_" -ForegroundColor Gray }

    Write-Host ""
    Write-Host "  未使用 common/ 的版本（建议回溯集成）:" -ForegroundColor Gray
    $notUsingCommon | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
}

# ============================================================================
# 4. 检查空行分隔
# ============================================================================
Write-Host ""
Write-Host "📏 检查导入语句空行分隔..." -ForegroundColor Yellow

$blankLineIssues = 0

foreach ($file in $pyFiles | Select-Object -First 30) {
    $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue

    # 检查 from __future__ 后是否有空行
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^from __future__') {
            if ($i+1 -lt $lines.Count -and $lines[$i+1] -notmatch '^\s*$') {
                $blankLineIssues++
                $issues += [PSCustomObject]@{
                    Type = "空行分隔"
                    Path = $file.FullName.Replace("$projectRoot\", "")
                    Issue = "from __future__ 后缺少空行"
                    Line = "行 $($i+1)"
                }
            }
            break
        }
    }
}

if ($blankLineIssues -eq 0) {
    Write-Host "  ✓ 导入语句空行分隔符合规范" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  发现 $blankLineIssues 个空行分隔问题" -ForegroundColor Yellow
}

# ============================================================================
# 5. 检查 sys.path 操作一致性
# ============================================================================
Write-Host ""
Write-Host "🛤️  检查 sys.path 操作模式..." -ForegroundColor Yellow

$sysPathFiles = Select-String -Path "$projectRoot\v*\*.py" -Pattern "sys\.path\.insert" -ErrorAction SilentlyContinue

$sysPathPatterns = @{}
foreach ($match in $sysPathFiles) {
    $pattern = $match.Line.Trim()
    if ($sysPathPatterns.ContainsKey($pattern)) {
        $sysPathPatterns[$pattern]++
    } else {
        $sysPathPatterns[$pattern] = 1
    }
}

Write-Host "  发现 $($sysPathFiles.Count) 处 sys.path 操作" -ForegroundColor Gray
Write-Host "  常见模式:" -ForegroundColor Gray

$sysPathPatterns.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Host "    - 使用 $($_.Value) 次: $($_.Key.Substring(0, [Math]::Min(60, $_.Key.Length)))..." -ForegroundColor Gray
}

# ============================================================================
# 生成报告
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "                    检查结果汇总" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# 统计摘要
Write-Host "📊 统计摘要:" -ForegroundColor Cyan
Write-Host "  • 检查文件总数: $($pyFiles.Count)" -ForegroundColor Gray
Write-Host "  • future annotations 使用率: $([math]::Round($withFuture.Count / $pyFiles.Count * 100, 1))%" -ForegroundColor Gray
Write-Host "  • common/ 库使用率: $([math]::Round($usingCommon.Count / $versionDirs.Count * 100, 1))% ($($usingCommon.Count)/$($versionDirs.Count) 版本)" -ForegroundColor Gray
Write-Host "  • 导入顺序问题: $importOrderIssues" -ForegroundColor Gray
Write-Host "  • 空行分隔问题: $blankLineIssues" -ForegroundColor Gray
Write-Host ""

if ($issues.Count -eq 0) {
    Write-Host "✅ 导入语句一致性检查通过！" -ForegroundColor Green
} else {
    Write-Host "⚠️  发现 $($issues.Count) 个导入相关问题：" -ForegroundColor Yellow
    Write-Host ""

    # 显示前 10 个问题
    $issues | Select-Object -First 10 | Format-Table -Property Type, Path, Issue, Line -AutoSize -Wrap

    if ($issues.Count -gt 10) {
        Write-Host "  ... 及其他 $($issues.Count - 10) 个问题" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "💡 改进建议:" -ForegroundColor Cyan
Write-Host "  1. 为未使用 future annotations 的文件添加 'from __future__ import annotations'" -ForegroundColor Gray
Write-Host "  2. 考虑将 V01-V10 的通用函数迁移到 common/ 库" -ForegroundColor Gray
Write-Host "  3. 确保所有导入语句遵循 PEP 8 顺序（stdlib → third-party → local）" -ForegroundColor Gray
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "检查完成！详细报告请查看: CONSISTENCY_REPORT.md" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

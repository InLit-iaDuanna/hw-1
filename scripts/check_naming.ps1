# check_naming.ps1
# 检查 hw-1 项目命名规范一致性
# 使用方法: .\scripts\check_naming.ps1

param(
    [switch]$Verbose = $false
)

$projectRoot = "D:\Dunna\Documents\hw-1"
$issues = @()
$warnings = @()

Write-Host "🔍 开始检查 hw-1 项目命名规范..." -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. 检查版本目录命名
# ============================================================================
Write-Host "📁 检查版本目录命名规范..." -ForegroundColor Yellow

$versionDirs = Get-ChildItem -Path $projectRoot -Directory | Where-Object { $_.Name -match '^v\d+' }

foreach ($dir in $versionDirs) {
    # 检查是否符合 v{数字}_snake_case 格式
    if ($dir.Name -notmatch '^v\d+_[a-z0-9_]+$') {
        $issues += [PSCustomObject]@{
            Type = "目录命名"
            Path = $dir.Name
            Issue = "不符合 v{数字}_snake_case 格式"
            Severity = "中"
        }

        # 提供建议修正
        if ($dir.Name -match '^v(\d+)([a-z])_(.+)$') {
            $baseVersion = $Matches[1]
            $suffix = $Matches[2]
            $desc = $Matches[3]
            $suggested = "v${baseVersion}_$([int][char]$suffix - [int][char]'a' + 2)_$desc"
            $warnings += "  建议: $($dir.Name) -> $suggested"
        }
    }

    if ($Verbose) {
        Write-Host "  ✓ $($dir.Name)" -ForegroundColor Gray
    }
}

# ============================================================================
# 2. 检查 Python 文件命名
# ============================================================================
Write-Host "🐍 检查 Python 文件命名规范..." -ForegroundColor Yellow

$validPrefixes = @(
    'simulate', 'analyze', 'render', 'view', 'scan', 'smoke', 'test', 'plot',
    'run', 'show', 'replay', 'check', 'diagnose', 'explore', 'playback',
    'disturbance', 'generate', 'control', 'model', 'sensor', 'state', 'step'
)

$pyFiles = Get-ChildItem -Path $projectRoot -Filter "*.py" -Recurse | Where-Object {
    $_.FullName -notmatch '\\.venv-|\\\..*cache|\\wheelhouse|\\common\\' -and
    $_.FullName -match '\\v\d+'
}

foreach ($file in $pyFiles) {
    $hasValidPrefix = $false

    foreach ($prefix in $validPrefixes) {
        if ($file.Name -like "${prefix}_*") {
            $hasValidPrefix = $true
            break
        }
    }

    if (-not $hasValidPrefix -and $file.Name -ne "__init__.py") {
        $issues += [PSCustomObject]@{
            Type = "文件命名"
            Path = $file.FullName.Replace("$projectRoot\", "")
            Issue = "不符合标准前缀命名"
            Severity = "低"
        }
    }

    if ($Verbose -and $hasValidPrefix) {
        Write-Host "  ✓ $($file.Name)" -ForegroundColor Gray
    }
}

# ============================================================================
# 3. 检查 snake_case 一致性
# ============================================================================
Write-Host "🐍 检查 snake_case 命名一致性..." -ForegroundColor Yellow

foreach ($file in $pyFiles | Select-Object -First 50) {
    # 检查是否有 camelCase 函数名
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match '\bdef\s+[a-z]+[A-Z]') {
        $issues += [PSCustomObject]@{
            Type = "函数命名"
            Path = $file.FullName.Replace("$projectRoot\", "")
            Issue = "发现 camelCase 函数名，应使用 snake_case"
            Severity = "低"
        }
    }
}

# ============================================================================
# 4. 检查 README.md 存在性
# ============================================================================
Write-Host "📄 检查 README.md 存在性..." -ForegroundColor Yellow

foreach ($dir in $versionDirs) {
    $readmePath = Join-Path $dir.FullName "README.md"
    if (-not (Test-Path $readmePath)) {
        $issues += [PSCustomObject]@{
            Type = "文档缺失"
            Path = $dir.Name
            Issue = "缺少 README.md"
            Severity = "中"
        }
    }
}

# ============================================================================
# 生成报告
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "                    检查结果汇总" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0) {
    Write-Host "✅ 恭喜！所有命名规范检查通过！" -ForegroundColor Green
} else {
    Write-Host "⚠️  发现 $($issues.Count) 个命名问题：" -ForegroundColor Yellow
    Write-Host ""

    # 按严重程度分组
    $highSeverity = $issues | Where-Object { $_.Severity -eq "高" }
    $mediumSeverity = $issues | Where-Object { $_.Severity -eq "中" }
    $lowSeverity = $issues | Where-Object { $_.Severity -eq "低" }

    if ($highSeverity.Count -gt 0) {
        Write-Host "🔴 高严重性问题 ($($highSeverity.Count))：" -ForegroundColor Red
        $highSeverity | Format-Table -AutoSize -Wrap
    }

    if ($mediumSeverity.Count -gt 0) {
        Write-Host "🟡 中等严重性问题 ($($mediumSeverity.Count))：" -ForegroundColor Yellow
        $mediumSeverity | Format-Table -AutoSize -Wrap
    }

    if ($lowSeverity.Count -gt 0) {
        Write-Host "🟢 低严重性问题 ($($lowSeverity.Count))：" -ForegroundColor Gray
        $lowSeverity | Format-Table -AutoSize -Wrap
    }

    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "💡 修正建议：" -ForegroundColor Cyan
        $warnings | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "检查完成！详细报告请查看: CONSISTENCY_REPORT.md" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

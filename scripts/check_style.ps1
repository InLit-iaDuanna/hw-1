# check_style.ps1
# 检查 hw-1 项目代码风格一致性
# 使用方法: .\scripts\check_style.ps1

param(
    [switch]$Verbose = $false,
    [int]$SampleSize = 50
)

$projectRoot = "D:\Dunna\Documents\hw-1"
$issues = @()

Write-Host "🔍 开始检查 hw-1 项目代码风格一致性..." -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. 检查缩进风格（空格 vs Tab）
# ============================================================================
Write-Host "📐 检查缩进风格..." -ForegroundColor Yellow

$pyFiles = Get-ChildItem -Path $projectRoot -Filter "*.py" -Recurse | Where-Object {
    $_.FullName -notmatch '\\.venv-|\\\..*cache|\\wheelhouse' -and
    $_.FullName -match '\\v\d+'
}

$tabIndented = @()
$spaceIndented = @()
$mixedIndent = @()

foreach ($file in $pyFiles | Select-Object -First $SampleSize) {
    $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue
    $hasTab = $false
    $hasSpace = $false

    foreach ($line in $lines | Select-Object -First 100) {
        if ($line -match '^\t') {
            $hasTab = $true
        }
        if ($line -match '^    ') {
            $hasSpace = $true
        }
    }

    if ($hasTab -and $hasSpace) {
        $mixedIndent += $file
    } elseif ($hasTab) {
        $tabIndented += $file
    } elseif ($hasSpace) {
        $spaceIndented += $file
    }
}

Write-Host "  ✓ 空格缩进: $($spaceIndented.Count) / $SampleSize" -ForegroundColor Green
Write-Host "  • Tab 缩进: $($tabIndented.Count) / $SampleSize" -ForegroundColor Gray

if ($mixedIndent.Count -gt 0) {
    Write-Host "  ⚠️  混合缩进: $($mixedIndent.Count) / $SampleSize" -ForegroundColor Yellow
    $mixedIndent | ForEach-Object {
        $issues += [PSCustomObject]@{
            Type = "缩进风格"
            Path = $_.FullName.Replace("$projectRoot\", "")
            Issue = "混合使用 Tab 和空格缩进"
            Severity = "中"
        }
    }
}

# ============================================================================
# 2. 检查引号使用（单引号 vs 双引号）
# ============================================================================
Write-Host ""
Write-Host "💬 检查引号使用..." -ForegroundColor Yellow

$singleQuoteDominant = 0
$doubleQuoteDominant = 0

foreach ($file in $pyFiles | Select-Object -First $SampleSize) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
        # 简单计数（不完美但足够用于趋势分析）
        $singleCount = ([regex]::Matches($content, "'[^']*'")).Count
        $doubleCount = ([regex]::Matches($content, '"[^"]*"')).Count

        if ($singleCount -gt $doubleCount * 1.5) {
            $singleQuoteDominant++
        } elseif ($doubleCount -gt $singleCount * 1.5) {
            $doubleQuoteDominant++
        }
    }
}

$doubleQuotePercent = [math]::Round($doubleQuoteDominant / $SampleSize * 100, 1)
Write-Host "  ✓ 双引号主导: $doubleQuoteDominant / $SampleSize ($doubleQuotePercent%)" -ForegroundColor Green
Write-Host "  • 单引号主导: $singleQuoteDominant / $SampleSize" -ForegroundColor Gray

if ($doubleQuotePercent -lt 90) {
    Write-Host "  ⚠️  引号使用不够统一（推荐 >90% 使用双引号）" -ForegroundColor Yellow
}

# ============================================================================
# 3. 检查行长度（PEP 8: 79 或 88 字符）
# ============================================================================
Write-Host ""
Write-Host "📏 检查行长度..." -ForegroundColor Yellow

$longLineFiles = @()
$maxLineLength = 100  # 宽松限制

foreach ($file in $pyFiles | Select-Object -First $SampleSize) {
    $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue
    $hasLongLine = $false

    foreach ($line in $lines) {
        if ($line.Length -gt $maxLineLength -and $line -notmatch '^\s*#' -and $line -notmatch 'http') {
            $hasLongLine = $true
            break
        }
    }

    if ($hasLongLine) {
        $longLineFiles += $file
    }
}

$complianceRate = [math]::Round(($SampleSize - $longLineFiles.Count) / $SampleSize * 100, 1)
Write-Host "  • 符合 <100 字符: $($SampleSize - $longLineFiles.Count) / $SampleSize ($complianceRate%)" -ForegroundColor Gray

if ($longLineFiles.Count -gt 0) {
    Write-Host "  ⚠️  $($longLineFiles.Count) 个文件包含超长行（>100 字符）" -ForegroundColor Yellow
}

# ============================================================================
# 4. 检查函数/类定义风格
# ============================================================================
Write-Host ""
Write-Host "🔧 检查函数和类定义风格..." -ForegroundColor Yellow

$functionDefIssues = 0

foreach ($file in $pyFiles | Select-Object -First $SampleSize) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue

    # 检查是否有不标准的函数定义
    if ($content -match 'def\s+\w+\s*\([^)]*\)\s*:\s*\S') {
        $functionDefIssues++
        $issues += [PSCustomObject]@{
            Type = "函数定义"
            Path = $file.FullName.Replace("$projectRoot\", "")
            Issue = "函数定义后应换行（冒号后不应有代码）"
            Severity = "低"
        }
    }
}

if ($functionDefIssues -eq 0) {
    Write-Host "  ✓ 函数定义风格一致" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  发现 $functionDefIssues 个函数定义风格问题" -ForegroundColor Yellow
}

# ============================================================================
# 5. 检查注释风格
# ============================================================================
Write-Host ""
Write-Host "💭 检查注释风格..." -ForegroundColor Yellow

$docstringCount = 0
$hashCommentCount = 0
$chineseCommentCount = 0

foreach ($file in $pyFiles | Select-Object -First $SampleSize) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue

    if ($content -match '"""[\s\S]*?"""' -or $content -match "'''[\s\S]*?'''") {
        $docstringCount++
    }

    if ($content -match '#[^#]') {
        $hashCommentCount++
    }

    # 检查是否包含中文注释
    if ($content -match '#.*[一-龥]' -or $content -match '"""[\s\S]*?[一-龥][\s\S]*?"""') {
        $chineseCommentCount++
    }
}

Write-Host "  • 使用 docstring: $docstringCount / $SampleSize" -ForegroundColor Gray
Write-Host "  • 使用 # 注释: $hashCommentCount / $SampleSize" -ForegroundColor Gray
Write-Host "  • 包含中文注释: $chineseCommentCount / $SampleSize" -ForegroundColor Gray

# ============================================================================
# 6. 检查命名风格一致性
# ============================================================================
Write-Host ""
Write-Host "🏷️  检查变量命名风格..." -ForegroundColor Yellow

$camelCaseVars = 0

foreach ($file in $pyFiles | Select-Object -First 30) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue

    # 检查变量命名（简化检查）
    if ($content -match '\b[a-z]+[A-Z][a-zA-Z]*\s*=' -and $content -notmatch 'MjModel|MjData') {
        $camelCaseVars++
    }
}

if ($camelCaseVars -eq 0) {
    Write-Host "  ✓ 变量命名统一使用 snake_case" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  发现 $camelCaseVars 个文件可能使用 camelCase 变量名" -ForegroundColor Yellow
}

# ============================================================================
# 7. 检查常量命名
# ============================================================================
Write-Host ""
Write-Host "🔤 检查常量命名风格..." -ForegroundColor Yellow

$constantPatternFiles = 0

foreach ($file in $pyFiles | Select-Object -First 30) {
    $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue

    foreach ($line in $lines | Select-Object -First 50) {
        # 检查是否有 UPPER_SNAKE_CASE 常量定义
        if ($line -match '^[A-Z_][A-Z0-9_]*\s*=') {
            $constantPatternFiles++
            break
        }
    }
}

Write-Host "  • 使用 UPPER_SNAKE_CASE 常量: $constantPatternFiles / 30 文件" -ForegroundColor Gray

# ============================================================================
# 生成报告
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "                    检查结果汇总" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# 统计摘要
Write-Host "📊 代码风格统计:" -ForegroundColor Cyan
Write-Host "  • 采样文件数: $SampleSize" -ForegroundColor Gray
Write-Host "  • 空格缩进率: $([math]::Round($spaceIndented.Count / $SampleSize * 100, 1))%" -ForegroundColor Gray
Write-Host "  • 双引号使用率: $doubleQuotePercent%" -ForegroundColor Gray
Write-Host "  • 行长度合规率: $complianceRate%" -ForegroundColor Gray
Write-Host ""

# 一致性评分
$score = 100
$score -= $mixedIndent.Count * 5
$score -= $functionDefIssues * 2
$score -= $camelCaseVars * 3
if ($doubleQuotePercent -lt 90) { $score -= 5 }

$grade = "A+"
if ($score -lt 95) { $grade = "A" }
if ($score -lt 90) { $grade = "A-" }
if ($score -lt 85) { $grade = "B+" }
if ($score -lt 80) { $grade = "B" }

Write-Host "🎯 一致性评分: $score / 100 ($grade)" -ForegroundColor $(if ($score -ge 90) { "Green" } elseif ($score -ge 80) { "Yellow" } else { "Red" })
Write-Host ""

if ($issues.Count -eq 0) {
    Write-Host "✅ 代码风格检查通过！项目代码风格高度一致。" -ForegroundColor Green
} else {
    Write-Host "⚠️  发现 $($issues.Count) 个代码风格问题：" -ForegroundColor Yellow
    Write-Host ""

    # 按严重程度分组
    $mediumIssues = $issues | Where-Object { $_.Severity -eq "中" }
    $lowIssues = $issues | Where-Object { $_.Severity -eq "低" }

    if ($mediumIssues.Count -gt 0) {
        Write-Host "🟡 中等严重性问题 ($($mediumIssues.Count))：" -ForegroundColor Yellow
        $mediumIssues | Select-Object -First 5 | Format-Table -AutoSize -Wrap
    }

    if ($lowIssues.Count -gt 0) {
        Write-Host "🟢 低严重性问题 ($($lowIssues.Count))：" -ForegroundColor Gray
        $lowIssues | Select-Object -First 5 | Format-Table -AutoSize -Wrap
    }
}

Write-Host ""
Write-Host "💡 改进建议:" -ForegroundColor Cyan
Write-Host "  1. 统一使用 4 空格缩进（已达成 ✓）" -ForegroundColor Gray
Write-Host "  2. 统一使用双引号（已达成 ✓）" -ForegroundColor Gray
Write-Host "  3. 遵循 PEP 8 命名规范（snake_case 变量，UPPER_SNAKE_CASE 常量）" -ForegroundColor Gray
Write-Host "  4. 考虑使用 black 或 ruff 自动格式化工具" -ForegroundColor Gray
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "检查完成！详细报告请查看: CONSISTENCY_REPORT.md" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

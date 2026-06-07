# Project Health Check
# 项目健康检查：测试、文档、代码质量、数据完整性

param(
    [Parameter(Mandatory=$false)]
    [switch]$quick,  # 快速模式：只检查关键项

    [Parameter(Mandatory=$false)]
    [switch]$full,  # 完整模式：运行所有测试和检查

    [Parameter(Mandatory=$false)]
    [switch]$fix  # 自动修复可修复的问题
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = "$projectRoot\health_check_$timestamp.txt"

$healthScore = 0
$maxScore = 0
$issues = @()

function Write-Status {
    param([string]$message, [string]$status = "INFO")

    switch ($status) {
        "PASS" { Write-Host "✓ $message" -ForegroundColor Green }
        "FAIL" { Write-Host "✗ $message" -ForegroundColor Red }
        "WARN" { Write-Host "⚠ $message" -ForegroundColor Yellow }
        default { Write-Host "ℹ $message" -ForegroundColor White }
    }
}

function Add-Issue {
    param(
        [string]$category,
        [string]$description,
        [string]$severity = "MEDIUM",
        [string]$fix = ""
    )

    $script:issues += @{
        category = $category
        description = $description
        severity = $severity
        fix = $fix
    }
}

# 1. 检查环境配置
Write-Host "`n========== 环境配置 ==========" -ForegroundColor Cyan
$maxScore += 10

if (Test-Path $pythonExe) {
    Write-Status "Python 虚拟环境存在" "PASS"
    $healthScore += 5

    try {
        $pythonVersion = & $pythonExe --version 2>&1
        Write-Status "Python 版本: $pythonVersion" "INFO"
        $healthScore += 5
    }
    catch {
        Write-Status "无法获取 Python 版本" "WARN"
        Add-Issue "Environment" "Python 版本检查失败" "LOW"
    }
} else {
    Write-Status "Python 虚拟环境不存在" "FAIL"
    Add-Issue "Environment" "缺少 .venv-mujoco 虚拟环境" "HIGH" "运行: python -m venv .venv-mujoco"
}

# 检查关键依赖
$requirementsPath = Join-Path $projectRoot "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Status "requirements.txt 存在" "PASS"
} else {
    Write-Status "requirements.txt 不存在" "FAIL"
    Add-Issue "Environment" "缺少 requirements.txt" "MEDIUM"
}

# 2. 检查测试覆盖率
Write-Host "`n========== 测试覆盖率 ==========" -ForegroundColor Cyan
$maxScore += 20

if (Test-Path "$projectRoot\tests") {
    $testFiles = Get-ChildItem -Path "$projectRoot\tests" -Filter "test_*.py" -Recurse

    Write-Status "发现 $($testFiles.Count) 个测试文件" "INFO"

    if (-not $quick) {
        try {
            Set-Location $projectRoot
            & $pythonExe -m pytest tests/ --quiet --tb=no 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Status "测试套件通过" "PASS"
                $healthScore += 15
            } else {
                Write-Status "测试套件失败 (退出码: $LASTEXITCODE)" "FAIL"
                Add-Issue "Tests" "部分测试未通过" "HIGH" "运行: pytest tests/ -v"
                $healthScore += 5
            }
        }
        catch {
            Write-Status "无法运行测试: $_" "FAIL"
            Add-Issue "Tests" "pytest 执行失败" "HIGH"
        }
    } else {
        Write-Status "快速模式：跳过测试执行" "WARN"
        $healthScore += 10
    }

    # 检查覆盖率报告
    if (Test-Path "$projectRoot\.coverage") {
        Write-Status "覆盖率数据存在" "PASS"
        $healthScore += 5
    } else {
        Write-Status "缺少覆盖率数据" "WARN"
        Add-Issue "Tests" "缺少覆盖率报告" "LOW" "运行: pytest --cov=. tests/"
    }
} else {
    Write-Status "tests/ 目录不存在" "FAIL"
    Add-Issue "Tests" "缺少测试目录" "CRITICAL"
}

# 3. 检查文档完整性
Write-Host "`n========== 文档完整性 ==========" -ForegroundColor Cyan
$maxScore += 15

$criticalDocs = @(
    "README.md",
    "VERSIONS.md",
    "QUICKSTART.md"
)

$docsFound = 0
foreach ($doc in $criticalDocs) {
    $docPath = Join-Path $projectRoot $doc
    if (Test-Path $docPath) {
        $docsFound++
    } else {
        Add-Issue "Documentation" "缺少 $doc" "MEDIUM"
    }
}

$healthScore += [int](($docsFound / $criticalDocs.Count) * 15)
Write-Status "关键文档: $docsFound / $($criticalDocs.Count)" "INFO"

# 检查版本文档
$versionDirs = Get-ChildItem -Path $projectRoot -Directory -Filter "v*" |
    Where-Object { $_.Name -match '^v\d+' }

$versionDocsCount = 0
foreach ($dir in $versionDirs) {
    if (Test-Path (Join-Path $dir.FullName "README.md")) {
        $versionDocsCount++
    }
}

Write-Status "版本文档: $versionDocsCount / $($versionDirs.Count)" "INFO"

# 4. 检查代码质量
Write-Host "`n========== 代码质量 ==========" -ForegroundColor Cyan
$maxScore += 20

# 检查是否配置了 linter
$linterConfigs = @(
    ".ruff.toml",
    "pyproject.toml",
    ".pre-commit-config.yaml"
)

$linterFound = $false
foreach ($config in $linterConfigs) {
    if (Test-Path (Join-Path $projectRoot $config)) {
        $linterFound = $true
        Write-Status "发现代码质量配置: $config" "PASS"
        break
    }
}

if ($linterFound) {
    $healthScore += 10

    if ($full -and -not $quick) {
        try {
            # 运行 ruff 检查（如果安装）
            & $pythonExe -m ruff check . --quiet 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Status "Ruff 检查通过" "PASS"
                $healthScore += 10
            } else {
                Write-Status "Ruff 发现代码问题" "WARN"
                Add-Issue "Code Quality" "Ruff linting 失败" "MEDIUM" "运行: ruff check . --fix"
                $healthScore += 5
            }
        }
        catch {
            Write-Status "无法运行 Ruff (可能未安装)" "WARN"
        }
    } else {
        $healthScore += 5
    }
} else {
    Write-Status "未配置代码质量工具" "WARN"
    Add-Issue "Code Quality" "缺少 linter 配置" "LOW" "创建 .ruff.toml 或 pyproject.toml"
}

# 5. 检查数据完整性
Write-Host "`n========== 数据完整性 ==========" -ForegroundColor Cyan
$maxScore += 15

# 检查数据库
$dbPath = Join-Path $projectRoot "data_storage\simulation_results.db"
if (Test-Path $dbPath) {
    $dbSize = (Get-Item $dbPath).Length / 1MB
    Write-Status "数据库存在 ($([math]::Round($dbSize, 2)) MB)" "PASS"
    $healthScore += 10

    # 检查数据版本控制
    if (Test-Path "$projectRoot\data_versioning") {
        Write-Status "数据版本控制系统存在" "PASS"
        $healthScore += 5
    } else {
        Write-Status "缺少数据版本控制" "WARN"
        Add-Issue "Data" "未配置数据版本控制" "LOW"
    }
} else {
    Write-Status "数据库不存在" "WARN"
    Add-Issue "Data" "缺少数据库文件" "MEDIUM"
}

# 6. 检查版本输出数据
Write-Host "`n========== 版本数据 ==========" -ForegroundColor Cyan
$maxScore += 10

$versionWithData = 0
$coreVersions = @("v10_rolling_foot_biomimetic_gait", "v13_7_friction_compensation", "v17_state_estimation")

foreach ($version in $coreVersions) {
    $outDir = Join-Path $projectRoot "$version\out"
    if (Test-Path $outDir) {
        $dataFiles = Get-ChildItem -Path $outDir -Recurse -File | Measure-Object
        if ($dataFiles.Count -gt 0) {
            $versionWithData++
        }
    }
}

$healthScore += [int](($versionWithData / $coreVersions.Count) * 10)
Write-Status "核心版本数据: $versionWithData / $($coreVersions.Count)" "INFO"

# 7. 检查自动化脚本
Write-Host "`n========== 自动化脚本 ==========" -ForegroundColor Cyan
$maxScore += 10

$expectedScripts = @(
    "batch_run_all_versions.ps1",
    "generate_all_animations.ps1",
    "update_all_docs.ps1",
    "check_project_health.ps1"
)

$scriptsFound = 0
foreach ($script in $expectedScripts) {
    if (Test-Path (Join-Path $projectRoot "scripts\$script")) {
        $scriptsFound++
    }
}

$healthScore += [int](($scriptsFound / $expectedScripts.Count) * 10)
Write-Status "自动化脚本: $scriptsFound / $($expectedScripts.Count)" "INFO"

# 计算健康分数
$healthPercentage = [int](($healthScore / $maxScore) * 100)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "项目健康评分: $healthScore / $maxScore ($healthPercentage%)" -ForegroundColor $(
    if ($healthPercentage -ge 80) { "Green" }
    elseif ($healthPercentage -ge 60) { "Yellow" }
    else { "Red" }
)
Write-Host "========================================" -ForegroundColor Cyan

# 生成报告
$reportContent = @"
hw-1 项目健康检查报告
生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

总体评分: $healthScore / $maxScore ($healthPercentage%)

评分等级:
- 80-100%: 优秀 ✓
- 60-79%: 良好 ⚠
- 40-59%: 需要改进 ⚠⚠
- 0-39%: 需要紧急修复 ✗

检查项:
1. 环境配置: $($healthScore -ge 8 ? "✓" : "✗")
2. 测试覆盖率: $($healthScore -ge 15 ? "✓" : "✗")
3. 文档完整性: $($healthScore -ge 10 ? "✓" : "✗")
4. 代码质量: $($healthScore -ge 15 ? "✓" : "✗")
5. 数据完整性: $($healthScore -ge 10 ? "✓" : "✗")
6. 版本数据: $($healthScore -ge 7 ? "✓" : "✗")
7. 自动化脚本: $($scriptsFound -ge 3 ? "✓" : "✗")

"@

if ($issues.Count -gt 0) {
    $reportContent += "`n发现的问题 ($($issues.Count) 项):`n"
    $reportContent += "=" * 50 + "`n"

    # 按严重程度排序
    $sortedIssues = $issues | Sort-Object @{
        Expression = {
            switch ($_.severity) {
                "CRITICAL" { 0 }
                "HIGH" { 1 }
                "MEDIUM" { 2 }
                "LOW" { 3 }
                default { 4 }
            }
        }
    }

    foreach ($issue in $sortedIssues) {
        $reportContent += "`n[$($issue.severity)] $($issue.category): $($issue.description)`n"
        if ($issue.fix) {
            $reportContent += "  修复建议: $($issue.fix)`n"
        }
    }
}

$reportContent += "`n建议:`n"
$reportContent += "=" * 50 + "`n"

if ($healthPercentage -ge 80) {
    $reportContent += "- 项目健康状况良好，继续保持！`n"
} elseif ($healthPercentage -ge 60) {
    $reportContent += "- 项目健康状况良好，但有改进空间`n"
    $reportContent += "- 优先解决 HIGH 和 CRITICAL 级别的问题`n"
} else {
    $reportContent += "- 项目需要紧急改进`n"
    $reportContent += "- 立即处理 CRITICAL 级别的问题`n"
    $reportContent += "- 建议运行: .\scripts\check_project_health.ps1 -fix`n"
}

Set-Content -Path $reportPath -Value $reportContent -Encoding UTF8

Write-Host "`n报告已保存到: $reportPath" -ForegroundColor Green

# 如果指定了 -fix，尝试自动修复
if ($fix) {
    Write-Host "`n========== 自动修复 ==========" -ForegroundColor Cyan

    foreach ($issue in $issues) {
        if ($issue.fix -and $issue.severity -in @("HIGH", "CRITICAL")) {
            Write-Host "尝试修复: $($issue.description)" -ForegroundColor Yellow
            # 这里可以添加自动修复逻辑
        }
    }
}

# 显示问题摘要
if ($issues.Count -gt 0) {
    Write-Host "`n问题摘要:" -ForegroundColor Yellow
    $criticalCount = ($issues | Where-Object { $_.severity -eq "CRITICAL" }).Count
    $highCount = ($issues | Where-Object { $_.severity -eq "HIGH" }).Count
    $mediumCount = ($issues | Where-Object { $_.severity -eq "MEDIUM" }).Count
    $lowCount = ($issues | Where-Object { $_.severity -eq "LOW" }).Count

    if ($criticalCount -gt 0) { Write-Host "  CRITICAL: $criticalCount" -ForegroundColor Red }
    if ($highCount -gt 0) { Write-Host "  HIGH: $highCount" -ForegroundColor Red }
    if ($mediumCount -gt 0) { Write-Host "  MEDIUM: $mediumCount" -ForegroundColor Yellow }
    if ($lowCount -gt 0) { Write-Host "  LOW: $lowCount" -ForegroundColor Gray }
}

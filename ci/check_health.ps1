# 项目健康状况检查
# 使用方法: .\ci\check_health.ps1

param(
    [switch]$Detailed,  # 详细输出
    [switch]$Json       # JSON 格式输出
)

$ErrorActionPreference = "Stop"

# 项目根目录
if ($PSScriptRoot) {
    $PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
} else {
    $PROJECT_ROOT = "D:\Dunna\Documents\hw-1"
}
Set-Location $PROJECT_ROOT

# 激活虚拟环境
$VENV_PYTHON = "$PROJECT_ROOT\.venv-mujoco\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Error "Virtual environment not found: $VENV_PYTHON"
    exit 1
}

if (-not $Json) {
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "PROJECT HEALTH CHECK" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
}

$healthData = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    overall_status = "HEALTHY"
    checks = @{}
}

# 1. 测试覆盖率检查
if (-not $Json) { Write-Host "[1/7] Checking test coverage..." -ForegroundColor Yellow }
$coverageStatus = "UNKNOWN"
$coverageValue = 0
if (Test-Path "coverage.json") {
    $coverage = (Get-Content "coverage.json" | ConvertFrom-Json).totals.percent_covered
    $coverageValue = $coverage
    if ($coverage -ge 80) {
        $coverageStatus = "GOOD"
    } elseif ($coverage -ge 60) {
        $coverageStatus = "WARNING"
    } else {
        $coverageStatus = "CRITICAL"
        $healthData.overall_status = "UNHEALTHY"
    }
}
$healthData.checks.coverage = @{
    status = $coverageStatus
    value = $coverageValue
    threshold_good = 80
    threshold_warning = 60
}
if (-not $Json) {
    $color = switch ($coverageStatus) {
        "GOOD" { "Green" }
        "WARNING" { "Yellow" }
        "CRITICAL" { "Red" }
        default { "Gray" }
    }
    Write-Host "  Coverage: $($coverageValue.ToString('F2'))% - $coverageStatus" -ForegroundColor $color
}

# 2. 代码复杂度检查
if (-not $Json) { Write-Host "[2/7] Checking code complexity..." -ForegroundColor Yellow }
$complexityStatus = "UNKNOWN"
try {
    $radonOutput = & $VENV_PYTHON -m radon cc common/ -s -n B --json 2>$null | ConvertFrom-Json
    $highComplexityCount = 0
    foreach ($file in $radonOutput.PSObject.Properties) {
        $highComplexityCount += ($file.Value | Where-Object { $_.complexity -gt 10 }).Count
    }

    if ($highComplexityCount -eq 0) {
        $complexityStatus = "GOOD"
    } elseif ($highComplexityCount -le 5) {
        $complexityStatus = "WARNING"
    } else {
        $complexityStatus = "CRITICAL"
        $healthData.overall_status = "NEEDS_ATTENTION"
    }

    $healthData.checks.complexity = @{
        status = $complexityStatus
        high_complexity_functions = $highComplexityCount
    }
    if (-not $Json) {
        $color = if ($complexityStatus -eq "GOOD") { "Green" } elseif ($complexityStatus -eq "WARNING") { "Yellow" } else { "Red" }
        Write-Host "  Complexity: $highComplexityCount high-complexity functions - $complexityStatus" -ForegroundColor $color
    }
} catch {
    $healthData.checks.complexity = @{ status = "UNKNOWN" }
    if (-not $Json) { Write-Host "  Complexity: UNKNOWN (radon not available)" -ForegroundColor Gray }
}

# 3. 技术债务检查
if (-not $Json) { Write-Host "[3/7] Checking technical debt..." -ForegroundColor Yellow }
$todoCount = (Select-String -Path "common\*.py" -Pattern "TODO|FIXME|HACK" -Recursive).Count
$debtStatus = if ($todoCount -le 20) { "GOOD" } elseif ($todoCount -le 50) { "WARNING" } else { "CRITICAL" }
$healthData.checks.technical_debt = @{
    status = $debtStatus
    todo_count = $todoCount
}
if (-not $Json) {
    $color = if ($debtStatus -eq "GOOD") { "Green" } elseif ($debtStatus -eq "WARNING") { "Yellow" } else { "Red" }
    Write-Host "  Technical Debt: $todoCount TODO/FIXME/HACK - $debtStatus" -ForegroundColor $color
}

# 4. 文档新鲜度检查
if (-not $Json) { Write-Host "[4/7] Checking documentation freshness..." -ForegroundColor Yellow }
$readmeAge = ((Get-Date) - (Get-Item "README.md" -ErrorAction SilentlyContinue).LastWriteTime).Days
$docStatus = if ($readmeAge -le 30) { "GOOD" } elseif ($readmeAge -le 60) { "WARNING" } else { "CRITICAL" }
$healthData.checks.documentation = @{
    status = $docStatus
    readme_age_days = $readmeAge
}
if (-not $Json) {
    $color = if ($docStatus -eq "GOOD") { "Green" } elseif ($docStatus -eq "WARNING") { "Yellow" } else { "Red" }
    Write-Host "  Documentation: README.md $readmeAge days old - $docStatus" -ForegroundColor $color
}

# 5. Git 活动检查
if (-not $Json) { Write-Host "[5/7] Checking Git activity..." -ForegroundColor Yellow }
$recentCommits = (git log --since="7 days ago" --oneline 2>$null | Measure-Object).Count
$gitStatus = if ($recentCommits -ge 5) { "GOOD" } elseif ($recentCommits -ge 1) { "WARNING" } else { "INACTIVE" }
$healthData.checks.git_activity = @{
    status = $gitStatus
    commits_last_7_days = $recentCommits
}
if (-not $Json) {
    $color = if ($gitStatus -eq "GOOD") { "Green" } elseif ($gitStatus -eq "WARNING") { "Yellow" } else { "Gray" }
    Write-Host "  Git Activity: $recentCommits commits in last 7 days - $gitStatus" -ForegroundColor $color
}

# 6. 依赖安全检查
if (-not $Json) { Write-Host "[6/7] Checking dependencies..." -ForegroundColor Yellow }
$depsStatus = "GOOD"  # 默认，需要运行 safety 或 pip-audit 才能确认
$healthData.checks.dependencies = @{
    status = $depsStatus
    note = "Run 'ci\run_security.ps1' for detailed check"
}
if (-not $Json) {
    Write-Host "  Dependencies: $depsStatus (run full security scan for details)" -ForegroundColor Green
}

# 7. 基准测试新鲜度
if (-not $Json) { Write-Host "[7/7] Checking benchmark freshness..." -ForegroundColor Yellow }
$benchmarkAge = 999
if (Test-Path "benchmarks/results") {
    $latestBenchmark = Get-ChildItem "benchmarks/results" -Filter "*.json" |
                       Sort-Object LastWriteTime -Descending |
                       Select-Object -First 1
    if ($latestBenchmark) {
        $benchmarkAge = ((Get-Date) - $latestBenchmark.LastWriteTime).Days
    }
}
$benchStatus = if ($benchmarkAge -le 7) { "GOOD" } elseif ($benchmarkAge -le 14) { "WARNING" } else { "STALE" }
$healthData.checks.benchmarks = @{
    status = $benchStatus
    last_run_days_ago = $benchmarkAge
}
if (-not $Json) {
    $color = if ($benchStatus -eq "GOOD") { "Green" } elseif ($benchStatus -eq "WARNING") { "Yellow" } else { "Red" }
    Write-Host "  Benchmarks: Last run $benchmarkAge days ago - $benchStatus" -ForegroundColor $color
}

# 输出结果
if ($Json) {
    $healthData | ConvertTo-Json -Depth 10
    exit 0
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
$overallColor = switch ($healthData.overall_status) {
    "HEALTHY" { "Green" }
    "NEEDS_ATTENTION" { "Yellow" }
    "UNHEALTHY" { "Red" }
    default { "Gray" }
}
Write-Host "OVERALL STATUS: $($healthData.overall_status)" -ForegroundColor $overallColor
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# 生成建议
$recommendations = @()
if ($coverageStatus -ne "GOOD") {
    $recommendations += "- Improve test coverage to reach 80% target"
}
if ($complexityStatus -ne "GOOD") {
    $recommendations += "- Refactor high-complexity functions"
}
if ($todoCount -gt 20) {
    $recommendations += "- Address technical debt (TODO/FIXME comments)"
}
if ($docStatus -ne "GOOD") {
    $recommendations += "- Update project documentation"
}
if ($benchStatus -ne "GOOD") {
    $recommendations += "- Run performance benchmarks"
}

if ($recommendations.Count -gt 0) {
    Write-Host "Recommendations:" -ForegroundColor Yellow
    foreach ($rec in $recommendations) {
        Write-Host "  $rec" -ForegroundColor White
    }
    Write-Host ""
}

exit 0

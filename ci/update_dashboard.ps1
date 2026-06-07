# 自动更新 dashboard 数据
# 使用方法: .\ci\update_dashboard.ps1

param(
    [switch]$Force  # 强制更新即使数据未变化
)

$ErrorActionPreference = "Stop"

# 项目根目录
if ($PSScriptRoot) {
    $PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
} else {
    $PROJECT_ROOT = "D:\Dunna\Documents\hw-1"
}
Set-Location $PROJECT_ROOT

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "UPDATING DASHBOARD DATA" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# 检查 dashboard 目录
if (-not (Test-Path "dashboard")) {
    Write-Warning "Dashboard directory not found. Skipping update."
    exit 0
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$updated = $false

# 1. 更新测试覆盖率数据
Write-Host "Updating test coverage data..." -ForegroundColor Yellow
if (Test-Path "coverage.json") {
    $coverage = Get-Content "coverage.json" | ConvertFrom-Json
    $coveragePercent = $coverage.totals.percent_covered

    # 创建或更新 coverage 历史文件
    $coverageHistoryFile = "dashboard/data/coverage_history.json"

    if (-not (Test-Path "dashboard/data")) {
        New-Item -ItemType Directory -Path "dashboard/data" -Force | Out-Null
    }

    $coverageHistory = @()
    if (Test-Path $coverageHistoryFile) {
        $coverageHistory = Get-Content $coverageHistoryFile | ConvertFrom-Json
    }

    # 添加新数据点
    $newDataPoint = @{
        timestamp = $timestamp
        coverage = $coveragePercent
        lines_covered = $coverage.totals.covered_lines
        lines_total = $coverage.totals.num_statements
    }

    $coverageHistory += $newDataPoint

    # 保留最近 100 个数据点
    if ($coverageHistory.Count -gt 100) {
        $coverageHistory = $coverageHistory | Select-Object -Last 100
    }

    $coverageHistory | ConvertTo-Json -Depth 10 | Out-File -FilePath $coverageHistoryFile -Encoding utf8
    Write-Host "  ✓ Coverage data updated: $($coveragePercent.ToString('F2'))%" -ForegroundColor Green
    $updated = $true
} else {
    Write-Host "  ⚠ No coverage.json found" -ForegroundColor Yellow
}

# 2. 更新基准测试数据
Write-Host "Updating benchmark data..." -ForegroundColor Yellow
if (Test-Path "benchmarks/results") {
    $latestBenchmark = Get-ChildItem "benchmarks/results" -Filter "*.json" |
                       Sort-Object LastWriteTime -Descending |
                       Select-Object -First 1

    if ($latestBenchmark) {
        $benchmarkData = Get-Content $latestBenchmark.FullName | ConvertFrom-Json

        # 复制到 dashboard/data
        $dashboardBenchmarkFile = "dashboard/data/latest_benchmark.json"
        Copy-Item $latestBenchmark.FullName -Destination $dashboardBenchmarkFile -Force

        Write-Host "  ✓ Benchmark data updated: $($latestBenchmark.Name)" -ForegroundColor Green
        $updated = $true
    } else {
        Write-Host "  ⚠ No benchmark results found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ No benchmarks/results directory" -ForegroundColor Yellow
}

# 3. 更新项目统计
Write-Host "Updating project statistics..." -ForegroundColor Yellow

$stats = @{
    timestamp = $timestamp
    git = @{
        total_commits = (git rev-list --count HEAD 2>$null)
        branches = (git branch -a 2>$null | Measure-Object).Count
        last_commit = (git log -1 --format="%h - %s" 2>$null)
    }
    code = @{
        python_files = (Get-ChildItem -Path "common" -Filter "*.py" -Recurse -File | Measure-Object).Count
        total_lines = 0  # 可以用 Get-Content 计算
    }
    tests = @{
        test_files = (Get-ChildItem -Path "tests" -Filter "test_*.py" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    }
}

$statsFile = "dashboard/data/project_stats.json"
$stats | ConvertTo-Json -Depth 10 | Out-File -FilePath $statsFile -Encoding utf8
Write-Host "  ✓ Project statistics updated" -ForegroundColor Green
$updated = $true

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
if ($updated) {
    Write-Host "DASHBOARD DATA UPDATED" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Updated files:" -ForegroundColor Yellow
    Write-Host "  - dashboard/data/coverage_history.json" -ForegroundColor White
    Write-Host "  - dashboard/data/latest_benchmark.json" -ForegroundColor White
    Write-Host "  - dashboard/data/project_stats.json" -ForegroundColor White
} else {
    Write-Host "NO UPDATES PERFORMED" -ForegroundColor Yellow
    Write-Host "=" * 80 -ForegroundColor Cyan
}
Write-Host ""

exit 0

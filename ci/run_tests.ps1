# 运行测试套件
# 使用方法: .\ci\run_tests.ps1 [-Parallel] [-Coverage] [-Markers "unit,regression"]

param(
    [switch]$Parallel,      # 是否并行测试
    [switch]$Coverage,      # 是否生成覆盖率报告
    [string]$Markers = "",  # pytest markers (unit, regression, integration, slow)
    [switch]$Verbose        # 详细输出
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

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "RUNNING TEST SUITE" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# 构建 pytest 参数
$pytest_args = @()

if ($Markers) {
    $pytest_args += "-m", $Markers
    Write-Host "Running tests with markers: $Markers" -ForegroundColor Yellow
}

if ($Parallel) {
    $pytest_args += "-n", "auto"
    Write-Host "Running tests in parallel mode" -ForegroundColor Yellow
}

if ($Coverage) {
    $pytest_args += "--cov=common", "--cov-report=html", "--cov-report=term", "--cov-report=json"
    Write-Host "Coverage reporting enabled" -ForegroundColor Yellow
}

if ($Verbose) {
    $pytest_args += "-vv"
}

Write-Host ""

# 运行测试
$start_time = Get-Date

try {
    & $VENV_PYTHON -m pytest @pytest_args
    $exit_code = $LASTEXITCODE
} catch {
    Write-Error "Failed to run pytest: $_"
    exit 1
}

$elapsed = (Get-Date) - $start_time

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
if ($exit_code -eq 0) {
    Write-Host "TEST SUITE PASSED" -ForegroundColor Green
} else {
    Write-Host "TEST SUITE FAILED" -ForegroundColor Red
}
Write-Host "Elapsed time: $($elapsed.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

if ($Coverage -and $exit_code -eq 0) {
    Write-Host ""
    Write-Host "Coverage report generated:" -ForegroundColor Yellow
    Write-Host "  HTML: htmlcov\index.html" -ForegroundColor Yellow
    Write-Host "  JSON: coverage.json" -ForegroundColor Yellow
}

exit $exit_code

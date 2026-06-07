# 代码质量检查
# 使用方法: .\ci\run_quality.ps1 [-Fix] [-Tool "black|ruff|mypy|all"]

param(
    [switch]$Fix,                    # 自动修复问题（仅 black, ruff）
    [string]$Tool = "all",          # 运行的工具：black, ruff, mypy, radon, all
    [switch]$Strict                 # 严格模式（任何警告都返回错误）
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
Write-Host "CODE QUALITY CHECK" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$failed = $false
$results = @{}

# Black 格式检查
if ($Tool -eq "all" -or $Tool -eq "black") {
    Write-Host "[1/4] Running Black..." -ForegroundColor Yellow

    if ($Fix) {
        & $VENV_PYTHON -m black .
        $black_exit = $LASTEXITCODE
    } else {
        & $VENV_PYTHON -m black --check --diff .
        $black_exit = $LASTEXITCODE
    }

    $results["Black"] = $black_exit
    if ($black_exit -ne 0) {
        Write-Host "  FAILED: Code formatting issues found" -ForegroundColor Red
        $failed = $true
    } else {
        Write-Host "  PASSED: Code is properly formatted" -ForegroundColor Green
    }
    Write-Host ""
}

# Ruff linting
if ($Tool -eq "all" -or $Tool -eq "ruff") {
    Write-Host "[2/4] Running Ruff..." -ForegroundColor Yellow

    if ($Fix) {
        & $VENV_PYTHON -m ruff check --fix .
        $ruff_exit = $LASTEXITCODE
    } else {
        & $VENV_PYTHON -m ruff check .
        $ruff_exit = $LASTEXITCODE
    }

    $results["Ruff"] = $ruff_exit
    if ($ruff_exit -ne 0) {
        Write-Host "  FAILED: Linting issues found" -ForegroundColor Red
        $failed = $true
    } else {
        Write-Host "  PASSED: No linting issues" -ForegroundColor Green
    }
    Write-Host ""
}

# Mypy 类型检查
if ($Tool -eq "all" -or $Tool -eq "mypy") {
    Write-Host "[3/4] Running Mypy..." -ForegroundColor Yellow

    & $VENV_PYTHON -m mypy common/
    $mypy_exit = $LASTEXITCODE

    $results["Mypy"] = $mypy_exit
    if ($mypy_exit -ne 0) {
        Write-Host "  FAILED: Type checking issues found" -ForegroundColor Red
        if ($Strict) {
            $failed = $true
        } else {
            Write-Host "  (Non-strict mode: continuing...)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  PASSED: Type checking passed" -ForegroundColor Green
    }
    Write-Host ""
}

# Radon 代码复杂度分析
if ($Tool -eq "all" -or $Tool -eq "radon") {
    Write-Host "[4/4] Running Radon (Cyclomatic Complexity)..." -ForegroundColor Yellow

    # 检查是否安装了 radon
    & $VENV_PYTHON -m pip show radon 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  SKIPPED: radon not installed (pip install radon)" -ForegroundColor Yellow
        $results["Radon"] = 0
    } else {
        # 显示复杂度 > 10 的函数（B 级及以上）
        $radon_output = & $VENV_PYTHON -m radon cc common/ -s -n B 2>&1

        if ($radon_output -match "Average complexity") {
            Write-Host $radon_output
            Write-Host "  WARNING: High complexity functions found" -ForegroundColor Yellow
            $results["Radon"] = 1
            if ($Strict) {
                $failed = $true
            }
        } else {
            Write-Host "  PASSED: All functions have acceptable complexity" -ForegroundColor Green
            $results["Radon"] = 0
        }
    }
    Write-Host ""
}

# 总结
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

foreach ($key in $results.Keys) {
    $status = if ($results[$key] -eq 0) { "PASS" } else { "FAIL" }
    $color = if ($results[$key] -eq 0) { "Green" } else { "Red" }
    Write-Host "$($key.PadRight(15)): $status" -ForegroundColor $color
}

Write-Host ""

if ($failed) {
    Write-Host "QUALITY CHECK FAILED" -ForegroundColor Red
    Write-Host "=" * 80 -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "QUALITY CHECK PASSED" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Cyan
    exit 0
}

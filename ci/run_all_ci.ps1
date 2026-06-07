# 运行完整 CI 流程
# 使用方法: .\ci\run_all_ci.ps1 [-Quick] [-NoBenchmarks] [-NoTests]

param(
    [switch]$Quick,              # 快速模式（跳过慢速测试和完整基准）
    [switch]$NoBenchmarks,       # 跳过基准测试
    [switch]$NoTests,            # 跳过测试套件
    [switch]$Fix,                # 自动修复代码质量问题
    [switch]$GenerateDocs        # 生成文档
)

$ErrorActionPreference = "Stop"

# 项目根目录
if ($PSScriptRoot) {
    $PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
} else {
    $PROJECT_ROOT = "D:\Dunna\Documents\hw-1"
}
Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host "HW-1 PROJECT CI/CD PIPELINE" -ForegroundColor Magenta
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host ""
Write-Host "Start time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

$global_start = Get-Date
$failed_steps = @()
$passed_steps = @()

# 步骤 1: 代码质量检查
Write-Host ""
Write-Host "▶ STEP 1/4: Code Quality Check" -ForegroundColor Cyan
Write-Host "-" * 80 -ForegroundColor Gray

$step_start = Get-Date
try {
    $base_args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$PROJECT_ROOT\ci\run_quality.ps1")
    if ($Fix) {
        $base_args += "-Fix"
    }

    $quality_process = Start-Process -FilePath "powershell.exe" `
        -ArgumentList $base_args `
        -NoNewWindow -Wait -PassThru

    if ($quality_process.ExitCode -eq 0) {
        $passed_steps += "Code Quality"
        Write-Host "✓ Code Quality Check PASSED" -ForegroundColor Green
    } else {
        $failed_steps += "Code Quality"
        Write-Host "✗ Code Quality Check FAILED" -ForegroundColor Red
    }
} catch {
    $failed_steps += "Code Quality"
    Write-Host "✗ Code Quality Check ERROR: $_" -ForegroundColor Red
}
$step_elapsed = ((Get-Date) - $step_start).TotalSeconds
Write-Host "  Duration: $($step_elapsed.ToString('F2'))s" -ForegroundColor Gray

# 步骤 2: 测试套件
if (-not $NoTests) {
    Write-Host ""
    Write-Host "▶ STEP 2/4: Test Suite" -ForegroundColor Cyan
    Write-Host "-" * 80 -ForegroundColor Gray

    $step_start = Get-Date
    try {
        $base_args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$PROJECT_ROOT\ci\run_tests.ps1", "-Coverage")

        if ($Quick) {
            # 快速模式：跳过标记过滤（全部测试更快）
            # $base_args += "-Markers", "unit"
        } else {
            # 完整模式：并行运行所有测试
            $base_args += "-Parallel"
        }

        $test_process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList $base_args `
            -NoNewWindow -Wait -PassThru

        if ($test_process.ExitCode -eq 0) {
            $passed_steps += "Test Suite"
            Write-Host "✓ Test Suite PASSED" -ForegroundColor Green
        } else {
            $failed_steps += "Test Suite"
            Write-Host "✗ Test Suite FAILED" -ForegroundColor Red
        }
    } catch {
        $failed_steps += "Test Suite"
        Write-Host "✗ Test Suite ERROR: $_" -ForegroundColor Red
    }
    $step_elapsed = ((Get-Date) - $step_start).TotalSeconds
    Write-Host "  Duration: $($step_elapsed.ToString('F2'))s" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "▶ STEP 2/4: Test Suite [SKIPPED]" -ForegroundColor Yellow
}

# 步骤 3: 性能基准
if (-not $NoBenchmarks) {
    Write-Host ""
    Write-Host "▶ STEP 3/4: Performance Benchmarks" -ForegroundColor Cyan
    Write-Host "-" * 80 -ForegroundColor Gray

    $step_start = Get-Date
    try {
        $base_args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$PROJECT_ROOT\ci\run_benchmarks.ps1", "-Compare")

        if ($Quick) {
            # 快速模式：只测试关键版本
            $base_args += "-Versions", "v10,v13_7_refactored,v17"
        } else {
            # 完整模式：生成可视化报告
            $base_args += "-GenerateReport"
        }

        $bench_process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList $base_args `
            -NoNewWindow -Wait -PassThru

        if ($bench_process.ExitCode -eq 0) {
            $passed_steps += "Benchmarks"
            Write-Host "✓ Performance Benchmarks PASSED" -ForegroundColor Green
        } else {
            $failed_steps += "Benchmarks"
            Write-Host "✗ Performance Benchmarks FAILED (regression detected)" -ForegroundColor Red
        }
    } catch {
        $failed_steps += "Benchmarks"
        Write-Host "✗ Performance Benchmarks ERROR: $_" -ForegroundColor Red
    }
    $step_elapsed = ((Get-Date) - $step_start).TotalSeconds
    Write-Host "  Duration: $($step_elapsed.ToString('F2'))s" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "▶ STEP 3/4: Performance Benchmarks [SKIPPED]" -ForegroundColor Yellow
}

# 步骤 4: 文档生成
if ($GenerateDocs) {
    Write-Host ""
    Write-Host "▶ STEP 4/4: Documentation Generation" -ForegroundColor Cyan
    Write-Host "-" * 80 -ForegroundColor Gray

    $step_start = Get-Date
    try {
        $base_args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$PROJECT_ROOT\ci\generate_docs.ps1", "-UpdateBadges")

        $docs_process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList $base_args `
            -NoNewWindow -Wait -PassThru

        if ($docs_process.ExitCode -eq 0) {
            $passed_steps += "Documentation"
            Write-Host "✓ Documentation Generation PASSED" -ForegroundColor Green
        } else {
            # 文档生成失败不影响整体流程
            Write-Host "⚠ Documentation Generation completed with warnings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠ Documentation Generation ERROR: $_" -ForegroundColor Yellow
    }
    $step_elapsed = ((Get-Date) - $step_start).TotalSeconds
    Write-Host "  Duration: $($step_elapsed.ToString('F2'))s" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "▶ STEP 4/4: Documentation Generation [SKIPPED]" -ForegroundColor Yellow
}

# 最终报告
$global_elapsed = ((Get-Date) - $global_start).TotalSeconds

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host "CI/CD PIPELINE SUMMARY" -ForegroundColor Magenta
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host ""

Write-Host "Total Duration: $($global_elapsed.ToString('F2'))s" -ForegroundColor Cyan
Write-Host ""

if ($passed_steps.Count -gt 0) {
    Write-Host "Passed Steps ($($passed_steps.Count)):" -ForegroundColor Green
    foreach ($step in $passed_steps) {
        Write-Host "  ✓ $step" -ForegroundColor Green
    }
    Write-Host ""
}

if ($failed_steps.Count -gt 0) {
    Write-Host "Failed Steps ($($failed_steps.Count)):" -ForegroundColor Red
    foreach ($step in $failed_steps) {
        Write-Host "  ✗ $step" -ForegroundColor Red
    }
    Write-Host ""
}

if ($failed_steps.Count -eq 0) {
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host "CI/CD PIPELINE PASSED" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host ""
    exit 0
} else {
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host "CI/CD PIPELINE FAILED" -ForegroundColor Red
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix the failing steps and run again:" -ForegroundColor Yellow
    Write-Host "  .\ci\run_all_ci.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

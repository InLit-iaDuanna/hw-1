# 运行性能基准测试并检测回归
# 使用方法: .\ci\run_benchmarks.ps1 [-Versions "v10,v13_7,v17"] [-Compare] [-Threshold 10]

param(
    [string]$Versions = "",         # 要测试的版本，逗号分隔，默认全部
    [switch]$Compare,               # 与上次结果对比
    [int]$Threshold = 10,          # 性能退化阈值（百分比）
    [switch]$GenerateReport        # 生成完整可视化报告
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
Write-Host "PERFORMANCE BENCHMARK" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$BENCHMARK_RUNNER = "$PROJECT_ROOT\benchmarks\benchmark_runner.py"
$RESULTS_DIR = "$PROJECT_ROOT\benchmarks\results"

if (-not (Test-Path $BENCHMARK_RUNNER)) {
    Write-Error "Benchmark runner not found: $BENCHMARK_RUNNER"
    exit 1
}

# 生成时间戳文件名
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$output_file = "benchmark_$timestamp.json"

# 构建参数
$benchmark_args = @("--output", $output_file)

if ($Versions) {
    $version_list = $Versions -split ","
    $benchmark_args += "--versions"
    $benchmark_args += $version_list
    Write-Host "Testing versions: $Versions" -ForegroundColor Yellow
} else {
    Write-Host "Testing all available versions" -ForegroundColor Yellow
}

Write-Host ""

# 运行基准测试
$start_time = Get-Date

try {
    & $VENV_PYTHON $BENCHMARK_RUNNER @benchmark_args
    $exit_code = $LASTEXITCODE
} catch {
    Write-Error "Failed to run benchmark: $_"
    exit 1
}

$elapsed = (Get-Date) - $start_time

if ($exit_code -ne 0) {
    Write-Host ""
    Write-Host "BENCHMARK FAILED" -ForegroundColor Red
    exit $exit_code
}

Write-Host ""
Write-Host "Benchmark completed in $($elapsed.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Green
Write-Host ""

# 对比历史结果
if ($Compare) {
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "REGRESSION DETECTION" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""

    # 查找最近的两个结果文件
    $result_files = Get-ChildItem -Path $RESULTS_DIR -Filter "benchmark_*.json" | Sort-Object LastWriteTime -Descending

    if ($result_files.Count -lt 2) {
        Write-Host "Not enough benchmark results to compare (need at least 2)" -ForegroundColor Yellow
        Write-Host "Current result saved as baseline: $output_file" -ForegroundColor Yellow
    } else {
        $current_file = $result_files[0].FullName
        $baseline_file = $result_files[1].FullName

        Write-Host "Comparing:" -ForegroundColor Yellow
        Write-Host "  Current:  $($result_files[0].Name)" -ForegroundColor Yellow
        Write-Host "  Baseline: $($result_files[1].Name)" -ForegroundColor Yellow
        Write-Host ""

        # 加载 JSON 结果
        $current_data = Get-Content $current_file -Raw | ConvertFrom-Json
        $baseline_data = Get-Content $baseline_file -Raw | ConvertFrom-Json

        # 创建版本映射
        $baseline_map = @{}
        foreach ($result in $baseline_data) {
            $baseline_map[$result.version] = $result
        }

        $regressions = @()
        $improvements = @()

        foreach ($current in $current_data) {
            $version = $current.version
            if (-not $baseline_map.ContainsKey($version)) {
                Write-Host "[$version] New version (no baseline)" -ForegroundColor Cyan
                continue
            }

            $baseline = $baseline_map[$version]

            # 检查成功状态变化
            if ($baseline.success -and -not $current.success) {
                Write-Host "[$version] REGRESSION: Previously successful, now failing!" -ForegroundColor Red
                $regressions += @{
                    version = $version
                    metric = "success"
                    change = "FAIL"
                }
                continue
            }

            if (-not $current.success) {
                Write-Host "[$version] Still failing (no comparison)" -ForegroundColor Yellow
                continue
            }

            # 对比 CoT（越低越好）
            if ($baseline.cot -gt 0 -and $current.cot -gt 0) {
                $cot_change = (($current.cot - $baseline.cot) / $baseline.cot) * 100
                if ($cot_change -gt $Threshold) {
                    Write-Host "[$version] REGRESSION: CoT increased by $($cot_change.ToString('F1'))%" -ForegroundColor Red
                    Write-Host "  Baseline: $($baseline.cot.ToString('F3')), Current: $($current.cot.ToString('F3'))" -ForegroundColor Red
                    $regressions += @{
                        version = $version
                        metric = "CoT"
                        change = $cot_change
                    }
                } elseif ($cot_change -lt -$Threshold) {
                    Write-Host "[$version] IMPROVEMENT: CoT decreased by $([Math]::Abs($cot_change).ToString('F1'))%" -ForegroundColor Green
                    $improvements += @{
                        version = $version
                        metric = "CoT"
                        change = $cot_change
                    }
                } else {
                    Write-Host "[$version] CoT: $($cot_change.ToString('F1'))% (within threshold)" -ForegroundColor Gray
                }
            }

            # 对比仿真时间（越低越好）
            if ($baseline.simulation_time -gt 0 -and $current.simulation_time -gt 0) {
                $time_change = (($current.simulation_time - $baseline.simulation_time) / $baseline.simulation_time) * 100
                if ($time_change -gt $Threshold) {
                    Write-Host "[$version] WARNING: Simulation time increased by $($time_change.ToString('F1'))%" -ForegroundColor Yellow
                }
            }
        }

        Write-Host ""
        Write-Host "=" * 80 -ForegroundColor Cyan
        Write-Host "REGRESSION SUMMARY" -ForegroundColor Cyan
        Write-Host "=" * 80 -ForegroundColor Cyan

        if ($regressions.Count -eq 0) {
            Write-Host "No performance regressions detected" -ForegroundColor Green
            $regression_exit = 0
        } else {
            Write-Host "Performance regressions detected: $($regressions.Count)" -ForegroundColor Red
            foreach ($reg in $regressions) {
                Write-Host "  - $($reg.version): $($reg.metric) $($reg.change)" -ForegroundColor Red
            }
            $regression_exit = 1
        }

        if ($improvements.Count -gt 0) {
            Write-Host ""
            Write-Host "Performance improvements: $($improvements.Count)" -ForegroundColor Green
            foreach ($imp in $improvements) {
                Write-Host "  + $($imp.version): $($imp.metric) improved by $([Math]::Abs($imp.change).ToString('F1'))%" -ForegroundColor Green
            }
        }

        Write-Host ""

        if ($regression_exit -ne 0) {
            exit $regression_exit
        }
    }
}

# 生成可视化报告
if ($GenerateReport) {
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "GENERATING VISUALIZATION REPORT" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""

    $latest_result = Get-ChildItem -Path $RESULTS_DIR -Filter "benchmark_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if ($latest_result) {
        try {
            & $VENV_PYTHON $BENCHMARK_RUNNER --load $latest_result.Name
            Write-Host ""
            Write-Host "Report generated in: benchmarks\results\" -ForegroundColor Green
            Write-Host "  - performance_evolution.png" -ForegroundColor Green
            Write-Host "  - radar_comparison.png" -ForegroundColor Green
            Write-Host "  - benchmark_report.txt" -ForegroundColor Green
        } catch {
            Write-Host "Failed to generate report: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "BENCHMARK COMPLETE" -ForegroundColor Green
exit 0

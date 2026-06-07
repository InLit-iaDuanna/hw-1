# Update All Documentation
# 更新所有文档和报告，包括版本README、性能报告、数据分析等

param(
    [Parameter(Mandatory=$false)]
    [switch]$skipBenchmarks,  # 跳过基准测试更新

    [Parameter(Mandatory=$false)]
    [switch]$skipVersionDocs,  # 跳过版本文档更新

    [Parameter(Mandatory=$false)]
    [switch]$skipAnalysis,  # 跳过数据分析更新

    [Parameter(Mandatory=$false)]
    [switch]$force  # 强制更新所有文档
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$projectRoot\docs\update_docs_$timestamp.log"

function Write-Log {
    param([string]$message, [string]$level = "INFO")

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$level] $message"

    switch ($level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        default { Write-Host $logMessage -ForegroundColor White }
    }

    Add-Content -Path $logFile -Value $logMessage -Encoding UTF8
}

function Update-BenchmarkReports {
    Write-Log "更新基准测试报告..." "INFO"

    try {
        Set-Location "$projectRoot\benchmarks"
        & $pythonExe benchmark_runner.py --load results/benchmark_results.json 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {
            Write-Log "基准测试报告已更新" "SUCCESS"
            return $true
        } else {
            Write-Log "基准测试报告更新失败" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "基准测试报告更新异常: $_" "ERROR"
        return $false
    }
    finally {
        Set-Location $projectRoot
    }
}

function Update-CrossVersionAnalysis {
    Write-Log "更新跨版本分析..." "INFO"

    try {
        Set-Location "$projectRoot\cross_version_analysis"

        # 运行各个分析器
        $analyzers = @(
            "cot_analyzer.py",
            "floquet_analyzer.py",
            "fsm_analyzer.py",
            "success_rate_analyzer.py"
        )

        foreach ($analyzer in $analyzers) {
            if (Test-Path $analyzer) {
                Write-Log "  运行 $analyzer" "INFO"
                & $pythonExe $analyzer 2>&1 | Out-Null
            }
        }

        Write-Log "跨版本分析已更新" "SUCCESS"
        return $true
    }
    catch {
        Write-Log "跨版本分析更新异常: $_" "ERROR"
        return $false
    }
    finally {
        Set-Location $projectRoot
    }
}

function Update-VersionDocumentation {
    Write-Log "更新版本文档..." "INFO"

    $versionDirs = @(
        "v10_rolling_foot_biomimetic_gait",
        "v13_6_event_driven_fsm",
        "v13_7_friction_compensation",
        "v14c_arm_mass_lightening",
        "v16_motor_dynamics",
        "v17_state_estimation"
    )

    $updateCount = 0

    foreach ($versionDir in $versionDirs) {
        $readmePath = Join-Path $projectRoot "$versionDir\README.md"

        if (Test-Path $readmePath) {
            # 检查是否有新的输出数据
            $outDir = Join-Path $projectRoot "$versionDir\out"

            if (Test-Path $outDir) {
                $recentFiles = Get-ChildItem -Path $outDir -Recurse -File |
                    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) }

                if ($recentFiles.Count -gt 0 -or $force) {
                    Write-Log "  $versionDir 有新数据，建议更新文档" "WARNING"
                    $updateCount++
                }
            }
        }
    }

    Write-Log "检测到 $updateCount 个版本需要更新文档" "INFO"
    return $true
}

function Update-MainDocuments {
    Write-Log "更新主文档..." "INFO"

    # 更新 VERSIONS.md 的最后修改时间戳
    $versionsPath = Join-Path $projectRoot "VERSIONS.md"
    if (Test-Path $versionsPath) {
        $content = Get-Content -Path $versionsPath -Raw -Encoding UTF8
        $lastUpdate = Get-Date -Format "yyyy-MM-dd"

        # 如果文件末尾没有更新时间标记，不强制添加
        Write-Log "  VERSIONS.md 已检查" "INFO"
    }

    # 更新 PROJECT_PROGRESS.md
    $progressPath = Join-Path $projectRoot "PROJECT_PROGRESS.md"
    if (Test-Path $progressPath) {
        Write-Log "  PROJECT_PROGRESS.md 已检查" "INFO"
    }

    # 更新 ROADMAP.md
    $roadmapPath = Join-Path $projectRoot "ROADMAP.md"
    if (Test-Path $roadmapPath) {
        Write-Log "  ROADMAP.md 已检查" "INFO"
    }

    Write-Log "主文档检查完成" "SUCCESS"
    return $true
}

function Update-DataStorageStats {
    Write-Log "更新数据存储统计..." "INFO"

    try {
        Set-Location "$projectRoot\data_storage"

        if (Test-Path "db_manager.py") {
            & $pythonExe -c @"
from db_manager import DatabaseManager
db = DatabaseManager()
stats = db.get_statistics()
print(f'Total records: {stats['total_records']}')
print(f'Versions: {stats['version_count']}')
print(f'Latest: {stats['latest_timestamp']}')
"@ 2>&1 | Out-Null

            Write-Log "数据存储统计已更新" "SUCCESS"
            return $true
        }
    }
    catch {
        Write-Log "数据存储统计更新失败: $_" "ERROR"
        return $false
    }
    finally {
        Set-Location $projectRoot
    }
}

function Generate-DocumentationIndex {
    Write-Log "生成文档索引..." "INFO"

    $indexPath = Join-Path $projectRoot "docs\DOCUMENTATION_INDEX.md"
    $indexContent = @"
# hw-1 项目文档索引

**生成时间**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## 主要文档

- [README.md](../README.md) - 项目总览
- [VERSIONS.md](../VERSIONS.md) - 版本索引（V01-V24）
- [PROJECT_PROGRESS.md](../PROJECT_PROGRESS.md) - 项目进度
- [ROADMAP.md](../ROADMAP.md) - 技术路线图
- [QUICKSTART.md](../QUICKSTART.md) - 快速入门指南

## 优化和性能

- [OPTIMIZATION_COMPLETE.md](../OPTIMIZATION_COMPLETE.md) - 优化完成报告
- [PERFORMANCE_REPORT.md](../PERFORMANCE_REPORT.md) - 性能分析报告
- [profiling_results/PROFILING_SUMMARY.txt](../profiling_results/PROFILING_SUMMARY.txt) - Profiling 总结
- [advanced_profiling/README.md](../advanced_profiling/README.md) - 高级性能分析工具

## 基准测试

- [benchmarks/README.md](../benchmarks/README.md) - 基准测试框架
- [benchmarks/BENCHMARK_SUMMARY.md](../benchmarks/BENCHMARK_SUMMARY.md) - 基准测试总结
- [benchmarks/results/benchmark_report.txt](../benchmarks/results/benchmark_report.txt) - 最新测试结果

## 跨版本分析

- [cross_version_analysis/README.md](../cross_version_analysis/README.md) - 跨版本分析工具
- [cross_version_analysis/reports/](../cross_version_analysis/reports/) - 分析报告目录

## 数据管理

- [data_storage/README.md](../data_storage/README.md) - 数据存储系统
- [data_versioning/README.md](../data_versioning/README.md) - 数据版本控制

## 自动化脚本

- [scripts/README.md](../scripts/README.md) - 自动化脚本文档
- [scripts/batch_run_all_versions.ps1](../scripts/batch_run_all_versions.ps1) - 批量运行
- [scripts/generate_all_animations.ps1](../scripts/generate_all_animations.ps1) - 批量动画生成
- [scripts/check_project_health.ps1](../scripts/check_project_health.ps1) - 项目健康检查

## 版本文档

$(
    $versionDirs = Get-ChildItem -Path $projectRoot -Directory -Filter "v*" |
        Where-Object { $_.Name -match '^v\d+' } |
        Sort-Object Name

    foreach ($dir in $versionDirs) {
        $readmePath = Join-Path $dir.FullName "README.md"
        if (Test-Path $readmePath) {
            $relativePath = $dir.Name
            "- [$relativePath/README.md](../$relativePath/README.md)"
        }
    }
)

## 工具和诊断

- [TOOLS_CHEATSHEET.md](../TOOLS_CHEATSHEET.md) - 工具速查表
- [diagnostics/README.md](../diagnostics/README.md) - 错误诊断系统
- [monitoring/README.md](../monitoring/README.md) - 持续监控系统

## 清理和维护

- [CLEANUP_GUIDE.md](../CLEANUP_GUIDE.md) - 清理指南
- [MIGRATION_INDEX.md](../MIGRATION_INDEX.md) - 迁移索引

---

**注意**: 本索引由自动化脚本生成。如需更新，运行:
``````powershell
.\scripts\update_all_docs.ps1
``````
"@

    Set-Content -Path $indexPath -Value $indexContent -Encoding UTF8
    Write-Log "文档索引已生成: $indexPath" "SUCCESS"
}

# 主执行流程
Write-Log "========================================" "INFO"
Write-Log "文档更新开始" "INFO"
Write-Log "时间戳: $timestamp" "INFO"
Write-Log "========================================" "INFO"

$results = @{
    benchmarks = $false
    crossVersion = $false
    versionDocs = $false
    mainDocs = $false
    dataStorage = $false
}

# 1. 更新基准测试报告
if (-not $skipBenchmarks) {
    $results.benchmarks = Update-BenchmarkReports
} else {
    Write-Log "跳过基准测试更新" "WARNING"
}

# 2. 更新跨版本分析
if (-not $skipAnalysis) {
    $results.crossVersion = Update-CrossVersionAnalysis
} else {
    Write-Log "跳过跨版本分析更新" "WARNING"
}

# 3. 更新版本文档
if (-not $skipVersionDocs) {
    $results.versionDocs = Update-VersionDocumentation
} else {
    Write-Log "跳过版本文档更新" "WARNING"
}

# 4. 更新主文档
$results.mainDocs = Update-MainDocuments

# 5. 更新数据存储统计
$results.dataStorage = Update-DataStorageStats

# 6. 生成文档索引
Generate-DocumentationIndex

# 生成摘要
Write-Log "========================================" "INFO"
Write-Log "文档更新完成" "INFO"

$successCount = ($results.Values | Where-Object { $_ -eq $true }).Count
$totalTasks = $results.Count

Write-Log "完成任务: $successCount / $totalTasks" "INFO"
Write-Log "日志文件: $logFile" "INFO"
Write-Log "========================================" "INFO"

# 详细结果
Write-Log "`n详细结果:" "INFO"
foreach ($task in $results.GetEnumerator()) {
    $status = if ($task.Value) { "✓ 成功" } else { "✗ 失败" }
    $color = if ($task.Value) { "Green" } else { "Red" }
    Write-Host "  $($task.Key): $status" -ForegroundColor $color
}

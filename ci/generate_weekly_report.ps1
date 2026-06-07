# 生成每周进度报告
# 使用方法: .\ci\generate_weekly_report.ps1

param(
    [string]$OutputPath = "weekly_reports",
    [switch]$SendEmail  # 预留：发送邮件通知
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
Write-Host "GENERATING WEEKLY REPORT" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$reportDate = Get-Date -Format "yyyy-MM-dd"
$reportFile = "$OutputPath\weekly_report_$reportDate.md"

# 创建输出目录
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

# 收集 Git 统计
Write-Host "Collecting Git statistics..." -ForegroundColor Yellow
$lastWeek = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
$commitCount = (git log --since="$lastWeek" --oneline).Count
$authors = git log --since="$lastWeek" --format="%an" | Sort-Object -Unique

# 收集测试覆盖率
Write-Host "Collecting test coverage..." -ForegroundColor Yellow
$coverageData = "N/A"
if (Test-Path "coverage.json") {
    $coverage = (Get-Content coverage.json | ConvertFrom-Json).totals.percent_covered
    $coverageData = "$($coverage.ToString('F2'))%"
}

# 收集基准测试结果
Write-Host "Collecting benchmark results..." -ForegroundColor Yellow
$benchmarkStatus = "N/A"
if (Test-Path "benchmarks/results") {
    $latestBenchmark = Get-ChildItem "benchmarks/results" -Filter "*.json" |
                       Sort-Object LastWriteTime -Descending |
                       Select-Object -First 1
    if ($latestBenchmark) {
        $benchmarkStatus = "Latest: $($latestBenchmark.Name)"
    }
}

# 收集待办事项
Write-Host "Collecting TODO items..." -ForegroundColor Yellow
$todoCount = 0
if (Test-Path "common") {
    $todoCount = (Select-String -Path "common\*.py" -Pattern "TODO|FIXME|HACK" -Recursive).Count
}

# 生成报告
Write-Host "Generating report..." -ForegroundColor Yellow

$report = @"
# HW-1 项目周报

**报告日期**: $reportDate
**报告周期**: $(Get-Date $lastWeek -Format 'yyyy-MM-dd') 至 $reportDate

---

## 开发活动

### Git 统计
- **提交次数**: $commitCount
- **活跃贡献者**: $($authors.Count)
$(if ($authors.Count -gt 0) { $authors | ForEach-Object { "  - $_" } } else { "  无" })

### 代码变更
``````bash
$(git diff --stat @{1.week.ago}..HEAD 2>$null)
``````

---

## 质量指标

### 测试覆盖率
- **当前覆盖率**: $coverageData
- **目标**: 80%
- **状态**: $(if ($coverageData -ne "N/A" -and [double]$coverageData.Replace('%','') -ge 80) { "✓ 达标" } elseif ($coverageData -ne "N/A") { "⚠ 未达标" } else { "未测量" })

### 代码质量
- **待办事项 (TODO/FIXME/HACK)**: $todoCount

---

## 性能基准

### 最新基准测试
- **状态**: $benchmarkStatus

$(if (Test-Path "benchmarks/results/benchmark_report.txt") {
    "### 关键指标"
    Get-Content "benchmarks/results/benchmark_report.txt" -Head 30
} else {
    "无最新报告"
})

---

## 本周亮点

<!-- 手动填写本周主要成果 -->
- [ ] 待补充

---

## 下周计划

<!-- 手动填写下周计划 -->
- [ ] 待补充

---

## 问题与风险

$(if ($coverageData -ne "N/A" -and [double]$coverageData.Replace('%','') -lt 70) {
    "- ⚠ **测试覆盖率低于 70%**：当前 $coverageData，需要增加测试用例"
} else { "" })

$(if ($todoCount -gt 50) {
    "- ⚠ **技术债务较高**：有 $todoCount 个待办标记，建议定期清理"
} else { "" })

---

**自动生成时间**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$report | Out-File -FilePath $reportFile -Encoding utf8

Write-Host ""
Write-Host "✓ Report generated: $reportFile" -ForegroundColor Green
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "WEEKLY REPORT COMPLETE" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review the report: $reportFile" -ForegroundColor White
Write-Host "  2. Fill in '本周亮点' and '下周计划' sections" -ForegroundColor White
Write-Host "  3. Share with team or archive for records" -ForegroundColor White
Write-Host ""

exit 0

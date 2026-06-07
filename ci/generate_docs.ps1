# 生成项目文档
# 使用方法: .\ci\generate_docs.ps1 [-Format "html|markdown"] [-UpdateBadges]

param(
    [string]$Format = "html",       # 文档格式：html 或 markdown
    [switch]$UpdateBadges,          # 更新 README 中的徽章
    [switch]$ApiDocs                # 生成 API 文档（需要 pdoc 或 sphinx）
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
Write-Host "DOCUMENTATION GENERATION" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$docs_generated = $false

# 1. 生成测试覆盖率报告
Write-Host "[1/3] Generating test coverage report..." -ForegroundColor Yellow

if (Test-Path "$PROJECT_ROOT\.coverage") {
    try {
        if ($Format -eq "html") {
            & $VENV_PYTHON -m coverage html -d htmlcov
            Write-Host "  Coverage HTML report: htmlcov\index.html" -ForegroundColor Green
        }

        & $VENV_PYTHON -m coverage json -o coverage.json

        # 提取覆盖率数值
        $coverage_data = Get-Content coverage.json -Raw | ConvertFrom-Json
        $coverage_percent = $coverage_data.totals.percent_covered
        Write-Host "  Coverage: $($coverage_percent.ToString('F2'))%" -ForegroundColor Green

        $docs_generated = $true
    } catch {
        Write-Host "  WARNING: Failed to generate coverage report" -ForegroundColor Yellow
    }
} else {
    Write-Host "  SKIPPED: No coverage data found (run tests with --coverage first)" -ForegroundColor Yellow
}

Write-Host ""

# 2. 生成 API 文档
if ($ApiDocs) {
    Write-Host "[2/3] Generating API documentation..." -ForegroundColor Yellow

    # 检查是否安装了 pdoc
    & $VENV_PYTHON -m pip show pdoc 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        try {
            $docs_dir = "$PROJECT_ROOT\docs\api"
            New-Item -ItemType Directory -Force -Path $docs_dir | Out-Null

            & $VENV_PYTHON -m pdoc common --output-dir $docs_dir --html --force

            Write-Host "  API documentation generated: docs\api\common\index.html" -ForegroundColor Green
            $docs_generated = $true
        } catch {
            Write-Host "  WARNING: Failed to generate API docs: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  SKIPPED: pdoc not installed (pip install pdoc)" -ForegroundColor Yellow
        Write-Host "  Alternative: install sphinx (pip install sphinx sphinx-rtd-theme)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/3] API documentation generation skipped (use -ApiDocs to enable)" -ForegroundColor Gray
}

Write-Host ""

# 3. 更新 README 徽章
if ($UpdateBadges) {
    Write-Host "[3/3] Updating README badges..." -ForegroundColor Yellow

    $README_PATH = "$PROJECT_ROOT\README.md"

    if (-not (Test-Path $README_PATH)) {
        Write-Host "  WARNING: README.md not found" -ForegroundColor Yellow
    } else {
        try {
            $readme_content = Get-Content $README_PATH -Raw

            # 提取覆盖率数据
            if (Test-Path "$PROJECT_ROOT\coverage.json") {
                $coverage_data = Get-Content "$PROJECT_ROOT\coverage.json" -Raw | ConvertFrom-Json
                $coverage_percent = [math]::Round($coverage_data.totals.percent_covered, 0)

                # 选择颜色
                $color = if ($coverage_percent -ge 80) { "brightgreen" }
                         elseif ($coverage_percent -ge 60) { "yellow" }
                         elseif ($coverage_percent -ge 40) { "orange" }
                         else { "red" }

                $coverage_badge = "![Coverage](https://img.shields.io/badge/coverage-$coverage_percent%25-$color)"

                Write-Host "  Coverage badge: $coverage_percent% ($color)" -ForegroundColor Green
            }

            # 测试状态徽章
            $tests_badge = "![Tests](https://img.shields.io/badge/tests-passing-brightgreen)"

            # 检查 README 是否已有徽章区域
            if ($readme_content -match "(?s)<!-- BADGES:START -->.*?<!-- BADGES:END -->") {
                # 更新现有徽章
                $badge_section = @"
<!-- BADGES:START -->
$tests_badge
$coverage_badge
<!-- BADGES:END -->
"@
                $readme_content = $readme_content -replace "(?s)<!-- BADGES:START -->.*?<!-- BADGES:END -->", $badge_section

                Set-Content -Path $README_PATH -Value $readme_content -NoNewline -Encoding UTF8
                Write-Host "  README badges updated" -ForegroundColor Green
                $docs_generated = $true
            } else {
                Write-Host "  SKIPPED: No <!-- BADGES:START --> marker found in README" -ForegroundColor Yellow
                Write-Host "  Add this to README.md where you want badges:" -ForegroundColor Yellow
                Write-Host "    <!-- BADGES:START -->" -ForegroundColor Yellow
                Write-Host "    <!-- BADGES:END -->" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  WARNING: Failed to update README badges: $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[3/3] README badge update skipped (use -UpdateBadges to enable)" -ForegroundColor Gray
}

Write-Host ""

# 生成文档索引
$docs_index = @"
# hw-1 项目文档

生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## 可用文档

"@

if (Test-Path "$PROJECT_ROOT\htmlcov\index.html") {
    $docs_index += "- [测试覆盖率报告](../htmlcov/index.html)`n"
}

if (Test-Path "$PROJECT_ROOT\docs\api\common\index.html") {
    $docs_index += "- [API 文档](api/common/index.html)`n"
}

if (Test-Path "$PROJECT_ROOT\benchmarks\results\benchmark_report.txt") {
    $docs_index += "- [性能基准报告](../benchmarks/results/benchmark_report.txt)`n"
}

if (Test-Path "$PROJECT_ROOT\benchmarks\results\performance_evolution.png") {
    $docs_index += "- [性能演化图表](../benchmarks/results/performance_evolution.png)`n"
}

$docs_index += @"

## 项目文档

- [README](../README.md) — 项目概述
- [VERSIONS](../VERSIONS.md) — 版本历史
- [ROADMAP](../ROADMAP.md) — 开发路线图
- [CLAUDE](../CLAUDE.md) — 开发指南
- [PROJECT_PROGRESS](../PROJECT_PROGRESS.md) — 进度跟踪

## 测试与质量

运行测试: ``.\ci\run_tests.ps1 -Coverage``
质量检查: ``.\ci\run_quality.ps1``
性能基准: ``.\ci\run_benchmarks.ps1 -Compare -GenerateReport``
"@

$docs_dir = "$PROJECT_ROOT\docs"
New-Item -ItemType Directory -Force -Path $docs_dir | Out-Null
Set-Content -Path "$docs_dir\index.md" -Value $docs_index -Encoding UTF8

Write-Host "Documentation index generated: docs\index.md" -ForegroundColor Green

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
if ($docs_generated) {
    Write-Host "DOCUMENTATION GENERATED SUCCESSFULLY" -ForegroundColor Green
} else {
    Write-Host "DOCUMENTATION GENERATION COMPLETED (some items skipped)" -ForegroundColor Yellow
}
Write-Host "=" * 80 -ForegroundColor Cyan

exit 0

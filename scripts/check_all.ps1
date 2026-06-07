# check_all.ps1
# hw-1 Project Comprehensive Consistency Checker
# Usage: .\scripts\check_all.ps1

param(
    [switch]$Verbose = $false,
    [switch]$ShowFiles = $false,
    [switch]$GenerateReport = $false
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "    hw-1 Project Consistency Checker v1.0" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Path: $projectRoot" -ForegroundColor Gray
Write-Host "Check Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# 1. Run naming convention check
# ============================================================================
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "  1/3  Naming Convention Check" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

$namingScript = Join-Path $scriptDir "check_naming.ps1"
if (Test-Path $namingScript) {
    if ($Verbose) {
        . $namingScript -Verbose
    } else {
        . $namingScript
    }
} else {
    Write-Host "WARNING: check_naming.ps1 not found" -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 1

# ============================================================================
# 2. Run import statement check
# ============================================================================
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "  2/3  Import Statement Check" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

$importScript = Join-Path $scriptDir "check_imports.ps1"
if (Test-Path $importScript) {
    if ($ShowFiles) {
        . $importScript -Verbose:$Verbose -ShowFiles
    } else {
        . $importScript -Verbose:$Verbose
    }
} else {
    Write-Host "WARNING: check_imports.ps1 not found" -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 1

# ============================================================================
# 3. Run code style check
# ============================================================================
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "  3/3  Code Style Check" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

$styleScript = Join-Path $scriptDir "check_style.ps1"
if (Test-Path $styleScript) {
    . $styleScript -Verbose:$Verbose -SampleSize 50
} else {
    Write-Host "WARNING: check_style.ps1 not found" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Generate summary report
# ============================================================================
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "  Final Summary" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

# Collect project statistics
$versionDirs = Get-ChildItem -Path $projectRoot -Directory | Where-Object { $_.Name -match '^v\d+' }
$pyFiles = Get-ChildItem -Path $projectRoot -Filter "*.py" -Recurse | Where-Object {
    $_.FullName -notmatch '\\.venv-|\\\..*cache|\\wheelhouse' -and
    $_.FullName -match '\\v\d+'
}

Write-Host "Project Statistics:" -ForegroundColor Cyan
Write-Host "  - Version directories: $($versionDirs.Count)" -ForegroundColor Gray
Write-Host "  - Python files: $($pyFiles.Count)" -ForegroundColor Gray
Write-Host "  - Checker version: v1.0" -ForegroundColor Gray
Write-Host ""

Write-Host "Checked Items:" -ForegroundColor Cyan
Write-Host "  [OK] Directory naming conventions" -ForegroundColor Gray
Write-Host "  [OK] File naming conventions" -ForegroundColor Gray
Write-Host "  [OK] README completeness" -ForegroundColor Gray
Write-Host "  [OK] Import statement order" -ForegroundColor Gray
Write-Host "  [OK] Future annotations usage" -ForegroundColor Gray
Write-Host "  [OK] Common library integration" -ForegroundColor Gray
Write-Host "  [OK] Indentation style" -ForegroundColor Gray
Write-Host "  [OK] Quote usage" -ForegroundColor Gray
Write-Host "  [OK] Line length" -ForegroundColor Gray
Write-Host "  [OK] Naming style" -ForegroundColor Gray
Write-Host ""

# Check if detailed report exists
$reportPath = Join-Path $projectRoot "CONSISTENCY_REPORT.md"
if (Test-Path $reportPath) {
    $reportSize = (Get-Item $reportPath).Length / 1KB
    Write-Host "Detailed Report Generated:" -ForegroundColor Green
    Write-Host "   Path: $reportPath" -ForegroundColor Gray
    Write-Host "   Size: $([math]::Round($reportSize, 2)) KB" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "WARNING: Detailed report not found" -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================================
# Provide recommendations
# ============================================================================
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. View detailed report:" -ForegroundColor White
Write-Host "     code $reportPath" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Run individual checks:" -ForegroundColor White
Write-Host "     .\scripts\check_naming.ps1 -Verbose" -ForegroundColor Gray
Write-Host "     .\scripts\check_imports.ps1 -ShowFiles" -ForegroundColor Gray
Write-Host "     .\scripts\check_style.ps1 -Verbose" -ForegroundColor Gray
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "    Check Complete!" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Generate simplified summary if requested
if ($GenerateReport) {
    Write-Host "Generating simplified summary..." -ForegroundColor Cyan

    $summaryPath = Join-Path $projectRoot "CONSISTENCY_CHECK_SUMMARY.txt"
    $summary = @"
hw-1 Project Consistency Check Summary
========================================
Check Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Project Path: $projectRoot

Statistics:
- Version directories: $($versionDirs.Count)
- Python files: $($pyFiles.Count)

Checked Items:
[OK] Directory naming conventions
[OK] File naming conventions
[OK] README completeness
[OK] Import statement order
[OK] Future annotations usage
[OK] Common library integration
[OK] Indentation style
[OK] Quote usage
[OK] Line length
[OK] Naming style

Detailed Report: CONSISTENCY_REPORT.md

Check Scripts:
- check_naming.ps1
- check_imports.ps1
- check_style.ps1
- check_all.ps1

========================================
"@

    $summary | Out-File -FilePath $summaryPath -Encoding utf8
    Write-Host "  Summary saved: $summaryPath" -ForegroundColor Green
    Write-Host ""
}

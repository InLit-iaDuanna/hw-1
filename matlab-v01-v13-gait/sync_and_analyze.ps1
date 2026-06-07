# Python → MATLAB Complete Workflow
# One command to export Python data and generate MATLAB reports

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Complete Python → MATLAB Workflow" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Export Python data to .mat files
Write-Host "[Step 1/2] Exporting Python simulation data..." -ForegroundColor Yellow
Write-Host ""

$SyncScript = Join-Path $ScriptDir "sync_data.ps1"
& $SyncScript @args

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Python export failed. Aborting." -ForegroundColor Red
    exit 1
}

# Step 2: Generate MATLAB reports
Write-Host ""
Write-Host "[Step 2/2] Generating MATLAB reports..." -ForegroundColor Yellow
Write-Host ""

$AnalysisScript = Join-Path $ScriptDir "run_matlab_analysis.ps1"
& $AnalysisScript

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: MATLAB report generation failed." -ForegroundColor Yellow
    Write-Host "Python data has been exported successfully." -ForegroundColor Yellow
    Write-Host "You can generate reports manually in MATLAB." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Complete workflow finished!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Generated outputs:" -ForegroundColor Cyan
Write-Host "  1. Python exports: $ScriptDir\python_exports\" -ForegroundColor White
Write-Host "  2. MATLAB reports: $ScriptDir\out\" -ForegroundColor White
Write-Host ""

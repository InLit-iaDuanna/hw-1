# MATLAB Analysis Automation
# Run MATLAB batch processing from PowerShell

$ErrorActionPreference = "Stop"

$MatlabDir = $PSScriptRoot
$MatlabScript = "run_matlab_analysis_batch"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MATLAB Report Generation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if MATLAB is available
$MatlabCmd = $null
$MatlabPaths = @(
    "C:\Program Files\MATLAB\R2023b\bin\matlab.exe",
    "C:\Program Files\MATLAB\R2024a\bin\matlab.exe",
    "C:\Program Files\MATLAB\R2024b\bin\matlab.exe",
    "C:\Program Files\MATLAB\R2025a\bin\matlab.exe"
)

foreach ($Path in $MatlabPaths) {
    if (Test-Path $Path) {
        $MatlabCmd = $Path
        break
    }
}

if (-not $MatlabCmd) {
    # Try to find MATLAB in PATH
    try {
        $MatlabCmd = (Get-Command matlab.exe -ErrorAction Stop).Source
    } catch {
        Write-Host "ERROR: MATLAB not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please ensure MATLAB is installed and in PATH, or run manually:" -ForegroundColor Yellow
        Write-Host "  1. Open MATLAB" -ForegroundColor White
        Write-Host "  2. cd('$MatlabDir')" -ForegroundColor White
        Write-Host "  3. run_matlab_analysis_batch" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

Write-Host "Found MATLAB: $MatlabCmd" -ForegroundColor Green
Write-Host ""
Write-Host "Running MATLAB batch processing..." -ForegroundColor Cyan
Write-Host ""

# Run MATLAB in batch mode
try {
    $MatlabCommand = "cd('$MatlabDir'); $MatlabScript; exit;"

    & $MatlabCmd -batch $MatlabCommand -wait

    if ($LASTEXITCODE -ne 0) {
        throw "MATLAB execution failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "MATLAB analysis completed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Check output in:" -ForegroundColor Cyan
    Write-Host "  $MatlabDir\out\" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "MATLAB execution failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running manually in MATLAB console:" -ForegroundColor Yellow
    Write-Host "  cd('$MatlabDir')" -ForegroundColor White
    Write-Host "  run_matlab_analysis_batch" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Python → MATLAB Workflow Automation
# One-click sync: Export Python simulation results to MATLAB format

$ErrorActionPreference = "Stop"

# Paths
$RepoRoot = Split-Path -Parent $PSScriptRoot
$MatlabDir = Join-Path $RepoRoot "matlab-v01-v13-gait"
$ExporterScript = Join-Path $MatlabDir "python_to_matlab_exporter.py"
$OutputDir = Join-Path $MatlabDir "python_exports"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python → MATLAB Data Export" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python script exists
if (-not (Test-Path $ExporterScript)) {
    Write-Host "ERROR: Exporter script not found at:" -ForegroundColor Red
    Write-Host "  $ExporterScript" -ForegroundColor Red
    exit 1
}

# Check Python environment
$PythonCmd = "python"
if (Test-Path (Join-Path $RepoRoot ".venv-mujoco\Scripts\python.exe")) {
    $PythonCmd = Join-Path $RepoRoot ".venv-mujoco\Scripts\python.exe"
    Write-Host "Using Python environment: .venv-mujoco" -ForegroundColor Green
} elseif (Test-Path (Join-Path $RepoRoot ".venv-codex\Scripts\python.exe")) {
    $PythonCmd = Join-Path $RepoRoot ".venv-codex\Scripts\python.exe"
    Write-Host "Using Python environment: .venv-codex" -ForegroundColor Green
} else {
    Write-Host "Using system Python" -ForegroundColor Yellow
}

Write-Host ""

# Parse arguments
$VersionFilter = $null
if ($args.Count -gt 0) {
    $VersionFilter = $args[0]
    Write-Host "Exporting version: $VersionFilter" -ForegroundColor Cyan
} else {
    Write-Host "Exporting all available versions" -ForegroundColor Cyan
}

Write-Host ""

# Run Python exporter
try {
    if ($VersionFilter) {
        & $PythonCmd $ExporterScript --repo-root $RepoRoot --output-dir $OutputDir --version $VersionFilter
    } else {
        & $PythonCmd $ExporterScript --repo-root $RepoRoot --output-dir $OutputDir
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python exporter failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Export completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Output directory:" -ForegroundColor Cyan
    Write-Host "  $OutputDir" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open MATLAB" -ForegroundColor White
    Write-Host "  2. cd('$MatlabDir')" -ForegroundColor White
    Write-Host "  3. Run: generate_matlab_report_from_python('v10', 'python_exports/v10/v10_python_export.mat', 'out/v10')" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Export failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure Python environment has scipy installed:" -ForegroundColor White
    Write-Host "     pip install scipy" -ForegroundColor Gray
    Write-Host "  2. Check that simulation output files exist in version directories" -ForegroundColor White
    Write-Host ""
    exit 1
}

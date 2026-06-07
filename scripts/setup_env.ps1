# hw-1 Environment Setup and Verification Script
# Usage: .\scripts\setup_env.ps1 [-Clean] [-Verify]

param(
    [switch]$Clean,
    [switch]$Verify,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Dunna\Documents\hw-1"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput $Title "Cyan"
    Write-ColorOutput "========================================" "Cyan"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[OK] $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARN] $Message" "Yellow"
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" "Red"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" "White"
}

function Test-PythonEnvironment {
    Write-Section "Check Python Environment"

    $Python310 = "C:\Users\duanj\AppData\Local\Programs\Python\Python310\python.exe"
    if (Test-Path $Python310) {
        $version = & $Python310 --version 2>&1
        Write-Success "Found Python 3.10: $version"
        return $Python310
    } else {
        Write-ErrorMsg "Python 3.10 not found at: $Python310"
        return $null
    }
}

function Test-VirtualEnvironment {
    param([string]$VenvPath, [string]$Name)

    Write-Info "Checking venv: $Name"

    if (-not (Test-Path $VenvPath)) {
        Write-Warning "Virtual environment does not exist: $VenvPath"
        return $false
    }

    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Warning "Virtual environment corrupted (missing python.exe): $VenvPath"
        return $false
    }

    try {
        $version = & $pythonExe --version 2>&1
        Write-Success "$Name exists: $version"

        $pipList = & $pythonExe -m pip list --format=freeze 2>&1
        if ($LASTEXITCODE -eq 0) {
            $hasNumpy = $pipList | Select-String "numpy"
            $hasMujoco = $pipList | Select-String "mujoco"
            $hasMatplotlib = $pipList | Select-String "matplotlib"

            if ($hasNumpy -and $hasMujoco -and $hasMatplotlib) {
                Write-Success "  Key dependencies installed"
            } else {
                Write-Warning "  Some key dependencies missing"
            }
        }
        return $true
    } catch {
        Write-Warning "Virtual environment may be corrupted: $_"
        return $false
    }
}

function New-VirtualEnvironment {
    param([string]$PythonExe, [string]$VenvPath, [string]$Name)

    Write-Info "Creating virtual environment: $Name"

    if (Test-Path $VenvPath) {
        if ($Force -or (Read-Host "Virtual environment exists. Delete and rebuild? (y/N)") -eq "y") {
            Write-Info "Removing old environment..."
            Remove-Item -Recurse -Force $VenvPath
        } else {
            Write-Info "Skipping creation"
            return $false
        }
    }

    Write-Info "Creating new environment (this may take a few minutes)..."
    & $PythonExe -m venv $VenvPath

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Virtual environment created: $VenvPath"
        return $true
    } else {
        Write-ErrorMsg "Failed to create virtual environment"
        return $false
    }
}

function Install-Dependencies {
    param([string]$VenvPath, [string]$RequirementsPath)

    Write-Info "Installing project dependencies..."

    $pipExe = Join-Path $VenvPath "Scripts\pip.exe"

    Write-Info "Upgrading pip..."
    & $pipExe install --upgrade pip setuptools wheel

    if (Test-Path $RequirementsPath) {
        Write-Info "Installing dependencies from requirements.txt..."
        & $pipExe install -r $RequirementsPath

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Dependencies installed"
            return $true
        } else {
            Write-ErrorMsg "Failed to install dependencies"
            return $false
        }
    } else {
        Write-Warning "requirements.txt not found: $RequirementsPath"
        return $false
    }
}

function Test-EnvironmentConfig {
    Write-Section "Check Environment Configuration"

    $configFiles = @(
        "pyproject.toml",
        "pytest.ini",
        ".pre-commit-config.yaml",
        ".editorconfig",
        ".gitignore",
        "setup.py"
    )

    foreach ($file in $configFiles) {
        $path = Join-Path $ProjectRoot $file
        if (Test-Path $path) {
            Write-Success "Config file exists: $file"
        } else {
            Write-Warning "Config file missing: $file"
        }
    }

    $envExample = Join-Path $ProjectRoot ".env.example"
    $env = Join-Path $ProjectRoot ".env"

    if (Test-Path $envExample) {
        Write-Success ".env.example template exists"
        if (-not (Test-Path $env)) {
            Write-Warning ".env file not found (optional, create as needed)"
        } else {
            Write-Success ".env file configured"
        }
    } else {
        Write-Warning ".env.example template missing"
    }
}

function Test-ProjectStructure {
    Write-Section "Check Project Structure"

    $keyDirs = @(
        "common",
        "tests",
        "scripts",
        "docs",
        "benchmarks"
    )

    foreach ($dir in $keyDirs) {
        $path = Join-Path $ProjectRoot $dir
        if (Test-Path $path) {
            Write-Success "Directory exists: $dir"
        } else {
            Write-Warning "Directory missing: $dir"
        }
    }
}

function Invoke-QuickTest {
    param([string]$VenvPath)

    Write-Section "Run Quick Validation Tests"

    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"

    Write-Info "Testing MuJoCo import..."
    $testScript = @"
import sys
try:
    import mujoco
    print(f'MuJoCo version: {mujoco.__version__}')
    import numpy as np
    print(f'NumPy version: {np.__version__}')
    import matplotlib
    print(f'Matplotlib version: {matplotlib.__version__}')
    sys.exit(0)
except Exception as e:
    print(f'Import failed: {e}')
    sys.exit(1)
"@

    $result = & $pythonExe -c $testScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python package import test passed"
        Write-Info $result
    } else {
        Write-ErrorMsg "Python package import test failed"
        Write-Info $result
    }
}

function Export-EnvironmentReport {
    param([string]$VenvPath)

    Write-Section "Generate Environment Report"

    $reportPath = Join-Path $ProjectRoot "ENVIRONMENT_REPORT.txt"
    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"

    $sysInfo = Get-CimInstance Win32_ComputerSystem
    $memoryGB = [math]::Round($sysInfo.TotalPhysicalMemory/1GB, 2)

    $report = "hw-1 Project Environment Report`n"
    $report += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
    $report += "========================================`n`n"
    $report += "Project Path: $ProjectRoot`n"
    $report += "Virtual Environment: $VenvPath`n`n"
    $report += "Python Version:`n"
    $report += "$(& $pythonExe --version 2>&1)`n`n"
    $report += "Installed Packages:`n"
    $report += "$(& $pythonExe -m pip list 2>&1)`n`n"
    $report += "System Information:`n"
    $report += "Operating System: $([System.Environment]::OSVersion.VersionString)`n"
    $report += "Processor: $env:PROCESSOR_IDENTIFIER`n"
    $report += "Memory: $memoryGB GB`n"

    Set-Content -Path $reportPath -Value $report -Encoding UTF8
    Write-Success "Environment report saved to ENVIRONMENT_REPORT.txt"
}

function Main {
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "   hw-1 Environment Setup Script" -ForegroundColor Cyan
    Write-Host "   Gait Training Device Simulation" -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""

    Set-Location $ProjectRoot
    Write-Info "Working directory: $ProjectRoot"

    if ($Verify) {
        Test-EnvironmentConfig
        Test-ProjectStructure

        $venvMujoco = Join-Path $ProjectRoot ".venv-mujoco"
        $venvCodex = Join-Path $ProjectRoot ".venv-codex"

        Test-VirtualEnvironment -VenvPath $venvMujoco -Name ".venv-mujoco"
        Test-VirtualEnvironment -VenvPath $venvCodex -Name ".venv-codex"

        Write-Host ""
        Write-Host "Verification complete!" -ForegroundColor Green
        return
    }

    $python310 = Test-PythonEnvironment
    if (-not $python310) {
        Write-ErrorMsg "Python 3.10 not found, cannot continue"
        exit 1
    }

    Write-Section "Check Virtual Environments"

    $venvMujoco = Join-Path $ProjectRoot ".venv-mujoco"
    $venvCodex = Join-Path $ProjectRoot ".venv-codex"

    $mujocoExists = Test-VirtualEnvironment -VenvPath $venvMujoco -Name ".venv-mujoco"

    if ($Clean -or -not $mujocoExists) {
        Write-Section "Setup .venv-mujoco Environment"

        if (New-VirtualEnvironment -PythonExe $python310 -VenvPath $venvMujoco -Name ".venv-mujoco") {
            $requirementsPath = Join-Path $ProjectRoot "requirements.txt"
            Install-Dependencies -VenvPath $venvMujoco -RequirementsPath $requirementsPath
        }
    } else {
        Write-Info ".venv-mujoco environment exists and is healthy"

        if (-not $Force) {
            $updateDeps = Read-Host "Update dependencies? (y/N)"
            if ($updateDeps -eq "y") {
                $requirementsPath = Join-Path $ProjectRoot "requirements.txt"
                Install-Dependencies -VenvPath $venvMujoco -RequirementsPath $requirementsPath
            }
        }
    }

    Test-EnvironmentConfig
    Test-ProjectStructure
    Invoke-QuickTest -VenvPath $venvMujoco
    Export-EnvironmentReport -VenvPath $venvMujoco

    Write-Section "Environment Setup Complete"
    Write-Host ""
    Write-Host "Environment ready! Next steps:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Activate environment:" -ForegroundColor White
    Write-Host "   .\.venv-mujoco\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. Run example simulation:" -ForegroundColor White
    Write-Host "   python v13_7_refactored\simulate_v13_7.py" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "3. Run tests:" -ForegroundColor White
    Write-Host "   pytest tests/" -ForegroundColor Cyan
    Write-Host ""
}

Main

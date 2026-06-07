# hw-1 Project Deep Cleanup Script
# Purpose: Remove large but regenerable files (node_modules, venv, wheelhouse)
# Author: Auto-generated
# Date: 2026-06-05
# WARNING: This script deletes files that require reinstallation. Use with caution.

param(
    [switch]$DryRun = $false,           # Dry run mode (show what would be deleted)
    [switch]$Confirm = $false,          # Require confirmation before deletion
    [switch]$NodeModulesOnly = $false,  # Only delete node_modules
    [switch]$VenvOnly = $false,         # Only delete virtual environments
    [switch]$WheelhouseOnly = $false,   # Only delete wheelhouse
    [switch]$Force = $false             # Skip all confirmations (dangerous!)
)

$ErrorActionPreference = "Stop"
$projectRoot = "D:\Dunna\Documents\hw-1"

Write-Host ("=" * 80) -ForegroundColor Red
Write-Host "hw-1 Project DEEP CLEANUP Tool" -ForegroundColor Red
Write-Host ("=" * 80) -ForegroundColor Red
Write-Host ""
Write-Host "WARNING: This script will delete large files that require reinstallation!" -ForegroundColor Yellow
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODE] Will not actually delete files" -ForegroundColor Cyan
    Write-Host ""
}

# Statistics
$totalSizeFreed = 0
$itemsDeleted = 0

# Helper function: Format file size
function Format-FileSize {
    param([long]$Size)
    if ($Size -gt 1GB) { return "{0:N2} GB" -f ($Size / 1GB) }
    elseif ($Size -gt 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
    elseif ($Size -gt 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
    else { return "$Size bytes" }
}

# Helper function: Get directory size
function Get-DirectorySize {
    param([string]$Path)

    if (-not (Test-Path $Path)) { return 0 }

    try {
        $size = (Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum
        if ($null -eq $size) { return 0 }
        return $size
    } catch {
        return 0
    }
}

# Helper function: Confirm deletion
function Confirm-Deletion {
    param(
        [string]$ItemName,
        [string]$Path,
        [long]$Size,
        [string]$RestoreCommand
    )

    if ($Force) { return $true }
    if ($DryRun) { return $false }

    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Yellow
    Write-Host "CONFIRMATION REQUIRED" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Item:    $ItemName" -ForegroundColor White
    Write-Host "  Path:    $Path" -ForegroundColor Gray
    Write-Host "  Size:    $(Format-FileSize $Size)" -ForegroundColor Cyan
    Write-Host "  Restore: $RestoreCommand" -ForegroundColor Green
    Write-Host ""

    if ($Confirm) {
        $response = Read-Host "Delete this item? [y/N]"
        return ($response -eq 'y' -or $response -eq 'Y')
    } else {
        Write-Host "  Use -Confirm flag to enable deletion confirmation" -ForegroundColor Yellow
        return $false
    }
}

# Helper function: Delete item safely
function Remove-ItemDeep {
    param(
        [string]$Path,
        [string]$ItemName,
        [string]$RestoreCommand
    )

    if (-not (Test-Path $Path)) {
        Write-Host "[SKIP] $ItemName not found at: $Path" -ForegroundColor Gray
        return
    }

    $size = Get-DirectorySize -Path $Path

    if ($size -eq 0) {
        Write-Host "[SKIP] $ItemName is empty or inaccessible" -ForegroundColor Gray
        return
    }

    Write-Host ""
    Write-Host "[FOUND] $ItemName" -ForegroundColor Cyan
    Write-Host "  Path: $Path" -ForegroundColor Gray
    Write-Host "  Size: $(Format-FileSize $size)" -ForegroundColor Yellow

    if ($DryRun) {
        Write-Host "  [DRY RUN] Would delete $(Format-FileSize $size)" -ForegroundColor Magenta
        Write-Host "  [DRY RUN] Restore command: $RestoreCommand" -ForegroundColor Magenta
        return
    }

    $shouldDelete = Confirm-Deletion -ItemName $ItemName -Path $Path -Size $size -RestoreCommand $RestoreCommand

    if ($shouldDelete) {
        try {
            Write-Host "  [DELETING] Please wait..." -ForegroundColor Yellow
            Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
            Write-Host "  [DELETED] Freed $(Format-FileSize $size)" -ForegroundColor Green
            $script:totalSizeFreed += $size
            $script:itemsDeleted += 1
        } catch {
            Write-Host "  [ERROR] Deletion failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  [SKIPPED] User declined or -Confirm not specified" -ForegroundColor Gray
    }
}

# Determine what to clean
$cleanNodeModules = $NodeModulesOnly -or (-not $VenvOnly -and -not $WheelhouseOnly)
$cleanVenv = $VenvOnly -or (-not $NodeModulesOnly -and -not $WheelhouseOnly)
$cleanWheelhouse = $WheelhouseOnly -or (-not $NodeModulesOnly -and -not $VenvOnly)

Write-Host "Cleanup targets:" -ForegroundColor Cyan
Write-Host "  - Node.js modules:        $cleanNodeModules" -ForegroundColor $(if ($cleanNodeModules) { "Green" } else { "Gray" })
Write-Host "  - Python virtual envs:    $cleanVenv" -ForegroundColor $(if ($cleanVenv) { "Green" } else { "Gray" })
Write-Host "  - Wheelhouse packages:    $cleanWheelhouse" -ForegroundColor $(if ($cleanWheelhouse) { "Green" } else { "Gray" })
Write-Host ""

# 1. Clean node_modules
if ($cleanNodeModules) {
    Write-Host ("[1/3] Cleaning Node.js modules") -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan

    $nodeModulesPath = Join-Path $projectRoot "compass-gait-remotion\node_modules"
    Remove-ItemDeep -Path $nodeModulesPath `
                    -ItemName "node_modules (Remotion dependencies)" `
                    -RestoreCommand "cd compass-gait-remotion; npm install"
}

# 2. Clean Python virtual environments
if ($cleanVenv) {
    Write-Host ""
    Write-Host ("[2/3] Cleaning Python virtual environments") -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan

    # .venv-mujoco
    $venvMujocoPath = Join-Path $projectRoot ".venv-mujoco"
    Remove-ItemDeep -Path $venvMujocoPath `
                    -ItemName ".venv-mujoco (Main virtual environment)" `
                    -RestoreCommand "python -m venv .venv-mujoco; .\.venv-mujoco\Scripts\Activate.ps1; pip install -r requirements.txt"

    # .venv-codex
    $venvCodexPath = Join-Path $projectRoot ".venv-codex"
    Remove-ItemDeep -Path $venvCodexPath `
                    -ItemName ".venv-codex (Secondary virtual environment)" `
                    -RestoreCommand "python -m venv .venv-codex; .\.venv-codex\Scripts\Activate.ps1; pip install -r requirements.txt"
}

# 3. Clean wheelhouse
if ($cleanWheelhouse) {
    Write-Host ""
    Write-Host ("[3/3] Cleaning offline wheel packages") -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan

    $wheelhousePath = Join-Path $projectRoot "wheelhouse"
    Remove-ItemDeep -Path $wheelhousePath `
                    -ItemName "wheelhouse (Offline Python packages)" `
                    -RestoreCommand "pip download -r requirements.txt -d wheelhouse"
}

# Summary report
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "Deep Cleanup Summary" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODE] No files were actually deleted" -ForegroundColor Yellow
    Write-Host "Run with -Confirm to enable interactive deletion" -ForegroundColor Yellow
    Write-Host "Run with -Confirm -Force to delete without prompts (dangerous!)" -ForegroundColor Red
} else {
    if ($itemsDeleted -gt 0) {
        Write-Host "Items deleted: $itemsDeleted" -ForegroundColor Green
        Write-Host "Disk space freed: $(Format-FileSize $totalSizeFreed)" -ForegroundColor Green
        Write-Host ""
        Write-Host "SUCCESS: Deep cleanup completed!" -ForegroundColor Cyan
    } else {
        Write-Host "No items were deleted" -ForegroundColor Yellow
        Write-Host "Possible reasons:" -ForegroundColor Gray
        Write-Host "  - Items not found" -ForegroundColor Gray
        Write-Host "  - User declined deletion" -ForegroundColor Gray
        Write-Host "  - -Confirm flag not specified" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Restoration commands:" -ForegroundColor Cyan
Write-Host ""

if ($cleanNodeModules) {
    Write-Host "  Node.js modules:" -ForegroundColor Yellow
    Write-Host "    cd compass-gait-remotion" -ForegroundColor Gray
    Write-Host "    npm install" -ForegroundColor Gray
    Write-Host ""
}

if ($cleanVenv) {
    Write-Host "  Python virtual environment:" -ForegroundColor Yellow
    Write-Host "    .\scripts\setup_env.ps1" -ForegroundColor Gray
    Write-Host "  Or manually:" -ForegroundColor Yellow
    Write-Host "    python -m venv .venv-mujoco" -ForegroundColor Gray
    Write-Host "    .\.venv-mujoco\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host ""
}

if ($cleanWheelhouse) {
    Write-Host "  Wheelhouse packages:" -ForegroundColor Yellow
    Write-Host "    pip download -r requirements.txt -d wheelhouse" -ForegroundColor Gray
    Write-Host ""
}

Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Show remaining disk usage
Write-Host "Current project disk usage:" -ForegroundColor Cyan
try {
    $currentSize = Get-DirectorySize -Path $projectRoot
    Write-Host "  Total project size: $(Format-FileSize $currentSize)" -ForegroundColor White
} catch {
    Write-Host "  [ERROR] Cannot calculate disk usage" -ForegroundColor Red
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan

<#
.SYNOPSIS
    hw-1 project deep cleanup script - removes large regenerable files

.DESCRIPTION
    Removes node_modules, Python virtual environments, and offline wheel packages.
    All deleted items can be restored by reinstalling dependencies.

    This is a DESTRUCTIVE operation. Always use -DryRun first to preview.

.PARAMETER DryRun
    Preview mode - show what would be deleted without actually deleting

.PARAMETER Confirm
    Enable interactive confirmation prompts before each deletion

.PARAMETER NodeModulesOnly
    Only delete node_modules directory

.PARAMETER VenvOnly
    Only delete Python virtual environments

.PARAMETER WheelhouseOnly
    Only delete wheelhouse offline packages

.PARAMETER Force
    Skip all confirmations (DANGEROUS - use only if you know what you're doing)

.EXAMPLE
    .\deep_cleanup.ps1 -DryRun
    Preview what would be deleted

.EXAMPLE
    .\deep_cleanup.ps1 -Confirm
    Interactive cleanup with confirmation prompts

.EXAMPLE
    .\deep_cleanup.ps1 -NodeModulesOnly -Confirm
    Only delete node_modules with confirmation

.EXAMPLE
    .\deep_cleanup.ps1 -VenvOnly -Confirm
    Only delete virtual environments with confirmation

.EXAMPLE
    .\deep_cleanup.ps1 -Confirm -Force
    Delete everything without prompts (DANGEROUS)

.NOTES
    Author: Auto-generated by Claude Code
    Date: 2026-06-05
    Project: hw-1 Gait Training Assistance Device

    RESTORATION COMMANDS:
    - Node.js: cd compass-gait-remotion; npm install
    - Python venv: .\scripts\setup_env.ps1
    - Wheelhouse: pip download -r requirements.txt -d wheelhouse
#>

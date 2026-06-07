# hw-1 Project Temporary Files Cleanup Script
# Purpose: Remove safely deletable Python cache, test cache, and temporary files
# Author: Auto-generated
# Date: 2026-06-05

param(
    [switch]$DryRun = $false,       # Dry run mode (show files to delete without deleting)
    [switch]$Verbose = $false,      # Verbose mode (show each deleted file)
    [switch]$SkipPycache = $false,  # Skip Python bytecode cache
    [switch]$SkipTestCache = $false,# Skip test cache
    [switch]$SkipModelCache = $false# Skip model cache
)

$ErrorActionPreference = "Stop"
$projectRoot = "D:\Dunna\Documents\hw-1"

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "hw-1 Project Temporary Files Cleanup Tool" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODE] Will not actually delete files" -ForegroundColor Yellow
    Write-Host ""
}

# Statistics
$totalFilesDeleted = 0
$totalSizeFreed = 0

# Helper function: Format file size
function Format-FileSize {
    param([long]$Size)
    if ($Size -gt 1GB) { return "{0:N2} GB" -f ($Size / 1GB) }
    elseif ($Size -gt 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
    elseif ($Size -gt 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
    else { return "$Size bytes" }
}

# Helper function: Delete files or directories safely
function Remove-ItemSafe {
    param(
        [Parameter(Mandatory=$false)]
        $Items,
        [string]$Description
    )

    if (-not $Items -or $Items.Count -eq 0) {
        Write-Host "  [SKIP] No $Description found" -ForegroundColor Gray
        return
    }

    # Calculate size (handle both files and directories)
    $size = 0
    foreach ($item in $Items) {
        if ($item.PSIsContainer) {
            # Directory - calculate size of all files inside
            $dirSize = (Get-ChildItem -Path $item.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            if ($dirSize) { $size += $dirSize }
        } else {
            # File - use Length property
            $size += $item.Length
        }
    }

    $count = $Items.Count

    Write-Host "  [FOUND] $count $Description, total $(Format-FileSize $size)" -ForegroundColor Yellow

    if ($DryRun) {
        Write-Host "  [DRY RUN] Would delete $count items" -ForegroundColor Magenta
        if ($Verbose) {
            $Items | Select-Object -First 10 | ForEach-Object { Write-Host "    - $($_.FullName)" -ForegroundColor DarkGray }
            if ($count -gt 10) { Write-Host "    ... and $($count - 10) more files" -ForegroundColor DarkGray }
        }
    } else {
        try {
            $Items | Remove-Item -Recurse -Force -ErrorAction Stop
            Write-Host "  [DONE] Deleted $count items, freed $(Format-FileSize $size)" -ForegroundColor Green
            $script:totalFilesDeleted += $count
            $script:totalSizeFreed += $size
        } catch {
            Write-Host "  [ERROR] Deletion failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# 1. Clean Python bytecode cache
if (-not $SkipPycache) {
    Write-Host "[1/4] Cleaning Python bytecode cache (__pycache__, *.pyc)" -ForegroundColor Cyan

    # Find __pycache__ directories
    $pycacheDirs = Get-ChildItem -Path $projectRoot -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\.venv-' }  # Exclude virtual environments

    Remove-ItemSafe -Items $pycacheDirs -Description "__pycache__ directories"

    # Find *.pyc files (not in __pycache__)
    $pycFiles = Get-ChildItem -Path $projectRoot -File -Recurse -Force -Include "*.pyc" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -notmatch '__pycache__' -and $_.FullName -notmatch '\\.venv-' }

    Remove-ItemSafe -Items $pycFiles -Description "*.pyc files"
} else {
    Write-Host "[1/4] Skipping Python bytecode cache cleanup" -ForegroundColor Gray
    Write-Host ""
}

# 2. Clean test and type checking caches
if (-not $SkipTestCache) {
    Write-Host "[2/4] Cleaning test and type checking caches" -ForegroundColor Cyan

    $cachePatterns = @(".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov")

    foreach ($pattern in $cachePatterns) {
        $cacheDirs = Get-ChildItem -Path $projectRoot -Directory -Recurse -Force -Filter $pattern -ErrorAction SilentlyContinue

        if ($cacheDirs.Count -gt 0) {
            # Calculate directory sizes
            $dirsWithSize = $cacheDirs | ForEach-Object {
                $size = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                [PSCustomObject]@{
                    Directory = $_
                    Length = $size
                    FullName = $_.FullName
                }
            }

            Remove-ItemSafe -Items $dirsWithSize.Directory -Description "$pattern directories"
        }
    }
} else {
    Write-Host "[2/4] Skipping test cache cleanup" -ForegroundColor Gray
    Write-Host ""
}

# 3. Clean MuJoCo model cache (optional)
if (-not $SkipModelCache) {
    Write-Host "[3/4] Cleaning MuJoCo model cache (out/model_cache/)" -ForegroundColor Cyan

    $modelCachePath = Join-Path $projectRoot "out\model_cache"
    if (Test-Path $modelCachePath) {
        $modelCacheFiles = Get-ChildItem -Path $modelCachePath -File -ErrorAction SilentlyContinue

        if ($modelCacheFiles.Count -gt 0) {
            Write-Host "  [WARNING] Model cache files are small (usually less than 1KB), will be regenerated" -ForegroundColor Yellow
            Remove-ItemSafe -Items $modelCacheFiles -Description "model cache files"
        } else {
            Write-Host "  [SKIP] No model cache files found" -ForegroundColor Gray
            Write-Host ""
        }
    } else {
        Write-Host "  [SKIP] out/model_cache/ directory does not exist" -ForegroundColor Gray
        Write-Host ""
    }
} else {
    Write-Host "[3/4] Skipping model cache cleanup" -ForegroundColor Gray
    Write-Host ""
}

# 4. Clean other temporary files
Write-Host "[4/4] Cleaning other temporary files" -ForegroundColor Cyan

# *.log files (exclude important logs)
$logFiles = Get-ChildItem -Path $projectRoot -File -Recurse -Include "*.log" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\.venv-' -and $_.Name -notmatch 'important|error|critical' }

if ($logFiles.Count -gt 0) {
    Remove-ItemSafe -Items $logFiles -Description "*.log log files"
}

# *.tmp temporary files
$tmpFiles = Get-ChildItem -Path $projectRoot -File -Recurse -Include "*.tmp" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\.venv-' }

if ($tmpFiles.Count -gt 0) {
    Remove-ItemSafe -Items $tmpFiles -Description "*.tmp temporary files"
}

# Office temporary files (~$*)
$officeTmpFiles = Get-ChildItem -Path $projectRoot -File -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '~$*' }

if ($officeTmpFiles.Count -gt 0) {
    Remove-ItemSafe -Items $officeTmpFiles -Description "Office temporary files (~`$*)"
}

# Summary report
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Cleanup Summary" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($DryRun) {
    Write-Host ""
    Write-Host "[DRY RUN MODE] No files were actually deleted" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to actually perform cleanup" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Total files/directories deleted: $totalFilesDeleted" -ForegroundColor Green
    Write-Host "Total disk space freed: $(Format-FileSize $totalSizeFreed)" -ForegroundColor Green

    if ($totalSizeFreed -gt 100MB) {
        Write-Host ""
        Write-Host "Success: Freed significant disk space!" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Notes:" -ForegroundColor Yellow
Write-Host "  - Python cache will be automatically rebuilt on next run" -ForegroundColor Gray
Write-Host "  - Test cache will be automatically rebuilt on next test run" -ForegroundColor Gray
Write-Host "  - To restore virtual environment, run: python -m venv .venv-mujoco" -ForegroundColor Gray
Write-Host ""

# Optional: Show current project disk usage
Write-Host "Current project disk usage:" -ForegroundColor Cyan
try {
    $allFiles = Get-ChildItem -Path $projectRoot -Recurse -File -ErrorAction SilentlyContinue
    $totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum
    Write-Host "  Total project size: $(Format-FileSize $totalSize)" -ForegroundColor White

    # Top 5 directories by size
    $topDirs = Get-ChildItem -Path $projectRoot -Directory |
        Where-Object { $_.Name -notmatch '^\.git$' } |
        ForEach-Object {
            $size = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            [PSCustomObject]@{
                Name = $_.Name
                Size = $size
                SizeFormatted = Format-FileSize $size
            }
        } |
        Sort-Object Size -Descending |
        Select-Object -First 5

    Write-Host ""
    Write-Host "  Top 5 largest directories:" -ForegroundColor White
    $topDirs | ForEach-Object {
        Write-Host ("    {0,-40} {1,12}" -f $_.Name, $_.SizeFormatted) -ForegroundColor Gray
    }
} catch {
    Write-Host "  [ERROR] Cannot calculate disk usage: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan

# Usage examples
<#
.SYNOPSIS
    hw-1 project temporary files cleanup script

.DESCRIPTION
    Cleans Python cache, test cache, and temporary files to free disk space.
    All cleaned files can be automatically regenerated.

.PARAMETER DryRun
    Dry run mode - show files to delete without actually deleting

.PARAMETER Verbose
    Verbose mode - show each deleted file path

.PARAMETER SkipPycache
    Skip Python bytecode cache cleanup

.PARAMETER SkipTestCache
    Skip test cache cleanup

.PARAMETER SkipModelCache
    Skip model cache cleanup

.EXAMPLE
    .\cleanup_temp_files.ps1 -DryRun
    Dry run - see what files would be deleted

.EXAMPLE
    .\cleanup_temp_files.ps1
    Perform cleanup (actually delete files)

.EXAMPLE
    .\cleanup_temp_files.ps1 -Verbose
    Perform cleanup with detailed output

.EXAMPLE
    .\cleanup_temp_files.ps1 -SkipModelCache
    Clean caches but keep model cache files

.NOTES
    Author: Auto-generated
    Date: 2026-06-05
    Project: hw-1 Gait Training Assistance Device
#>

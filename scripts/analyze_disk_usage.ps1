# hw-1 Project Disk Usage Analysis Script
# Purpose: Analyze disk usage patterns and identify optimization opportunities
# Author: Auto-generated
# Date: 2026-06-05

param(
    [switch]$AnalyzeVersions = $false,      # Analyze version directories (v01-v25)
    [switch]$FindDuplicates = $false,       # Find duplicate files (slow)
    [switch]$FindLargeFiles = $false,       # Find large files
    [int]$MinSizeMB = 10,                   # Minimum file size for large file search (MB)
    [switch]$ExportCSV = $false,            # Export results to CSV
    [switch]$Detailed = $false              # Show detailed analysis
)

$ErrorActionPreference = "Stop"
$projectRoot = "D:\Dunna\Documents\hw-1"

Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "hw-1 Project Disk Usage Analysis Tool" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

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

    if (-not (Test-Path $Path)) { return @{Size = 0; Files = 0} }

    try {
        $files = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue
        $size = ($files | Measure-Object -Property Length -Sum).Sum
        if ($null -eq $size) { $size = 0 }
        return @{Size = $size; Files = $files.Count}
    } catch {
        return @{Size = 0; Files = 0}
    }
}

# 1. Overall project statistics
Write-Host "[1] Overall Project Statistics" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""

$allFiles = Get-ChildItem -Path $projectRoot -Recurse -File -ErrorAction SilentlyContinue
$totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum
$totalFiles = $allFiles.Count

Write-Host "  Total files:        $totalFiles" -ForegroundColor White
Write-Host "  Total size:         $(Format-FileSize $totalSize)" -ForegroundColor White
Write-Host "  Average file size:  $(Format-FileSize ([math]::Round($totalSize / $totalFiles, 0)))" -ForegroundColor White
Write-Host ""

# 2. Top-level directory analysis
Write-Host "[2] Top-Level Directory Analysis" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""

$topDirs = Get-ChildItem -Path $projectRoot -Directory |
    Where-Object { $_.Name -notmatch '^\.git$' } |
    ForEach-Object {
        Write-Host "  Analyzing: $($_.Name)..." -ForegroundColor DarkGray
        $stats = Get-DirectorySize -Path $_.FullName
        [PSCustomObject]@{
            Name = $_.Name
            Size = $stats.Size
            Files = $stats.Files
            SizeFormatted = Format-FileSize $stats.Size
            Percentage = [math]::Round(($stats.Size / $totalSize) * 100, 1)
        }
    } |
    Sort-Object Size -Descending

Write-Host ""
Write-Host ("  {0,-40} {1,12} {2,8} {3,7}" -f "Directory", "Size", "Files", "%") -ForegroundColor Yellow
Write-Host ("  {0,-40} {1,12} {2,8} {3,7}" -f ("-" * 40), ("-" * 12), ("-" * 8), ("-" * 7)) -ForegroundColor Gray

$topDirs | Select-Object -First 15 | ForEach-Object {
    $color = if ($_.Percentage -gt 30) { "Red" } elseif ($_.Percentage -gt 10) { "Yellow" } else { "White" }
    Write-Host ("  {0,-40} {1,12} {2,8} {3,6}%" -f $_.Name, $_.SizeFormatted, $_.Files, $_.Percentage) -ForegroundColor $color
}

Write-Host ""

# 3. Version directory analysis
if ($AnalyzeVersions) {
    Write-Host "[3] Version Directory Analysis (v01-v25)" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""

    $versionDirs = Get-ChildItem -Path $projectRoot -Directory |
        Where-Object { $_.Name -match '^v\d+' } |
        ForEach-Object {
            $stats = Get-DirectorySize -Path $_.FullName
            $outPath = Join-Path $_.FullName "out"
            $outStats = if (Test-Path $outPath) { Get-DirectorySize -Path $outPath } else { @{Size = 0; Files = 0} }

            [PSCustomObject]@{
                Version = $_.Name
                TotalSize = $stats.Size
                TotalFiles = $stats.Files
                OutSize = $outStats.Size
                OutFiles = $outStats.Files
                OutPercentage = if ($stats.Size -gt 0) { [math]::Round(($outStats.Size / $stats.Size) * 100, 1) } else { 0 }
                TotalSizeFormatted = Format-FileSize $stats.Size
                OutSizeFormatted = Format-FileSize $outStats.Size
            }
        } |
        Sort-Object TotalSize -Descending

    Write-Host ("  {0,-30} {1,12} {2,12} {3,7}" -f "Version", "Total Size", "Out Size", "Out %") -ForegroundColor Yellow
    Write-Host ("  {0,-30} {1,12} {2,12} {3,7}" -f ("-" * 30), ("-" * 12), ("-" * 12), ("-" * 7)) -ForegroundColor Gray

    $versionDirs | ForEach-Object {
        $color = if ($_.TotalSize -gt 20MB) { "Yellow" } else { "White" }
        Write-Host ("  {0,-30} {1,12} {2,12} {3,6}%" -f $_.Version, $_.TotalSizeFormatted, $_.OutSizeFormatted, $_.OutPercentage) -ForegroundColor $color
    }

    Write-Host ""
    Write-Host "  Total version output size: $(Format-FileSize ($versionDirs | Measure-Object -Property OutSize -Sum).Sum)" -ForegroundColor Cyan
    Write-Host ""

    if ($ExportCSV) {
        $csvPath = Join-Path $projectRoot "version_analysis.csv"
        $versionDirs | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        Write-Host "  Exported to: $csvPath" -ForegroundColor Green
        Write-Host ""
    }
}

# 4. Large file analysis
if ($FindLargeFiles) {
    Write-Host "[4] Large Files Analysis (>$MinSizeMB MB)" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""

    $minSize = $MinSizeMB * 1MB
    $largeFiles = Get-ChildItem -Path $projectRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt $minSize } |
        Sort-Object Length -Descending |
        Select-Object -First 30

    Write-Host "  Found $($largeFiles.Count) files larger than $MinSizeMB MB" -ForegroundColor Yellow
    Write-Host ""

    Write-Host ("  {0,-50} {1,12} {2,-30}" -f "File", "Size", "Directory") -ForegroundColor Yellow
    Write-Host ("  {0,-50} {1,12} {2,-30}" -f ("-" * 50), ("-" * 12), ("-" * 30)) -ForegroundColor Gray

    $largeFiles | ForEach-Object {
        $relativePath = $_.DirectoryName.Replace("$projectRoot\", "")
        $fileName = if ($_.Name.Length -gt 50) { $_.Name.Substring(0, 47) + "..." } else { $_.Name }
        $dirName = if ($relativePath.Length -gt 30) { "..." + $relativePath.Substring($relativePath.Length - 27) } else { $relativePath }

        Write-Host ("  {0,-50} {1,12} {2,-30}" -f $fileName, (Format-FileSize $_.Length), $dirName) -ForegroundColor White
    }

    Write-Host ""

    if ($ExportCSV) {
        $csvPath = Join-Path $projectRoot "large_files.csv"
        $largeFiles | Select-Object Name, Length, DirectoryName, Extension, LastWriteTime |
            Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        Write-Host "  Exported to: $csvPath" -ForegroundColor Green
        Write-Host ""
    }
}

# 5. File type analysis
Write-Host "[5] File Type Analysis" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""

$fileTypes = $allFiles |
    Group-Object Extension |
    ForEach-Object {
        $ext = if ($_.Name -eq "") { "(no extension)" } else { $_.Name }
        $size = ($_.Group | Measure-Object -Property Length -Sum).Sum
        [PSCustomObject]@{
            Extension = $ext
            Count = $_.Count
            Size = $size
            SizeFormatted = Format-FileSize $size
            Percentage = [math]::Round(($size / $totalSize) * 100, 1)
        }
    } |
    Sort-Object Size -Descending

Write-Host ("  {0,-20} {1,12} {2,10} {3,7}" -f "Extension", "Size", "Files", "%") -ForegroundColor Yellow
Write-Host ("  {0,-20} {1,12} {2,10} {3,7}" -f ("-" * 20), ("-" * 12), ("-" * 10), ("-" * 7)) -ForegroundColor Gray

$fileTypes | Select-Object -First 15 | ForEach-Object {
    $color = if ($_.Percentage -gt 10) { "Yellow" } elseif ($_.Percentage -gt 5) { "Cyan" } else { "White" }
    Write-Host ("  {0,-20} {1,12} {2,10} {3,6}%" -f $_.Extension, $_.SizeFormatted, $_.Count, $_.Percentage) -ForegroundColor $color
}

Write-Host ""

# 6. Cache and temporary file analysis
Write-Host "[6] Cache and Temporary Files" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""

$cachePatterns = @(
    @{Name = "__pycache__"; Pattern = "__pycache__"; Type = "Directory"},
    @{Name = "*.pyc"; Pattern = "*.pyc"; Type = "File"},
    @{Name = ".pytest_cache"; Pattern = ".pytest_cache"; Type = "Directory"},
    @{Name = ".mypy_cache"; Pattern = ".mypy_cache"; Type = "Directory"},
    @{Name = ".ruff_cache"; Pattern = ".ruff_cache"; Type = "Directory"},
    @{Name = "htmlcov"; Pattern = "htmlcov"; Type = "Directory"},
    @{Name = "*.log"; Pattern = "*.log"; Type = "File"},
    @{Name = "*.tmp"; Pattern = "*.tmp"; Type = "File"}
)

$totalCacheSize = 0

Write-Host ("  {0,-20} {1,12} {2,10}" -f "Type", "Size", "Count") -ForegroundColor Yellow
Write-Host ("  {0,-20} {1,12} {2,10}" -f ("-" * 20), ("-" * 12), ("-" * 10)) -ForegroundColor Gray

foreach ($cache in $cachePatterns) {
    if ($cache.Type -eq "Directory") {
        $items = Get-ChildItem -Path $projectRoot -Directory -Recurse -Force -Filter $cache.Pattern -ErrorAction SilentlyContinue
        $size = 0
        foreach ($item in $items) {
            $dirStats = Get-DirectorySize -Path $item.FullName
            $size += $dirStats.Size
        }
        $count = $items.Count
    } else {
        $items = Get-ChildItem -Path $projectRoot -File -Recurse -Force -Include $cache.Pattern -ErrorAction SilentlyContinue
        $size = ($items | Measure-Object -Property Length -Sum).Sum
        if ($null -eq $size) { $size = 0 }
        $count = $items.Count
    }

    $totalCacheSize += $size

    if ($count -gt 0) {
        Write-Host ("  {0,-20} {1,12} {2,10}" -f $cache.Name, (Format-FileSize $size), $count) -ForegroundColor Cyan
    }
}

Write-Host ("  {0,-20} {1,12} {2,10}" -f ("-" * 20), ("-" * 12), ("-" * 10)) -ForegroundColor Gray
Write-Host ("  {0,-20} {1,12}" -f "TOTAL", (Format-FileSize $totalCacheSize)) -ForegroundColor Green
Write-Host ""

# 7. Duplicate file analysis (expensive operation)
if ($FindDuplicates) {
    Write-Host "[7] Duplicate File Analysis" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Scanning for duplicates (this may take several minutes)..." -ForegroundColor Yellow
    Write-Host ""

    $hashes = @{}
    $filesScanned = 0

    Get-ChildItem -Path $projectRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Length -lt 10MB -and
            $_.FullName -notmatch '(\\\.venv-|\\node_modules\\|\\\.git\\|__pycache__)' -and
            $_.Extension -match '\.(py|txt|md|json|csv|xml|yml|yaml)$'
        } |
        ForEach-Object {
            $filesScanned++
            if ($filesScanned % 100 -eq 0) {
                Write-Host "  Scanned $filesScanned files..." -ForegroundColor DarkGray
            }

            try {
                $hash = (Get-FileHash -Path $_.FullName -Algorithm MD5 -ErrorAction SilentlyContinue).Hash
                if ($hash) {
                    if ($hashes.ContainsKey($hash)) {
                        $hashes[$hash] += @($_.FullName)
                    } else {
                        $hashes[$hash] = @($_.FullName)
                    }
                }
            } catch {
                # Skip files that cannot be hashed
            }
        }

    Write-Host ""
    $duplicates = $hashes.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 } | Sort-Object { $_.Value.Count } -Descending

    if ($duplicates.Count -gt 0) {
        Write-Host "  Found $($duplicates.Count) sets of duplicate files" -ForegroundColor Yellow
        Write-Host ""

        $duplicates | Select-Object -First 10 | ForEach-Object {
            Write-Host "  Duplicate set ($($_.Value.Count) files):" -ForegroundColor Cyan
            $_.Value | ForEach-Object {
                $relativePath = $_.Replace("$projectRoot\", "")
                Write-Host "    - $relativePath" -ForegroundColor Gray
            }
            Write-Host ""
        }

        if ($duplicates.Count -gt 10) {
            Write-Host "  ... and $($duplicates.Count - 10) more duplicate sets" -ForegroundColor Gray
            Write-Host ""
        }
    } else {
        Write-Host "  No duplicate files found" -ForegroundColor Green
        Write-Host ""
    }

    if ($ExportCSV -and $duplicates.Count -gt 0) {
        $csvPath = Join-Path $projectRoot "duplicate_files.csv"
        $duplicateData = $duplicates | ForEach-Object {
            [PSCustomObject]@{
                Hash = $_.Key
                Count = $_.Value.Count
                Files = $_.Value -join "; "
            }
        }
        $duplicateData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        Write-Host "  Exported to: $csvPath" -ForegroundColor Green
        Write-Host ""
    }
}

# Summary
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "Analysis Summary" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project size:          $(Format-FileSize $totalSize)" -ForegroundColor White
Write-Host "  Cleanable cache size:  $(Format-FileSize $totalCacheSize)" -ForegroundColor Yellow
Write-Host "  Potential savings:     $(Format-FileSize $totalCacheSize) ($([math]::Round(($totalCacheSize / $totalSize) * 100, 1))%)" -ForegroundColor Green
Write-Host ""
Write-Host "Cleanup commands:" -ForegroundColor Cyan
Write-Host "  .\scripts\cleanup_temp_files.ps1           # Clean cache (~$(Format-FileSize $totalCacheSize))" -ForegroundColor Gray
Write-Host "  .\scripts\deep_cleanup.ps1 -Confirm        # Deep clean (node_modules, venv)" -ForegroundColor Gray
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan

<#
.SYNOPSIS
    Analyze disk usage patterns in the hw-1 project

.DESCRIPTION
    Comprehensive disk usage analysis tool that helps identify optimization opportunities.
    Analyzes directories, file types, caches, large files, and optionally duplicates.

.PARAMETER AnalyzeVersions
    Analyze version directories (v01-v25) and their out/ folders

.PARAMETER FindDuplicates
    Find duplicate files by MD5 hash (slow, may take several minutes)

.PARAMETER FindLargeFiles
    Find and list large files

.PARAMETER MinSizeMB
    Minimum file size for large file search (default: 10 MB)

.PARAMETER ExportCSV
    Export analysis results to CSV files

.PARAMETER Detailed
    Show detailed analysis output

.EXAMPLE
    .\analyze_disk_usage.ps1
    Basic disk usage analysis

.EXAMPLE
    .\analyze_disk_usage.ps1 -AnalyzeVersions
    Include version directory analysis

.EXAMPLE
    .\analyze_disk_usage.ps1 -FindLargeFiles -MinSizeMB 5
    Find files larger than 5 MB

.EXAMPLE
    .\analyze_disk_usage.ps1 -FindDuplicates -ExportCSV
    Find duplicates and export to CSV

.EXAMPLE
    .\analyze_disk_usage.ps1 -AnalyzeVersions -FindLargeFiles -ExportCSV
    Full analysis with CSV export

.NOTES
    Author: Auto-generated by Claude Code
    Date: 2026-06-05
    Project: hw-1 Gait Training Assistance Device
#>

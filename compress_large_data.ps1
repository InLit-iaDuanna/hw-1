# compress_large_data.ps1
# 压缩 hw-1 项目中的大型 CSV 数据文件
# 主要针对 V13-V17 的参数扫描数据
# 用法:
#   .\compress_large_data.ps1           # 执行压缩
#   .\compress_large_data.ps1 -DryRun   # 预览将要压缩的内容
#   .\compress_large_data.ps1 -Threshold 2  # 压缩大于 2MB 的 CSV

param(
    [switch]$DryRun = $false,
    [double]$Threshold = 1.0  # 压缩阈值（MB）
)

$projectRoot = "D:\Dunna\Documents\hw-1"
$compressedRoot = "$projectRoot\archives\compressed_data"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "hw-1 大型数据文件压缩工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "压缩阈值: $Threshold MB" -ForegroundColor Gray
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN 模式] 仅预览，不会压缩任何文件" -ForegroundColor Yellow
    Write-Host ""
}

# 需要压缩的版本目录（主要是扫描数据较多的版本）
$targetVersions = @(
    "v13_7_floquet_analysis",
    "v13_7_friction_compensation",
    "v13b_floquet_long_run",
    "v15_1_sea_direct",
    "v16_motor_dynamics",
    "v17_state_estimation"
)

# 统计变量
$totalOriginalSize = 0
$totalCompressedSize = 0
$totalFiles = 0

function Compress-VersionData {
    param(
        [string]$VersionPath,
        [double]$ThresholdBytes
    )

    $fullPath = "$projectRoot\$VersionPath\out"

    if (-not (Test-Path $fullPath)) {
        Write-Host "[跳过] $VersionPath - 输出目录不存在" -ForegroundColor DarkGray
        return
    }

    # 查找大于阈值的 CSV 文件
    $csvFiles = Get-ChildItem -Path $fullPath -Filter "*.csv" -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Length -gt $ThresholdBytes }

    if ($csvFiles.Count -eq 0) {
        Write-Host "[跳过] $VersionPath - 没有需要压缩的大型 CSV" -ForegroundColor DarkGray
        return
    }

    Write-Host "[$VersionPath]" -ForegroundColor Green
    Write-Host "  路径: $fullPath" -ForegroundColor Gray
    Write-Host "  符合条件的 CSV: $($csvFiles.Count) 个" -ForegroundColor Gray

    # 计算总大小
    $versionSize = ($csvFiles | Measure-Object -Property Length -Sum).Sum
    $versionSizeMB = [math]::Round($versionSize / 1MB, 2)
    Write-Host "  总大小: $versionSizeMB MB" -ForegroundColor Gray

    # 准备压缩
    $archiveName = "$VersionPath`_scan_data_$(Get-Date -Format 'yyyyMMdd').zip"
    $archivePath = "$compressedRoot\$archiveName"

    Write-Host "  目标归档: $archiveName" -ForegroundColor Gray

    if (-not $DryRun) {
        try {
            # 确保压缩目录存在
            if (-not (Test-Path $compressedRoot)) {
                New-Item -ItemType Directory -Path $compressedRoot -Force | Out-Null
            }

            # 压缩文件
            $tempList = $csvFiles | Select-Object -ExpandProperty FullName
            Compress-Archive -Path $tempList -DestinationPath $archivePath -Force -ErrorAction Stop

            # 检查压缩后大小
            $compressedSize = (Get-Item $archivePath).Length
            $compressedSizeMB = [math]::Round($compressedSize / 1MB, 2)
            $compressionRatio = [math]::Round((1 - $compressedSize / $versionSize) * 100, 1)

            Write-Host "  压缩后: $compressedSizeMB MB (节省 $compressionRatio%)" -ForegroundColor Green

            # 询问是否删除原文件
            Write-Host "  是否删除原始 CSV 文件？(Y/N): " -ForegroundColor Yellow -NoNewline
            $confirmation = Read-Host

            if ($confirmation -eq 'Y' -or $confirmation -eq 'y') {
                foreach ($file in $csvFiles) {
                    Remove-Item -Path $file.FullName -Force
                }
                Write-Host "  状态: 已压缩并删除原文件" -ForegroundColor Green

                $script:totalCompressedSize += $compressedSize
            } else {
                Write-Host "  状态: 已压缩，保留原文件" -ForegroundColor Yellow
                $script:totalCompressedSize += $versionSize  # 未删除，统计中保持原大小
            }

            $script:totalOriginalSize += $versionSize
            $script:totalFiles += $csvFiles.Count

        } catch {
            Write-Host "  状态: 压缩失败 - $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  状态: [预览] 将被压缩" -ForegroundColor Yellow
        $script:totalOriginalSize += $versionSize
        $script:totalFiles += $csvFiles.Count
    }

    Write-Host ""
}

# 创建压缩归档说明文件
function New-CompressionReadme {
    if (-not $DryRun) {
        if (-not (Test-Path $compressedRoot)) {
            New-Item -ItemType Directory -Path $compressedRoot -Force | Out-Null
        }

        $readmePath = "$compressedRoot\README.md"
        $readmeContent = @"
# 压缩数据归档

本目录存放已压缩的大型 CSV 扫描数据。

压缩时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
压缩阈值: $Threshold MB

## 为什么压缩？

V13-V17 的参数扫描实验产生了大量 CSV 数据文件：
- 单个文件大小 1-3 MB
- 总计超过 100 MB
- 大多数情况下不需要直接访问

压缩后可以：
- 节省磁盘空间（通常节省 80-90%）
- 保留数据以备需要时恢复
- 加快项目同步和备份速度

## 解压方法

需要访问压缩数据时：

``````powershell
# 解压到原目录
Expand-Archive -Path "v13_7_floquet_analysis_scan_data_20260604.zip" ``
               -DestinationPath "..\..\v13_7_floquet_analysis\out\"
``````

或使用 Windows 资源管理器右键解压。

## 压缩清单

每个 ZIP 文件包含对应版本 /out/ 目录下的大型 CSV 文件（> $Threshold MB）。

文件命名格式: `{版本目录名}_scan_data_{日期}.zip`

## 注意事项

- 原始 CSV 文件在压缩后可选择删除
- 小于阈值的 CSV 文件不会被压缩
- 核心结果文件（如 *_verdict.json）不会被压缩
- 视频和图像文件不在此压缩范围内
"@
        Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8
    }
}

Write-Host "=== 扫描大型 CSV 数据文件 ===" -ForegroundColor Cyan
Write-Host ""

$thresholdBytes = $Threshold * 1MB

foreach ($version in $targetVersions) {
    Compress-VersionData -VersionPath $version -ThresholdBytes $thresholdBytes
}

# 创建说明文件
if (-not $DryRun -and $totalFiles -gt 0) {
    New-CompressionReadme
}

# 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "压缩统计" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalOriginalSizeMB = [math]::Round($totalOriginalSize / 1MB, 2)
$totalCompressedSizeMB = [math]::Round($totalCompressedSize / 1MB, 2)

Write-Host "文件数量: $totalFiles" -ForegroundColor Green
Write-Host "原始大小: $totalOriginalSizeMB MB" -ForegroundColor Green

if (-not $DryRun -and $totalFiles -gt 0) {
    Write-Host "压缩后大小: $totalCompressedSizeMB MB" -ForegroundColor Green

    if ($totalOriginalSize -gt 0) {
        $savedSize = $totalOriginalSize - $totalCompressedSize
        $savedSizeMB = [math]::Round($savedSize / 1MB, 2)
        $savedPercent = [math]::Round(($savedSize / $totalOriginalSize) * 100, 1)
        Write-Host "节省空间: $savedSizeMB MB ($savedPercent%)" -ForegroundColor Green
    }
}

Write-Host ""

if ($DryRun) {
    Write-Host "这是预览模式，未压缩任何文件。" -ForegroundColor Yellow
    Write-Host "要执行压缩，请运行: .\compress_large_data.ps1" -ForegroundColor Yellow
} else {
    if ($totalFiles -gt 0) {
        Write-Host "压缩完成！" -ForegroundColor Green
        Write-Host ""
        Write-Host "压缩归档位置: $compressedRoot" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "提示：压缩文件已创建，原始文件根据您的选择保留或删除。" -ForegroundColor Gray
    } else {
        Write-Host "未找到需要压缩的文件。" -ForegroundColor Yellow
    }
}

Write-Host ""

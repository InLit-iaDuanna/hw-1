# Generate All Animations
# 为所有版本生成动画视频，用于演示和可视化

param(
    [Parameter(Mandatory=$false)]
    [string[]]$versions = @(),  # 指定版本，留空则生成所有

    [Parameter(Mandatory=$false)]
    [int]$fps = 30,  # 视频帧率

    [Parameter(Mandatory=$false)]
    [int]$width = 1280,  # 视频宽度

    [Parameter(Mandatory=$false)]
    [int]$height = 720,  # 视频高度

    [Parameter(Mandatory=$false)]
    [switch]$highQuality,  # 高质量模式

    [Parameter(Mandatory=$false)]
    [string]$outputDir = "D:\Dunna\Documents\hw-1\animations"
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"

# 高质量模式设置
if ($highQuality) {
    $fps = 60
    $width = 1920
    $height = 1080
}

# 定义版本配置（带最佳参数）
$versionConfigs = @{
    "v10" = @{
        dir = "v10_rolling_foot_biomimetic_gait"
        script = "simulate_rolling_foot_gait_v10.py"
        title = "V10 足踝滚动基线"
        params = @{
            duration = 8.0
            camera_mode = "follow"
        }
    }
    "v13.6" = @{
        dir = "v13_6_event_driven_fsm"
        script = "simulate_v13_6.py"
        title = "V13.6 事件驱动FSM"
        params = @{
            duration = 8.0
            camera_mode = "follow"
        }
    }
    "v13.7" = @{
        dir = "v13_7_friction_compensation"
        script = "simulate_v13_7.py"
        title = "V13.7 摩擦补偿"
        params = @{
            duration = 10.0
            camera_mode = "follow"
        }
    }
    "v14c" = @{
        dir = "v14c_arm_mass_lightening"
        script = "simulate_v14c.py"
        title = "V14c 摆臂减重"
        params = @{
            duration = 8.0
            camera_mode = "follow"
        }
    }
    "v16" = @{
        dir = "v16_motor_dynamics"
        script = "simulate_v16.py"
        title = "V16 电机动力学"
        params = @{
            duration = 8.0
            camera_mode = "follow"
            motor_preset = "mx64ar_full"
        }
    }
    "v17" = @{
        dir = "v17_state_estimation"
        script = "simulate_v17.py"
        title = "V17 状态估计"
        params = @{
            duration = 10.0
            camera_mode = "follow"
            noise_scale = 1.0
        }
    }
}

# 过滤版本
if ($versions.Count -gt 0) {
    $versionConfigs = $versionConfigs.GetEnumerator() | Where-Object { $versions -contains $_.Key }
}

# 创建输出目录
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$outputDir\generation_$timestamp.log"

function Write-Log {
    param([string]$message, [string]$level = "INFO")

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$level] $message"

    switch ($level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        default { Write-Host $logMessage -ForegroundColor White }
    }

    Add-Content -Path $logFile -Value $logMessage -Encoding UTF8
}

function Generate-Animation {
    param(
        [string]$versionKey,
        [hashtable]$config
    )

    Write-Log "开始生成 $versionKey 动画..." "INFO"

    $versionDir = Join-Path $projectRoot $config.dir
    $scriptPath = Join-Path $versionDir $config.script

    if (-not (Test-Path $scriptPath)) {
        Write-Log "脚本不存在: $scriptPath" "ERROR"
        return $false
    }

    $videoFile = "$outputDir\${versionKey}_${timestamp}.mp4"

    # 构建命令行参数
    $args = @(
        $scriptPath,
        "--duration", $config.params.duration,
        "--render",
        "--video-output", $videoFile,
        "--fps", $fps,
        "--width", $width,
        "--height", $height
    )

    # 添加额外参数
    if ($config.params.camera_mode) {
        $args += "--camera-mode", $config.params.camera_mode
    }
    if ($config.params.motor_preset) {
        $args += "--motor-preset", $config.params.motor_preset
    }
    if ($config.params.noise_scale) {
        $args += "--noise-scale", $config.params.noise_scale
    }

    try {
        $startTime = Get-Date

        Write-Log "命令: python $scriptPath ..." "INFO"
        & $pythonExe @args 2>&1 | Out-Null

        $endTime = Get-Date
        $elapsed = ($endTime - $startTime).TotalSeconds

        if ($LASTEXITCODE -eq 0 -and (Test-Path $videoFile)) {
            $fileSize = (Get-Item $videoFile).Length / 1MB
            Write-Log "$versionKey 完成 (耗时: $([math]::Round($elapsed, 2))s, 大小: $([math]::Round($fileSize, 2)) MB)" "SUCCESS"
            return $true
        } else {
            Write-Log "$versionKey 失败 (退出码: $LASTEXITCODE)" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "$versionKey 异常: $_" "ERROR"
        return $false
    }
}

# 主执行流程
Write-Log "========================================" "INFO"
Write-Log "批量动画生成开始" "INFO"
Write-Log "版本数: $($versionConfigs.Count)" "INFO"
Write-Log "分辨率: ${width}x${height} @ ${fps}fps" "INFO"
Write-Log "输出目录: $outputDir" "INFO"
Write-Log "========================================" "INFO"

$successCount = 0
$failCount = 0

foreach ($version in $versionConfigs.GetEnumerator()) {
    $success = Generate-Animation -versionKey $version.Key -config $version.Value

    if ($success) {
        $successCount++
    } else {
        $failCount++
    }

    # 短暂休息，避免资源占用过高
    Start-Sleep -Seconds 2
}

# 生成摘要
Write-Log "========================================" "INFO"
Write-Log "批量动画生成完成" "INFO"
Write-Log "成功: $successCount / 失败: $failCount / 总计: $($versionConfigs.Count)" "INFO"
Write-Log "输出目录: $outputDir" "INFO"
Write-Log "日志文件: $logFile" "INFO"
Write-Log "========================================" "INFO"

# 列出生成的文件
Write-Log "`n生成的动画文件:" "INFO"
Get-ChildItem -Path $outputDir -Filter "*.mp4" |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-60) } |
    ForEach-Object {
        $size = $_.Length / 1MB
        Write-Log "  - $($_.Name) ($([math]::Round($size, 2)) MB)" "INFO"
    }

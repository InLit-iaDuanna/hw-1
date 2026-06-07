# Batch Run All Versions
# 批量运行所有版本的仿真，用于回归测试或生成完整数据集

param(
    [Parameter(Mandatory=$false)]
    [string[]]$versions = @(),  # 指定版本，留空则运行所有

    [Parameter(Mandatory=$false)]
    [double]$duration = 5.0,  # 仿真时长（秒）

    [Parameter(Mandatory=$false)]
    [switch]$quick,  # 快速模式：只运行核心版本

    [Parameter(Mandatory=$false)]
    [switch]$parallel,  # 并行执行（实验性）

    [Parameter(Mandatory=$false)]
    [string]$outputDir = "D:\Dunna\Documents\hw-1\batch_results"
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"

# 定义版本配置
$allVersions = @{
    "v10" = @{
        dir = "v10_rolling_foot_biomimetic_gait"
        script = "simulate_rolling_foot_gait_v10.py"
        description = "足踝滚动基线"
        priority = 1
    }
    "v13.6" = @{
        dir = "v13_6_event_driven_fsm"
        script = "simulate_v13_6.py"
        description = "事件驱动FSM"
        priority = 1
    }
    "v13.7" = @{
        dir = "v13_7_friction_compensation"
        script = "simulate_v13_7.py"
        description = "摩擦补偿"
        priority = 1
    }
    "v14c" = @{
        dir = "v14c_arm_mass_lightening"
        script = "simulate_v14c.py"
        description = "摆臂减重"
        priority = 2
    }
    "v16" = @{
        dir = "v16_motor_dynamics"
        script = "simulate_v16.py"
        description = "电机动力学"
        priority = 2
    }
    "v17" = @{
        dir = "v17_state_estimation"
        script = "simulate_v17.py"
        description = "状态估计"
        priority = 1
    }
}

# 快速模式：只运行优先级1的版本
if ($quick) {
    $allVersions = $allVersions.GetEnumerator() | Where-Object { $_.Value.priority -eq 1 }
}

# 如果指定了版本，只运行这些版本
if ($versions.Count -gt 0) {
    $allVersions = $allVersions.GetEnumerator() | Where-Object { $versions -contains $_.Key }
}

# 创建输出目录
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$outputDir\batch_run_$timestamp.log"

function Write-Log {
    param([string]$message, [string]$level = "INFO")

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$level] $message"

    # 输出到控制台
    switch ($level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        default { Write-Host $logMessage -ForegroundColor White }
    }

    # 写入日志文件
    Add-Content -Path $logFile -Value $logMessage -Encoding UTF8
}

function Run-Version {
    param(
        [string]$versionKey,
        [hashtable]$versionConfig
    )

    $versionDir = Join-Path $projectRoot $versionConfig.dir
    $scriptPath = Join-Path $versionDir $versionConfig.script

    Write-Log "开始运行 $versionKey - $($versionConfig.description)" "INFO"

    if (-not (Test-Path $scriptPath)) {
        Write-Log "脚本不存在: $scriptPath" "ERROR"
        return @{
            version = $versionKey
            success = $false
            error = "Script not found"
        }
    }

    $outputFile = "$outputDir\${versionKey}_${timestamp}.json"

    try {
        $startTime = Get-Date

        # 运行仿真
        & $pythonExe $scriptPath --duration $duration --output $outputFile 2>&1 | Out-Null

        $endTime = Get-Date
        $elapsed = ($endTime - $startTime).TotalSeconds

        if ($LASTEXITCODE -eq 0 -and (Test-Path $outputFile)) {
            Write-Log "$versionKey 完成 (耗时: $([math]::Round($elapsed, 2))s)" "SUCCESS"
            return @{
                version = $versionKey
                success = $true
                elapsed = $elapsed
                output = $outputFile
            }
        } else {
            Write-Log "$versionKey 失败 (退出码: $LASTEXITCODE)" "ERROR"
            return @{
                version = $versionKey
                success = $false
                error = "Exit code: $LASTEXITCODE"
                elapsed = $elapsed
            }
        }
    }
    catch {
        Write-Log "$versionKey 异常: $_" "ERROR"
        return @{
            version = $versionKey
            success = $false
            error = $_.Exception.Message
        }
    }
}

# 主执行流程
Write-Log "========================================" "INFO"
Write-Log "批量仿真开始" "INFO"
Write-Log "总版本数: $($allVersions.Count)" "INFO"
Write-Log "仿真时长: ${duration}s" "INFO"
Write-Log "输出目录: $outputDir" "INFO"
Write-Log "========================================" "INFO"

$results = @()

if ($parallel) {
    Write-Log "使用并行模式（实验性功能）" "WARNING"

    # 并行执行（使用后台作业）
    $jobs = @()
    foreach ($version in $allVersions.GetEnumerator()) {
        $job = Start-Job -ScriptBlock {
            param($versionKey, $versionConfig, $projectRoot, $pythonExe, $duration, $outputDir, $timestamp)

            $versionDir = Join-Path $projectRoot $versionConfig.dir
            $scriptPath = Join-Path $versionDir $versionConfig.script
            $outputFile = "$outputDir\${versionKey}_${timestamp}.json"

            if (-not (Test-Path $scriptPath)) {
                return @{
                    version = $versionKey
                    success = $false
                    error = "Script not found"
                }
            }

            try {
                $startTime = Get-Date
                & $pythonExe $scriptPath --duration $duration --output $outputFile 2>&1 | Out-Null
                $endTime = Get-Date
                $elapsed = ($endTime - $startTime).TotalSeconds

                return @{
                    version = $versionKey
                    success = ($LASTEXITCODE -eq 0)
                    elapsed = $elapsed
                    output = $outputFile
                }
            }
            catch {
                return @{
                    version = $versionKey
                    success = $false
                    error = $_.Exception.Message
                }
            }
        } -ArgumentList $version.Key, $version.Value, $projectRoot, $pythonExe, $duration, $outputDir, $timestamp

        $jobs += $job
    }

    # 等待所有作业完成
    $results = $jobs | Wait-Job | Receive-Job
    $jobs | Remove-Job

} else {
    # 串行执行
    foreach ($version in $allVersions.GetEnumerator()) {
        $result = Run-Version -versionKey $version.Key -versionConfig $version.Value
        $results += $result
    }
}

# 生成摘要报告
Write-Log "========================================" "INFO"
Write-Log "批量仿真完成" "INFO"

$successCount = ($results | Where-Object { $_.success }).Count
$failCount = ($results | Where-Object { -not $_.success }).Count
$totalTime = ($results | Where-Object { $_.elapsed } | Measure-Object -Property elapsed -Sum).Sum

Write-Log "成功: $successCount / 失败: $failCount / 总计: $($results.Count)" "INFO"
Write-Log "总耗时: $([math]::Round($totalTime, 2))s" "INFO"

# 保存结果到JSON
$reportPath = "$outputDir\batch_run_${timestamp}_summary.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $reportPath -Encoding UTF8

Write-Log "结果已保存到: $reportPath" "SUCCESS"
Write-Log "日志文件: $logFile" "INFO"
Write-Log "========================================" "INFO"

# 返回结果
return $results

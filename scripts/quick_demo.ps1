# Quick Demo Script
# 快速演示脚本，运行关键版本展示项目效果

param(
    [Parameter(Mandatory=$false)]
    [switch]$withVideo,  # 生成视频

    [Parameter(Mandatory=$false)]
    [switch]$fullDemo,  # 完整演示（包含所有版本）

    [Parameter(Mandatory=$false)]
    [string]$outputDir = "D:\Dunna\Documents\hw-1\demo_output"
)

$ErrorActionPreference = "Continue"
$projectRoot = "D:\Dunna\Documents\hw-1"
$pythonExe = "$projectRoot\.venv-mujoco\Scripts\python.exe"

# 创建输出目录
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

function Write-Banner {
    param([string]$text)
    $line = "=" * 60
    Write-Host "`n$line" -ForegroundColor Cyan
    Write-Host $text -ForegroundColor Cyan
    Write-Host "$line`n" -ForegroundColor Cyan
}

function Run-Demo {
    param(
        [string]$version,
        [string]$dir,
        [string]$script,
        [string]$description,
        [hashtable]$params
    )

    Write-Banner "$version - $description"

    $versionDir = Join-Path $projectRoot $dir
    $scriptPath = Join-Path $versionDir $script

    if (-not (Test-Path $scriptPath)) {
        Write-Host "✗ 脚本不存在: $scriptPath" -ForegroundColor Red
        return $false
    }

    # 构建参数
    $args = @($scriptPath)
    foreach ($key in $params.Keys) {
        $args += "--$key"
        $args += $params[$key]
    }

    # 添加输出路径
    $outputFile = "$outputDir\${version}_demo_$timestamp"
    $args += "--output"
    $args += "$outputFile.json"

    if ($withVideo) {
        $args += "--render"
        $args += "--video-output"
        $args += "$outputFile.mp4"
    }

    try {
        Write-Host "运行中..." -ForegroundColor Yellow
        $startTime = Get-Date

        & $pythonExe @args

        $endTime = Get-Date
        $elapsed = ($endTime - $startTime).TotalSeconds

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ 完成 (耗时: $([math]::Round($elapsed, 2))s)" -ForegroundColor Green

            # 显示关键指标
            if (Test-Path "$outputFile.json") {
                try {
                    $result = Get-Content "$outputFile.json" -Raw | ConvertFrom-Json

                    Write-Host "`n关键指标:" -ForegroundColor Cyan
                    Write-Host "  前进距离: $([math]::Round($result.forward_distance, 2)) m" -ForegroundColor White
                    Write-Host "  足部交替: $($result.alternations) 次" -ForegroundColor White

                    if ($result.cot) {
                        Write-Host "  CoT: $([math]::Round($result.cot, 4))" -ForegroundColor White
                    }

                    if ($result.success) {
                        Write-Host "  状态: 成功 ✓" -ForegroundColor Green
                    } else {
                        Write-Host "  状态: 失败 ($($result.failure_mode))" -ForegroundColor Yellow
                    }
                }
                catch {
                    Write-Host "  (无法解析结果数据)" -ForegroundColor Gray
                }
            }

            return $true
        } else {
            Write-Host "✗ 失败 (退出码: $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "✗ 异常: $_" -ForegroundColor Red
        return $false
    }
}

# 定义演示配置
$demoConfigs = @(
    @{
        version = "V10"
        dir = "v10_rolling_foot_biomimetic_gait"
        script = "simulate_rolling_foot_gait_v10.py"
        description = "足踝滚动基线 (PD控制)"
        params = @{
            duration = 8.0
        }
        priority = 1
    },
    @{
        version = "V13.7"
        dir = "v13_7_friction_compensation"
        script = "simulate_v13_7.py"
        description = "摩擦补偿 (FSM + 前馈补偿)"
        params = @{
            duration = 10.0
        }
        priority = 1
    },
    @{
        version = "V17"
        dir = "v17_state_estimation"
        script = "simulate_v17.py"
        description = "状态估计 (传感器噪声 + Kalman滤波)"
        params = @{
            duration = 10.0
            "noise-scale" = 1.0
        }
        priority = 1
    }
)

if ($fullDemo) {
    $demoConfigs += @(
        @{
            version = "V13.6"
            dir = "v13_6_event_driven_fsm"
            script = "simulate_v13_6.py"
            description = "事件驱动FSM"
            params = @{ duration = 8.0 }
            priority = 2
        },
        @{
            version = "V14c"
            dir = "v14c_arm_mass_lightening"
            script = "simulate_v14c.py"
            description = "摆臂减重"
            params = @{ duration = 8.0 }
            priority = 2
        },
        @{
            version = "V16"
            dir = "v16_motor_dynamics"
            script = "simulate_v16.py"
            description = "电机动力学"
            params = @{
                duration = 8.0
                "motor-preset" = "mx64ar_full"
            }
            priority = 2
        }
    )
}

# 过滤优先级
if (-not $fullDemo) {
    $demoConfigs = $demoConfigs | Where-Object { $_.priority -eq 1 }
}

# 显示欢迎信息
Write-Host @"

╔════════════════════════════════════════════════════════════╗
║                                                            ║
║          hw-1 步态训练康复设备 - 快速演示                   ║
║                                                            ║
║  展示 V01-V24 版本中的关键技术演进                          ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Write-Host "演示配置:" -ForegroundColor Cyan
Write-Host "  版本数量: $($demoConfigs.Count)" -ForegroundColor White
Write-Host "  视频生成: $(if ($withVideo) { '是' } else { '否' })" -ForegroundColor White
Write-Host "  输出目录: $outputDir" -ForegroundColor White
Write-Host ""

# 开始演示
$successCount = 0
$failCount = 0

foreach ($config in $demoConfigs) {
    $success = Run-Demo `
        -version $config.version `
        -dir $config.dir `
        -script $config.script `
        -description $config.description `
        -params $config.params

    if ($success) {
        $successCount++
    } else {
        $failCount++
    }

    # 短暂暂停
    Start-Sleep -Seconds 1
}

# 生成演示摘要
Write-Banner "演示完成"

Write-Host "结果统计:" -ForegroundColor Cyan
Write-Host "  成功: $successCount" -ForegroundColor Green
Write-Host "  失败: $failCount" -ForegroundColor Red
Write-Host "  总计: $($demoConfigs.Count)" -ForegroundColor White
Write-Host ""

Write-Host "输出文件:" -ForegroundColor Cyan
Get-ChildItem -Path $outputDir -Filter "*demo_$timestamp*" | ForEach-Object {
    $size = $_.Length / 1KB
    $sizeStr = if ($size -gt 1024) { "$([math]::Round($size/1024, 2)) MB" } else { "$([math]::Round($size, 2)) KB" }
    Write-Host "  - $($_.Name) ($sizeStr)" -ForegroundColor White
}

Write-Host "`n演示总结:" -ForegroundColor Cyan
Write-Host @"

  V10:  足踝滚动基线 - 展示基础准被动行走机制
  V13.7: 摩擦补偿 - 展示 FSM 控制 + 前馈补偿修复电机摩擦问题
  V17:  状态估计 - 展示传感器噪声下的鲁棒控制

  技术演进路径:
  V10 (PD基线) → V13.6 (FSM) → V13.7 (摩擦补偿) → V17 (状态估计) → V22 (硬件设计)

"@ -ForegroundColor Gray

if ($withVideo) {
    Write-Host "视频文件已生成，可用于演示和汇报。" -ForegroundColor Green
}

Write-Host "`n要查看完整项目信息，请运行:" -ForegroundColor Yellow
Write-Host "  .\scripts\check_project_health.ps1" -ForegroundColor White
Write-Host ""

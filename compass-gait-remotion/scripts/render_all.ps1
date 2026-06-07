# 自动渲染所有 Remotion 动画
# 用法: .\scripts\render_all.ps1

param(
    [switch]$HighQuality,  # 使用高质量设置
    [switch]$LowQuality,   # 使用低质量设置（快速预览）
    [string]$Only          # 只渲染指定的 composition
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Remotion 动画批量渲染" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 切换到项目目录
Set-Location "$PSScriptRoot\.."

# 检查 node_modules 是否存在
if (-not (Test-Path "node_modules")) {
    Write-Host "未找到 node_modules，正在安装依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 创建输出目录
New-Item -ItemType Directory -Path "out" -Force | Out-Null

# 定义所有 composition
$compositions = @(
    @{
        id = "FSMStateTransition"
        name = "V13.6 四相位状态机"
        output = "out/fsm_state_transition.mp4"
    },
    @{
        id = "RollingFootAnimation"
        name = "V10 足踝滚动动画"
        output = "out/rolling_foot_animation.mp4"
    },
    @{
        id = "PhaseVisualization"
        name = "步态相位可视化"
        output = "out/phase_visualization.mp4"
    },
    @{
        id = "GaitComparison"
        name = "V10 vs V13.6 对比"
        output = "out/gait_comparison.mp4"
    }
)

# 如果指定了 Only，只渲染指定的
if ($Only) {
    $compositions = $compositions | Where-Object { $_.id -eq $Only }
    if ($compositions.Count -eq 0) {
        Write-Host "未找到 composition: $Only" -ForegroundColor Red
        Write-Host "可用的 compositions:" -ForegroundColor Yellow
        @("FSMStateTransition", "RollingFootAnimation", "PhaseVisualization", "GaitComparison") | ForEach-Object {
            Write-Host "  - $_" -ForegroundColor Yellow
        }
        exit 1
    }
}

# 设置渲染质量
$quality = "medium"
$codec = "h264"
$crf = 18

if ($HighQuality) {
    $quality = "high"
    $crf = 15
    Write-Host "使用高质量设置 (CRF=$crf)" -ForegroundColor Green
} elseif ($LowQuality) {
    $quality = "low"
    $crf = 28
    Write-Host "使用低质量设置 (CRF=$crf, 快速预览)" -ForegroundColor Yellow
} else {
    Write-Host "使用中等质量设置 (CRF=$crf)" -ForegroundColor Green
}

Write-Host ""

# 渲染每个 composition
$success_count = 0
$total_count = $compositions.Count

foreach ($comp in $compositions) {
    Write-Host "[$($success_count + 1)/$total_count] 渲染: $($comp.name)" -ForegroundColor Cyan
    Write-Host "  ID: $($comp.id)" -ForegroundColor Gray
    Write-Host "  输出: $($comp.output)" -ForegroundColor Gray

    $start_time = Get-Date

    # 构建渲染命令
    $args = @(
        "remotion", "render",
        $comp.id,
        $comp.output,
        "--codec=$codec",
        "--crf=$crf"
    )

    try {
        & npx @args

        if ($LASTEXITCODE -eq 0) {
            $duration = (Get-Date) - $start_time
            $file_size = (Get-Item $comp.output).Length / 1MB

            Write-Host "  ✓ 渲染成功" -ForegroundColor Green
            Write-Host "    耗时: $($duration.TotalSeconds.ToString('F1'))s" -ForegroundColor Gray
            Write-Host "    文件大小: $($file_size.ToString('F2')) MB" -ForegroundColor Gray
            $success_count++
        } else {
            Write-Host "  ✗ 渲染失败 (退出码: $LASTEXITCODE)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ 渲染失败: $_" -ForegroundColor Red
    }

    Write-Host ""
}

# 汇总
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "渲染完成: $success_count/$total_count" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

if ($success_count -eq $total_count) {
    Write-Host "所有动画渲染成功！" -ForegroundColor Green
    Write-Host "输出目录: $(Resolve-Path 'out')" -ForegroundColor Green

    # 列出所有输出文件
    Write-Host "`n输出文件:" -ForegroundColor Green
    Get-ChildItem "out" -Filter "*.mp4" | ForEach-Object {
        $size = $_.Length / 1MB
        Write-Host "  - $($_.Name) ($($size.ToString('F2')) MB)" -ForegroundColor Gray
    }
} else {
    Write-Host "部分动画渲染失败，请检查错误信息" -ForegroundColor Yellow
    exit 1
}

# 项目依赖检查和更新脚本
# 检查依赖包的版本并提供更新建议

param(
    [switch]$Check,      # 仅检查，不更新
    [switch]$Update,     # 更新过期的包
    [switch]$Freeze      # 导出当前环境到 requirements-freeze.txt
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Dunna\Documents\hw-1"
$VenvPath = Join-Path $ProjectRoot ".venv-mujoco"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"

function Write-Section {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Check-Dependencies {
    Write-Section "检查依赖包状态"

    # 检查核心依赖
    $coreDeps = @("mujoco", "numpy", "matplotlib", "scipy", "pytest")

    Write-Host "核心依赖包:" -ForegroundColor Yellow
    foreach ($pkg in $coreDeps) {
        $installed = & $PipExe show $pkg 2>&1 | Select-String "Version:"
        if ($installed) {
            $version = $installed -replace "Version: ", ""
            Write-Host "  ✓ $pkg $version" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $pkg (未安装)" -ForegroundColor Red
        }
    }

    # 检查过期的包
    Write-Host "`n检查过期的包..." -ForegroundColor Yellow
    $outdated = & $PipExe list --outdated --format=columns 2>&1

    if ($outdated -match "Package") {
        Write-Host $outdated -ForegroundColor White
    } else {
        Write-Host "所有包都是最新版本！" -ForegroundColor Green
    }
}

function Update-Dependencies {
    Write-Section "更新依赖包"

    # 先升级 pip
    Write-Host "升级 pip..." -ForegroundColor Yellow
    & $PipExe install --upgrade pip

    # 更新 requirements.txt 中的包
    $requirementsPath = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $requirementsPath) {
        Write-Host "从 requirements.txt 更新依赖..." -ForegroundColor Yellow
        & $PipExe install --upgrade -r $requirementsPath
        Write-Host "依赖更新完成！" -ForegroundColor Green
    } else {
        Write-Host "未找到 requirements.txt" -ForegroundColor Red
    }
}

function Export-Dependencies {
    Write-Section "导出依赖列表"

    $freezePath = Join-Path $ProjectRoot "requirements-freeze.txt"
    & $PipExe freeze > $freezePath

    Write-Host "依赖列表已导出到: $freezePath" -ForegroundColor Green

    # 显示包数量
    $count = (Get-Content $freezePath | Measure-Object -Line).Lines
    Write-Host "总共 $count 个包" -ForegroundColor White
}

# 主逻辑
Set-Location $ProjectRoot

if (-not (Test-Path $VenvPath)) {
    Write-Host "错误: 虚拟环境不存在: $VenvPath" -ForegroundColor Red
    Write-Host "请先运行: .\scripts\setup_env.ps1" -ForegroundColor Yellow
    exit 1
}

if ($Update) {
    Update-Dependencies
} elseif ($Freeze) {
    Export-Dependencies
} else {
    Check-Dependencies
}

Write-Host "`n完成！" -ForegroundColor Green

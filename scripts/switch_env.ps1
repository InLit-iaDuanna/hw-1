# 环境快速切换和验证脚本
# 用于在不同虚拟环境间切换并验证环境状态

param(
    [Parameter(Position=0)]
    [ValidateSet("mujoco", "codex", "info")]
    [string]$Environment = "info"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Dunna\Documents\hw-1"

function Write-EnvironmentInfo {
    param([string]$VenvPath, [string]$Name)

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "环境信息: $Name" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if (-not (Test-Path $VenvPath)) {
        Write-Host "[错误] 环境不存在: $VenvPath" -ForegroundColor Red
        return
    }

    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"

    # Python 版本
    $version = & $pythonExe --version 2>&1
    Write-Host "Python 版本: $version" -ForegroundColor Green

    # 虚拟环境路径
    Write-Host "环境路径: $VenvPath" -ForegroundColor White

    # 关键包版本
    Write-Host "`n已安装的关键包:" -ForegroundColor Yellow
    $packages = & $pythonExe -m pip list --format=freeze 2>&1 | Select-String "mujoco|numpy|matplotlib|scipy|pytest"
    if ($packages) {
        $packages | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
    } else {
        Write-Host "  (未找到关键包)" -ForegroundColor DarkGray
    }

    # 激活脚本路径
    $activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    Write-Host "`n激活命令:" -ForegroundColor Yellow
    Write-Host "  $activateScript" -ForegroundColor Cyan
}

# 主逻辑
Set-Location $ProjectRoot

$venvMujoco = Join-Path $ProjectRoot ".venv-mujoco"
$venvCodex = Join-Path $ProjectRoot ".venv-codex"

switch ($Environment) {
    "mujoco" {
        Write-Host "切换到 MuJoCo 开发环境..." -ForegroundColor Green
        Write-EnvironmentInfo -VenvPath $venvMujoco -Name ".venv-mujoco"
        Write-Host "`n执行以下命令激活:" -ForegroundColor Yellow
        Write-Host "  .\.venv-mujoco\Scripts\Activate.ps1" -ForegroundColor Cyan
    }
    "codex" {
        Write-Host "切换到 Codex 环境..." -ForegroundColor Green
        Write-EnvironmentInfo -VenvPath $venvCodex -Name ".venv-codex"
        Write-Host "`n执行以下命令激活:" -ForegroundColor Yellow
        Write-Host "  .\.venv-codex\Scripts\Activate.ps1" -ForegroundColor Cyan
    }
    "info" {
        Write-Host "`nhw-1 项目虚拟环境信息" -ForegroundColor Cyan
        Write-Host "========================================"
        Write-EnvironmentInfo -VenvPath $venvMujoco -Name ".venv-mujoco (主要开发)"
        Write-EnvironmentInfo -VenvPath $venvCodex -Name ".venv-codex (Claude Code)"

        Write-Host "`n使用方法:" -ForegroundColor Yellow
        Write-Host "  .\scripts\switch_env.ps1 mujoco   # 显示 MuJoCo 环境信息" -ForegroundColor White
        Write-Host "  .\scripts\switch_env.ps1 codex    # 显示 Codex 环境信息" -ForegroundColor White
        Write-Host "  .\scripts\switch_env.ps1 info     # 显示所有环境信息" -ForegroundColor White
    }
}

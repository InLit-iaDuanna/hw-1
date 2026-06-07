# HW-1 参数调优工具启动脚本

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  HW-1 参数调优工具启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查当前目录
$CurrentDir = Get-Location
$ExpectedDir = "D:\Dunna\Documents\hw-1"

if ($CurrentDir.Path -ne $ExpectedDir) {
    Write-Host "切换到项目目录: $ExpectedDir" -ForegroundColor Yellow
    Set-Location $ExpectedDir
}

# 检查虚拟环境
$VenvPath = ".\.venv-mujoco\Scripts\Activate.ps1"

if (-not (Test-Path $VenvPath)) {
    Write-Host "错误: 虚拟环境不存在 ($VenvPath)" -ForegroundColor Red
    Write-Host "请先创建虚拟环境并安装依赖" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Green
& $VenvPath

# 检查 Streamlit 是否安装
$StreamlitInstalled = & python -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Streamlit 未安装，正在安装依赖..." -ForegroundColor Yellow
    pip install -r parameter_tuner\requirements.txt

    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 创建 cache 目录
$CacheDir = ".\parameter_tuner\cache"
if (-not (Test-Path $CacheDir)) {
    Write-Host "创建缓存目录: $CacheDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动 Streamlit 应用..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "浏览器将自动打开 http://localhost:8501" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

# 启动 Streamlit
streamlit run parameter_tuner\app.py

Write-Host ""
Write-Host "应用已关闭" -ForegroundColor Yellow

# Parameter Tuner 启动脚本
# 使用 .venv-mujoco 环境运行 Streamlit 应用

$ErrorActionPreference = "Stop"

Write-Host "=== HW-1 参数调优工具启动 ===" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境
$venvPath = "D:\Dunna\Documents\hw-1\.venv-mujoco"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$streamlitExe = Join-Path $venvPath "Scripts\streamlit.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "错误: 未找到 .venv-mujoco Python 环境" -ForegroundColor Red
    Write-Host "路径: $pythonExe" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Python 环境: $pythonExe" -ForegroundColor Green

# 检查 Streamlit 是否安装
if (-not (Test-Path $streamlitExe)) {
    Write-Host "警告: Streamlit 未安装，正在安装..." -ForegroundColor Yellow
    & $pythonExe -m pip install streamlit plotly pyyaml

    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: Streamlit 安装失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Streamlit 已就绪" -ForegroundColor Green
Write-Host ""

# 切换到 parameter_tuner 目录
$tunerDir = "D:\Dunna\Documents\hw-1\parameter_tuner"
Set-Location $tunerDir

Write-Host "启动目录: $tunerDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "启动 Streamlit 应用..." -ForegroundColor Cyan
Write-Host "浏览器将自动打开。如未打开，请访问: http://localhost:8501" -ForegroundColor Yellow
Write-Host ""
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

# 启动 Streamlit
& $streamlitExe run app.py --server.port 8501 --server.headless false

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "错误: Streamlit 启动失败 (退出码: $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

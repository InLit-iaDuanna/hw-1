# 跨版本分析工具集 - 一键运行脚本
# 用法: 在 PowerShell 中运行 .\run_all.ps1

$ErrorActionPreference = "Stop"
$PYTHON = "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe"
$SCRIPT_DIR = $PSScriptRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "HW-1 跨版本分析工具集 - 一键运行" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 环境
if (-not (Test-Path $PYTHON)) {
    Write-Host "[ERROR] 未找到 Python: $PYTHON" -ForegroundColor Red
    exit 1
}

# 检查必要的库
Write-Host "[1/4] 检查依赖项..." -ForegroundColor Yellow
$packages = @("matplotlib", "numpy", "pandas")
foreach ($pkg in $packages) {
    $result = & $PYTHON -m pip show $pkg 2>$null
    if (-not $?) {
        Write-Host "  [WARN] 缺少 $pkg，正在安装..." -ForegroundColor Yellow
        & $PYTHON -m pip install $pkg | Out-Null
    } else {
        Write-Host "  [OK] $pkg 已安装" -ForegroundColor Green
    }
}

# 运行综合报告生成器（会自动调用其他三个工具）
Write-Host ""
Write-Host "[2/4] 运行跨版本分析工具..." -ForegroundColor Yellow
Write-Host "      这将依次运行所有分析工具并生成综合报告" -ForegroundColor Gray
Write-Host ""

Set-Location $SCRIPT_DIR
& $PYTHON generate_comprehensive_report.py

if ($?) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] 分析完成！" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "[3/4] 生成的文件:" -ForegroundColor Yellow
    $outputDir = Join-Path $SCRIPT_DIR "out"
    Get-ChildItem $outputDir | ForEach-Object {
        $size = if ($_.Length -gt 1MB) { "{0:N2} MB" -f ($_.Length / 1MB) } else { "{0:N2} KB" -f ($_.Length / 1KB) }
        Write-Host "  - $($_.Name) ($size)" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "[4/4] 打开报告:" -ForegroundColor Yellow
    $reportPath = Join-Path $outputDir "comprehensive_report.html"
    Write-Host "  HTML 报告: $reportPath" -ForegroundColor Cyan

    # 询问是否打开浏览器
    Write-Host ""
    $answer = Read-Host "是否在浏览器中打开报告? (Y/n)"
    if ($answer -eq "" -or $answer -eq "Y" -or $answer -eq "y") {
        Start-Process $reportPath
        Write-Host "  [OK] 已在浏览器中打开报告" -ForegroundColor Green
    }

} else {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "[ERROR] 分析失败，请检查错误信息" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

@echo off
chcp 65001 >nul
echo ================================================================================
echo HW-1 跨版本分析工具集 - 一键运行
echo ================================================================================
echo.
echo 正在启动分析工具...
echo.
powershell.exe -ExecutionPolicy Bypass -File "%~dp0run_all.ps1"
pause

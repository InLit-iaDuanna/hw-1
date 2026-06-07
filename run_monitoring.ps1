# 激活虚拟环境
& .\.venv-mujoco\Scripts\Activate.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "hw-1 项目监控系统 - 完整健康检查" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 健康检查
Write-Host "[1/5] 运行健康检查..." -ForegroundColor Yellow
python monitoring/health_monitor.py
Write-Host ""

# 2. 收集指标
Write-Host "[2/5] 收集指标数据..." -ForegroundColor Yellow
python monitoring/metrics_collector.py
Write-Host ""

# 3. 代码质量监控
Write-Host "[3/5] 代码质量监控..." -ForegroundColor Yellow
python monitoring/monitors/code_quality.py
Write-Host ""

# 4. 告警分析
Write-Host "[4/5] 告警分析..." -ForegroundColor Yellow
python monitoring/alerting.py
Write-Host ""

# 5. 生成报告
Write-Host "[5/5] 生成报告..." -ForegroundColor Yellow
python monitoring/report_generator.py
Write-Host ""

Write-Host "================================================" -ForegroundColor Green
Write-Host "监控完成！" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "查看报告:" -ForegroundColor Cyan
Write-Host "  - 健康报告: monitoring\reports\health_report_latest.md" -ForegroundColor White
Write-Host "  - 详细数据: monitoring\health_report.json" -ForegroundColor White
Write-Host "  - 告警日志: monitoring\alerts.log" -ForegroundColor White
Write-Host ""

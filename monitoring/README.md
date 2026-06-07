# hw-1 监控系统

项目持续监控和健康检查系统。

## 系统架构

```
monitoring/
├── config.yaml                 # 监控配置
├── health_monitor.py           # 健康检查器
├── metrics_collector.py        # 指标收集器
├── alerting.py                 # 告警系统
├── report_generator.py         # 报告生成器
├── monitors/                   # 专项监控模块
│   ├── code_quality.py         # 代码质量监控
│   ├── test_coverage.py        # 测试覆盖率监控
│   ├── performance.py          # 性能监控
│   └── data_integrity.py       # 数据完整性监控
└── reports/                    # 生成的报告
```

## 功能特性

### 1. 健康检查 (`health_monitor.py`)

**检查项**：
- **环境健康**: Python 版本、依赖包版本
- **代码健康**: 关键文件存在性、代码质量检查
- **测试健康**: 测试通过率、覆盖率
- **数据健康**: 关键数据文件完整性

**使用方法**：
```powershell
# 在虚拟环境中运行
.\.venv-mujoco\Scripts\Activate.ps1
python monitoring/health_monitor.py
```

**输出**：
- 控制台输出检查结果
- 生成 `monitoring/health_report.json`

### 2. 指标收集 (`metrics_collector.py`)

**收集指标**：
- **代码度量**: 代码行数、文件数、版本数
- **测试度量**: 测试数量、覆盖率
- **性能度量**: 基准测试结果
- **存储度量**: 目录大小

**使用方法**：
```powershell
python monitoring/metrics_collector.py
```

**输出**：
- `monitoring/metrics_latest.json` - 最新指标
- `monitoring/metrics_history.json` - 历史记录（最多1000条）

### 3. 告警系统 (`alerting.py`)

**告警级别**：
- `CRITICAL` 🔴: 严重问题，需立即处理
- `WARNING` 🟡: 警告，需要关注
- `INFO` 🔵: 信息，仅记录

**告警方式**：
- 控制台输出
- 日志文件 (`monitoring/alerts.log`)
- 告警历史 (`monitoring/alerts_history.json`)

**使用方法**：
```powershell
python monitoring/alerting.py
```

### 4. 专项监控

#### 代码质量监控 (`monitors/code_quality.py`)
- Ruff 代码检查
- Mypy 类型检查
- 代码格式检查

```powershell
python monitoring/monitors/code_quality.py
```

#### 测试覆盖率监控 (`monitors/test_coverage.py`)
- 运行测试并生成覆盖率报告
- 跟踪覆盖率趋势
- 识别低覆盖率文件

```powershell
python monitoring/monitors/test_coverage.py
```

#### 性能监控 (`monitors/performance.py`)
- 检查基准测试结果
- 运行快速性能测试
- 与基线性能比较

```powershell
python monitoring/monitors/performance.py
```

#### 数据完整性监控 (`monitors/data_integrity.py`)
- 检查关键文件和目录
- 验证数据文件格式
- 跟踪文件变化（哈希值）

```powershell
python monitoring/monitors/data_integrity.py
```

### 5. 报告生成 (`report_generator.py`)

**生成内容**：
- Markdown 格式的健康报告
- 覆盖率趋势图表（PNG）
- 问题清单和改进建议

**使用方法**：
```powershell
python monitoring/report_generator.py
```

**输出**：
- `monitoring/reports/health_report_YYYYMMDD_HHMMSS.md`
- `monitoring/reports/health_report_latest.md`
- `monitoring/reports/coverage_trend.png`

## 完整监控流程

### 一键运行所有监控

创建 `run_monitoring.ps1`：
```powershell
# 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 1. 健康检查
Write-Host "=== 运行健康检查 ===" -ForegroundColor Cyan
python monitoring/health_monitor.py

# 2. 收集指标
Write-Host "`n=== 收集指标数据 ===" -ForegroundColor Cyan
python monitoring/metrics_collector.py

# 3. 专项监控（可选）
Write-Host "`n=== 代码质量监控 ===" -ForegroundColor Cyan
python monitoring/monitors/code_quality.py

# 4. 告警分析
Write-Host "`n=== 告警分析 ===" -ForegroundColor Cyan
python monitoring/alerting.py

# 5. 生成报告
Write-Host "`n=== 生成报告 ===" -ForegroundColor Cyan
python monitoring/report_generator.py

Write-Host "`n✅ 监控完成" -ForegroundColor Green
```

使用：
```powershell
.\run_monitoring.ps1
```

## 配置说明

编辑 `monitoring/config.yaml` 自定义监控行为：

```yaml
# 检查阈值
checks:
  - name: "test_coverage"
    threshold: 80          # 覆盖率阈值
    severity: "warning"

  - name: "performance_regression"
    threshold: 10          # 性能退化阈值（%）
    severity: "critical"

# 调度配置
schedule:
  health_check: "daily"
  metrics_collection: "hourly"

# 关键文件和目录
critical_files:
  - "pyproject.toml"
  - "requirements.txt"
  - "pytest.ini"

critical_directories:
  - "common"
  - "tests"
```

## CI/CD 集成

### GitHub Actions

创建 `.github/workflows/monitoring.yml`：

```yaml
name: Health Monitoring

on:
  schedule:
    - cron: '0 0 * * *'  # 每天运行
  workflow_dispatch:      # 手动触发

jobs:
  monitor:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyyaml
      
      - name: Run health check
        run: python monitoring/health_monitor.py
      
      - name: Collect metrics
        run: python monitoring/metrics_collector.py
      
      - name: Generate report
        run: python monitoring/report_generator.py
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: monitoring-report
          path: monitoring/reports/health_report_latest.md
```

### Windows 任务计划

使用任务计划程序定期运行监控：

```powershell
# 创建每日监控任务
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File D:\Dunna\Documents\hw-1\run_monitoring.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 9am

Register-ScheduledTask -TaskName "hw-1-monitoring" `
    -Action $action -Trigger $trigger `
    -Description "hw-1 项目每日健康监控"
```

## 告警阈值说明

| 检查项 | 阈值 | 严重性 |
|--------|------|--------|
| 测试覆盖率 | < 80% | Warning |
| 性能退化 | > 10% | Critical |
| 测试通过率 | < 95% | Critical |
| 代码质量违规 | > 50 | Warning |

## 故障排查

### 常见问题

1. **依赖缺失错误**
   ```powershell
   pip install pyyaml
   ```

2. **权限错误**
   - 确保有写入 `monitoring/` 目录的权限

3. **超时错误**
   - 增加 `pytest` 超时时间
   - 或在配置中禁用慢速测试

4. **图表生成失败**
   - 安装 matplotlib: `pip install matplotlib`

### 查看日志

```powershell
# 查看告警日志
Get-Content monitoring/alerts.log -Tail 20

# 查看最新报告
Get-Content monitoring/reports/health_report_latest.md
```

## 依赖项

监控系统需要以下 Python 包：
```
pyyaml       # 配置文件解析
pytest       # 测试运行
pytest-cov   # 覆盖率
matplotlib   # 图表生成（可选）
```

安装：
```powershell
pip install pyyaml matplotlib
```

## 最佳实践

1. **定期运行**: 建议每天运行一次完整监控
2. **关注趋势**: 不仅看当前值，更要关注变化趋势
3. **及时响应**: Critical 告警应在 24 小时内处理
4. **保留历史**: 定期备份 `metrics_history.json`
5. **调整阈值**: 根据项目实际情况调整配置中的阈值

## 扩展开发

### 添加新的检查项

1. 在 `health_monitor.py` 中添加新方法：
```python
def check_custom_item(self) -> HealthCheck:
    check = HealthCheck("custom_check", "自定义检查")
    # 实现检查逻辑
    check.status = "PASS"
    return check
```

2. 在 `run_all_checks()` 中调用：
```python
self.add_check(self.check_custom_item())
```

### 添加新的告警方式

在 `alerting.py` 的 `add_alert()` 方法中添加：
```python
if "email" in methods:
    self._send_email_alert(alert)
```

## 许可证

本监控系统为 hw-1 项目的一部分。

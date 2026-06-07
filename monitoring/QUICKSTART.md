# hw-1 监控系统快速启动指南

## 快速开始

### 一键运行完整监控

```powershell
# 进入项目目录
cd D:\Dunna\Documents\hw-1

# 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 运行完整监控（推荐）
python monitoring/health_monitor.py
python monitoring/metrics_collector.py
python monitoring/alerting.py
python monitoring/report_generator.py

# 查看报告
notepad monitoring\reports\health_report_latest.md
```

## 单独运行各个组件

### 1. 健康检查
```powershell
python monitoring/health_monitor.py
```
- 检查环境、代码、测试、数据完整性
- 输出：`monitoring/health_report.json`

### 2. 指标收集
```powershell
python monitoring/metrics_collector.py
```
- 收集代码、测试、性能、存储指标
- 输出：`monitoring/metrics_latest.json`, `monitoring/metrics_history.json`

### 3. 代码质量监控
```powershell
python monitoring/monitors/code_quality.py
```
- Ruff 代码检查、Mypy 类型检查、格式检查
- 输出：`monitoring/code_quality_report.json`

### 4. 测试覆盖率监控
```powershell
python monitoring/monitors/test_coverage.py
```
- 运行测试并生成覆盖率报告
- 输出：`monitoring/coverage_report.json`, `monitoring/coverage_history.json`

### 5. 性能监控
```powershell
python monitoring/monitors/performance.py
```
- 检查基准测试结果、运行快速性能测试
- 输出：`monitoring/performance_report.json`

### 6. 数据完整性监控
```powershell
python monitoring/monitors/data_integrity.py
```
- 检查关键文件和数据完整性
- 输出：`monitoring/integrity_report.json`, `monitoring/integrity_snapshot.json`

### 7. 告警分析
```powershell
python monitoring/alerting.py
```
- 分析健康报告和指标，生成告警
- 输出：`monitoring/alerts.log`, `monitoring/alerts_history.json`

### 8. 生成报告
```powershell
python monitoring/report_generator.py
```
- 生成 Markdown 报告和趋势图表
- 输出：`monitoring/reports/health_report_latest.md`, `monitoring/reports/coverage_trend.png`

## 查看结果

### 查看最新报告
```powershell
# Markdown 报告
notepad monitoring\reports\health_report_latest.md

# JSON 数据
notepad monitoring\health_report.json
notepad monitoring\metrics_latest.json

# 告警日志
notepad monitoring\alerts.log

# 查看图表
start monitoring\reports\coverage_trend.png
```

### 查看历史数据
```powershell
# 指标历史
notepad monitoring\metrics_history.json

# 告警历史
notepad monitoring\alerts_history.json

# 覆盖率历史
notepad monitoring\coverage_history.json
```

## 当前项目状态

根据最新监控报告（2026-06-04 12:52:07）：

### ✅ 健康状况
- **健康分数**: 75.0/100
- **状态**: 🟡 需要关注
- **检查项**: 4 项 (3 通过, 0 失败, 1 警告)

### 📊 关键指标
- **代码**: 3,523 行，19 个文件，37 个版本目录
- **测试**: 104 个测试用例，7 个测试文件
- **覆盖率**: 29.91% ⚠️ (目标: ≥80%)
- **存储**: 输出 131 KB，缓存 12.59 MB

### ⚠️ 主要问题
1. **测试覆盖率不足**: 当前 29.91%，建议提高至 80% 以上
2. **测试通过率**: 需要确保测试正常运行

### 🔧 改进建议
- 为 `common/` 目录下的模块增加单元测试
- 运行完整测试套件：`pytest tests/ --cov=common --cov-report=html`
- 查看覆盖率报告：`start htmlcov/index.html`

## 配置文件

编辑 `monitoring/config.yaml` 自定义：
- 检查阈值（覆盖率、性能退化等）
- 告警方式（控制台、日志、邮件）
- 关键文件和目录列表
- 调度频率

## 定时任务

### 每日自动监控（Windows 任务计划）

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File D:\Dunna\Documents\hw-1\monitoring\daily_check.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 9am

Register-ScheduledTask -TaskName "hw-1-daily-monitoring" `
    -Action $action -Trigger $trigger `
    -Description "hw-1 项目每日健康监控"
```

## 故障排查

### 常见问题

1. **ModuleNotFoundError: No module named 'yaml'**
   ```powershell
   pip install pyyaml
   ```

2. **UnicodeEncodeError**
   - 已修复控制台输出的 emoji 问题
   - 使用文本符号替代 emoji

3. **测试超时**
   - 默认超时 5 分钟，可在代码中调整 `timeout` 参数

4. **图表中文显示问题**
   - matplotlib 中文字体警告，不影响功能
   - 图表已正常生成为 PNG 文件

## 下一步行动

1. **提高测试覆盖率** - 当前首要任务
   ```powershell
   # 查看未覆盖的代码
   pytest tests/ --cov=common --cov-report=html
   start htmlcov/index.html
   ```

2. **修复代码质量问题**
   ```powershell
   # 自动修复部分问题
   ruff check common --fix
   
   # 格式化代码
   ruff format common
   ```

3. **建立基线性能数据**
   - 运行基准测试并记录结果
   - 更新 `config.yaml` 中的 `baseline_performance`

4. **集成到 CI/CD**
   - 在 `.github/workflows/` 中添加监控工作流
   - 每次提交时运行健康检查

## 文件说明

| 文件 | 说明 |
|------|------|
| `health_monitor.py` | 主健康检查器 |
| `metrics_collector.py` | 指标收集器 |
| `alerting.py` | 告警系统 |
| `report_generator.py` | 报告生成器 |
| `config.yaml` | 监控配置 |
| `monitors/code_quality.py` | 代码质量监控 |
| `monitors/test_coverage.py` | 覆盖率监控 |
| `monitors/performance.py` | 性能监控 |
| `monitors/data_integrity.py` | 数据完整性监控 |

## 联系方式

如有问题，请查看：
- 详细文档：`monitoring/README.md`
- 配置示例：`monitoring/config.yaml`
- 告警日志：`monitoring/alerts.log`

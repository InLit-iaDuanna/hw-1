# hw-1 项目文档

生成时间: 2026-06-04 12:39:57

## 可用文档
- [测试覆盖率报告](../htmlcov/index.html)
- [性能基准报告](../benchmarks/results/benchmark_report.txt)
- [性能演化图表](../benchmarks/results/performance_evolution.png)

## 项目文档

- [README](../README.md) — 项目概述
- [VERSIONS](../VERSIONS.md) — 版本历史
- [ROADMAP](../ROADMAP.md) — 开发路线图
- [CLAUDE](../CLAUDE.md) — 开发指南
- [PROJECT_PROGRESS](../PROJECT_PROGRESS.md) — 进度跟踪

## 测试与质量

运行测试: `.\ci\run_tests.ps1 -Coverage`
质量检查: `.\ci\run_quality.ps1`
性能基准: `.\ci\run_benchmarks.ps1 -Compare -GenerateReport`

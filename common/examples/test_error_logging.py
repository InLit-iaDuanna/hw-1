"""测试错误处理和日志系统模块。

运行此脚本以验证所有模块是否正常导入和工作。
"""

import sys
from pathlib import Path

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# 设置控制台编码
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def test_imports():
    """测试模块导入。"""
    print("Testing imports...")

    try:
        # 测试异常模块
        from common.exceptions import (
            DataValidationError,
            HW1Error,
            ModelLoadError,
            SimulationFailureError,
            wrap_exception,
        )

        print("[OK] exceptions module imported successfully")

        # 测试日志模块
        from common.logging_config import (
            LogContext,
            get_logger,
            log_execution_time,
            setup_logging,
        )

        print("[OK] logging_config module imported successfully")

        # 测试错误处理模块
        from common.error_handler import (
            ErrorContext,
            handle_errors,
            retry_on_failure,
            safe_execute,
        )

        print("[OK] error_handler module imported successfully")

        # 测试监控模块
        from common.monitoring import (
            AlertManager,
            PerformanceTracker,
            SimulationMonitor,
            SystemMonitor,
        )

        print("[OK] monitoring module imported successfully")

        return True

    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        return False


def test_exceptions():
    """测试异常类。"""
    print("\nTesting exception classes...")

    from common.exceptions import (
        SimulationFailureError,
        wrap_exception,
    )

    try:
        # 测试自定义异常
        error = SimulationFailureError(
            "Test failure",
            failure_type="test",
            time=1.5,
            state={"x": 1.0, "y": 2.0},
        )

        assert error.message == "Test failure"
        assert error.context["failure_type"] == "test"
        assert error.context["time"] == 1.5

        # 测试转换为字典
        error_dict = error.to_dict()
        assert error_dict["type"] == "SimulationFailureError"
        assert error_dict["message"] == "Test failure"

        # 测试包装异常
        try:
            raise ValueError("Original error")
        except ValueError as e:
            wrapped = wrap_exception(e, "Wrapped error", {"key": "value"})
            assert wrapped.message == "Wrapped error"
            assert wrapped.context["key"] == "value"
            assert wrapped.original_exception is e

        print("[OK] Exception classes work correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Exception test failed: {e}")
        return False


def test_logging():
    """测试日志系统。"""
    print("\nTesting logging system...")

    import time

    from common.logging_config import (
        LogContext,
        get_logger,
        log_execution_time,
        setup_logging,
    )

    try:
        # 设置日志
        setup_logging(
            level="INFO",
            log_dir="out/logs/test",
            log_file_prefix="test",
            enable_console=False,  # 不输出到控制台，避免干扰
            enable_file=True,
        )

        # 获取 logger
        logger = get_logger("test_module")

        # 测试日志记录
        logger.info("Test info message")
        logger.warning("Test warning message")

        # 测试上下文
        with LogContext(test="context", value=42):
            logger.info("Message with context")

        # 测试计时装饰器
        @log_execution_time(logger=logger, level="INFO")
        def slow_function():
            time.sleep(0.1)
            return "done"

        result = slow_function()
        assert result == "done"

        print("[OK] Logging system works correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Logging test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_error_handler():
    """测试错误处理装饰器。"""
    print("\nTesting error handler...")

    from common.error_handler import (
        ErrorContext,
        FallbackStrategy,
        handle_errors,
        retry_on_failure,
        safe_execute,
        safe_execute_with_recovery,
    )
    from common.exceptions import SimulationError

    try:
        # 测试 handle_errors 装饰器
        @handle_errors(error_types=(ValueError,), default_return=None)
        def may_fail(should_fail=False):
            if should_fail:
                raise ValueError("Intentional error")
            return "success"

        assert may_fail(should_fail=False) == "success"
        assert may_fail(should_fail=True) is None

        # 测试 retry_on_failure
        call_count = [0]

        @retry_on_failure(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Retry me")
            return "finally succeeded"

        result = flaky_function()
        assert result == "finally succeeded"
        assert call_count[0] == 2

        # 测试 safe_execute
        def risky_func():
            raise RuntimeError("Error!")

        success, result, error = safe_execute(
            risky_func,
            default="fallback",
            log_errors=False,
        )

        assert not success
        assert result == "fallback"
        assert isinstance(error, RuntimeError)

        # 测试 ErrorContext
        try:
            with ErrorContext(SimulationError, "Test context"):
                raise ValueError("Original")
        except SimulationError as e:
            assert "Test context" in str(e)
            assert isinstance(e.original_exception, ValueError)

        # 测试恢复策略
        strategy = FallbackStrategy(fallback_value=42)

        def failing_func():
            raise ValueError("Always fails")

        result = safe_execute_with_recovery(failing_func, strategy)
        assert result == 42

        print("[OK] Error handler works correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Error handler test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_monitoring():
    """测试监控系统。"""
    print("\nTesting monitoring system...")

    import time

    from common.monitoring import (
        AlertManager,
        PerformanceTracker,
        SimulationMonitor,
        SystemMonitor,
    )

    try:
        # 测试系统监控
        sys_monitor = SystemMonitor(
            memory_threshold_percent=100.0,  # 设置高阈值，避免触发告警
        )
        sys_monitor.start()

        # 模拟一些工作
        time.sleep(0.2)
        sys_monitor.check()

        sys_monitor.stop()
        report = sys_monitor.get_report()

        # 检查报告（可能 psutil 不可用）
        if report.get("status") == "psutil_not_available":
            print("  Note: psutil not installed, skipping system monitoring tests")
        else:
            assert "cpu" in report
            assert "memory_mb" in report
            assert report["snapshots_count"] >= 1

        # 测试仿真监控
        sim_monitor = SimulationMonitor()
        sim_monitor.start()

        for step in range(100):
            time.sleep(0.001)
            if step % 10 == 0:
                sim_monitor.update(
                    simulated_time=step * 0.01,
                    step_count=step,
                )

        sim_monitor.stop()
        sim_report = sim_monitor.get_report()

        assert sim_report["total_steps"] > 0
        assert sim_report["metrics_count"] > 0

        # 测试性能追踪
        tracker = PerformanceTracker()

        for _ in range(10):
            with tracker.track("operation_a"):
                time.sleep(0.01)

            with tracker.track("operation_b"):
                time.sleep(0.005)

        perf_report = tracker.get_report()

        assert "operation_a" in perf_report
        assert "operation_b" in perf_report
        assert perf_report["operation_a"]["count"] == 10

        # 测试告警管理器
        alert_mgr = AlertManager()

        sys_mon_with_alerts = SystemMonitor(
            memory_threshold_percent=0.1,  # 低阈值，触发告警
            alert_callback=alert_mgr.handle_alert,
        )

        sys_mon_with_alerts.start()
        sys_mon_with_alerts.check()  # 应该触发告警
        sys_mon_with_alerts.stop()

        # 可能有告警（取决于当前内存使用）
        if len(alert_mgr.alerts) > 0:
            print(f"  Generated {len(alert_mgr.alerts)} alert(s) as expected")

        print("[OK] Monitoring system works correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Monitoring test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """运行所有测试。"""
    print("=" * 60)
    print("HW-1 Error Handling and Logging System Test")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Exceptions", test_exceptions),
        ("Logging", test_logging),
        ("Error Handler", test_error_handler),
        ("Monitoring", test_monitoring),
    ]

    results = []

    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[CRASH] Test '{name}' crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 打印总结
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

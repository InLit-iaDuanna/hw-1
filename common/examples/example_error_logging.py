"""示例：使用统一的错误处理和日志系统。

本示例演示如何在仿真脚本中集成：
1. 日志系统配置
2. 自定义异常处理
3. 错误恢复策略
4. 系统监控和告警
"""

import time
from pathlib import Path

import mujoco
import numpy as np

# 导入错误处理和日志模块
from common import (
    AlertManager,
    ErrorContext,
    LogContext,
    # 异常
    ModelLoadError,
    PerformanceTracker,
    SimulationFailureError,
    SimulationMonitor,
    SimulationNaNError,
    # 监控
    SystemMonitor,
    get_logger,
    # 错误处理
    handle_errors,
    log_simulation_end,
    log_simulation_start,
    retry_on_failure,
    safe_execute,
    # 日志
    setup_logging,
)

# ============================================================================
# 配置
# ============================================================================

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"

# 设置日志系统（只需调用一次）
setup_logging(
    level="INFO",
    log_dir=OUT_DIR / "logs",
    log_file_prefix="example_error_logging",
    enable_console=True,
    enable_file=True,
    enable_json=False,  # 设为 True 可输出 JSON 格式日志
    console_colors=True,
)

logger = get_logger(__name__)


# ============================================================================
# 带错误处理的模型加载
# ============================================================================


@handle_errors(
    error_types=(OSError, ValueError),
    raise_as=ModelLoadError,
    log_level="ERROR",
)
def load_model(xml_path: Path) -> mujoco.MjModel:
    """加载 MuJoCo 模型（带统一错误处理）。

    如果加载失败，会自动记录日志并转换为 ModelLoadError。
    """
    logger.info(f"Loading model from {xml_path}")

    if not xml_path.exists():
        raise FileNotFoundError(f"Model file not found: {xml_path}")

    model = mujoco.MjModel.from_xml_path(str(xml_path))
    logger.info(f"Model loaded: {model.nq} DOFs, {model.nu} actuators")

    return model


@retry_on_failure(
    max_attempts=3,
    delay=0.5,
    backoff=2.0,
    exceptions=(OSError, TimeoutError),
)
def save_results(data: dict, output_path: Path):
    """保存结果（带自动重试）。

    如果保存失败（如磁盘满、网络中断），会自动重试。
    """
    logger.info(f"Saving results to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import json

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Results saved successfully")


# ============================================================================
# 仿真函数（带监控和错误处理）
# ============================================================================


def run_simulation_with_monitoring(
    model: mujoco.MjModel,
    duration: float = 5.0,
    timestep: float = 0.001,
) -> dict:
    """运行仿真（集成监控和错误处理）。

    Args:
        model: MuJoCo 模型
        duration: 仿真时长（秒）
        timestep: 时间步长（秒）

    Returns:
        仿真结果字典

    Raises:
        SimulationFailureError: 仿真失败
        SimulationNaNError: 出现 NaN 值
    """
    # 创建监控系统
    alert_mgr = AlertManager()
    sys_monitor = SystemMonitor(
        memory_threshold_percent=80.0,
        alert_callback=alert_mgr.handle_alert,
    )
    sim_monitor = SimulationMonitor(
        min_steps_per_second=100.0,
        alert_callback=alert_mgr.handle_alert,
    )
    perf_tracker = PerformanceTracker()

    # 启动监控
    sys_monitor.start()
    sim_monitor.start()

    # 初始化仿真
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    n_steps = int(duration / timestep)
    success = False
    failure_reason = None

    logger.info(f"Starting simulation: {n_steps} steps, {duration}s")

    try:
        # 使用 ErrorContext 自动捕获和转换异常
        with ErrorContext(SimulationFailureError, "Simulation loop failed"):
            for step in range(n_steps):
                t = step * timestep

                # 性能追踪：前向动力学
                with perf_tracker.track("forward"):
                    mujoco.mj_forward(model, data)

                # 性能追踪：积分
                with perf_tracker.track("step"):
                    mujoco.mj_step(model, data)

                # 周期性检查
                if step % 100 == 0:
                    # 检查系统资源
                    sys_monitor.check()

                    # 更新仿真监控
                    sim_monitor.update(
                        simulated_time=t,
                        step_count=step,
                        custom_metrics={
                            "energy": float(data.energy[0] + data.energy[1]),
                        },
                    )

                    # 检查 NaN
                    if not np.all(np.isfinite(data.qpos)):
                        raise SimulationNaNError(
                            "NaN detected in joint positions",
                            time=t,
                            step=step,
                            nan_variables=["qpos"],
                        )

                # 周期性日志（不要太频繁）
                if step % 1000 == 0 and step > 0:
                    logger.debug(
                        f"Step {step}/{n_steps} ({step/n_steps*100:.1f}%)",
                        extra={"time": t, "step": step},
                    )

        success = True
        logger.info("Simulation completed successfully")

    except SimulationNaNError as e:
        failure_reason = "nan_detected"
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise

    except SimulationFailureError as e:
        failure_reason = "simulation_failure"
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise

    finally:
        # 停止监控
        sys_monitor.stop()
        sim_monitor.stop()

        # 生成报告
        sys_report = sys_monitor.get_report()
        sim_report = sim_monitor.get_report()
        perf_report = perf_tracker.get_report()

        # 记录监控结果
        logger.info("=== Monitoring Report ===")
        logger.info(
            f"CPU: mean={sys_report['cpu']['mean']:.1f}%, "
            f"max={sys_report['cpu']['max']:.1f}%"
        )
        logger.info(
            f"Memory: mean={sys_report['memory_mb']['mean']:.1f} MB, "
            f"max={sys_report['memory_mb']['max']:.1f} MB"
        )
        logger.info(
            f"Simulation speed: "
            f"{sim_report['steps_per_second']['mean']:.0f} steps/s"
        )

        # 记录性能
        for operation, stats in perf_report.items():
            logger.info(
                f"Performance [{operation}]: "
                f"mean={stats['mean']*1000:.2f}ms, "
                f"total={stats['total']:.2f}s"
            )

        # 打印告警摘要
        alert_mgr.print_summary()

    return {
        "success": success,
        "failure_reason": failure_reason,
        "system_report": sys_report,
        "simulation_report": sim_report,
        "performance_report": perf_report,
    }


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数：演示完整的错误处理和日志流程。"""

    # 使用 LogContext 自动附加元数据
    with LogContext(example="error_logging_demo", version="v20"):
        logger.info("=== Error Handling and Logging Demo ===")

        # 1. 加载模型（带错误处理）
        model_path = ROOT / "example_model.xml"

        # 创建简单的示例模型
        xml_content = """
        <mujoco>
            <worldbody>
                <body name="cart" pos="0 0 0.5">
                    <joint name="slider" type="slide" axis="1 0 0"/>
                    <geom type="box" size="0.2 0.1 0.1" mass="1"/>
                </body>
            </worldbody>
            <actuator>
                <motor joint="slider" gear="10"/>
            </actuator>
        </mujoco>
        """

        model_path.parent.mkdir(exist_ok=True)
        model_path.write_text(xml_content)

        try:
            model = load_model(model_path)
        except ModelLoadError as e:
            logger.critical(f"Failed to load model: {e}")
            return

        # 2. 运行仿真（带监控）
        params = {
            "duration": 5.0,
            "timestep": 0.001,
        }

        log_simulation_start(logger, "demo", params)

        start_time = time.time()

        try:
            result = run_simulation_with_monitoring(
                model,
                duration=params["duration"],
                timestep=params["timestep"],
            )

            elapsed = time.time() - start_time

            log_simulation_end(
                logger,
                "demo",
                success=result["success"],
                duration=elapsed,
                metrics={
                    "avg_speed": result["simulation_report"]["steps_per_second"][
                        "mean"
                    ],
                },
            )

            # 3. 保存结果（带重试）
            output_path = OUT_DIR / "example_results.json"
            save_results(result, output_path)

        except Exception:
            elapsed = time.time() - start_time
            logger.error(f"Simulation failed after {elapsed:.2f}s", exc_info=True)

            log_simulation_end(
                logger,
                "demo",
                success=False,
                duration=elapsed,
            )

        # 4. 演示安全执行
        logger.info("=== Demonstrating safe_execute ===")

        def risky_operation():
            # 50% 概率失败
            if np.random.random() < 0.5:
                raise ValueError("Random failure!")
            return "Success!"

        success, result, error = safe_execute(
            risky_operation,
            default="Fallback value",
            log_errors=True,
        )

        if success:
            logger.info(f"Operation succeeded: {result}")
        else:
            logger.warning(f"Operation failed, using fallback: {error}")

        logger.info("=== Demo completed ===")


if __name__ == "__main__":
    main()

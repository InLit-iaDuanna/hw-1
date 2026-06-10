"""跨版本公共库。从 V11 起逐步填充，避免每版重写工具脚本。"""

from .control_utils import limited_pd
from .failure_classifier import FailureMode, classify_failure
from .ik_utils import leg_ik_front_knee, ramp_height, smoothstep
from .rolling_foot_gait import RollingFootGait, RollingFootParams
from .energy_metrics import (
    collision_loss_per_step,
    cost_of_transport,
    mechanical_energy_series,
)
from .ik_solvers import (
    compute_foot_position_from_joints,
    solve_2d_leg_ik,
    solve_3d_leg_ik,
)
from .motor_dynamics import (
    PRESETS as MOTOR_PRESETS,
)
from .motor_dynamics import (
    L1MotorActuator,
    MotorParams,
    joint_armature_with_motor,
    joint_damping_with_motor,
)
from .mujoco_utils import get_contact_flags, get_joint_address
from .plot_styles import PALETTE, set_style
from .poincare import collect_section, floquet_multipliers, plot_section
from .phase_portrait_visualizer import (
    PhasePortraitVisualizer,
    StateVariable,
    TrajectoryAnnotation,
    quick_phase_portrait,
)
from .simulation_framework import (
    ContactState,
    Controller,
    DictRowRecorder,
    EnergyStats,
    FailureClassifier,
    IntegratedSimulationCallback,
    PhaseTracker,
    update_contact_state,
)
from .simulation_runner import (
    Callback,
    ControllerCallback,
    DataRecorder,
    EarlyStopCondition,
    HeightThreshold,
    NaNDetector,
    PenetrationDetector,
    SimulationResult,
    SimulationRunner,
)

# 错误处理和日志系统（V20+）
from .exceptions import (
    HW1Error,
    ModelError,
    ModelLoadError,
    ModelValidationError,
    SimulationError,
    SimulationFailureError,
    SimulationTimeoutError,
    SimulationNaNError,
    DataError,
    DataValidationError,
    DataIOError,
    ControlError,
    ControlLimitError,
    ControlStabilityError,
    wrap_exception,
)
from .logging_config import (
    setup_logging,
    get_logger,
    get_context_logger,
    log_execution_time,
    log_exception,
    log_simulation_start,
    log_simulation_end,
    LogContext,
)
from .error_handler import (
    handle_errors,
    retry_on_failure,
    safe_execute,
    safe_execute_with_recovery,
    ErrorContext,
    ErrorRecoveryStrategy,
    FallbackStrategy,
    RetryStrategy,
    classify_exception,
    get_recovery_suggestion,
)
from .monitoring import (
    SystemMonitor,
    SimulationMonitor,
    PerformanceTracker,
    AlertManager,
    Alert,
    ResourceSnapshot,
    SimulationMetrics,
)

__all__ = [
    "set_style",
    "PALETTE",
    "cost_of_transport",
    "mechanical_energy_series",
    "collision_loss_per_step",
    "collect_section",
    "plot_section",
    "floquet_multipliers",
    # phase_portrait_visualizer
    "PhasePortraitVisualizer",
    "StateVariable",
    "TrajectoryAnnotation",
    "quick_phase_portrait",
    "MotorParams",
    "MOTOR_PRESETS",
    "L1MotorActuator",
    "joint_armature_with_motor",
    "joint_damping_with_motor",
    "smoothstep",
    "limited_pd",
    "ramp_height",
    "leg_ik_front_knee",
    "FailureMode",
    "classify_failure",
    "get_joint_address",
    "get_contact_flags",
    "solve_2d_leg_ik",
    "solve_3d_leg_ik",
    "compute_foot_position_from_joints",
    # rolling_foot_gait
    "RollingFootGait",
    "RollingFootParams",
    # simulation_runner
    "SimulationRunner",
    "SimulationResult",
    "Callback",
    "EarlyStopCondition",
    "DataRecorder",
    "ControllerCallback",
    "NaNDetector",
    "HeightThreshold",
    "PenetrationDetector",
    # simulation_framework
    "Controller",
    "ContactState",
    "update_contact_state",
    "EnergyStats",
    "PhaseTracker",
    "DictRowRecorder",
    "IntegratedSimulationCallback",
    "FailureClassifier",
    # exceptions
    "HW1Error",
    "ModelError",
    "ModelLoadError",
    "ModelValidationError",
    "SimulationError",
    "SimulationFailureError",
    "SimulationTimeoutError",
    "SimulationNaNError",
    "DataError",
    "DataValidationError",
    "DataIOError",
    "ControlError",
    "ControlLimitError",
    "ControlStabilityError",
    "wrap_exception",
    # logging_config
    "setup_logging",
    "get_logger",
    "get_context_logger",
    "log_execution_time",
    "log_exception",
    "log_simulation_start",
    "log_simulation_end",
    "LogContext",
    # error_handler
    "handle_errors",
    "retry_on_failure",
    "safe_execute",
    "safe_execute_with_recovery",
    "ErrorContext",
    "ErrorRecoveryStrategy",
    "FallbackStrategy",
    "RetryStrategy",
    "classify_exception",
    "get_recovery_suggestion",
    # monitoring
    "SystemMonitor",
    "SimulationMonitor",
    "PerformanceTracker",
    "AlertManager",
    "Alert",
    "ResourceSnapshot",
    "SimulationMetrics",
]

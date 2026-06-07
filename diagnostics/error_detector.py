"""错误检测和分类模块。

分析仿真输出、日志文件和数据，自动检测并分类常见错误。
"""

import re
from pathlib import Path
from typing import Any
import json
import numpy as np


class ErrorSignature:
    """错误特征签名。"""

    def __init__(
        self,
        error_type: str,
        patterns: list[str],
        data_checks: list[tuple[str, Any]] | None = None,
        severity: str = "medium"
    ):
        self.error_type = error_type
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.data_checks = data_checks or []
        self.severity = severity

    def match_log(self, log_text: str) -> bool:
        """检查日志文本是否匹配此错误。"""
        return any(pattern.search(log_text) for pattern in self.patterns)

    def match_data(self, data: dict[str, Any]) -> bool:
        """检查数据字典是否匹配此错误。"""
        for key, expected_value in self.data_checks:
            if key not in data:
                continue
            actual = data[key]

            # 处理不同类型的检查
            if callable(expected_value):
                if expected_value(actual):
                    return True
            elif actual == expected_value:
                return True

        return False


# 预定义错误签名
ERROR_SIGNATURES = [
    ErrorSignature(
        "simulation_nan",
        patterns=[
            r"NaN.*joint",
            r"qpos.*NaN",
            r"qvel.*NaN",
            r"integration error",
            r"contains NaN"
        ],
        data_checks=[
            ("has_nan", True),
            ("failure", "nan_or_unstable")
        ],
        severity="critical"
    ),
    ErrorSignature(
        "fall_down",
        patterns=[
            r"fall[_\s]?down",
            r"hip.*height.*low",
            r"trunk.*pitch.*exceed"
        ],
        data_checks=[
            ("failure", "fall_down"),
            ("hip_height", lambda x: x < 0.5 if isinstance(x, (int, float)) else False)
        ],
        severity="high"
    ),
    ErrorSignature(
        "fly_away",
        patterns=[
            r"fly[_\s]?away",
            r"hip.*height.*exceed",
            r"explosive.*contact"
        ],
        data_checks=[
            ("failure", "fly_away"),
            ("hip_height", lambda x: x > 3.0 if isinstance(x, (int, float)) else False)
        ],
        severity="critical"
    ),
    ErrorSignature(
        "penetration",
        patterns=[
            r"penetration",
            r"excessive.*contact.*force",
            r"geom.*overlap"
        ],
        data_checks=[
            ("failure", "penetration")
        ],
        severity="medium"
    ),
    ErrorSignature(
        "no_alternation",
        patterns=[
            r"insufficient.*alternation",
            r"stuck.*stance",
            r"no.*gait.*cycle"
        ],
        data_checks=[
            ("alternation_count", lambda x: x <= 1 if isinstance(x, int) else False),
            ("failure", "insufficient_alternations")
        ],
        severity="high"
    ),
    ErrorSignature(
        "mujoco_not_found",
        patterns=[
            r"ModuleNotFoundError.*mujoco",
            r"No module named.*mujoco",
            r"import mujoco.*fail"
        ],
        severity="critical"
    ),
    ErrorSignature(
        "model_file_not_found",
        patterns=[
            r"FileNotFoundError.*xml",
            r"model.*not found",
            r"path.*does not exist"
        ],
        severity="high"
    ),
    ErrorSignature(
        "common_import_error",
        patterns=[
            r"ModuleNotFoundError.*common",
            r"No module named.*common"
        ],
        severity="medium"
    ),
    ErrorSignature(
        "invalid_timestep",
        patterns=[
            r"invalid.*timestep",
            r"timestep.*out of range"
        ],
        data_checks=[
            ("dt", lambda x: x <= 0 or x > 0.01 if isinstance(x, (int, float)) else False)
        ],
        severity="critical"
    ),
]


class ErrorDetector:
    """错误检测器。"""

    def __init__(self, signatures: list[ErrorSignature] | None = None):
        self.signatures = signatures or ERROR_SIGNATURES

    def detect_from_log(self, log_path: Path | str) -> list[tuple[str, str]]:
        """从日志文件检测错误。

        Returns:
            [(error_type, severity), ...] 列表
        """
        log_path = Path(log_path)
        if not log_path.exists():
            return [("log_file_not_found", "high")]

        try:
            log_text = log_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return [("log_read_error", "medium")]

        detected = []
        for sig in self.signatures:
            if sig.match_log(log_text):
                detected.append((sig.error_type, sig.severity))

        return detected

    def detect_from_data(self, data: dict[str, Any]) -> list[tuple[str, str]]:
        """从数据字典检测错误。

        Returns:
            [(error_type, severity), ...] 列表
        """
        detected = []
        for sig in self.signatures:
            if sig.match_data(data):
                detected.append((sig.error_type, sig.severity))

        return detected

    def detect_from_json(self, json_path: Path | str) -> list[tuple[str, str]]:
        """从 JSON 文件检测错误。"""
        json_path = Path(json_path)
        if not json_path.exists():
            return [("data_file_not_found", "high")]

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return [("json_corrupted", "medium")]
        except Exception:
            return [("data_read_error", "medium")]

        return self.detect_from_data(data)

    def detect_from_timeseries(
        self,
        qpos: np.ndarray | None = None,
        qvel: np.ndarray | None = None,
        ctrl: np.ndarray | None = None
    ) -> list[tuple[str, str]]:
        """从时间序列数据检测错误。"""
        detected = []

        # 检查 NaN
        if qpos is not None and np.any(np.isnan(qpos)):
            detected.append(("simulation_nan", "critical"))
        if qvel is not None and np.any(np.isnan(qvel)):
            detected.append(("simulation_nan", "critical"))
        if ctrl is not None and np.any(np.isnan(ctrl)):
            detected.append(("control_nan", "critical"))

        # 检查 Inf
        if qpos is not None and np.any(np.isinf(qpos)):
            detected.append(("simulation_diverge", "critical"))
        if qvel is not None and np.any(np.isinf(qvel)):
            detected.append(("simulation_diverge", "critical"))

        # 检查异常大的值
        if qpos is not None and np.any(np.abs(qpos) > 1000):
            detected.append(("fly_away", "critical"))
        if qvel is not None and np.any(np.abs(qvel) > 100):
            detected.append(("excessive_velocity", "high"))

        return detected

    def analyze_simulation_result(
        self,
        result: dict[str, Any],
        timeseries_path: Path | str | None = None
    ) -> dict[str, Any]:
        """综合分析仿真结果。

        Args:
            result: 仿真结果字典 (包含 success, failure, forward, alternation_count 等)
            timeseries_path: 可选的时间序列数据 CSV 路径

        Returns:
            分析报告字典
        """
        errors = []

        # 从结果数据检测
        errors.extend(self.detect_from_data(result))

        # 如果提供了时间序列，加载并检测
        if timeseries_path:
            ts_path = Path(timeseries_path)
            if ts_path.exists() and ts_path.suffix == ".csv":
                try:
                    import pandas as pd
                    df = pd.read_csv(ts_path)

                    # 检测时间序列错误
                    if "qpos_hip_x" in df.columns:
                        qpos_sample = df["qpos_hip_x"].values
                        errors.extend(self.detect_from_timeseries(qpos=qpos_sample))
                except Exception:
                    errors.append(("timeseries_read_error", "low"))

        # 去重并按严重性排序
        unique_errors = list(set(errors))
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique_errors.sort(key=lambda x: severity_order.get(x[1], 4))

        report = {
            "has_errors": len(unique_errors) > 0,
            "error_count": len(unique_errors),
            "errors": [
                {"type": err_type, "severity": sev}
                for err_type, sev in unique_errors
            ],
            "primary_error": unique_errors[0][0] if unique_errors else None,
            "severity": unique_errors[0][1] if unique_errors else "none"
        }

        return report


def detect_errors_in_directory(directory: Path | str, pattern: str = "*.json") -> dict[str, Any]:
    """批量检测目录中所有匹配文件的错误。

    Args:
        directory: 目录路径
        pattern: 文件匹配模式

    Returns:
        {file_name: error_report, ...} 字典
    """
    directory = Path(directory)
    detector = ErrorDetector()

    results = {}
    for file_path in directory.glob(pattern):
        try:
            report = detector.detect_from_json(file_path)
            if report:
                results[file_path.name] = {
                    "errors": [{"type": t, "severity": s} for t, s in report],
                    "error_count": len(report)
                }
        except Exception as e:
            results[file_path.name] = {"error": str(e)}

    return results


if __name__ == "__main__":
    # 测试示例
    detector = ErrorDetector()

    # 测试数据检测
    test_data = {
        "success": False,
        "failure": "fall_down",
        "hip_height": 0.3,
        "forward": 0.5,
        "alternation_count": 2
    }

    errors = detector.detect_from_data(test_data)
    print(f"检测到 {len(errors)} 个错误:")
    for error_type, severity in errors:
        print(f"  - {error_type} (严重性: {severity})")

    # 测试时间序列检测
    qpos_with_nan = np.array([0.0, 0.5, 1.0, np.nan, 0.8])
    errors = detector.detect_from_timeseries(qpos=qpos_with_nan)
    print(f"\n时间序列检测到 {len(errors)} 个错误:")
    for error_type, severity in errors:
        print(f"  - {error_type} (严重性: {severity})")

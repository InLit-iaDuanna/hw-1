"""诊断系统包初始化文件。"""

from .diagnostic_wizard import DiagnosticWizard
from .error_detector import ErrorDetector, ErrorSignature, detect_errors_in_directory
from .health_checker import HealthChecker
from .solution_database import ErrorEntry, Solution, SolutionDatabase

__version__ = "1.0.0"

__all__ = [
    "ErrorDetector",
    "ErrorSignature",
    "detect_errors_in_directory",
    "SolutionDatabase",
    "ErrorEntry",
    "Solution",
    "DiagnosticWizard",
    "HealthChecker",
]

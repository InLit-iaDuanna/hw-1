"""诊断系统包初始化文件。"""

from .error_detector import ErrorDetector, ErrorSignature, detect_errors_in_directory
from .solution_database import SolutionDatabase, ErrorEntry, Solution
from .diagnostic_wizard import DiagnosticWizard
from .health_checker import HealthChecker

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

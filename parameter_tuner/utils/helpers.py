"""工具函数模块"""

from datetime import datetime
from pathlib import Path

import yaml


def save_config(params, version_key: str, filename: str = None):
    """保存参数配置到文件"""
    from dataclasses import asdict

    cache_dir = Path(__file__).resolve().parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{version_key}_config_{timestamp}.yaml"

    filepath = cache_dir / filename

    params_dict = asdict(params)

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(params_dict, f, default_flow_style=False, allow_unicode=True)

    return filepath


def load_config(filepath: Path):
    """从文件加载参数配置"""
    with open(filepath, encoding="utf-8") as f:
        params_dict = yaml.safe_load(f)

    return params_dict


def format_duration(seconds: float) -> str:
    """格式化时长显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def classify_failure_reason(reason: str) -> str:
    """分类失败原因"""
    reason_lower = reason.lower()

    if "fall" in reason_lower or "tip" in reason_lower:
        return "跌倒"
    elif "forward" in reason_lower or "distance" in reason_lower:
        return "前进不足"
    elif "time" in reason_lower or "duration" in reason_lower:
        return "时长不足"
    elif "touchdown" in reason_lower or "contact" in reason_lower:
        return "触地异常"
    elif "knee" in reason_lower:
        return "膝关节异常"
    else:
        return "其他"

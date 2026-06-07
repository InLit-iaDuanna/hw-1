"""跨版本基准场景占位。V11 仅声明数据类，实际场景库由 V12 填充。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkScenario:
    name: str
    description: str
    duration_s: float


BENCHMARKS = {
    "flat_100_steps": BenchmarkScenario("flat_100_steps", "平地 100 步直线", 60.0),
    "single_impulse": BenchmarkScenario("single_impulse", "5 s 处单脉冲扰动", 12.0),
    "stairs_5deg": BenchmarkScenario("stairs_5deg", "5° 阶梯地形", 15.0),
}

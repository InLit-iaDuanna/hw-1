"""benchmark.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from benchmark import BENCHMARKS, BenchmarkScenario


class TestBenchmarkScenario:
    """测试基准场景数据类。"""

    def test_scenario_creation(self):
        """测试场景创建。"""
        scenario = BenchmarkScenario(
            name="test_scenario", description="测试场景", duration_s=10.0
        )
        assert scenario.name == "test_scenario"
        assert scenario.description == "测试场景"
        assert scenario.duration_s == 10.0

    def test_scenario_frozen(self):
        """场景应为不可变（frozen=True）。"""
        scenario = BenchmarkScenario("test", "desc", 5.0)
        with pytest.raises(AttributeError):
            scenario.name = "new_name"


class TestBenchmarksRegistry:
    """测试预定义基准场景注册表。"""

    def test_benchmarks_is_dict(self):
        """BENCHMARKS 应为字典。"""
        assert isinstance(BENCHMARKS, dict)

    def test_benchmarks_nonempty(self):
        """应至少包含一些预定义场景。"""
        assert len(BENCHMARKS) > 0

    def test_required_benchmarks_exist(self):
        """验证必需的基准场景存在。"""
        required = ["flat_100_steps", "single_impulse", "stairs_5deg"]
        for name in required:
            assert name in BENCHMARKS, f"缺少必需基准场景: {name}"

    def test_all_values_are_scenarios(self):
        """所有注册值应为 BenchmarkScenario 实例。"""
        for key, value in BENCHMARKS.items():
            assert isinstance(
                value, BenchmarkScenario
            ), f"{key} 不是 BenchmarkScenario 实例"

    def test_scenario_names_match_keys(self):
        """场景的 name 属性应与字典键一致。"""
        for key, scenario in BENCHMARKS.items():
            assert scenario.name == key, f"键 {key} 与场景名称 {scenario.name} 不匹配"


class TestSpecificBenchmarks:
    """测试特定基准场景的属性。"""

    def test_flat_100_steps(self):
        """验证 flat_100_steps 场景配置。"""
        scenario = BENCHMARKS["flat_100_steps"]
        assert scenario.name == "flat_100_steps"
        assert "平地" in scenario.description or "100" in scenario.description
        assert scenario.duration_s > 0

    def test_single_impulse(self):
        """验证 single_impulse 场景配置。"""
        scenario = BENCHMARKS["single_impulse"]
        assert scenario.name == "single_impulse"
        assert "脉冲" in scenario.description or "扰动" in scenario.description
        assert scenario.duration_s > 0

    def test_stairs_5deg(self):
        """验证 stairs_5deg 场景配置。"""
        scenario = BENCHMARKS["stairs_5deg"]
        assert scenario.name == "stairs_5deg"
        assert "5" in scenario.description or "阶梯" in scenario.description
        assert scenario.duration_s > 0

    def test_all_durations_positive(self):
        """所有场景的持续时间应为正数。"""
        for name, scenario in BENCHMARKS.items():
            assert (
                scenario.duration_s > 0
            ), f"场景 {name} 持续时间应为正: {scenario.duration_s}"

    def test_all_durations_reasonable(self):
        """所有场景的持续时间应在合理范围内（不超过 5 分钟）。"""
        for name, scenario in BENCHMARKS.items():
            assert (
                scenario.duration_s <= 300.0
            ), f"场景 {name} 持续时间过长: {scenario.duration_s}s"


class TestBenchmarkUsage:
    """测试基准场景的典型使用模式。"""

    def test_iterate_all_benchmarks(self):
        """验证可以迭代所有基准场景。"""
        count = 0
        for name, scenario in BENCHMARKS.items():
            assert isinstance(name, str)
            assert isinstance(scenario, BenchmarkScenario)
            count += 1
        assert count == len(BENCHMARKS)

    def test_lookup_by_name(self):
        """验证可以按名称查找场景。"""
        scenario = BENCHMARKS.get("flat_100_steps")
        assert scenario is not None
        assert scenario.name == "flat_100_steps"

    def test_nonexistent_benchmark(self):
        """查找不存在的场景应返回 None。"""
        scenario = BENCHMARKS.get("nonexistent_scenario")
        assert scenario is None

    def test_scenarios_have_descriptions(self):
        """所有场景应有非空描述。"""
        for name, scenario in BENCHMARKS.items():
            assert scenario.description, f"场景 {name} 缺少描述"
            assert len(scenario.description) > 0

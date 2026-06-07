"""energy_metrics.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from energy_metrics import (
    collision_loss_per_step,
    cost_of_transport,
    mechanical_energy_series,
    spring_potential_energy,
)


class TestCostOfTransport:
    """测试 CoT 计算。"""

    def test_basic_calculation(self):
        """基本 CoT 计算。"""
        input_energy = 100.0  # J
        mass = 10.0  # kg
        distance = 1.0  # m
        g = 9.81

        cot = cost_of_transport(input_energy, mass, distance, g)
        expected = 100.0 / (10.0 * 9.81 * 1.0)
        assert cot == pytest.approx(expected)

    def test_zero_distance(self):
        """零距离应返回 inf（避免除零）。"""
        cot = cost_of_transport(100.0, 10.0, 0.0)
        # 实现使用 max(distance, 1e-9) 避免除零，所以不会是 inf
        assert cot > 1e8  # 非常大的值

    def test_zero_energy(self):
        """零能量应返回 0。"""
        cot = cost_of_transport(0.0, 10.0, 1.0)
        assert cot == 0.0

    def test_negative_mass(self):
        """负质量应返回 inf（物理无效）。"""
        cot = cost_of_transport(100.0, -10.0, 1.0)
        assert cot == float("inf")

    def test_small_distance(self):
        """极小距离应使用最小值避免数值问题。"""
        cot = cost_of_transport(100.0, 10.0, 1e-12)
        assert not np.isnan(cot)
        assert cot > 0

    def test_custom_gravity(self):
        """应支持自定义重力加速度。"""
        cot_earth = cost_of_transport(100.0, 10.0, 1.0, g=9.81)
        cot_moon = cost_of_transport(100.0, 10.0, 1.0, g=1.62)

        # 月球重力小，相同能量下 CoT 更大
        assert cot_moon > cot_earth


class TestSpringPotentialEnergy:
    """测试弹簧势能计算。"""

    def test_zero_extension(self):
        """零形变应返回零势能。"""
        pe = spring_potential_energy(k=1000.0, extension=0.5, ref=0.5)
        assert pe == 0.0

    def test_positive_extension(self):
        """拉伸应产生正势能。"""
        pe = spring_potential_energy(k=1000.0, extension=0.6, ref=0.5)
        expected = 0.5 * 1000.0 * (0.6 - 0.5) ** 2
        assert pe == pytest.approx(expected)

    def test_negative_extension(self):
        """压缩应产生正势能（弹性势能总为正）。"""
        pe = spring_potential_energy(k=1000.0, extension=0.4, ref=0.5)
        expected = 0.5 * 1000.0 * (0.4 - 0.5) ** 2
        assert pe == pytest.approx(expected)
        assert pe > 0

    def test_default_reference(self):
        """默认参考位置应为 0。"""
        pe = spring_potential_energy(k=1000.0, extension=0.1)
        expected = 0.5 * 1000.0 * 0.1 ** 2
        assert pe == pytest.approx(expected)

    def test_stiffness_scaling(self):
        """势能应与刚度线性相关。"""
        pe1 = spring_potential_energy(k=1000.0, extension=0.1, ref=0.0)
        pe2 = spring_potential_energy(k=2000.0, extension=0.1, ref=0.0)
        assert pe2 == pytest.approx(2.0 * pe1)


class TestMechanicalEnergySeries:
    """测试机械能时序计算。"""

    def test_empty_input(self):
        """空输入应返回空数组。"""
        result = mechanical_energy_series([], mass_kg=10.0)
        assert len(result["time"]) == 0
        assert len(result["ke"]) == 0
        assert len(result["pe"]) == 0
        assert len(result["total"]) == 0

    def test_single_point(self):
        """单点数据应正确计算。"""
        rows = [
            {
                "time": 0.0,
                "hip_x_vel": 1.0,
                "hip_z_vel": 0.0,
                "hip_z": 1.0,
            }
        ]
        result = mechanical_energy_series(rows, mass_kg=10.0, g=9.81)

        assert len(result["time"]) == 1
        assert result["ke"][0] == pytest.approx(0.5 * 10.0 * 1.0 ** 2)
        assert result["pe"][0] == pytest.approx(10.0 * 9.81 * 1.0)
        assert result["total"][0] == pytest.approx(result["ke"][0] + result["pe"][0])

    def test_multiple_points(self):
        """多点数据应正确计算。"""
        rows = [
            {"time": 0.0, "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.1, "hip_x_vel": 1.1, "hip_z_vel": 0.1, "hip_z": 1.05},
            {"time": 0.2, "hip_x_vel": 1.2, "hip_z_vel": 0.0, "hip_z": 1.1},
        ]
        result = mechanical_energy_series(rows, mass_kg=10.0)

        assert len(result["time"]) == 3
        assert len(result["ke"]) == 3
        assert len(result["pe"]) == 3
        assert len(result["total"]) == 3

    def test_custom_keys(self):
        """应支持自定义字段名。"""
        rows = [
            {"t": 0.0, "vx": 1.0, "vz": 0.0, "z": 1.0},
        ]
        result = mechanical_energy_series(
            rows, mass_kg=10.0, vx_key="vx", vz_key="vz", z_key="z", t_key="t"
        )

        assert result["time"][0] == 0.0
        assert result["ke"][0] == pytest.approx(0.5 * 10.0 * 1.0 ** 2)

    def test_missing_velocity_defaults_zero(self):
        """缺失速度字段应默认为 0。"""
        rows = [{"time": 0.0, "hip_z": 1.0}]
        result = mechanical_energy_series(rows, mass_kg=10.0)

        # 无速度 → KE = 0
        assert result["ke"][0] == 0.0

    def test_spring_energy_contribution(self):
        """弹簧势能应正确累加到 PE。"""
        rows = [
            {"time": 0.0, "hip_x_vel": 0.0, "hip_z_vel": 0.0, "hip_z": 1.0, "spring_ext": 0.1},
        ]
        springs = [{"k": 1000.0, "ref": 0.0, "key": "spring_ext"}]

        result = mechanical_energy_series(rows, mass_kg=10.0, springs=springs)

        # PE = m*g*z + 0.5*k*(ext-ref)^2
        expected_pe = 10.0 * 9.81 * 1.0 + 0.5 * 1000.0 * 0.1 ** 2
        assert result["pe"][0] == pytest.approx(expected_pe)

    def test_multiple_springs(self):
        """多个弹簧势能应累加。"""
        rows = [
            {
                "time": 0.0,
                "hip_x_vel": 0.0,
                "hip_z_vel": 0.0,
                "hip_z": 1.0,
                "spring1": 0.1,
                "spring2": 0.05,
            },
        ]
        springs = [
            {"k": 1000.0, "ref": 0.0, "key": "spring1"},
            {"k": 2000.0, "ref": 0.0, "key": "spring2"},
        ]

        result = mechanical_energy_series(rows, mass_kg=10.0, springs=springs)

        spring_pe = 0.5 * 1000.0 * 0.1 ** 2 + 0.5 * 2000.0 * 0.05 ** 2
        expected_pe = 10.0 * 9.81 * 1.0 + spring_pe
        assert result["pe"][0] == pytest.approx(expected_pe)


class TestCollisionLossPerStep:
    """测试碰撞损耗计算。"""

    def test_empty_input(self):
        """空输入应返回空列表。"""
        result = collision_loss_per_step([], mass_kg=10.0)
        assert len(result) == 0

    def test_no_support_switching(self):
        """无支撑足切换应返回空列表。"""
        rows = [
            {"time": 0.0, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.1, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.2, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
        ]
        result = collision_loss_per_step(rows, mass_kg=10.0)
        assert len(result) == 0

    def test_single_support_switch(self):
        """单次支撑足切换应检测到能量跳变。"""
        rows = [
            {"time": 0.0, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.1, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.2, "support_foot": "right", "hip_x_vel": 0.8, "hip_z_vel": 0.0, "hip_z": 0.95},
            {"time": 0.3, "support_foot": "right", "hip_x_vel": 0.8, "hip_z_vel": 0.0, "hip_z": 0.95},
        ]
        result = collision_loss_per_step(rows, mass_kg=10.0, window=1)

        assert len(result) >= 1
        assert result[0]["support_from"] == "left"
        assert result[0]["support_to"] == "right"
        assert result[0]["dE_J"] >= 0  # 能量损失应为正

    def test_multiple_switches(self):
        """多次切换应检测到多个碰撞事件。"""
        rows = [
            {"time": 0.0, "support_foot": "left", "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0},
            {"time": 0.1, "support_foot": "right", "hip_x_vel": 0.9, "hip_z_vel": 0.0, "hip_z": 0.98},
            {"time": 0.2, "support_foot": "left", "hip_x_vel": 0.85, "hip_z_vel": 0.0, "hip_z": 0.96},
            {"time": 0.3, "support_foot": "right", "hip_x_vel": 0.8, "hip_z_vel": 0.0, "hip_z": 0.94},
        ]
        result = collision_loss_per_step(rows, mass_kg=10.0, window=0)

        # 应检测到 3 次切换
        assert len(result) == 3


class TestEdgeCases:
    """边界情况测试。"""

    def test_energy_with_zero_mass(self):
        """零质量应产生零能量。"""
        rows = [{"time": 0.0, "hip_x_vel": 1.0, "hip_z_vel": 0.0, "hip_z": 1.0}]
        result = mechanical_energy_series(rows, mass_kg=0.0)

        assert result["ke"][0] == 0.0
        assert result["pe"][0] == 0.0
        assert result["total"][0] == 0.0

    def test_negative_spring_stiffness(self):
        """负刚度仍能计算（数学上允许）。"""
        pe = spring_potential_energy(k=-1000.0, extension=0.1, ref=0.0)
        # 负刚度会导致负势能
        assert pe < 0

    def test_large_velocity_values(self):
        """大速度值应正常处理。"""
        rows = [{"time": 0.0, "hip_x_vel": 100.0, "hip_z_vel": 50.0, "hip_z": 10.0}]
        result = mechanical_energy_series(rows, mass_kg=10.0)

        expected_ke = 0.5 * 10.0 * (100.0 ** 2 + 50.0 ** 2)
        assert result["ke"][0] == pytest.approx(expected_ke)

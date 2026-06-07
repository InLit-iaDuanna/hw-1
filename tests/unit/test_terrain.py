"""terrain.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from terrain import (
    HFIELD_NAME,
    HFIELD_NCOL,
    HFIELD_NROW,
    build_rugged_assets_xml,
    build_rugged_geom_xml,
    fill_hfield_data,
    generate_profile,
)


class TestTerrainXMLGeneration:
    """测试 XML 生成函数。"""

    def test_flat_terrain_returns_empty_asset(self):
        """amplitude=0 时 assets XML 应为空。"""
        xml = build_rugged_assets_xml(amplitude_m=0.0)
        assert xml == ""

    def test_flat_terrain_returns_plane_geom(self):
        """amplitude=0 时应返回 plane 类型 geom。"""
        xml = build_rugged_geom_xml(amplitude_m=0.0)
        assert 'type="plane"' in xml
        assert 'name="ramp"' in xml

    def test_rugged_terrain_returns_hfield_asset(self):
        """amplitude>0 时应返回 hfield 声明。"""
        xml = build_rugged_assets_xml(amplitude_m=0.05, length_m=90.0, width_m=3.6)
        assert HFIELD_NAME in xml
        assert f'nrow="{HFIELD_NROW}"' in xml
        assert f'ncol="{HFIELD_NCOL}"' in xml

    def test_rugged_terrain_returns_hfield_geom(self):
        """amplitude>0 时应返回 hfield 类型 geom。"""
        xml = build_rugged_geom_xml(amplitude_m=0.05)
        assert 'type="hfield"' in xml
        assert f'hfield="{HFIELD_NAME}"' in xml
        assert 'name="ramp"' in xml

    def test_geom_name_consistency(self):
        """无论 amplitude 值，geom name 始终为 'ramp'。"""
        xml_flat = build_rugged_geom_xml(amplitude_m=0.0)
        xml_rugged = build_rugged_geom_xml(amplitude_m=0.05)
        assert 'name="ramp"' in xml_flat
        assert 'name="ramp"' in xml_rugged


class TestProfileGeneration:
    """测试地形高度剖面生成。"""

    def test_profile_shape(self):
        """生成的 profile 应为 (HFIELD_NROW, HFIELD_NCOL)。"""
        profile = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=42
        )
        assert profile.shape == (HFIELD_NROW, HFIELD_NCOL)

    def test_profile_range(self):
        """profile 值域应在 [0, 1]。"""
        profile = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=42
        )
        assert np.all(profile >= 0.0)
        assert np.all(profile <= 1.0)

    def test_profile_flat_start(self):
        """起始区域（x < 0）应为平地（高度 = 0）。"""
        profile = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=42
        )
        # 前 1/4 列应接近 0（x < 0 区域）
        flat_zone = profile[:, : HFIELD_NCOL // 4]
        assert np.mean(flat_zone) < 0.05

    def test_profile_reproducibility(self):
        """相同 seed 应生成相同的 profile。"""
        p1 = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=123
        )
        p2 = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=123
        )
        np.testing.assert_array_equal(p1, p2)

    def test_profile_variability(self):
        """不同 seed 应生成不同的 profile。"""
        p1 = generate_profile(amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=1)
        p2 = generate_profile(amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=2)
        assert not np.allclose(p1, p2)

    def test_profile_y_uniformity(self):
        """y 方向（行方向）应保持一致（矢状面对称）。"""
        profile = generate_profile(
            amplitude_m=0.05, wavelength_m=1.0, length_m=90.0, seed=42
        )
        for col_idx in range(HFIELD_NCOL):
            col_vals = profile[:, col_idx]
            assert np.std(col_vals) < 1e-10  # 同一列所有行应相同


class TestHfieldDataFilling:
    """测试 hfield 数据填充。"""

    def test_fill_hfield_data_size_match(self):
        """profile 尺寸与 model.hfield_data 匹配时不应抛异常。"""
        import mujoco

        # 创建最小 model 用于测试
        xml = f"""
        <mujoco>
          <asset>
            <hfield name="{HFIELD_NAME}" nrow="{HFIELD_NROW}" ncol="{HFIELD_NCOL}"
                    size="45 1.8 0.05 0.08"/>
          </asset>
          <worldbody>
            <geom type="hfield" hfield="{HFIELD_NAME}"/>
          </worldbody>
        </mujoco>
        """
        model = mujoco.MjModel.from_xml_string(xml)
        profile = np.random.rand(HFIELD_NROW, HFIELD_NCOL).astype(np.float32)

        # 不应抛异常
        fill_hfield_data(model, profile)

        # 验证数据已写入
        assert model.hfield_data.size == HFIELD_NROW * HFIELD_NCOL
        np.testing.assert_array_almost_equal(
            model.hfield_data.reshape(HFIELD_NROW, HFIELD_NCOL), profile
        )

    def test_fill_hfield_data_size_mismatch(self):
        """profile 尺寸不匹配时应抛 AssertionError。"""
        import mujoco

        xml = f"""
        <mujoco>
          <asset>
            <hfield name="{HFIELD_NAME}" nrow="4" ncol="64" size="45 1.8 0.05 0.08"/>
          </asset>
          <worldbody>
            <geom type="hfield" hfield="{HFIELD_NAME}"/>
          </worldbody>
        </mujoco>
        """
        model = mujoco.MjModel.from_xml_string(xml)
        wrong_profile = np.random.rand(HFIELD_NROW, HFIELD_NCOL).astype(np.float32)

        with pytest.raises(AssertionError, match="hfield 尺寸不匹配"):
            fill_hfield_data(model, wrong_profile)


class TestEdgeCases:
    """边界情况测试。"""

    def test_zero_amplitude_profile(self):
        """amplitude=0 时 profile 仍会生成但不会用于 XML（实际由 build_rugged_geom_xml 控制）。"""
        profile = generate_profile(
            amplitude_m=0.0, wavelength_m=1.0, length_m=90.0, seed=42
        )
        # generate_profile 本身不检查 amplitude，仍生成正常 profile
        # 实际使用中 amplitude=0 时不会调用 fill_hfield_data
        assert profile.shape == (HFIELD_NROW, HFIELD_NCOL)
        assert np.all(profile >= 0.0)
        assert np.all(profile <= 1.0)

    def test_large_amplitude(self):
        """大幅值不应导致 profile 超出 [0,1]。"""
        profile = generate_profile(
            amplitude_m=0.5, wavelength_m=1.0, length_m=90.0, seed=42
        )
        assert np.all(profile >= 0.0)
        assert np.all(profile <= 1.0)

    def test_small_wavelength(self):
        """小波长应产生高频地形。"""
        profile = generate_profile(
            amplitude_m=0.05, wavelength_m=0.2, length_m=90.0, seed=42
        )
        # 检查相邻列差异较大（高频）
        diffs = np.abs(np.diff(profile[0, :]))
        assert np.mean(diffs) > 0.01

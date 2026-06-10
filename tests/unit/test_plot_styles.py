"""Unit tests for common.plot_styles."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from plot_styles import CHINESE_FONTS, PALETTE, plot_robustness_heatmap, set_style


class TestPalette:
    def test_palette_keys(self):
        expected_keys = {"ok", "warn", "fail", "neutral", "left", "right"}
        assert set(PALETTE.keys()) == expected_keys

    def test_palette_hex_format(self):
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for key, color in PALETTE.items():
            assert hex_pattern.match(color), f"Invalid color {key}={color}"

    def test_palette_immutability(self):
        assert "ok" in PALETTE
        assert PALETTE["ok"] == "#2a7a3b"


class TestChineseFonts:
    def test_chinese_fonts_type(self):
        assert isinstance(CHINESE_FONTS, list)

    def test_chinese_fonts_nonempty(self):
        assert len(CHINESE_FONTS) > 0

    def test_chinese_fonts_content(self):
        assert "Microsoft YaHei" in CHINESE_FONTS
        assert "SimHei" in CHINESE_FONTS


class TestSetStyle:
    def setup_method(self):
        self.original_sans_serif = matplotlib.rcParams.get("font.sans-serif", []).copy()
        self.original_unicode_minus = matplotlib.rcParams.get("axes.unicode_minus")
        self.original_dpi = matplotlib.rcParams.get("figure.dpi")

    def teardown_method(self):
        matplotlib.rcParams["font.sans-serif"] = self.original_sans_serif
        matplotlib.rcParams["axes.unicode_minus"] = self.original_unicode_minus
        matplotlib.rcParams["figure.dpi"] = self.original_dpi

    def test_set_style_modifies_rcparams(self):
        set_style()
        current_fonts = matplotlib.rcParams["font.sans-serif"]
        for font in CHINESE_FONTS:
            assert font in current_fonts

    def test_chinese_fonts_prepended(self):
        matplotlib.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
        set_style()
        current_fonts = matplotlib.rcParams["font.sans-serif"]
        assert current_fonts.index("Microsoft YaHei") < current_fonts.index("Arial")

    def test_unicode_minus_disabled(self):
        set_style()
        assert matplotlib.rcParams["axes.unicode_minus"] is False

    def test_dpi_settings(self):
        set_style()
        assert matplotlib.rcParams["figure.dpi"] == 110
        assert matplotlib.rcParams["savefig.dpi"] > 0

    def test_grid_settings(self):
        set_style()
        assert matplotlib.rcParams["axes.grid"] is True
        assert matplotlib.rcParams["grid.alpha"] == 0.3

    def test_idempotent(self):
        set_style()
        fonts_after_first = len(matplotlib.rcParams["font.sans-serif"])
        set_style()
        fonts_after_second = len(matplotlib.rcParams["font.sans-serif"])
        assert fonts_after_second >= fonts_after_first


class TestIntegration:
    def test_style_works_with_pyplot(self):
        import matplotlib.pyplot as plt

        set_style()
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_xlabel("test")
        fonts = matplotlib.rcParams["font.sans-serif"]
        assert any(font in fonts for font in CHINESE_FONTS)
        plt.close(fig)

    def test_palette_colors_valid_for_plotting(self):
        import matplotlib.pyplot as plt

        set_style()
        fig, ax = plt.subplots()
        for key, color in PALETTE.items():
            ax.plot([0, 1], [0, 1], color=color, label=key)
        plt.close(fig)

    def test_plot_robustness_heatmap(self):
        import matplotlib.pyplot as plt

        fig, ax = plot_robustness_heatmap(
            np.array([[0.2, 0.8], [1.0, 0.0]]),
            x_labels=["low", "high"],
            y_labels=["flat", "rough"],
        )
        assert ax.get_title() == "Robustness Heatmap"
        assert len(ax.texts) == 4
        plt.close(fig)

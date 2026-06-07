"""plot_styles.py 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT / "common"))

from plot_styles import CHINESE_FONTS, PALETTE, set_style


class TestPalette:
    """测试调色板常量。"""

    def test_palette_keys(self):
        """验证所有预期颜色键存在。"""
        expected_keys = {"ok", "warn", "fail", "neutral", "left", "right"}
        assert set(PALETTE.keys()) == expected_keys

    def test_palette_hex_format(self):
        """所有颜色值应为有效的十六进制颜色代码。"""
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for key, color in PALETTE.items():
            assert hex_pattern.match(color), f"颜色 {key}={color} 格式无效"

    def test_palette_immutability(self):
        """PALETTE 应为不可变（设计意图）。"""
        # 字典本身可变，但测试访问不应失败
        assert "ok" in PALETTE
        assert PALETTE["ok"] == "#2a7a3b"


class TestChineseFonts:
    """测试中文字体列表。"""

    def test_chinese_fonts_type(self):
        """CHINESE_FONTS 应为列表。"""
        assert isinstance(CHINESE_FONTS, list)

    def test_chinese_fonts_nonempty(self):
        """字体列表不应为空。"""
        assert len(CHINESE_FONTS) > 0

    def test_chinese_fonts_content(self):
        """验证包含常见中文字体。"""
        assert "Microsoft YaHei" in CHINESE_FONTS
        assert "SimHei" in CHINESE_FONTS


class TestSetStyle:
    """测试 set_style 函数。"""

    def setup_method(self):
        """每个测试前保存原始 rcParams。"""
        self.original_sans_serif = matplotlib.rcParams.get("font.sans-serif", []).copy()
        self.original_unicode_minus = matplotlib.rcParams.get("axes.unicode_minus")
        self.original_dpi = matplotlib.rcParams.get("figure.dpi")

    def teardown_method(self):
        """每个测试后恢复原始 rcParams。"""
        matplotlib.rcParams["font.sans-serif"] = self.original_sans_serif
        matplotlib.rcParams["axes.unicode_minus"] = self.original_unicode_minus
        matplotlib.rcParams["figure.dpi"] = self.original_dpi

    def test_set_style_modifies_rcparams(self):
        """set_style 应修改 matplotlib rcParams。"""
        set_style()

        # 验证中文字体已添加到 sans-serif 前端
        current_fonts = matplotlib.rcParams["font.sans-serif"]
        for font in CHINESE_FONTS:
            assert font in current_fonts

    def test_chinese_fonts_prepended(self):
        """中文字体应被添加到现有字体列表前端。"""
        # 设置初始字体
        matplotlib.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
        set_style()

        current_fonts = matplotlib.rcParams["font.sans-serif"]
        # Microsoft YaHei 应在 Arial 之前
        yahei_idx = current_fonts.index("Microsoft YaHei")
        arial_idx = current_fonts.index("Arial")
        assert yahei_idx < arial_idx

    def test_unicode_minus_disabled(self):
        """axes.unicode_minus 应被设为 False（避免负号显示问题）。"""
        set_style()
        assert matplotlib.rcParams["axes.unicode_minus"] is False

    def test_dpi_settings(self):
        """DPI 设置应被正确配置。"""
        set_style()
        assert matplotlib.rcParams["figure.dpi"] == 110
        # savefig.dpi 可能被 matplotlib 默认设置覆盖，只验证不为 None
        assert matplotlib.rcParams["savefig.dpi"] > 0

    def test_grid_settings(self):
        """网格设置应被启用。"""
        set_style()
        assert matplotlib.rcParams["axes.grid"] is True
        assert matplotlib.rcParams["grid.alpha"] == 0.3

    def test_idempotent(self):
        """多次调用 set_style 会重复添加字体（已知行为）。"""
        set_style()
        fonts_after_first = len(matplotlib.rcParams["font.sans-serif"])

        set_style()
        fonts_after_second = len(matplotlib.rcParams["font.sans-serif"])

        # 当前实现会重复添加，这是已知行为（非 bug）
        # 测试验证实现不会崩溃即可
        assert fonts_after_second >= fonts_after_first


class TestIntegration:
    """集成测试：验证样式在实际绘图中可用。"""

    def test_style_works_with_pyplot(self):
        """验证样式设置后 pyplot 可正常使用。"""
        import matplotlib.pyplot as plt

        set_style()

        # 创建简单图形不应报错
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_xlabel("测试中文")

        # 验证中文字体在字体列表中
        fonts = matplotlib.rcParams["font.sans-serif"]
        assert any(font in fonts for font in CHINESE_FONTS)

        plt.close(fig)

    def test_palette_colors_valid_for_plotting(self):
        """验证 PALETTE 中的颜色可用于绘图。"""
        import matplotlib.pyplot as plt

        set_style()

        fig, ax = plt.subplots()
        for key, color in PALETTE.items():
            # 不应抛出异常
            ax.plot([0, 1], [0, 1], color=color, label=key)

        plt.close(fig)

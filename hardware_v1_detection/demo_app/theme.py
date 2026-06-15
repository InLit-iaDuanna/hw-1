"""Clinical visual theme for the Hardware V1 gait dashboard.

This module isolates all visual styling (color palette, Qt stylesheet, and
pyqtgraph defaults) from the dashboard logic in ``app.py``. Swap the palette
here to restyle the whole app without touching the data pipeline.

Design intent: move away from the default dark "oscilloscope" look toward a
light, clean clinical instrument feel — soft off-white surfaces, card panels,
clear typography, and the red/yellow/green symmetry semantics used in stroke
gait reporting.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # pragma: no cover - styling is optional at import time
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Palette:
    """Clinical color palette. All values are hex strings."""

    # Surfaces
    window: str = "#eef2f6"        # app background, cool clinical grey-blue
    surface: str = "#ffffff"       # card / panel background
    surface_alt: str = "#f6f8fb"   # subtle alternate fill
    border: str = "#d8e0e8"        # hairline card border
    grid: str = "#e3e9f0"          # plot gridlines

    # Text
    text: str = "#1f2d3d"          # primary text, near-black slate
    text_muted: str = "#5b6b7b"    # secondary labels
    text_inverse: str = "#ffffff"

    # Brand / accents
    accent: str = "#2b6cb0"        # primary action blue
    accent_dark: str = "#22517f"
    accent_soft: str = "#e8f1fb"

    # Clinical zones (symmetry index)
    zone_green: str = "#2f9e6f"    # < 10% — symmetric
    zone_yellow: str = "#e2a13b"   # 10-20% — mild asymmetry
    zone_red: str = "#d6533c"      # > 20% — marked asymmetry
    zone_unknown: str = "#9aa7b4"

    # Body-side semantics (left vs right)
    left: str = "#d6533c"          # warm — left side
    left_soft: str = "#f3a18f"
    right: str = "#2b6cb0"         # cool — right side
    right_soft: str = "#8fb8df"
    left_accent: str = "#e07a2f"   # secondary left trace (e.g. hip)
    right_accent: str = "#3aa6a0"  # secondary right trace (e.g. hip)


PALETTE = Palette()

# Font stack: prefer a clean clinical sans, gracefully degrade.
FONT_FAMILY = "Segoe UI, Inter, Roboto, Helvetica Neue, Arial, sans-serif"


def qss(p: Palette = PALETTE) -> str:
    """Return the application-wide Qt stylesheet for the clinical look."""

    return f"""
    QMainWindow, QWidget {{
        background: {p.window};
        color: {p.text};
        font-family: {FONT_FAMILY};
        font-size: 13px;
    }}

    /* ---- Cards / framed panels ---- */
    QFrame#card {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 10px;
    }}

    /* ---- Controls bar ---- */
    QLabel {{
        color: {p.text};
    }}
    QLabel#fieldLabel {{
        color: {p.text_muted};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#statusBar {{
        color: {p.text_muted};
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    QComboBox, QLineEdit {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 5px 8px;
        selection-background-color: {p.accent_soft};
        selection-color: {p.text};
    }}
    QComboBox:focus, QLineEdit:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: {p.surface_alt};
        border: 1px solid {p.accent};
    }}
    QPushButton:disabled {{
        color: {p.text_muted};
        background: {p.surface_alt};
        border: 1px solid {p.border};
    }}
    QPushButton#primary {{
        background: {p.accent};
        color: {p.text_inverse};
        border: 1px solid {p.accent_dark};
    }}
    QPushButton#primary:hover {{
        background: {p.accent_dark};
    }}
    QPushButton#primary:disabled {{
        background: {p.right_soft};
        border: 1px solid {p.right_soft};
        color: {p.surface};
    }}

    /* ---- Tabs ---- */
    QTabWidget::pane {{
        border: 1px solid {p.border};
        border-radius: 8px;
        background: {p.surface};
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {p.text_muted};
        padding: 8px 18px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {p.surface};
        color: {p.accent};
        border: 1px solid {p.border};
        border-bottom: 2px solid {p.accent};
    }}
    QTabBar::tab:hover:!selected {{
        color: {p.text};
    }}

    /* ---- Metric tiles (side panel) ---- */
    QLabel#metricValue {{
        color: {p.text};
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#metricCaption {{
        color: {p.text_muted};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    """


def apply_pyqtgraph_theme(p: Palette = PALETTE) -> None:
    """Set global pyqtgraph defaults to match the clinical look."""

    if pg is None:  # pragma: no cover
        return
    pg.setConfigOption("background", p.surface)
    pg.setConfigOption("foreground", p.text)
    pg.setConfigOptions(antialias=True)


def style_plot(plot, p: Palette = PALETTE) -> None:
    """Apply consistent clinical styling to a pyqtgraph PlotWidget."""

    if pg is None:  # pragma: no cover
        return
    plot.setBackground(p.surface)
    plot.showGrid(x=True, y=True, alpha=0.18)
    for axis_name in ("left", "bottom"):
        axis = plot.getAxis(axis_name)
        axis.setPen(pg.mkPen(p.text_muted, width=1))
        axis.setTextPen(pg.mkPen(p.text_muted))
    title_item = getattr(plot, "titleLabel", None)
    if title_item is not None:
        try:
            title_item.setText(title_item.text, color=p.text, size="11pt", bold=True)
        except Exception:  # pragma: no cover - pyqtgraph version drift
            pass


# Trace colors keyed by joint name, for consistent left/right semantics.
JOINT_COLORS: dict[str, str] = {
    "left_knee": PALETTE.left,
    "right_knee": PALETTE.right,
    "left_hip": PALETTE.left_accent,
    "right_hip": PALETTE.right_accent,
    "left_ankle": PALETTE.left_soft,
    "right_ankle": PALETTE.right_soft,
}

EVENT_COLORS: dict[str, str] = {
    "left_heel_strike": PALETTE.left,
    "left_toe_off": PALETTE.left_accent,
    "right_heel_strike": PALETTE.right,
    "right_toe_off": PALETTE.right_accent,
}

ZONE_COLORS: dict[str, str] = {
    "green": PALETTE.zone_green,
    "yellow": PALETTE.zone_yellow,
    "red": PALETTE.zone_red,
    "unknown": PALETTE.zone_unknown,
}

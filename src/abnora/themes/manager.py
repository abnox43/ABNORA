"""Centralized theme manager.

All interface styling flows through here: a Theme's tokens are converted to a
single Qt stylesheet, and the active theme (with accent / font-size /
reduced-motion adjustments) is broadcast to the UI. Switching never restarts
the application.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette

from .definitions import DEFAULT_THEME_ID, ALL_THEMES, theme_by_id
from .models import Theme

MIN_UI_FONT = 9
MAX_UI_FONT = 18


class ThemeManager(QObject):
    """Owns the active theme plus user adjustments and emits change signals."""

    theme_changed = Signal(Theme)

    def __init__(self, settings):
        """`settings` is an abnora.storage.settings.Settings instance."""
        super().__init__()
        self._settings = settings
        self._accent: str | None = self._settings.value("theme/accent", "")
        if not self._accent:
            self._accent = None
        self._font_scale: int = int(self._settings.value("theme/ui_font_scale", 0))
        self._reduced_motion: bool = self._settings.value(
            "theme/reduced_motion",
            self._detect_reduced_motion(),
            type=bool,
        )
        # Per-effect overrides (e.g. CRT scanlines toggled off by the user).
        self._effect_overrides: dict[str, bool] = {}
        theme_id = self._settings.value("theme/id", DEFAULT_THEME_ID)
        theme = theme_by_id(theme_id) or theme_by_id(DEFAULT_THEME_ID)
        assert theme is not None
        self._theme: Theme = self._apply_adjustments(theme)

    # ------------------------------------------------------------------ state

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    @staticmethod
    def _detect_reduced_motion() -> bool:
        import os
        return os.environ.get("QT_QPA_PLATFORM") == "offscreen" or bool(
            os.environ.get("ABNORA_REDUCED_MOTION")
        )

    def _apply_adjustments(self, theme: Theme) -> Theme:
        t = theme
        if self._accent:
            t = t.with_overrides(
                accent=self._accent,
                accent_hover=_lighten(self._accent, 0.18),
                focus=self._accent,
            )
        if self._effect_overrides:
            eff = t.effects
            changes = {
                k: v for k, v in self._effect_overrides.items()
                if hasattr(eff, k)
            }
            if changes:
                t = t.with_overrides(effects=eff.__class__(**{**eff.__dict__, **changes}))
        return t

    # ---------------------------------------------------------------- actions

    def set_theme(self, theme_id: str, persist: bool = True) -> bool:
        theme = theme_by_id(theme_id)
        if theme is None:
            return False
        self._theme = self._apply_adjustments(theme)
        if persist:
            self._settings.setValue("theme/id", theme_id)
        self.theme_changed.emit(self._theme)
        return True

    def set_accent(self, color: str | None, persist: bool = True) -> None:
        self._accent = color if color and QColor(color).isValid() else None
        if persist:
            self._settings.setValue("theme/accent", self._accent or "")
        self._theme = self._apply_adjustments(
            theme_by_id(self._theme.id) or self._theme
        )
        self.theme_changed.emit(self._theme)

    def set_ui_font_scale(self, scale: int, persist: bool = True) -> None:
        """scale is an offset in points applied to the base UI font size."""
        self._font_scale = max(MIN_UI_FONT - 11, min(MAX_UI_FONT - 11, scale))
        if persist:
            self._settings.setValue("theme/ui_font_scale", self._font_scale)
        self._theme = self._apply_adjustments(
            theme_by_id(self._theme.id) or self._theme
        )
        self.theme_changed.emit(self._theme)

    @property
    def ui_font_scale(self) -> int:
        return self._font_scale

    def set_reduced_motion(self, on: bool, persist: bool = True) -> None:
        self._reduced_motion = bool(on)
        if persist:
            self._settings.setValue("theme/reduced_motion", self._reduced_motion)

    def set_effect(self, name: str, enabled: bool, persist: bool = True) -> None:
        """Toggle a single decorative effect of the active theme."""
        self._effect_overrides[name] = bool(enabled)
        if persist:
            self._settings.setValue(f"theme/effect/{name}", bool(enabled))
        self._theme = self._apply_adjustments(
            theme_by_id(self._theme.id) or self._theme
        )
        self.theme_changed.emit(self._theme)

    def load_effect_overrides(self) -> None:
        for name in ("scanlines", "glow", "stars", "grid", "horizon",
                     "wood", "gears", "vignette", "canvas_texture"):
            key = f"theme/effect/{name}"
            stored = self._settings.value(key, None)
            if stored is not None:
                self._effect_overrides[name] = self._settings.value(key, type=bool)

    def reset(self) -> None:
        """Reset theme, accent, font scale, motion and effect overrides."""
        self._accent = None
        self._font_scale = 0
        self._effect_overrides.clear()
        self._settings.remove_prefix("theme/")
        self.set_theme(DEFAULT_THEME_ID, persist=True)

    # ------------------------------------------------------------------ style

    def base_font_size(self) -> int:
        return 11 + self._font_scale

    def stylesheet(self) -> str:
        return build_stylesheet(self._theme, self.base_font_size())

    def qpalette(self) -> QPalette:
        """A QPalette matching the theme (used by native dialogs)."""
        t = self._theme
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(t.window_bg))
        p.setColor(QPalette.ColorRole.WindowText, QColor(t.text))
        p.setColor(QPalette.ColorRole.Base, QColor(t.input_bg))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor(t.panel_bg))
        p.setColor(QPalette.ColorRole.Text, QColor(t.text))
        p.setColor(QPalette.ColorRole.Button, QColor(t.button_bg))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(t.text))
        p.setColor(QPalette.ColorRole.Highlight, QColor(t.accent))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(t.accent_text))
        p.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.panel_bg))
        p.setColor(QPalette.ColorRole.ToolTipText, QColor(t.text))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.text_muted))
        p.setColor(QPalette.ColorRole.Link, QColor(t.accent))
        return p

    def apply_to_app(self, app) -> None:
        app.setStyleSheet(self.stylesheet())
        app.setPalette(self.qpalette())


def _lighten(hex_color: str, amount: float) -> str:
    c = QColor(hex_color)
    if not c.isValid():
        return hex_color
    ch = lambda v: min(255, int(v + (255 - v) * amount))
    c.setRgb(ch(c.red()), ch(c.green()), ch(c.blue()))
    return c.name()


# ---------------------------------------------------------------------- QSS


def build_stylesheet(theme: Theme, base_font: int) -> str:
    """Generate the complete application stylesheet from theme tokens."""
    f_ui = theme.fonts.body
    f_head = theme.fonts.heading
    f_mono = theme.fonts.mono
    accent = theme.accent
    glow = "QPushButton:hover { border-color: %s; }" % theme.accent_hover

    return f"""
/* ---- ABNORA: {theme.name} ---- */
* {{ outline: none; }}
QMainWindow, QDialog {{ background: {theme.window_bg}; }}
QWidget {{ color: {theme.text}; font-family: {f_ui}; font-size: {base_font}px; }}

/* Toolbar */
QFrame#Toolbar {{
    background: {theme.toolbar_bg};
    border: none;
    border-bottom: 1px solid {theme.border};
}}
QLabel#AppTitle {{
    font-family: {f_head};
    font-size: {base_font + 4}px;
    font-weight: 600;
    color: {theme.text};
    letter-spacing: 1px;
}}
QLabel#DocTitle {{
    color: {theme.text_muted};
    font-family: {f_head};
    font-size: {base_font}px;
}}
QLabel[role="heading"] {{
    font-family: {f_head};
    font-size: {base_font + 2}px;
    font-weight: 600;
}}
QLabel[role="mono"] {{
    font-family: {f_mono};
    font-size: {base_font - 1}px;
    color: {theme.text_muted};
}}
QLabel[role="muted"] {{ color: {theme.text_muted}; }}

/* Buttons */
QToolButton, QPushButton {{
    background: transparent;
    color: {theme.text};
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 8px;
}}
QToolButton:hover, QPushButton:hover {{
    background: {theme.button_bg};
    border-color: {theme.border};
}}
QToolButton:pressed, QPushButton:pressed {{
    background: {theme.selection_bg};
}}
QToolButton:checked, QPushButton:checked {{
    background: {theme.selection_bg};
    border: 1px solid {accent};
    color: {theme.text};
}}
QToolButton:focus, QPushButton:focus {{
    border: 1px solid {theme.focus};
}}
QPushButton[accent="true"] {{
    background: {accent};
    color: {theme.accent_text};
    border: 1px solid {accent};
    font-weight: 600;
    padding: 5px 14px;
}}
QPushButton[accent="true"]:hover {{ background: {theme.accent_hover}; }}
{glow}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {theme.input_bg};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: {theme.selection_bg};
    selection-color: {theme.selection_text};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {theme.focus};
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {theme.panel_bg};
    color: {theme.text};
    border: 1px solid {theme.border};
    selection-background-color: {theme.selection_bg};
    selection-color: {theme.selection_text};
}}

/* Lists / trees (side panel) */
QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit {{
    background: {theme.panel_bg};
    color: {theme.text};
    border: none;
    alternate-background-color: {theme.panel_bg};
}}
QListWidget::item, QTreeWidget::item {{
    padding: 3px 4px;
    border-radius: 3px;
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background: {theme.button_bg};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {theme.selection_bg};
    color: {theme.selection_text};
}}
QTreeWidget::branch {{ background: transparent; }}

/* Tabs */
QTabWidget::pane {{
    border: none;
    background: {theme.panel_bg};
}}
QTabBar::tab {{
    background: transparent;
    color: {theme.text_muted};
    padding: 6px 10px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {theme.text};
    border-bottom: 2px solid {accent};
}}
QTabBar::tab:hover {{ color: {theme.text}; }}

/* Side panel */
QFrame#SidePanel {{
    background: {theme.panel_bg};
    border: none;
    border-right: 1px solid {theme.border};
}}
QFrame#SidePanel[right-border="false"] {{ border-right: none; }}

/* Status bar */
QFrame#StatusBar {{
    background: {theme.toolbar_bg};
    border: none;
    border-top: 1px solid {theme.border};
}}
QLabel#StatusLabel {{
    color: {theme.text_muted};
    font-family: {f_mono};
    font-size: {base_font - 1}px;
}}

/* Scroll bars */
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {theme.border};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: {theme.text_muted}; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
}}
QScrollBar::handle:horizontal {{
    background: {theme.border};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: {theme.text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Menus, tooltips */
QMenu, QMenuBar {{
    background: {theme.panel_bg};
    color: {theme.text};
    border: 1px solid {theme.border};
}}
QMenuBar {{ border: none; }}
QMenu::item {{ padding: 4px 22px 4px 12px; border-radius: 3px; }}
QMenu::item:selected {{ background: {theme.selection_bg}; color: {theme.selection_text}; }}
QToolTip {{
    background: {theme.panel_bg};
    color: {theme.text};
    border: 1px solid {theme.border};
    padding: 4px 6px;
}}

/* Progress / slider */
QProgressBar {{
    background: {theme.input_bg};
    border: 1px solid {theme.border};
    border-radius: 3px;
    text-align: center;
    color: {theme.text};
    height: 14px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}
QSlider::groove:horizontal {{ height: 3px; background: {theme.border}; }}
QSlider::handle:horizontal {{
    background: {accent};
    width: 12px; height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {theme.border};
    border-radius: 3px;
    background: {theme.input_bg};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}

/* Scroll area canvas */
QScrollArea {{ border: none; background: {theme.canvas_bg}; }}
QWidget#CanvasContainer {{ background: transparent; }}

/* Splitter */
QSplitter::handle {{ background: {theme.border}; width: 1px; }}

/* Docks */
QDockWidget {{ color: {theme.text}; titlebar-close-icon: none; }}
"""

"""Top toolbar: identity, document title, search, layout, and view controls."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QSizePolicy, QToolButton, QWidget)

from .icons import draw_logo, icon


class Toolbar(QFrame):
    open_requested = Signal()
    search_requested = Signal(str)
    search_next = Signal()
    search_prev = Signal()
    theme_browser_requested = Signal()
    layout_selected = Signal(str)
    fullscreen_toggled = Signal(bool)
    panel_toggled = Signal()
    zoom_in = Signal()
    zoom_out = Signal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self._theme = theme
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(6)

        # identity
        self.logo = QLabel()
        self.logo.setPixmap(draw_logo(30))
        self.logo.setFixedWidth(32)
        lay.addWidget(self.logo)

        self.title = QLabel("ABNORA")
        self.title.setObjectName("AppTitle")
        lay.addWidget(self.title)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: rgba(128,128,128,0.35); margin: 8px 6px;")
        lay.addWidget(sep)

        self.open_btn = QToolButton()
        self.open_btn.setToolTip("Open document  (Ctrl+O)")
        lay.addWidget(self.open_btn)

        self.doc_title = QLabel("")
        self.doc_title.setObjectName("DocTitle")
        self.doc_title.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Preferred)
        lay.addWidget(self.doc_title, 1)

        # search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search document…  (Ctrl+F)")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(170)
        self.search_edit.setMaximumWidth(280)
        self.search_edit.returnPressed.connect(
            lambda: self.search_requested.emit(self.search_edit.text()))
        lay.addWidget(self.search_edit)

        self.search_prev_btn = QToolButton()
        self.search_prev_btn.setToolTip("Previous match  (Shift+Enter)")
        self.search_prev_btn.clicked.connect(self.search_prev.emit)
        lay.addWidget(self.search_prev_btn)

        self.search_next_btn = QToolButton()
        self.search_next_btn.setToolTip("Next match  (Enter)")
        self.search_next_btn.clicked.connect(self.search_next.emit)
        lay.addWidget(self.search_next_btn)

        lay.addSpacing(4)

        # layout selector (exclusive checkable group)
        self.layout_buttons: dict[str, QToolButton] = {}
        for mode, tip in (("single", "Single page  (1)"),
                          ("pair", "Open book — two pages  (2)"),
                          ("continuous", "Continuous scroll  (3)")):
            b = QToolButton()
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, m=mode: self._on_layout(m))
            lay.addWidget(b)
            self.layout_buttons[mode] = b

        lay.addSpacing(4)

        self.theme_btn = QToolButton()
        self.theme_btn.setToolTip("Themes  (T)")
        self.theme_btn.clicked.connect(self.theme_browser_requested.emit)
        lay.addWidget(self.theme_btn)

        self.panel_btn = QToolButton()
        self.panel_btn.setToolTip("Toggle navigation panel  (F5)")
        self.panel_btn.setCheckable(True)
        self.panel_btn.clicked.connect(self.panel_toggled.emit)
        lay.addWidget(self.panel_btn)

        self.fullscreen_btn = QToolButton()
        self.fullscreen_btn.setToolTip("Full screen  (F11)")
        self.fullscreen_btn.setCheckable(True)
        self.fullscreen_btn.clicked.connect(self._on_fullscreen)
        lay.addWidget(self.fullscreen_btn)

        self.refresh_icons()

    def _on_fullscreen(self) -> None:
        self.fullscreen_toggled.emit(self.fullscreen_btn.isChecked())

    def _on_layout(self, mode: str) -> None:
        self.layout_selected.emit(mode)

    def set_layout(self, mode: str) -> None:
        for m, b in self.layout_buttons.items():
            b.setChecked(m == mode)

    def set_fullscreen(self, on: bool) -> None:
        self.fullscreen_btn.blockSignals(True)
        self.fullscreen_btn.setChecked(on)
        self.fullscreen_btn.blockSignals(False)

    def set_document_title(self, title: str) -> None:
        self.doc_title.setText(title)
        self.doc_title.setToolTip(title)

    def refresh_icons(self) -> None:
        c = self._theme.text
        self.open_btn.setIcon(icon("open", 20, c))
        self.search_prev_btn.setIcon(icon("prev", 18, self._theme.text_muted))
        self.search_next_btn.setIcon(icon("next", 18, self._theme.text_muted))
        self.layout_buttons["single"].setIcon(icon("layout-single", 19, c))
        self.layout_buttons["pair"].setIcon(icon("layout-pair", 19, c))
        self.layout_buttons["continuous"].setIcon(icon("layout-continuous", 19, c))
        self.theme_btn.setIcon(icon("theme", 20, c))
        self.panel_btn.setIcon(icon("panel", 20, c))
        self.fullscreen_btn.setIcon(icon("fullscreen", 20, c))

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.refresh_icons()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(900, 48)

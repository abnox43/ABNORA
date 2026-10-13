"""Bottom status bar: page controls, zoom, layout, and status messages."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSpinBox,
                               QToolButton, QWidget)

from .icons import icon


class StatusBar(QFrame):
    go_to_page = Signal(int)
    prev_page = Signal()
    next_page = Signal()
    zoom_in = Signal()
    zoom_out = Signal()
    fit_page_requested = Signal()
    fit_width_requested = Signal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self._theme = theme
        self.setFixedHeight(34)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 3, 12, 3)
        lay.setSpacing(6)

        self.prev_btn = QToolButton()
        self.prev_btn.setToolTip("Previous page  (← / PageUp)")
        self.prev_btn.clicked.connect(self.prev_page.emit)
        lay.addWidget(self.prev_btn)

        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(64)
        self.page_spin.setToolTip("Go to page  (G)")
        self.page_spin.valueChanged.connect(self.go_to_page.emit)
        lay.addWidget(self.page_spin)

        self.page_total = QLabel("/ 1")
        self.page_total.setObjectName("StatusLabel")
        lay.addWidget(self.page_total)

        self.next_btn = QToolButton()
        self.next_btn.setToolTip("Next page  (→ / PageDown)")
        self.next_btn.clicked.connect(self.next_page.emit)
        lay.addWidget(self.next_btn)

        lay.addSpacing(8)

        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setToolTip("Zoom out  (−)")
        self.zoom_out_btn.clicked.connect(self.zoom_out.emit)
        lay.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("StatusLabel")
        self.zoom_label.setMinimumWidth(46)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.zoom_label)

        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setToolTip("Zoom in  (+)")
        self.zoom_in_btn.clicked.connect(self.zoom_in.emit)
        lay.addWidget(self.zoom_in_btn)

        self.fit_page_btn = QToolButton()
        self.fit_page_btn.setToolTip("Fit page  (0)")
        self.fit_page_btn.clicked.connect(self.fit_page_requested.emit)
        lay.addWidget(self.fit_page_btn)

        self.fit_width_btn = QToolButton()
        self.fit_width_btn.setToolTip("Fit width  (W)")
        self.fit_width_btn.clicked.connect(self.fit_width_requested.emit)
        lay.addWidget(self.fit_width_btn)

        lay.addStretch(1)

        self.layout_label = QLabel("")
        self.layout_label.setObjectName("StatusLabel")
        lay.addWidget(self.layout_label)

        lay.addSpacing(10)

        self.message = QLabel("Ready")
        self.message.setObjectName("StatusLabel")
        self.message.setAlignment(Qt.AlignmentFlag.AlignRight |
                                  Qt.AlignmentFlag.AlignVCenter)
        self.message.setSizePolicy(self.message.sizePolicy().horizontalPolicy(),
                                   self.message.sizePolicy().verticalPolicy())
        lay.addWidget(self.message, 1)

        self._msg_timer = QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.setInterval(5000)
        self._msg_timer.timeout.connect(lambda: self.message.setText("Ready"))

        self.refresh_icons()

    def refresh_icons(self) -> None:
        t = self._theme
        self.prev_btn.setIcon(icon("prev", 16, t.text))
        self.next_btn.setIcon(icon("next", 16, t.text))
        self.zoom_out_btn.setIcon(icon("zoom-out", 16, t.text))
        self.zoom_in_btn.setIcon(icon("zoom-in", 16, t.text))
        self.fit_page_btn.setIcon(icon("fit-page", 16, t.text))
        self.fit_width_btn.setIcon(icon("fit-width", 16, t.text))

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.refresh_icons()

    # ----------------------------------------------------------- updating

    def set_page(self, page: int, total: int) -> None:
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, max(1, total))
        self.page_spin.setValue(page)
        self.page_spin.blockSignals(False)
        self.page_total.setText(f"/ {total}")

    def set_zoom(self, zoom: float) -> None:
        self.zoom_label.setText(f"{round(zoom * 100)}%")

    def set_layout_name(self, name: str) -> None:
        pretty = {"single": "Single page", "pair": "Open book",
                  "continuous": "Continuous"}.get(name, name)
        self.layout_label.setText(pretty)

    def show_message(self, text: str, temporary: bool = True) -> None:
        self.message.setText(text)
        if temporary:
            self._msg_timer.start()
        else:
            self._msg_timer.stop()

    def set_busy(self, busy: bool) -> None:
        if busy:
            self.show_message("Working…", temporary=False)

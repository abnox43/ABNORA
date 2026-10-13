"""Lightweight decorative overlays for theme effects.

The scanline overlay is a transparent, mouse-transparent child painted once
with a cached pixmap — no per-frame cost, no blur. It attaches to chrome
widgets (toolbar, status bar, side panel) and never covers PDF pages.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class ScanlineOverlay(QWidget):
    """Paints subtle CRT scanlines over a chrome widget."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._cache: QPixmap | None = None
        self._color = QColor(0, 0, 0, 26)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.hide()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.parent() and event.type() in (
                event.Type.Resize, event.Type.Show):
            self.setGeometry(self.parent().rect())
            if event.type() == event.Type.Show and self.isVisible():
                self.raise_()
        return False

    def set_color(self, color: str, alpha: int = 26) -> None:
        c = QColor(color)
        c.setAlpha(alpha)
        self._color = c
        self._cache = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._cache is None or self._cache.size() != self.size():
            self._cache = QPixmap(self.size())
            self._cache.fill(Qt.GlobalColor.transparent)
            p = QPainter(self._cache)
            p.setPen(QPen(self._color, 1))
            for y in range(0, self.height(), 3):
                p.drawLine(0, y, self.width(), y)
            p.end()
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)
        painter.end()

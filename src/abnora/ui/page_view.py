"""A single rendered PDF page inside the reading canvas.

PageView displays the actual rendered page (from PdfRenderer), draws the
surrounding shadow, search highlights, text selection, and hit-tests internal
links. All coordinate math accounts for page rotation.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QMouseEvent,
                           QPaintEvent, QPainter, QPen, QPixmap, QWheelEvent)
from PySide6.QtWidgets import QWidget

from ..pdf.document import PdfDocument

# Points-per-pixel for the current render step; mapping helpers work in PDF
# point space of the *unrotated* page.


def pdf_to_view(x: float, y: float, page_w: float, page_h: float,
                rotation: int, step: float) -> tuple[float, float]:
    """Map an unrotated PDF point to view pixels of the rendered (rotated) page."""
    r = rotation % 360
    if r == 0:
        return x * step, y * step
    if r == 90:
        return y * step, (page_w - x) * step
    if r == 180:
        return (page_w - x) * step, (page_h - y) * step
    # 270
    return (page_h - y) * step, x * step


def view_to_pdf(vx: float, vy: float, page_w: float, page_h: float,
                rotation: int, step: float) -> tuple[float, float]:
    """Inverse of pdf_to_view."""
    r = rotation % 360
    if r == 0:
        return vx / step, vy / step
    if r == 90:
        return page_w - vy / step, vx / step
    if r == 180:
        return page_w - vx / step, page_h - vy / step
    # 270
    return vy / step, page_h - vx / step


class PageView(QWidget):
    """Displays one PDF page at a given render step."""

    link_activated = Signal(int)          # target page, 0-based
    status_message = Signal(str)

    def __init__(self, doc: PdfDocument, page_index: int, renderer,
                 theme, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.page_index = page_index
        self.renderer = renderer
        self._theme = theme
        self.step = 1.0
        self.image: QImage | None = None
        self.search_rects: list[tuple[float, float, float, float]] = []
        self.selection_rects: list[tuple[float, float, float, float]] = []
        self._links: list | None = None
        self._selecting = False
        self._select_anchor: tuple[float, float] | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------- geometry

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.update()

    def set_step(self, step: float) -> None:
        self.step = step
        w, h = self.doc.rotated_page_size(self.page_index)
        self.setFixedSize(int(round(w * step)), int(round(h * step)))
        self.image = None
        self.request_render()

    def sizeHint(self):  # noqa: N802
        w, h = self.doc.rotated_page_size(self.page_index)
        from PySide6.QtCore import QSize
        return QSize(int(round(w * self.step)), int(round(h * self.step)))

    def page_size_points(self) -> tuple[float, float]:
        return self.doc.page_size(self.page_index)

    def request_render(self) -> None:
        img = self.renderer.request_page(
            self.doc, self.page_index, self.step, self.doc.rotation(self.page_index),
            step=self.step,
        )
        if img is not None:
            self._set_image(img)

    def _set_image(self, img: QImage) -> None:
        self.image = img
        self.update()

    def on_render_ready(self, path: str, page: int, step: float, img: QImage) -> None:
        if path == self.doc.path and page == self.page_index and abs(step - self.step) < 1e-6:
            self._set_image(img)

    # --------------------------------------------------------------- search

    def set_search_rects(self, rects) -> None:
        self.search_rects = list(rects)
        self.update()

    # ----------------------------------------------------------- selection

    def _pdf_rect_from_view(self, a: QPoint, b: QPoint) -> tuple[float, float, float, float]:
        w, h = self.page_size_points()
        rot = self.doc.rotation(self.page_index)
        x0, y0 = view_to_pdf(min(a.x(), b.x()), min(a.y(), b.y()), w, h, rot, self.step)
        x1, y1 = view_to_pdf(max(a.x(), b.x()), max(a.y(), b.y()), w, h, rot, self.step)
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        return (x0, y0, x1, y1)

    def _words(self):
        try:
            return self.doc.doc[self.page_index].get_text("words")
        except Exception:  # noqa: BLE001
            return []

    def update_selection(self, a: QPoint, b: QPoint) -> None:
        rect = self._pdf_rect_from_view(a, b)
        rects = []
        x0, y0, x1, y1 = rect
        for w in self._words():
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
            if wx1 >= x0 and wx0 <= x1 and wy1 >= y0 and wy0 <= y1:
                rects.append((wx0, wy0, wx1, wy1))
        self.selection_rects = rects
        self.update()

    def clear_selection(self) -> None:
        if self.selection_rects:
            self.selection_rects = []
            self.update()

    def selected_text(self) -> str:
        """Selected words in reading order (top-to-bottom, left-to-right)."""
        if not self.selection_rects:
            return ""
        words = self._words()
        picked = []
        for w in words:
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
            for (rx0, ry0, rx1, ry1) in self.selection_rects:
                if wx1 >= rx0 and wx0 <= rx1 and wy1 >= ry0 and wy0 <= ry1:
                    picked.append((round(wy0, 1), round(wx0, 1), w[4]))
                    break
        picked.sort()
        return " ".join(t for _, _, t in picked)

    # ---------------------------------------------------------------- paint

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = QRectF(self.rect())
        t = self._theme

        if self.image is None:
            p.fillRect(rect, QColor(t.canvas_bg).darker(115))
            p.setPen(QPen(QColor(t.text_muted)))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                       f"Rendering page {self.page_index + 1}…")
        else:
            # soft drop shadow
            shadow = QColor(t.page_shadow)
            for i, spread in enumerate((9, 6, 3)):
                c = QColor(shadow)
                c.setAlpha(70 - i * 20)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(rect.translated(2 + i * 0.5, 3 + i * 0.5)
                                  .adjusted(-spread * 0.4, -spread * 0.4,
                                            spread * 0.4, spread * 0.4), 2, 2)
            p.drawImage(rect.topLeft(), self.image)
            p.setPen(QPen(QColor(t.border)))

        # page border
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(t.border)))
        p.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        w, h = self.page_size_points()
        rot = self.doc.rotation(self.page_index)

        # search highlights
        if self.search_rects:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t.accent) if not t.dark else QColor(t.accent))
            for (rx0, ry0, rx1, ry1) in self.search_rects:
                vx0, vy0 = pdf_to_view(rx0, ry0, w, h, rot, self.step)
                vx1, vy1 = pdf_to_view(rx1, ry1, w, h, rot, self.step)
                r = QRectF(min(vx0, vx1), min(vy0, vy1), abs(vx1 - vx0), abs(vy1 - vy0))
                c = QColor(t.accent)
                c.setAlpha(90)
                p.setBrush(c)
                p.drawRect(r)

        # text selection
        if self.selection_rects:
            for (rx0, ry0, rx1, ry1) in self.selection_rects:
                vx0, vy0 = pdf_to_view(rx0, ry0, w, h, rot, self.step)
                vx1, vy1 = pdf_to_view(rx1, ry1, w, h, rot, self.step)
                r = QRectF(min(vx0, vx1), min(vy0, vy1), abs(vx1 - vx0), abs(vy1 - vy0))
                c = QColor(t.selection_bg)
                c.setAlpha(150)
                p.setBrush(c)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(r)
        p.end()

    # ---------------------------------------------------------- interaction

    def _ensure_links(self) -> list:
        if self._links is None:
            try:
                self._links = self.doc.links(self.page_index)
            except Exception:  # noqa: BLE001
                self._links = []
        return self._links

    def invalidate_links(self) -> None:
        self._links = None

    def _link_at(self, pos) -> object | None:
        w, h = self.page_size_points()
        rot = self.doc.rotation(self.page_index)
        px, py = view_to_pdf(pos.x(), pos.y(), w, h, rot, self.step)
        import pymupdf
        try:
            links = self.doc.doc[self.page_index].get_links()
        except Exception:  # noqa: BLE001
            return None
        for l in links:
            if l.get("kind") != pymupdf.LINK_GOTO:
                continue
            r = l.get("from")
            if r and r.x0 <= px <= r.x1 and r.y0 <= py <= r.y1:
                return l
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            link = self._link_at(event.position().toPoint())
            if link is not None and link.get("page") is not None:
                self.link_activated.emit(int(link["page"]) - 1)
                return
            self._selecting = True
            self._select_anchor = (
                event.position().toPoint().x(), event.position().toPoint().y()
            )
            self.clear_selection()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._selecting and self._select_anchor is not None:
            from PySide6.QtCore import QPoint as _QPoint
            a = _QPoint(int(self._select_anchor[0]), int(self._select_anchor[1]))
            b = event.position().toPoint()
            self.update_selection(a, b)
        else:
            # link hover cursor
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if self._link_at(event.position().toPoint()) is not None
                else Qt.CursorShape.ArrowCursor
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._selecting:
            self._selecting = False
            text = self.selected_text()
            if text:
                QGuiApplication.clipboard().setText(text)
                self.status_message.emit("Selection copied to clipboard")
            else:
                self._select_anchor = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # double-click selects a word
        pos = event.position().toPoint()
        w, h = self.page_size_points()
        rot = self.doc.rotation(self.page_index)
        px, py = view_to_pdf(pos.x(), pos.y(), w, h, rot, self.step)
        for word in self._words():
            wx0, wy0, wx1, wy1 = word[0], word[1], word[2], word[3]
            if wx0 <= px <= wx1 and wy0 <= py <= wy1:
                self.selection_rects = [(wx0, wy0, wx1, wy1)]
                QGuiApplication.clipboard().setText(word[4])
                self.update()
                self.status_message.emit("Selection copied to clipboard")
                return

"""Vector icons and the ABNORA logo, drawn programmatically.

Silver-linework-on-dark identity: every icon is painted with QPainter at the
requested size, so there are no binary assets and colors follow the theme.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QLinearGradient


def _painter(pixmap: QPixmap) -> QPainter:
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    return p


def draw_logo(size: int, line: str = "#c8ccd4", bg: str = "#14161a") -> QPixmap:
    """Abstract open book: two curved page halves meeting at a spine."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _painter(pm)
    s = float(size)
    pen = QPen(QColor(line))
    pen.setWidthF(max(1.0, s * 0.045))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if bg and bg != "none":
        p.setBrush(QBrush(QColor(bg)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)
        p.setPen(pen)

    cx = s / 2
    top = s * 0.30
    bot = s * 0.72
    wing = s * 0.30

    # spine
    p.drawLine(QPointF(cx, top), QPointF(cx, bot))

    # left page: outward-curving cover line + two content lines
    left = QPainterPath()
    left.moveTo(cx, top)
    left.cubicTo(cx - wing * 0.6, top - s * 0.05, cx - wing, top + s * 0.02,
                 cx - wing, top + s * 0.10)
    left.lineTo(cx - wing, bot - s * 0.06)
    left.cubicTo(cx - wing, bot + s * 0.02, cx - wing * 0.5, bot - s * 0.02, cx, bot)
    p.drawPath(left)

    right = QPainterPath()
    right.moveTo(cx, top)
    right.cubicTo(cx + wing * 0.6, top - s * 0.05, cx + wing, top + s * 0.02,
                  cx + wing, top + s * 0.10)
    right.lineTo(cx + wing, bot - s * 0.06)
    right.cubicTo(cx + wing, bot + s * 0.02, cx + wing * 0.5, bot - s * 0.02, cx, bot)
    p.drawPath(right)

    # inner page hints
    inner_pen = QPen(QColor(line))
    inner_pen.setWidthF(max(1.0, s * 0.03))
    inner_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(inner_pen)
    for frac in (0.32, 0.50):
        y = top + (bot - top) * frac
        p.drawLine(QPointF(cx - wing * 0.72, y), QPointF(cx - wing * 0.15, y - s * 0.02))
        p.drawLine(QPointF(cx + wing * 0.15, y - s * 0.02), QPointF(cx + wing * 0.72, y))
    p.end()
    return pm


def app_icon(size: int = 64) -> QIcon:
    ic = QIcon()
    for s in (16, 24, 32, 48, 64, 128):
        if s <= size * 2:
            ic.addPixmap(draw_logo(s))
    return ic


# --------------------------------------------------------------- icon set

def _stroke_icon(size: int, color: str, draw) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _painter(pm)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.1, size * 0.085))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw(p, size)
    p.end()
    return QIcon(pm)


def icon(name: str, size: int = 20, color: str = "#c8ccd4") -> QIcon:
    """Return a stroke-style icon by name."""
    return _stroke_icon(size, color, _DRAWERS[name])


def _d_open(p, s):
    u = s / 20.0
    p.drawPolyline([QPointF(3 * u, 16 * u), QPointF(3 * u, 5 * u),
                    QPointF(9 * u, 5 * u), QPointF(9 * u, 16 * u)])
    p.drawPolyline([QPointF(9 * u, 6 * u), QPointF(17 * u, 3 * u),
                    QPointF(17 * u, 14 * u), QPointF(9 * u, 17 * u)])


def _d_search(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(4 * u, 4 * u, 9 * u, 9 * u))
    p.drawLine(QPointF(11 * u, 11 * u), QPointF(16.5 * u, 16.5 * u))


def _d_prev(p, s):
    u = s / 20.0
    p.drawPolyline([QPointF(13 * u, 4 * u), QPointF(7 * u, 10 * u),
                    QPointF(13 * u, 16 * u)])


def _d_next(p, s):
    u = s / 20.0
    p.drawPolyline([QPointF(7 * u, 4 * u), QPointF(13 * u, 10 * u),
                    QPointF(7 * u, 16 * u)])


def _d_zoom_in(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(3.5 * u, 3.5 * u, 9.5 * u, 9.5 * u))
    p.drawLine(QPointF(10.5 * u, 10.5 * u), QPointF(17 * u, 17 * u))
    p.drawLine(QPointF(6 * u, 8.25 * u), QPointF(10.5 * u, 8.25 * u))
    p.drawLine(QPointF(8.25 * u, 6 * u), QPointF(8.25 * u, 10.5 * u))


def _d_zoom_out(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(3.5 * u, 3.5 * u, 9.5 * u, 9.5 * u))
    p.drawLine(QPointF(10.5 * u, 10.5 * u), QPointF(17 * u, 17 * u))
    p.drawLine(QPointF(6 * u, 8.25 * u), QPointF(10.5 * u, 8.25 * u))


def _d_fit_page(p, s):
    u = s / 20.0
    p.drawRect(QRectF(5 * u, 3.5 * u, 10 * u, 13 * u))
    p.drawLine(QPointF(7.5 * u, 7 * u), QPointF(12.5 * u, 7 * u))
    p.drawLine(QPointF(7.5 * u, 10 * u), QPointF(12.5 * u, 10 * u))


def _d_fit_width(p, s):
    u = s / 20.0
    p.drawRect(QRectF(3 * u, 5 * u, 14 * u, 10 * u))
    p.drawLine(QPointF(5.5 * u, 10 * u), QPointF(14.5 * u, 10 * u))
    p.drawPolyline([QPointF(6.5 * u, 8.5 * u), QPointF(5 * u, 10 * u),
                    QPointF(6.5 * u, 11.5 * u)])
    p.drawPolyline([QPointF(13.5 * u, 8.5 * u), QPointF(15 * u, 10 * u),
                    QPointF(13.5 * u, 11.5 * u)])


def _d_fullscreen(p, s):
    u = s / 20.0
    for (x1, y1, x2, y2) in ((4, 8, 4, 4), (4, 4, 8, 4), (12, 4, 16, 4),
                             (16, 4, 16, 8), (16, 12, 16, 16), (16, 16, 12, 16),
                             (8, 16, 4, 16), (4, 16, 4, 12)):
        p.drawLine(QPointF(x1 * u, y1 * u), QPointF(x2 * u, y2 * u))


def _d_layout_single(p, s):
    u = s / 20.0
    p.drawRect(QRectF(6.5 * u, 3.5 * u, 7 * u, 13 * u))


def _d_layout_pair(p, s):
    u = s / 20.0
    p.drawRect(QRectF(2.5 * u, 4.5 * u, 6.75 * u, 11 * u))
    p.drawRect(QRectF(10.75 * u, 4.5 * u, 6.75 * u, 11 * u))


def _d_layout_continuous(p, s):
    u = s / 20.0
    p.drawRect(QRectF(5 * u, 2.5 * u, 10 * u, 6 * u))
    p.drawRect(QRectF(5 * u, 10.5 * u, 10 * u, 6 * u))


def _d_theme(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(3.5 * u, 3.5 * u, 13 * u, 13 * u))
    p.drawEllipse(QRectF(8.5 * u, 3.2 * u, 3 * u, 3 * u))   # holes as circles
    p.drawEllipse(QRectF(12.8 * u, 7.5 * u, 3 * u, 3 * u))
    p.drawEllipse(QRectF(5 * u, 9 * u, 3 * u, 3 * u))


def _d_panel(p, s):
    u = s / 20.0
    p.drawRect(QRectF(3 * u, 4 * u, 14 * u, 12 * u))
    p.drawLine(QPointF(8 * u, 4 * u), QPointF(8 * u, 16 * u))


def _d_bookmark(p, s):
    u = s / 20.0
    path = QPainterPath()
    path.moveTo(6 * u, 3.5 * u)
    path.lineTo(14 * u, 3.5 * u)
    path.lineTo(14 * u, 16.5 * u)
    path.lineTo(10 * u, 13 * u)
    path.lineTo(6 * u, 16.5 * u)
    path.closeSubpath()
    p.drawPath(path)


def _d_bookmark_add(p, s):
    _d_bookmark(p, s)
    u = s / 20.0
    p.drawLine(QPointF(16.5 * u, 4 * u), QPointF(16.5 * u, 9 * u))
    p.drawLine(QPointF(14 * u, 6.5 * u), QPointF(19 * u, 6.5 * u))


def _d_close(p, s):
    u = s / 20.0
    p.drawLine(QPointF(5.5 * u, 5.5 * u), QPointF(14.5 * u, 14.5 * u))
    p.drawLine(QPointF(14.5 * u, 5.5 * u), QPointF(5.5 * u, 14.5 * u))


def _d_outline(p, s):
    u = s / 20.0
    for (x, y) in ((4, 5), (4, 10), (4, 15)):
        p.drawEllipse(QRectF(x * u, y * u, 2 * u, 2 * u))
    for (x1, y, x2) in ((8, 6, 16), (8, 11, 14), (8, 16, 16)):
        p.drawLine(QPointF(x1 * u, y * u), QPointF(x2 * u, y * u))


def _d_thumbnails(p, s):
    u = s / 20.0
    p.drawRect(QRectF(3 * u, 3 * u, 6 * u, 6 * u))
    p.drawRect(QRectF(11 * u, 3 * u, 6 * u, 6 * u))
    p.drawRect(QRectF(3 * u, 11 * u, 6 * u, 6 * u))
    p.drawRect(QRectF(11 * u, 11 * u, 6 * u, 6 * u))


def _d_info(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(3.5 * u, 3.5 * u, 13 * u, 13 * u))
    p.drawLine(QPointF(10 * u, 9 * u), QPointF(10 * u, 14 * u))
    p.drawPoint(QPointF(10 * u, 6.4 * u))


def _d_rotate(p, s):
    u = s / 20.0
    p.drawArc(QRectF(4.5 * u, 4.5 * u, 11 * u, 11 * u), 30 * 16, 250 * 16)
    p.drawPolyline([QPointF(4.2 * u, 4.2 * u), QPointF(4.2 * u, 8.5 * u),
                    QPointF(8.5 * u, 8.5 * u)])


def _d_settings(p, s):
    u = s / 20.0
    p.drawEllipse(QRectF(7 * u, 7 * u, 6 * u, 6 * u))
    import math
    for i in range(8):
        a = math.pi / 4 * i
        x1, y1 = 10 + math.cos(a) * 6.2, 10 + math.sin(a) * 6.2
        x2, y2 = 10 + math.cos(a) * 8.3, 10 + math.sin(a) * 8.3
        p.drawLine(QPointF(x1 * u, y1 * u), QPointF(x2 * u, y2 * u))


_DRAWERS = {
    "open": _d_open,
    "search": _d_search,
    "prev": _d_prev,
    "next": _d_next,
    "zoom-in": _d_zoom_in,
    "zoom-out": _d_zoom_out,
    "fit-page": _d_fit_page,
    "fit-width": _d_fit_width,
    "fullscreen": _d_fullscreen,
    "layout-single": _d_layout_single,
    "layout-pair": _d_layout_pair,
    "layout-continuous": _d_layout_continuous,
    "theme": _d_theme,
    "panel": _d_panel,
    "bookmark": _d_bookmark,
    "bookmark-add": _d_bookmark_add,
    "close": _d_close,
    "outline": _d_outline,
    "thumbnails": _d_thumbnails,
    "info": _d_info,
    "rotate": _d_rotate,
    "settings": _d_settings,
}

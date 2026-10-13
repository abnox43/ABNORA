"""The reading canvas: single, pair (open book), and continuous layouts.

The canvas paints the themed reading surface (walnut, starfield, blueprint
grid... depending on the active theme), arranges real rendered PDF pages on
it, draws the central spine in pair mode, and animates spread changes when
motion is allowed.
"""

from __future__ import annotations

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation,
                            QRectF, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPen, QPolygonF,
                           QPixmap, QBrush)
from PySide6.QtWidgets import (QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
                               QHBoxLayout)

from ..pdf.document import PdfDocument
from ..pdf.navigation import (Layout, SpreadNavigator, clamp_zoom,
                              continuous_page_for_offset, fit_width_zoom,
                              fit_zoom)
from ..pdf.renderer import PdfRenderer
from .page_view import PageView

CANVAS_MARGIN = 26        # px around the open book
GUTTER_WIDTH = 26         # spine width between paired pages


class CanvasBackground(QWidget):
    """Paints the themed surface behind the pages (cheap, no per-frame cost)."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._stars: list[tuple[int, int, int]] = []
        self._texture: QPixmap | None = None
        self._texture_key = None

    def set_theme(self, theme) -> None:
        self._theme = theme
        self._texture = None
        self._texture_key = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        self.paint_into(p, self.rect())
        p.end()

    def paint_into(self, p: QPainter, rect) -> None:
        t = self._theme
        p.fillRect(rect, QColor(t.canvas_bg))
        eff = t.effects
        w, h = rect.width(), rect.height()

        if eff.wood:
            self._paint_wood(p, w, h)
        if eff.grid:
            self._paint_grid(p, w, h)
        if eff.horizon:
            self._paint_horizon(p, w, h)
        if eff.stars:
            self._paint_stars(p, w, h)
        if eff.canvas_texture:
            self._paint_texture(p, w, h)
        if eff.vignette:
            self._paint_vignette(p, w, h)
        p.end()

    # ------------------------------------------------------------- effects

    def _paint_wood(self, p: QPainter, w: int, h: int) -> None:
        base = QColor(self._theme.canvas_bg)
        # vertical warm gradient suggesting a desk surface under a lamp
        g = QLinearGradient(0, 0, 0, h)
        lighter = base.lighter(118)
        darker = base.darker(122)
        g.setColorAt(0.0, darker)
        g.setColorAt(0.45, base)
        g.setColorAt(1.0, darker)
        p.fillRect(self.rect(), g)
        # subtle grain lines
        pen = QPen(lighter)
        pen.setWidth(1)
        p.setPen(pen)
        step = 23
        for x in range(0, w, step):
            p.drawLine(x, 0, x + 6, h)

    def _paint_grid(self, p: QPainter, w: int, h: int) -> None:
        minor = QColor(self._theme.accent)
        minor.setAlpha(26)
        major = QColor(self._theme.accent)
        major.setAlpha(52)
        p.setPen(minor)
        for x in range(0, w, 24):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 24):
            p.drawLine(0, y, w, y)
        p.setPen(major)
        for x in range(0, w, 120):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 120):
            p.drawLine(0, y, w, y)

    def _paint_horizon(self, p: QPainter, w: int, h: int) -> None:
        # receding horizon lines at the bottom, synthwave-style
        horizon_y = int(h * 0.68)
        accent = QColor(self._theme.accent)
        accent.setAlpha(40)
        p.setPen(QPen(accent, 1))
        y = horizon_y
        gap = 6
        while y < h:
            p.drawLine(0, y, w, y)
            gap = int(gap * 1.35)
            y += gap
        glow = QColor(self._theme.accent_hover)
        glow.setAlpha(22)
        p.setPen(QPen(glow, 1))
        for i in range(1, 9):
            x = w // 2 + (i - 4) * w // 4
            p.drawLine(w // 2, horizon_y, x, h)

    def _paint_stars(self, p: QPainter, w: int, h: int) -> None:
        # deterministic starfield, generated once per (theme, size)
        key = (w, h)
        if self._stars and self._texture_key == key:
            stars = self._stars
        else:
            import random
            rng = random.Random(20261013 + w * 7 + h)
            stars = [(rng.randrange(w), rng.randrange(h), rng.choice((1, 1, 1, 2)))
                     for _ in range(max(60, (w * h) // 9000))]
            self._stars = stars
            self._texture_key = key
        accent = QColor(self._theme.accent)
        for (x, y, r) in stars:
            c = QColor(accent)
            c.setAlpha(120 if r == 1 else 200)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawEllipse(x, y, r, r)
        # a few silver stars
        silver = QColor(self._theme.text)
        silver.setAlpha(160)
        p.setBrush(silver)
        import random
        rng = random.Random(99 + w)
        for _ in range(max(8, (w * h) // 60000)):
            x, y = rng.randrange(w), rng.randrange(h)
            p.drawEllipse(x, y, 2, 2)

    def _paint_texture(self, p: QPainter, w: int, h: int) -> None:
        # sparse noise specks, seeded — reads as paper/linen tooth
        import random
        rng = random.Random(4242 + w * 13 + h)
        c = QColor(self._theme.text)
        c.setAlpha(14)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        count = (w * h) // 700
        for _ in range(count):
            p.drawEllipse(rng.randrange(w), rng.randrange(h), 1, 1)

    def _paint_vignette(self, p: QPainter, w: int, h: int) -> None:
        edge = QColor(0, 0, 0, 60) if not self._theme.dark else QColor(0, 0, 0, 90)
        p.setPen(Qt.PenStyle.NoPen)
        band = 70
        for i in range(band):
            a = int(edge.alpha() * (1 - i / band) ** 2)
            c = QColor(edge)
            c.setAlpha(a)
            p.setBrush(c)
            step = max(1, band // 8)
            if i % step:
                continue
            p.drawRect(i, i, w - 2 * i, band)
            p.drawRect(i, h - band + i, w - 2 * i, band)
            p.drawRect(i, i, band, h - 2 * i)
            p.drawRect(w - band + i, i, band, h - 2 * i)


class _CanvasViewport(QWidget):
    """Scroll-area viewport that paints the themed background itself.

    Subclassing (instead of event-filter painting) keeps Qt's paint system
    happy and avoids 'Painter not active' warnings.
    """

    def __init__(self, bg: "CanvasBackground", parent=None):
        super().__init__(parent)
        self._bg = bg
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        self._bg.paint_into(p, self.rect())
        p.end()


class _PagesHost(QWidget):
    """Widget that hosts page views and paints the pair-mode spine."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.spine_visible = False
        self.setObjectName("CanvasContainer")

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self.spine_visible:
            return
        p = QPainter(self)
        t = self._theme
        # find the gap between the two page views
        kids = [c for c in self.findChildren(QWidget) if isinstance(c, PageView)]
        vis = sorted((c for c in kids if c.isVisible()),
                     key=lambda c: c.x())
        if len(vis) >= 2:
            left = vis[0]
            right = vis[1]
            x0 = left.geometry().right()
            x1 = right.geometry().x()
            top = min(left.geometry().top(), right.geometry().top())
            bot = max(left.geometry().bottom(), right.geometry().bottom())
            band = QRectF(x0, top, x1 - x0, bot - top)
            # spine gradient: dark center, lighter edges (page curvature)
            g = QLinearGradient(band.left(), 0, band.right(), 0)
            c0 = QColor(t.spine_color)
            c1 = QColor(t.spine_color).lighter(140)
            g.setColorAt(0.0, QColor(t.page_shadow))
            g.setColorAt(0.28, c1)
            g.setColorAt(0.5, c0)
            g.setColorAt(0.72, c1)
            g.setColorAt(1.0, QColor(t.page_shadow))
            p.fillRect(band, g)
            # inner shadow gradient onto each page edge
            sh = QColor(t.page_shadow)
            for edge_x, direction in ((band.left(), 1), (band.right(), -1)):
                gg = QLinearGradient(edge_x, 0, edge_x + direction * 14, 0)
                sh.setAlpha(110)
                gg.setColorAt(0, sh)
                sh.setAlpha(0)
                gg.setColorAt(1, QColor(sh.red(), sh.green(), sh.blue(), 0))
                p.fillRect(QRectF(min(edge_x, edge_x + direction * 14), band.top(),
                                  14, band.height()), gg)
        p.end()


class ReadingCanvas(QScrollArea):
    """Themed scrollable area presenting the document in the chosen layout."""

    current_page_changed = Signal(int)          # 1-based anchor page
    zoom_changed = Signal(float)
    layout_changed = Signal(str)
    status_message = Signal(str)
    link_activated = Signal(int)                # 0-based page

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.doc: PdfDocument | None = None
        self.renderer: PdfRenderer | None = None
        self.layout_mode = Layout.PAIR
        self.cover_alone = True
        self.current_page = 1
        self.zoom = 1.0
        self._fit_mode = "fit-page"   # fit-page | fit-width | manual
        self._search_rects: dict[int, list] = {}
        self._page_views: list[PageView] = []
        self._anim: QPropertyAnimation | None = None

        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self._bg = CanvasBackground(theme)
        self.setViewport(_CanvasViewport(self._bg))

        self._host = _PagesHost(theme)
        self.setWidget(self._host)
        self._layout = QVBoxLayout(self._host)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._row = QHBoxLayout()
        self._vcol = QVBoxLayout()
        self._vcol.setSpacing(18)
        self._layout.addStretch(1)
        self._layout.addLayout(self._row)
        self._layout.addLayout(self._vcol)
        self._layout.addStretch(1)
        self._vcol.addStretch(1)

        self._prefetch_timer = QTimer(self)
        self._prefetch_timer.setSingleShot(True)
        self._prefetch_timer.setInterval(120)
        self._prefetch_timer.timeout.connect(self._prefetch_neighbors)

    # ------------------------------------------------------ viewport paint

    # ------------------------------------------------------------ settings

    def set_theme(self, theme) -> None:
        self._theme = theme
        self._bg.set_theme(theme)
        self._host.set_theme(theme)
        for v in self._page_views:
            v.set_theme(theme)
        self.viewport().update()

    def set_renderer(self, renderer: PdfRenderer) -> None:
        self.renderer = renderer
        renderer.page_ready.connect(self._on_page_ready)

    def set_document(self, doc: PdfDocument | None) -> None:
        self.doc = doc
        self.current_page = 1
        self._search_rects = {}
        self._clear_views()
        if doc is not None:
            self.rebuild()

    def set_layout_mode(self, mode: Layout | str) -> None:
        mode = Layout(mode) if isinstance(mode, str) else mode
        if mode == self.layout_mode and self._page_views:
            return
        self.layout_mode = mode
        self._fit_mode = "fit-width" if mode == Layout.CONTINUOUS else "fit-page"
        if self.doc is not None:
            self.rebuild()
        self.layout_changed.emit(mode.value)

    def set_cover_alone(self, on: bool) -> None:
        if on != self.cover_alone:
            self.cover_alone = on
            if self.doc is not None and self.layout_mode == Layout.PAIR:
                self.rebuild()

    # ------------------------------------------------------------- rebuild

    def _navigator(self) -> SpreadNavigator:
        assert self.doc is not None
        return SpreadNavigator(self.doc.page_count, self.layout_mode,
                               self.cover_alone)

    def _clear_views(self) -> None:
        for v in self._page_views:
            v.setParent(None)
            v.deleteLater()
        self._page_views.clear()

    def _effective_zoom_for_width(self, page_w: float) -> float:
        avail = self.viewport().width() - 2 * CANVAS_MARGIN
        if self.layout_mode == Layout.PAIR:
            avail = (avail - GUTTER_WIDTH) / 2.0
        return clamp_zoom(fit_width_zoom(page_w, avail))

    def _spread_total_width_pt(self) -> float:
        """Sum of rotated page widths in the current views (pair mode)."""
        if not self._page_views or self.doc is None:
            return 595.0
        return sum(self.doc.rotated_page_size(v.page_index)[0]
                   for v in self._page_views)

    def rebuild(self) -> None:
        if self.doc is None:
            return
        self._clear_views()
        nav = self._navigator()
        if self.layout_mode == Layout.CONTINUOUS:
            self._rebuild_continuous()
        else:
            spread = nav.spread_for_page(self.current_page)
            if self.layout_mode == Layout.PAIR:
                self._host.spine_visible = len(spread.pages) == 2
            else:
                self._host.spine_visible = False
            for page in spread.pages:
                self._add_page_view(page - 1)
            self._apply_zoom_to_views()
        self._relayout_row()
        self.apply_search_highlights()
        self._prefetch_timer.start()

    def _rebuild_continuous(self) -> None:
        # one view per page, stacked; zoom fit-width (or manual)
        count = self.doc.page_count
        # cap initially built views for huge documents: build lazily via timer
        self._continuous_total = count
        self._continuous_built = 0
        self._build_continuous_chunk(0, min(count, 40))

    def _build_continuous_chunk(self, start: int, end: int) -> None:
        for i in range(start, end):
            v = self._add_page_view(i, continuous=True)
        self._apply_zoom_to_views()
        self._relayout_row()
        self._continuous_built = end

    def maybe_extend_continuous(self) -> None:
        """Extend the continuous layout with more pages near the viewport end."""
        if self.layout_mode != Layout.CONTINUOUS or self.doc is None:
            return
        total = getattr(self, "_continuous_total", 0)
        built = getattr(self, "_continuous_built", 0)
        if built < total:
            self._build_continuous_chunk(built, min(total, built + 40))

    def _add_page_view(self, page_index: int, continuous: bool = False) -> PageView:
        v = PageView(self.doc, page_index, self.renderer, self._theme)
        v.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        v.link_activated.connect(self._on_link)
        v.status_message.connect(self.status_message.emit)
        if continuous:
            self._row.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
        else:
            self._row.addWidget(v)
        self._page_views.append(v)
        return v

    def _relayout_row(self) -> None:
        # Clear both containers; widgets stay parented to the host.
        while self._row.count():
            self._row.takeAt(0)
        while self._vcol.count():
            self._vcol.takeAt(0)
        if self.layout_mode == Layout.CONTINUOUS:
            # single column, fit-width; extra space pushed to the bottom
            for v in self._page_views:
                self._vcol.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
            self._vcol.addStretch(1)
        else:
            single_in_pair = (self.layout_mode == Layout.PAIR
                              and len(self._page_views) == 1)
            if single_in_pair:
                # a lone page (cover or tail) sits on the right like a real book
                self._row.addStretch(2)
                self._row.addWidget(self._page_views[0], 0)
                self._row.addStretch(3)
            else:
                self._row.addStretch(1)
                for i, v in enumerate(self._page_views):
                    if i:
                        # gutter between paired pages; the spine is painted here
                        self._row.addSpacing(GUTTER_WIDTH)
                    self._row.addWidget(v, 0)
                self._row.addStretch(1)
        self._layout.activate()
        self._host.updateGeometry()

    # ---------------------------------------------------------------- zoom

    def _apply_zoom_to_views(self) -> None:
        if self.doc is None:
            return
        if self.layout_mode == Layout.CONTINUOUS:
            w_pt = max(self.doc.page_size(v.page_index)[0]
                       for v in self._page_views) if self._page_views else 595.0
            self.zoom = clamp_zoom(self._effective_zoom_for_width(w_pt))
        elif self._fit_mode == "fit-page":
            self.zoom = self._compute_fit_page_zoom()
        elif self._fit_mode == "fit-width":
            if self.layout_mode == Layout.PAIR and len(self._page_views) >= 2:
                # fit the whole spread's width
                avail = self.viewport().width() - 2 * CANVAS_MARGIN - GUTTER_WIDTH
                self.zoom = clamp_zoom(avail / max(1.0, self._spread_total_width_pt()))
            else:
                w_pt = self.doc.rotated_page_size(self._page_views[0].page_index)[0] \
                    if self._page_views else 595.0
                self.zoom = clamp_zoom(self._effective_zoom_for_width(w_pt))
        self.zoom = clamp_zoom(self.zoom)
        step = self.zoom
        for v in self._page_views:
            v.set_step(step)
        self.zoom_changed.emit(self.zoom)

    def _compute_fit_page_zoom(self) -> float:
        assert self.doc is not None and self._page_views
        avail_w = self.viewport().width() - 2 * CANVAS_MARGIN
        avail_h = self.viewport().height() - 2 * CANVAS_MARGIN
        if self.layout_mode == Layout.PAIR and len(self._page_views) >= 2:
            avail_w = max(1.0, avail_w - GUTTER_WIDTH)
            # fit width by the total spread width, height by the tallest page
            width_fit = avail_w / max(1.0, self._spread_total_width_pt())
            height_fit = min(
                avail_h / max(1.0, self.doc.rotated_page_size(v.page_index)[1])
                for v in self._page_views)
            return clamp_zoom(min(width_fit, height_fit))
        w_pt, h_pt = self.doc.rotated_page_size(self._page_views[0].page_index)
        return clamp_zoom(fit_zoom(w_pt, h_pt, avail_w, avail_h))

    def set_zoom(self, zoom: float, manual: bool = True) -> None:
        if manual:
            self._fit_mode = "manual"
        self.zoom = clamp_zoom(zoom)
        for v in self._page_views:
            v.set_step(self.zoom)
        self.zoom_changed.emit(self.zoom)
        self._prefetch_timer.start()

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom * 1.2)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom / 1.2)

    def fit_page(self) -> None:
        self._fit_mode = "fit-page"
        self._apply_zoom_to_views()

    def fit_width(self) -> None:
        self._fit_mode = "fit-width"
        self._apply_zoom_to_views()

    @property
    def fit_mode(self) -> str:
        return self._fit_mode

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.doc is not None and self._fit_mode in ("fit-page", "fit-width"):
            self._apply_zoom_to_views()
            if self.layout_mode in (Layout.SINGLE, Layout.PAIR):
                self.rebuild()
        self.viewport().update()

    # ---------------------------------------------------------- navigation

    def show_page(self, page: int, animate: bool = True) -> None:
        if self.doc is None:
            return
        page = max(1, min(page, self.doc.page_count))
        self.current_page = page
        if self.layout_mode == Layout.CONTINUOUS:
            self._scroll_to_page(page, animate)
        else:
            self.rebuild()
            if animate:
                self._animate_reveal()
        self._prefetch_timer.start()
        self.current_page_changed.emit(page)

    def next_page(self) -> None:
        if self.doc is None:
            return
        nav = self._navigator()
        if self.layout_mode == Layout.CONTINUOUS:
            self.show_page(self.current_page + 1)
        else:
            i = nav.spread_index_for_page(self.current_page)
            if i + 1 < nav.spread_count:
                self.show_page(nav.spread(i + 1).first_page)

    def prev_page(self) -> None:
        if self.doc is None:
            return
        nav = self._navigator()
        if self.layout_mode == Layout.CONTINUOUS:
            self.show_page(self.current_page - 1)
        else:
            i = nav.spread_index_for_page(self.current_page)
            if i > 0:
                self.show_page(nav.spread(i - 1).first_page)

    def first_page(self) -> None:
        self.show_page(1)

    def last_page(self) -> None:
        if self.doc:
            self.show_page(self.doc.page_count)

    def _scroll_to_page(self, page: int, animate: bool) -> None:
        for v in self._page_views:
            if v.page_index == page - 1:
                bar = self.verticalScrollBar()
                target = max(0, v.mapTo(self._host, v.rect().topLeft()).y() - 12)
                if animate and not self._theme_motion_disabled():
                    anim = QPropertyAnimation(bar, b"value", self)
                    anim.setDuration(180)
                    anim.setStartValue(bar.value())
                    anim.setEndValue(target)
                    anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
                else:
                    bar.setValue(target)
                return

    # ------------------------------------------------------------ animation

    def _theme_motion_disabled(self) -> bool:
        return bool(getattr(self, "_reduced_motion", False))

    def set_reduced_motion(self, on: bool) -> None:
        self._reduced_motion = bool(on)

    def _animate_reveal(self) -> None:
        if self._theme_motion_disabled():
            return
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        eff = QGraphicsOpacityEffect(self._host)
        self._host.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _cleanup():
            self._host.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim = anim

    # ------------------------------------------------------------- signals

    def _on_link(self, target_page: int) -> None:
        self.link_activated.emit(target_page)
        self.show_page(target_page + 1)

    def _on_page_ready(self, path: str, page: int, step: float, img) -> None:
        if self.doc is None or path != self.doc.path:
            return
        for v in self._page_views:
            if v.page_index == page:
                v.on_render_ready(path, page, step, img)

    def _prefetch_neighbors(self) -> None:
        if self.doc is None or self.renderer is None:
            return
        nav = self._navigator()
        idx = nav.spread_index_for_page(self.current_page)
        pages: list[int] = []
        for di in (1, 2):
            sp = nav.spread(min(idx + di, nav.spread_count - 1))
            pages.extend(p - 1 for p in sp.pages)
            sp = nav.spread(max(idx - di, 0))
            pages.extend(p - 1 for p in sp.pages)
        rot = self.doc.rotation(max(0, self.current_page - 1))
        self.renderer.prefetch(self.doc, pages, self.zoom, rot)

    # ------------------------------------------------------------- search

    def set_search_highlights(self, rects_by_page: dict[int, list]) -> None:
        """rects_by_page: 1-based page -> list of (x0,y0,x1,y1) in PDF points."""
        self._search_rects = dict(rects_by_page)
        self.apply_search_highlights()

    def apply_search_highlights(self) -> None:
        for v in self._page_views:
            v.set_search_rects(self._search_rects.get(v.page_index + 1, []))

    def clear_search_highlights(self) -> None:
        self._search_rects = {}
        self.apply_search_highlights()

    # ---------------------------------------------------------- continuous

    def scrollEvent(self, event) -> None:  # noqa: N802
        super().scrollEvent(event)
        if self.layout_mode == Layout.CONTINUOUS and self.doc is not None:
            self.maybe_extend_continuous()
            # update current page from scroll position
            offsets = []
            for v in self._page_views:
                top = v.mapTo(self._host, v.rect().topLeft()).y()
                offsets.append((v.page_index + 1, float(top), float(v.height())))
            y = self.verticalScrollBar().value() + self.viewport().height() * 0.3
            page = continuous_page_for_offset(offsets, y)
            if page != self.current_page:
                self.current_page = page
                self.current_page_changed.emit(page)
            self._prefetch_timer.start()

    # ---------------------------------------------------------- selection

    def clear_page_selections(self) -> None:
        for v in self._page_views:
            v.clear_selection()

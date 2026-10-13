"""On-demand page rendering with a bounded cache and worker threads.

PyMuPDF renders pages to Pixmaps; we convert them to QImage/QPixmap on a
worker thread and hand them to the UI through Qt signals. The main-thread
document handle is never touched by workers — each worker leases its own
fitz handle (see PdfDocument.worker_handle).
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage

import pymupdf

from .document import PdfDocument

RENDER_CACHE_MAX = 48
ZOOM_STEPS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0)


def zoom_to_step(zoom: float) -> float:
    """Quantize a zoom factor to a cache-friendly step.

    Nearby zoom requests (e.g. fit-width results) snap to a shared step so
    pages re-use cached renders. The quantization is coarse only at high
    zooms; text stays crisp because renders happen at the snapped resolution
    requested by the view.
    """
    if zoom <= 0:
        return 1.0
    best = min(ZOOM_STEPS, key=lambda s: abs(s - zoom))
    return best


class RenderCache:
    """Bounded LRU cache of rendered pages, keyed by document generation."""

    def __init__(self, max_entries: int = RENDER_CACHE_MAX):
        self._max = max_entries
        self._data: OrderedDict[tuple, QImage] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: tuple) -> QImage | None:
        img = self._data.get(key)
        if img is None:
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return img

    def put(self, key: tuple, image: QImage) -> None:
        self._data[key] = image
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def invalidate_document(self, path: str) -> None:
        """Drop every cached page belonging to `path`."""
        for k in [k for k in self._data if k[0] == path]:
            del self._data[k]

    def invalidate_zoom(self, path: str) -> None:
        """Drop stale renders of `path` made at other zoom levels."""
        self.invalidate_document(path)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    @staticmethod
    def key(doc: PdfDocument, page: int, step: float, rotation: int) -> tuple:
        return (doc.path, doc.generation, page, round(step, 3), rotation % 360)


def _pixmap_to_qimage(pix: pymupdf.Pixmap) -> QImage:
    if pix.n - pix.alpha < 3:  # grayscale or palette
        pix = pix.convert(pymupdf.csRGB)
    fmt = QImage.Format.Format_RGB888 if pix.alpha == 0 else QImage.Format.Format_ARGB32
    if fmt == QImage.Format.Format_ARGB32:
        # PyMuPDF RGBA bytes -> Qt ARGB32 (premultiplied off; straight alpha)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                     QImage.Format.Format_RGBA8888)
        return img.copy().convertToFormat(QImage.Format.Format_ARGB32)
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    return img.copy()


class _RenderTask(QRunnable):
    """Render one page on a worker thread."""

    def __init__(self, doc: PdfDocument, page: int, step: float,
                 rotation: int, priority: int = 0):
        super().__init__()
        self.doc = doc
        self.page = page
        self.step = step
        self.rotation = rotation % 360
        self.priority = priority
        self.key = RenderCache.key(doc, page, step, rotation)
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            handle = self.doc.worker_handle()
            page_obj = handle[self.page]
            current = page_obj.rotation % 360
            if current != self.rotation:
                page_obj.set_rotation(self.rotation)
            mat = pymupdf.Matrix(self.step, self.step)
            pix = page_obj.get_pixmap(matrix=mat, alpha=False)
            img = _pixmap_to_qimage(pix)
            self.on_done(img, None)
        except Exception as e:  # noqa: BLE001 - worker must never crash the app
            self.on_done(None, e)

    # assigned by the renderer before submission
    on_done: Callable = staticmethod(lambda img, err: None)


class _SearchTask(QRunnable):
    """Search all pages for a term on a worker thread."""

    def __init__(self, doc: PdfDocument, term: str, token: int):
        super().__init__()
        self.doc = doc
        self.term = term
        self.token = token
        self.cancelled = False
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            handle = self.doc.worker_handle()
            results: list[tuple[int, list[tuple[float, float, float, float]]]] = []
            per_page: list[int] = []
            has_text = False
            total = handle.page_count
            for i in range(total):
                if self.cancelled:
                    return
                page = handle[i]
                try:
                    text = page.get_text("text")
                except Exception:  # noqa: BLE001
                    text = ""
                if text.strip():
                    has_text = True
                rects = page.search_for(self.term)
                if rects:
                    results.append((i, [(r.x0, r.y0, r.x1, r.y1) for r in rects]))
                    per_page.append(len(rects))
                if i % 10 == 0:
                    self.on_progress(i, total)
            if not self.cancelled:
                self.on_done(results, per_page, has_text, None)
        except Exception as e:  # noqa: BLE001
            if not self.cancelled:
                self.on_done([], [], False, e)

    on_progress: Callable = staticmethod(lambda done, total: None)
    on_done: Callable = staticmethod(lambda results, counts, has_text, err: None)


class PdfRenderer(QObject):
    """Facade the UI talks to. Owns the thread pool and the render cache."""

    page_ready = Signal(str, int, float, object)   # path, page, step, QImage
    page_failed = Signal(str, int, str)           # path, page, error
    search_progress = Signal(int, int)            # done pages, total
    search_finished = Signal(int, list, list, bool, object)  # token, results, counts, has_text, err

    def __init__(self, pool: QThreadPool | None = None, cache: RenderCache | None = None):
        super().__init__()
        self._pool = pool or QThreadPool.globalInstance()
        self.cache = cache or RenderCache()
        self._inflight: set[tuple] = set()
        self._search_task: _SearchTask | None = None
        self._search_token = 0

    # ------------------------------------------------------------- rendering

    def request_page(self, doc: PdfDocument, page: int, zoom: float,
                     rotation: int, priority: int = 0, step: float | None = None) -> QImage | None:
        """Return a cached render or schedule one. Returns cached QImage or None."""
        if not (0 <= page < doc.page_count):
            return None
        use_step = step if step is not None else zoom_to_step(zoom)
        key = RenderCache.key(doc, page, use_step, rotation)
        cached = self.cache.get(key)
        if cached is not None:
            if key not in self._inflight:
                self.page_ready.emit(doc.path, page, use_step, cached)
            return cached
        if key in self._inflight:
            return None
        self._inflight.add(key)

        task = _RenderTask(doc, page, use_step, rotation, priority)

        def _done(img, err, _key=key, _page=page, _path=doc.path, _step=use_step):
            # runs on the worker thread; marshal to UI thread via signal
            self._inflight.discard(_key)
            if img is not None and not img.isNull():
                self.cache.put(_key, img)
                self.page_ready.emit(_path, _page, _step, img)
            else:
                self.page_failed.emit(_path, _page, str(err) if err else "render failed")

        task.on_done = _done
        self._pool.start(task)
        return None

    def invalidate(self, path: str | None = None) -> None:
        if path is None:
            self.cache.clear()
        else:
            self.cache.invalidate_document(path)

    def cancel_document(self, path: str) -> None:
        """Cancel in-flight search and drop cached pages for a closed document."""
        self.cancel_search()
        self.cache.invalidate_document(path)

    # --------------------------------------------------------------- search

    def search(self, doc: PdfDocument, term: str) -> int:
        """Start a document-wide search; returns a token identifying it."""
        self.cancel_search()
        self._search_token += 1
        token = self._search_token
        task = _SearchTask(doc, term, token)

        def _progress(done, total, _token=token):
            if _token == self._search_token:
                self.search_progress.emit(done, total)

        def _done(results, counts, has_text, err, _token=token):
            if _token == self._search_token:
                self.search_finished.emit(_token, results, counts, has_text, err)

        task.on_progress = _progress
        task.on_done = _done
        self._search_task = task
        self._pool.start(task)
        return token

    def cancel_search(self) -> None:
        if self._search_task is not None:
            self._search_task.cancelled = True
            self._search_task = None

    # ------------------------------------------------------------ thumbnails

    def request_thumbnail(self, doc: PdfDocument, page: int, width_px: int = 120) -> None:
        """Render a small thumbnail; delivered through page_ready with step<1."""
        size = doc.page_size(page)
        step = width_px / max(size[0], 1.0)
        step = max(0.05, min(step, 1.0))
        self.request_page(doc, page, step, doc.rotation(page), step=step)

    def prefetch(self, doc: PdfDocument, pages: list[int], zoom: float, rotation: int) -> None:
        """Schedule renders for a set of pages at low priority."""
        for p in pages:
            if 0 <= p < doc.page_count:
                self.request_page(doc, p, zoom, rotation, priority=1)

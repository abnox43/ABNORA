"""Rendering cache: bounds, zoom invalidation, rotation keys, real renders."""

import pytest

from abnora.pdf.document import PdfDocument
from abnora.pdf.renderer import (PdfRenderer, RenderCache, zoom_to_step)


@pytest.fixture()
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _img():
    from PySide6.QtGui import QImage
    return QImage(4, 4, QImage.Format.Format_RGB888)


def test_cache_put_get():
    c = RenderCache(max_entries=4)
    img = _img()
    c.put(("a.pdf", 1, 0, 1.0, 0), img)
    assert c.get(("a.pdf", 1, 0, 1.0, 0)) is img
    assert c.get(("a.pdf", 1, 0, 2.0, 0)) is None    # different zoom -> miss


def test_cache_bounded():
    c = RenderCache(max_entries=3)
    for i in range(6):
        c.put(("a.pdf", 1, i, 1.0, 0), _img())
    assert len(c) == 3
    # oldest entries evicted
    assert c.get(("a.pdf", 1, 0, 1.0, 0)) is None
    assert c.get(("a.pdf", 1, 5, 1.0, 0)) is not None


def test_cache_lru_order():
    c = RenderCache(max_entries=2)
    c.put(("a.pdf", 1, 0, 1.0, 0), _img())
    c.put(("a.pdf", 1, 1, 1.0, 0), _img())
    c.get(("a.pdf", 1, 0, 1.0, 0))     # refresh entry 0
    c.put(("a.pdf", 1, 2, 1.0, 0), _img())
    assert c.get(("a.pdf", 1, 0, 1.0, 0)) is not None   # was refreshed
    assert c.get(("a.pdf", 1, 1, 1.0, 0)) is None       # evicted


def test_cache_invalidate_document():
    c = RenderCache()
    c.put(("a.pdf", 1, 0, 1.0, 0), _img())
    c.put(("b.pdf", 1, 0, 1.0, 0), _img())
    c.invalidate_document("a.pdf")
    assert c.get(("a.pdf", 1, 0, 1.0, 0)) is None
    assert c.get(("b.pdf", 1, 0, 1.0, 0)) is not None


def test_cache_invalidate_on_zoom_change():
    """After zoom changes, stale renders must not satisfy new requests."""
    c = RenderCache()
    key_old = ("a.pdf", 1, 0, 1.0, 0)
    c.put(key_old, _img())
    assert c.get(key_old) is not None
    # a zoom change for this document drops its cached pages
    c.invalidate_zoom("a.pdf")
    assert c.get(key_old) is None
    assert len(c) == 0


def test_generation_changes_invalidate_keys(simple_pdf):
    doc = PdfDocument(str(simple_pdf))
    k1 = RenderCache.key(doc, 0, 1.0, 0)
    doc.close()
    # closing bumps the generation on this instance, so any key computed
    # afterwards (and any in-flight render keyed on the old generation)
    # no longer collides with the cache
    assert doc.generation != k1[1]
    doc2 = PdfDocument(str(simple_pdf))
    k2 = RenderCache.key(doc2, 0, 1.0, 0)
    assert k2[1] == 1
    doc2.close()


def test_zoom_to_step():
    assert zoom_to_step(1.0) == 1.0
    assert zoom_to_step(1.1) == 1.0
    assert zoom_to_step(1.4) == 1.5
    assert zoom_to_step(0) == 1.0


def test_real_render(qapp, simple_pdf):
    """request_page renders actual page pixels via a worker thread."""
    from PySide6.QtCore import QEventLoop, QTimer
    doc = PdfDocument(str(simple_pdf))
    r = PdfRenderer()
    got = {}
    loop = QEventLoop()

    def on_ready(path, page, step, img):
        got["img"] = img
        loop.quit()

    r.page_ready.connect(on_ready)
    cached = r.request_page(doc, 0, 1.0, 0)
    assert cached is None      # not rendered yet
    QTimer.singleShot(8000, loop.quit)
    loop.exec()
    r.page_ready.disconnect(on_ready)
    assert "img" in got, "render did not complete"
    img = got["img"]
    assert not img.isNull()
    # 595x842pt page at zoom 1.0 -> 595x842 px
    assert img.width() == 595
    assert img.height() == 842
    # second request is served from cache synchronously
    cached = r.request_page(doc, 0, 1.0, 0)
    assert cached is not None
    doc.close()


def test_render_out_of_range(simple_pdf):
    doc = PdfDocument(str(simple_pdf))
    r = PdfRenderer()
    assert r.request_page(doc, 99, 1.0, 0) is None
    doc.close()


def test_mixed_sizes_render(qapp, mixed_pdf):
    from PySide6.QtCore import QEventLoop, QTimer
    doc = PdfDocument(str(mixed_pdf))
    r = PdfRenderer()
    sizes = {}
    loop = QEventLoop()

    def on_ready(path, page, step, img):
        sizes[page] = (img.width(), img.height())
        if len(sizes) == 3:
            loop.quit()

    r.page_ready.connect(on_ready)
    for i in range(3):
        r.request_page(doc, i, 1.0, 0)
    QTimer.singleShot(8000, loop.quit)
    loop.exec()
    assert sizes[0] == (595, 842)
    assert sizes[1] == (842, 595)
    assert sizes[2] == (400, 400)
    doc.close()


def test_render_with_rotation(qapp, simple_pdf):
    from PySide6.QtCore import QEventLoop, QTimer
    doc = PdfDocument(str(simple_pdf))
    r = PdfRenderer()
    got = {}
    loop = QEventLoop()

    def on_ready(path, page, step, img):
        got["size"] = (img.width(), img.height())
        loop.quit()

    r.page_ready.connect(on_ready)
    r.request_page(doc, 0, 1.0, 90)
    QTimer.singleShot(8000, loop.quit)
    loop.exec()
    assert got["size"] == (842, 595)     # swapped by rotation
    doc.close()

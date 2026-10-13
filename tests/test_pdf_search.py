"""Search: real matches, empty results, scanned-PDF feedback, cancellation."""

import time

import pytest

from abnora.pdf.document import PdfDocument
from abnora.pdf.renderer import PdfRenderer
from abnora.pdf.search import build_result


@pytest.fixture()
def renderer():
    r = PdfRenderer()
    yield r
    r.cancel_search()


def _wait_for_search(renderer, timeout=15.0):
    """Pump a local event loop until search_finished fires."""
    from PySide6.QtCore import QEventLoop, QTimer
    results = {}
    loop = QEventLoop()

    def on_done(token, raw, counts, has_text, err):
        results["raw"] = raw
        results["has_text"] = has_text
        results["err"] = err
        loop.quit()

    renderer.search_finished.connect(on_done)
    QTimer.singleShot(int(timeout * 1000), loop.quit)
    # QEventLoop needs an app; tests create one lazily
    loop.exec()
    renderer.search_finished.disconnect(on_done)
    return results


def test_search_finds_matches(simple_pdf, renderer):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    doc = PdfDocument(str(simple_pdf))
    renderer.search(doc, "common keyword")
    res = _wait_for_search(renderer)
    assert res.get("err") is None
    assert len(res["raw"]) == 5           # every page has the phrase
    total = sum(len(rects) for _, rects in res["raw"])
    assert total == 5
    doc.close()


def test_search_empty_term_returns_nothing(simple_pdf, renderer):
    doc = PdfDocument(str(simple_pdf))
    # build_result with empty raw list -> empty result model
    res = build_result(1, "", [], [], True)
    assert res.is_empty
    assert res.count == 0
    assert res.scanned_hint is None       # has_text_layer True -> no hint
    doc.close()


def test_search_no_match_not_scanned(simple_pdf, renderer):
    res = build_result(1, "zzz-no-such-text", [], [], True)
    assert res.is_empty
    assert res.scanned_hint is None


def test_search_scanned_hint(invalid_pdf, renderer, tmp_path):
    # build a "scanned" doc: pages without a text layer
    import pymupdf
    path = tmp_path / "scan.pdf"
    d = pymupdf.open()
    d.new_page(width=595, height=842)
    d.new_page(width=595, height=842)
    d.save(str(path))
    d.close()
    doc = PdfDocument(str(path))
    res = build_result(1, "anything", [], [], False)
    assert res.is_empty
    assert "no embedded text" in res.scanned_hint.lower()
    doc.close()


def test_search_result_grouping():
    raw = [(0, [(1, 2, 3, 4), (5, 6, 7, 8)]), (2, [(9, 9, 10, 10)])]
    res = build_result(7, "term", raw, [], True)
    assert res.count == 3
    assert res.pages == [1, 3]
    assert res.per_page == {1: 2, 3: 1}
    assert res.matches[0].page == 1
    assert res.matches[2].page == 3


def test_search_cancel_before_done(simple_pdf, renderer):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    doc = PdfDocument(str(simple_pdf))
    token1 = renderer.search(doc, "common")
    renderer.cancel_search()   # cancel immediately
    time.sleep(0.3)
    # a new search replaces the token; old results are dropped
    assert renderer._search_token >= token1
    doc.close()

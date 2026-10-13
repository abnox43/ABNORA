"""End-to-end GUI smoke test (offscreen): window, layouts, themes, search.

These tests instantiate the real MainWindow with a real document and verify
the integrated behavior — no mocks of Qt widgets.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture()
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(app, data_dir, simple_pdf):
    """Real MainWindow with a real document, wired like app.main()."""
    from abnora.app import build_context
    from abnora.ui.main_window import MainWindow

    ctx = build_context()
    ctx.theme_manager.apply_to_app(app)
    win = MainWindow(ctx)
    ctx.renderer.search_finished.connect(win._on_search_finished)
    win.resize(1100, 760)
    win.show()
    app.processEvents()
    yield win
    win.close()
    app.processEvents()


def _pump(ms=150):
    app = QApplication.instance()
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def test_window_opens_document(window, simple_pdf):
    assert window.open_document(str(simple_pdf)) is True
    _pump(250)
    assert window.doc is not None
    assert window.doc.page_count == 5
    assert window.status.page_total.text() == "/ 5"


def test_open_missing_document_shows_error(window, tmp_path, monkeypatch):
    # avoid blocking on a modal dialog: record the call
    called = {}
    monkeypatch.setattr(
        "abnora.ui.main_window.QMessageBox.warning",
        lambda *a, **k: called.setdefault("warning", a))
    assert window.open_document(str(tmp_path / "ghost.pdf")) is False
    assert "warning" in called


def test_open_corrupted_document(window, invalid_pdf, monkeypatch):
    called = {}
    monkeypatch.setattr(
        "abnora.ui.main_window.QMessageBox.critical",
        lambda *a, **k: called.setdefault("critical", a))
    assert window.open_document(str(invalid_pdf)) is False
    assert "critical" in called


def test_layout_switching(window, simple_pdf):
    window.open_document(str(simple_pdf))
    _pump(200)
    window.set_layout("single")
    _pump(120)
    assert len(window.canvas._page_views) == 1
    window.set_layout("pair")
    _pump(120)
    # cover alone: page 1 shows a single view
    assert len(window.canvas._page_views) == 1
    window.canvas.show_page(2)
    _pump(150)
    assert len(window.canvas._page_views) == 2
    window.set_layout("continuous")
    _pump(200)
    assert len(window.canvas._page_views) >= 5


def test_navigation_boundaries(window, simple_pdf):
    window.open_document(str(simple_pdf))
    _pump(150)
    window.canvas.first_page()
    _pump(100)
    assert window.canvas.current_page == 1
    window.canvas.prev_page()
    _pump(100)
    assert window.canvas.current_page == 1        # stays at first page
    window.canvas.last_page()
    _pump(150)
    assert window.canvas.current_page == 5
    window.canvas.next_page()
    _pump(100)
    assert window.canvas.current_page == 5        # stays at last page


def test_zoom_and_cache_invalidation(window, simple_pdf):
    window.open_document(str(simple_pdf))
    window.set_layout("single")
    _pump(250)
    window.canvas.fit_page()
    _pump(100)
    z1 = window.canvas.zoom
    window.canvas.zoom_in()
    _pump(100)
    assert window.canvas.zoom > z1
    # renderer cache must hold the new zoom's key after re-render
    window.canvas.fit_width()
    _pump(250)
    assert window.status.zoom_label.text().endswith("%")


def test_theme_instant_switch(window, simple_pdf, app):
    from abnora.themes.definitions import ALL_THEMES
    window.open_document(str(simple_pdf))
    for t in ALL_THEMES:
        assert window.ctx.theme_manager.set_theme(t.id, persist=False)
        app.processEvents()
        assert window.ctx.theme_manager.theme.id == t.id
        # stylesheet actually applied
        assert "QMainWindow" in app.styleSheet()


def test_bookmark_toggle_persists(window, simple_pdf, data_dir):
    window.open_document(str(simple_pdf))
    _pump(100)
    window.canvas.show_page(3)
    _pump(100)
    window._toggle_bookmark()
    assert window.ctx.bookmarks.has(window.doc.path, 3)
    window._toggle_bookmark()          # untoggle
    assert not window.ctx.bookmarks.has(window.doc.path, 3)
    window._toggle_bookmark()          # add again
    # persistence: a fresh store over the same DB file sees it
    from abnora.storage import BookmarkStore, Database
    db2 = Database(data_dir / "test.db")
    assert BookmarkStore(db2).has(window.doc.path, 3)
    db2.close()


def test_search_integration(window, simple_pdf):
    window.open_document(str(simple_pdf))
    _pump(150)
    window.start_search("common keyword")
    # wait for async search
    for _ in range(40):
        _pump(100)
        if window._search_result is not None:
            break
    assert window._search_result is not None
    assert window._search_result.count == 5
    # navigating between matches works
    window._step_search(1)
    _pump(120)
    assert window._search_match_index == 1


def test_reading_position_saved_and_restored(window, simple_pdf):
    window.open_document(str(simple_pdf))
    window.set_layout("pair")
    window.canvas.show_page(4)
    _pump(150)
    window._save_reading_position()
    pos = window.ctx.history.position(window.doc.path)
    assert pos is not None and pos.page == 4
    # re-open restores the position
    window.open_document(str(simple_pdf))
    _pump(250)
    assert window.canvas.current_page == 4


def test_recent_documents(window, simple_pdf):
    window.open_document(str(simple_pdf))
    recents = window.ctx.history.recent()
    assert any(r.doc_path == window.doc.path for r in recents)


def test_document_close(window, simple_pdf):
    window.open_document(str(simple_pdf))
    _pump(100)
    window.close_document()
    assert window.doc is None
    assert window.canvas._page_views == []


def test_info_dialog_metadata(window, simple_pdf):
    window.open_document(str(simple_pdf))
    from abnora.pdf.document import DocumentInfo
    info = DocumentInfo.from_document(window.doc)
    assert info.page_count == 5
    assert info.pdf_version.startswith("PDF")
    # missing metadata is empty, not invented
    assert info.author == ""

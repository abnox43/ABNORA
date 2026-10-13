"""Main application window: toolbar, side panel, canvas, status bar.

Wires the PDF engine, theme system, and storage together; owns document
lifecycle (open/close/replace), shortcuts, fullscreen/distraction-free modes.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QByteArray, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QSplitter, QVBoxLayout,
                               QWidget, QInputDialog)

from .. import config
from ..pdf.document import DocumentInfo, PdfDocument, PdfOpenError, format_size
from ..pdf.navigation import Layout
from ..pdf.search import build_result
from ..themes.models import Theme
from .effects import ScanlineOverlay
from .icons import icon
from .reading_canvas import ReadingCanvas
from .shortcuts_dialog import ShortcutsDialog
from .side_panel import SidePanel
from .status_bar import StatusBar
from .theme_browser import ThemeBrowser
from .toolbar import Toolbar


class MainWindow(QMainWindow):
    def __init__(self, app_ctx):
        super().__init__()
        self.ctx = app_ctx                 # AppContext: settings/theme/db/renderer/stores
        self.doc: PdfDocument | None = None
        self._search_result = None
        self._search_match_index = 0
        self._distraction_free = False
        self._fs_before_fullscreen = None

        self.setWindowTitle("ABNORA")
        self.setMinimumSize(880, 560)
        self.resize(1280, 820)
        self.setAcceptDrops(True)

        # central layout
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = Toolbar(self.ctx.theme_manager.theme)
        root.addWidget(self.toolbar)

        body = QHBoxLayout()
        body.setSpacing(0)
        self.side_panel = SidePanel(self.ctx.theme_manager.theme)
        body.addWidget(self.side_panel)

        self.canvas = ReadingCanvas(self.ctx.theme_manager.theme)
        self.canvas.set_renderer(self.ctx.renderer)
        self.canvas.set_reduced_motion(self.ctx.theme_manager.reduced_motion)
        body.addWidget(self.canvas, 1)
        root.addLayout(body, 1)

        self.status = StatusBar(self.ctx.theme_manager.theme)
        root.addWidget(self.status)
        self.setCentralWidget(central)

        self._scanline_overlays: list[ScanlineOverlay] = []

        self._wire()
        self._shortcuts()
        self._apply_theme(self.ctx.theme_manager.theme)
        self.canvas.set_layout_mode(
            Layout(self.ctx.settings.value("reading/layout", config.DEFAULT_LAYOUT)))

        # restore window state
        geo = self.ctx.settings.value("window/geometry", None)
        if geo:
            self.restoreGeometry(QByteArray.fromHex(geo.encode() if isinstance(geo, str) else geo))
        if not self.ctx.settings.value("window/panel_visible", True, type=bool):
            self._set_panel_visible(False, animate=False)

        # react to renderer thumbnails
        self.ctx.renderer.page_ready.connect(self._on_page_ready)

        # deferred startup: open CLI file or show empty state
        QTimer.singleShot(0, self._startup)

    # ------------------------------------------------------------------ wire

    def _wire(self) -> None:
        tb = self.toolbar
        tb.open_requested.connect(self.open_document_dialog)
        tb.search_requested.connect(self.start_search)
        tb.search_next.connect(lambda: self._step_search(1))
        tb.search_prev.connect(lambda: self._step_search(-1))
        tb.theme_browser_requested.connect(self.open_theme_browser)
        tb.layout_selected.connect(self.set_layout)
        tb.fullscreen_toggled.connect(self._toggle_fullscreen)
        tb.panel_toggled.connect(lambda: self._set_panel_visible(
            not self.side_panel.isVisible()))
        tb.zoom_in.connect(self.canvas.zoom_in)
        tb.zoom_out.connect(self.canvas.zoom_out)

        sp = self.side_panel
        sp.panel_closed.connect(lambda: self._set_panel_visible(False))
        sp.page_selected.connect(self.canvas.show_page)
        sp.outline_selected.connect(self.canvas.show_page)
        sp.bookmark_selected.connect(self.canvas.show_page)
        sp.search_result_selected.connect(self._goto_search_match_page)
        sp.search_submitted.connect(self.start_search)
        sp.bookmark_remove_requested.connect(self._remove_bookmark)
        sp.bookmark_rename_requested.connect(self._rename_bookmark)

        st = self.status
        st.prev_page.connect(self.canvas.prev_page)
        st.next_page.connect(self.canvas.next_page)
        st.go_to_page.connect(self.canvas.show_page)
        st.zoom_in.connect(self.canvas.zoom_in)
        st.zoom_out.connect(self.canvas.zoom_out)
        st.fit_page_requested.connect(self.canvas.fit_page)
        st.fit_width_requested.connect(self.canvas.fit_width)

        cv = self.canvas
        cv.current_page_changed.connect(self._on_current_page)
        cv.zoom_changed.connect(self.status.set_zoom)
        cv.layout_changed.connect(self.status.set_layout_name)
        cv.status_message.connect(self.status.show_message)
        cv.link_activated.connect(self._on_link)

        self.ctx.theme_manager.theme_changed.connect(self._apply_theme)

    def _shortcuts(self) -> None:
        def add(key, slot):
            s = QShortcut(QKeySequence(key), self)
            s.activated.connect(slot)
            return s

        add("Right", self.canvas.next_page)
        add("PgDown", self.canvas.next_page)
        add("Space", self.canvas.next_page)
        add("Left", self.canvas.prev_page)
        add("PgUp", self.canvas.prev_page)
        add("Backspace", self.canvas.prev_page)
        add("Home", self.canvas.first_page)
        add("End", self.canvas.last_page)
        add("G", self._goto_page_dialog)
        add("1", lambda: self.set_layout("single"))
        add("2", lambda: self.set_layout("pair"))
        add("3", lambda: self.set_layout("continuous"))
        add(QKeySequence.StandardKey.ZoomIn, self.canvas.zoom_in)
        add("+", self.canvas.zoom_in)
        add("=", self.canvas.zoom_in)
        add("-", self.canvas.zoom_out)
        add("0", self.canvas.fit_page)
        add("W", self.canvas.fit_width)
        add("R", self._rotate)
        add("F5", lambda: self._set_panel_visible(not self.side_panel.isVisible()))
        add("F11", self._toggle_fullscreen_action)
        add("F9", self._toggle_distraction_free)
        add("F1", self._show_shortcuts)
        add("T", self.open_theme_browser)
        add(QKeySequence.StandardKey.Open, self.open_document_dialog)
        add(QKeySequence.StandardKey.Close, self.close_document)
        add(QKeySequence.StandardKey.Quit, self.close)
        add(QKeySequence.StandardKey.Find, self._focus_search)
        add(QKeySequence.StandardKey.Copy, self._copy_selection)
        add("Ctrl+D", self._toggle_bookmark)
        add("Ctrl+I", self._show_document_info)
        add("Escape", self._on_escape)

    # ------------------------------------------------------------- startup

    def _startup(self) -> None:
        pending = getattr(self.ctx, "pending_file", None)
        if pending:
            self.open_document(pending)
            return
        recent = self.ctx.history.recent(1)
        self.status.show_message("Ready — press Ctrl+O to open a PDF", temporary=False)

    # ------------------------------------------------------------- document

    def open_document_dialog(self) -> None:
        start = self.ctx.settings.value("window/last_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF document", start, "PDF documents (*.pdf);;All files (*)")
        if path:
            self.ctx.settings.setValue("window/last_dir", os.path.dirname(path))
            self.open_document(path)

    def open_document(self, path: str, password: str | None = None) -> bool:
        path = os.path.abspath(path)
        try:
            doc = PdfDocument(path, password=password)
        except PdfOpenError as e:
            if e.kind == "password":
                from PySide6.QtWidgets import QLineEdit
                pwd, ok = QInputDialog.getText(
                    self, "Password required",
                    "This document is password protected.\nPassword:",
                    QLineEdit.EchoMode.Password)
                if ok and pwd:
                    return self.open_document(path, password=pwd)
                self.status.show_message("Password required — document not opened")
                return False
            if e.kind == "missing":
                QMessageBox.warning(self, "ABNORA", e.message)
            else:
                QMessageBox.critical(self, "ABNORA", e.message)
            self.status.show_message(f"Could not open document: {e.kind}")
            return False

        # replace current document
        if self.doc is not None:
            self._save_reading_position()
            self.ctx.renderer.cancel_document(self.doc.path)
            self.doc.close()

        self.doc = doc
        self._search_result = None
        self.side_panel.bind_document(doc, self.ctx.renderer)
        self.canvas.set_document(doc)
        self.toolbar.set_document_title(doc.display_title)
        self.side_panel.set_outline(doc.toc())
        self.status.set_page(1, doc.page_count)
        self.status.set_layout_name(self.canvas.layout_mode.value)
        self.status.show_message(
            f"Opened {doc.filename} — {doc.page_count} pages, "
            f"{format_size(doc.file_size)}", temporary=False)

        # recents + restore position
        self.ctx.history.touch(doc.path, doc.display_title, doc.page_count)
        pos = self.ctx.history.position(doc.path)
        if pos and pos.page > 1:
            self.canvas.show_page(pos.page, animate=False)
        # sync layout from stored position if user hasn't overridden recently
        self._update_window_title()
        return True

    def close_document(self) -> None:
        if self.doc is None:
            return
        self._save_reading_position()
        path = self.doc.path
        self.ctx.renderer.cancel_document(path)
        self.doc.close()
        self.doc = None
        self.canvas.set_document(None)
        self.side_panel.bind_document(None, self.ctx.renderer)
        self.toolbar.set_document_title("")
        self.status.set_page(0, 0)
        self.status.show_message("Document closed", temporary=False)
        self.setWindowTitle("ABNORA")

    def _update_window_title(self) -> None:
        if self.doc:
            self.setWindowTitle(f"{self.doc.display_title} — ABNORA")
        else:
            self.setWindowTitle("ABNORA")

    def _save_reading_position(self) -> None:
        if self.doc is None:
            return
        self.ctx.history.save_position(
            self.doc.path, self.canvas.current_page, self.canvas.zoom,
            self.canvas.layout_mode.value)

    # ----------------------------------------------------------- navigation

    def _on_current_page(self, page: int) -> None:
        if self.doc is None:
            return
        self.status.set_page(page, self.doc.page_count)
        self.side_panel.highlight_current_page(page)
        # highlight active bookmark
        self.status.show_message(f"Page {page}", temporary=True)

    def _goto_page_dialog(self) -> None:
        if self.doc is None:
            return
        page, ok = QInputDialog.getInt(
            self, "Go to page", "Page number:",
            self.canvas.current_page, 1, self.doc.page_count)
        if ok:
            self.canvas.show_page(page)

    def _rotate(self) -> None:
        if self.doc is None:
            return
        self.doc.rotate_all(90)
        self.ctx.renderer.invalidate(self.doc.path)
        self.canvas.rebuild()
        self.status.show_message("Rotated 90°")

    def _on_link(self, target_page: int) -> None:
        if self.doc is not None and 0 <= target_page < self.doc.page_count:
            self.status.show_message(f"Jumped to page {target_page + 1}")
        else:
            self.status.show_message("Link target outside document")

    # ---------------------------------------------------------------- zoom

    def set_layout(self, mode: str) -> None:
        self.toolbar.set_layout(mode)
        self.canvas.set_layout_mode(Layout(mode))
        self.ctx.settings.setValue("reading/layout", mode)
        if self.doc is not None:
            self.canvas.show_page(self.canvas.current_page, animate=False)

    # --------------------------------------------------------------- search

    def _focus_search(self) -> None:
        self.toolbar.search_edit.setFocus()
        self.toolbar.search_edit.selectAll()

    def start_search(self, term: str) -> None:
        term = term.strip()
        if self.doc is None:
            self.status.show_message("Open a document to search")
            return
        if not term:
            self.canvas.clear_search_highlights()
            return
        if self.side_panel.tabs.currentWidget() is not self.side_panel.tabs.widget(3):
            self.side_panel.tabs.setCurrentIndex(3)
        self.side_panel.search_input.setText(term)
        self.status.set_busy(True)
        self.ctx.renderer.search(self.doc, term)
        self._search_term = term

    def _on_search_finished(self, token, results, counts, has_text, err) -> None:
        self.status.show_message("Search finished", temporary=True)
        if self.doc is None or token != self.ctx.renderer._search_token:
            return
        result = build_result(token, getattr(self, "_search_term", ""),
                              results, counts, has_text, err)
        self._search_result = result
        self._search_match_index = 0
        rects_by_page: dict[int, list] = {}
        for m in result.matches:
            rects_by_page.setdefault(m.page, []).append(m.rect)
        self.canvas.set_search_highlights(rects_by_page)
        self.side_panel.show_search_results(result)
        if result.is_empty:
            self.status.show_message(result.scanned_hint or "No matches")
        else:
            self.status.show_message(f"{result.count} match(es) found")
            self._step_search(0)

    def _step_search(self, delta: int) -> None:
        if not self._search_result or self._search_result.is_empty:
            return
        n = self._search_result.count
        self._search_match_index = (self._search_match_index + delta) % n
        m = self._search_result.matches[self._search_match_index]
        if m.page != self.canvas.current_page:
            self.canvas.show_page(m.page)
        self.side_panel.results.setCurrentRow(self._search_match_index)

    def _goto_search_match_page(self, page: int) -> None:
        if self._search_result:
            for i, m in enumerate(self._search_result.matches):
                if m.page == page:
                    self._search_match_index = i
                    break
        self.canvas.show_page(page)

    # ------------------------------------------------------------ bookmarks

    def _toggle_bookmark(self) -> None:
        if self.doc is None:
            return
        page = self.canvas.current_page
        store = self.ctx.bookmarks
        if store.has(self.doc.path, page):
            store.remove_at_page(self.doc.path, page)
            self.status.show_message(f"Bookmark removed (page {page})")
        else:
            store.add(self.doc.path, page)
            self.status.show_message(f"Bookmark added (page {page})")
        self._refresh_bookmarks()

    def _remove_bookmark(self, bookmark_id: int) -> None:
        self.ctx.bookmarks.remove(bookmark_id)
        self._refresh_bookmarks()

    def _rename_bookmark(self, bookmark_id: int, label: str) -> None:
        self.ctx.bookmarks.rename(bookmark_id, label)
        self._refresh_bookmarks()

    def _refresh_bookmarks(self) -> None:
        if self.doc is None:
            self.side_panel.set_bookmarks([])
            return
        self.side_panel.set_bookmarks(self.ctx.bookmarks.list_for(self.doc.path))

    # --------------------------------------------------------------- theme

    def open_theme_browser(self) -> None:
        dlg = ThemeBrowser(self.ctx.theme_manager, self)
        dlg.exec()

    def _apply_theme(self, theme: Theme) -> None:
        # re-generate and apply the app-wide stylesheet + palette instantly
        app = QApplication.instance()
        if app is not None:
            self.ctx.theme_manager.apply_to_app(app)
        self.toolbar.set_theme(theme)
        self.side_panel.set_theme(theme)
        self.status.set_theme(theme)
        self.canvas.set_theme(theme)
        self.canvas.set_reduced_motion(self.ctx.theme_manager.reduced_motion)
        # CRT scanlines over the chrome only (never over PDF pages)
        for o in self._scanline_overlays:
            o.hide()
            o.deleteLater()
        self._scanline_overlays.clear()
        if theme.effects.scanlines:
            for chrome in (self.toolbar, self.status, self.side_panel):
                o = ScanlineOverlay(chrome)
                o.set_color("#000000", 30)
                o.show()
                o.raise_()
                self._scanline_overlays.append(o)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    # --------------------------------------------------------- presentation

    def _toggle_fullscreen(self, on: bool) -> None:
        if on:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_fullscreen_action(self) -> None:
        on = not self.isFullScreen()
        self.toolbar.set_fullscreen(on)
        self._toggle_fullscreen(on)

    def _toggle_distraction_free(self) -> None:
        self._distraction_free = not self._distraction_free
        if self._distraction_free:
            self._fs_before_fullscreen = self.isFullScreen()
            self.toolbar.hide()
            self.status.hide()
            self.side_panel.hide()
            if not self.isFullScreen():
                self.showFullScreen()
            self.status.show_message("Distraction-free — F9 or Esc to restore",
                                     temporary=False)
        else:
            self.toolbar.show()
            self.status.show()
            if self.ctx.settings.value("window/panel_visible", True, type=bool):
                self.side_panel.show()
            if not self._fs_before_fullscreen:
                self.showNormal()
            self.toolbar.set_fullscreen(self.isFullScreen())

    def _on_escape(self) -> None:
        if self._distraction_free:
            self._toggle_distraction_free()
        elif self.isFullScreen():
            self.toolbar.set_fullscreen(False)
            self.showNormal()
        else:
            self.canvas.clear_page_selections()

    def _show_shortcuts(self) -> None:
        ShortcutsDialog(self).exec()

    def _copy_selection(self) -> None:
        # PageView copies on release; this shortcut covers keyboard users by
        # re-copying the last selection if any page holds one.
        for v in self.canvas._page_views:
            if v.selection_rects:
                text = v.selected_text()
                if text:
                    QApplication.clipboard().setText(text)
                    self.status.show_message("Selection copied to clipboard")
                return

    # ---------------------------------------------------------------- panel

    def _set_panel_visible(self, visible: bool, animate: bool = True) -> None:
        self.side_panel.setVisible(visible)
        self.toolbar.panel_btn.setChecked(visible)
        self.ctx.settings.setValue("window/panel_visible", visible)
        _ = animate

    # ----------------------------------------------------------------- info

    def _show_document_info(self) -> None:
        if self.doc is None:
            return
        info = DocumentInfo.from_document(self.doc)
        lines = []
        lines.append(f"Title: {info.title}" if info.title else "Title: (not set)")
        lines.append(f"Author: {info.author}" if info.author else "Author: (not set)")
        if info.subject:
            lines.append(f"Subject: {info.subject}")
        if info.creator:
            lines.append(f"Creator: {info.creator}")
        if info.producer:
            lines.append(f"Producer: {info.producer}")
        lines.append(f"Pages: {info.page_count}")
        lines.append(f"PDF version: {info.pdf_version}")
        lines.append(f"File: {info.filename}")
        lines.append(f"Location: {info.path}")
        lines.append(f"Size: {format_size(info.file_size)}")
        if info.encrypted:
            lines.append("Encrypted: yes (opened with valid password)")
        QMessageBox.information(self, f"Document information — {info.filename}",
                                "\n".join(lines))

    # --------------------------------------------------------------- events

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.open_document(path)
                event.acceptProposedAction()
                return

    def _on_page_ready(self, path: str, page: int, step: float, img) -> None:
        # feed thumbnails
        if (self.doc is not None and path == self.doc.path
                and step < 1.0):
            from PySide6.QtGui import QPixmap
            pm = QPixmap.fromImage(img)
            self.side_panel.set_thumbnail(page, pm)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._save_reading_position()
        geo = self.saveGeometry().toHex().data()
        self.ctx.settings.setValue("window/geometry", geo.decode())
        if self.doc is not None:
            self.ctx.renderer.cancel_document(self.doc.path)
            self.doc.close()
        self.ctx.settings.sync()
        super().closeEvent(event)

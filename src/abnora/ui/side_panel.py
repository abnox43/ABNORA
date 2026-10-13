"""Collapsible side navigation panel: outline, thumbnails, bookmarks, search."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QToolButton, QVBoxLayout, QWidget)

from .icons import icon


class SidePanel(QFrame):
    """Four-tab navigation panel, collapsible from the left edge."""

    page_selected = Signal(int)          # 1-based
    outline_selected = Signal(int)       # 1-based
    bookmark_selected = Signal(int)      # 1-based
    bookmark_remove_requested = Signal(int)   # bookmark id
    bookmark_rename_requested = Signal(int, str)
    search_result_selected = Signal(int)      # 1-based page
    search_submitted = Signal(str)
    panel_closed = Signal()

    PANEL_WIDTH = 268

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("SidePanel")
        self._theme = theme
        self.setFixedWidth(self.PANEL_WIDTH)
        self._collapsed = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # header
        header = QFrame()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 6, 6, 4)
        self.header_label = QLabel("Navigation")
        self.header_label.setObjectName("AppTitle")
        self.header_label.setStyleSheet("font-size: 13px;")
        hl.addWidget(self.header_label)
        hl.addStretch(1)
        close_btn = QToolButton()
        close_btn.setToolTip("Close panel  (F5)")
        close_btn.setIcon(icon("close", 14, theme.text_muted))
        close_btn.clicked.connect(self._on_close)
        hl.addWidget(close_btn)
        lay.addWidget(header)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

        # outline tab
        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.setIndentation(14)
        self.outline.itemActivated.connect(self._on_outline_item)
        self.tabs.addTab(self.outline, "")
        self.tabs.setTabToolTip(0, "Document outline")

        # thumbnails tab
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbs.setIconSize(QSize(104, 140))
        self.thumbs.setGridSize(QSize(132, 176))
        self.thumbs.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.thumbs.setMovement(QListWidget.Movement.Static)
        self.thumbs.setWrapping(True)
        self.thumbs.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.thumbs.itemClicked.connect(self._on_thumb_item)
        self.tabs.addTab(self.thumbs, "")
        self.tabs.setTabToolTip(1, "Page thumbnails")

        # bookmarks tab
        self.bookmarks = QListWidget()
        self.bookmarks.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmarks.customContextMenuRequested.connect(self._bookmark_menu)
        self.bookmarks.itemActivated.connect(self._on_bookmark_item)
        self.tabs.addTab(self.bookmarks, "")
        self.tabs.setTabToolTip(2, "Bookmarks")

        # search tab
        search_page = QWidget()
        sl = QVBoxLayout(search_page)
        sl.setContentsMargins(6, 6, 6, 6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search…  (Enter)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(
            lambda: self.search_submitted.emit(self.search_input.text()))
        sl.addWidget(self.search_input)
        self.search_status = QLabel("")
        self.search_status.setWordWrap(True)
        self.search_status.setProperty("role", "muted")
        sl.addWidget(self.search_status)
        self.results = QListWidget()
        self.results.itemActivated.connect(self._on_result_item)
        sl.addWidget(self.results, 1)
        self.tabs.addTab(search_page, "")
        self.tabs.setTabToolTip(3, "Search results")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._apply_tab_icons()
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(200)
        self._thumb_timer.timeout.connect(self._request_visible_thumbs)

        self._doc = None
        self._renderer = None

    # ----------------------------------------------------------- document

    def bind_document(self, doc, renderer) -> None:
        self._doc = doc
        self._renderer = renderer
        self.clear_document()

    def clear_document(self) -> None:
        self.outline.clear()
        self.thumbs.clear()
        self.bookmarks.clear()
        self.results.clear()
        self.search_status.setText("")

    # ------------------------------------------------------------- outline

    def set_outline(self, entries) -> None:
        self.outline.clear()
        if not entries:
            self.outline.setToolTip("This document has no outline.")
            return
        stack: dict[int, QTreeWidgetItem] = {}
        for e in entries:
            item = QTreeWidgetItem([f"{e.title}"])
            item.setData(0, Qt.ItemDataRole.UserRole, e.page)
            item.setToolTip(0, f"{e.title} — page {e.page}")
            lvl = max(1, e.level)
            if lvl == 1 or (lvl - 1) not in stack:
                self.outline.addTopLevelItem(item)
            else:
                stack[lvl - 1].addChild(item)
            stack[lvl] = item
        self.outline.expandToDepth(0)

    def _on_outline_item(self, item: QTreeWidgetItem, _col: int) -> None:
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page:
            self.outline_selected.emit(int(page))

    # ---------------------------------------------------------- thumbnails

    def prepare_thumbnails(self) -> None:
        if self._doc is None:
            return
        self.thumbs.clear()
        count = self._doc.page_count
        for i in range(count):
            item = QListWidgetItem(f"{i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i + 1)
            item.setToolTip(f"Page {i + 1}")
            self.thumbs.addItem(item)
        self._thumb_timer.start()

    def _request_visible_thumbs(self) -> None:
        if self._doc is None or self._renderer is None:
            return
        rect = self.thumbs.viewport().rect()
        for i in range(self.thumbs.count()):
            item = self.thumbs.item(i)
            if item.icon() and not item.icon().isNull():
                continue
            r = self.thumbs.visualItemRect(item)
            if r.bottom() < -400 or r.top() > rect.height() + 400:
                continue
            page = int(item.data(Qt.ItemDataRole.UserRole)) - 1
            self._renderer.request_thumbnail(self._doc, page, 104)

    def set_thumbnail(self, page: int, pixmap: QPixmap) -> None:
        idx = page  # item index == 0-based page == 1-based page - 1
        if 0 <= idx < self.thumbs.count():
            item = self.thumbs.item(idx)
            if item.icon().isNull():
                item.setIcon(QIcon(pixmap))

    def highlight_current_page(self, page: int) -> None:
        idx = page - 1
        if 0 <= idx < self.thumbs.count():
            self.thumbs.setCurrentRow(idx)

    def _on_thumb_item(self, item: QListWidgetItem) -> None:
        self.page_selected.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    # ----------------------------------------------------------- bookmarks

    def set_bookmarks(self, bookmarks) -> None:
        self.bookmarks.clear()
        for b in bookmarks:
            label = b.label or f"Page {b.page}"
            item = QListWidgetItem(icon("bookmark", 14, self._theme.accent),
                                   f"{label}  ·  p.{b.page}")
            item.setData(Qt.ItemDataRole.UserRole, b.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, b.page)
            item.setToolTip(f"Page {b.page}")
            self.bookmarks.addItem(item)

    def _on_bookmark_item(self, item: QListWidgetItem) -> None:
        self.bookmark_selected.emit(int(item.data(Qt.ItemDataRole.UserRole + 1)))

    def _bookmark_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu
        item = self.bookmarks.itemAt(pos)
        if item is None:
            return
        bid = int(item.data(Qt.ItemDataRole.UserRole))
        page = int(item.data(Qt.ItemDataRole.UserRole + 1))
        menu = QMenu(self)
        rename = menu.addAction("Rename…")
        remove = menu.addAction("Remove bookmark")
        act = menu.exec(self.bookmarks.viewport().mapToGlobal(pos))
        if act is rename:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                self, "Rename bookmark", "Label:", text=item.text().split("  ·  ")[0])
            if ok and text.strip():
                self.bookmark_rename_requested.emit(bid, text.strip())
        elif act is remove:
            self.bookmark_remove_requested.emit(bid)
        _ = page

    # -------------------------------------------------------------- search

    def show_search_results(self, result, current_index: int = 0) -> None:
        self.results.clear()
        if result.error:
            self.search_status.setText(f"Search failed: {result.error}")
            return
        if result.is_empty:
            self.search_status.setText(
                result.scanned_hint or f"No matches for “{result.term}”.")
            return
        self.search_status.setText(
            f"{result.count} match(es) on {len(result.pages)} page(s) "
            f"for “{result.term}”.")
        for i, m in enumerate(result.matches):
            item = QListWidgetItem(f"p.{m.page}  ·  match {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, m.page)
            item.setData(Qt.ItemDataRole.UserRole + 1, i)
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(min(current_index, self.results.count() - 1))

    def set_search_progress(self, done: int, total: int) -> None:
        self.search_status.setText(f"Searching… {done}/{total} pages")

    def _on_result_item(self, item: QListWidgetItem) -> None:
        self.search_result_selected.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    # -------------------------------------------------------------- events

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if widget is self.thumbs:
            self.prepare_thumbnails()

    def _on_close(self) -> None:
        self.panel_closed.emit()

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.tabs.tabBar().setExpanding(False)
        self._apply_tab_icons()

    def _apply_tab_icons(self) -> None:
        c = self._theme.text_muted
        self.tabs.setTabIcon(0, icon("outline", 15, c))
        self.tabs.setTabIcon(1, icon("thumbnails", 15, c))
        self.tabs.setTabIcon(2, icon("bookmark", 15, c))
        self.tabs.setTabIcon(3, icon("search", 15, c))

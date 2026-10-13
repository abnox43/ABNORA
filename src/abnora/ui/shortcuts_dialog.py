"""Keyboard shortcut reference dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

SHORTCUTS = [
    ("Navigation", [
        ("Next page / spread", "→  /  PageDown  /  Space"),
        ("Previous page / spread", "←  /  PageUp  /  Backspace"),
        ("First page", "Home"),
        ("Last page", "End"),
        ("Go to page…", "G"),
        ("Follow internal link", "Click the link"),
    ]),
    ("View", [
        ("Single-page layout", "1"),
        ("Open-book (two-page) layout", "2"),
        ("Continuous scroll layout", "3"),
        ("Zoom in", "+  /  ="),
        ("Zoom out", "−"),
        ("Fit page", "0"),
        ("Fit width", "W"),
        ("Rotate page 90°", "R"),
        ("Toggle navigation panel", "F5"),
        ("Full screen", "F11"),
        ("Distraction-free reading", "F9"),
        ("Toggle themes", "T"),
    ]),
    ("Document", [
        ("Open document…", "Ctrl+O"),
        ("Close document", "Ctrl+W"),
        ("Quit", "Ctrl+Q"),
        ("Search document…", "Ctrl+F"),
        ("Next / previous match", "Enter / Shift+Enter"),
        ("Bookmark current page", "Ctrl+D"),
        ("Document information", "Ctrl+I"),
    ]),
    ("Text", [
        ("Select text", "Drag over text"),
        ("Copy selection", "Automatic on release  (or Ctrl+C)"),
        ("Select single word", "Double-click"),
    ]),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ABNORA — Keyboard shortcuts")
        self.setMinimumSize(520, 480)
        lay = QVBoxLayout(self)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Action", "Shortcut"])
        tree.setColumnWidth(0, 280)
        tree.setRootIsDecorated(True)
        for section, rows in SHORTCUTS:
            sec_item = QTreeWidgetItem([section, ""])
            font = tree.font(0)
            sec_item.setFont(0, font)
            for action, keys in rows:
                child = QTreeWidgetItem([action, keys])
                sec_item.addChild(child)
            tree.addTopLevelItem(sec_item)
        tree.expandAll()
        lay.addWidget(tree, 1)
        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Close")
        close.setProperty("accent", "true")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        lay.addLayout(btns)

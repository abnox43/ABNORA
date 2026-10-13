"""SQLite database access.

One small database holds bookmarks, recent documents, and per-document
reading positions. Access is serialized with a lock; the whole app runs on
the UI thread for storage calls (they are tiny), so this is cheap.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path TEXT NOT NULL,
    page INTEGER NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL,
    UNIQUE(doc_path, page)
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_path ON bookmarks(doc_path);

CREATE TABLE IF NOT EXISTS recent_docs (
    doc_path TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    last_opened REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    doc_path TEXT PRIMARY KEY,
    page INTEGER NOT NULL DEFAULT 1,
    zoom REAL NOT NULL DEFAULT 1.0,
    layout TEXT NOT NULL DEFAULT 'pair',
    updated REAL NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | str):
        self._path = str(path)
        parent = Path(self._path).parent
        if str(parent):
            parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    @property
    def path(self) -> str:
        return self._path

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

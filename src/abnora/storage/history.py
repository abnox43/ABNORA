"""Recent-document history and per-document reading positions."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .database import Database

MAX_RECENT = 15


@dataclass(frozen=True)
class RecentDoc:
    doc_path: str
    title: str
    page_count: int
    last_opened: float


@dataclass(frozen=True)
class Position:
    doc_path: str
    page: int
    zoom: float
    layout: str
    updated: float


class HistoryStore:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------- recents

    def touch(self, doc_path: str, title: str, page_count: int) -> None:
        self._db.execute(
            "INSERT INTO recent_docs (doc_path, title, page_count, last_opened) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(doc_path) DO UPDATE SET "
            "title = excluded.title, page_count = excluded.page_count, "
            "last_opened = excluded.last_opened",
            (doc_path, title, page_count, time.time()),
        )
        # Prune beyond the cap.
        self._db.execute(
            "DELETE FROM recent_docs WHERE doc_path NOT IN "
            "(SELECT doc_path FROM recent_docs ORDER BY last_opened DESC LIMIT ?)",
            (MAX_RECENT,),
        )

    def recent(self, limit: int = MAX_RECENT) -> list[RecentDoc]:
        rows = self._db.query(
            "SELECT * FROM recent_docs ORDER BY last_opened DESC LIMIT ?", (limit,)
        )
        return [
            RecentDoc(r["doc_path"], r["title"], r["page_count"], r["last_opened"])
            for r in rows
        ]

    def remove_recent(self, doc_path: str) -> None:
        self._db.execute("DELETE FROM recent_docs WHERE doc_path = ?", (doc_path,))

    # ------------------------------------------------------------ positions

    def save_position(
        self, doc_path: str, page: int, zoom: float, layout: str
    ) -> None:
        self._db.execute(
            "INSERT INTO positions (doc_path, page, zoom, layout, updated) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(doc_path) DO UPDATE SET "
            "page = excluded.page, zoom = excluded.zoom, layout = excluded.layout, "
            "updated = excluded.updated",
            (doc_path, page, zoom, layout, time.time()),
        )

    def position(self, doc_path: str) -> Position | None:
        rows = self._db.query("SELECT * FROM positions WHERE doc_path = ?", (doc_path,))
        if not rows:
            return None
        r = rows[0]
        return Position(r["doc_path"], r["page"], r["zoom"], r["layout"], r["updated"])

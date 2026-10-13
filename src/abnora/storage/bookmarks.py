"""Bookmark persistence per document."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .database import Database


@dataclass(frozen=True)
class Bookmark:
    id: int
    doc_path: str
    page: int
    label: str
    created: float


class BookmarkStore:
    def __init__(self, db: Database):
        self._db = db

    def add(self, doc_path: str, page: int, label: str = "") -> Bookmark:
        now = time.time()
        self._db.execute(
            "INSERT INTO bookmarks (doc_path, page, label, created) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(doc_path, page) DO UPDATE SET label = excluded.label",
            (doc_path, page, label, now),
        )
        row = self._db.query(
            "SELECT * FROM bookmarks WHERE doc_path = ? AND page = ?",
            (doc_path, page),
        )[0]
        return self._row_to_bookmark(row)

    def rename(self, bookmark_id: int, label: str) -> None:
        self._db.execute(
            "UPDATE bookmarks SET label = ? WHERE id = ?", (label, bookmark_id)
        )

    def remove(self, bookmark_id: int) -> None:
        self._db.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))

    def remove_at_page(self, doc_path: str, page: int) -> None:
        self._db.execute(
            "DELETE FROM bookmarks WHERE doc_path = ? AND page = ?", (doc_path, page)
        )

    def list_for(self, doc_path: str) -> list[Bookmark]:
        rows = self._db.query(
            "SELECT * FROM bookmarks WHERE doc_path = ? ORDER BY page", (doc_path,)
        )
        return [self._row_to_bookmark(r) for r in rows]

    def has(self, doc_path: str, page: int) -> bool:
        rows = self._db.query(
            "SELECT 1 FROM bookmarks WHERE doc_path = ? AND page = ?",
            (doc_path, page),
        )
        return bool(rows)

    @staticmethod
    def _row_to_bookmark(row) -> Bookmark:
        return Bookmark(
            id=row["id"],
            doc_path=row["doc_path"],
            page=row["page"],
            label=row["label"],
            created=row["created"],
        )

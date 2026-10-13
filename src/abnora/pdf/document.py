"""PDF document access (PyMuPDF).

PdfDocument is the UI-thread handle: metadata, page geometry, outline, links.
Rendering and searching never run on this handle — worker threads lease their
own fitz.Document via ``worker_handle`` (one handle per thread, cached), which
keeps PyMuPDF's non-thread-safe document objects safe without re-opening the
file for every page.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf


class PdfOpenError(Exception):
    """Raised when a document cannot be opened."""

    def __init__(self, kind: str, message: str, path: str = ""):
        super().__init__(message)
        self.kind = kind        # "missing" | "password" | "corrupted" | "unsupported"
        self.message = message
        self.path = path


@dataclass(frozen=True)
class Link:
    page: int
    kind: str                  # "goto" | "uri" | "named" | "other"
    target_page: int | None    # internal destination page (0-based), if any
    uri: str = ""


@dataclass(frozen=True)
class TocEntry:
    level: int
    title: str
    page: int                  # 1-based


_THREAD_HANDLES = threading.local()


class PdfDocument:
    def __init__(self, path: str, password: str | None = None):
        self.path = os.path.abspath(path)
        self._password = password
        self._doc: pymupdf.Document | None = None
        self._rotations: dict[int, int] = {}   # page index -> extra rotation degrees
        self.generation = 0                    # bumped on open/close; stale renders dropped
        self._open()

    # ------------------------------------------------------------------ open

    def _open(self) -> None:
        if not os.path.exists(self.path):
            raise PdfOpenError("missing", f"File not found: {self.path}", self.path)
        try:
            doc = pymupdf.open(self.path)
        except pymupdf.FileDataError as e:
            raise PdfOpenError(
                "corrupted",
                f"Not a valid PDF file: {os.path.basename(self.path)} ({e})",
                self.path,
            ) from e
        except Exception as e:  # noqa: BLE001 - surface any open failure gracefully
            raise PdfOpenError(
                "unsupported",
                f"Could not open document: {e}",
                self.path,
            ) from e
        if doc.needs_pass:
            ok = bool(password_ok := False)
            if self._password:
                ok = bool(doc.authenticate(self._password))
            if not ok:
                doc.close()
                raise PdfOpenError(
                    "password",
                    "This document is password protected.",
                    self.path,
                )
            _ = password_ok
        if doc.page_count <= 0:
            doc.close()
            raise PdfOpenError(
                "corrupted", "The document contains no pages.", self.path
            )
        self._doc = doc
        self.generation += 1

    def close(self) -> None:
        self._doc = None
        self.generation += 1

    # -------------------------------------------------------------- metadata

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    @property
    def doc(self) -> pymupdf.Document:
        if self._doc is None:
            raise PdfOpenError("closed", "Document is closed.", self.path)
        return self._doc

    @property
    def page_count(self) -> int:
        return self.doc.page_count

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)

    @property
    def display_title(self) -> str:
        meta = self.metadata
        return meta.get("title") or self.filename

    @property
    def file_size(self) -> int:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0

    @property
    def metadata(self) -> dict[str, str]:
        m = self.doc.metadata or {}
        return {k: (v or "") for k, v in m.items()}

    @property
    def pdf_version(self) -> str:
        fmt = self.metadata.get("format", "")
        return fmt or "unknown"

    @property
    def is_encrypted(self) -> bool:
        return bool(self.doc.is_encrypted)

    # ----------------------------------------------------------------- pages

    def page_size(self, index: int) -> tuple[float, float]:
        """Unrotated page size in points (width, height)."""
        self._check_page(index)
        r = self.doc[index].rect
        # rect reflects rotation; recover unrotated size for stable layout math
        rot = self.rotation(index) % 360
        if rot in (90, 270):
            return (r.height, r.width)
        return (r.width, r.height)

    def rotated_page_size(self, index: int) -> tuple[float, float]:
        """Effective (after rotation) page size in points."""
        self._check_page(index)
        r = self.doc[index].rect
        return (r.width, r.height)

    def rotation(self, index: int) -> int:
        return self._rotations.get(index, 0)

    def set_rotation(self, index: int, degrees: int) -> None:
        self._check_page(index)
        degrees = int(degrees) % 360
        self._rotations[index] = degrees
        self.doc[index].set_rotation(degrees)

    def rotate_all(self, degrees: int) -> None:
        for i in range(self.page_count):
            self.set_rotation(i, (self.rotation(i) + degrees) % 360)

    def toc(self) -> list[TocEntry]:
        try:
            raw = self.doc.get_toc(simple=True)
        except Exception:  # noqa: BLE001 - broken outlines must not crash the UI
            return []
        return [TocEntry(level=int(lv), title=str(t), page=int(pg))
                for lv, t, pg in raw]

    def links(self, page_index: int) -> list[Link]:
        self._check_page(page_index)
        out: list[Link] = []
        for l in self.doc[page_index].get_links():
            kind = l.get("kind")
            target = l.get("page")
            uri = l.get("uri") or ""
            if kind == pymupdf.LINK_GOTO:
                out.append(Link(page_index, "goto", int(target) if target is not None else None))
            elif kind == pymupdf.LINK_URI:
                out.append(Link(page_index, "uri", None, uri))
            elif kind == pymupdf.LINK_NAMED:
                out.append(Link(page_index, "named", None, uri))
            else:
                out.append(Link(page_index, "other", None, uri))
        return out

    def page_text(self, page_index: int) -> str:
        self._check_page(page_index)
        try:
            return self.doc[page_index].get_text("text")
        except Exception:  # noqa: BLE001
            return ""

    def _check_page(self, index: int) -> None:
        if not (0 <= index < self.page_count):
            raise IndexError(f"page {index} out of range 0..{self.page_count - 1}")

    # -------------------------------------------------------- worker leasing

    def worker_handle(self) -> pymupdf.Document:
        """Return this thread's private fitz handle to the same file.

        Handles are cached per thread and keyed by (path, mtime, generation)
        so a closed/replaced document forces a fresh open.
        """
        cache = getattr(_THREAD_HANDLES, "docs", None)
        if cache is None:
            cache = _THREAD_HANDLES.docs = {}
        key = (self.path, self.generation)
        handle = cache.get(key)
        if handle is None:
            try:
                mtime = os.path.getmtime(self.path)
            except OSError:
                mtime = 0.0
            # Drop stale handles for the same path.
            for k in [k for k in cache if k[0] == self.path]:
                try:
                    cache[k].close()
                except Exception:  # noqa: BLE001
                    pass
                del cache[k]
            handle = pymupdf.open(self.path)
            if handle.needs_pass and self._password:
                handle.authenticate(self._password)
            cache[key] = (handle, mtime)
            return handle
        return handle[0]

    # --------------------------------------------------------------- helpers

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<PdfDocument {self.filename!r} pages={self._doc.page_count if self._doc else 0}>"


@dataclass
class DocumentInfo:
    """Plain-data document description used by the info dialog/tests."""

    path: str
    filename: str
    title: str
    author: str
    subject: str
    creator: str
    producer: str
    page_count: int
    pdf_version: str
    file_size: int
    encrypted: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_document(cls, doc: PdfDocument) -> "DocumentInfo":
        m = doc.metadata
        return cls(
            path=doc.path,
            filename=doc.filename,
            title=m.get("title", ""),
            author=m.get("author", ""),
            subject=m.get("subject", ""),
            creator=m.get("creator", ""),
            producer=m.get("producer", ""),
            page_count=doc.page_count,
            pdf_version=doc.pdf_version,
            file_size=doc.file_size,
            encrypted=doc.is_encrypted,
        )


def format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    for unit in ("KB", "MB", "GB"):
        num_bytes /= 1024.0
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
    return f"{num_bytes:.1f} TB"


def make_test_pdf(path: str | Path, pages: int = 6, mixed_sizes: bool = False) -> Path:
    """Create a small test PDF (used by tests and dev tooling)."""
    path = Path(path)
    doc = pymupdf.open()
    for i in range(pages):
        if mixed_sizes and i % 3 == 2:
            page = doc.new_page(width=842, height=595)  # landscape A4-ish
        else:
            page = doc.new_page(width=595, height=842)  # portrait A4-ish
        page.insert_text(
            (72, 90 + i * 8),
            f"ABNORA test page {i + 1} of {pages}",
            fontsize=18,
        )
        page.insert_text((72, 130), "Lorem ipsum dolor sit amet, consectetur.", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path

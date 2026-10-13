"""Document search facade.

Wraps the renderer's worker search into a small result model the UI can
consume, with per-page match counts and snippets when available.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchMatch:
    page: int                     # 1-based
    rect: tuple[float, float, float, float]   # PDF points, unrotated page space


@dataclass
class SearchResult:
    token: int
    term: str
    matches: list[SearchMatch] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)     # 1-based pages with hits
    per_page: dict[int, int] = field(default_factory=dict)
    has_text_layer: bool = True
    error: str | None = None
    done_pages: int = 0
    total_pages: int = 0

    @property
    def count(self) -> int:
        return len(self.matches)

    @property
    def is_empty(self) -> bool:
        return not self.matches

    @property
    def scanned_hint(self) -> str | None:
        """Feedback for PDFs without an embedded text layer (no OCR here)."""
        if self.matches or self.has_text_layer or self.error:
            return None
        return ("No matches. This document appears to have no embedded text "
                "layer (likely a scan). OCR is not implemented in ABNORA.")


def build_result(token: int, term: str,
                 raw_results: list[tuple[int, list[tuple[float, float, float, float]]]],
                 per_page_counts: list[int],
                 has_text_layer: bool,
                 error: object = None) -> SearchResult:
    res = SearchResult(token=token, term=term, has_text_layer=has_text_layer)
    res.error = str(error) if error else None
    for page_idx, rects in raw_results:
        for r in rects:
            res.matches.append(SearchMatch(page=page_idx + 1, rect=r))
        res.pages.append(page_idx + 1)
        res.per_page[page_idx + 1] = len(rects)
    _ = per_page_counts
    res.done_pages = res.total_pages = len(raw_results)
    return res

"""Reading-layout and page-navigation logic.

Pure functions/classes with no Qt dependencies so layouts are unit-testable.
Page numbers are 1-based everywhere in this module (matching what the user
sees); internal PDF indexes are 0-based.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Layout(str, Enum):
    SINGLE = "single"
    PAIR = "pair"
    CONTINUOUS = "continuous"


@dataclass(frozen=True)
class Spread:
    """A set of pages shown together (1 or 2 pages)."""

    pages: tuple[int, ...]          # 1-based page numbers
    index: int                      # 0-based spread index within the document

    @property
    def first_page(self) -> int:
        return self.pages[0]


class SpreadNavigator:
    """Computes spreads for single/pair layouts, honoring cover-alone behavior.

    In pair mode with cover_alone, page 1 stands alone (like a book cover on
    the right side of an open cover); subsequent spreads pair (2|3), (4|5)...
    Without cover_alone, spreads are (1|2), (3|4)...
    """

    def __init__(self, page_count: int, layout: Layout = Layout.PAIR,
                 cover_alone: bool = True):
        if page_count < 1:
            raise ValueError("page_count must be >= 1")
        self.page_count = page_count
        self.layout = layout
        self.cover_alone = cover_alone

    # ------------------------------------------------------------------ math

    def _spreads(self) -> list[tuple[int, ...]]:
        if self.layout != Layout.PAIR or self.page_count == 1:
            return [(p,) for p in range(1, self.page_count + 1)]
        out: list[tuple[int, ...]] = []
        if self.cover_alone:
            out.append((1,))
            p = 2
        else:
            p = 1
        while p <= self.page_count:
            if p + 1 <= self.page_count:
                out.append((p, p + 1))
            else:
                out.append((p,))
            p += 2
        return out

    @property
    def spread_count(self) -> int:
        return len(self._spreads())

    def spread_index_for_page(self, page: int) -> int:
        page = max(1, min(page, self.page_count))
        target = self._spreads()
        for i, sp in enumerate(target):
            if page in sp:
                return i
        return 0

    def spread(self, index: int) -> Spread:
        spreads = self._spreads()
        index = max(0, min(index, len(spreads) - 1))
        return Spread(pages=spreads[index], index=index)

    def spread_for_page(self, page: int) -> Spread:
        return self.spread(self.spread_index_for_page(page))

    def next_spread(self, current_page: int) -> Spread:
        i = self.spread_index_for_page(current_page)
        return self.spread(i + 1)

    def prev_spread(self, current_page: int) -> Spread:
        i = self.spread_index_for_page(current_page)
        return self.spread(i - 1)

    def step(self, current_page: int, delta: int) -> int:
        """Move by `delta` spreads; returns the target first page."""
        i = self.spread_index_for_page(current_page) + delta
        i = max(0, min(i, self.spread_count - 1))
        return self.spread(i).first_page


# ---------------------------------------------------------------- fit / zoom


def fit_zoom(page_w: float, page_h: float, view_w: float, view_h: float,
             margin: float = 0.0) -> float:
    """Zoom factor that fits a page (points) inside a viewport (pixels)."""
    if page_w <= 0 or page_h <= 0 or view_w <= 0 or view_h <= 0:
        return 1.0
    avail_w = max(1.0, view_w - 2 * margin)
    avail_h = max(1.0, view_h - 2 * margin)
    return min(avail_w / page_w, avail_h / page_h)


def fit_width_zoom(page_w: float, view_w: float, margin: float = 0.0) -> float:
    if page_w <= 0 or view_w <= 0:
        return 1.0
    avail_w = max(1.0, view_w - 2 * margin)
    return avail_w / page_w


def clamp_zoom(zoom: float, min_zoom: float = 0.1, max_zoom: float = 8.0) -> float:
    return max(min_zoom, min(max_zoom, zoom))


def continuous_page_for_offset(offsets: list[tuple[int, float, float]],
                               y: float) -> int:
    """Pick the page whose vertical span contains scroll offset `y`.

    `offsets` is a list of (page, top, height) in canvas pixels.
    """
    if not offsets:
        return 1
    best_page = offsets[0][0]
    best_delta = float("inf")
    for page, top, height in offsets:
        mid = top + height / 2
        if top <= y <= top + height:
            return page
        delta = abs(mid - y)
        if delta < best_delta:
            best_delta = delta
            best_page = page
    return best_page

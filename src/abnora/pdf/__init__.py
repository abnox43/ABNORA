"""PDF engine: documents, rendering, navigation, search."""

from .document import (
    DocumentInfo,
    Link,
    PdfDocument,
    PdfOpenError,
    TocEntry,
    format_size,
    make_test_pdf,
)
from .navigation import (
    Layout,
    Spread,
    SpreadNavigator,
    clamp_zoom,
    continuous_page_for_offset,
    fit_width_zoom,
    fit_zoom,
)
from .renderer import PdfRenderer, RenderCache, zoom_to_step
from .search import SearchMatch, SearchResult, build_result

__all__ = [
    "DocumentInfo",
    "Link",
    "PdfDocument",
    "PdfOpenError",
    "TocEntry",
    "format_size",
    "make_test_pdf",
    "Layout",
    "Spread",
    "SpreadNavigator",
    "clamp_zoom",
    "continuous_page_for_offset",
    "fit_width_zoom",
    "fit_zoom",
    "PdfRenderer",
    "RenderCache",
    "zoom_to_step",
    "SearchMatch",
    "SearchResult",
    "build_result",
]

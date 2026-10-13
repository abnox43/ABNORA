"""Theme data models.

A Theme is a declarative set of design tokens. The UI never hard-codes colors;
it consumes tokens, and a centralized QSS generator turns tokens into styling.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Fonts:
    heading: str = "Serif"
    body: str = "Sans Serif"
    mono: str = "Monospace"


@dataclass(frozen=True)
class Effects:
    """Optional decorative effects. All are cheap and disabled on reduced motion
    or low performance unless they are static textures."""

    scanlines: bool = False      # CRT scanlines over chrome
    glow: bool = False           # subtle phosphor/neon glow on accents
    stars: bool = False          # starfield in canvas background
    grid: bool = False           # blueprint-style grid
    horizon: bool = False        # synthwave horizon lines
    wood: bool = False           # walnut wood-grain reading surface
    gears: bool = False          # steampunk engraved corner gears (static)
    vignette: bool = False       # darkened canvas edges
    canvas_texture: bool = False # subtle paper/linen noise on canvas


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    description: str
    dark: bool

    # Surfaces
    window_bg: str
    panel_bg: str
    toolbar_bg: str
    canvas_bg: str          # reading surface around pages
    input_bg: str
    button_bg: str

    # Content
    text: str
    text_muted: str
    border: str
    accent: str
    accent_hover: str
    accent_text: str        # text on accent-colored controls
    selection_bg: str
    selection_text: str
    focus: str

    # Book presentation
    page_shadow: str        # shadow color around rendered pages
    spine_color: str        # gutter color between pages in pair mode

    fonts: Fonts = field(default_factory=Fonts)
    effects: Effects = field(default_factory=Effects)

    def with_overrides(self, **kwargs) -> "Theme":
        return replace(self, **kwargs)

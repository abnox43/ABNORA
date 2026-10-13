"""Application configuration: identity, paths, defaults, QSettings access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "ABNORA"
ORG_NAME = "abnora"
APP_ID = "abnora"
VERSION = "0.1.0"
TAGLINE = "An open book. Twelve worlds."

DEFAULT_THEME = "classic-book"

# Rendering
BASE_DPI = 72.0          # PyMuPDF renders at 72 dpi for zoom = 1.0
MIN_ZOOM = 0.1
MAX_ZOOM = 8.0
ZOOM_STEP = 1.2
RENDER_CACHE_MAX_PAGES = 24
THUMBNAIL_MAX_PAGES = 200

# Reading defaults
DEFAULT_LAYOUT = "pair"          # single | pair | continuous
COVER_ALONE = True               # page 1 shown alone in pair mode


def data_dir() -> Path:
    """Writable per-user data directory (XDG-aware, overridable for tests)."""
    override = os.environ.get("ABNORA_DATA_DIR")
    if override:
        p = Path(override)
    else:
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        p = Path(xdg) / APP_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


def database_path() -> Path:
    override = os.environ.get("ABNORA_DB_PATH")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return data_dir() / "abnora.db"


def settings_path() -> Path:
    """QSettings ini path (kept next to the database for easy inspection)."""
    override = os.environ.get("ABNORA_SETTINGS_PATH")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return data_dir() / "settings.ini"


@dataclass
class WindowState:
    """Persisted window geometry and panel visibility."""

    geometry: bytes | None = None
    side_panel_visible: bool = True
    side_panel_tab: int = 0

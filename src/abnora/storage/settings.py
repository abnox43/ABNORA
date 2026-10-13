"""Persistent user settings backed by a QSettings ini file.

A thin, testable wrapper so the rest of the app never touches QSettings
directly and tests can point at a temporary file via ABNORA_SETTINGS_PATH.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from .. import config


class Settings:
    def __init__(self, path: Path | None = None):
        self._path = path or config.settings_path()
        self._qs = QSettings(str(self._path), QSettings.Format.IniFormat)

    @property
    def path(self) -> Path:
        return self._path

    def value(self, key: str, default=None, type=None):  # noqa: A002
        v = self._qs.value(key, default)
        if type is not None and v is not None:
            try:
                return type(v)
            except (TypeError, ValueError):
                return default
        # QSettings may return strings for bools stored without type info.
        if isinstance(v, str) and type is None and default is not None:
            if isinstance(default, bool):
                return v.lower() in ("true", "1", "yes")
        return v

    def setValue(self, key: str, value) -> None:  # noqa: N802
        self._qs.setValue(key, value)

    def remove(self, key: str) -> None:
        self._qs.remove(key)

    def remove_prefix(self, prefix: str) -> None:
        for key in self._qs.allKeys():
            if key.startswith(prefix):
                self._qs.remove(key)
        self._qs.sync()

    def sync(self) -> None:
        self._qs.sync()

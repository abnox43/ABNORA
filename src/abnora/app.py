"""Application bootstrap: context objects, QApplication setup, main()."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from . import __version__, config
from .pdf.renderer import PdfRenderer
from .storage import BookmarkStore, Database, HistoryStore, Settings
from .themes import ThemeManager
from .ui.icons import app_icon


@dataclass
class AppContext:
    """Everything the UI needs, constructed once and injected."""

    settings: Settings
    theme_manager: ThemeManager
    database: Database
    bookmarks: BookmarkStore
    history: HistoryStore
    renderer: PdfRenderer
    pending_file: str | None = None


def build_context(pending_file: str | None = None) -> AppContext:
    settings = Settings()
    theme_manager = ThemeManager(settings)
    theme_manager.load_effect_overrides()
    database = Database(config.database_path())
    return AppContext(
        settings=settings,
        theme_manager=theme_manager,
        database=database,
        bookmarks=BookmarkStore(database),
        history=HistoryStore(database),
        renderer=PdfRenderer(),
        pending_file=pending_file,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="abnora",
        description="ABNORA — an immersive, themeable PDF reader. "
                    "An open book. Twelve worlds.")
    parser.add_argument("file", nargs="?", help="PDF file to open")
    parser.add_argument("--version", action="version",
                        version=f"abnora {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = parse_args(argv)

    # High-DPI: Qt6 enables this by default; make rounding policy explicit
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv[:1] + argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(config.ORG_NAME)
    app.setDesktopFileName("abnora")
    app.setWindowIcon(app_icon(64))

    pending = os.path.abspath(args.file) if args.file else None
    if pending and not os.path.exists(pending):
        print(f"abnora: file not found: {pending}", file=sys.stderr)
        pending = None

    ctx = build_context(pending)
    ctx.theme_manager.apply_to_app(app)

    # late import to avoid a Qt dependency in build_context tests
    from .ui.main_window import MainWindow

    window = MainWindow(ctx)
    # connect renderer search results
    ctx.renderer.search_finished.connect(window._on_search_finished)

    window.show()
    try:
        code = app.exec()
    finally:
        ctx.renderer.cancel_search()
        ctx.database.close()
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

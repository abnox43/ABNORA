#!/usr/bin/env python3
"""Capture real screenshots of the running ABNORA application.

Requires a display (or QT_QPA_PLATFORM=offscreen for headless capture).
Generates a sample PDF, opens it in the real window, and grabs the widget.

Usage:  python scripts/capture_screenshots.py [output_dir]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "screenshots")
OUT.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("ABNORA_DATA_DIR", "/tmp/abnora-screenshot-data")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def pump(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def make_sample_pdf(path: Path) -> Path:
    """A multi-page sample with mixed sizes, TOC, and links."""
    import pymupdf
    doc = pymupdf.open()
    chapters = ["The Walnut Study", "Margins & Light", "A Wandering Page",
                "The Twelve Worlds", "Quiet Tools", "Night Reading",
                "Silver Ink", "The Long Scroll", "Turn Again"]
    # cover (portrait)
    cover = doc.new_page(width=595, height=842)
    cover.insert_text((72, 380), "ABNORA", fontsize=48)
    cover.insert_text((72, 430), "An open book. Twelve worlds.", fontsize=16)
    cover.insert_text((72, 470), "A sample document for screenshots.", fontsize=11)
    for i, title in enumerate(chapters):
        landscape = i in (2, 6)
        if landscape:
            page = doc.new_page(width=842, height=595)
            x, y = 60, 80
        else:
            page = doc.new_page(width=595, height=842)
            x, y = 72, 90
        page.insert_text((x, y), f"Chapter {i + 1}", fontsize=13)
        page.insert_text((x, y + 34), title, fontsize=26)
        # body text
        lines = [
            "The reader opened the volume and the room grew still. Outside,",
            "the evening settled over the rooftops; inside, the pages held",
            "their quiet argument with the lamp. Every spread is a doorway,",
            "and every doorway keeps its own weather.",
            "",
            "She read of paper mills and of ink made from soot, of the long",
            "afternoons in which a single sentence can bloom and close.",
            "Reading, she thought, is a kind of standing still while the",
            "world turns pages around you.",
            "",
            "And when the chapter ended she did not look up at once.",
        ]
        yy = y + 90
        for line in lines:
            page.insert_text((x, yy), line, fontsize=12)
            yy += 20
        # a keyword for search screenshots
        page.insert_text((x, yy + 14), "walnut", fontsize=12,
                         color=(0.45, 0.27, 0.1))
    doc.set_toc([[1, c, i + 2] for i, c in enumerate(chapters)])
    doc.save(str(path))
    doc.close()
    return path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ABNORA")
    app.setOrganizationName("abnora")

    sample = make_sample_pdf(Path("/tmp/abnora-sample.pdf"))

    from abnora.app import build_context
    from abnora.themes.definitions import ALL_THEMES
    from abnora.ui.main_window import MainWindow

    ctx = build_context()
    ctx.theme_manager.apply_to_app(app)
    win = MainWindow(ctx)
    ctx.renderer.search_finished.connect(win._on_search_finished)
    win.resize(1440, 900)
    win.show()
    pump(200)
    win.open_document(str(sample))
    win.canvas.show_page(3)          # a two-page spread
    win.set_layout("pair")
    win.canvas.show_page(3)
    pump(1200)

    # 1. Classic Book (default) — the signature view
    win.grab().save(str(OUT / "classic-book.png"))
    print("classic-book.png")

    # 2. Side panel with thumbnails
    win._set_panel_visible(True)
    win.side_panel.tabs.setCurrentIndex(1)
    pump(1500)
    win.grab().save(str(OUT / "thumbnails.png"))
    print("thumbnails.png")

    # 3. Search with real highlights
    win.side_panel.tabs.setCurrentIndex(3)
    win.start_search("walnut")
    pump(1500)
    win.canvas.show_page(6)
    pump(800)
    win.grab().save(str(OUT / "search.png"))
    print("search.png")

    # 4. Theme screenshots (close panel, single spread)
    win.side_panel.tabs.setCurrentIndex(0)
    for theme in ALL_THEMES:
        ctx.theme_manager.set_theme(theme.id, persist=False)
        pump(250)
        name = theme.id
        win.grab().save(str(OUT / f"theme-{name}.png"))
        print(f"theme-{name}.png")

    # 5. Continuous layout in classic theme
    ctx.theme_manager.set_theme("classic-book", persist=False)
    win.set_layout("continuous")
    win._set_panel_visible(False)
    win.canvas.show_page(5)
    pump(1200)
    win.grab().save(str(OUT / "continuous.png"))
    print("continuous.png")

    # 6. Theme browser dialog
    win.set_layout("pair")
    from abnora.ui.theme_browser import ThemeBrowser
    dlg = ThemeBrowser(ctx.theme_manager, win)
    dlg.resize(1100, 760)
    dlg.show()
    pump(500)
    dlg.grab().save(str(OUT / "theme-browser.png"))
    print("theme-browser.png")
    dlg.close()

    win.close()
    print(f"\nSaved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

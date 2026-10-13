"""Shared fixtures: small PDFs generated per test run."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Keep Qt away from the user's real display/config in GUI tests.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ABNORA_REDUCED_MOTION", "1")


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Point ABNORA's storage at a temp directory."""
    d = tmp_path / "abnora-data"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ABNORA_DATA_DIR", str(d))
    monkeypatch.setenv("ABNORA_DB_PATH", str(d / "test.db"))
    monkeypatch.setenv("ABNORA_SETTINGS_PATH", str(d / "settings.ini"))
    return d


@pytest.fixture()
def simple_pdf(tmp_path):
    """A 5-page portrait PDF with text on every page."""
    import pymupdf
    path = tmp_path / "simple.pdf"
    doc = pymupdf.open()
    for i in range(5):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f"Alpha page {i + 1}", fontsize=20)
        page.insert_text((72, 140), "common keyword here", fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def mixed_pdf(tmp_path):
    """PDF with mixed portrait/landscape page sizes."""
    import pymupdf
    path = tmp_path / "mixed.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)          # portrait
    doc.new_page(width=842, height=595)          # landscape
    doc.new_page(width=400, height=400)          # square
    doc[0].insert_text((50, 60), "portrait page", fontsize=14)
    doc[1].insert_text((50, 60), "landscape page", fontsize=14)
    doc[2].insert_text((50, 60), "square page", fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def outlined_pdf(tmp_path):
    """PDF with a table of contents and an internal link."""
    import pymupdf
    path = tmp_path / "outlined.pdf"
    doc = pymupdf.open()
    for i in range(4):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f"Chapter {i + 1}", fontsize=22)
    doc.set_toc([[1, "Chapter One", 1], [1, "Chapter Two", 2],
                 [1, "Chapter Three", 3], [1, "Chapter Four", 4]])
    # internal link on page 1 -> page 4
    doc[0].insert_link({
        "kind": pymupdf.LINK_GOTO, "page": 3,
        "from": pymupdf.Rect(72, 80, 220, 110),
    })
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def encrypted_pdf(tmp_path):
    """Password-protected PDF."""
    import pymupdf
    path = tmp_path / "secret.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Secret contents", fontsize=18)
    doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256,
             user_pw="hunter2", owner_pw="hunter2")
    doc.close()
    return path


@pytest.fixture()
def invalid_pdf(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\nthis is definitely not a valid pdf body \x00\x01")
    return path


@pytest.fixture()
def settings(data_dir):
    from abnora.storage.settings import Settings
    return Settings()


@pytest.fixture()
def db(data_dir):
    from abnora.storage.database import Database
    database = Database(data_dir / "test.db")
    yield database
    database.close()

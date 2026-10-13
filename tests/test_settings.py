"""Settings persistence, reading positions, recent documents."""

from abnora.storage.history import HistoryStore
from abnora.storage.settings import Settings


def test_settings_roundtrip(data_dir):
    s = Settings()
    s.setValue("test/int", 42)
    s.setValue("test/flag", True)
    s.setValue("test/text", "héllo wörld")
    s2 = Settings()
    assert s2.value("test/int", type=int) == 42
    assert s2.value("test/flag", type=bool) is True
    assert s2.value("test/text") == "héllo wörld"


def test_settings_default(data_dir):
    s = Settings()
    assert s.value("nothing/here", "fallback") == "fallback"


def test_settings_remove_prefix(data_dir):
    s = Settings()
    s.setValue("theme/id", "cyberpunk")
    s.setValue("other/key", 1)
    s.remove_prefix("theme/")
    s2 = Settings()
    assert s2.value("theme/id", "classic-book") == "classic-book"
    assert s2.value("other/key", type=int) == 1


def test_positions(db):
    h = HistoryStore(db)
    assert h.position("/docs/a.pdf") is None
    h.save_position("/docs/a.pdf", page=12, zoom=1.5, layout="pair")
    p = h.position("/docs/a.pdf")
    assert (p.page, p.zoom, p.layout) == (12, 1.5, "pair")
    # update
    h.save_position("/docs/a.pdf", page=30, zoom=0.8, layout="single")
    p = h.position("/docs/a.pdf")
    assert (p.page, p.zoom, p.layout) == (30, 0.8, "single")


def test_positions_persist_across_instances(db):
    h = HistoryStore(db)
    h.save_position("/docs/a.pdf", 7, 1.0, "continuous")
    h2 = HistoryStore(db)
    assert h2.position("/docs/a.pdf").page == 7


def test_positions_isolated_per_doc(db):
    h = HistoryStore(db)
    h.save_position("/docs/a.pdf", 1, 1.0, "pair")
    h.save_position("/docs/b.pdf", 99, 2.0, "single")
    assert h.position("/docs/a.pdf").page == 1
    assert h.position("/docs/b.pdf").page == 99


def test_recent_docs(db):
    h = HistoryStore(db)
    h.touch("/docs/a.pdf", "A", 10)
    h.touch("/docs/b.pdf", "B", 20)
    recents = h.recent()
    assert [r.doc_path for r in recents] == ["/docs/b.pdf", "/docs/a.pdf"]
    assert recents[0].title == "B"
    assert recents[0].page_count == 20


def test_recent_updates_and_reorders(db):
    h = HistoryStore(db)
    h.touch("/docs/a.pdf", "A", 10)
    h.touch("/docs/b.pdf", "B", 20)
    h.touch("/docs/a.pdf", "A v2", 12)
    recents = h.recent()
    assert recents[0].doc_path == "/docs/a.pdf"
    assert recents[0].title == "A v2"
    assert len(recents) == 2


def test_recent_pruned(db):
    h = HistoryStore(db)
    for i in range(20):
        h.touch(f"/docs/{i}.pdf", f"D{i}", i)
    assert len(h.recent()) <= 15


def test_remove_recent(db):
    h = HistoryStore(db)
    h.touch("/docs/a.pdf", "A", 1)
    h.remove_recent("/docs/a.pdf")
    assert h.recent() == []

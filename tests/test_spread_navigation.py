"""Spread navigation logic for all layouts and cover-page handling."""

import pytest

from abnora.pdf.navigation import (Layout, SpreadNavigator, clamp_zoom,
                                   continuous_page_for_offset, fit_width_zoom,
                                   fit_zoom)


def test_single_layout_spreads():
    nav = SpreadNavigator(5, Layout.SINGLE)
    assert nav.spread_count == 5
    assert nav.spread(0).pages == (1,)
    assert nav.spread(4).pages == (5,)


def test_pair_cover_alone():
    nav = SpreadNavigator(8, Layout.PAIR, cover_alone=True)
    spreads = [nav.spread(i).pages for i in range(nav.spread_count)]
    assert spreads == [(1,), (2, 3), (4, 5), (6, 7), (8,)]


def test_pair_cover_with_first():
    nav = SpreadNavigator(8, Layout.PAIR, cover_alone=False)
    spreads = [nav.spread(i).pages for i in range(nav.spread_count)]
    assert spreads == [(1, 2), (3, 4), (5, 6), (7, 8)]


def test_pair_odd_last_page():
    nav = SpreadNavigator(7, Layout.PAIR, cover_alone=False)
    spreads = [nav.spread(i).pages for i in range(nav.spread_count)]
    assert spreads[-1] == (7,)


def test_spread_for_page():
    nav = SpreadNavigator(10, Layout.PAIR, cover_alone=True)
    assert nav.spread_for_page(1).pages == (1,)
    assert nav.spread_for_page(2).pages == (2, 3)
    assert nav.spread_for_page(3).pages == (2, 3)
    assert nav.spread_for_page(4).pages == (4, 5)


def test_next_prev_boundaries():
    nav = SpreadNavigator(4, Layout.PAIR, cover_alone=True)
    # [(1,), (2,3), (4,)]
    assert nav.next_spread(1).pages == (2, 3)
    assert nav.next_spread(3).pages == (4,)
    # last spread: next stays put
    assert nav.next_spread(4).pages == (4,)
    assert nav.prev_spread(1).pages == (1,)
    assert nav.prev_spread(4).pages == (2, 3)


def test_step_clamps():
    nav = SpreadNavigator(6, Layout.PAIR, cover_alone=False)
    assert nav.step(1, -5) == 1
    assert nav.step(1, 99) == nav.spread(nav.spread_count - 1).first_page


def test_single_page_document():
    nav = SpreadNavigator(1, Layout.PAIR, cover_alone=True)
    assert nav.spread_count == 1
    assert nav.spread_for_page(1).pages == (1,)


def test_invalid_page_count():
    with pytest.raises(ValueError):
        SpreadNavigator(0, Layout.SINGLE)


def test_fit_zoom():
    # A4 portrait into a 600x700 viewport
    z = fit_zoom(595, 842, 600, 700)
    assert z == pytest.approx(700 / 842)
    # landscape
    z = fit_zoom(842, 595, 600, 700)
    assert z == pytest.approx(600 / 842)


def test_fit_width_zoom():
    assert fit_width_zoom(595, 1190) == pytest.approx(2.0)
    assert fit_width_zoom(595, 600, margin=10) == pytest.approx(580 / 595)


def test_clamp_zoom():
    assert clamp_zoom(0.01) == 0.1
    assert clamp_zoom(100) == 8.0
    assert clamp_zoom(1.5) == 1.5


def test_continuous_page_for_offset():
    offsets = [(1, 0.0, 800.0), (2, 800.0, 800.0), (3, 1600.0, 800.0)]
    assert continuous_page_for_offset(offsets, 100) == 1
    assert continuous_page_for_offset(offsets, 900) == 2
    assert continuous_page_for_offset(offsets, 1700) == 3
    assert continuous_page_for_offset([], 50) == 1

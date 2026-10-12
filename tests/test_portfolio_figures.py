"""Tests for portfolio figure data selection, not pixel appearance."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hospitality_analytics.adr_analysis import ADR_VIEW_POSITIVE
from hospitality_analytics.portfolio_figures import (
    PORTFOLIO_SEGMENTS,
    STAY_DISPLAY_BUCKETS,
    load_verified_tables,
    major_segment_rows,
    positive_monthly_adr,
    stay_display_rows,
    write_portfolio_figures,
)


def test_major_segments_omit_tiny_categories() -> None:
    tables = load_verified_tables()
    mix = major_segment_rows(tables["market_segment"])
    nonarrival = major_segment_rows(tables["nonarrival_segment"])
    assert set(mix["category"]).issubset(set(PORTFOLIO_SEGMENTS))
    assert "Complementary" not in set(mix["category"])
    assert "Aviation" not in set(mix["category"])
    assert "Complementary" in set(tables["market_segment"]["category"])
    assert set(nonarrival["category"]).issubset(set(PORTFOLIO_SEGMENTS))


def test_stay_display_omits_zero_nights_only_for_visual() -> None:
    tables = load_verified_tables()
    displayed = stay_display_rows(tables["stay_length_bucket"])
    assert "0" not in set(displayed["category"])
    assert "0" in set(tables["stay_length_bucket"]["category"])
    assert list(STAY_DISPLAY_BUCKETS) == ["1", "2", "3", "4", "5", "6", "7", "8+"]
    seven = displayed.loc[
        (displayed["hotel"] == "Resort Hotel")
        & (displayed["convention_label"] == "A")
        & (displayed["category"] == "7"),
        "share_pct",
    ].iloc[0]
    assert abs(float(seven) - 14.628103624710509) < 1e-6


def test_monthly_adr_uses_positive_view_only() -> None:
    tables = load_verified_tables()
    monthly = positive_monthly_adr(tables["adr_monthly"])
    assert set(monthly["adr_view"]) == {ADR_VIEW_POSITIVE}
    assert "PUBLISHED_ADR" in set(tables["adr_monthly"]["adr_view"])


def test_groups_nonarrival_matches_verified_csv() -> None:
    tables = load_verified_tables()
    source = tables["nonarrival_segment"]
    city_a = source.loc[
        (source["hotel"] == "City Hotel")
        & (source["convention_label"] == "A")
        & (source["category"] == "Groups"),
        "nonarrival_rate_pct",
    ].iloc[0]
    city_b = source.loc[
        (source["hotel"] == "City Hotel")
        & (source["convention_label"] == "B")
        & (source["category"] == "Groups"),
        "nonarrival_rate_pct",
    ].iloc[0]
    assert abs(float(city_a) - 74.65329635161085) < 1e-6
    assert abs(float(city_b) - 34.809348093480935) < 1e-6


def test_write_portfolio_figures_does_not_overwrite_phase_pngs(tmp_path: Path) -> None:
    sentinel = tmp_path / "market_segment_2016.png"
    sentinel.write_bytes(b"phase3")
    tables = load_verified_tables()
    paths = write_portfolio_figures(tables=tables, output_dir=tmp_path)
    names = {path.name for path in paths}
    assert names == {
        "portfolio_market_segment_2016.png",
        "portfolio_stay_length_2016.png",
        "portfolio_quoted_adr_seasonality_2016.png",
        "portfolio_nonarrival_segment_2016.png",
    }
    assert sentinel.read_bytes() == b"phase3"
    for path in paths:
        assert path.is_file()
        assert path.stat().st_size > 1000


def test_load_verified_tables_does_not_require_mutating_source() -> None:
    tables = load_verified_tables()
    snapshot = tables["market_segment"].copy(deep=True)
    major_segment_rows(tables["market_segment"])
    pd.testing.assert_frame_equal(tables["market_segment"], snapshot)

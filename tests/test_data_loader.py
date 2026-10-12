"""Behaviour tests for the Phase 1 booking-demand loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hospitality_analytics.data_loader import (
    HOTEL_COLUMN,
    PUBLISHED_COLUMNS,
    load_bookings,
    load_hotel,
    project_root,
    raw_csv_path,
)


@pytest.fixture(scope="module")
def resort() -> pd.DataFrame:
    return load_hotel("H1")


@pytest.fixture(scope="module")
def city() -> pd.DataFrame:
    return load_hotel("H2")


@pytest.fixture(scope="module")
def bookings() -> pd.DataFrame:
    return load_bookings()


def test_project_paths_are_independent_of_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    root = project_root()
    assert (root / "pyproject.toml").is_file()
    assert raw_csv_path("H1").is_file()
    assert raw_csv_path("H2").is_file()
    loaded = load_hotel("H1")
    assert len(loaded) == 40_060


def test_load_resort_shape_and_label(resort: pd.DataFrame) -> None:
    assert resort.shape == (40_060, 32)
    assert set(resort[HOTEL_COLUMN].unique()) == {"Resort Hotel"}
    assert list(resort.columns) == [HOTEL_COLUMN, *PUBLISHED_COLUMNS]


def test_load_city_shape_and_label(city: pd.DataFrame) -> None:
    assert city.shape == (79_330, 32)
    assert set(city[HOTEL_COLUMN].unique()) == {"City Hotel"}
    assert list(city.columns) == [HOTEL_COLUMN, *PUBLISHED_COLUMNS]


def test_combined_shape_and_hotel_counts(bookings: pd.DataFrame) -> None:
    assert bookings.shape == (119_390, 32)
    counts = bookings[HOTEL_COLUMN].value_counts().to_dict()
    assert counts == {"City Hotel": 79_330, "Resort Hotel": 40_060}


def test_raw_files_have_identical_published_schemas() -> None:
    header_h1 = pd.read_csv(raw_csv_path("H1"), nrows=0)
    header_h2 = pd.read_csv(raw_csv_path("H2"), nrows=0)
    assert list(header_h1.columns) == list(PUBLISHED_COLUMNS)
    assert list(header_h2.columns) == list(PUBLISHED_COLUMNS)
    assert list(header_h1.columns) == list(header_h2.columns)
    assert header_h1.shape[1] == 31
    assert header_h2.shape[1] == 31


def test_loaded_hotels_share_schema(resort: pd.DataFrame, city: pd.DataFrame) -> None:
    assert list(resort.columns) == list(city.columns)
    assert list(resort.dtypes) == list(city.dtypes)


def test_whitespace_is_stripped(resort: pd.DataFrame, city: pd.DataFrame) -> None:
    text_columns = [
        "Meal",
        "DepositType",
        "ReservedRoomType",
        "AssignedRoomType",
        "MarketSegment",
        "DistributionChannel",
        "CustomerType",
        "ReservationStatus",
    ]
    for frame in (resort, city):
        for column in text_columns:
            values = frame[column].dropna().astype(str)
            assert (values == values.str.strip()).all(), column
            assert not values.str.fullmatch(r"\s+.*|.*\s+").any(), column


def test_null_and_na_tokens_become_missing(resort: pd.DataFrame, city: pd.DataFrame) -> None:
    assert int(resort["Country"].isna().sum()) == 464
    assert int(city["Country"].isna().sum()) == 24
    assert int(resort["Agent"].isna().sum()) == 8_209
    assert int(city["Agent"].isna().sum()) == 8_131
    assert int(resort["Company"].isna().sum()) == 36_952
    assert int(city["Company"].isna().sum()) == 75_641
    assert int(resort["Children"].isna().sum()) == 0
    assert int(city["Children"].isna().sum()) == 4

    remaining = pd.concat([resort, city], ignore_index=True)
    for column in remaining.columns:
        if remaining[column].dtype == object or str(remaining[column].dtype) == "string":
            text = remaining[column].dropna().astype(str)
            assert not text.isin(["NULL", "NA"]).any(), column


def test_exact_duplicates_are_preserved(resort: pd.DataFrame, city: pd.DataFrame, bookings: pd.DataFrame) -> None:
    assert int(resort.duplicated(keep="first").sum()) == 6_092
    assert int(city.duplicated(keep="first").sum()) == 25_902
    assert int(bookings.duplicated(keep="first").sum()) == 6_092 + 25_902
    assert len(resort.drop_duplicates()) == 33_968
    assert len(city.drop_duplicates()) == 53_428


def test_adr_extremes_are_preserved(resort: pd.DataFrame, city: pd.DataFrame) -> None:
    assert float(resort["ADR"].min()) == pytest.approx(-6.38)
    assert float(resort["ADR"].max()) == pytest.approx(508.0)
    assert int((resort["ADR"] < 0).sum()) == 1
    assert float(city["ADR"].min()) == pytest.approx(0.0)
    assert float(city["ADR"].max()) == pytest.approx(5400.0)
    assert int((city["ADR"] == 5400).sum()) == 1
    assert int(resort["ADR"].isna().sum()) == 0
    assert int(city["ADR"].isna().sum()) == 0


def test_is_canceled_and_reservation_status_domains(bookings: pd.DataFrame) -> None:
    assert set(bookings["IsCanceled"].dropna().unique().tolist()) == {0, 1}
    assert set(bookings["ReservationStatus"].dropna().unique()) == {
        "Check-Out",
        "Canceled",
        "No-Show",
    }


def test_unknown_hotel_code_raises() -> None:
    from hospitality_analytics.data_loader import DataValidationError

    with pytest.raises(DataValidationError, match="Unknown hotel code"):
        load_hotel("H3")

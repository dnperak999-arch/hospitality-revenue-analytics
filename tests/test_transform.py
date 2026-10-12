"""Behaviour tests for analysis-ready transformations."""

from __future__ import annotations

import pandas as pd
import pytest

from hospitality_analytics.data_loader import (
    HOTEL_COLUMN,
    PUBLISHED_COLUMNS,
    DataValidationError,
)
from hospitality_analytics.transform import (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
    DERIVED_COLUMNS,
    LEAD_TIME_BANDS,
    add_analysis_fields,
    all_published_rows,
    apply_counting_convention,
    exact_row_deduplicated,
    lead_time_band,
    prepare_analysis_data,
)

_DEFAULTS: dict[str, object] = {
    "IsCanceled": 0,
    "LeadTime": 10,
    "ArrivalDateYear": 2016,
    "ArrivalDateMonth": "July",
    "ArrivalDateWeekNumber": 99,
    "ArrivalDateDayOfMonth": 15,
    "StaysInWeekendNights": 1,
    "StaysInWeekNights": 2,
    "Adults": 2,
    "Children": 0,
    "Babies": 0,
    "Meal": "BB",
    "Country": "PRT",
    "MarketSegment": "Direct",
    "DistributionChannel": "Direct",
    "IsRepeatedGuest": 0,
    "PreviousCancellations": 0,
    "PreviousBookingsNotCanceled": 0,
    "ReservedRoomType": "A",
    "AssignedRoomType": "A",
    "BookingChanges": 0,
    "DepositType": "No Deposit",
    "Agent": 1,
    "Company": pd.NA,
    "DaysInWaitingList": 0,
    "CustomerType": "Transient",
    "ADR": 80.0,
    "RequiredCarParkingSpaces": 0,
    "TotalOfSpecialRequests": 0,
    "ReservationStatus": "Check-Out",
    "ReservationStatusDate": "2016-07-18",
}


def _row(hotel: str = "Resort Hotel", **overrides: object) -> dict[str, object]:
    values = {HOTEL_COLUMN: hotel, **_DEFAULTS, **overrides}
    return {column: values[column] for column in (HOTEL_COLUMN, *PUBLISHED_COLUMNS)}


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def analysis_ready() -> pd.DataFrame:
    return prepare_analysis_data()


def test_input_dataframe_is_not_mutated() -> None:
    original = _frame(
        [
            _row(LeadTime=0, ADR=0.0),
            _row(LeadTime=181, ReservationStatus="Canceled", IsCanceled=1),
        ]
    )
    snapshot = original.copy(deep=True)
    result = add_analysis_fields(original)
    pd.testing.assert_frame_equal(original, snapshot)
    assert list(result.columns) != list(original.columns)
    assert len(result) == len(original)


def test_arrival_date_parses_without_week_number() -> None:
    frame = _frame(
        [
            _row(
                ArrivalDateYear=2016,
                ArrivalDateMonth="February",
                ArrivalDateDayOfMonth=29,
                ArrivalDateWeekNumber=99,
            )
        ]
    )
    result = add_analysis_fields(frame)
    assert pd.api.types.is_datetime64_any_dtype(result["ArrivalDate"])
    assert result["ArrivalDate"].tolist() == [pd.Timestamp("2016-02-29")]
    assert int(result["ArrivalDate"].isna().sum()) == 0


def test_unparseable_arrival_date_raises() -> None:
    frame = _frame([_row(ArrivalDateMonth="Smarch", ArrivalDateDayOfMonth=1)])
    with pytest.raises(DataValidationError, match="ArrivalDate"):
        add_analysis_fields(frame)


def test_total_nights_is_the_sum_of_stored_night_fields() -> None:
    frame = _frame(
        [
            _row(StaysInWeekendNights=0, StaysInWeekNights=0),
            _row(StaysInWeekendNights=2, StaysInWeekNights=5),
            _row(StaysInWeekendNights=4, StaysInWeekNights=6),
        ]
    )
    result = add_analysis_fields(frame)
    assert result["TotalNights"].tolist() == [0, 7, 10]
    assert (result["TotalNights"] >= 0).all()
    assert "WeekendNights" not in result.columns


def test_lead_time_band_boundaries() -> None:
    samples = [0, 1, 7, 8, 30, 31, 90, 91, 180, 181, 737]
    expected = [
        "0 days",
        "1–7 days",
        "1–7 days",
        "8–30 days",
        "8–30 days",
        "31–90 days",
        "31–90 days",
        "91–180 days",
        "91–180 days",
        "181+ days",
        "181+ days",
    ]
    bands = lead_time_band(pd.Series(samples))
    assert list(bands) == expected
    assert list(bands.categories) == list(LEAD_TIME_BANDS)
    assert bands.ordered

    frame = _frame([_row(LeadTime=value) for value in samples])
    result = add_analysis_fields(frame)
    assert result["LeadTime"].tolist() == samples
    assert result["LeadTimeBand"].tolist() == expected


def test_booking_outcome_matches_reservation_status() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Check-Out", IsCanceled=0),
            _row(ReservationStatus="Canceled", IsCanceled=1),
            _row(ReservationStatus="No-Show", IsCanceled=1),
        ]
    )
    result = add_analysis_fields(frame)
    assert result["BookingOutcome"].tolist() == ["Check-Out", "Canceled", "No-Show"]
    assert (result["BookingOutcome"] == result["ReservationStatus"]).all()
    assert not (result["BookingOutcome"] == result["IsCanceled"].map({0: "Check-Out", 1: "Canceled"})).all()


def test_duplicate_group_size_is_within_hotel_and_uses_published_columns() -> None:
    shared = _row(hotel="Resort Hotel", LeadTime=5, ADR=100.0)
    other_hotel = _row(hotel="City Hotel", LeadTime=5, ADR=100.0)
    different = _row(hotel="Resort Hotel", LeadTime=6, ADR=100.0)
    frame = _frame([shared, shared, other_hotel, different])
    result = add_analysis_fields(frame)

    expected = (
        frame.groupby([HOTEL_COLUMN, *PUBLISHED_COLUMNS], dropna=False)[HOTEL_COLUMN]
        .transform("size")
        .astype("int64")
    )
    assert result["ExactDuplicateGroupSize"].tolist() == expected.tolist()
    assert result["ExactDuplicateGroupSize"].tolist() == [2, 2, 1, 1]
    assert result["IsExactDuplicate"].tolist() == [True, True, False, False]


def test_duplicate_identity_ignores_derived_columns() -> None:
    frame = _frame(
        [
            _row(LeadTime=3, StaysInWeekendNights=1, StaysInWeekNights=1, ADR=50.0),
            _row(LeadTime=3, StaysInWeekendNights=1, StaysInWeekNights=1, ADR=50.0),
        ]
    )
    result = add_analysis_fields(frame)
    derived_only_keys = list(result.columns)
    grouped_on_all = result.groupby(derived_only_keys, dropna=False)[HOTEL_COLUMN].transform("size")
    assert result["ExactDuplicateGroupSize"].tolist() == [2, 2]
    assert grouped_on_all.tolist() == [2, 2]
    published_only = result.groupby(list((HOTEL_COLUMN, *PUBLISHED_COLUMNS)), dropna=False)[
        HOTEL_COLUMN
    ].transform("size")
    assert result["ExactDuplicateGroupSize"].tolist() == published_only.tolist()
    assert "ArrivalDate" not in (HOTEL_COLUMN, *PUBLISHED_COLUMNS)
    assert "TotalNights" not in PUBLISHED_COLUMNS
    assert "LeadTimeBand" not in PUBLISHED_COLUMNS
    assert "BookingOutcome" not in PUBLISHED_COLUMNS


def test_counting_conventions_a_and_b() -> None:
    frame = add_analysis_fields(
        _frame(
            [
                _row(hotel="Resort Hotel", LeadTime=4),
                _row(hotel="Resort Hotel", LeadTime=4),
                _row(hotel="Resort Hotel", LeadTime=9),
                _row(hotel="City Hotel", LeadTime=4),
                _row(hotel="City Hotel", LeadTime=4),
            ]
        )
    )
    convention_a = all_published_rows(frame)
    convention_b = exact_row_deduplicated(frame)
    assert len(convention_a) == 5
    assert len(convention_b) == 3
    assert convention_b[HOTEL_COLUMN].value_counts().to_dict() == {
        "Resort Hotel": 2,
        "City Hotel": 1,
    }
    assert len(apply_counting_convention(frame, COUNTING_ALL_PUBLISHED_ROWS)) == 5
    assert len(apply_counting_convention(frame, COUNTING_EXACT_ROW_DEDUPLICATED)) == 3


def test_adr_flags_do_not_change_adr() -> None:
    frame = _frame(
        [
            _row(ADR=0.0),
            _row(ADR=-6.38),
            _row(ADR=5400.0),
            _row(ADR=80.0),
        ]
    )
    result = add_analysis_fields(frame)
    assert result["ADR"].tolist() == [0.0, -6.38, 5400.0, 80.0]
    assert result["ADRIsZero"].tolist() == [True, False, False, False]
    assert result["ADRIsNegative"].tolist() == [False, True, False, False]
    assert result["ADRIsExtremeHigh"].tolist() == [False, False, True, False]


def test_complete_year_and_july_august_flags() -> None:
    frame = _frame(
        [
            _row(ArrivalDateYear=2015, ArrivalDateMonth="July"),
            _row(ArrivalDateYear=2016, ArrivalDateMonth="March"),
            _row(ArrivalDateYear=2016, ArrivalDateMonth="August"),
            _row(ArrivalDateYear=2017, ArrivalDateMonth="January"),
        ]
    )
    result = add_analysis_fields(frame)
    assert result["IsCompleteYear"].tolist() == [False, True, True, False]
    assert result["IsJulyAugustArrival"].tolist() == [True, False, True, False]


def test_unknown_counting_convention_raises() -> None:
    frame = add_analysis_fields(_frame([_row()]))
    with pytest.raises(DataValidationError, match="Unknown counting convention"):
        apply_counting_convention(frame, "clean_data")


def test_published_extract_row_count_and_original_columns(analysis_ready: pd.DataFrame) -> None:
    assert len(analysis_ready) == 119_390
    for column in (HOTEL_COLUMN, *PUBLISHED_COLUMNS):
        assert column in analysis_ready.columns
    for column in DERIVED_COLUMNS:
        assert column in analysis_ready.columns
    assert analysis_ready["ArrivalDate"].isna().sum() == 0
    assert pd.api.types.is_datetime64_any_dtype(analysis_ready["ArrivalDate"])


def test_published_zero_night_counts(analysis_ready: pd.DataFrame) -> None:
    zeros = analysis_ready.loc[analysis_ready["TotalNights"] == 0]
    counts = zeros[HOTEL_COLUMN].value_counts().to_dict()
    assert counts["Resort Hotel"] == 384
    assert counts["City Hotel"] == 331
    assert len(zeros) == 715
    night_sum = (
        analysis_ready["StaysInWeekendNights"].astype("int64")
        + analysis_ready["StaysInWeekNights"].astype("int64")
    )
    assert (analysis_ready["TotalNights"] == night_sum).all()
    assert (analysis_ready["TotalNights"] >= 0).all()


def test_published_duplicate_conventions(analysis_ready: pd.DataFrame) -> None:
    convention_a = apply_counting_convention(analysis_ready, COUNTING_ALL_PUBLISHED_ROWS)
    convention_b = apply_counting_convention(analysis_ready, COUNTING_EXACT_ROW_DEDUPLICATED)
    assert len(convention_a) == 119_390
    assert convention_a[HOTEL_COLUMN].value_counts().to_dict() == {
        "City Hotel": 79_330,
        "Resort Hotel": 40_060,
    }
    assert len(convention_b) == 87_396
    assert convention_b[HOTEL_COLUMN].value_counts().to_dict() == {
        "City Hotel": 53_428,
        "Resort Hotel": 33_968,
    }
    in_duplicate_group = analysis_ready["IsExactDuplicate"]
    assert int(in_duplicate_group.sum()) == 8_417 + 31_748


def test_published_adr_flags(analysis_ready: pd.DataFrame) -> None:
    resort = analysis_ready.loc[analysis_ready[HOTEL_COLUMN] == "Resort Hotel"]
    city = analysis_ready.loc[analysis_ready[HOTEL_COLUMN] == "City Hotel"]
    assert int(resort["ADRIsNegative"].sum()) == 1
    assert int(resort["ADRIsZero"].sum()) == 751
    assert int(resort["ADRIsExtremeHigh"].sum()) == 0
    assert int(city["ADRIsNegative"].sum()) == 0
    assert int(city["ADRIsZero"].sum()) == 1_208
    assert int(city["ADRIsExtremeHigh"].sum()) == 1
    assert float(resort.loc[resort["ADRIsNegative"], "ADR"].iloc[0]) == pytest.approx(-6.38)
    assert float(city.loc[city["ADRIsExtremeHigh"], "ADR"].iloc[0]) == pytest.approx(5400.0)
    assert len(analysis_ready) == 119_390


def test_published_booking_outcome_and_complete_year(analysis_ready: pd.DataFrame) -> None:
    assert (analysis_ready["BookingOutcome"] == analysis_ready["ReservationStatus"]).all()
    assert set(analysis_ready["BookingOutcome"].unique()) == {"Check-Out", "Canceled", "No-Show"}
    complete = analysis_ready.loc[analysis_ready["IsCompleteYear"]]
    assert set(complete["ArrivalDateYear"].unique()) == {2016}
    assert int((~analysis_ready["IsCompleteYear"]).sum()) == int(
        analysis_ready["ArrivalDateYear"].ne(2016).sum()
    )
    counts = complete[HOTEL_COLUMN].value_counts().to_dict()
    assert counts["Resort Hotel"] == 18_567
    assert counts["City Hotel"] == 38_140

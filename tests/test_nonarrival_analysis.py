"""Tests for descriptive non-arrival analysis functions, not figure appearance."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hospitality_analytics.commercial_profile import windowed_convention
from hospitality_analytics.data_loader import HOTEL_COLUMN, PUBLISHED_COLUMNS
from hospitality_analytics.nonarrival_analysis import (
    BOOKING_OUTCOMES,
    DEPOSIT_TYPE_ORDER,
    grouped_outcome_rates,
    hotel_outcome_summary,
    is_nonarrival,
    leakage_diagnostic,
    outcome_rate_row,
    parking_separation,
)
from hospitality_analytics.transform import (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
    LEAD_TIME_BANDS,
    add_analysis_fields,
)

_DEFAULTS: dict[str, object] = {
    "IsCanceled": 0,
    "LeadTime": 10,
    "ArrivalDateYear": 2016,
    "ArrivalDateMonth": "July",
    "ArrivalDateWeekNumber": 28,
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
    if "ReservationStatus" in overrides:
        status = str(overrides["ReservationStatus"])
        values["IsCanceled"] = 0 if status == "Check-Out" else 1
    return {column: values[column] for column in (HOTEL_COLUMN, *PUBLISHED_COLUMNS)}


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return add_analysis_fields(pd.DataFrame(rows))


def test_three_way_rates_sum_to_one() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Check-Out"),
            _row(ReservationStatus="Check-Out"),
            _row(ReservationStatus="Canceled"),
            _row(ReservationStatus="No-Show"),
        ]
    )
    summary = hotel_outcome_summary(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    row = summary.iloc[0]
    assert row["checkout_rate"] + row["canceled_rate"] + row["noshow_rate"] == pytest.approx(1.0)
    assert set(BOOKING_OUTCOMES) == {"Check-Out", "Canceled", "No-Show"}


def test_nonarrival_equals_canceled_plus_noshow() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Check-Out"),
            _row(ReservationStatus="Canceled"),
            _row(ReservationStatus="Canceled"),
            _row(ReservationStatus="No-Show"),
        ]
    )
    summary = hotel_outcome_summary(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    row = summary.iloc[0]
    assert row["nonarrival_count"] == row["canceled_count"] + row["noshow_count"]
    assert row["nonarrival_rate"] == pytest.approx(row["canceled_rate"] + row["noshow_rate"])
    assert row["row_count"] == 4
    assert row["canceled_count"] == 2
    assert row["noshow_count"] == 1
    assert row["nonarrival_rate"] == pytest.approx(0.75)


def test_synthetic_group_rates_and_denominators() -> None:
    frame = _frame(
        [
            _row(MarketSegment="Groups", ReservationStatus="Canceled"),
            _row(MarketSegment="Groups", ReservationStatus="Canceled"),
            _row(MarketSegment="Groups", ReservationStatus="Check-Out"),
            _row(MarketSegment="Direct", ReservationStatus="Check-Out"),
        ]
    )
    table = grouped_outcome_rates(
        frame,
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        category_order=("Direct", "Groups"),
    )
    groups = table.loc[table["category"] == "Groups"].iloc[0]
    direct = table.loc[table["category"] == "Direct"].iloc[0]
    assert groups["row_count"] == 3
    assert groups["canceled_rate"] == pytest.approx(2 / 3)
    assert direct["row_count"] == 1
    assert direct["checkout_rate"] == pytest.approx(1.0)


def test_outcomes_not_mutated_and_labels_preserved() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Check-Out"),
            _row(ReservationStatus="Canceled"),
            _row(ReservationStatus="No-Show"),
        ]
    )
    snapshot = frame.copy(deep=True)
    hotel_outcome_summary(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    grouped_outcome_rates(frame, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    pd.testing.assert_frame_equal(frame, snapshot)
    assert set(frame["BookingOutcome"]) == {"Check-Out", "Canceled", "No-Show"}


def test_conventions_a_and_b_remain_separate() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Canceled", LeadTime=200),
            _row(ReservationStatus="Canceled", LeadTime=200),
            _row(ReservationStatus="Check-Out", LeadTime=1),
        ]
    )
    convention_a = windowed_convention(frame, COUNTING_ALL_PUBLISHED_ROWS)
    convention_b = windowed_convention(frame, COUNTING_EXACT_ROW_DEDUPLICATED)
    summary_a = hotel_outcome_summary(convention_a, convention=COUNTING_ALL_PUBLISHED_ROWS).iloc[0]
    summary_b = hotel_outcome_summary(convention_b, convention=COUNTING_EXACT_ROW_DEDUPLICATED).iloc[0]
    assert summary_a["row_count"] == 3
    assert summary_b["row_count"] == 2
    assert summary_a["canceled_rate"] == pytest.approx(2 / 3)
    assert summary_b["canceled_rate"] == pytest.approx(0.5)


def test_2016_window_counts_on_published_extract() -> None:
    from hospitality_analytics.nonarrival_analysis import build_2016_nonarrival_profile
    from hospitality_analytics.transform import prepare_analysis_data

    profile = build_2016_nonarrival_profile(prepare_analysis_data())
    hotel = profile["hotel_summary"]
    published_a = hotel.loc[hotel["convention_label"] == "A"]
    resort = published_a.loc[published_a["hotel"] == "Resort Hotel"].iloc[0]
    city = published_a.loc[published_a["hotel"] == "City Hotel"].iloc[0]
    assert resort["row_count"] == 18_567
    assert city["row_count"] == 38_140
    assert resort["canceled_count"] + resort["noshow_count"] == resort["nonarrival_count"]
    assert city["canceled_count"] + city["noshow_count"] == city["nonarrival_count"]
    assert resort["checkout_count"] + resort["canceled_count"] + resort["noshow_count"] == 18_567
    published_b = hotel.loc[hotel["convention_label"] == "B"]
    assert int(published_b.loc[published_b["hotel"] == "Resort Hotel", "row_count"].iloc[0]) == 15_632
    assert int(published_b.loc[published_b["hotel"] == "City Hotel", "row_count"].iloc[0]) == 26_759


def test_groups_segment_not_conflated_with_customer_type_group() -> None:
    frame = _frame(
        [
            _row(MarketSegment="Groups", CustomerType="Transient", ReservationStatus="Canceled"),
            _row(MarketSegment="Online TA", CustomerType="Group", ReservationStatus="Check-Out"),
        ]
    )
    segments = grouped_outcome_rates(frame, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    customers = grouped_outcome_rates(frame, "CustomerType", convention=COUNTING_ALL_PUBLISHED_ROWS)
    assert "Groups" in set(segments["category"])
    assert "Group" not in set(segments["category"])
    assert "Group" in set(customers["category"])
    assert "Groups" not in set(customers["category"])


def test_lead_time_band_order_preserved() -> None:
    frame = _frame(
        [
            _row(LeadTime=0, ReservationStatus="Check-Out"),
            _row(LeadTime=3, ReservationStatus="Canceled"),
            _row(LeadTime=20, ReservationStatus="Check-Out"),
            _row(LeadTime=40, ReservationStatus="Canceled"),
            _row(LeadTime=120, ReservationStatus="Check-Out"),
            _row(LeadTime=200, ReservationStatus="Canceled"),
        ]
    )
    table = grouped_outcome_rates(
        frame,
        "LeadTimeBand",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        category_order=LEAD_TIME_BANDS,
    )
    assert table["category"].tolist() == [band for band in LEAD_TIME_BANDS if band in set(table["category"])]


def test_deposit_type_categories_preserved() -> None:
    frame = _frame(
        [
            _row(DepositType="No Deposit", ReservationStatus="Check-Out"),
            _row(DepositType="Non Refund", ReservationStatus="Canceled"),
            _row(DepositType="Refundable", ReservationStatus="Check-Out"),
        ]
    )
    table = grouped_outcome_rates(
        frame,
        "DepositType",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        category_order=DEPOSIT_TYPE_ORDER,
    )
    assert table["category"].tolist() == list(DEPOSIT_TYPE_ORDER)


def test_parking_separation_on_published_extract() -> None:
    from hospitality_analytics.transform import prepare_analysis_data

    analysis_ready = prepare_analysis_data()
    parked = parking_separation(analysis_ready)
    combined = parked.loc[parked["hotel"] == "combined"].iloc[0]
    assert combined["parking_positive_count"] == 7416
    assert combined["nonarrival_count"] == 0
    assert combined["canceled_count"] == 0
    assert combined["noshow_count"] == 0
    assert combined["checkout_count"] == 7416
    window = analysis_ready.loc[analysis_ready["IsCompleteYear"]]
    parked_2016 = parking_separation(window)
    assert int(parked_2016.loc[parked_2016["hotel"] == "combined", "nonarrival_count"].iloc[0]) == 0


def test_rates_do_not_depend_on_adr_or_weekend_nights() -> None:
    base = _frame(
        [
            _row(ADR=80.0, StaysInWeekendNights=1, ReservationStatus="Canceled"),
            _row(ADR=80.0, StaysInWeekendNights=1, ReservationStatus="Check-Out", LeadTime=3),
        ]
    )
    changed = base.copy()
    changed["ADR"] = [5400.0, -6.38]
    changed["StaysInWeekendNights"] = [9, 9]
    summary_base = hotel_outcome_summary(base, convention=COUNTING_ALL_PUBLISHED_ROWS)
    summary_changed = hotel_outcome_summary(changed, convention=COUNTING_ALL_PUBLISHED_ROWS)
    pd.testing.assert_series_equal(
        summary_base.drop(columns=["hotel", "category"]).iloc[0],
        summary_changed.drop(columns=["hotel", "category"]).iloc[0],
    )


def test_is_nonarrival_does_not_use_iscanceled_alone() -> None:
    outcomes = pd.Series(["Check-Out", "Canceled", "No-Show"])
    flags = is_nonarrival(outcomes)
    assert flags.tolist() == [False, True, True]


def test_leakage_table_includes_parking() -> None:
    from hospitality_analytics.transform import prepare_analysis_data

    table = leakage_diagnostic(prepare_analysis_data())
    parking_full = table.loc[
        (table["variable"] == "RequiredCarParkingSpaces")
        & (table["window"] == "full extract")
        & (table["hotel"] == "combined")
        & (table["subset"] == "> 0")
    ].iloc[0]
    assert parking_full["nonarrival_count"] == 0
    assert parking_full["row_count"] == 7416


def test_outcome_rate_row_small_example() -> None:
    outcomes = pd.Series(["Check-Out", "Canceled", "No-Show", "Check-Out"])
    row = outcome_rate_row(
        outcomes,
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        hotel="Resort Hotel",
        category_column="Hotel",
        category="Resort Hotel",
    )
    assert row["row_count"] == 4
    assert row["checkout_rate"] == pytest.approx(0.5)
    assert row["canceled_rate"] == pytest.approx(0.25)
    assert row["noshow_rate"] == pytest.approx(0.25)
    assert row["nonarrival_rate"] == pytest.approx(0.5)


def test_module_source_does_not_use_adr_or_weekend_as_weekend() -> None:
    source = Path("src/hospitality_analytics/nonarrival_analysis.py").read_text(encoding="utf-8")
    assert "ADR" not in source
    assert "StaysInWeekendNights" not in source
    assert "IsCanceled" not in source

"""Tests for quoted-ADR analysis functions, not figure appearance."""

from __future__ import annotations

import pandas as pd
import pytest

from hospitality_analytics.adr_analysis import (
    ADR_VIEW_POSITIVE,
    ADR_VIEW_POSITIVE_EXCLUDING_5400,
    ADR_VIEW_PUBLISHED,
    adr_distribution,
    adr_view,
    grouped_adr_summary,
    zero_adr_diagnostic,
)
from hospitality_analytics.commercial_profile import windowed_convention
from hospitality_analytics.data_loader import HOTEL_COLUMN, PUBLISHED_COLUMNS
from hospitality_analytics.transform import (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
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
    return {column: values[column] for column in (HOTEL_COLUMN, *PUBLISHED_COLUMNS)}


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return add_analysis_fields(pd.DataFrame(rows))


def test_published_view_preserves_zero_negative_and_5400() -> None:
    frame = _frame(
        [
            _row(ADR=0.0),
            _row(ADR=-6.38, ArrivalDateYear=2017, ArrivalDateMonth="March", ArrivalDateDayOfMonth=5),
            _row(hotel="City Hotel", ADR=5400.0),
            _row(ADR=80.0),
        ]
    )
    published = adr_view(frame, ADR_VIEW_PUBLISHED)
    assert len(published) == 4
    assert published["ADR"].tolist() == pytest.approx([0.0, -6.38, 5400.0, 80.0])
    assert int((published["ADR"] == 0).sum()) == 1
    assert int((published["ADR"] < 0).sum()) == 1
    assert int((published["ADR"] == 5400).sum()) == 1
    assert published["ADR"].isna().sum() == 0


def test_positive_view_keeps_only_adr_above_zero() -> None:
    frame = _frame(
        [
            _row(ADR=0.0),
            _row(ADR=-6.38, ArrivalDateYear=2017, ArrivalDateMonth="March", ArrivalDateDayOfMonth=5),
            _row(hotel="City Hotel", ADR=5400.0),
            _row(ADR=80.0),
        ]
    )
    positive = adr_view(frame, ADR_VIEW_POSITIVE)
    assert (positive["ADR"] > 0).all()
    assert 0.0 not in positive["ADR"].tolist()
    assert -6.38 not in [float(v) for v in positive["ADR"].tolist()]
    assert 5400.0 in positive["ADR"].tolist()
    excluded = adr_view(frame, ADR_VIEW_POSITIVE_EXCLUDING_5400)
    assert 5400.0 not in excluded["ADR"].tolist()
    assert 80.0 in excluded["ADR"].tolist()


def test_adr_views_do_not_mutate_input() -> None:
    frame = _frame([_row(ADR=0.0), _row(ADR=5400.0, hotel="City Hotel")])
    snapshot = frame.copy(deep=True)
    adr_view(frame, ADR_VIEW_POSITIVE)
    adr_distribution(frame, convention=COUNTING_ALL_PUBLISHED_ROWS, view=ADR_VIEW_PUBLISHED)
    pd.testing.assert_frame_equal(frame, snapshot)


def test_median_quartiles_on_synthetic_adr() -> None:
    frame = _frame(
        [
            _row(ADR=10.0),
            _row(ADR=20.0),
            _row(ADR=30.0),
            _row(ADR=40.0),
        ]
    )
    summary = adr_distribution(frame, convention=COUNTING_ALL_PUBLISHED_ROWS, view=ADR_VIEW_PUBLISHED)
    resort = summary.loc[summary["hotel"] == "Resort Hotel"].iloc[0]
    assert resort["median"] == pytest.approx(25.0)
    assert resort["q1"] == pytest.approx(17.5)
    assert resort["q3"] == pytest.approx(32.5)
    assert resort["iqr"] == pytest.approx(15.0)
    assert resort["row_count"] == 4


def test_grouped_counts_use_the_filtered_view() -> None:
    frame = _frame(
        [
            _row(MarketSegment="Groups", ADR=0.0),
            _row(MarketSegment="Groups", ADR=50.0),
            _row(MarketSegment="Online TA", ADR=100.0),
        ]
    )
    published = grouped_adr_summary(
        adr_view(frame, ADR_VIEW_PUBLISHED),
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        view=ADR_VIEW_PUBLISHED,
    )
    positive = grouped_adr_summary(
        adr_view(frame, ADR_VIEW_POSITIVE),
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        view=ADR_VIEW_POSITIVE,
    )
    groups_pub = published.loc[published["category"] == "Groups", "row_count"].iloc[0]
    groups_pos = positive.loc[positive["category"] == "Groups", "row_count"].iloc[0]
    assert groups_pub == 2
    assert groups_pos == 1
    assert published.loc[published["category"] == "Groups", "median"].iloc[0] == pytest.approx(25.0)


def test_zero_adr_is_not_converted_to_missing() -> None:
    frame = _frame([_row(ADR=0.0, MarketSegment="Complementary"), _row(ADR=80.0)])
    diagnostic = zero_adr_diagnostic(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    hotel_row = diagnostic.loc[diagnostic["dimension"] == "Hotel"].iloc[0]
    assert hotel_row["zero_count"] == 1
    assert frame.loc[frame["ADR"] == 0, "ADR"].iloc[0] == 0
    assert not frame.loc[frame["ADR"] == 0, "ADR"].isna().any()


def test_groups_segment_not_conflated_with_customer_type_group() -> None:
    frame = _frame(
        [
            _row(MarketSegment="Groups", CustomerType="Transient", ADR=60.0),
            _row(MarketSegment="Online TA", CustomerType="Group", ADR=90.0),
        ]
    )
    segments = grouped_adr_summary(
        frame,
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        view=ADR_VIEW_PUBLISHED,
    )
    customers = grouped_adr_summary(
        frame,
        "CustomerType",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        view=ADR_VIEW_PUBLISHED,
    )
    assert "Groups" in set(segments["category"])
    assert "Group" not in set(segments["category"])
    assert "Group" in set(customers["category"])
    assert "Groups" not in set(customers["category"])


def test_outcomes_remain_three_way() -> None:
    frame = _frame(
        [
            _row(ReservationStatus="Check-Out", IsCanceled=0, ADR=70.0),
            _row(ReservationStatus="Canceled", IsCanceled=1, ADR=90.0),
            _row(ReservationStatus="No-Show", IsCanceled=1, ADR=50.0),
        ]
    )
    table = grouped_adr_summary(
        frame,
        "BookingOutcome",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
        view=ADR_VIEW_PUBLISHED,
        category_order=("Check-Out", "Canceled", "No-Show"),
    )
    assert set(table["category"]) == {"Check-Out", "Canceled", "No-Show"}
    assert len(table) == 3


def test_conventions_a_and_b_remain_separate() -> None:
    frame = _frame(
        [
            _row(ADR=40.0, LeadTime=5),
            _row(ADR=40.0, LeadTime=5),
            _row(ADR=100.0, LeadTime=9),
        ]
    )
    convention_a = windowed_convention(frame, COUNTING_ALL_PUBLISHED_ROWS)
    convention_b = windowed_convention(frame, COUNTING_EXACT_ROW_DEDUPLICATED)
    summary_a = adr_distribution(convention_a, convention=COUNTING_ALL_PUBLISHED_ROWS, view=ADR_VIEW_PUBLISHED)
    summary_b = adr_distribution(convention_b, convention=COUNTING_EXACT_ROW_DEDUPLICATED, view=ADR_VIEW_PUBLISHED)
    assert int(summary_a.loc[summary_a["hotel"] == "Resort Hotel", "row_count"].iloc[0]) == 3
    assert int(summary_b.loc[summary_b["hotel"] == "Resort Hotel", "row_count"].iloc[0]) == 2
    assert summary_a["median"].iloc[0] == pytest.approx(40.0)
    assert summary_b["median"].iloc[0] == pytest.approx(70.0)


def test_published_2016_window_and_anomaly_locations() -> None:
    from hospitality_analytics.adr_analysis import anomaly_status, build_2016_adr_profile
    from hospitality_analytics.transform import prepare_analysis_data

    analysis_ready = prepare_analysis_data()
    anomalies = anomaly_status(analysis_ready)
    negative = anomalies.loc[anomalies["anomaly"] == "ADR < 0"].iloc[0]
    extreme = anomalies.loc[anomalies["anomaly"] == "ADR = 5400"].iloc[0]
    assert negative["in_2016_window"] == False
    assert negative["arrival_year"] == 2017
    assert extreme["in_2016_window"] == True
    assert extreme["arrival_year"] == 2016

    profile = build_2016_adr_profile(analysis_ready)
    hotel = profile["hotel_summary"]
    published_a = hotel.loc[
        (hotel["convention_label"] == "A")
        & (hotel["adr_view"] == ADR_VIEW_PUBLISHED)
    ]
    resort = published_a.loc[published_a["hotel"] == "Resort Hotel"].iloc[0]
    city = published_a.loc[published_a["hotel"] == "City Hotel"].iloc[0]
    assert resort["row_count"] == 18_567
    assert city["row_count"] == 38_140
    assert resort["negative_count"] == 0
    assert city["extreme_high_5400_count"] == 1
    assert resort["zero_count"] == 382
    assert city["zero_count"] == 536
    positive_a = hotel.loc[
        (hotel["convention_label"] == "A")
        & (hotel["adr_view"] == ADR_VIEW_POSITIVE)
        & (hotel["hotel"] == "City Hotel")
    ].iloc[0]
    assert positive_a["minimum"] > 0
    assert positive_a["extreme_high_5400_count"] == 1

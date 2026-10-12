"""Tests for 2016 commercial-profile calculations, not figure appearance."""

from __future__ import annotations

import pandas as pd
import pytest

from hospitality_analytics.data_loader import HOTEL_COLUMN, PUBLISHED_COLUMNS
from hospitality_analytics.transform import (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
    add_analysis_fields,
)
from hospitality_analytics.commercial_profile import (
    PRIMARY_YEAR,
    complete_calendar_year,
    composition_table,
    lead_time_band_table,
    numeric_distribution,
    stay_length_bucket_table,
    windowed_convention,
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


def _analysis_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return add_analysis_fields(pd.DataFrame(rows))


def test_complete_year_filter_uses_2016_only() -> None:
    frame = _analysis_frame(
        [
            _row(ArrivalDateYear=2015, ArrivalDateMonth="July", ArrivalDateDayOfMonth=1),
            _row(ArrivalDateYear=2016, ArrivalDateMonth="March", ArrivalDateDayOfMonth=2),
            _row(ArrivalDateYear=2017, ArrivalDateMonth="August", ArrivalDateDayOfMonth=3),
        ]
    )
    window = complete_calendar_year(frame)
    assert PRIMARY_YEAR == 2016
    assert set(window["ArrivalDateYear"].unique()) == {2016}
    assert len(window) == 1
    assert (window["IsCompleteYear"]).all()


def test_composition_shares_sum_to_one_within_hotel_and_convention() -> None:
    frame = _analysis_frame(
        [
            _row(hotel="Resort Hotel", MarketSegment="Online TA"),
            _row(hotel="Resort Hotel", MarketSegment="Online TA"),
            _row(hotel="Resort Hotel", MarketSegment="Groups"),
            _row(hotel="City Hotel", MarketSegment="Direct"),
            _row(hotel="City Hotel", MarketSegment="Aviation"),
            _row(hotel="City Hotel", MarketSegment="Aviation"),
        ]
    )
    table = composition_table(
        frame,
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
    )
    for hotel, subset in table.groupby("hotel"):
        assert subset["share"].sum() == pytest.approx(1.0)
        assert (subset["hotel_row_count"] == subset["row_count"].sum()).all()
        assert set(subset["convention"]) == {COUNTING_ALL_PUBLISHED_ROWS}


def test_conventions_a_and_b_are_not_mixed() -> None:
    frame = _analysis_frame(
        [
            _row(hotel="Resort Hotel", LeadTime=4, MarketSegment="Groups"),
            _row(hotel="Resort Hotel", LeadTime=4, MarketSegment="Groups"),
            _row(hotel="Resort Hotel", LeadTime=9, MarketSegment="Online TA"),
            _row(hotel="City Hotel", LeadTime=4, MarketSegment="Groups"),
        ]
    )
    convention_a = windowed_convention(frame, COUNTING_ALL_PUBLISHED_ROWS)
    convention_b = windowed_convention(frame, COUNTING_EXACT_ROW_DEDUPLICATED)
    assert len(convention_a) == 4
    assert len(convention_b) == 3
    share_a = composition_table(convention_a, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    share_b = composition_table(convention_b, "MarketSegment", convention=COUNTING_EXACT_ROW_DEDUPLICATED)
    resort_a = share_a.loc[
        (share_a["hotel"] == "Resort Hotel") & (share_a["category"] == "Groups"),
        "share",
    ].iloc[0]
    resort_b = share_b.loc[
        (share_b["hotel"] == "Resort Hotel") & (share_b["category"] == "Groups"),
        "share",
    ].iloc[0]
    assert resort_a == pytest.approx(2 / 3)
    assert resort_b == pytest.approx(0.5)
    assert set(share_a["convention_label"]) == {"A"}
    assert set(share_b["convention_label"]) == {"B"}


def test_groups_segment_is_not_conflated_with_customer_type_group() -> None:
    frame = _analysis_frame(
        [
            _row(MarketSegment="Groups", CustomerType="Transient"),
            _row(MarketSegment="Online TA", CustomerType="Group"),
        ]
    )
    segments = composition_table(frame, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    customers = composition_table(frame, "CustomerType", convention=COUNTING_ALL_PUBLISHED_ROWS)
    assert "Groups" in set(segments["category"])
    assert "Group" not in set(segments["category"])
    assert "Group" in set(customers["category"])
    assert "Groups" not in set(customers["category"])
    groups_share = segments.loc[segments["category"] == "Groups", "share"].iloc[0]
    group_share = customers.loc[customers["category"] == "Group", "share"].iloc[0]
    assert groups_share == pytest.approx(0.5)
    assert group_share == pytest.approx(0.5)


def test_undefined_and_aviation_categories_are_preserved() -> None:
    frame = _analysis_frame(
        [
            _row(
                hotel="City Hotel",
                MarketSegment="Undefined",
                DistributionChannel="Undefined",
            ),
            _row(
                hotel="City Hotel",
                MarketSegment="Aviation",
                DistributionChannel="GDS",
            ),
        ]
    )
    segments = composition_table(frame, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    channels = composition_table(frame, "DistributionChannel", convention=COUNTING_ALL_PUBLISHED_ROWS)
    assert set(segments["category"]) == {"Undefined", "Aviation"}
    assert set(channels["category"]) == {"Undefined", "GDS"}


def test_median_and_iqr_on_synthetic_lead_time_and_nights() -> None:
    frame = _analysis_frame(
        [
            _row(LeadTime=0, StaysInWeekendNights=0, StaysInWeekNights=1),
            _row(LeadTime=10, StaysInWeekendNights=1, StaysInWeekNights=2),
            _row(LeadTime=20, StaysInWeekendNights=2, StaysInWeekNights=5),
            _row(LeadTime=40, StaysInWeekendNights=0, StaysInWeekNights=7),
        ]
    )
    lead = numeric_distribution(frame, "LeadTime", convention=COUNTING_ALL_PUBLISHED_ROWS)
    stay = numeric_distribution(frame, "TotalNights", convention=COUNTING_ALL_PUBLISHED_ROWS)
    resort_lead = lead.loc[lead["hotel"] == "Resort Hotel"].iloc[0]
    resort_stay = stay.loc[stay["hotel"] == "Resort Hotel"].iloc[0]
    assert resort_lead["variable"] == "LeadTime"
    assert resort_stay["variable"] == "TotalNights"
    assert resort_lead["median"] == pytest.approx(15.0)
    assert resort_lead["q1"] == pytest.approx(7.5)
    assert resort_lead["q3"] == pytest.approx(25.0)
    assert resort_lead["iqr"] == pytest.approx(17.5)
    assert resort_stay["median"] == pytest.approx(5.0)
    assert "mean" not in lead.columns


def test_lead_time_bands_and_total_nights_fields() -> None:
    frame = _analysis_frame(
        [
            _row(LeadTime=0, StaysInWeekendNights=0, StaysInWeekNights=0),
            _row(LeadTime=181, StaysInWeekendNights=2, StaysInWeekNights=5),
        ]
    )
    bands = lead_time_band_table(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    stays = stay_length_bucket_table(frame, convention=COUNTING_ALL_PUBLISHED_ROWS)
    assert bands["category_column"].eq("LeadTimeBand").all()
    assert set(bands["category"]) >= {"0 days", "181+ days"}
    zero_nights = stays.loc[stays["category"] == "0", "share"].iloc[0]
    seven_nights = stays.loc[stays["category"] == "7", "share"].iloc[0]
    assert zero_nights == pytest.approx(0.5)
    assert seven_nights == pytest.approx(0.5)


def test_profile_functions_do_not_mutate_input() -> None:
    frame = _analysis_frame(
        [
            _row(MarketSegment="Groups", CustomerType="Transient"),
            _row(MarketSegment="Online TA", CustomerType="Group"),
        ]
    )
    snapshot = frame.copy(deep=True)
    complete_calendar_year(frame)
    windowed_convention(frame, COUNTING_EXACT_ROW_DEDUPLICATED)
    composition_table(frame, "MarketSegment", convention=COUNTING_ALL_PUBLISHED_ROWS)
    numeric_distribution(frame, "LeadTime", convention=COUNTING_ALL_PUBLISHED_ROWS)
    pd.testing.assert_frame_equal(frame, snapshot)


def test_published_2016_window_counts_under_a_and_b() -> None:
    from hospitality_analytics.transform import prepare_analysis_data

    analysis_ready = prepare_analysis_data()
    convention_a = windowed_convention(analysis_ready, COUNTING_ALL_PUBLISHED_ROWS)
    convention_b = windowed_convention(analysis_ready, COUNTING_EXACT_ROW_DEDUPLICATED)
    assert convention_a["ArrivalDateYear"].eq(2016).all()
    assert convention_b["ArrivalDateYear"].eq(2016).all()
    assert convention_a[HOTEL_COLUMN].value_counts().to_dict() == {
        "City Hotel": 38_140,
        "Resort Hotel": 18_567,
    }
    assert convention_b[HOTEL_COLUMN].value_counts().to_dict() == {
        "City Hotel": 26_759,
        "Resort Hotel": 15_632,
    }
    shares = composition_table(
        convention_a,
        "CustomerType",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
    )
    assert "Group" in set(shares["category"])
    market = composition_table(
        convention_a,
        "MarketSegment",
        convention=COUNTING_ALL_PUBLISHED_ROWS,
    )
    assert "Groups" in set(market["category"])

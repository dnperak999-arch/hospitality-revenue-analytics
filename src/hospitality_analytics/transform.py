"""Analysis-ready fields derived from the loaded booking extract.

This module does not replace the published files.

- Raw data: the unchanged CSVs in ``data/raw/``, loaded by ``data_loader``.
- Analysis-ready transformations: documented columns added here. No rows are
  dropped, ADR is not recoded, and occupancy / RevPAR / revenue are not
  computed.
- Analytical filtering: later analysis may subset by year or counting
  convention. That is not done here.

``StaysInWeekendNights`` is not reinterpreted as Saturday/Sunday demand.
Total stay length uses the stored night fields only because they sum
consistently.

Exact-duplicate counting is a sensitivity convention, not a claim about
the true number of bookings:

- ALL_PUBLISHED_ROWS: every published row.
- EXACT_ROW_DEDUPLICATED: one row per exact 31-column combination
  within each hotel. This is not "clean data" and not "true bookings".
"""

from __future__ import annotations

import pandas as pd

from hospitality_analytics.data_loader import (
    EXPECTED_ROW_COUNTS,
    HOTEL_COLUMN,
    PUBLISHED_COLUMNS,
    DataValidationError,
    load_bookings,
)

COUNTING_ALL_PUBLISHED_ROWS = "ALL_PUBLISHED_ROWS"
COUNTING_EXACT_ROW_DEDUPLICATED = "EXACT_ROW_DEDUPLICATED"

LEAD_TIME_BANDS: tuple[str, ...] = (
    "0 days",
    "1–7 days",
    "8–30 days",
    "31–90 days",
    "91–180 days",
    "181+ days",
)

BOOKING_OUTCOMES: tuple[str, ...] = ("Check-Out", "Canceled", "No-Show")

DERIVED_COLUMNS: tuple[str, ...] = (
    "ArrivalDate",
    "TotalNights",
    "LeadTimeBand",
    "BookingOutcome",
    "ExactDuplicateGroupSize",
    "IsExactDuplicate",
    "ADRIsZero",
    "ADRIsNegative",
    "ADRIsExtremeHigh",
    "IsCompleteYear",
    "IsJulyAugustArrival",
)

# Verified on the published extract (Phase 1 audit). Used only when
# prepare_analysis_data() loads that extract.
EXPECTED_ZERO_NIGHT_COUNTS: dict[str, int] = {
    "Resort Hotel": 384,
    "City Hotel": 331,
}
EXPECTED_DEDUPLICATED_COUNTS: dict[str, int] = {
    "Resort Hotel": 33_968,
    "City Hotel": 53_428,
}
EXPECTED_ADR_FLAG_COUNTS: dict[str, dict[str, int]] = {
    "Resort Hotel": {"negative": 1, "zero": 751, "extreme_high": 0},
    "City Hotel": {"negative": 0, "zero": 1_208, "extreme_high": 1},
}

_DUPLICATE_KEYS: tuple[str, ...] = (HOTEL_COLUMN, *PUBLISHED_COLUMNS)


def lead_time_band(lead_time: pd.Series) -> pd.Series:
    """Map integer lead time to the project's ordered booking-window bands.

    Boundaries (inclusive):

    - 0 → ``0 days``
    - 1–7 → ``1–7 days``
    - 8–30 → ``8–30 days``
    - 31–90 → ``31–90 days``
    - 91–180 → ``91–180 days``
    - 181 and above → ``181+ days``
    """
    values = pd.to_numeric(lead_time, errors="raise")
    labels = pd.Series(pd.NA, index=values.index, dtype="object")
    labels.loc[values.eq(0)] = "0 days"
    labels.loc[(values >= 1) & (values <= 7)] = "1–7 days"
    labels.loc[(values >= 8) & (values <= 30)] = "8–30 days"
    labels.loc[(values >= 31) & (values <= 90)] = "31–90 days"
    labels.loc[(values >= 91) & (values <= 180)] = "91–180 days"
    labels.loc[values >= 181] = "181+ days"
    if labels.isna().any():
        raise DataValidationError("LeadTimeBand could not be assigned for every row.")
    return pd.Categorical(labels, categories=LEAD_TIME_BANDS, ordered=True)


def add_analysis_fields(bookings: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``bookings`` with documented derived columns.

    The input frame is not modified. All original columns and rows are kept.
    """
    required = [HOTEL_COLUMN, *PUBLISHED_COLUMNS]
    missing = [column for column in required if column not in bookings.columns]
    if missing:
        raise DataValidationError(f"Input is missing required columns: {missing}.")

    out = bookings.copy()
    original_row_count = len(out)

    out["ArrivalDate"] = _arrival_date(out)
    out["TotalNights"] = (
        out["StaysInWeekendNights"].astype("int64") + out["StaysInWeekNights"].astype("int64")
    )
    out["LeadTimeBand"] = lead_time_band(out["LeadTime"])
    out["BookingOutcome"] = out["ReservationStatus"].astype("string")
    out["ExactDuplicateGroupSize"] = _exact_duplicate_group_size(out)
    out["IsExactDuplicate"] = out["ExactDuplicateGroupSize"] > 1
    out["ADRIsZero"] = out["ADR"] == 0
    out["ADRIsNegative"] = out["ADR"] < 0
    out["ADRIsExtremeHigh"] = out["ADR"] == 5400
    out["IsCompleteYear"] = out["ArrivalDateYear"] == 2016
    out["IsJulyAugustArrival"] = out["ArrivalDateMonth"].isin(["July", "August"])

    _validate_transformed(out, bookings, original_row_count)
    return out


def prepare_analysis_data(bookings: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the analysis-ready table from loader output.

    When ``bookings`` is omitted, the published extract is loaded and the
    verified dataset invariants are checked. Passing a frame skips those
    extract-level counts so unit tests can use synthetic rows.
    """
    loaded_published_extract = bookings is None
    if bookings is None:
        bookings = load_bookings()
    result = add_analysis_fields(bookings)
    if loaded_published_extract:
        _validate_published_extract(result)
    return result


def all_published_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Counting convention A: every row (119,390 in the published extract).

    This is not a preferred 'true' dataset. It is one counting convention.
    """
    return frame.copy()


def exact_row_deduplicated(frame: pd.DataFrame) -> pd.DataFrame:
    """Counting convention B: one row per exact 31-column combination within hotel.

    Keep-first is deterministic given the current row order. This is not
    clean data and not the true number of bookings.
    """
    return frame.drop_duplicates(subset=list(_DUPLICATE_KEYS), keep="first").copy()


def apply_counting_convention(frame: pd.DataFrame, convention: str) -> pd.DataFrame:
    """Return convention A or B. Neither result is claimed as ground truth."""
    if convention == COUNTING_ALL_PUBLISHED_ROWS:
        return all_published_rows(frame)
    if convention == COUNTING_EXACT_ROW_DEDUPLICATED:
        return exact_row_deduplicated(frame)
    raise DataValidationError(
        f"Unknown counting convention {convention!r}; expected "
        f"{COUNTING_ALL_PUBLISHED_ROWS!r} or {COUNTING_EXACT_ROW_DEDUPLICATED!r}."
    )


def _arrival_date(frame: pd.DataFrame) -> pd.Series:
    """Parse arrival dates from year, English month name, and day. Not week number."""
    text = (
        frame["ArrivalDateYear"].astype(str)
        + "-"
        + frame["ArrivalDateMonth"].astype(str)
        + "-"
        + frame["ArrivalDateDayOfMonth"].astype(str)
    )
    parsed = pd.to_datetime(text, format="%Y-%B-%d", errors="coerce")
    if parsed.isna().any():
        n_bad = int(parsed.isna().sum())
        raise DataValidationError(f"{n_bad} ArrivalDate values failed to parse.")
    return parsed


def _exact_duplicate_group_size(frame: pd.DataFrame) -> pd.Series:
    """Count exact 31-column copies within each hotel only.

    Identity uses the published columns. Hotel is a partition, not a
    published field: identical patterns in H1 and H2 are not grouped.
    Derived columns are not part of the key.
    """
    return (
        frame.groupby(list(_DUPLICATE_KEYS), dropna=False, sort=False)[HOTEL_COLUMN]
        .transform("size")
        .astype("int64")
    )


def _validate_transformed(
    out: pd.DataFrame,
    original: pd.DataFrame,
    original_row_count: int,
) -> None:
    if len(out) != original_row_count:
        raise DataValidationError("Transformation changed the number of rows.")
    missing_original = [column for column in original.columns if column not in out.columns]
    if missing_original:
        raise DataValidationError(f"Original columns were dropped: {missing_original}.")
    if not pd.api.types.is_datetime64_any_dtype(out["ArrivalDate"]):
        raise DataValidationError("ArrivalDate must be a pandas datetime type.")
    if out["ArrivalDate"].isna().any():
        raise DataValidationError("ArrivalDate contains missing values.")
    if (out["TotalNights"] < 0).any():
        raise DataValidationError("TotalNights contains negative values.")
    if not (out["BookingOutcome"] == out["ReservationStatus"]).all():
        raise DataValidationError("BookingOutcome must match ReservationStatus exactly.")
    unexpected_outcomes = set(out["BookingOutcome"].dropna().unique()) - set(BOOKING_OUTCOMES)
    if unexpected_outcomes:
        raise DataValidationError(f"Unexpected BookingOutcome values: {unexpected_outcomes}.")
    if not out["ADR"].equals(original["ADR"]):
        raise DataValidationError("ADR values were changed; they must be preserved.")
    if out["LeadTimeBand"].isna().any():
        raise DataValidationError("LeadTimeBand contains missing values.")


def _validate_published_extract(frame: pd.DataFrame) -> None:
    expected_total = EXPECTED_ROW_COUNTS["H1"] + EXPECTED_ROW_COUNTS["H2"]
    if len(frame) != expected_total:
        raise DataValidationError(
            f"Analysis-ready table has {len(frame)} rows; expected {expected_total}."
        )

    hotel_counts = frame[HOTEL_COLUMN].value_counts().to_dict()
    if hotel_counts.get("Resort Hotel") != EXPECTED_ROW_COUNTS["H1"]:
        raise DataValidationError("Resort Hotel row count no longer matches H1.")
    if hotel_counts.get("City Hotel") != EXPECTED_ROW_COUNTS["H2"]:
        raise DataValidationError("City Hotel row count no longer matches H2.")

    for hotel, expected in EXPECTED_ZERO_NIGHT_COUNTS.items():
        actual = int(((frame[HOTEL_COLUMN] == hotel) & (frame["TotalNights"] == 0)).sum())
        if actual != expected:
            raise DataValidationError(
                f"{hotel} zero-night rows are {actual}; expected {expected}."
            )

    deduplicated = exact_row_deduplicated(frame)
    dedup_counts = deduplicated[HOTEL_COLUMN].value_counts().to_dict()
    for hotel, expected in EXPECTED_DEDUPLICATED_COUNTS.items():
        actual = dedup_counts.get(hotel, 0)
        if actual != expected:
            raise DataValidationError(
                f"{hotel} exact-row-deduplicated count is {actual}; expected {expected}."
            )
    expected_dedup_total = sum(EXPECTED_DEDUPLICATED_COUNTS.values())
    if len(deduplicated) != expected_dedup_total:
        raise DataValidationError(
            f"Combined exact-row-deduplicated count is {len(deduplicated)}; "
            f"expected {expected_dedup_total}."
        )

    for hotel, expected in EXPECTED_ADR_FLAG_COUNTS.items():
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        actual = {
            "negative": int(subset["ADRIsNegative"].sum()),
            "zero": int(subset["ADRIsZero"].sum()),
            "extreme_high": int(subset["ADRIsExtremeHigh"].sum()),
        }
        if actual != expected:
            raise DataValidationError(
                f"{hotel} ADR flags are {actual}; expected {expected}."
            )

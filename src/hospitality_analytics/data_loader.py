"""Load the published Hotel Booking Demand CSVs.

Behaviour is intentionally narrow:

- Paths are resolved from the project root (the directory that contains
  ``pyproject.toml``), not from the current working directory.
- Original files under ``data/raw/`` are read only and never rewritten.
- Published column names are kept.
- The only added column is ``Hotel``, derived from the filename
  (H1 → Resort Hotel, H2 → City Hotel).
- Surrounding whitespace is stripped from every field.
- The tokens ``NULL`` and ``NA`` (after stripping) become missing values.
- All rows are kept, including exact duplicates.
- ADR and other numeric fields are converted in place; outliers are not
  removed or recoded.
- No occupancy, RevPAR, or revenue figures are computed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PUBLISHED_COLUMNS: tuple[str, ...] = (
    "IsCanceled",
    "LeadTime",
    "ArrivalDateYear",
    "ArrivalDateMonth",
    "ArrivalDateWeekNumber",
    "ArrivalDateDayOfMonth",
    "StaysInWeekendNights",
    "StaysInWeekNights",
    "Adults",
    "Children",
    "Babies",
    "Meal",
    "Country",
    "MarketSegment",
    "DistributionChannel",
    "IsRepeatedGuest",
    "PreviousCancellations",
    "PreviousBookingsNotCanceled",
    "ReservedRoomType",
    "AssignedRoomType",
    "BookingChanges",
    "DepositType",
    "Agent",
    "Company",
    "DaysInWaitingList",
    "CustomerType",
    "ADR",
    "RequiredCarParkingSpaces",
    "TotalOfSpecialRequests",
    "ReservationStatus",
    "ReservationStatusDate",
)

HOTEL_COLUMN = "Hotel"

HOTEL_LABELS: dict[str, str] = {
    "H1": "Resort Hotel",
    "H2": "City Hotel",
}

EXPECTED_ROW_COUNTS: dict[str, int] = {
    "H1": 40_060,
    "H2": 79_330,
}

# Exact extra copies (duplicated keep='first') in the published files.
EXPECTED_EXTRA_DUPLICATES: dict[str, int] = {
    "H1": 6_092,
    "H2": 25_902,
}

MISSING_TOKENS = {"NULL", "NA"}
ALLOWED_IS_CANCELED = {0, 1}
ALLOWED_RESERVATION_STATUS = {"Check-Out", "Canceled", "No-Show"}

INTEGER_COLUMNS: tuple[str, ...] = (
    "IsCanceled",
    "LeadTime",
    "ArrivalDateYear",
    "ArrivalDateWeekNumber",
    "ArrivalDateDayOfMonth",
    "StaysInWeekendNights",
    "StaysInWeekNights",
    "Adults",
    "Children",
    "Babies",
    "IsRepeatedGuest",
    "PreviousCancellations",
    "PreviousBookingsNotCanceled",
    "BookingChanges",
    "DaysInWaitingList",
    "RequiredCarParkingSpaces",
    "TotalOfSpecialRequests",
    "Agent",
    "Company",
)


class DataValidationError(ValueError):
    """Raised when a published-file assumption does not hold."""


def project_root() -> Path:
    """Return the project root that contains ``pyproject.toml`` and ``data/raw``."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "data" / "raw").is_dir():
            return candidate
    raise DataValidationError(
        "Could not locate the project root (expected pyproject.toml and data/raw/)."
    )


def raw_csv_path(hotel_code: str) -> Path:
    """Return the published CSV path for ``H1`` or ``H2``."""
    if hotel_code not in HOTEL_LABELS:
        raise DataValidationError(
            f"Unknown hotel code {hotel_code!r}; expected one of {sorted(HOTEL_LABELS)}."
        )
    path = project_root() / "data" / "raw" / f"{hotel_code}.csv"
    if not path.is_file():
        raise DataValidationError(f"Missing published extract: {path}")
    return path


def load_hotel(hotel_code: str) -> pd.DataFrame:
    """Load one published extract, label the hotel, and run validations.

    Parameters
    ----------
    hotel_code:
        ``H1`` (resort) or ``H2`` (city).
    """
    path = raw_csv_path(hotel_code)
    # Read every field as text so padded NULL tokens are not dropped by
    # pandas' default NA inference, and so no rows are skipped.
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)

    _validate_raw_schema(frame, hotel_code)

    frame = frame.apply(lambda column: column.str.strip())
    frame = frame.replace({token: pd.NA for token in MISSING_TOKENS})
    frame = _to_published_dtypes(frame)
    frame.insert(0, HOTEL_COLUMN, HOTEL_LABELS[hotel_code])

    _validate_loaded_hotel(frame, hotel_code)
    return frame


def load_bookings() -> pd.DataFrame:
    """Load H1 and H2 and return the combined 119,390-row table."""
    resort = load_hotel("H1")
    city = load_hotel("H2")
    combined = pd.concat([resort, city], ignore_index=True)
    _validate_combined(combined, resort, city)
    return combined


def _validate_raw_schema(frame: pd.DataFrame, hotel_code: str) -> None:
    expected_rows = EXPECTED_ROW_COUNTS[hotel_code]
    if list(frame.columns) != list(PUBLISHED_COLUMNS):
        raise DataValidationError(
            f"{hotel_code} column names or order do not match the published schema."
        )
    if frame.shape[1] != 31:
        raise DataValidationError(
            f"{hotel_code} has {frame.shape[1]} columns; published extracts have 31."
        )
    if frame.shape[0] != expected_rows:
        raise DataValidationError(
            f"{hotel_code} has {frame.shape[0]} rows; expected {expected_rows}."
        )


def _to_published_dtypes(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric fields without filtering values.

    ReservationStatusDate is left as text so the loader does not invent a
    calendar type the published files do not store as a typed date.
    """
    converted = frame.copy()
    converted["ADR"] = pd.to_numeric(converted["ADR"], errors="raise")
    for column in INTEGER_COLUMNS:
        converted[column] = pd.to_numeric(converted[column], errors="raise").astype("Int64")
    return converted


def _validate_loaded_hotel(frame: pd.DataFrame, hotel_code: str) -> None:
    expected_rows = EXPECTED_ROW_COUNTS[hotel_code]
    if len(frame) != expected_rows:
        raise DataValidationError(
            f"{hotel_code} row count changed during load ({len(frame)} != {expected_rows})."
        )

    extra_duplicates = int(frame.duplicated(keep="first").sum())
    expected_extra = EXPECTED_EXTRA_DUPLICATES[hotel_code]
    if extra_duplicates != expected_extra:
        raise DataValidationError(
            f"{hotel_code} extra exact duplicates are {extra_duplicates}; "
            f"published files contain {expected_extra}. Rows must not be dropped."
        )

    canceled_values = set(frame["IsCanceled"].dropna().unique().tolist())
    if not canceled_values <= ALLOWED_IS_CANCELED:
        raise DataValidationError(
            f"{hotel_code} IsCanceled contains unexpected values: {sorted(canceled_values)}."
        )

    status_values = set(frame["ReservationStatus"].dropna().unique().tolist())
    if status_values != ALLOWED_RESERVATION_STATUS:
        raise DataValidationError(
            f"{hotel_code} ReservationStatus values are {sorted(status_values)}; "
            f"expected {sorted(ALLOWED_RESERVATION_STATUS)}."
        )

    if hotel_code == "H1":
        negative = frame.loc[frame["ADR"] < 0, "ADR"]
        if len(negative) != 1 or abs(float(negative.iloc[0]) + 6.38) > 1e-9:
            raise DataValidationError(
                "H1 must retain the single published ADR value of -6.38."
            )
    if hotel_code == "H2":
        high = frame.loc[frame["ADR"] == 5400, "ADR"]
        if len(high) != 1:
            raise DataValidationError(
                "H2 must retain the single published ADR value of 5400."
            )

    labels = set(frame[HOTEL_COLUMN].unique())
    if labels != {HOTEL_LABELS[hotel_code]}:
        raise DataValidationError(
            f"{hotel_code} Hotel labels are {labels}; expected {{{HOTEL_LABELS[hotel_code]!r}}}."
        )


def _validate_combined(
    combined: pd.DataFrame,
    resort: pd.DataFrame,
    city: pd.DataFrame,
) -> None:
    expected_rows = EXPECTED_ROW_COUNTS["H1"] + EXPECTED_ROW_COUNTS["H2"]
    if len(combined) != expected_rows:
        raise DataValidationError(
            f"Combined table has {len(combined)} rows; expected {expected_rows}."
        )
    if combined.shape[1] != 32:
        raise DataValidationError(
            f"Combined table has {combined.shape[1]} columns; expected 32 "
            "(31 published fields plus Hotel)."
        )
    if list(resort.columns) != list(city.columns):
        raise DataValidationError("Loaded H1 and H2 schemas are not identical.")
    if list(combined.columns) != [HOTEL_COLUMN, *PUBLISHED_COLUMNS]:
        raise DataValidationError("Combined columns do not match Hotel + published schema.")

    hotel_counts = combined[HOTEL_COLUMN].value_counts().to_dict()
    if hotel_counts.get("Resort Hotel") != EXPECTED_ROW_COUNTS["H1"]:
        raise DataValidationError("Combined Resort Hotel row count does not match H1.")
    if hotel_counts.get("City Hotel") != EXPECTED_ROW_COUNTS["H2"]:
        raise DataValidationError("Combined City Hotel row count does not match H2.")

    extra_duplicates = int(combined.duplicated(keep="first").sum())
    expected_extra = EXPECTED_EXTRA_DUPLICATES["H1"] + EXPECTED_EXTRA_DUPLICATES["H2"]
    if extra_duplicates != expected_extra:
        raise DataValidationError(
            f"Combined extra duplicates are {extra_duplicates}; expected {expected_extra}."
        )

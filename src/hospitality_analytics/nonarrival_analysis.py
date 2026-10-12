"""2016 descriptive non-arrival profile: Check-Out, Canceled, No-Show.

This module summarises final booking outcomes in the extract. It does not
predict cancellation, estimate lost revenue, or recommend overbooking or
deposit policy.

NonArrival is the aggregate of Canceled and No-Show. The three-way
outcome is always computed first.

Counting conventions A and B are inherited from the commercial-profile
layer. Neither is the true booking count.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hospitality_analytics.commercial_profile import (
    CONVENTION_LABELS,
    CONVENTION_ORDER,
    CUSTOMER_TYPE_ORDER,
    HOTEL_ORDER,
    MARKET_SEGMENT_ORDER,
    PRIMARY_YEAR,
    windowed_convention,
)
from hospitality_analytics.data_loader import HOTEL_COLUMN, project_root
from hospitality_analytics.transform import (
    BOOKING_OUTCOMES,
    LEAD_TIME_BANDS,
    prepare_analysis_data,
)

NON_ARRIVAL_OUTCOMES: tuple[str, ...] = ("Canceled", "No-Show")

DEPOSIT_TYPE_ORDER: tuple[str, ...] = ("No Deposit", "Non Refund", "Refundable")

MAJOR_MARKET_SEGMENTS: tuple[str, ...] = (
    "Online TA",
    "Offline TA/TO",
    "Direct",
    "Groups",
    "Corporate",
)

MONTH_ORDER: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_COLOR_A = "#1F4E5F"
_COLOR_B = "#C46B4A"
_COLOR_CHECKOUT = "#1F4E5F"
_COLOR_CANCELED = "#C46B4A"
_COLOR_NOSHOW = "#8A8A8A"


def is_nonarrival(outcomes: pd.Series) -> pd.Series:
    """True where BookingOutcome is Canceled or No-Show."""
    return outcomes.isin(NON_ARRIVAL_OUTCOMES)


def outcome_rate_row(
    outcomes: pd.Series,
    *,
    convention: str,
    hotel: str,
    category_column: str,
    category: str,
) -> dict[str, object]:
    """Three-way rates plus combined NonArrival for one denominator."""
    n = int(len(outcomes))
    counts = {label: int((outcomes == label).sum()) for label in BOOKING_OUTCOMES}
    nonarrival = counts["Canceled"] + counts["No-Show"]
    if n == 0:
        rates = {label: 0.0 for label in BOOKING_OUTCOMES}
        nonarrival_rate = 0.0
    else:
        rates = {label: counts[label] / n for label in BOOKING_OUTCOMES}
        nonarrival_rate = nonarrival / n
    return {
        "convention": convention,
        "convention_label": CONVENTION_LABELS[convention],
        "hotel": hotel,
        "category_column": category_column,
        "category": category,
        "row_count": n,
        "checkout_count": counts["Check-Out"],
        "canceled_count": counts["Canceled"],
        "noshow_count": counts["No-Show"],
        "nonarrival_count": nonarrival,
        "checkout_rate": rates["Check-Out"],
        "canceled_rate": rates["Canceled"],
        "noshow_rate": rates["No-Show"],
        "nonarrival_rate": nonarrival_rate,
        "checkout_rate_pct": 100.0 * rates["Check-Out"],
        "canceled_rate_pct": 100.0 * rates["Canceled"],
        "noshow_rate_pct": 100.0 * rates["No-Show"],
        "nonarrival_rate_pct": 100.0 * nonarrival_rate,
    }


def hotel_outcome_summary(frame: pd.DataFrame, *, convention: str) -> pd.DataFrame:
    """Within-hotel three-way outcome profile for one convention and window."""
    rows = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        if subset.empty:
            continue
        rows.append(
            outcome_rate_row(
                subset["BookingOutcome"],
                convention=convention,
                hotel=hotel,
                category_column="Hotel",
                category=hotel,
            )
        )
    return pd.DataFrame(rows)


def grouped_outcome_rates(
    frame: pd.DataFrame,
    category_column: str,
    *,
    convention: str,
    category_order: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Within-hotel outcome rates for one category column."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        if subset.empty:
            continue
        observed = [_label(item) for item in subset[category_column].dropna().unique().tolist()]
        categories = _ordered(observed, category_order)
        for category in categories:
            values = subset.loc[subset[category_column] == category, "BookingOutcome"]
            if values.empty:
                continue
            rows.append(
                outcome_rate_row(
                    values,
                    convention=convention,
                    hotel=hotel,
                    category_column=category_column,
                    category=category,
                )
            )
    return pd.DataFrame(rows)


def deposit_segment_diagnostic(
    frame: pd.DataFrame,
    *,
    convention: str,
    segments: tuple[str, ...] = MAJOR_MARKET_SEGMENTS,
) -> pd.DataFrame:
    """Focused Hotel × DepositType × MarketSegment outcome rates."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        if subset.empty:
            continue
        for deposit in DEPOSIT_TYPE_ORDER:
            for segment in segments:
                values = subset.loc[
                    (subset["DepositType"] == deposit) & (subset["MarketSegment"] == segment),
                    "BookingOutcome",
                ]
                if values.empty:
                    continue
                row = outcome_rate_row(
                    values,
                    convention=convention,
                    hotel=hotel,
                    category_column="DepositType × MarketSegment",
                    category=f"{deposit} × {segment}",
                )
                row["deposit_type"] = deposit
                row["market_segment"] = segment
                rows.append(row)
    return pd.DataFrame(rows)


def parking_separation(frame: pd.DataFrame) -> pd.DataFrame:
    """Outcome counts among rows with RequiredCarParkingSpaces > 0."""
    rows = []
    parked = frame.loc[frame["RequiredCarParkingSpaces"] > 0]
    scopes = [("combined", parked)]
    for hotel in HOTEL_ORDER:
        scopes.append((hotel, parked.loc[parked[HOTEL_COLUMN] == hotel]))
    for hotel, subset in scopes:
        n = len(subset)
        counts = {label: int((subset["BookingOutcome"] == label).sum()) for label in BOOKING_OUTCOMES}
        rows.append(
            {
                "hotel": hotel,
                "parking_positive_count": n,
                "checkout_count": counts["Check-Out"],
                "canceled_count": counts["Canceled"],
                "noshow_count": counts["No-Show"],
                "nonarrival_count": counts["Canceled"] + counts["No-Show"],
            }
        )
    return pd.DataFrame(rows)


def leakage_diagnostic(analysis_ready: pd.DataFrame) -> pd.DataFrame:
    """Document outcome-adjacent fields that are not used as booking-time factors."""
    window = analysis_ready.loc[analysis_ready["IsCompleteYear"]].copy()
    rows: list[dict[str, object]] = []

    def _add(window_label: str, frame: pd.DataFrame, variable: str, subset_label: str, mask) -> None:
        subset = frame.loc[mask]
        for hotel in ("combined", *HOTEL_ORDER):
            piece = subset if hotel == "combined" else subset.loc[subset[HOTEL_COLUMN] == hotel]
            n = len(piece)
            counts = {label: int((piece["BookingOutcome"] == label).sum()) for label in BOOKING_OUTCOMES}
            rows.append(
                {
                    "window": window_label,
                    "variable": variable,
                    "subset": subset_label,
                    "hotel": hotel,
                    "row_count": n,
                    "checkout_count": counts["Check-Out"],
                    "canceled_count": counts["Canceled"],
                    "noshow_count": counts["No-Show"],
                    "nonarrival_count": counts["Canceled"] + counts["No-Show"],
                    "nonarrival_rate_pct": 0.0 if n == 0 else 100.0 * (counts["Canceled"] + counts["No-Show"]) / n,
                }
            )

    _add("full extract", analysis_ready, "RequiredCarParkingSpaces", "> 0", analysis_ready["RequiredCarParkingSpaces"] > 0)
    _add("2016", window, "RequiredCarParkingSpaces", "> 0", window["RequiredCarParkingSpaces"] > 0)
    _add("2016", window, "RequiredCarParkingSpaces", "= 0", window["RequiredCarParkingSpaces"] == 0)
    _add(
        "2016",
        window,
        "AssignedRoomType",
        "differs from ReservedRoomType",
        window["AssignedRoomType"] != window["ReservedRoomType"],
    )
    _add("2016", window, "BookingChanges", "> 0", window["BookingChanges"] > 0)
    _add("2016", window, "TotalOfSpecialRequests", "> 0", window["TotalOfSpecialRequests"] > 0)
    return pd.DataFrame(rows)


def rate_sensitivity(hotel_summary: pd.DataFrame) -> pd.DataFrame:
    """A vs B hotel-level rates. Does not average A and B."""
    wide = hotel_summary.pivot_table(
        index=["hotel"],
        columns="convention_label",
        values=["row_count", "canceled_rate_pct", "noshow_rate_pct", "nonarrival_rate_pct"],
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{convention}" for metric, convention in wide.columns]
    out = wide.reset_index()
    out["canceled_rate_pct_B_minus_A"] = out["canceled_rate_pct_B"] - out["canceled_rate_pct_A"]
    out["nonarrival_rate_pct_B_minus_A"] = out["nonarrival_rate_pct_B"] - out["nonarrival_rate_pct_A"]
    return out.sort_values("hotel").reset_index(drop=True)


def build_2016_nonarrival_profile(analysis_ready: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute 2016 outcome-rate tables under conventions A and B."""
    frames = {
        convention: windowed_convention(analysis_ready, convention)
        for convention in CONVENTION_ORDER
    }
    hotel_parts = []
    segment_parts = []
    deposit_parts = []
    lead_parts = []
    customer_parts = []
    deposit_segment_parts = []
    month_parts = []
    for convention, frame in frames.items():
        hotel_parts.append(hotel_outcome_summary(frame, convention=convention))
        segment_parts.append(
            grouped_outcome_rates(
                frame,
                "MarketSegment",
                convention=convention,
                category_order=MARKET_SEGMENT_ORDER,
            )
        )
        deposit_parts.append(
            grouped_outcome_rates(
                frame,
                "DepositType",
                convention=convention,
                category_order=DEPOSIT_TYPE_ORDER,
            )
        )
        lead_parts.append(
            grouped_outcome_rates(
                frame,
                "LeadTimeBand",
                convention=convention,
                category_order=LEAD_TIME_BANDS,
            )
        )
        customer_parts.append(
            grouped_outcome_rates(
                frame,
                "CustomerType",
                convention=convention,
                category_order=CUSTOMER_TYPE_ORDER,
            )
        )
        deposit_segment_parts.append(deposit_segment_diagnostic(frame, convention=convention))
        month_parts.append(
            grouped_outcome_rates(
                frame,
                "ArrivalDateMonth",
                convention=convention,
                category_order=MONTH_ORDER,
            )
        )
    hotel_summary = pd.concat(hotel_parts, ignore_index=True)
    return {
        "hotel_summary": hotel_summary,
        "market_segment": pd.concat(segment_parts, ignore_index=True),
        "deposit_type": pd.concat(deposit_parts, ignore_index=True),
        "lead_time": pd.concat(lead_parts, ignore_index=True),
        "customer_type": pd.concat(customer_parts, ignore_index=True),
        "deposit_segment": pd.concat(deposit_segment_parts, ignore_index=True),
        "monthly": pd.concat(month_parts, ignore_index=True),
        "sensitivity": rate_sensitivity(hotel_summary),
        "leakage": leakage_diagnostic(analysis_ready),
        "parking": parking_separation(analysis_ready),
    }


def write_tables(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    names = {
        "hotel_summary": "nonarrival_hotel_summary_2016.csv",
        "market_segment": "nonarrival_market_segment_2016.csv",
        "deposit_type": "nonarrival_deposit_type_2016.csv",
        "lead_time": "nonarrival_lead_time_2016.csv",
        "customer_type": "nonarrival_customer_type_2016.csv",
        "deposit_segment": "nonarrival_deposit_segment_diagnostic_2016.csv",
        "monthly": "nonarrival_monthly_2016.csv",
        "leakage": "nonarrival_leakage_diagnostic.csv",
    }
    for key, filename in names.items():
        profile[key].to_csv(output_dir / filename, index=False)


def write_figures(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    _set_figure_style(plt)
    _hotel_outcome_figure(plt, profile["hotel_summary"], output_dir / "nonarrival_hotel_outcome_2016.png")
    _rate_bar_figure(
        plt,
        profile["market_segment"],
        title="Non-arrival rate by market segment, 2016",
        xlabel="Market segment",
        path=output_dir / "nonarrival_market_segment_2016.png",
        category_order=MAJOR_MARKET_SEGMENTS,
    )
    _rate_bar_figure(
        plt,
        profile["lead_time"],
        title="Non-arrival rate by lead-time band, 2016",
        xlabel="Lead-time band",
        path=output_dir / "nonarrival_lead_time_2016.png",
        category_order=LEAD_TIME_BANDS,
    )
    _deposit_figure(plt, profile["deposit_type"], output_dir / "nonarrival_deposit_type_2016.png")


def export_phase5_outputs(analysis_ready: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if analysis_ready is None:
        analysis_ready = prepare_analysis_data()
    profile = build_2016_nonarrival_profile(analysis_ready)
    root = project_root()
    write_tables(profile, root / "outputs" / "tables")
    write_figures(profile, root / "outputs" / "figures")
    return profile


def _label(value: object) -> str:
    if pd.isna(value):
        return "(missing)"
    return str(value)


def _ordered(observed: list[str], preferred: tuple[str, ...] | None) -> list[str]:
    if preferred is None:
        return observed
    ordered = [item for item in preferred if item in observed]
    extras = [item for item in observed if item not in ordered]
    return ordered + extras


def _set_figure_style(plt) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.45,
            "legend.frameon": False,
        }
    )


def _hotel_outcome_figure(plt, table: pd.DataFrame, path: Path) -> None:
    labels = []
    checkout = []
    canceled = []
    noshow = []
    for hotel in HOTEL_ORDER:
        short = "Resort" if hotel.startswith("Resort") else "City"
        for convention_label in ("A", "B"):
            row = table.loc[
                (table["hotel"] == hotel) & (table["convention_label"] == convention_label)
            ].iloc[0]
            labels.append(f"{short} · {convention_label}")
            checkout.append(float(row["checkout_rate_pct"]))
            canceled.append(float(row["canceled_rate_pct"]))
            noshow.append(float(row["noshow_rate_pct"]))
    x = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.bar(x, checkout, color=_COLOR_CHECKOUT, label="Check-Out")
    ax.bar(x, canceled, bottom=checkout, color=_COLOR_CANCELED, label="Canceled")
    bottom_noshow = [c + k for c, k in zip(checkout, canceled, strict=True)]
    ax.bar(x, noshow, bottom=bottom_noshow, color=_COLOR_NOSHOW, label="No-Show")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of 2016 rows (%)")
    ax.set_title("Final booking outcome by hotel (A all rows / B deduplicated)")
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _rate_bar_figure(
    plt,
    table: pd.DataFrame,
    *,
    title: str,
    xlabel: str,
    path: Path,
    category_order: tuple[str, ...],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), sharey=True)
    width = 0.38
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        hotel_table = table.loc[table["hotel"] == hotel]
        present = [category for category in category_order if category in set(hotel_table["category"])]
        x = range(len(present))
        for offset, convention_label, color in (
            (-width / 2, "A", _COLOR_A),
            (width / 2, "B", _COLOR_B),
        ):
            rates = []
            for category in present:
                match = hotel_table.loc[
                    (hotel_table["convention_label"] == convention_label)
                    & (hotel_table["category"] == category),
                    "nonarrival_rate_pct",
                ]
                rates.append(float(match.iloc[0]) if not match.empty else 0.0)
            ax.bar(
                [position + offset for position in x],
                rates,
                width=width,
                color=color,
                label=f"{convention_label} · {'all rows' if convention_label == 'A' else 'deduplicated'}",
            )
        ax.set_title(hotel)
        ax.set_xticks(list(x), present, rotation=30, ha="right")
        ax.set_xlabel(xlabel)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("Non-arrival rate in the extract (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle(title, y=1.08)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _deposit_figure(plt, table: pd.DataFrame, path: Path) -> None:
    shown = ("No Deposit", "Non Refund")
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.2), sharey=True)
    width = 0.38
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        hotel_table = table.loc[table["hotel"] == hotel]
        x = range(len(shown))
        for offset, convention_label, color in (
            (-width / 2, "A", _COLOR_A),
            (width / 2, "B", _COLOR_B),
        ):
            rates = []
            for category in shown:
                match = hotel_table.loc[
                    (hotel_table["convention_label"] == convention_label)
                    & (hotel_table["category"] == category),
                    "nonarrival_rate_pct",
                ]
                rates.append(float(match.iloc[0]) if not match.empty else 0.0)
            ax.bar(
                [position + offset for position in x],
                rates,
                width=width,
                color=color,
                label=f"{convention_label} · {'all rows' if convention_label == 'A' else 'deduplicated'}",
            )
        ax.set_title(hotel)
        ax.set_xticks(list(x), shown)
        ax.set_xlabel("Deposit type")
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("Non-arrival rate in the extract (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Non-arrival rate by deposit type, 2016 (association in the extract)", y=1.08)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    export_phase5_outputs()

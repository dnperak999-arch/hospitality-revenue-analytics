"""2016 commercial booking profile: mix, lead time, and stay length.

This module summarises booking composition and booking behaviour. It does
not compute occupancy, RevPAR, revenue, or cancellation rates.

Counting conventions (neither is the true booking count):

- ALL_PUBLISHED_ROWS (A): every published row in the window
- EXACT_ROW_DEDUPLICATED (B): one row per exact 31-column combination
  within each hotel

The primary window is the 2016 arrival year (the only complete calendar
year). Shares are always within hotel, convention, and window.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hospitality_analytics.data_loader import HOTEL_COLUMN, project_root
from hospitality_analytics.transform import (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
    LEAD_TIME_BANDS,
    apply_counting_convention,
    prepare_analysis_data,
)

PRIMARY_YEAR = 2016
HOTEL_ORDER: tuple[str, ...] = ("Resort Hotel", "City Hotel")
CONVENTION_ORDER: tuple[str, ...] = (
    COUNTING_ALL_PUBLISHED_ROWS,
    COUNTING_EXACT_ROW_DEDUPLICATED,
)
CONVENTION_LABELS: dict[str, str] = {
    COUNTING_ALL_PUBLISHED_ROWS: "A",
    COUNTING_EXACT_ROW_DEDUPLICATED: "B",
}

MARKET_SEGMENT_ORDER: tuple[str, ...] = (
    "Online TA",
    "Offline TA/TO",
    "Direct",
    "Groups",
    "Corporate",
    "Complementary",
    "Aviation",
    "Undefined",
)
DISTRIBUTION_CHANNEL_ORDER: tuple[str, ...] = (
    "TA/TO",
    "Direct",
    "Corporate",
    "GDS",
    "Undefined",
)
CUSTOMER_TYPE_ORDER: tuple[str, ...] = (
    "Transient",
    "Transient-Party",
    "Contract",
    "Group",
)

_COLOR_A = "#1F4E5F"
_COLOR_B = "#C46B4A"


def complete_calendar_year(frame: pd.DataFrame, year: int = PRIMARY_YEAR) -> pd.DataFrame:
    """Return bookings with arrival in ``year`` without mutating ``frame``."""
    if year == PRIMARY_YEAR and "IsCompleteYear" in frame.columns:
        return frame.loc[frame["IsCompleteYear"]].copy()
    return frame.loc[frame["ArrivalDateYear"] == year].copy()


def windowed_convention(
    analysis_ready: pd.DataFrame,
    convention: str,
    year: int = PRIMARY_YEAR,
) -> pd.DataFrame:
    """Apply the year filter first, then one counting convention."""
    window = complete_calendar_year(analysis_ready, year=year)
    return apply_counting_convention(window, convention)


def composition_table(
    frame: pd.DataFrame,
    category_column: str,
    *,
    convention: str,
    category_order: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Within-hotel counts and shares for one convention and window."""
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "convention",
                "convention_label",
                "hotel",
                "category_column",
                "category",
                "row_count",
                "hotel_row_count",
                "share",
                "share_pct",
            ]
        )
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        hotel_n = len(subset)
        if hotel_n == 0:
            continue
        counts = subset[category_column].value_counts(dropna=False)
        categories = _ordered_categories(counts.index.tolist(), category_order)
        for category in categories:
            count = int(counts.get(category, 0))
            share = count / hotel_n
            rows.append(
                {
                    "convention": convention,
                    "convention_label": CONVENTION_LABELS[convention],
                    "hotel": hotel,
                    "category_column": category_column,
                    "category": _category_label(category),
                    "row_count": count,
                    "hotel_row_count": hotel_n,
                    "share": share,
                    "share_pct": 100.0 * share,
                }
            )
    return pd.DataFrame(rows)


def numeric_distribution(
    frame: pd.DataFrame,
    value_column: str,
    *,
    convention: str,
) -> pd.DataFrame:
    """Median, IQR, and related summaries. Mean is intentionally omitted."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        values = pd.to_numeric(subset[value_column], errors="raise")
        if values.empty:
            continue
        q1 = float(values.quantile(0.25))
        median = float(values.quantile(0.50))
        q3 = float(values.quantile(0.75))
        rows.append(
            {
                "convention": convention,
                "convention_label": CONVENTION_LABELS[convention],
                "hotel": hotel,
                "variable": value_column,
                "hotel_row_count": len(subset),
                "median": median,
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
                "p90": float(values.quantile(0.90)),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "zero_count": int((values == 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def lead_time_band_table(frame: pd.DataFrame, *, convention: str) -> pd.DataFrame:
    """LeadTimeBand shares using the project's ordered bands."""
    table = composition_table(
        frame,
        "LeadTimeBand",
        convention=convention,
        category_order=LEAD_TIME_BANDS,
    )
    return table


def stay_length_bucket_table(frame: pd.DataFrame, *, convention: str) -> pd.DataFrame:
    """Share of booked stays by length, with 8+ nights collapsed."""
    working = frame.copy()
    nights = working["TotalNights"].astype("int64")
    working["StayLengthBucket"] = nights.astype(str)
    working.loc[nights >= 8, "StayLengthBucket"] = "8+"
    order = tuple(str(n) for n in range(0, 8)) + ("8+",)
    return composition_table(
        working,
        "StayLengthBucket",
        convention=convention,
        category_order=order,
    )


def monthly_segment_table(
    frame: pd.DataFrame,
    *,
    convention: str,
    segments: tuple[str, ...] = ("Online TA", "Groups", "Direct"),
) -> pd.DataFrame:
    """2016 arrival-month shares for selected market segments."""
    months = (
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
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        for month in months:
            month_rows = subset.loc[subset["ArrivalDateMonth"] == month]
            month_n = len(month_rows)
            if month_n == 0:
                continue
            for segment in segments:
                count = int((month_rows["MarketSegment"] == segment).sum())
                share = count / month_n
                rows.append(
                    {
                        "convention": convention,
                        "convention_label": CONVENTION_LABELS[convention],
                        "hotel": hotel,
                        "arrival_month": month,
                        "market_segment": segment,
                        "row_count": count,
                        "month_row_count": month_n,
                        "share": share,
                        "share_pct": 100.0 * share,
                    }
                )
    return pd.DataFrame(rows)


def sensitivity_table(*composition_tables: pd.DataFrame) -> pd.DataFrame:
    """Compare convention A and B shares or medians. Does not average them."""
    stacked = pd.concat(composition_tables, ignore_index=True)
    if "share" in stacked.columns:
        wide = stacked.pivot_table(
            index=["hotel", "category_column", "category"],
            columns="convention_label",
            values=["row_count", "hotel_row_count", "share", "share_pct"],
            aggfunc="first",
        )
        wide.columns = [f"{metric}_{convention}" for metric, convention in wide.columns]
        out = wide.reset_index()
        out["share_pct_point_change_B_minus_A"] = out["share_pct_B"] - out["share_pct_A"]
        return out.sort_values(
            ["category_column", "hotel", "share_pct_A"],
            ascending=[True, True, False],
        ).reset_index(drop=True)

    wide = stacked.pivot_table(
        index=["hotel", "variable"],
        columns="convention_label",
        values=["hotel_row_count", "median", "q1", "q3", "iqr", "zero_count"],
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{convention}" for metric, convention in wide.columns]
    out = wide.reset_index()
    out["median_change_B_minus_A"] = out["median_B"] - out["median_A"]
    return out.sort_values(["variable", "hotel"]).reset_index(drop=True)


def build_2016_profile(analysis_ready: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute all 2016 commercial-profile tables under conventions A and B."""
    frames = {
        convention: windowed_convention(analysis_ready, convention)
        for convention in CONVENTION_ORDER
    }
    market = pd.concat(
        [
            composition_table(
                frames[convention],
                "MarketSegment",
                convention=convention,
                category_order=MARKET_SEGMENT_ORDER,
            )
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    channel = pd.concat(
        [
            composition_table(
                frames[convention],
                "DistributionChannel",
                convention=convention,
                category_order=DISTRIBUTION_CHANNEL_ORDER,
            )
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    customer = pd.concat(
        [
            composition_table(
                frames[convention],
                "CustomerType",
                convention=convention,
                category_order=CUSTOMER_TYPE_ORDER,
            )
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    lead_time = pd.concat(
        [
            numeric_distribution(frames[convention], "LeadTime", convention=convention)
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    lead_bands = pd.concat(
        [lead_time_band_table(frames[convention], convention=convention) for convention in CONVENTION_ORDER],
        ignore_index=True,
    )
    stay = pd.concat(
        [
            numeric_distribution(frames[convention], "TotalNights", convention=convention)
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    stay_buckets = pd.concat(
        [
            stay_length_bucket_table(frames[convention], convention=convention)
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    monthly = pd.concat(
        [
            monthly_segment_table(frames[convention], convention=convention)
            for convention in CONVENTION_ORDER
        ],
        ignore_index=True,
    )
    summary = _profile_summary(frames, lead_time, stay)
    return {
        "market_segment": market,
        "distribution_channel": channel,
        "customer_type": customer,
        "lead_time": lead_time,
        "lead_time_band": lead_bands,
        "stay_length": stay,
        "stay_length_bucket": stay_buckets,
        "monthly_segment": monthly,
        "composition_sensitivity": sensitivity_table(market, channel, customer),
        "numeric_sensitivity": sensitivity_table(lead_time, stay),
        "summary": summary,
    }


def write_tables(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Write the concise 2016 CSV set used in the Phase 3 report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    names = {
        "summary": "commercial_profile_summary_2016.csv",
        "market_segment": "market_segment_comparison_2016.csv",
        "distribution_channel": "distribution_channel_comparison_2016.csv",
        "customer_type": "customer_type_comparison_2016.csv",
        "lead_time": "lead_time_comparison_2016.csv",
        "lead_time_band": "lead_time_band_comparison_2016.csv",
        "stay_length": "stay_length_comparison_2016.csv",
        "composition_sensitivity": "duplicate_sensitivity_2016.csv",
    }
    for key, filename in names.items():
        profile[key].to_csv(output_dir / filename, index=False)


def write_figures(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Save four 2016 commercial-profile figures."""
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    _set_figure_style(plt)
    _grouped_share_figure(
        plt,
        profile["market_segment"],
        title="Market segment share of 2016 bookings",
        xlabel="Market segment",
        path=output_dir / "market_segment_2016.png",
        category_order=MARKET_SEGMENT_ORDER,
    )
    _grouped_share_figure(
        plt,
        profile["distribution_channel"],
        title="Distribution channel share of 2016 bookings",
        xlabel="Distribution channel",
        path=output_dir / "distribution_channel_2016.png",
        category_order=DISTRIBUTION_CHANNEL_ORDER,
    )
    _grouped_share_figure(
        plt,
        profile["lead_time_band"],
        title="Lead-time band share of 2016 bookings",
        xlabel="Lead-time band",
        path=output_dir / "lead_time_bands_2016.png",
        category_order=LEAD_TIME_BANDS,
    )
    _grouped_share_figure(
        plt,
        profile["stay_length_bucket"],
        title="Booked length of stay, 2016",
        xlabel="Total booked nights",
        path=output_dir / "stay_length_2016.png",
        category_order=tuple(str(n) for n in range(0, 8)) + ("8+",),
    )


def export_phase3_outputs(analysis_ready: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Load (if needed), compute, and write Phase 3 tables and figures."""
    if analysis_ready is None:
        analysis_ready = prepare_analysis_data()
    profile = build_2016_profile(analysis_ready)
    root = project_root()
    write_tables(profile, root / "outputs" / "tables")
    write_figures(profile, root / "outputs" / "figures")
    return profile


def _profile_summary(
    frames: dict[str, pd.DataFrame],
    lead_time: pd.DataFrame,
    stay: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for convention, frame in frames.items():
        for hotel in HOTEL_ORDER:
            subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
            lead = lead_time.loc[
                (lead_time["convention"] == convention) & (lead_time["hotel"] == hotel)
            ].iloc[0]
            nights = stay.loc[
                (stay["convention"] == convention) & (stay["hotel"] == hotel)
            ].iloc[0]
            rows.append(
                {
                    "convention": convention,
                    "convention_label": CONVENTION_LABELS[convention],
                    "hotel": hotel,
                    "arrival_year": PRIMARY_YEAR,
                    "hotel_row_count": len(subset),
                    "online_ta_share_pct": _share_pct(subset, "MarketSegment", "Online TA"),
                    "groups_share_pct": _share_pct(subset, "MarketSegment", "Groups"),
                    "direct_segment_share_pct": _share_pct(subset, "MarketSegment", "Direct"),
                    "ta_to_channel_share_pct": _share_pct(subset, "DistributionChannel", "TA/TO"),
                    "direct_channel_share_pct": _share_pct(subset, "DistributionChannel", "Direct"),
                    "transient_share_pct": _share_pct(subset, "CustomerType", "Transient"),
                    "transient_party_share_pct": _share_pct(subset, "CustomerType", "Transient-Party"),
                    "customer_type_group_share_pct": _share_pct(subset, "CustomerType", "Group"),
                    "lead_time_median": lead["median"],
                    "lead_time_iqr": lead["iqr"],
                    "total_nights_median": nights["median"],
                    "total_nights_iqr": nights["iqr"],
                    "seven_night_share_pct": 100.0 * float((subset["TotalNights"] == 7).mean()),
                    "zero_night_count": int((subset["TotalNights"] == 0).sum()),
                }
            )
    return pd.DataFrame(rows)


def _share_pct(frame: pd.DataFrame, column: str, category: str) -> float:
    if frame.empty:
        return 0.0
    return 100.0 * float((frame[column] == category).mean())


def _category_label(category: object) -> str:
    if pd.isna(category):
        return "(missing)"
    return str(category)


def _ordered_categories(
    observed: list[object],
    preferred: tuple[str, ...] | None,
) -> list[object]:
    labels = [_category_label(item) for item in observed]
    if preferred is None:
        return labels
    ordered = [item for item in preferred if item in labels]
    extras = [item for item in labels if item not in ordered]
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


def _grouped_share_figure(
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
    y_max = min(100.0, max(float(table["share_pct"].max()) * 1.12, 25.0))
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        hotel_table = table.loc[table["hotel"] == hotel]
        present = [category for category in category_order if category in set(hotel_table["category"])]
        x = range(len(present))
        for offset, convention_label, color in (
            (-width / 2, "A", _COLOR_A),
            (width / 2, "B", _COLOR_B),
        ):
            shares = []
            for category in present:
                match = hotel_table.loc[
                    (hotel_table["convention_label"] == convention_label)
                    & (hotel_table["category"] == category),
                    "share_pct",
                ]
                shares.append(float(match.iloc[0]) if not match.empty else 0.0)
            ax.bar(
                [position + offset for position in x],
                shares,
                width=width,
                color=color,
                label=f"{convention_label} · {'all rows' if convention_label == 'A' else 'deduplicated'}",
            )
        ax.set_title(hotel)
        ax.set_xticks(list(x), present, rotation=30, ha="right")
        ax.set_xlabel(xlabel)
        ax.set_ylim(0, y_max)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{value:.0f}"))
    axes[0].set_ylabel("Share of hotel bookings (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle(title, y=1.08)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    export_phase3_outputs()

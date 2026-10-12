"""2016 quoted-ADR summaries. ADR is a booked/quoted rate, not revenue.

Analytical views (neither rewrites the published ADR column):

- PUBLISHED_ADR: every stored ADR value
- POSITIVE_ADR: rows with ADR > 0 (sensitivity for typical quoted rates)

A third, narrowly documented mean diagnostic can drop the single
verified ADR = 5400 value. It is not a cleaned dataset.

Counting conventions A and B are inherited from the commercial-profile
layer. Neither is the true booking count.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hospitality_analytics.commercial_profile import (
    CONVENTION_LABELS,
    CONVENTION_ORDER,
    HOTEL_ORDER,
    MARKET_SEGMENT_ORDER,
    PRIMARY_YEAR,
    windowed_convention,
)
from hospitality_analytics.data_loader import HOTEL_COLUMN, project_root
from hospitality_analytics.transform import (
    BOOKING_OUTCOMES,
    COUNTING_ALL_PUBLISHED_ROWS,
    LEAD_TIME_BANDS,
    prepare_analysis_data,
)

ADR_VIEW_PUBLISHED = "PUBLISHED_ADR"
ADR_VIEW_POSITIVE = "POSITIVE_ADR"
ADR_VIEW_POSITIVE_EXCLUDING_5400 = "POSITIVE_ADR_EXCLUDING_5400"

ADR_VIEW_LABELS: dict[str, str] = {
    ADR_VIEW_PUBLISHED: "Published ADR",
    ADR_VIEW_POSITIVE: "Positive ADR",
    ADR_VIEW_POSITIVE_EXCLUDING_5400: "Positive ADR excluding 5400",
}

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

MAJOR_MARKET_SEGMENTS: tuple[str, ...] = (
    "Online TA",
    "Offline TA/TO",
    "Direct",
    "Groups",
    "Corporate",
)

_COLOR_A = "#1F4E5F"
_COLOR_B = "#C46B4A"
_COLOR_RESORT = "#1F4E5F"
_COLOR_CITY = "#C46B4A"


def adr_view(frame: pd.DataFrame, view: str) -> pd.DataFrame:
    """Return a copy filtered to an ADR view. ADR values are not recoded."""
    if "ADR" not in frame.columns:
        raise ValueError("Frame has no ADR column.")
    out = frame.copy()
    if view == ADR_VIEW_PUBLISHED:
        return out
    if view == ADR_VIEW_POSITIVE:
        return out.loc[out["ADR"] > 0].copy()
    if view == ADR_VIEW_POSITIVE_EXCLUDING_5400:
        return out.loc[(out["ADR"] > 0) & (out["ADR"] != 5400)].copy()
    raise ValueError(f"Unknown ADR view {view!r}.")


def adr_distribution(
    frame: pd.DataFrame,
    *,
    convention: str,
    view: str,
) -> pd.DataFrame:
    """Hotel-level quoted-ADR summary. Mean is a diagnostic only."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        values = pd.to_numeric(subset["ADR"], errors="raise")
        if values.empty:
            continue
        q1 = float(values.quantile(0.25))
        median = float(values.quantile(0.50))
        q3 = float(values.quantile(0.75))
        rows.append(
            {
                "convention": convention,
                "convention_label": CONVENTION_LABELS[convention],
                "adr_view": view,
                "adr_view_label": ADR_VIEW_LABELS[view],
                "hotel": hotel,
                "row_count": int(values.size),
                "median": median,
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
                "mean": float(values.mean()),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "zero_count": int((values == 0).sum()),
                "negative_count": int((values < 0).sum()),
                "extreme_high_5400_count": int((values == 5400).sum()),
            }
        )
    return pd.DataFrame(rows)


def grouped_adr_summary(
    frame: pd.DataFrame,
    category_column: str,
    *,
    convention: str,
    view: str,
    category_order: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Median/IQR quoted ADR within hotel and one category."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        if subset.empty:
            continue
        observed = [str(item) for item in subset[category_column].dropna().unique().tolist()]
        categories = _ordered(observed, category_order)
        for category in categories:
            values = pd.to_numeric(
                subset.loc[subset[category_column] == category, "ADR"],
                errors="raise",
            )
            if values.empty:
                continue
            q1 = float(values.quantile(0.25))
            median = float(values.quantile(0.50))
            q3 = float(values.quantile(0.75))
            rows.append(
                {
                    "convention": convention,
                    "convention_label": CONVENTION_LABELS[convention],
                    "adr_view": view,
                    "hotel": hotel,
                    "category_column": category_column,
                    "category": category,
                    "row_count": int(values.size),
                    "median": median,
                    "q1": q1,
                    "q3": q3,
                    "iqr": q3 - q1,
                    "mean": float(values.mean()),
                }
            )
    return pd.DataFrame(rows)


def zero_adr_diagnostic(frame: pd.DataFrame, *, convention: str) -> pd.DataFrame:
    """Profile ADR == 0. Does not recode zeros and does not assume a cause."""
    rows: list[dict[str, object]] = []
    for hotel in HOTEL_ORDER:
        subset = frame.loc[frame[HOTEL_COLUMN] == hotel]
        zeros = subset.loc[subset["ADR"] == 0]
        hotel_n = len(subset)
        zero_n = len(zeros)
        rows.append(
            _zero_row(
                convention,
                hotel,
                "Hotel",
                hotel,
                zero_n,
                zero_n,
                hotel_n,
            )
        )
        for column, order in (
            ("BookingOutcome", BOOKING_OUTCOMES),
            ("MarketSegment", MARKET_SEGMENT_ORDER),
            ("DistributionChannel", None),
            ("CustomerType", None),
            ("TotalNightsZero", None),
        ):
            if column == "TotalNightsZero":
                count = int((zeros["TotalNights"] == 0).sum())
                rows.append(
                    _zero_row(
                        convention,
                        hotel,
                        "TotalNights",
                        "0",
                        count,
                        zero_n,
                        hotel_n,
                    )
                )
                continue
            counts = zeros[column].value_counts(dropna=False)
            categories = _ordered([_label(item) for item in counts.index.tolist()], order)
            for category in categories:
                count = int(counts.get(category, 0))
                if count == 0:
                    continue
                rows.append(
                    _zero_row(
                        convention,
                        hotel,
                        column,
                        category,
                        count,
                        zero_n,
                        hotel_n,
                    )
                )
    return pd.DataFrame(rows)


def anomaly_status(analysis_ready: pd.DataFrame) -> pd.DataFrame:
    """Locate the verified negative and 5400 ADR rows relative to 2016."""
    rows = []
    for mask, name in (
        (analysis_ready["ADR"] < 0, "ADR < 0"),
        (analysis_ready["ADR"] == 5400, "ADR = 5400"),
    ):
        subset = analysis_ready.loc[mask]
        for _, row in subset.iterrows():
            year = int(row["ArrivalDateYear"])
            rows.append(
                {
                    "anomaly": name,
                    "hotel": row[HOTEL_COLUMN],
                    "adr": float(row["ADR"]),
                    "arrival_date": str(pd.Timestamp(row["ArrivalDate"]).date()),
                    "arrival_year": year,
                    "in_2016_window": year == PRIMARY_YEAR,
                    "booking_outcome": row["BookingOutcome"],
                    "market_segment": row["MarketSegment"],
                    "total_nights": int(row["TotalNights"]),
                }
            )
    return pd.DataFrame(rows)


def median_sensitivity(hotel_summary: pd.DataFrame) -> pd.DataFrame:
    """A vs B median quoted ADR by hotel and ADR view. Does not average A and B."""
    wide = hotel_summary.pivot_table(
        index=["adr_view", "hotel"],
        columns="convention_label",
        values=["row_count", "median", "iqr", "mean"],
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{convention}" for metric, convention in wide.columns]
    out = wide.reset_index()
    out["median_change_B_minus_A"] = out["median_B"] - out["median_A"]
    return out.sort_values(["adr_view", "hotel"]).reset_index(drop=True)


def build_2016_adr_profile(analysis_ready: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute 2016 quoted-ADR tables under conventions A and B."""
    frames = {
        convention: windowed_convention(analysis_ready, convention)
        for convention in CONVENTION_ORDER
    }
    hotel_parts = []
    zero_parts = []
    segment_parts = []
    lead_parts = []
    month_parts = []
    outcome_parts = []
    for convention, frame in frames.items():
        published = adr_view(frame, ADR_VIEW_PUBLISHED)
        positive = adr_view(frame, ADR_VIEW_POSITIVE)
        positive_ex_5400 = adr_view(frame, ADR_VIEW_POSITIVE_EXCLUDING_5400)
        hotel_parts.append(adr_distribution(published, convention=convention, view=ADR_VIEW_PUBLISHED))
        hotel_parts.append(adr_distribution(positive, convention=convention, view=ADR_VIEW_POSITIVE))
        hotel_parts.append(
            adr_distribution(
                positive_ex_5400,
                convention=convention,
                view=ADR_VIEW_POSITIVE_EXCLUDING_5400,
            )
        )
        zero_parts.append(zero_adr_diagnostic(published, convention=convention))
        for view_name, viewed in (
            (ADR_VIEW_PUBLISHED, published),
            (ADR_VIEW_POSITIVE, positive),
        ):
            segment_parts.append(
                grouped_adr_summary(
                    viewed,
                    "MarketSegment",
                    convention=convention,
                    view=view_name,
                    category_order=MARKET_SEGMENT_ORDER,
                )
            )
            lead_parts.append(
                grouped_adr_summary(
                    viewed,
                    "LeadTimeBand",
                    convention=convention,
                    view=view_name,
                    category_order=LEAD_TIME_BANDS,
                )
            )
            month_parts.append(
                grouped_adr_summary(
                    viewed,
                    "ArrivalDateMonth",
                    convention=convention,
                    view=view_name,
                    category_order=MONTH_ORDER,
                )
            )
            outcome_parts.append(
                grouped_adr_summary(
                    viewed,
                    "BookingOutcome",
                    convention=convention,
                    view=view_name,
                    category_order=BOOKING_OUTCOMES,
                )
            )
    hotel_summary = pd.concat(hotel_parts, ignore_index=True)
    return {
        "hotel_summary": hotel_summary,
        "zero_diagnostic": pd.concat(zero_parts, ignore_index=True),
        "market_segment": pd.concat(segment_parts, ignore_index=True),
        "lead_time": pd.concat(lead_parts, ignore_index=True),
        "monthly": pd.concat(month_parts, ignore_index=True),
        "outcome": pd.concat(outcome_parts, ignore_index=True),
        "sensitivity": median_sensitivity(hotel_summary),
        "anomalies": anomaly_status(analysis_ready),
    }


def write_tables(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    names = {
        "hotel_summary": "adr_hotel_summary_2016.csv",
        "zero_diagnostic": "adr_zero_diagnostic_2016.csv",
        "market_segment": "adr_market_segment_2016.csv",
        "lead_time": "adr_lead_time_2016.csv",
        "monthly": "adr_monthly_2016.csv",
        "outcome": "adr_outcome_2016.csv",
        "sensitivity": "adr_sensitivity_2016.csv",
        "anomalies": "adr_anomaly_status.csv",
    }
    for key, filename in names.items():
        profile[key].to_csv(output_dir / filename, index=False)


def write_figures(profile: dict[str, pd.DataFrame], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    _set_figure_style(plt)
    _monthly_figure(plt, profile["monthly"], output_dir / "adr_monthly_2016.png")
    _grouped_median_figure(
        plt,
        profile["market_segment"],
        title="Median quoted ADR by market segment, 2016",
        xlabel="Market segment",
        path=output_dir / "adr_market_segment_2016.png",
        category_order=MAJOR_MARKET_SEGMENTS,
        view=ADR_VIEW_POSITIVE,
    )
    _grouped_median_figure(
        plt,
        profile["lead_time"],
        title="Median quoted ADR by lead-time band, 2016",
        xlabel="Lead-time band",
        path=output_dir / "adr_lead_time_2016.png",
        category_order=LEAD_TIME_BANDS,
        view=ADR_VIEW_POSITIVE,
    )
    _grouped_median_figure(
        plt,
        profile["outcome"],
        title="Median quoted ADR by final booking outcome, 2016",
        xlabel="Booking outcome",
        path=output_dir / "adr_outcome_2016.png",
        category_order=BOOKING_OUTCOMES,
        view=ADR_VIEW_POSITIVE,
    )


def export_phase4_outputs(analysis_ready: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if analysis_ready is None:
        analysis_ready = prepare_analysis_data()
    profile = build_2016_adr_profile(analysis_ready)
    root = project_root()
    write_tables(profile, root / "outputs" / "tables")
    write_figures(profile, root / "outputs" / "figures")
    return profile


def _zero_row(
    convention: str,
    hotel: str,
    dimension: str,
    category: str,
    count: int,
    hotel_zero_count: int,
    hotel_row_count: int,
) -> dict[str, object]:
    return {
        "convention": convention,
        "convention_label": CONVENTION_LABELS[convention],
        "hotel": hotel,
        "dimension": dimension,
        "category": category,
        "zero_count": count,
        "hotel_zero_count": hotel_zero_count,
        "hotel_row_count": hotel_row_count,
        "pct_of_hotel_zeros": 0.0 if hotel_zero_count == 0 else 100.0 * count / hotel_zero_count,
        "pct_of_hotel_rows": 0.0 if hotel_row_count == 0 else 100.0 * count / hotel_row_count,
    }


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


def _monthly_figure(plt, table: pd.DataFrame, path: Path) -> None:
    data = table.loc[
        (table["adr_view"] == ADR_VIEW_POSITIVE) & (table["category_column"] == "ArrivalDateMonth")
    ]
    fig, ax = plt.subplots(figsize=(11.2, 5.2))
    x = list(range(len(MONTH_ORDER)))
    styles = {
        ("Resort Hotel", "A"): dict(color=_COLOR_RESORT, linestyle="-", marker="o", linewidth=2.0),
        ("Resort Hotel", "B"): dict(color=_COLOR_RESORT, linestyle="--", marker="o", linewidth=1.6, alpha=0.85),
        ("City Hotel", "A"): dict(color=_COLOR_CITY, linestyle="-", marker="s", linewidth=2.0),
        ("City Hotel", "B"): dict(color=_COLOR_CITY, linestyle="--", marker="s", linewidth=1.6, alpha=0.85),
    }
    labels = {
        ("Resort Hotel", "A"): "Resort · A all rows",
        ("Resort Hotel", "B"): "Resort · B deduplicated",
        ("City Hotel", "A"): "City · A all rows",
        ("City Hotel", "B"): "City · B deduplicated",
    }
    for hotel in HOTEL_ORDER:
        for convention_label in ("A", "B"):
            subset = data.loc[
                (data["hotel"] == hotel) & (data["convention_label"] == convention_label)
            ].set_index("category")
            y = [float(subset.loc[month, "median"]) if month in subset.index else None for month in MONTH_ORDER]
            ax.plot(x, y, label=labels[(hotel, convention_label)], **styles[(hotel, convention_label)])
    ax.set_xticks(x, [month[:3] for month in MONTH_ORDER])
    ax.set_ylim(0, None)
    ax.set_ylabel("Median quoted ADR")
    ax.set_xlabel("Arrival month, 2016")
    ax.set_title("Monthly median quoted ADR (positive ADR view)")
    ax.legend(ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _grouped_median_figure(
    plt,
    table: pd.DataFrame,
    *,
    title: str,
    xlabel: str,
    path: Path,
    category_order: tuple[str, ...],
    view: str,
) -> None:
    data = table.loc[table["adr_view"] == view]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), sharey=True)
    width = 0.38
    y_max = max(float(data.loc[data["category"].isin(category_order), "median"].max()) * 1.12, 20.0)
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        hotel_table = data.loc[data["hotel"] == hotel]
        present = [category for category in category_order if category in set(hotel_table["category"])]
        x = range(len(present))
        for offset, convention_label, color in (
            (-width / 2, "A", _COLOR_A),
            (width / 2, "B", _COLOR_B),
        ):
            medians = []
            for category in present:
                match = hotel_table.loc[
                    (hotel_table["convention_label"] == convention_label)
                    & (hotel_table["category"] == category),
                    "median",
                ]
                medians.append(float(match.iloc[0]) if not match.empty else 0.0)
            ax.bar(
                [position + offset for position in x],
                medians,
                width=width,
                color=color,
                label=f"{convention_label} · {'all rows' if convention_label == 'A' else 'deduplicated'}",
            )
        ax.set_title(hotel)
        ax.set_xticks(list(x), present, rotation=30, ha="right")
        ax.set_xlabel(xlabel)
        ax.set_ylim(0, y_max)
    axes[0].set_ylabel("Median quoted ADR")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle(title + " (positive ADR view)", y=1.08)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    export_phase4_outputs()

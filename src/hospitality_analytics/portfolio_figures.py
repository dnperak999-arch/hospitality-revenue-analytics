"""Publication figures for the GitHub README. No new analysis.

Consumes verified Phase 3–5 tables (and the existing stay-length bucket
function, which is not written to CSV). Does not overwrite Phase 3–5 PNGs.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd

from hospitality_analytics.adr_analysis import ADR_VIEW_POSITIVE, MONTH_ORDER
from hospitality_analytics.commercial_profile import (
    CONVENTION_ORDER,
    HOTEL_ORDER,
    stay_length_bucket_table,
    windowed_convention,
)
from hospitality_analytics.data_loader import project_root
from hospitality_analytics.transform import prepare_analysis_data

PORTFOLIO_SEGMENTS: tuple[str, ...] = (
    "Online TA",
    "Offline TA/TO",
    "Direct",
    "Groups",
    "Corporate",
)
STAY_DISPLAY_BUCKETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7", "8+")

_COLOR_A = "#1F4E5F"
_COLOR_B = "#C46B4A"
_INK = "#1A1A1A"
_MUTED = "#5A5A5A"
_NOTE = "#6E6E6E"
_GRID = "#D0D0D0"

_HOTEL_SHORT = {"Resort Hotel": "Resort", "City Hotel": "City"}
_LEGEND_A = "A  all published rows"
_LEGEND_B = "B  exact-row-deduplicated"


def load_verified_tables(tables_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Read existing Phase 3–5 CSVs. Stay-length buckets use the Phase 3 function."""
    root_tables = tables_dir or (project_root() / "outputs" / "tables")
    return {
        "market_segment": pd.read_csv(root_tables / "market_segment_comparison_2016.csv"),
        "adr_monthly": pd.read_csv(root_tables / "adr_monthly_2016.csv"),
        "nonarrival_segment": pd.read_csv(root_tables / "nonarrival_market_segment_2016.csv"),
        "profile_summary": pd.read_csv(root_tables / "commercial_profile_summary_2016.csv"),
        "stay_length_bucket": _stay_length_buckets(),
    }


def major_segment_rows(table: pd.DataFrame, category_column: str = "category") -> pd.DataFrame:
    """Keep commercially meaningful segments for portfolio display only."""
    return table.loc[table[category_column].isin(PORTFOLIO_SEGMENTS)].copy()


def stay_display_rows(table: pd.DataFrame) -> pd.DataFrame:
    """Positive stay-length buckets for display. Zero-night rows stay in the source table."""
    return table.loc[table["category"].isin(STAY_DISPLAY_BUCKETS)].copy()


def positive_monthly_adr(table: pd.DataFrame) -> pd.DataFrame:
    """Phase 4 positive-ADR monthly medians only."""
    return table.loc[table["adr_view"] == ADR_VIEW_POSITIVE].copy()


def write_portfolio_figures(
    tables: dict[str, pd.DataFrame] | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Write the four hero PNGs. Does not touch Phase 3–5 figure filenames."""
    import matplotlib.pyplot as plt

    if tables is None:
        tables = load_verified_tables()
    figures = output_dir or (project_root() / "outputs" / "figures")
    figures.mkdir(parents=True, exist_ok=True)
    _set_style(plt)
    paths = [
        figures / "portfolio_market_segment_2016.png",
        figures / "portfolio_stay_length_2016.png",
        figures / "portfolio_quoted_adr_seasonality_2016.png",
        figures / "portfolio_nonarrival_segment_2016.png",
    ]
    _market_segment_figure(plt, tables["market_segment"], paths[0])
    _stay_length_figure(plt, tables["stay_length_bucket"], paths[1])
    _adr_seasonality_figure(plt, tables["adr_monthly"], paths[2])
    _nonarrival_segment_figure(plt, tables["nonarrival_segment"], paths[3])
    return paths


def _stay_length_buckets() -> pd.DataFrame:
    analysis_ready = prepare_analysis_data()
    parts = [
        stay_length_bucket_table(windowed_convention(analysis_ready, convention), convention=convention)
        for convention in CONVENTION_ORDER
    ]
    return pd.concat(parts, ignore_index=True)


def _set_style(plt) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "font.family": "sans-serif",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#B0B0B0",
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": _GRID,
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
            "grid.alpha": 1.0,
            "legend.frameon": False,
            "axes.titlesize": 11,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )


def _two_panel(plt, *, top: float = 0.74, bottom: float = 0.16):
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 6.55), sharey=True)
    fig.subplots_adjust(top=top, bottom=bottom, left=0.07, right=0.98, wspace=0.20)
    return fig, axes


def _header(fig, title: str, subtitle: str) -> None:
    fig.text(
        0.02,
        0.975,
        textwrap.fill(title, width=88),
        fontsize=13.5,
        color=_INK,
        va="top",
        ha="left",
        fontweight="bold",
        linespacing=1.25,
    )
    fig.text(
        0.02,
        0.885,
        textwrap.fill(subtitle, width=118),
        fontsize=8.4,
        color=_MUTED,
        va="top",
        ha="left",
        linespacing=1.35,
    )


def _footer(fig, note: str) -> None:
    fig.text(
        0.02,
        0.018,
        textwrap.fill(note, width=130),
        fontsize=7.4,
        color=_NOTE,
        va="bottom",
        ha="left",
        linespacing=1.3,
    )


def _legend(fig, handles, labels) -> None:
    fig.legend(
        handles,
        labels,
        loc="upper left",
        ncol=2,
        bbox_to_anchor=(0.02, 0.825),
        fontsize=8.4,
        handlelength=1.6,
        columnspacing=1.4,
        borderaxespad=0.0,
    )


def _panel_title(ax, hotel: str) -> None:
    ax.set_title(_HOTEL_SHORT[hotel], loc="left", color=_INK, pad=8, fontweight="bold")


def _lookup(table: pd.DataFrame, hotel: str, category: str, convention: str, value: str) -> float:
    match = table.loc[
        (table["hotel"] == hotel)
        & (table["category"] == category)
        & (table["convention_label"] == convention),
        value,
    ]
    if match.empty:
        raise KeyError(f"Missing {hotel} {category} {convention} {value}")
    return float(match.iloc[0])


def _grouped_bars(ax, table: pd.DataFrame, hotel: str, categories: tuple[str, ...], value: str):
    hotel_table = table.loc[table["hotel"] == hotel]
    x = list(range(len(categories)))
    width = 0.36
    series = {}
    for offset, convention, color, hatch in (
        (-width / 2, "A", _COLOR_A, None),
        (width / 2, "B", _COLOR_B, "///"),
    ):
        values = [_lookup(hotel_table, hotel, category, convention, value) for category in categories]
        series[convention] = values
        ax.bar(
            [position + offset for position in x],
            values,
            width=width,
            color=color,
            hatch=hatch,
            edgecolor="#FFFFFF" if hatch else color,
            linewidth=0.7 if hatch else 0.0,
            label=_LEGEND_A if convention == "A" else _LEGEND_B,
        )
    return x, series


def _market_segment_figure(plt, table: pd.DataFrame, path: Path) -> None:
    data = major_segment_rows(table)
    fig, axes = _two_panel(plt, top=0.72, bottom=0.17)
    _header(
        fig,
        "City is more OTA-led; Resort has more Direct business",
        "Arrival year 2016. A = all published rows; B = each exact 31-column combination counted once within hotel. Neither is the true booking count.",
    )
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        x, series = _grouped_bars(ax, data, hotel, PORTFOLIO_SEGMENTS, "share_pct")
        _panel_title(ax, hotel)
        ax.set_xticks(x, PORTFOLIO_SEGMENTS, rotation=20, ha="right")
        ax.set_ylim(0, 82)
        ax.set_xlabel("")
        groups_index = PORTFOLIO_SEGMENTS.index("Groups")
        a_val = series["A"][groups_index]
        b_val = series["B"][groups_index]
        ax.annotate(
            f"Groups  {a_val:.1f}% → {b_val:.1f}%",
            xy=(groups_index, max(a_val, b_val)),
            xytext=(groups_index + 0.28, max(a_val, b_val) + 1.6),
            ha="center",
            va="bottom",
            fontsize=8.2,
            color=_INK,
        )
    axes[0].set_ylabel("Share of hotel rows (%)")
    _legend(fig, *axes[0].get_legend_handles_labels())
    _footer(
        fig,
        "Major segments only. Complementary and Aviation remain in the Phase 3 tables. B is a sensitivity view, not a corrected mix.",
    )
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _stay_length_figure(plt, buckets: pd.DataFrame, path: Path) -> None:
    data = stay_display_rows(buckets)
    fig, axes = _two_panel(plt, top=0.72, bottom=0.17)
    _header(
        fig,
        "Same 3-night median, different stay pattern: Resort has a 7-night peak",
        "Arrival year 2016. A = all published rows; B = exact-row-deduplicated sensitivity view. Neither is the true booking count.",
    )
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        x, series = _grouped_bars(ax, data, hotel, STAY_DISPLAY_BUCKETS, "share_pct")
        _panel_title(ax, hotel)
        ax.set_xticks(x, STAY_DISPLAY_BUCKETS)
        ax.set_xlabel("Booked nights")
        ax.set_ylim(0, 36)
        seven_index = STAY_DISPLAY_BUCKETS.index("7")
        a_val = series["A"][seven_index]
        b_val = series["B"][seven_index]
        ax.annotate(
            f"7 nights: {a_val:.1f}% → {b_val:.1f}%",
            xy=(seven_index, max(a_val, b_val)),
            xytext=(seven_index + 0.15, max(a_val, b_val) + 1.6),
            ha="center",
            va="bottom",
            fontsize=8.2,
            color=_INK,
        )
    axes[0].set_ylabel("Share of hotel rows (%)")
    _legend(fig, *axes[0].get_legend_handles_labels())
    _footer(
        fig,
        "Zero-night rows omitted from this display; they remain in the Phase 3 tables. Median booked stay is 3 nights at both hotels under A and B.",
    )
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _adr_seasonality_figure(plt, table: pd.DataFrame, path: Path) -> None:
    data = positive_monthly_adr(table)
    fig, ax = plt.subplots(figsize=(11.0, 6.35))
    fig.subplots_adjust(top=0.72, bottom=0.16, left=0.07, right=0.98)
    _header(
        fig,
        "Resort quoted ADR peaks in summer; City is flatter and higher in winter",
        "Median quoted ADR · arrival year 2016 · positive-ADR view. A = all published rows; B = exact-row-deduplicated sensitivity view.",
    )
    x = list(range(len(MONTH_ORDER)))
    styles = {
        ("Resort Hotel", "A"): dict(color=_COLOR_A, linestyle="-", marker="o", linewidth=2.15, markersize=5.5),
        ("Resort Hotel", "B"): dict(color=_COLOR_A, linestyle=(0, (4, 2.2)), marker="o", linewidth=1.6, markersize=4.5, markerfacecolor="white", markeredgewidth=1.2),
        ("City Hotel", "A"): dict(color=_COLOR_B, linestyle="-", marker="s", linewidth=2.15, markersize=5.0),
        ("City Hotel", "B"): dict(color=_COLOR_B, linestyle=(0, (4, 2.2)), marker="s", linewidth=1.6, markersize=4.2, markerfacecolor="white", markeredgewidth=1.2),
    }
    labels = {
        ("Resort Hotel", "A"): "Resort · A  all published rows",
        ("Resort Hotel", "B"): "Resort · B  exact-row-deduplicated",
        ("City Hotel", "A"): "City · A  all published rows",
        ("City Hotel", "B"): "City · B  exact-row-deduplicated",
    }
    plotted = {}
    for hotel in HOTEL_ORDER:
        for convention in ("A", "B"):
            subset = data.loc[
                (data["hotel"] == hotel) & (data["convention_label"] == convention)
            ].set_index("category")
            y = [float(subset.loc[month, "median"]) for month in MONTH_ORDER]
            plotted[(hotel, convention)] = y
            ax.plot(x, y, label=labels[(hotel, convention)], **styles[(hotel, convention)])
    ax.set_xticks(x, [month[:3] for month in MONTH_ORDER])
    ax.set_ylim(0, 235)
    ax.set_ylabel("Median quoted ADR")
    ax.set_xlabel("Arrival month, 2016")
    resort_aug = plotted[("Resort Hotel", "A")][7]
    resort_jan = plotted[("Resort Hotel", "A")][0]
    ax.annotate(
        f"Resort Aug  {resort_aug:.0f}",
        xy=(7, resort_aug),
        xytext=(5.15, 214),
        fontsize=8.4,
        color=_COLOR_A,
        ha="left",
        arrowprops=dict(arrowstyle="-", color=_COLOR_A, lw=0.7),
    )
    ax.annotate(
        f"Resort Jan  {resort_jan:.0f}",
        xy=(0, resort_jan),
        xytext=(0.35, 22),
        fontsize=8.4,
        color=_COLOR_A,
        ha="left",
    )
    _legend(fig, *ax.get_legend_handles_labels())
    _footer(
        fig,
        "Quoted / booked ADR recorded in the extract, not revenue. A and B tracks keep the same seasonal shape; B is not a corrected rate.",
    )
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _nonarrival_segment_figure(plt, table: pd.DataFrame, path: Path) -> None:
    data = major_segment_rows(table)
    fig, axes = _two_panel(plt, top=0.72, bottom=0.17)
    _header(
        fig,
        "The apparent Groups non-arrival spike is duplicate-sensitive",
        "Non-arrival = Canceled + No-Show. Arrival year 2016. A = all published rows; B = exact-row-deduplicated sensitivity view.",
    )
    for ax, hotel in zip(axes, HOTEL_ORDER, strict=True):
        x, series = _grouped_bars(ax, data, hotel, PORTFOLIO_SEGMENTS, "nonarrival_rate_pct")
        _panel_title(ax, hotel)
        ax.set_xticks(x, PORTFOLIO_SEGMENTS, rotation=20, ha="right")
        ax.set_ylim(0, 100)
        ax.set_xlabel("")
        groups_index = PORTFOLIO_SEGMENTS.index("Groups")
        a_val = series["A"][groups_index]
        b_val = series["B"][groups_index]
        ax.annotate(
            f"Groups  {a_val:.1f}% → {b_val:.1f}%",
            xy=(groups_index, max(a_val, b_val)),
            xytext=(groups_index + 0.12, max(a_val, b_val) + 1.5),
            ha="center",
            va="bottom",
            fontsize=8.2,
            color=_INK,
        )
    axes[0].set_ylabel("Non-arrival in the extract (%)")
    _legend(fig, *axes[0].get_legend_handles_labels())
    _footer(
        fig,
        "Identical-row sensitivity materially changes the Groups result; it does not identify the true booking count. Online TA stays near one-third under A and B. Direct is lower and comparatively stable.",
    )
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    write_portfolio_figures()

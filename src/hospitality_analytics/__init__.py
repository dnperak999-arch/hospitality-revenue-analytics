"""Hospitality booking-demand analytics.

Loads the António, Almeida & Nunes (2019) extracts, adds analysis-ready
fields without dropping rows or altering ADR, and supports descriptive
2016 mix, quoted-ADR, and non-arrival profiles under two duplicate
counting conventions.
"""

from hospitality_analytics.data_loader import load_bookings, load_hotel
from hospitality_analytics.transform import (
    all_published_rows,
    exact_row_deduplicated,
    prepare_analysis_data,
)

__all__ = [
    "all_published_rows",
    "exact_row_deduplicated",
    "load_bookings",
    "load_hotel",
    "prepare_analysis_data",
]

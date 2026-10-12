# Phase 4 — Quoted ADR Analysis

How quoted ADR differs between the Resort Hotel and the City Hotel across booking mix, booking window, season, and final booking outcome, and which of those differences remain stable under duplicate handling and known ADR anomalies.

This note describes **quoted / booked / recorded ADR** in the 2016 booking extract. It is not revenue, not realised room revenue, not RevPAR, and not a performance ranking. The extract has no auditable revenue or room inventory. The hotels are anonymised Portuguese properties from António, Almeida & Nunes (2019). This is not Hilton data.

## Scope and terminology

The window is **arrival year 2016**, the only complete calendar year. Monthly seasonality uses January–December 2016. Incomplete 2015/2017 years are not compared as annual totals.

Two counting conventions are reported throughout. Neither is the true number of bookings:

| Convention | Rule | 2016 Resort | 2016 City |
|---|---|---:|---:|
| **A** (`ALL_PUBLISHED_ROWS`) | Every published row | 18,567 | 38,140 |
| **B** (`EXACT_ROW_DEDUPLICATED`) | One row per exact 31-column combination within hotel | 15,632 | 26,759 |

Two ADR views are used. Neither recodes the stored ADR column:

| View | Rule | Role |
|---|---|---|
| **PUBLISHED ADR** | Every stored ADR value, including 0, negatives, and 5400 | Baseline / sensitivity |
| **POSITIVE ADR** | Rows with ADR > 0 | Typical quoted-rate comparison, after the zero-ADR diagnostic below |

A third, narrowly documented diagnostic drops the single verified ADR = 5400 row from the positive view. It is not a cleaned dataset.

Headline statistics are **median and IQR**. Means are diagnostic only. `MarketSegment = Groups` is not `CustomerType = Group`. `StaysInWeekendNights` is not used.

A finding is **robust** only if its direction and practical reading hold under both A and B. Material A/B movement with a stable direction is **robust direction / sensitive magnitude**. Findings that change interpretation under B are **duplicate-sensitive**.

## ADR data-quality diagnostic

### Verified anomalies

| Anomaly | Hotel | ADR | Arrival | Outcome | Segment | Nights | In 2016? |
|---|---|---:|---|---|---|---:|---|
| Negative ADR | Resort Hotel | −6.38 | 2017-03-05 | Check-Out | Groups | 10 | **No** |
| Extreme high | City Hotel | 5400 | 2016-03-25 | Canceled | Offline TA/TO | 1 | **Yes** |

The negative row is outside the 2016 window and does not enter any 2016 median, IQR, or mean below. It is not recoded.

The ADR = 5400 row is inside 2016. Dropping it leaves the **City median unchanged** (published A still 99.00; positive A still 99.45). It moves the City **mean** on the published view from 103.48 to about 103.34, and on the positive view from 104.96 to 104.82. That is why medians are the headline and why 5400 is not removed from the published view.

### Zero ADR in 2016

ADR = 0 is uncommon but not rare, and it is **not a single category**.

| Hotel | A zeros | A % of hotel | B zeros | B % of hotel |
|---|---:|---:|---:|---:|
| Resort | 382 / 18,567 | 2.06% | 359 / 15,632 | 2.30% |
| City | 536 / 38,140 | 1.41% | 487 / 26,759 | 1.82% |

Within those zeros (convention A; B is similar):

- **About 90% are Check-Out** (Resort 347 / 382 = 90.8%; City 479 / 536 = 89.4%). Canceled zeros are 7.1% (Resort) and 9.1% (City). No-Show zeros are 8 rows in each hotel.
- **Complementary is a concentration, not a synonym.** Complementary is 23.0% of Resort zeros (88 / 382) and 44.0% of City zeros (236 / 536). Among Complementary rows themselves, ADR is 0 for 88 / 103 = 85.4% (Resort A) and 236 / 261 = 90.4% (City A). Complementary is still a small slice of the hotel files (0.6–0.7%).
- **Every 2016 row with `TotalNights` = 0 has ADR = 0** (Resort 224; City 193). Those 0-night rows are 58.6% of Resort zeros and 36.0% of City zeros. The converse is false: many zero-ADR rows have nights booked (158 Resort; 343 City).
- A remainder is **neither Complementary nor 0-night**: 70 Resort zeros (18.3%) and 121 City zeros (22.6%).
- Zeros also sit in Online TA, Direct, Groups, Offline TA/TO, and Corporate. Online TA is 27.2% of Resort zeros because Online TA is large, not because that segment is typically unpriced (104 / 7,953 = 1.3% of Resort Online TA rows).

The data therefore show mixed concentrations, not a single coding rule. Zero ADR is **not** treated here as an error, a complimentary stay, or a missing rate. It is excluded from the **POSITIVE ADR** view only as a labelled sensitivity for typical quoted rates.

Hotel-level medians move by about **1 quoted-ADR unit** when zeros are dropped (see next section). That supports using POSITIVE ADR for segment, lead-time, month, and outcome comparisons, with PUBLISHED ADR retained as the sensitivity table.

## Hotel-level quoted ADR

PUBLISHED ADR, 2016:

| Hotel | A n | A median | A IQR (Q1–Q3) | A mean | B n | B median | B IQR (Q1–Q3) | B mean |
|---|---:|---:|---|---:|---:|---:|---|---:|
| Resort | 18,567 | 70.00 | 58.00 (49.00–107.00) | 87.73 | 15,632 | 71.00 | 67.81 (48.60–116.41) | 90.66 |
| City | 38,140 | 99.00 | 42.07 (79.43–121.50) | 103.48 | 26,759 | 102.60 | 47.50 (82.00–129.50) | 107.90 |

POSITIVE ADR, 2016:

| Hotel | A n | A median | A IQR (Q1–Q3) | A mean | B n | B median | B IQR (Q1–Q3) | B mean |
|---|---:|---:|---|---:|---:|---:|---|---:|
| Resort | 18,185 | 71.00 | 58.67 (50.33–109.00) | 89.57 | 15,273 | 72.00 | 68.15 (50.00–118.15) | 92.79 |
| City | 37,604 | 99.45 | 42.40 (80.00–122.40) | 104.96 | 26,272 | 103.50 | 45.85 (84.15–130.00) | 109.90 |

The City Hotel has the **higher typical quoted ADR** under every combination of A/B and published/positive: the City–Resort median gap is 29.00 (published A), 31.60 (published B), 28.45 (positive A), and 31.50 (positive B).

Excluding zero ADR does **not** change that ranking. Resort median rises 70 → 71 (A) and 71 → 72 (B); City rises 99.00 → 99.45 (A) and 102.60 → 103.50 (B).

The **direction is robust**. The **magnitude is mildly duplicate-sensitive**: City median rises by 3.60 (published) / 4.05 (positive) from A to B; Resort rises by 1.00 in both views. Resort IQR widens more under B (58.00 → 67.81 published) than City IQR (42.07 → 47.50). Higher quoted ADR is not interpreted as higher profitability.

## ADR by market segment

Main comparison: **POSITIVE ADR**. PUBLISHED ADR is the sensitivity check. Complementary is shown because it explains zeros; with n = 15 (Resort) / 25 (City) remaining positive-ADR rows it is not ranked as a commercial rate segment. Aviation is City-only and small (n ≈ 120).

POSITIVE ADR median (IQR) and count, major segments:

| Segment | Resort A | Resort B | City A | City B |
|---|---|---|---|---|
| Online TA | 83.00 (87.00) n=7,849 | 85.00 (89.00) n=7,377 | 109.20 (45.00) n=19,611 | 110.00 (45.70) n=17,774 |
| Direct | 83.00 (91.00) n=2,884 | 84.01 (93.70) n=2,784 | 109.15 (53.46) n=2,674 | 112.00 (56.70) n=2,441 |
| Offline TA/TO | 60.70 (43.33) n=3,423 | 61.00 (44.69) n=3,083 | 90.00 (35.00) n=8,896 | 85.00 (26.75) n=3,878 |
| Groups | 67.67 (27.50) n=3,117 | 66.00 (27.50) n=1,179 | 73.33 (37.00) n=4,654 | 75.00 (33.00) n=782 |
| Corporate | 42.00 (27.00) n=897 | 42.00 (27.00) n=835 | 80.00 (29.00) n=1,619 | 79.00 (30.00) n=1,253 |

PUBLISHED ADR medians for the same major segments are within about 0–3 units of the positive-ADR medians, except Complementary, whose published median is 0.00 in both hotels because most Complementary rows are ADR = 0.

**Meaningful hotel differences (major segments).** In every major segment the City median is higher than the Resort median under both A and B. The gap is large for Corporate (City 80 vs Resort 42 under A; 79 vs 42 under B), Online TA (109 vs 83 A; 110 vs 85 B), Direct (109 vs 83 A; 112 vs 84 B), and Offline TA/TO (90 vs 61 A; 85 vs 61 B). Groups is closer (73 vs 68 A; 75 vs 66 B) but still City-higher. Within each hotel, Online TA and Direct sit at the top of the major-segment medians; Corporate is the lowest major Resort rate; Groups is the lowest major City rate.

**Duplicate handling.** Online TA, Direct, and Corporate medians move by at most about 3 units A → B. **Groups counts collapse** (Resort 3,117 → 1,179; City 4,654 → 782) but **Groups medians barely move** (Resort 67.67 → 66.00; City 73.33 → 75.00). The Phase 3 Groups duplication issue changes *how much* Groups business appears in the file, not the typical quoted ADR recorded on those rows.

City **Offline TA/TO** is the main segment-rate exception on magnitude: median 90.00 under A vs 85.00 under B, and count 8,896 → 3,878. Direction (City still well above Resort Offline TA/TO) is unchanged.

`CustomerType = Group` is not analysed as a rate segment here; it remains <1% of 2016 rows (Phase 3).

## ADR by booking window

POSITIVE ADR median by existing `LeadTimeBand`, 2016:

| Band | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| 0 days | 55.00 | 55.00 | 98.60 | 99.00 |
| 1–7 days | 58.80 | 60.00 | 101.68 | 104.00 |
| 8–30 days | 70.00 | 70.00 | 108.57 | 109.00 |
| 31–90 days | 72.00 | 75.00 | 102.43 | 105.00 |
| 91–180 days | 80.00 | 88.00 | 100.63 | 105.30 |
| 181+ days | 76.05 | 79.90 | 90.10 | 94.50 |

**Resort.** Same-day and 1–7 day bookings are associated with the **lowest** median quoted ADR (55–60). Medians rise through 8–30 and 31–90, peak in **91–180 days** (80.00 A / 88.00 B), then ease slightly at 181+ (76.05 A / 79.90 B). Long-lead bookings are **not** recorded at the lowest Resort rates.

**City.** The profile is flatter. The **highest** median is in 8–30 days (108.57 A / 109.00 B). The **lowest** is 181+ days (90.10 A / 94.50 B). Same-day City bookings sit in the middle of that range on the positive view (98.60 A), not at the bottom.

These are associations in the stored extract. They are not evidence that booking earlier causes lower prices.

A/B **direction is stable** (Resort: short-lead lower, 91–180 highest; City: 8–30 highest, 181+ lowest). **Magnitude is more sensitive at longer Resort windows**: the 91–180 median rises 80 → 88 under B. City 181+ rises 90.10 → 94.50. Published-ADR tables show the same shapes; same-day City published median is pulled down to 90.00 (A) by zeros, which is why the positive view is used for typical quoted rates.

## ADR seasonality

Monthly median quoted ADR, POSITIVE ADR, 2016 arrival month:

| Month | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| January | 45.00 | 44.80 | 78.30 | 78.25 |
| February | 54.00 | 48.00 | 79.00 | 80.30 |
| March | 54.90 | 52.25 | 85.00 | 86.00 |
| April | 68.00 | 66.10 | 96.48 | 99.45 |
| May | 69.30 | 70.00 | 109.65 | 116.10 |
| June | 95.69 | 96.36 | 110.34 | 110.00 |
| July | 159.38 | 160.00 | 107.95 | 113.52 |
| August | 197.94 | 199.00 | 115.00 | 120.70 |
| September | 92.00 | 101.00 | 117.00 | 125.10 |
| October | 62.29 | 64.10 | 108.00 | 110.70 |
| November | 48.00 | 48.00 | 89.00 | 89.04 |
| December | 62.20 | 60.00 | 88.00 | 89.89 |

**The two hotels have different seasonal shapes.** Resort median quoted ADR is low in winter (January 45.00 A; November 48.00), rises through spring, then **jumps in July–August** (159.38 / 197.94 under A) and falls back in September (92.00). City seasonality is milder: January about 78, a plateau around 108–117 from May to October, with the 2016 high in **September** (117.00 A / 125.10 B) rather than August.

Duplicate handling **does not change the shapes**. A and B tracks lie close, especially at the Resort summer peak (August 197.94 A vs 199.00 B). City summer/early-autumn medians are a few units higher under B (May 109.65 → 116.10; September 117.00 → 125.10). Individual months are not over-interpreted; the robust reading is “Resort has a sharp summer peak; City is higher in winter and flatter in summer.”

No forecast and no price-optimisation claim follows from this calendar pattern.

## ADR by final booking outcome

This is an ADR comparison only, not a cancellation-risk analysis. Quoted ADR on Canceled or No-Show rows is **not realised revenue**.

POSITIVE ADR, 2016:

| Outcome | Resort A | Resort B | City A | City B |
|---|---|---|---|---|
| Check-Out | 68.00 n=13,290 | 68.00 n=11,886 | 99.45 n=22,254 | 100.75 n=18,534 |
| Canceled | 79.41 n=4,790 | 89.00 n=3,287 | 99.45 n=14,803 | 108.45 n=7,283 |
| No-Show | 66.00 n=105 | 70.00 n=100 | 93.00 n=547 | 97.00 n=455 |

**Resort.** Canceled bookings **carried a higher median quoted ADR** than Check-Out under both conventions (79.41 vs 68.00 under A; 89.00 vs 68.00 under B). The direction is stable; the gap widens under B (11 vs 21 units). No-Show n is about 100; those medians (66–70) sit near Check-Out and should not be read strongly.

**City.** Under A, Check-Out and Canceled have the **same** median quoted ADR (99.45). Under B, Canceled is higher (108.45 vs 100.75). Whether City cancellations “look like” Check-Out on quoted ADR is therefore **duplicate-sensitive**. No-Show n is larger than at the Resort (547 A / 455 B) but still the smallest City outcome; median 93.00 A / 97.00 B, below Check-Out.

PUBLISHED ADR does not reverse these readings. City published A medians are Check-Out 99.00, Canceled 99.45, No-Show 92.60.

## Duplicate sensitivity

Largest A → B movements in **median quoted ADR** (positive view unless noted):

| Comparison | A | B | Change |
|---|---:|---:|---:|
| Resort Canceled median | 79.41 | 89.00 | +9.59 |
| City Canceled median | 99.45 | 108.45 | +9.00 |
| Resort 91–180 day median | 80.00 | 88.00 | +8.00 |
| City Offline TA/TO median | 90.00 | 85.00 | −5.00 |
| City hotel-level median | 99.45 | 103.50 | +4.05 |
| Resort hotel-level median | 71.00 | 72.00 | +1.00 |

Groups **counts** are highly duplicate-sensitive (as in Phase 3). Groups **quoted-ADR medians** are not. City Offline TA/TO is the major segment whose typical quoted ADR moves enough to note. City Canceled vs Check-Out **equality under A vs a gap under B** is the outcome finding that does not survive both conventions.

Resort IQR is more duplicate-sensitive than the Resort median (published IQR 58.00 → 67.81).

## Robust findings

1. City Hotel typical quoted ADR is higher than Resort Hotel typical quoted ADR in 2016 (published A medians 99 vs 70; positive A 99.45 vs 71). The ranking holds under B and after dropping ADR = 0.
2. Excluding zero ADR changes hotel medians by about one unit and does not change hotel ranking.
3. In every major market segment, City median quoted ADR exceeds Resort median quoted ADR under A and B.
4. Within each hotel, Online TA and Direct are the highest major-segment medians; Resort Corporate is the lowest major Resort median (42 under A and B).
5. Groups duplication changes Groups **counts**, not Groups **median quoted ADR** (Resort 67.67 → 66.00; City 73.33 → 75.00).
6. Resort short-lead bookings (0 and 1–7 days) are associated with lower median quoted ADR than 31–180 day bookings, under A and B.
7. City 181+ day bookings are associated with the lowest City median quoted ADR among lead-time bands, under A and B.
8. Resort monthly quoted ADR has a sharp July–August peak (about 159 / 198 under A); City 2016 seasonality is flatter, with winter medians well above the Resort and a high around August–September.
9. ADR = −6.38 is outside 2016. ADR = 5400 is inside 2016 and distorts the City **mean**, not the City **median**.
10. About 1.4–2.3% of 2016 rows have ADR = 0; ~90% of those zeros are Check-Out; Complementary and 0-night stays are concentrations, not a complete explanation.

## Robust direction / sensitive magnitude

1. City–Resort hotel-level median gap: about 28–32 quoted-ADR units depending on A/B and ADR view. Direction stable; City median rises ~4 units under B.
2. Resort Canceled vs Check-Out: Canceled median is higher under both conventions; the gap is 11 units (A) vs 21 units (B).
3. Resort 91–180 day median: highest lead-time band under both conventions, but 80 (A) vs 88 (B).
4. City Offline TA/TO median: still well above Resort Offline TA/TO, but 90 (A) vs 85 (B), with a large count drop.
5. City May and September medians are several units higher under B; the seasonal *shape* is unchanged.
6. Resort IQR widens under B (published 58 → 68); the hotel ranking by typical ADR does not.

## Duplicate-sensitive findings

1. **City Canceled vs Check-Out quoted ADR.** Equal medians under A (both 99.45 on the positive view). Canceled higher under B (108.45 vs 100.75). The City outcome comparison cannot be summarised as a single gap.
2. **How large Groups is as a slice of the file** remains convention-dependent (Phase 3). That is a mix finding, not an ADR-median finding.
3. Absolute 2016 row counts, including positive-ADR counts (Resort 18,185 vs 15,273; City 37,604 vs 26,272), are not a demand measure without choosing A or B.

## Limitations

- Quoted / booked / recorded ADR only. No revenue, lost revenue, RevPAR, occupancy, or room-night value is calculated.
- One file row is not shown to be one room or one stay that paid the quoted rate.
- POSITIVE ADR is a sensitivity view, not cleaned ADR. Zeros are profiled, not explained.
- ADR = 5400 remains in the published and positive views; it is excluded only in a labelled mean diagnostic.
- No-Show samples are small, especially at the Resort (~100 rows).
- Complementary positive-ADR n is too small to interpret as a rate.
- Lead time is the final stored window, not pickup. Associations are not causal price effects.
- 2016 only. Partial years are excluded.
- `StaysInWeekendNights` is not used.
- No hotel-brand inference. No pricing recommendation.

Supporting tables: `outputs/tables/adr_*_2016.csv` and `outputs/tables/adr_anomaly_status.csv`. Figures: `outputs/figures/adr_*_2016.png`. Regenerated with `python -m hospitality_analytics.adr_analysis`.

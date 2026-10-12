# Phase 3 — Commercial Booking Profile

How booking composition and booking behaviour differ between the Resort Hotel (H1) and the City Hotel (H2).

Quoted ADR and non-arrival are out of scope. This note describes the 2016 booking file only. It is not a performance ranking and not a branded-chain extract.

## Scope and counting conventions

The window is **arrival year 2016**, the only complete calendar year (Resort 18,567 rows; City 38,140 rows; 56,707 combined). 2015 and 2017 totals are not used as annual volumes.

Two counting conventions are reported throughout. Neither is the true number of bookings or rooms:

| Convention | Rule | 2016 Resort | 2016 City | 2016 combined |
|---|---|---:|---:|---:|
| **A** (`ALL_PUBLISHED_ROWS`) | Every published row | 18,567 | 38,140 | 56,707 |
| **B** (`EXACT_ROW_DEDUPLICATED`) | One row per exact 31-column combination within hotel | 15,632 | 26,759 | 42,391 |

Shares are within hotel, convention, and 2016. A finding is **robust** only if its direction and practical reading hold under both A and B. Material A/B movement is labelled **duplicate-sensitive**. A and B are not averaged.

Row counts are booking-file lines, not proven occupied rooms and not hotel demand.

## Resort vs City commercial profile

In 2016 the city-hotel file is more travel-agency / OTA-weighted and more short-stay. The resort-hotel file has a larger Direct share, more Contract business, more same-week lead times, and a weekly (7-night) stay peak that the city hotel does not.

How large those gaps look depends on whether identical Groups rows are counted once or many times. Channel mix and stay-length shape move less than market-segment mix.

## Booking composition

### Market segment

Online TA is the largest segment in both hotels under both conventions.

| Segment | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| Online TA | 42.8% (7,953) | 47.8% (7,474) | 51.7% (19,708) | 66.8% (17,868) |
| Offline TA/TO | 18.7% (3,472) | 20.0% (3,129) | 23.6% (9,001) | 14.8% (3,951) |
| Direct | 15.9% (2,943) | 18.2% (2,840) | 7.1% (2,720) | 9.3% (2,486) |
| Groups | 17.1% (3,170) | 7.9% (1,228) | 12.3% (4,687) | 3.0% (813) |
| Corporate | 5.0% (926) | 5.5% (863) | 4.3% (1,636) | 4.7% (1,269) |
| Complementary | 0.6% | 0.6% | 0.7% | 0.9% |
| Aviation | — | — | 0.3% (127) | 0.5% (121) |

**Robust.** The city hotel has a higher Online TA share and a lower Direct share than the resort under both A and B. Aviation appears only in the city file. Complementary is small in both.

**Duplicate-sensitive.** Groups falls from 17.1% to 7.9% at the resort (−9.2 pp) and from 12.3% to 3.0% at the city hotel (−9.3 pp). City Online TA then rises from 51.7% to 66.8% (+15.1 pp). City Offline TA/TO falls from 23.6% to 14.8% (−8.8 pp). The city file’s “OTA-heavy” reading is true in direction under both conventions; the *size* of that OTA majority is not.

`MarketSegment = Groups` is not `CustomerType = Group` (see below).

### Distribution channel

| Channel | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| TA/TO | 71.9% (13,357) | 71.6% (11,186) | 86.9% (33,155) | 83.8% (22,427) |
| Direct | 20.4% (3,792) | 20.9% (3,270) | 7.9% (3,007) | 10.3% (2,744) |
| Corporate | 7.6% (1,418) | 7.5% (1,176) | 4.9% (1,874) | 5.6% (1,491) |
| GDS | — | — | 0.3% (104) | 0.4% (97) |

**Robust.** Both hotels are TA/TO-majority. The city hotel is more TA/TO and less Direct than the resort, with A/B movement of about 3 pp or less on TA/TO. GDS is city-only and rare. Resort channel shares barely move when identical rows are collapsed.

Direct as a **channel** (20% resort / 8–10% city) is larger than Direct as a **market segment** (16–18% resort / 7–9% city). The two fields are not interchangeable.

### Customer type

| Type | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| Transient | 75.9% (14,093) | 81.7% (12,776) | 79.4% (30,298) | 85.5% (22,880) |
| Transient-Party | 20.4% (3,793) | 14.2% (2,222) | 19.9% (7,600) | 13.7% (3,679) |
| Contract | 3.1% (576) | 3.4% (539) | 0.5% (180) | 0.5% (144) |
| Group | 0.6% (105) | 0.6% (95) | 0.2% (62) | 0.2% (56) |

**Robust.** Transient is the majority type in both hotels. `CustomerType = Group` is rare (under 1%) and must not be read as `MarketSegment = Groups` (17% / 12% under A). Contract is several times more common at the resort than at the city hotel (about 3.1–3.4% vs 0.5%).

**Duplicate-sensitive.** Transient-Party falls by about 6 pp in both hotels under B, and Transient rises by about 6 pp. Identical rows are concentrated in party/group-like blocks, not in `CustomerType = Group`.

## Booking window

Median lead time (days), 2016. Mean is not used.

| Hotel | A median (IQR) | B median (IQR) |
|---|---|---|
| Resort | 54 (9–157, IQR 148) | 42 (7–137, IQR 130) |
| City | 71 (22–162, IQR 140) | 49 (13–111, IQR 98) |

**Robust direction.** The city-hotel file has a longer median booking window than the resort under both conventions (71 vs 54 days under A; 49 vs 42 under B). Same-day / 0-day lead time is more common at the resort (8.4% A / 9.6% B) than at the city hotel (3.9% / 5.2%).

**Duplicate-sensitive magnitude.** Collapsing identical rows shortens both medians and shrinks the city–resort gap from 17 days to 7. The city 181+ day band is 21.7% under A and 10.2% under B (−11.4 pp). Long-window city rows are disproportionately duplicated. The resort lead-time mix is flatter across bands and moves less.

Dominant bands: city bookings pile into 31–90 days (26.9% A / 30.7% B). The resort is more even, with 91–180 days slightly largest under A (21.1%) and 31–90 days slightly largest under B (20.7%).

These figures are the lead time stored on the **final** snapshot. They are not a pickup curve.

## Length of stay

`TotalNights` is the sum of the two stored night fields. It is not Saturday/Sunday demand.

| Hotel | A median (IQR) | B median (IQR) | 7-night share A | 7-night share B |
|---|---|---|---:|---:|
| Resort | 3 (2–6, IQR 4) | 3 (2–7, IQR 5) | 14.6% | 15.2% |
| City | 3 (2–4, IQR 2) | 3 (2–4, IQR 2) | 2.6% | 3.3% |

**Robust.** Medians are 3 nights at both hotels under both conventions. That median hides different shapes: the city file is concentrated on 1–4 night stays (1–3 nights are 18.3%, 25.7%, 27.4% under A and 20.5%, 20.2%, 24.8% under B); the resort file has a second peak at 7 nights (14.6% A / 15.2% B) that the city hotel lacks. Resort IQR is wider (4–5 nights vs 2). 90th percentile booked length is 7–8 nights at the resort and 5 at the city hotel.

Zero-night rows are retained. In the **full** extract they are 384 (resort) and 331 (city). In **2016** they are 224 / 193 under A and 213 / 159 under B (about 1.2% of resort 2016 rows and 0.5% of city 2016 rows under A). They are not treated as sold rooms.

`TotalNights` is not converted to revenue or rooms sold.

## Duplicate sensitivity

Largest share movements, 2016, B minus A (percentage points):

| Hotel | Item | A | B | Change |
|---|---|---:|---:|---:|
| City | MarketSegment Online TA | 51.7% | 66.8% | +15.1 |
| City | MarketSegment Groups | 12.3% | 3.0% | −9.3 |
| Resort | MarketSegment Groups | 17.1% | 7.9% | −9.2 |
| City | MarketSegment Offline TA/TO | 23.6% | 14.8% | −8.8 |
| Both | CustomerType Transient-Party | ~20% | ~14% | ≈ −6 |
| City | LeadTimeBand 181+ days | 21.7% | 10.2% | −11.4 |
| City | LeadTime median (days) | 71 | 49 | −22 |
| Resort | DistributionChannel TA/TO | 71.9% | 71.6% | −0.4 |

As context only: 2016 Non Refund rows collapse from 884 to 99 at the resort and from 5,910 to 359 at the city hotel. Deposit policy is not analysed here.

Seasonality (not plotted): under A, resort Groups share spikes in April (32.4%) and October (31.6%) and is near zero in July–August. Under B those April/October spikes shrink (13.5% and 23.4%). Summer Online TA dominance at both hotels is less sensitive to duplicates.

## Robust findings

1. The city-hotel 2016 file is more TA/TO and more Online TA, and less Direct, than the resort file.
2. Resort channel mix is stable under A and B (TA/TO about 72%, Direct about 20%).
3. `CustomerType = Group` is rare (<1%). `MarketSegment = Groups` is a different, much larger slice.
4. Contract is a resort feature (about 3%) and negligible at the city hotel (about 0.5%).
5. Median booked stay is 3 nights at both hotels; the resort has a 7-night peak (~15%) that the city hotel does not (~3%).
6. Median lead time is longer in the city file than in the resort file; 0-day lead time is more common at the resort.
7. Aviation and GDS appear only in the city file, at well under 1%.

## Duplicate-sensitive findings

1. Groups share roughly halves (resort) or falls to about a quarter (city) when identical rows are collapsed. Any “how much group business” statement is convention-dependent.
2. City Online TA can be described as a majority (52%) or a two-thirds majority (67%) depending on A vs B.
3. City Offline TA/TO is 24% under A and 15% under B.
4. Transient-Party is about 20% under A and 14% under B in both hotels.
5. City median lead time and the city 181+ day band shrink sharply under B; long-lead city rows are heavily duplicated.
6. Absolute 2016 volumes (18,567 vs 15,632 resort; 38,140 vs 26,759 city) are not interpretable as demand without choosing a counting rule.

## Limitations

- 2016 booking-file mix, not occupancy, RevPAR, revenue, or rooms sold.
- One row is not shown to be one room. Identical Groups/Non Refund lines may be many rooms or repeated extracts; the file cannot say.
- `StaysInWeekendNights` is not used as Saturday/Sunday demand.
- Lead time is the final stored window, not pickup.
- Partial years 2015 and 2017 are excluded from this profile.
- No causal claim: hotel type, market, and coding practice are confounded.
- ADR and cancellation/no-show behaviour are not estimated here.

Supporting tables: `outputs/tables/`. Figures: `outputs/figures/`. Regenerated with `python -m hospitality_analytics.commercial_profile`.

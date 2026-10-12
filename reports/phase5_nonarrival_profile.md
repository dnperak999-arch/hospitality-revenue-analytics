# Phase 5 — Cancellation and No-Show Profile

Where final non-arrival is concentrated in the Resort Hotel and City Hotel extracts, how it varies across booking mix and booking window, and which readings survive exact-row duplicate sensitivity.

This is a **descriptive historical profile of final booking outcomes** in the 2016 extract. It is not a prediction model, not a causal analysis, not an overbooking model, and not a revenue-loss estimate. The hotels are anonymised Portuguese properties from António, Almeida & Nunes (2019). This is not Hilton data.

## Scope and terminology

The window is **arrival year 2016**, the only complete calendar year.

Primary outcome is the existing three-way `BookingOutcome` (copied from `ReservationStatus`):

- Check-Out
- Canceled
- No-Show

**NonArrival** is defined only as the aggregate **Canceled or No-Show**. Combined rates are shown after the three-way split. `IsCanceled` is not used as the outcome because it folds No-Show into Canceled.

Rates are within hotel, convention, and subgroup. Denominators are file rows, not rooms and not unconstrained demand.

Two counting conventions. Neither is the true booking count:

| Convention | Rule | 2016 Resort | 2016 City |
|---|---|---:|---:|
| **A** (`ALL_PUBLISHED_ROWS`) | Every published row | 18,567 | 38,140 |
| **B** (`EXACT_ROW_DEDUPLICATED`) | One row per exact 31-column combination within hotel | 15,632 | 26,759 |

A finding is **robust** only if its direction and practical reading hold under both A and B. Material A/B movement with a stable direction is **robust direction / sensitive magnitude**. Findings that change interpretation under B are **duplicate-sensitive**.

## Hotel-level final outcomes

| Hotel | Convention | n | Check-Out | Canceled | No-Show | NonArrival |
|---|---|---:|---|---|---|---|
| Resort | A | 18,567 | 73.45% (13,637) | 25.94% (4,817) | 0.61% (113) | 26.55% (4,930) |
| Resort | B | 15,632 | 78.13% (12,213) | 21.19% (3,312) | 0.68% (107) | 21.87% (3,419) |
| City | A | 38,140 | 59.60% (22,733) | 38.94% (14,852) | 1.46% (555) | 40.40% (15,407) |
| City | B | 26,759 | 70.89% (18,970) | 27.38% (7,326) | 1.73% (463) | 29.11% (7,789) |

The City Hotel **file** has the higher cancellation rate and the higher no-show rate under both conventions. Combined NonArrival is 40.40% vs 26.55% under A, and 29.11% vs 21.87% under B.

The **ranking survives A/B**. The **magnitude does not**: City Canceled falls 38.94 → 27.38 (−11.56 pp); Resort Canceled falls 25.94 → 21.19 (−4.75 pp). No-Show rates barely move and stay rare.

This is a difference between two booking extracts with different mix and duplicate structure. It is not a ranking of hotel operational performance.

## Market segment

NonArrival rate (Canceled and No-Show shown separately in the tables). Major segments:

| Segment | Resort A | Resort B | City A | City B |
|---|---|---|---|---|
| Online TA | 33.80% n=7,953 (C 33.14 / NS 0.65) | 32.35% n=7,474 (C 31.67 / NS 0.68) | 36.27% n=19,708 (C 34.71 / NS 1.56) | 34.87% n=17,868 (C 33.33 / NS 1.54) |
| Offline TA/TO | 12.15% n=3,472 | 10.55% n=3,129 | 43.42% n=9,001 | 16.27% n=3,951 |
| Direct | 12.33% n=2,943 | 12.04% n=2,840 | 18.53% n=2,720 | 17.50% n=2,486 |
| Groups | 42.68% n=3,170 | 18.89% n=1,228 | 74.65% n=4,687 | 34.81% n=813 |
| Corporate | 9.29% n=926 | 9.27% n=863 | 17.67% n=1,636 | 11.58% n=1,269 |

**Relatively stable, lower NonArrival:** Resort Corporate (~9%), Resort Direct and Offline TA/TO (~10–12%), City Direct (~18%). **Relatively stable, higher NonArrival:** Online TA in both hotels (about 32–36%).

**Duplicate-sensitive:** Groups and City Offline TA/TO. Under A, City Groups NonArrival is 74.65% and City Offline TA/TO is 43.42%. Under B those fall to 34.81% and 16.27%. Resort Groups falls 42.68 → 18.89, and is then **below** Resort Online TA (32.35%). Groups does **not** remain the unusual high-NonArrival segment once identical rows are collapsed.

That collapse is not a generic Groups effect. Groups rows with **No Deposit** have NonArrival of 25.90% (Resort A) / 14.92% (Resort B) and 25.58% / 17.55% (City). The A-only spike sits in **Non Refund × Groups** (and, in the City file, **Non Refund × Offline TA/TO**). See Deposit type.

Complementary (n ≈ 100–260) and Aviation (n ≈ 120) are retained in the CSV and not used as headline segments. No-Show at segment level is generally <2%; City Direct No-Show is 3.27% (89 / 2,720 under A) and is not promoted further.

`MarketSegment = Groups` is not `CustomerType = Group`.

## Deposit type

Published categories only. Association in a final snapshot, not a policy effect.

| Deposit | Resort A | Resort B | City A | City B |
|---|---|---|---|---|
| No Deposit | 23.30% NA n=17,555 (C 22.67 / NS 0.63) | 21.60% n=15,455 | 29.53% n=32,227 (C 27.81 / NS 1.72) | 28.23% n=26,398 |
| Non Refund | 93.89% NA n=884 (C 93.78 / NS 0.11) | 78.79% n=99 (C 77.78 / NS 1.01) | 99.63% NA n=5,910 (C 99.63 / NS 0) | 93.87% n=359 (C 93.87 / NS 0) |
| Refundable | 7.03% NA n=128 | 3.85% n=78 | n=3 | n=2 |

**Non Refund rows are strongly concentrated in Canceled outcomes in this extract.** Under A, 829 / 884 Resort Non Refund rows and 5,888 / 5,910 City Non Refund rows are Canceled. The association **remains** under B (77.78% and 93.87% Canceled), but the **file share of Non Refund collapses**: Resort 4.8% of rows (884) → 0.6% (99); City 15.5% (5,910) → 1.3% (359). Non Refund accounts for 17.2% of Resort Canceled rows under A vs 2.3% under B, and 39.6% of City Canceled rows under A vs 4.6% under B.

This does **not** say that non-refundable deposits cause cancellations, increase cancellation risk, or should be used or refused. The extract is a final snapshot. Repeated identical Non Refund rows may be rooms, legitimate identical bookings, extraction duplicates, or a mixture; the file cannot say.

Refundable is too small in the City file (n = 3 / 2) to interpret. Resort Refundable NonArrival is low (7.03% A / 3.85% B) with modest n.

### Non Refund × Groups

| Hotel | Convention | Non Refund n | of which Groups | Groups × Non Refund NA | Groups × No Deposit NA |
|---|---|---:|---:|---|---|
| Resort | A | 884 | 818 (92.5%) | 93.77% n=818 | 25.90% n=2,228 |
| Resort | B | 99 | 88 (88.9%) | 79.55% n=88 | 14.92% n=1,066 |
| City | A | 5,910 | 3,096 (52.4%) | 99.87% n=3,096 | 25.58% n=1,591 |
| City | B | 359 | 175 (48.7%) | 97.71% n=175 | 17.55% n=638 |

City Non Refund is also concentrated in Offline TA/TO: 2,692 rows under A with 99.96% Canceled, collapsing to 134 rows under B still at 99.25% Canceled.

The large A/B drops in City Groups, City Offline TA/TO, and hotel-level City Canceled are therefore **the same duplicate blocks**: identical Non Refund rows, mainly Groups and Offline TA/TO, counted many times under A and once under B. No Deposit rates move much less.

## Booking window

NonArrival rate by `LeadTimeBand`:

| Band | Resort A | Resort B | City A | City B |
|---|---:|---:|---:|---:|
| 0 days | 4.75% n=1,559 | 4.59% n=1,502 | 8.34% n=1,499 | 7.85% n=1,402 |
| 1–7 days | 6.88% n=2,762 | 6.35% n=2,614 | 14.39% n=4,003 | 12.49% n=3,668 |
| 8–30 days | 21.06% n=3,072 | 19.91% n=2,763 | 31.32% n=5,775 | 29.58% n=5,057 |
| 31–90 days | 32.78% n=3,749 | 30.12% n=3,237 | 38.66% n=10,264 | 33.28% n=8,227 |
| 91–180 days | 38.99% n=3,909 | 31.57% n=3,079 | 45.51% n=8,337 | 33.90% n=5,667 |
| 181+ days | 36.01% n=3,516 | 28.19% n=2,437 | 62.15% n=8,262 | 38.93% n=2,738 |

Canceled dominates these rates; No-Show is highest in short-lead City bands (0-day 3.34% A, n=50 / 1,499) and is not a long-lead phenomenon.

**Resort: not monotonic.** NonArrival rises from same-day (4.75% A) through 91–180 days (38.99%), then eases at 181+ (36.01%). Under B the same shape holds (peak 31.57% at 91–180, then 28.19% at 181+). Longer stored lead time is associated with higher NonArrival than same-week bookings, but the longest band is not the highest.

**City: increasing, with a duplicate-sensitive long tail.** Under A the association is **monotonic** (8.34 → 14.39 → 31.32 → 38.66 → 45.51 → 62.15). Under B it is still **increasing overall** but almost flat from 31–90 through 91–180 (33.28 vs 33.90), with 181+ at 38.93 rather than 62.15. The 181+ City reading under A is largely repeated identical rows (8,262 → 2,738).

Longer lead time is **associated with** higher NonArrival in the stored extract than very short lead time, in both hotels, under both conventions. That is not a claim that long lead time causes cancellation, and it is not a pickup curve.

## Customer type

| Type | Resort A | Resort B | City A | City B |
|---|---|---|---|---|
| Transient | 29.20% NA n=14,093 | 24.29% n=12,776 | 44.91% n=30,298 | 31.20% n=22,880 |
| Transient-Party | 20.49% n=3,793 | 12.69% n=2,222 | 22.39% n=7,600 | 15.87% n=3,679 |
| Contract | 5.90% n=576 | 5.57% n=539 | 50.00% n=180 | 44.44% n=144 |
| Group | 3.81% n=105 | 4.21% n=95 | 11.29% n=62 | 5.36% n=56 |

Transient is the majority type and has a higher NonArrival rate than Transient-Party in both hotels under both conventions. City Transient NonArrival falls 44.91 → 31.20 because Transient includes much of the duplicated Non Refund mass. Resort Contract stays low (~6%) with usable n. City Contract (n = 180 / 144) and `CustomerType = Group` (under 1%) are not interpreted as commercial patterns. `CustomerType = Group` is not `MarketSegment = Groups`.

## No-show context

No-Show is rare. Resort: 113 / 18,567 = 0.61% under A and 107 / 15,632 = 0.68% under B. City: 555 / 38,140 = 1.46% and 463 / 26,759 = 1.73%. The City file has the higher no-show rate under both conventions. Segment-level No-Show rates are generally too small for headline claims; they are retained in the tables. No-Show is never merged into Canceled in this profile.

## Duplicate sensitivity

Largest A → B movements in NonArrival rate:

| Comparison | A | B | Change |
|---|---:|---:|---:|
| City Groups | 74.65% | 34.81% | −39.84 pp |
| City Offline TA/TO | 43.42% | 16.27% | −27.14 pp |
| City 181+ days | 62.15% | 38.93% | −23.22 pp |
| Resort Groups | 42.68% | 18.89% | −23.79 pp |
| City hotel-level NonArrival | 40.40% | 29.11% | −11.29 pp |
| City Transient | 44.91% | 31.20% | −13.72 pp |
| Resort Non Refund (rate) | 93.89% | 78.79% | −15.10 pp |
| City Non Refund **share of file** | 15.5% | 1.3% | −14.2 pp |

These movements share a structure: identical Non Refund rows, especially Groups and City Offline TA/TO, and long-lead City rows. Online TA, Direct, No Deposit, and short-lead bands move by a few percentage points.

## Outcome-adjacent variable diagnostic

These fields are **not** used as booking-time associations in the main profile.

**RequiredCarParkingSpaces.** Every row with parking requested > 0 is Check-Out: 7,416 / 7,416 in the full extract (Resort 5,490; City 1,926) and 3,862 / 3,862 in 2016 (Resort 2,666; City 1,196). Zero non-arrivals. In this final snapshot parking is perfectly separated from Canceled and No-Show, so it cannot be read as a booking-time non-arrival factor.

**ReservationStatusDate** is the date attached to the final status. It is not a booking-time attribute.

**AssignedRoomType** is the assigned room, typically known at or after arrival. In 2016, rows with Assigned ≠ Reserved have NonArrival 5.33% (407 / 7,630) versus a much higher rate when assigned equals reserved. That pattern is outcome-adjacent (stay occurred and a room was assigned), not a pre-arrival factor.

**BookingChanges** and **TotalOfSpecialRequests** are also lower-NonArrival among positive values in 2016 (changes > 0: 15.85%; special requests > 0: 18.08%). Both can be updated after the initial booking, including on stays that later check out. They are not treated as cancellation “drivers” here.

## Robust findings

1. The City Hotel file has a higher cancellation rate and a higher no-show rate than the Resort Hotel file in 2016 under A and B (Canceled 38.94% vs 25.94% under A; 27.38% vs 21.19% under B).
2. No-Show is rare in both files (Resort ~0.6%; City ~1.5–1.7%) and is not the source of the hotel gap.
3. Online TA NonArrival is about one-third in both hotels and moves little under B (Resort 33.80 → 32.35; City 36.27 → 34.87).
4. Direct NonArrival is lower than Online TA in both hotels and is stable (~12% Resort; ~18% City).
5. Resort Corporate NonArrival is about 9% under A and B.
6. No Deposit NonArrival is stable (Resort 23.30 → 21.60; City 29.53 → 28.23) and well below Non Refund.
7. Non Refund rows are concentrated in Canceled outcomes under both conventions (Resort 93.78% / 77.78% Canceled; City 99.63% / 93.87%). This is an association in the extract, not a policy effect.
8. Same-week lead times are associated with much lower NonArrival than 31+ day bands in both hotels under A and B.
9. `CustomerType = Group` is rare (<1%) and is not `MarketSegment = Groups`.
10. Every `RequiredCarParkingSpaces > 0` row is Check-Out (7,416 full extract; 3,862 in 2016).

## Robust direction / sensitive magnitude

1. City vs Resort hotel-level NonArrival: City higher under both conventions; the gap shrinks from 13.84 pp (A) to 7.24 pp (B).
2. Non Refund remains high-Canceled under B, but its **share of the file and of Canceled rows** collapses, and the Resort Non Refund rate itself falls 93.89 → 78.79 with n = 884 → 99.
3. Longer lead time is associated with higher NonArrival than very short lead time in both hotels; the size of the long-lead City rate is duplicate-sensitive (181+ 62.15% A vs 38.93% B).
4. Transient NonArrival is higher than Transient-Party in both hotels; City Transient magnitude (44.91 → 31.20) tracks duplicate Non Refund blocks.
5. Resort 91–180 remains the highest Resort lead-time band under A and B, but 38.99% vs 31.57%.

## Duplicate-sensitive findings

1. **Groups NonArrival.** Under A, Groups looks like the high-NonArrival segment (Resort 42.68%; City 74.65%). Under B it does not (Resort 18.89%, below Online TA; City 34.81%, similar to Online TA). The A spike is Non Refund × Groups duplicate blocks.
2. **City Offline TA/TO NonArrival** (43.42% A vs 16.27% B), explained by Non Refund × Offline TA/TO (2,692 rows at ~100% Canceled under A → 134 under B).
3. **City 181+ NonArrival** as an extreme long-lead rate (62% vs 39%). Direction (higher than short-lead) survives; the 62% figure does not.
4. **Whether Groups “remains unusual” after deduplication:** no, not as a high-NonArrival segment. Groups **file share** remains convention-dependent (Phase 3).
5. Absolute 2016 cancellation *counts* (City 14,852 vs 7,326) are not a demand or rooms-lost measure without choosing A or B.

## Limitations

- Final snapshot outcomes only. No cancellation probability, no predicted risk, no causal claim.
- No overbooking recommendation and no deposit-policy recommendation.
- No lost-revenue, rooms-lost, or demand-lost estimate. Row counts are not rooms.
- Non Refund / Groups / Offline TA/TO duplicate blocks cannot be classified as rooms vs extraction artefacts.
- No-Show samples are small at segment level.
- Refundable, Complementary, Aviation, City Contract, and `CustomerType = Group` are too small or too convention-thin for commercial claims.
- Monthly NonArrival was computed; City months are noisy and duplicate-sensitive, and the mild Resort summer elevation is not separated from mix, so seasonality is not a headline finding.
- Parking, assigned room, booking changes, special requests, and status date are outcome-adjacent in this extract.

Supporting tables: `outputs/tables/nonarrival_*`. Figures: `outputs/figures/nonarrival_*_2016.png`. Regenerated with `python -m hospitality_analytics.nonarrival_analysis`.

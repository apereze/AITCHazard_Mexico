# Meeting 2026-11-16: Block 1 campaign, link to ITCHI and work plan

Prepared 2026-11-12, updated 2026-11-15, for the meeting with Tom and Milton.
Background: `docs/decisions.md` (D1-D16, O1-O16), `docs/framework.md`, `docs/block1-aifs.md`,
ITCHI: [`apereze/itchi-core`](https://github.com/apereze/itchi-core) v0.2.1.

## Agenda (60 min)

1. Block 1 status and the five launch decisions O1-O5 (20 min).
2. Training years (agreed): case counts for 2023-2025 and what follows (10 min).
3. ITCHI: status, and what AITCHazard has to deliver to it (10 min).
4. Path to a first forecast ITCHI case; Blocks 2 and 3 open questions (O10, O11) (10 min).
5. Work plan until the next meeting, WeatherNext 3 comparison, and date (10 min).

Expected outcome: O1-O5 decided so the campaign can start this week; a direction for
O10 (precipitation bias) and O11 (intensity correction); agreement on the deliverables
for the next meeting.

## Status

The production chain runs end to end on Curnagl: monthly ERA5 download from the CDS,
`run_aifs_month.py` as one Slurm array task per (year, month), NetCDF output in the format
TempestExtremes reads (CF `time` dimension, D13), manifest per task.

Pilot May 2023 (task 161): 124/124 forecasts, 0 failures, 0 NaN or range issues, 27 min
wall time, 248 files (2.7 GB); the task resumed correctly after a 2-forecast smoke test.
TempestExtremes (commit `cafb070`) detects Emily 2005 at all 13 times of a 72 h AIFS forecast.

Measured (A100 40 GB, 2 CPUs, 16 GB):

| Quantity | Value |
|---|---|
| Time per forecast | 12.95 s median; first forecast of a task about 50 s (lazy checkpoint load) |
| Wall time per month task | 27 min (31 days) -> `--time=01:00:00` |
| RSS peak / VRAM peak | 5.7 GiB / 20.7 GiB |
| Output per month (`split`) | 2.7 GB -> 0.49 TB for 182 months |
| ERA5 per month | 23.4 GB (pl 19, sfc 3.4, soil 1.0) -> 4.4 TB for 182 months |
| ERA5 download per month | 33 min mean, 25-47 min (pl 17-41 min); June-November 2023, measured 2026-11-12 |
| GPU time, full campaign | about 84 h including per-task overhead |
| Project quota (`/work`) | 107 of 342 TB used; 8.18 M of 8.99 M files (91 %) |

The CDS, not the GPU, sets the pace: about 100 h of sequential downloads (about 145 h at the
slowest measured month) against about 84 GPU hours. Downloads must run ahead of the GPU tasks, and in parallel if the CDS allows it.

## Decisions needed

| | Question | Recommendation | Owner |
|---|---|---|---|
| O1 | Run 2023-2025 first? | Yes | Tom |
| O2 | `split` or `single` | `split` | Adolfo (for information) |
| O3 | Eastern edge 310 or 330 E | 310 E, candidates kept 6.5 deg from the edges | Milton |
| O4 | Extra variables for Block 3 | u, v at 200 and 850 hPa and 100u, 100v on the tempest domain | Tom, Milton |
| O5 | Keep or delete ERA5 GRIB | Keep (quota allows it) | Adolfo, Tom |

**O1.** 2023-2025 is 21 tasks, 2 568 forecasts, about 10 GPU hours; ERA5 for May-November 2023 is
already on Curnagl, and 2024-2025 needs about 8 h of downloads. It covers storms relevant for Mexico (e.g. Otis 2023, Beryl and John 2024) and
lets tracking, the wind model and ITCHI run end to end before the remaining GPU hours are
spent. 2023-2025 are also the validation and test years agreed for SwAIther (D17).

**O2.** Each consumer reads only its file: SwAIther the regional domain (11 channels),
TempestExtremes the tempest domain (5 fields). `single` stores the union of variables on the
extended domain (0.65 TB) and every reader must crop. Two files per forecast add about
44 500 files (see the file quota under O5).

**O3.** On the Emily test, `DetectNodes` also returns candidates on the domain boundary
(44.75 N). Restricting candidates to at least 6.5 deg (the largest closed-contour radius)
inside the stored domain removes them without changing the files. With 310 E, candidates
reach 303.5 E. A system east of that at t0 would need a translation speed above about 12 m/s
to reach Mexico within 72 h, so 330 E (+0.14 TB) adds little to the hazard over Mexico.
Milton: is there a tracking reason (StitchNodes continuity, matching to IBTrACS at t0) to
see systems further east?

**O4.** The only decision that cannot be fixed later without rerunning the campaign
(about 84 GPU h plus downloads). The v1.1 checkpoint provides u and v on all 13 pressure
levels and 100u, 100v. Vertical shear (200-850 hPa) and the steering flow are standard
predictors for the intensity correction (O11); 100 m wind is closer to the surface wind used
for hazard. Rough cost from the tempest file: about 0.05 TB per extra field, about 0.3 TB for
six (upper-level winds compress worse; up to about 1.5 times that).

**O5.** The project has 234 TB free, so the 4.4 TB of ERA5 can be kept; deleting it would
make any rerun (an O4 change, O16) cost about 100 h of downloads again. The binding limit is
the number of files: the group uses 91 % of its file quota. The campaign adds about 45 000
files (about 5 % of the remaining margin), but if the quota is reached by anyone in the group,
writes fail for everyone during the campaign. To discuss with Tom.

## If time allows

O11 (intensity correction, Emily about 60 hPa too weak already in ERA5 at t0), O15 (genesis
inside the 72 h window, spurious minima over terrain), O16 (subset with operational initial
conditions).

## Training years (agreed earlier with Tom)

AIFS Single v1.1 is pre-trained on ERA5 1979-2022 and fine-tuned on ECMWF operational
analyses 2016-2022 (Moldovan et al. 2026, GMD 19, 4703,
https://gmd.copernicus.org/articles/19/4703/2026/). Agreed mitigation:

- SwAIther-Precip trained up to 2022; 2023-2024 for validation, 2025 for testing (D17).
  If 2023-2025 hold too few TC cases, some in-sample years are used as validation years.
- Wind hazard model: few samples for many features, so feature selection, diagnosed on
  the validation years.
- Blocks 2 (precipitation) and 3 (wind) are parallel: SwAIther outputs are not inputs to
  the wind model. This matches the ITCHI structure (precipitation and wind combined only
  in the index).
- WeatherNext 3 as comparison on 2024-2025 (below).

To report: number of TC cases per year in 2023, 2024 and 2025 (IBTrACS NA + EP inside the
regional domain), which decides whether the fallback is needed.

## ITCHI (complementary work, itchi-core)

ITCHI is the observed TC hazard index over Mexico (MSWEP V3.16 precipitation and parametric
W06 wind from best tracks, 2000-2025). AITCHazard is its forecast layer: it produces the
same inputs from AIFS so ITCHI can be computed by lead time (ITCHI v0.3, phase F5).

**v0.2.1 (released 2026-10-30).** Single entry point `compute_itchi_snapshot_v02`;
precipitation as a class table P6 x R24 x A72 against MSWEP percentiles; W06 wind per
quadrant calibrated to R34; attribution radius ROCLOUD with an R_W06 floor (R_W06 = radius
of 2 m/s, Perez-Alarcon et al. 2021). Experiment on 381 929 municipality-cyclone pairs
against disaster declarations (ordinal check only):

- P95 of 6 h as maximum hazard is not adopted (rain-only AUC 0.869 -> 0.842);
- R24 and A72 add information only above P95 (P(D) from 5.7 % to 21.8 % with A72 >= P95);
- cutting the wind tail at 17 kt recovers class 1 (PSS 0.480, against 0.000 with the
  tail to R_W06).

**v0.3 plan (branch `dev/v0.3`).** Hazard defined by climatological rarity, not by
declarations: F1 return periods of R6, R24, R72 per pixel (GEV and POT; code committed
2026-10-30); F2 catalogue of physical states under each cyclone; F3 schemes on the catalogue
(rain levels in years, wind in local Saffir-Simpson categories, ITCHI = max of both);
F4 ITCHI climatology 2000-2025 (hazard paper); F5 forecast ITCHI with AIFS.

**What AITCHazard must deliver to ITCHI** (`docs/hazard-itchi.md`): per initialisation and
lead, a track table (centre, Vmax, Pmin, RMW, R34 per quadrant) and P6 on the MSWEP 0.1
grid; R24 and A72 are built from P6, and A72 mixes observed MSWEP before t0 with the
forecast after t0 (O14).

Wind normalisation: the v0.2.1 work (branch `avance/v0.2.1-casos`) already offers the
absolute Saffir-Simpson scale (`wind.hazard_scale: saffir_simpson`, nodes 34/64/96/113/137 kt
-> H_W 0.2/0.4/0.6/0.8/1.0; used in the case studies), alongside the Vmax-relative form. With
the absolute scale the AIFS intensity bias limits the wind hazard directly, so O11 is
required for forecast ITCHI.

## Path to a first forecast ITCHI case

Proposal: one out-of-sample case end to end with the simplest choice at each step, before
SwAIther and the intensity correction exist.

| Step | Simplest version | Status |
|---|---|---|
| AIFS forecasts | June-November 2023 (ERA5 already on Curnagl, about 3 GPU h) | launched 2026-11-15 (tasks 162-167) |
| Track | TempestExtremes (TCBench parameters) + IBTrACS matching at t0 | detection tested on Emily 2005 |
| Wind | Parametric R34 and ROCLOUD (PA21) from (a) raw AIFS Vmax, (b) IBTrACS Vmax as an oracle | ITCHI code exists |
| Precipitation | Raw AIFS P6 interpolated to 0.1; A72 from MSWEP before t0 | converter in progress |
| Index | `compute_itchi_snapshot_v02` per lead, against the observed ITCHI | ITCHI code exists |

Candidate cases: Hilary 2023 (August, rain over the Baja California peninsula and the
northwest) and Otis 2023 (October, rapid intensification at Acapulco, worst case for O11).
The oracle run (b) separates the track and precipitation errors from the intensity error.

## Work plan until the next meeting (two weeks)

| Item | Done when |
|---|---|
| Campaign 2023-2025 (if O1) | 21 tasks written, manifests clean; ERA5 2024-2025 downloaded |
| Tracking | TempestExtremes on all 2023 forecasts, IBTrACS NA + EP matching, false alarms per month, track error by lead against persistence |
| Block 2 | Converter to the SwAIther format; MSWEP 6 h and DEM on Curnagl; SwAIther container; `model_size: mini` run end to end (shapes only) |
| ITCHI | F1 run with MSWEP and reviewed; F2 storage format decided |
| Forecast ITCHI | Hilary 2023 with raw AIFS, versions (a) and (b) |
| WeatherNext 3 | Access route (Cloud Storage or BigQuery) and volume for 2024-2025 over the domain |

## WeatherNext 3 for comparison

Per the model guide (https://developers.google.com/weathernext/guides/models):
64-member ensemble; 0.1 surface fields (0.25 on pressure levels); three 1 h precipitation
products (model, IMERG-calibrated, PARDIG-trained); 15-day leads from 00/06/12/18 UTC;
historical forecasts from 2024, 8 initialisations per day in 2024-2025; access through
BigQuery, Earth Engine and Cloud Storage (pressure levels only on Cloud Storage). The page
gives no training years and does not mention IBTrACS scalars; both to confirm. Natural
use: P6 and track comparison on the 2024-2025 validation and test years.

## Questions beyond O1-O5

- Tom: O10, i.e. SwAIther against observed percentiles, raw AIFS against its own
  climatology, or both; whether the 2023-2025 case counts are enough or the fallback
  (in-sample validation years) is needed.
- Milton: whether the post-processed intensity of Gomez et al. (2025) applies to AIFS v1.1
  initialised from ERA5 (O11); tracking reason for 330 E (O3); genesis inside the 72 h
  window and spurious minima over the Sierra Madre (O15).

## Results added 2026-11-15

**Tracking, negative and positive controls** (`scripts/tracking/te_month.sh`, TCBench
parameters, candidates >= 6.5 deg inside the domain; `--range 5`, `--maxgap 0` and the
10 m/s wind threshold still to check against the TCBench code).

- May 2023 (124 forecasts, no TC in IBTrACS NA/EP): 14 `DetectNodes` candidates, 0 tracks,
  so 0 false alarms. Candidates: one at the latitude limit (6 May); a 1007-1008 hPa low near
  24.5 N, 71.5 W (21-22 May) and a 1004 hPa low near 31.5 N, 79.5 W (27-28 May), each lasting
  at most 2 nodes per forecast, so removed by the 3-node minimum.
- Arlene 2023 (disturbance from 31 May 18 UTC, tropical from 1 June 12 UTC, Gulf of Mexico):
  no candidate in the forecasts of 30-31 May. Not a miss under the TCBench protocol (not
  active at t0), but a genesis inside the 72 h window that AIFS did not produce (O15).
- Emily 2005 (init 17 July 00 UTC), same options: Emily tracked at all 13 times (Pmin 971 hPa,
  maximum 10 m wind 22-30 m/s on the 0.25 grid) and Eugene from 18 July 18 UTC (6 nodes,
  1002-1006 hPa). IBTrACS has Eugene at 15.9 N, 105.0 W, 35 kt at that time (first fix 18 July
  06 UTC): a genesis inside the window that AIFS did produce (O15).

**TC cases per season** (`scripts/tracking/ibtracs_counts.py`; NA + EP systems with at least
one fix in 5-35 N, 130-60 W, May-November):

| | Systems | Reaching 34 kt in the domain |
|---|---|---|
| Mean 2000-2022 | 30.3 | 26.7 |
| 2023 | 29 | 24 |
| 2024 | 27 | 26 |
| 2025 | 28 | 28 |

The validation (2023-2024) and test (2025) seasons are ordinary: about 56 and 28 systems.
Enough for SwAIther (trained on fields), short for the wind model, where the independent
unit is the storm (feature selection, D17). Systems affecting Mexico are fewer; count by
distance to the coast if needed.

- Time-window check AIFS tp vs MSWEP 6 h (lag correlation): pending.

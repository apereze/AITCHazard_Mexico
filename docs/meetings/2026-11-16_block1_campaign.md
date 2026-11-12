# Block 1 campaign: decisions before launch

Prepared 2026-11-12 for the meeting with Tom and Milton (16 or 23 November).
Background: `docs/decisions.md` (D1-D16, O1-O16), `docs/block1-aifs.md`.

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
| ERA5 download per month | about 55 min (pl about 45 min) |
| GPU time, full campaign | about 84 h including per-task overhead |
| Project quota (`/work`) | 107 of 342 TB used; 8.18 M of 8.99 M files (91 %) |

The CDS, not the GPU, sets the pace: about 170 h of sequential downloads against about
84 GPU hours. Downloads must run ahead of the GPU tasks, and in parallel if the CDS allows it.

## Decisions needed

| | Question | Recommendation | Owner |
|---|---|---|---|
| O1 | Run 2023-2025 first? | Yes | Tom |
| O2 | `split` or `single` | `split` | Adolfo (for information) |
| O3 | Eastern edge 310 or 330 E | 310 E, candidates kept 6.5 deg from the edges | Milton |
| O4 | Extra variables for Block 3 | u, v at 200 and 850 hPa and 100u, 100v on the tempest domain | Tom, Milton |
| O5 | Keep or delete ERA5 GRIB | Keep (quota allows it) | Adolfo, Tom |

**O1.** 2023-2025 is 21 tasks, 2 568 forecasts, about 10 GPU hours and about 19 h of
downloads. It covers storms relevant for Mexico (e.g. Otis 2023, Beryl and John 2024) and
lets tracking, the wind model and ITCHI run end to end before the remaining GPU hours are
spent. Question for Tom: whether 2000-2022 overlaps the AIFS v1.1 training period, since
in-sample hindcasts would bias the comparison with observed ITCHI.

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
make any rerun (an O4 change, O16) cost about 170 h of downloads again. The binding limit is
the number of files: the group uses 91 % of its file quota. The campaign adds about 45 000
files (about 5 % of the remaining margin), but if the quota is reached by anyone in the group,
writes fail for everyone during the campaign. To discuss with Tom.

## If time allows

O11 (intensity correction, Emily about 60 hPa too weak already in ERA5 at t0), O15 (genesis
inside the 72 h window, spurious minima over terrain), O16 (subset with operational initial
conditions).

# Decision log

Last updated: 2026-11-08. One line per decision; the rationale is in the block documents.

## Decided

| ID | Block | Decision | Date |
|---|---|---|---|
| D1 | 1 | AIFS Single v1.1 (`ecmwf/aifs-single-1.1`, `aifs-single-mse-1.1.ckpt`); v2 discarded for the study period | 2026-09 |
| D2 | 1 | Initial conditions from ERA5 via CDS (no MARS access), t−6 h and t0 | 2026-09 |
| D3 | 1 | Full May–November seasons 2000–2025, 4 cycles per day (00/06/12/18 UTC), 0–72 h every 6 h | 2026-10-20 |
| D4 | 1 | Global N320 run; batched regridding to 0.25° restricted to the domain box | 2026-11-08 |
| D5 | 1 | Two domains: regional 5–35°N 230–300°E (Block 2) and extended −5–45°N 220–310°E (tracking) | 2026-10-20 |
| D6 | 1 | Environment: `aifs_single_v2_era5.sif` + `aifs/pylibs/aifs11` (torch_geometric 2.4.0, anemoi-models 0.5.0, anemoi-inference 0.6.3); the 1.1 checkpoint does not load with anemoi-models 0.9.3 | 2026-11-08 |
| D7 | 1 | `tp` and `cp` are per 6 h step (no differencing); t0 is taken from ERA5 because `runner.run` does not yield it | 2026-11-08 |
| D8 | 2 | Target: MSWEP V3.16 hourly aggregated to 6 h, window (T−6 h, T], reusing the ITCHI 6 h product | 2026-11-08 |
| D9 | 2 | Static altitude from the INEGI Continuo de Elevaciones Mexicano 15 m (`continuonacional_15m`) | 2026-11-08 |
| D10 | Tracking | TempestExtremes with the fields and parameters of TCBench (Gomez et al. 2026): msl, 10u, 10v, z300, z500 (+ zs); systems present at t0, matched to IBTrACS; minimum duration 12 h | 2026-11-08 |
| D11 | 3 | Wind hazard follows ITCHI: Willoughby et al. (2006) profile per quadrant, outer limit where the wind falls to 2 m/s (R_W06, Pérez-Alarcón et al. 2021), hazard normalised to Saffir-Simpson categories | 2026-11-08 |
| D12 | 3–4 | AIFS outputs are converted into ITCHI inputs (track table + 6 h precipitation) so ITCHI can be computed per lead time | 2026-11-08 |

## Open

| ID | Block | Question | Who decides | Needed before |
|---|---|---|---|---|
| O1 | 1 | Run 2023–2025 (out of sample, ~10 GPU-h) first? | Tom | Campaign |
| O2 | 1 | Output layout: `split` (0.51 TB) or `single` (0.65 TB) | Adolfo | Campaign |
| O3 | 1 | Eastern edge of the extended domain: 310°E or 330°E (+0.14 TB) | Milton | Campaign |
| O4 | 1 | Extra variables for Block 3 (u/v at 200 and 850 hPa for shear, 100u/100v) | Tom, Milton | Campaign (cannot be added later without rerunning) |
| O5 | 1 | Keep or delete the monthly ERA5 GRIB after verification (4.4 TB if kept) | Adolfo, DCSR quota | Campaign |
| O6 | 2 | Is Stage 2 worth it with a 2.5× factor (0.25° → 0.1°)? Compare against conservative interpolation | Tom | Block 2 training |
| O7 | 2 | Disable the per-image gamma capping at the 99.5th percentile (it removes TC rain extremes) | Tom | Block 2 preprocessing |
| O8 | 2 | Splits: Stage 2 perfect-prog on all years; Stage 1 calibrated only out of sample (2023–2025) | Tom | Block 2 training |
| O9 | 2 | DEM outside Mexico (INEGI covers Mexico only): fill with GMTED or ERA5 orography | Adolfo | Block 2 preprocessing |
| O10 | 2–4 | Precipitation bias: SwAIther correction against observed climatology, or raw AIFS against its own climatology by lead (ITCHI v0.3, P3), or both | Tutor, Tom | Block 4 |
| O11 | 3 | Intensity correction of AIFS (Emily: ~60 hPa too weak already at t0 in ERA5) | Milton | Block 3 |
| O12 | 3 | R34 per quadrant: from the AIFS 10 m wind field or parametric (PA21) from corrected Vmax | Milton, tutor | Block 3 |
| O13 | 3 | Exact Saffir-Simpson normalisation and tail cut (17 kt or 12 m/s) as in ITCHI v0.3 | Tutor | Block 3 |
| O14 | 4 | Antecedent window A72 mixes observed MSWEP (before t0) and forecast (after t0) | Tutor | Block 4 |
| O15 | Tracking | Genesis inside the 72 h window; spurious minima over high terrain at landfall | Milton | Tracking evaluation |
| O16 | 1 | Subset with operational initial conditions to measure the ERA5 → operational shift | Tom | Optional |

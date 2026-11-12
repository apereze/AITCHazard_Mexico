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

## Decisions of 2026-11-12 (Block 1 production)

**D13. Forecast file format: CF `time` dimension.** Forecast files are
`(time, latitude, longitude)`; `time` is the valid time encoded as `hours since <t0>`
(calendar `standard`, int32). `lead_time` (hours, `standard_name = forecast_period`) is a
coordinate along `time` and `init_time` a scalar coordinate (`forecast_reference_time`).
`latitude` and `longitude` carry no `_FillValue`. Reason: TempestExtremes `DetectNodes`
stops with *Dimension "time" or equivalent not found* on `lead_time` files (tested
2026-11-12 on the Emily benchmark); the converted file is read and Emily is detected at all
13 times. Readers that index by lead time use `ds.swap_dims(time="lead_time")`.
Implemented in `src/aitchazard/block1/output.py` (commit ce0cad0).

**D14. TempestExtremes build.** Commit `cafb070` (master, 2026-11-11), built on Curnagl with
`gcc/11.5.0`, `cmake/3.31.9`, `netcdf-c/4.9.3`, `-DENABLE_MPI=OFF`,
`-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON` (the Spack `netcdf-c` module does not set
`LD_LIBRARY_PATH`; without the RPATH the installed binaries fail to find `libnetcdf.so.22`).
Executables: `$BASE/software/tempestextremes/bin`. Pending: compare with the version used by
Gomez et al. 2026 (TCBench).

**D15. Production runner.** `scripts/block1/run_aifs_month.py` runs one (year, month) array
task (`slurm/block1_campaign.slurm`; task 161 = 2023-05). Output
`outputs/block1/{domain}/{YYYY}/{MM}/aifs11_{domain}_{YYYYMMDDHH}.nc` plus
`outputs/block1/{domain}/static_{domain}.nc`; forecasts with files for every domain are
skipped; atomic writes; manifest `outputs/block1/manifests/YYYY-MM.json` rewritten after each
forecast and on SIGTERM (status, counts, failures, NaN/range issues, timings, commit, versions).

**D16. Campaign environment.** The campaign keeps `aifs_single_v2_era5.sif` plus the
`PYTHONPATH` overlay used in the benchmark, so timings and Emily results stay comparable.
`containers/aifs_single_v1_1.def` documents the equivalent single image (overlay packages
installed with `--no-deps`); it is built after the campaign. The image chain starts from
`dawn_containers/AIFS/aifs-ens.sif`, outside this project: checksums are recorded in
`containers/README.md` and a copy of the v2_era5 image is kept with the campaign outputs.

### Notes for open questions (2026-11-12)

- **O1 / O5, ERA5 throughput.** May 2023 (sfc 3.4 GB, pl 19 GB, soil 1.0 GB) took about
  55 min from the CDS, about 45 min of it for pressure levels. Sequentially, 182 months need
  about 170 h of downloads against about 80 GPU hours: the CDS, not the GPU, sets the campaign
  pace unless downloads run ahead or in parallel.
- **O2, output size.** Smoke test (2023-05-01 00 and 06 UTC): 12 MB regional + 11 MB tempest
  per forecast, i.e. 0.51 TB for 22 256 forecasts with `split`, as estimated in the benchmark.
- **O3, eastern edge.** `DetectNodes` on the Emily file returns spurious candidates on the
  domain boundary (e.g. 44.75 N). Proposal: restrict candidates with
  `--minlat/--maxlat/--minlon/--maxlon` to at least 6.5 deg (the largest closed-contour
  radius) inside the stored domain. With -5-45 N, 220-310 E this keeps the regional domain
  plus a margin.
- **Resources.** Smoke test with `--cpus-per-task=2 --mem=16G`: 13.1 s per forecast after the
  first (53.8 s, includes lazy checkpoint load, CUDA initialisation and the first scan of the
  monthly GRIB), RSS peak 5.6 GiB, VRAM peak 20.7 GiB. Final values from the 2023-05 pilot.

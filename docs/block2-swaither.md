# Block 2 · Precipitation bias correction and downscaling (SwAIther-Precip)

Last updated: 2026-11-08. Status: design decided; no code yet.

Upstream: [danassou/swaither-precip](https://github.com/danassou/swaither-precip)
([Assouline et al. 2026](https://arxiv.org/abs/2605.16163)), Apache-2.0. Keep its licence
notices if code is copied.

## Upstream method (checked in the code, 2026-11-08)

- **Stage 1, lead-time-aware bias correction.** FiLM-conditioned U-Net that learns a
  residual correction of AIFS precipitation; Huber loss with cross-lead consistency
  (`lambda_time = 2`). Runs on the AIFS grid.
- **Stage 2, generative super-resolution.** CorrDiff (regression U-Net + EDM diffusion),
  PhysicsNeMo 1.2.0.
- **Original setting.** AIFS 1.0 with IFS initial conditions, 24 leads (0–144 h), 00/12 UTC,
  Switzerland 2019–2023, CombiPrecip 1 km target (block mean to 0.25° for Stage 1),
  DHM25 altitude.
- **Inputs.** The same 11 channels as our regional domain, named
  `total_precipitation_NoNeg`, `convective_precipitation_NoNeg`, `total_cloud_cover`,
  `wind_10m_u/v`, `specific_humidity_500/850hPa`, `temperature_500/850hPa`,
  `geopotential_500/850hPa`; static `altitude`.
- **Format.** NetCDF with `time` = valid time, `prediction_delta` = lead, `lat`, `lon`
  (class `CustomDownscalingDatasetWithLeadFast_Time`). Precipitation in mm per 6 h, clipped
  at 0.
- **Target preprocessing.** Drops times with ≥ 99.5 % dry pixels; caps each image at the
  99.5th percentile of a fitted gamma distribution.
- **Normalisation.** Robust min/max (0.5 and 99.5 percentiles) on the training split only.
- **Container.** `containers/swaither_precip.def` (`nvcr.io/nvidia/pytorch:25.08-py3`).

## Adaptation to Mexico

| Item | AITCHazard |
|---|---|
| Low-resolution input | Block 1 regional file, 0.25°, leads 6–72 h (12 leads), 4 cycles per day |
| Target | **MSWEP V3.16** hourly aggregated to 6 h, window (T−6 h, T], 0.1° (decision D8) |
| Stage 1 target | MSWEP 6 h remapped conservatively to 0.25° (0.25/0.1 = 2.5, so no block mean) |
| Stage 2 target | MSWEP 6 h at 0.1° |
| Static channel | INEGI Continuo de Elevaciones Mexicano 15 m, aggregated to 0.25° and 0.1° (decision D9) |
| Statistics | Recomputed on the Mexican training split; Swiss statistics are not reused |

### MSWEP 6 h product (shared with ITCHI)

ITCHI already builds it with `scripts/mswep_v3_6h_accum.py` in `itchi-core`:

- `precipitation(T)` = sum of the hourly values in (T−6 h, T], T ∈ {00, 06, 12, 18} UTC;
- season T ∈ [1 May 06 UTC, 1 Dec 00 UTC], 856 windows per year;
- a window with a missing hour is NaN (not filled);
- domain 5–35°N, 140–60°W (220–300°E); one file per year, `mswep_v3_6h_YYYY.nc`;
- current copy on Adolfo's computer: `D:/MSWEP_V316_6H/`. To be copied to
  `/work/.../apereze/data/mswep_v3_6h/` on Curnagl.

The same files give the 6/24/72 h percentiles (`p_wet_raw`) and, in ITCHI v0.3, the
return periods used by Block 4.

### DEM

- Source: INEGI, Continuo de Elevaciones Mexicano, 15 m (file `continuonacional_15m`;
  confirm the format and projection before processing).
- Aggregation: area mean to the 0.25° and 0.1° grids; keep the standard deviation as an
  optional orographic-complexity channel.
- INEGI covers Mexico only. Outside Mexico (United States, Guatemala, Belize, ocean): fill
  with GMTED2010 or the AIFS/ERA5 orography (open question O9).

## Proposals still to agree (see decisions O6–O10)

1. **Do not cap extremes.** Disable the gamma capping: it removes TC rain, and MSWEP has
   no radar artefacts.
2. **Splits by complete years.** Windows overlap between cycles, so weekly splits leak.
   Stage 2 trained in perfect-prog (degraded MSWEP → MSWEP) on all years; Stage 1
   calibrated only on out-of-sample seasons (2023–2025). Replace the "last two years"
   rule of `train_yearly.py` with explicit year lists.
3. **Stage 2 value.** The factor is only 2.5 (0.25° → 0.1°), against ~25 in Switzerland;
   keep Stage 2 only if it beats conservative interpolation.
4. **Forecast bias and ITCHI.** ITCHI v0.3 (P3) corrects forecast bias with the model's own
   climatology by lead. Decide whether Block 4 uses SwAIther-corrected precipitation
   against observed percentiles, raw AIFS against AIFS percentiles, or both.

## Implementation steps

1. Converter: Block 1 files (one per initialisation) → valid time × `prediction_delta`
   (6–72 h), m → mm, clip at 0, SwAIther variable names.
2. Copy the MSWEP 6 h files to Curnagl; conservative remap to 0.25°.
3. DEM processing (INEGI + fill) to both grids.
4. Build the SwAIther container on Curnagl (`--fakeroot`) or reuse a group image.
5. End-to-end test with `model_size: mini` on the benchmark and Emily days (shapes and
   flow only, no skill).

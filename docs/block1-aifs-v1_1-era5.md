# Block 1 decisions: AIFS Single v1.1 initialised from ERA5

Status: adopted. Supersedes the AIFS Single v2 / MARS plan in `docs/aifs-single-v2-execution.md`.

## Decisions

| Item | Decision | Rationale |
|---|---|---|
| Model | AIFS Single v1.1 (`ecmwf/aifs-single-1.1`) | v2 limitations for the study period |
| Initial conditions | ERA5 via CDS API, t-6 h and t0, 0.25 deg -> N320 | No MARS credentials |
| Period | Full May-November season, 2000-2025 | Training data for Block 2 beyond TC cases |
| Initialisation | 00, 06, 12, 18 UTC (22 256 forecasts) | |
| Horizon | t0 to t+72 h, 6-hourly (12 model steps) | |
| Execution grid | Global N320; cropping only after regridding to 0.25 deg | AIFS is global |
| Regional domain | 5-35N, 230-300E | SwAIther-Precip inputs |
| TempestExtremes domain | -5-45N, 220-310E | Closed-contour radii (5.5/6.5 deg GCD) need a buffer |

## Output variables

Regional file (SwAIther-Precip, 11 channels): `tp`, `cp`, `tcc`, `10u`, `10v`, `q_500`, `q_850`,
`t_500`, `t_850`, `z_500`, `z_850`.

TempestExtremes file: `msl`, `10u`, `10v`, `z_300`, `z_500`. Static: `zs` (m), `lsm`.

Geopotential is stored in m2 s-2 (TempestExtremes warm-core threshold of 58.8 m2 s-2 assumes it).
`tp` and `cp` are 6 h accumulations from the first step; undefined at t0.

## Known methodological caveats

- Part of 2000-2025 overlaps the AIFS training period (ERA5 pre-training; operational
  analyses fine-tuning). Forecast skill over those years is in-sample. Document the
  exact periods from the model card / AIFS Single 1.1.0 paper
  (https://gmd.copernicus.org/articles/19/4703/2026/).
- AIFS v1.x is fine-tuned on operational IFS analyses; ERA5 initial conditions are a
  distribution shift relative to operational use.
- SwAIther-Precip was developed with aifs-single-1.0 and IFS initial conditions; Step 1
  and all normalisation statistics must be retrained/recomputed for this dataset.
- Block 2 target requires 3-hourly MSWEP aggregated to 6 h (not the daily product).
- TempestExtremes StitchNodes defaults (mintime 54 h, 10-step thresholds) are designed for
  continuous records; recalibrate on ERA5 vs IBTrACS for 72 h windows before use.

## Data staging

ERA5 is staged monthly (`scripts/block1/download_era5.py`): about 624 CDS requests for the
full campaign instead of ~133 000 per-date requests. Layout: `data/era5/{YYYY}/{MM}/{sfc,pl,soil}.grib`.
Pressure-level monthly requests contain ~9 700 fields; split by variable if CDS rejects them.

# Block 2 SwAIther-Compatible Interface

This document defines the first interface between AITCHazard Block 1 and the SwAIther-style Block 2 downscaling pipeline.

## Low-Resolution Input

The low-resolution input should be generated from Block 1 AIFS Single v2 NetCDF outputs and exposed to Block 2 with dimensions compatible with SwAIther-style datasets:

- `time`: initialization or sample reference time.
- `prediction_delta`: lead time, every 6 hours from 0 to 72 hours.
- `lat`
- `lon`

Canonical AITCHazard variables remain in the Block 1 files. A Block 2 adapter may create SwAIther-compatible aliases.

## Variable Mapping

| AITCHazard canonical | SwAIther-style alias | Role |
|---|---|---|
| `tp_6h` | `total_precipitation_NoNeg` | Main precipitation predictor |
| `cp_6h` | `convective_precipitation_NoNeg` | Optional convective precipitation predictor |
| `10u` | `wind_10m_u` | 10 m zonal wind |
| `10v` | `wind_10m_v` | 10 m meridional wind |
| `q_500` | `specific_humidity_500hPa` | Mid-level moisture predictor |
| `q_850` | `specific_humidity_850hPa` | Lower-tropospheric moisture predictor |
| `t_500` | `temperature_500hPa` | Mid-level thermodynamic predictor |
| `t_850` | `temperature_850hPa` | Lower-tropospheric thermodynamic predictor |
| `z_500` | `geopotential_500hPa` | Mid-level geopotential predictor |
| `z_850` | `geopotential_850hPa` | Lower-tropospheric geopotential predictor |

Optional predictors may be added later, but this table is the initial compatibility target.

## High-Resolution Target

The high-resolution target replaces SwAIther's CombiPrecip product with an MSWEP-like 6-hour precipitation field over Mexico.

Initial target alias:

- `precip6h_cumulative_capped`

This alias may point to a capped/transformed MSWEP 6-hour accumulation after preprocessing. The raw canonical target name should be documented once the MSWEP preprocessing workflow is implemented.

## Static Fields

Initial invariant variable:

- `altitude`

Additional candidates:

- `land_sea_mask`
- `slope`
- `orography_std`
- hydroclimate or region masks, if justified later.

## Required Preprocessing

- Convert AIFS accumulated precipitation into 6-hour intervals before Block 2.
- Enforce non-negative precipitation after differencing.
- Pair AIFS valid times with MSWEP 6-hour accumulation windows.
- Coarsen MSWEP to the AIFS grid using a mass-conserving aggregation for Step 1 training.
- Regrid static topography/masks to both low-resolution and target grids.
- Compute new normalization statistics for Mexico; do not reuse SwAIther Switzerland stats.

## Initial Output Products

- `tp_6h_bc_coarse`: lead-time-aware bias-corrected coarse precipitation.
- `tp_6h_hr`: high-resolution downscaled precipitation.
- Optional probabilistic samples or ensemble dimension for diffusion outputs.

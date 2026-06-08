# Preliminary Block 1 NetCDF Schema

This document records the confirmed Block 1 output conventions. It is preliminary and should be refined before code implementation.

## Purpose

Block 1 should produce standardized regional NetCDF files from retrospective AIFS Single v2 forecasts over the Mexico domain.

## Domain

- Latitude: `5N` to `35N`.
- Longitude: `130W` to `60W`.
- Longitude in 0-360 convention: `230E` to `300E`.

## Time Coordinates

Recommended coordinates:

- `init_time`: forecast initialization time.
- `lead_time`: forecast lead time, every 6 hours from `0 h` to `72 h`.
- `valid_time`: forecast valid time derived from `init_time + lead_time`.

## Core Dimensions

Expected dimensions:

- `init_time`
- `lead_time`
- `valid_time` or a derived coordinate linked to `init_time` and `lead_time`
- `latitude`
- `longitude`
- `level` for pressure-level variables

The exact dimension strategy should be finalized when the writer is implemented.

## Surface and Near-Surface Variables

Recommended variables to preserve where available:

- `tp_raw`: total accumulated precipitation.
- `cp_raw`: accumulated convective precipitation.
- `10u`: 10 m zonal wind.
- `10v`: 10 m meridional wind.
- `msl`: mean sea-level pressure.
- `sp`: surface pressure.
- `2t`: 2 m temperature.
- `2d`: 2 m dewpoint temperature.
- `skt`: skin temperature.
- `sst`: sea-surface temperature, if available.
- `tcw`: total column water.

## Pressure-Level Variables

Recommended pressure-level families:

- `t_*`: temperature.
- `u_*`: zonal wind.
- `v_*`: meridional wind.
- `z_*`: geopotential or geopotential height.
- `q_*`: specific humidity.
- `w_*`: vertical velocity, optional.

Example levels of interest: `1000`, `925`, `850`, `700`, `600`, `500`, `400`, `300`, `250`, `200`, `150`, `100`, and `50` hPa.

## Static Fields

Recommended static or slowly varying fields:

- `lsm`: land-sea mask.
- `sdor`: standard deviation of orography.
- `slor`: slope of sub-gridscale orography.
- Other terrain or orography-related fields when available.

## Derived Variables

Derived variables should be computed during post-processing:

- `tp_6h`: 6-hour interval total precipitation.
- `cp_6h`: 6-hour interval convective precipitation, when `cp_raw` is available.
- `ws10`: 10 m wind speed derived from `10u` and `10v`.

The official precipitation predictor for Block 2 is `tp_6h`.

## Open Decisions

- Exact NetCDF file naming convention.
- One file per case, one file per initialization, or grouped files by storm/season.
- Compression and chunking strategy.
- Final CF metadata attributes.
- Handling of missing variables from AIFS Single v2 implementation constraints.

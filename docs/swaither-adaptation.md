# SwAIther-Precip Adaptation Plan

This document records how AITCHazard Mexico will use SwAIther-Precip as the main upstream technical reference for precipitation downscaling.

Upstream repository: `https://github.com/danassou/swaither-precip`
Inspected upstream commit: `f225b40`
Upstream license: Apache-2.0

## Decision

AITCHazard will align Block 2 with the SwAIther-Precip design:

1. Lead-time-aware coarse bias correction using a FiLM-conditioned residual U-Net.
2. Spatial super-resolution using a CorrDiff-style regression plus diffusion model.

This is an adaptation, not a direct Switzerland replication. AITCHazard targets Mexico, tropical cyclone cases, MSWEP-like precipitation, and AIFS Single v2.

## What Carries Over

- Two-stage downscaling design.
- Lead-time conditioning for coarse bias correction.
- Residual correction on top of raw AIFS precipitation.
- CorrDiff-style deterministic regression plus conditional diffusion for fine-scale structure.
- Hydra configuration pattern.
- Normalization-statistics workflow.
- Separation between training, inference, generation, and evaluation scripts.
- Container-first deployment philosophy for HPC.

## What Changes for AITCHazard

- AIFS source: `ecmwf/aifs-single-2.0`, not AIFS Single 1.0.
- Domain: Mexico and surrounding region (`5N-35N`, `130W-60W`).
- Time period: tropical cyclone cases from `2000-2025`.
- Forecast horizon: `t0` to `t+72 h`, stored every 6 hours.
- Low-resolution precipitation predictor: canonical `tp_6h` from Block 1.
- Optional convective precipitation predictor: canonical `cp_6h`.
- High-resolution target: MSWEP-like 6-hour precipitation instead of CombiPrecip.
- Static fields: Mexico-region DEM, land/sea mask, and optional terrain descriptors instead of DHM25.
- Evaluation: tropical-cyclone-centered, Mexico-domain, and hazard-relevant metrics.

## Integration Strategy

Do not copy the complete SwAIther codebase into this repository yet. The preferred first implementation path is:

1. Document the SwAIther-compatible NetCDF interface.
2. Build an adapter from Block 1 NetCDF outputs to SwAIther-style variable names and dimensions.
3. Add AITCHazard-specific Hydra configs.
4. Decide whether the long-term code relationship is a fork, submodule, or selective vendoring.
5. If any upstream code is copied, preserve Apache-2.0 license notices, SPDX headers, and the upstream `NOTICE` requirements.

## Block Mapping

- Block 1 provides AIFS Single v2 retrospective forecasts and derived variables.
- Block 2 consumes the Block 1 adapter output and trains/inferences SwAIther-style downscaling.
- Block 3 consumes high-resolution precipitation and meteorological context for wind/hazard modeling.
- Block 4 consumes hazard fields for final tropical cyclone hazard index prediction.

## Open Implementation Questions

- Exact MSWEP target grid and whether it should remain at native MSWEP resolution or be regridded.
- Whether super-resolution should be deterministic-only first, then diffusion later.
- Whether to train on all TC-adjacent times or broader rainy-season/background samples.
- Which terrain/static predictors should accompany `altitude`.
- Whether to keep SwAIther variable names internally in Block 2 or expose only AITCHazard names plus an adapter.

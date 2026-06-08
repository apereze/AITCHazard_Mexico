# Methodology Draft

This document summarizes the current manuscript-facing methodology for AITCHazard Mexico. It is a planning document, not a completed implementation report.

## Overview

The proposed workflow links AI weather forecasting, precipitation downscaling, wind hazard estimation, and hazard index prediction for tropical cyclone cases over Mexico. The design is organized around four blocks so that each scientific step has clear inputs, outputs, and validation needs.

## Block 1: Retrospective AIFS Forecasting

Block 1 generates the meteorological backbone. For selected tropical cyclone cases from `2000-2025`, AIFS Single v2 (`ecmwf/aifs-single-2.0`) will be run retrospectively using MARS-based atmospheric initial conditions. Forecasts are initialized every 6 hours and stored at 6-hour output intervals from `t0` to `t+72 h`.

The output domain is Mexico and surrounding regions: `5N-35N`, `130W-60W`. Outputs should be standardized as regional NetCDF files.

The central post-processing requirement is to convert accumulated precipitation into 6-hour interval fields:

- `tp_6h` from consecutive total precipitation accumulations.
- `cp_6h` from consecutive convective precipitation accumulations when available.

## Block 2: Precipitation Downscaling

Block 2 adapts SwAIther-Precip to downscale AIFS Single v2 precipitation toward an MSWEP-like target grid over Mexico. The preferred design is not a single direct super-resolution step. Instead, it is a two-stage framework:

1. Lead-time-aware coarse bias correction to reduce systematic forecast biases at the AIFS scale.
2. Spatial super-resolution to represent finer precipitation structure on the target grid.

The main precipitation predictor is `tp_6h`. The optional recommended precipitation predictor is `cp_6h`. SwAIther's Switzerland-specific CombiPrecip target, DHM25 topography, and AIFS Single 1.0 assumptions must be replaced with MSWEP-like precipitation, Mexico-region static fields, and AIFS Single v2 outputs.

## Block 3: Wind Hazard Estimation

Block 3 estimates wind hazard using meteorological fields from Block 1 and tropical cyclone structure information. Candidate inputs include near-surface winds, pressure fields, vertical atmospheric structure, and storm geometry.

The final wind hazard formulation, input variable list, and validation metrics remain open.

## Block 4: Hazard Index Prediction

Block 4 combines precipitation and wind hazard information into a final tropical cyclone hazard index. The index should preserve bounded hazard behavior and support later impact-oriented calibration.

The final integration strategy remains open and should be selected before implementation.

## Reproducibility Principle

The repository should separate scientific definitions from executable implementation. Until a workflow is implemented, documentation should describe intended behavior and unresolved decisions without presenting placeholders as complete code.

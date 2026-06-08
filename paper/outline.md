# Article Outline

## Working Title

AI-assisted multi-hazard forecasting for tropical cyclones over Mexico.

## Abstract

- Motivation: tropical cyclones produce compound wind and precipitation hazards across Mexico.
- Gap: forecasting spatially continuous hazard fields requires linking meteorological forecasts, downscaling, and hazard calibration.
- Method: four-block AITCHazard workflow using retrospective AIFS Single v2 forecasts, precipitation downscaling, wind hazard estimation, and final hazard index prediction.
- Expected contribution: reproducible framework for article-scale evaluation of tropical cyclone hazard prediction.

## Introduction

- Tropical cyclone hazard relevance for Mexico.
- Need for integrated wind and precipitation hazard representation.
- Role of AI weather forecasts and downscaling.
- Research objective and manuscript contribution.

## Methods

- Study domain and period: Mexico and surrounding region, `2000-2025`.
- Tropical cyclone case selection.
- Block 1: retrospective AIFS forecasting.
- Block 2: precipitation downscaling toward MSWEP-like target grid.
- Block 3: wind hazard estimation.
- Block 4: final hazard index prediction.
- Reproducibility and data governance.

## Expected Outputs

- Regional AIFS-derived meteorological NetCDF dataset.
- High-resolution precipitation product.
- Wind hazard fields.
- Final tropical cyclone hazard index fields.
- Publication-quality conceptual workflow figure.

## Evaluation

- Precipitation metrics remain to be finalized.
- Wind hazard metrics remain to be finalized.
- Hazard index validation strategy remains to be finalized.

## Limitations and Open Questions

- Target grid and resolution for Block 2.
- Deterministic versus probabilistic precipitation downscaling.
- Full wind hazard input variable list.
- Storage and compute strategy for large retrospective outputs.
- Final case selection rules near Mexico.

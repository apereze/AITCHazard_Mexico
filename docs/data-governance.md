# Data Governance

This repository documents reproducible workflows for tropical cyclone hazard research. It should not become an archive of large raw or generated scientific data.

## Tracked in Git

Track lightweight files that help reproduce the project:

- Source code and scripts once implemented.
- Small configuration files.
- Documentation and manuscript planning files.
- Lightweight metadata templates.
- Small, final publication figures when appropriate.

## Not Tracked in Git

Do not commit:

- Raw climate datasets.
- NetCDF files (`*.nc`, `*.nc4`, `*.cdf`).
- GRIB files (`*.grib`, `*.grib2`).
- Zarr stores (`*.zarr/`).
- Large rasters (`*.tif`, `*.tiff`).
- Model checkpoints and weights.
- Temporary HPC outputs, logs, and scratch files.
- Private documents, PDFs, or local reference libraries.
- Credential files such as `.ecmwfapirc`, `.cdsapirc`, `.netrc`, SSH keys, API tokens, or local `.env` files.

## Data Directories

The `data/` directory is a local staging area. Its subdirectories may be created locally as needed, but large contents should remain untracked.

Recommended local layout:

```text
data/
  raw/
  interim/
  processed/
  external/
```

The `outputs/` directory is for generated local products. Its contents should be regenerable from documented inputs and workflows.

## Provenance Expectations

For each dataset used in the project, document:

- Provider and product name.
- Version or access date.
- Spatial and temporal coverage.
- Native resolution and units.
- License or access constraints.
- Processing steps needed to regenerate derived products.

## Publication Reproducibility

For article submission, the repository should contain enough documentation to reproduce the computational logic even when raw data are hosted externally or must be downloaded from controlled-access providers.

## Credential Policy

The shared AITCHazard container must contain dependencies and code only. Credentials remain on the host and are supplied at runtime by read-only mounts or environment variables.

Allowed credential handles are documented in `containers/README.md`. Scripts may check whether handles exist, but they must not print token values or credential file contents.

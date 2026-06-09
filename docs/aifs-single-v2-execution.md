# AIFS Single v2 Execution

This document records the first executable Block 1 path for AITCHazard Mexico.

## Current Scope

The implemented path is smoke-first:

- uses `ecmwf/aifs-single-2.0` as the canonical checkpoint identifier;
- validates the Mexico domain and `0..72 h` lead-time contract;
- generates a tiny deterministic synthetic dataset;
- derives `tp_6h`, `cp_6h`, and `ws10`;
- writes a canonical Block 1 NetCDF;
- converts that output to the SwAIther-compatible low-resolution interface;
- runs without MARS, GPU, network access, or credentials.

Real AIFS Single v2 inference is intentionally guarded. It validates credential handles and imports the Anemoi runner boundary, then stops before MARS retrieval and inference until the production input-state builder is implemented.

## Canonical Commands

Run Block 1 smoke mode:

```bash
python scripts/block1/run_aifs_single_v2.py \
  --config conf/aitchazard_mexico/block1_aifs_single_v2.yaml \
  --mode smoke
```

Prepare SwAIther-compatible inputs:

```bash
python scripts/block1/prepare_swaither_inputs.py \
  --input outputs/block1_smoke.nc \
  --output outputs/swaither_inputs_smoke.nc
```

Check credential handles safely:

```bash
python scripts/check_credentials.py --profile mars
```

## Curnagl/UNIL Container Path

The Apptainer definition is `containers/aitchazard_aifs.def`. It is designed for a shared container pattern: -- This need to change on talk with Flavio

- bind the repository into `/ws`;
- bind `/users`, `/scratch`, and `/work`;
- mount credentials read-only only when real mode is needed;
- keep all large outputs in local scratch/work paths;
- never bake secrets into the image.

See `containers/README.md` and `workflows/slurm/` for build and job examples.

## External Technical Notes

ECMWF documents that AIFS deterministic forecasts are produced four times per day, with 6-hourly time steps, and that historical AIFS Single data are available through archive/MARS for registered users. The Hugging Face model card for `ecmwf/aifs-single-2.0` states that AIFS Single v2 receives atmospheric states at `t-6 h` and `t0` and produces `t+6 h` forecasts. These details motivate the repository's `t-6h/t0`, 6-hour output, and MARS-guarded design.

References:

- [`ecmwf/aifs-single-2.0`](https://huggingface.co/ecmwf/aifs-single-2.0)
- [ECMWF AIFS Machine Learning data](https://www.ecmwf.int/en/forecasts/dataset/aifs-machine-learning-data)
- [Implementation of AIFS Single v2](https://confluence.ecmwf.int/display/FCST/Implementation%2Bof%2BAIFS%2BSingle%2Bv2)

## Open Work

- Implement the MARS input-state builder for retrospective cases.
- Decide cache layout for retrieved initial states on Curnagl.
- Add real-mode integration tests once credentials and access permissions are available.
*- Validate container build on Curnagl modules and adjust CUDA/PyTorch versions if cluster policy requires it.
*
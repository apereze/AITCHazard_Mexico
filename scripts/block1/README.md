# Block 1 Scripts

This directory will contain cleaned command-line scripts for Block 1: retrospective AIFS Single v2 forecasting over the Mexico domain.

Current status:

- `legacy/` preserves the initial prototype scripts added to the repository.
- The legacy scripts are useful references, but they are not yet production Block 1 entry points.
- New scripts should call tested utilities from `src/aitchazard/block1/` instead of duplicating constants, variable lists, or post-processing logic.

## Current Entry Points

Run smoke mode:

```bash
python scripts/block1/run_aifs_single_v2.py \
  --config conf/aitchazard_mexico/block1_aifs_single_v2.yaml \
  --mode smoke
```

Convert Block 1 smoke output to the SwAIther-compatible low-resolution interface:

```bash
python scripts/block1/prepare_swaither_inputs.py \
  --input outputs/block1_smoke.nc \
  --output outputs/swaither_inputs_smoke.nc
```

`--mode real` is present only as a guarded boundary. It checks credentials and Anemoi imports, then stops before launching MARS or production inference.

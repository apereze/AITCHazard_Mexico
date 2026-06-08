# Block 1 Prototype Code Audit

This audit summarizes the initial Block 1 programs added in commit `cc18588`.

## Overall Assessment

The prototype files are useful because they demonstrate existing experiments with Anemoi inference, AIFS-style input states, MARS retrieval attempts, S3/Zarr datasets, NetCDF writing, and SLURM execution. They should not yet be treated as the production Block 1 implementation.

## Main Alignment Gaps

- The current project target is AIFS Single v2 (`ecmwf/aifs-single-2.0`), while the prototype runners use `ecmwf/aifs-ens-1.0`.
- The target forecast horizon is `t0` to `t+72 h`, while the runners default to `120 h`.
- The target output frequency is 6-hourly; this is broadly consistent, but the scripts should expose it explicitly.
- The target domain is Mexico (`5N-35N`, `130W-60W`), while the runners write global 0.25 degree grids.
- The target output is standardized regional NetCDF, while the prototypes use multiple output layouts and variable subsets.
- The target input strategy is MARS-based retrospective inference, while the prototypes mix S3/Zarr access, partial MARS retrieval, and debug pickle loading.
- The target downstream precipitation interface requires `tp_6h` and optionally `cp_6h`, but interval precipitation is not yet formalized in the runners.

## File-Level Notes

- `scripts/block1/legacy/date_maker.py`: useful case scheduling sketch, but it hard-codes IBTrACS paths, filters only recent years, overrides years manually, runs only `00` and `12` UTC, and launches a hard-coded AIFS-ens script path.
- `scripts/block1/legacy/state_runner.py`: useful Anemoi/S3 inference reference, but it runs AIFS-ens, writes one file per member, uses global output, and does not implement the official Block 1 schema.
- `scripts/block1/legacy/state_runner_altCDF.py`: useful reference for writing all members into one NetCDF file, but it still uses AIFS-ens/S3/global output and a limited saved-variable list.
- `scripts/block1/legacy/state_runner_altMars.py`: closest conceptual reference for MARS retrieval, but debug mode bypasses real MARS access and the checkpoint/output assumptions remain AIFS-ens oriented.
- `scripts/block1/legacy/state_runner_ERA5.py`: close to the S3 runner pattern and should be treated as a reference variant rather than a separate production path.
- `workflows/slurm/legacy/*.slurm`: useful HPC examples, but currently hard-code paths, container names, logs, and personal directories.

## Alignment Decisions Applied

- Legacy prototype scripts were moved under `scripts/block1/legacy/`.
- Legacy SLURM files were moved under `workflows/slurm/legacy/`.
- Shared Block 1 constants and post-processing helpers were introduced under `src/aitchazard/block1/`.
- Tests were added for project constants, interval precipitation derivation, negative accumulation reset clipping, and `ws10`.

## Recommended Next Refactor

Build a new production runner instead of editing the legacy scripts in place:

1. Define a config object or YAML file for date, domain, lead times, paths, checkpoint, and output naming.
2. Implement case scheduling from IBTrACS without hard-coded year overrides.
3. Implement a MARS input-state builder for `t-6 h` and `t0`.
4. Run AIFS Single v2 with explicit device selection.
5. Crop to the Mexico domain before writing.
6. Write standardized NetCDF files with `init_time`, `lead_time`, `valid_time`, `latitude`, and `longitude`.
7. Apply `tp_6h`, `cp_6h`, and `ws10` derivations through tested utilities.

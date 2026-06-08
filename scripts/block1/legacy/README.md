# Legacy Block 1 Prototypes

These files are preserved as working prototypes for AIFS inference experiments.

They are intentionally kept separate from production scripts because they currently mix several approaches:

- AIFS-ens checkpoints rather than the project target of AIFS Single v2.
- S3/Zarr input paths, MARS retrieval logic, and debug pickle loading.
- Hard-coded HPC paths and personal scratch directories.
- Multiple NetCDF writing strategies.
- Forecast horizons and ensemble assumptions that differ from the current Block 1 design.

The next refactor should extract reusable ideas from these files into small, tested modules under `src/aitchazard/block1/`.

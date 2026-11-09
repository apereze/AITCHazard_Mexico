# Changelog

## [0.2.0] - 2026-11-08

Block 1 validated on Curnagl; repository cleaned and aligned with ITCHI.

### Added
- `notebooks/02_block1_benchmark_un_dia.ipynb`: one-day benchmark (time, RAM, VRAM,
  output volume, extrapolation to the campaign, diagnostics of t0 and precipitation).
- `scripts/block1/bench_preflight.py`: environment checks and staging of checkpoint, ERA5
  day and regridding matrices.
- `scripts/block1/plot_case.py`: TC case figures against IBTrACS.
- `src/aitchazard/block1/regrid.py` and `tests/block1/test_regrid.py`: batched box regridding
  with the earthkit-regrid matrices (52 s → 12.6 s per forecast).
- `slurm/block1_bench_day.slurm`, `slurm/jupyter_gpu.slurm`.
- Documentation: framework with diagram and data contracts, decision log, block documents,
  Curnagl guide, results of 2026-11-08, presentation material.
- `conf/aitchazard_mexico/hazard_tracking_wind.yaml` (design).

### Changed
- `ERA5Local` interpolates all fields of an analysis time in one sparse product.
- Block 1 configuration: absolute paths on /work, AIFS 1.1 environment, per-step
  precipitation, proposed SLURM resources.
- Block 2 configuration: MSWEP V3.16 6 h target, INEGI DEM, AIFS 1.1, leads 6–72 h.
- `scripts/block1/download_era5.py` moved out of `legacy/`; Jupyter job moved to `slurm/`
  and switched to the AIFS 1.1 environment.

### Removed
- AIFS Single v2 material (notebooks, configuration, execution notes, container recipe).
- Legacy prototypes (`scripts/block1/legacy/`, `workflows/`), unused `variables.py`,
  outdated documents (`methodology.md`, `project-context.md`, separate schema and
  interface notes, now merged into the block documents).

Everything removed is still in the Git history before this version (tag `pre-cleanup`).

## [0.1.0] - 2026-06

Initial structure, Block 1 calendar, ERA5 reader and CDS parameters, AIFS v2 prototypes.

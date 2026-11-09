# Notebooks

| Notebook | Purpose |
|---|---|
| `02_block1_benchmark_un_dia.ipynb` | One-day Block 1 benchmark: 4 cycles × 72 h, time/RAM/VRAM per phase, output volume, extrapolation to the campaign, diagnostics (t0, tcc/cp, precipitation per step), batched-regridding check. Run with `slurm/block1_bench_day.slurm`; day with `BENCH_DAY` |

The executed copy is written to `logs/` and its results to
`/work/.../apereze/benchmarks/block1/<YYYYMMDD>_<JOB_ID>/`. Earlier AIFS v2 and prototype
notebooks are in the Git history (tag `pre-cleanup`).

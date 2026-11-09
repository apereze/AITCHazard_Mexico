# SLURM jobs (Curnagl)

| Job | Purpose |
|---|---|
| `block1_bench_day.slurm` | Runs notebook 02 headless on one GPU; `sbatch --export=BENCH_DAY=YYYY-MM-DD ...` for another day |
| `jupyter_gpu.slurm` | Jupyter server in the AIFS 1.1 environment; prints the SSH tunnel command |

Both use `aifs_single_v2_era5.sif` with `PYTHONPATH=$BASE/aifs/pylibs/aifs11`, bind `/work`
and `export SLURM_EXPORT_ENV=ALL` after `module load` (needed with `--export=NONE`).
Logs go to `logs/` (ignored by Git). Commands: `docs/curnagl-guide.md`.

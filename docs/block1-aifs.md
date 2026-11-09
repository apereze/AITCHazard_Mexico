# Block 1 · AIFS Single v1.1 hindcasts initialised from ERA5

Last updated: 2026-11-08. Status: environment validated and one-day benchmark done;
production runner and campaign pending.

## Design

| Item | Value |
|---|---|
| Model | AIFS Single v1.1, `ecmwf/aifs-single-1.1`, checkpoint `aifs-single-mse-1.1.ckpt` (253 M parameters) |
| Initial conditions | ERA5 via CDS API at t−6 h and t0, 0.25° → N320 |
| Period | May–November, 2000–2025 |
| Cycles | 00, 06, 12, 18 UTC: 22 256 forecasts in 182 year-month tasks (~122 per task) |
| Horizon | 0–72 h every 6 h (12 model steps + t0) |
| Execution | Global N320; regridding to 0.25° and cropping at the end |
| Regional domain | 5–35°N, 230–300°E: `tp cp tcc 10u 10v q_500 q_850 t_500 t_850 z_500 z_850` |
| Extended domain | −5–45°N, 220–310°E: `msl 10u 10v z_300 z_500` |
| Static fields | `zs = z_sfc/g` (m) and `lsm`, once per domain |

## Conventions

- `z` in m² s⁻² (the TempestExtremes thickness threshold of −58.8 m² s⁻² assumes it).
- `10u`/`10v` are written as `u10`/`v10` in NetCDF.
- `tp` and `cp` are **per 6 h step** (m), not accumulated from t0: the benchmark found
  the domain mean at 72 h equal to the mean at 6 h (ratio 0.94 and 1.00), against ~12
  for an accumulation. No differencing is needed.
- `runner.run` does not yield t0; t0 is the ERA5 state regridded with the same weights.
  `tp`, `cp` and `tcc` are NaN at t0.
- Precipitation at valid time T covers (T−6 h, T], the same window as the MSWEP 6 h product.

## Environment (Curnagl)

The AIFS 1.1 checkpoint stores the whole pickled model. It references
`torch_geometric.nn.conv.utils.inspector`, which no longer exists in recent
`torch_geometric`, and classes of `anemoi-models` 0.4/0.5. It **does not load** with the
anemoi-models 0.9.3 shipped in the container. The training provenance stored in the
checkpoint metadata (`provenance_training`) gives: Python 3.12.1, torch 2.6.0+cu124,
torch_geometric 2.4.0, anemoi.models 0.4.2.post64, anemoi.utils 0.4.22.

Working environment:

| Component | Path / version |
|---|---|
| Container | `/work/FAC/FGSE/IDYST/tbeucler/default/apereze/aifs/aifs_single_v2_era5.sif` (torch 2.7.0, flash-attn 2.7.4.post1, earthkit-regrid 0.5.1, cdsapi 0.7.7) |
| Overlay | `.../apereze/aifs/pylibs/aifs11`, passed as `--env PYTHONPATH=...`: torch_geometric 2.4.0, anemoi-models 0.5.0, anemoi-inference 0.6.3 |
| Checkpoint | `.../apereze/aifs/checkpoints/aifs-single-mse-1.1.ckpt` |
| Module | `apptainer/1.4.1` (software stack 20260114) |

Re-create the overlay with:

```bash
apptainer exec --bind /work $SIF python -m pip install --no-deps --target $BASE/aifs/pylibs/aifs11 \
    torch_geometric==2.4.0 anemoi-models==0.5.0 anemoi-inference==0.6.3
```

**Pending:** freeze this environment into a definition file in `containers/` before the
campaign (see `containers/README.md`).

## Regridding

`src/aitchazard/block1/regrid.py` takes the sparse matrices of `earthkit-regrid`
(`earthkit.regrid.db.find`), keeps only the rows of the output box and applies them to
all fields in one product. It is used in both directions:

- ERA5 inputs, 0.25° → N320 (`ERA5Local.read_time`, ~95 fields per analysis time);
- AIFS outputs, N320 → 0.25° in the bounding box of the two domains.

The notebook checks both paths against `earthkit.regrid.interpolate` in cycle 0; the
maximum relative difference was 0.0.

## Benchmark (2005-05-15, A100 40 GB)

| Quantity | Before (job 20308990) | Batched regridding (job 20309047) |
|---|---|---|
| Wall time per forecast | 52 s (CV 7.4 %) | **12.6 s** (CV 1.7 %) |
| AIFS inference | 0.84 s per step | 0.80 s per step |
| Regridding and cropping | 2.3 s per step | 0.05 s per step |
| Mean GPU utilisation | 15 % | 44 % |
| Fixed cost per task | 33 s | 17 s |
| Longest task (one month) | 1.8 h | 0.44 h |
| Campaign GPU-h (with 30 % margin) | 325 (420) | **79 (103)** |
| Peak VRAM | 21 GiB | 21 GiB |
| Peak RAM | 4.0 GiB | 5.6 GiB |

Storage: 23 MB per forecast (`split`) or 29 MB (`single`), compressed to ~60 %. Total
0.51 TB (`split`) or 0.65 / 0.72 / 0.79 TB (`single` with the eastern edge at 310 / 320 /
330°E). ERA5: 199 MB per analysis time, 4.4 TB for 22 282 times if kept, ~25 GB per month
on disk at a time. `complevel` 1 and 4 give the same size; 9 triples the write time.

Proposed resources per year-month task:

```bash
#SBATCH --partition=gpu --gres=gpu:1 --cpus-per-task=2 --mem=16G --time=01:00:00 --array=0-181
```

The margin covers reading a full monthly GRIB, which the benchmark (one-day GRIB) did not
measure. Run one month as a pilot first.

Notes:

- Run-to-run differences of ~0.1 mm in the precipitation maxima come from non-deterministic
  GPU kernels, not from the regridding.
- The precipitation maximum per step drops from 100 mm at +6 h to ~30 mm at +72 h on the
  benchmark day; consistent with MSE smoothing, not conclusive with one day.

Full results and the Emily case: [`results/2026-11-08_block1_benchmark_emily.md`](results/2026-11-08_block1_benchmark_emily.md).

## How to run

Step-by-step commands for Curnagl: [`curnagl-guide.md`](curnagl-guide.md).

| Step | Command (repository root on Curnagl) |
|---|---|
| Preflight (login node) | `apptainer exec --bind /work --env PYTHONPATH=$PYLIBS $SIF python scripts/block1/bench_preflight.py --base $BASE --day 2005-05-15 --try-load` |
| One-day benchmark (GPU) | `sbatch [--export=BENCH_DAY=YYYY-MM-DD] slurm/block1_bench_day.slurm` |
| Case figures | `apptainer exec --bind /work $SIF python scripts/block1/plot_case.py --run-dir ... --ibtracs ... --name EMILY --season 2005` |
| Monthly ERA5 download | `scripts/block1/download_era5.py --config conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml --year YYYY [--dry-run]` |

## Pending before the campaign

1. Production runner `scripts/block1/run_aifs_month.py` (one year-month task, logic of
   notebook 02, skips finished forecasts, writes a manifest) and its SLURM array.
2. ERA5 download array (CPU) ahead of the GPU array.
3. Container definition file for the AIFS 1.1 environment.
4. Decisions O1–O5 in [`decisions.md`](decisions.md).
5. TempestExtremes read test on one extended file (does it accept `lead_time` as the
   time dimension?).

## Methodological caveats

- **In-sample years.** AIFS 1.1 was pre-trained on ERA5 1979–2022 and fine-tuned with
  rollout up to 72 h on operational analyses 2016–2022
  ([Moldovan et al. 2026](https://doi.org/10.5194/gmd-19-4703-2026)). Only 2023–2025 are
  out of sample.
- **Initial-condition shift.** ERA5 at 0.25° holds weak TC vortices (Emily 2005: ~990 hPa
  at t0 versus 929 hPa in IBTrACS). Operational analyses at higher resolution will start
  from stronger vortices, so corrections calibrated on these hindcasts may over-correct
  in operations.

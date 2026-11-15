# Block 1 pilot: May 2023 production task and TempestExtremes check

Run 2026-11-12 on Curnagl; ERA5 download rates added 2026-11-15.
Context: `docs/meetings/2026-11-16_block1_campaign.md`, decisions D13-D16 in `docs/decisions.md`.

## Production task (array task 161, job 20478945)

| Quantity | Value |
|---|---|
| Forecasts | 124/124 written (00/06/12/18 UTC, 1-31 May 2023), 0 failed, 0 NaN or range issues |
| Files | 248 (regional + tempest per initialisation), 2.7 GB |
| Wall time | 27 min |
| Time per forecast | 12.95 s median; first forecast of the task about 50 s |
| Peak RSS / peak reserved VRAM | 5.7 GiB / 20.7 GiB (A100 40 GB, 2 CPUs, 16 GB requested) |
| Resume | the task resumed correctly after a 2-forecast smoke test |

The checkpoint is loaded lazily by `SimpleRunner`, so the former `load_checkpoint_s`
measured only the constructor. From this commit the manifest stores `runner_init_s`
(constructor) and `first_forecast_s` (first forecast of the task, including the checkpoint
load and CUDA warm-up).

Consequence for the array: `#SBATCH --time=01:00:00` (about 2x the 31-day wall time).

## TempestExtremes (D14)

Commit `cafb070`, built with the NetCDF path embedded in the executables (no modules at run
time). `DetectNodes` on the 72 h AIFS forecast of Emily 2005 detects the storm at all 13
output times. Spurious candidates appear on the stored domain boundary; requiring candidates
at least 6.5 deg (largest closed-contour radius) inside the domain removes them (O3).

## ERA5 download from the CDS (June-November 2023)

Sequential `download_era5.py` for June-November (tmux session `era5_2023`, started
2026-11-12 23:25 Curnagl time). One request per group in the order sfc, pl, soil
(`GROUP_PARAMS`):

| Month | sfc | pl | soil | Total (min) |
|---|---|---|---|---|
| 2023-06 | 4:16 | 20:44 | 1:30 | 26.5 |
| 2023-07 | 6:29 | 17:07 | 1:00 | 24.6 |
| 2023-08 | 3:27 | 40:36 | 3:02 | 47.1 |
| 2023-09 | 9:06 | 29:17 | 2:12 | 40.6 |
| 2023-10 | 5:43 | 22:47 | 1:28 | 30.0 |
| 2023-11 | 4:19 | 23:42 | 2:09 | 30.2 |

Mean 33 min per month (range 25-47 min), against about 55 min assumed in the meeting brief.
Extrapolated to 182 months: about 100 h sequential (about 145 h at the slowest month here).
The CDS remains the bottleneck relative to about 84 GPU hours, but by less than estimated.
Queue times on the CDS vary with load, so this is one night's sample, not a guarantee.
Volume: 23-24 GB per month, consistent with the pilot.

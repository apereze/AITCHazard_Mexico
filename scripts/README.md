# Scripts

| Script | Where it runs | Purpose |
|---|---|---|
| `block1/bench_preflight.py` | Login node, in the container | Versions, /work access, CDS credentials; downloads checkpoint, ERA5 of one day and regridding matrices; `--try-load` deserialises the checkpoint |
| `block1/download_era5.py` | CPU (login node or CPU job) | Monthly ERA5 GRIB for a season from the Block 1 YAML; idempotent; `--dry-run` |
| `block1/plot_case.py` | Login node, in the container | MSLP/wind and 6 h precipitation maps, track and intensity against IBTrACS for one case |

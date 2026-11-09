# Containers

Block 1 runs in `aifs_single_v2_era5.sif` (on Curnagl, `/work/.../apereze/aifs/`) plus an
overlay with the libraries that load the AIFS 1.1 checkpoint:

```bash
apptainer exec --bind /work --env PYTHONPATH=$BASE/aifs/pylibs/aifs11 $BASE/aifs/aifs_single_v2_era5.sif ...
```

Overlay: torch_geometric 2.4.0, anemoi-models 0.5.0, anemoi-inference 0.6.3 (installed with
`pip install --no-deps --target`). See `docs/block1-aifs.md`.

**Pending before the campaign:** add the recipe of the current image
(`apptainer inspect --deffile aifs_single_v2_era5.sif > containers/aifs_single_v2_era5.def`)
and a recipe `aifs_single_v1_1.def` that installs the overlay versions directly.

Containers never include credentials (`.cdsapirc`, tokens, SSH keys).

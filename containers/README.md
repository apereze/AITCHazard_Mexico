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

## Image checksums (sha256, 2026-11-12)

Chain: aifs-ens.sif (dawn_containers, outside this project) -> aifs_single_v2_era5.sif (+ PYTHONPATH overlay aifs11).

    eca036a2daf2e5728ae4a79661cf68462fb5dd540a2692b726bfdd0615a01898  /work/FAC/FGSE/IDYST/tbeucler/default/dawn_containers/AIFS/aifs-ens.sif
    4096278037da5169aa7291dbc0b6970f8bf67988eef46f27a5d36cbb56760dfe  /work/FAC/FGSE/IDYST/tbeucler/default/apereze/aifs/aifs_single_v2_era5.sif

Verify: sha256sum <path>. If aifs-ens.sif changes or disappears, aifs_single_v2_era5.def no longer rebuilds the same image; keep a copy of aifs_single_v2_era5.sif with the campaign outputs.

# AITCHazard AIFS Container

This directory contains the shared Apptainer/Singularity definition for running AITCHazard Block 1 on Curnagl/UNIL-style HPC environments.

The container includes code dependencies only. It must never contain MARS, ECMWF, CDS, Hugging Face, SSH, or other private credentials.

## Build

From the repository root:

```bash
module load gcc cuda apptainer
apptainer build aitchazard_aifs.sif containers/aitchazard_aifs.def
```

If the cluster requires a writable build cache:

```bash
export APPTAINER_CACHEDIR=/scratch/$USER/apptainer-cache
mkdir -p "$APPTAINER_CACHEDIR"
apptainer build "$AITCHAZARD_CONTAINER" containers/aitchazard_aifs.def
```

## Smoke Test

Smoke mode uses synthetic data and does not require GPU, MARS, or credentials:

```bash
export AITCHAZARD_REPO=/users/$USER/AITCHazard_Mexico
export AITCHAZARD_CONTAINER=/work/$USER/containers/aitchazard_aifs.sif

apptainer exec --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  "$AITCHAZARD_CONTAINER" \
  bash -lc "cd /ws && python -m pytest && python scripts/block1/run_aifs_single_v2.py --config conf/aitchazard_mexico/block1_aifs_single_v2.yaml --mode smoke"
```

Convert smoke output to the SwAIther-compatible interface:

```bash
apptainer exec --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  "$AITCHAZARD_CONTAINER" \
  bash -lc "cd /ws && python scripts/block1/prepare_swaither_inputs.py --input outputs/block1_smoke.nc --output outputs/swaither_inputs_smoke.nc"
```

## Interactive Session

```bash
apptainer shell --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  "$AITCHAZARD_CONTAINER"
```

Inside the container:

```bash
cd /ws
python scripts/check_credentials.py --profile mars
```

## Credentials

Credentials stay on the host and are mounted or passed at runtime.

Supported file handles:

- `$AITCHAZARD_CREDENTIALS_DIR/.ecmwfapirc`
- `$AITCHAZARD_CREDENTIALS_DIR/.cdsapirc`
- `$AITCHAZARD_CREDENTIALS_DIR/.netrc`
- `$HOME/.ecmwfapirc`
- `$HOME/.cdsapirc`
- `$HOME/.netrc`
- `$HOME/.config/earthkit/`

Supported environment variable handles:

- `ECMWF_API_URL`
- `ECMWF_API_KEY`
- `ECMWF_API_EMAIL`
- `CDSAPI_URL`
- `CDSAPI_KEY`
- `HF_TOKEN`

Example:

```bash
export AITCHAZARD_CREDENTIALS_DIR=/users/$USER/.aitchazard-credentials

apptainer exec --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  -B "$AITCHAZARD_CREDENTIALS_DIR:$AITCHAZARD_CREDENTIALS_DIR:ro" \
  "$AITCHAZARD_CONTAINER" \
  python /ws/scripts/check_credentials.py --profile mars --credentials-dir "$AITCHAZARD_CREDENTIALS_DIR"
```

`scripts/check_credentials.py` reports only which handles exist. It does not print tokens or file contents.

The image includes a minimal installed copy of the package for container self-tests. During normal work, bind the active repository to `/ws`; the CLI scripts prioritize `/ws/src` so collaborators can run the checked-out branch without rebuilding after every source edit.

## SLURM

Templates live in `workflows/slurm/`:

- `aifs_single_v2_smoke.slurm`: synthetic smoke test, no credentials required.
- `aifs_single_v2_real.slurm`: guarded real-mode template, credentials required.

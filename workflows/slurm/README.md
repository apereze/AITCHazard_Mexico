# SLURM Workflows

Future HPC job scripts for AITCHazard Mexico should live here.

Production SLURM scripts should use environment variables or documented configuration for:

- Repository path.
- Container path.
- Output path.
- Logs path.
- Forecast initialization date.
- Forecast horizon and output frequency.

## Current Templates

- `aifs_single_v2_smoke.slurm`: runs tests, Block 1 smoke mode, and SwAIther adapter conversion inside Apptainer. It does not require credentials.
- `aifs_single_v2_real.slurm`: guarded real-mode template. It requires `AITCHAZARD_CREDENTIALS_DIR` and stops early if credential handles are missing.

Required variables:

- `AITCHAZARD_REPO`
- `AITCHAZARD_CONTAINER`

Optional or mode-specific variables:

- `AITCHAZARD_OUTPUT_DIR`
- `AITCHAZARD_CONFIG`
- `AITCHAZARD_CREDENTIALS_DIR`

All templates bind `/users`, `/scratch`, and `/work` for Curnagl/UNIL-style shared execution.

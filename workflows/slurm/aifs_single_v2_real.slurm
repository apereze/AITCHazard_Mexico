#!/bin/bash
#SBATCH --job-name=aitchazard-aifs-real
#SBATCH --output=aifs_real_%j.out
#SBATCH --error=aifs_real_%j.err
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1

set -euo pipefail

module purge
module load gcc cuda apptainer

: "${AITCHAZARD_REPO:?Set AITCHAZARD_REPO to the repository path}"
: "${AITCHAZARD_CONTAINER:?Set AITCHAZARD_CONTAINER to the Apptainer image path}"
: "${AITCHAZARD_OUTPUT_DIR:=$AITCHAZARD_REPO/outputs}"
: "${AITCHAZARD_CONFIG:=conf/aitchazard_mexico/block1_aifs_single_v2.yaml}"
: "${AITCHAZARD_CREDENTIALS_DIR:?Set AITCHAZARD_CREDENTIALS_DIR to a host directory containing credential files}"

mkdir -p "$AITCHAZARD_REPO/logs" "$AITCHAZARD_OUTPUT_DIR"

apptainer exec --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  -B "$AITCHAZARD_CREDENTIALS_DIR:$AITCHAZARD_CREDENTIALS_DIR:ro" \
  "$AITCHAZARD_CONTAINER" \
  bash -lc "cd /ws && python scripts/check_credentials.py --profile mars --credentials-dir '$AITCHAZARD_CREDENTIALS_DIR' --require && python scripts/block1/run_aifs_single_v2.py --config '$AITCHAZARD_CONFIG' --mode real --output '$AITCHAZARD_OUTPUT_DIR/block1_real.nc' --credentials-dir '$AITCHAZARD_CREDENTIALS_DIR'"

#!/bin/bash
#SBATCH --job-name=aitchazard-aifs-smoke
#SBATCH --output=aifs_smoke_%j.out
#SBATCH --error=aifs_smoke_%j.err
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G

set -euo pipefail

module purge
module load gcc cuda apptainer

: "${AITCHAZARD_REPO:?Set AITCHAZARD_REPO to the repository path}"
: "${AITCHAZARD_CONTAINER:?Set AITCHAZARD_CONTAINER to the Apptainer image path}"
: "${AITCHAZARD_OUTPUT_DIR:=$AITCHAZARD_REPO/outputs}"
: "${AITCHAZARD_CONFIG:=conf/aitchazard_mexico/block1_aifs_single_v2.yaml}"

mkdir -p "$AITCHAZARD_REPO/logs" "$AITCHAZARD_OUTPUT_DIR"

apptainer exec --nv \
  -B /users,/scratch,/work \
  -B "$AITCHAZARD_REPO:/ws" \
  "$AITCHAZARD_CONTAINER" \
  bash -lc "cd /ws && python -m pytest && python scripts/block1/run_aifs_single_v2.py --config '$AITCHAZARD_CONFIG' --mode smoke --output '$AITCHAZARD_OUTPUT_DIR/block1_smoke.nc' && python scripts/block1/prepare_swaither_inputs.py --input '$AITCHAZARD_OUTPUT_DIR/block1_smoke.nc' --output '$AITCHAZARD_OUTPUT_DIR/swaither_inputs_smoke.nc'"

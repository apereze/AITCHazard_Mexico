#!/bin/bash -l

# Job general details
#SBATCH --job-name=AIFS_single_v2
#SBATCH --account=tbeucler_default
#SBATCH --mail-user=adolfo.perezestrada@unil.ch
#SBATCH --mail-type=NONE
#SBATCH --time=01:29:59

# Working directory and logs
#SBATCH --chdir=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico
#SBATCH --output=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/AIFSAPE-%j.out
#SBATCH --error=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/AIFSAPE-%j.err

# Resources
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=8G
#SBATCH --qos=dcsr
#SBATCH --partition=gpu

# Environment
#SBATCH --export=NONE

set -euo pipefail

module load apptainer/1.4.1

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MV2_ENABLE_AFFINITY=0
export SLURM_EXPORT_ENV=ALL

# Paths
PROJECT_DIR="/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico"
AIFS_DIR="/work/FAC/FGSE/IDYST/tbeucler/default/apereze/aifs"
CONTAINER="${AIFS_DIR}/aifs_single_v2.sif"

# Validate paths
if [[ ! -f "${CONTAINER}" ]]; then
    echo "ERROR: Container not found: ${CONTAINER}" >&2
    exit 1
fi

if [[ ! -d "${PROJECT_DIR}" ]]; then
    echo "ERROR: Repository not found: ${PROJECT_DIR}" >&2
    exit 1
fi

echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: $(hostname)"
echo "Container: ${CONTAINER}"
echo "Project: ${PROJECT_DIR}"
echo "Working directory: $(pwd)"

srun apptainer run \
    --nv \
    --bind "${PROJECT_DIR}:${PROJECT_DIR}" \
    --pwd "${PROJECT_DIR}" \
    --app jup-server \
    "${CONTAINER}"

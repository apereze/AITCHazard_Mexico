#!/bin/bash -l
# Block 1 campaign: one (year, month) per array task (scripts/block1/run_aifs_month.py).
# Usage (from the repo root):
#   sbatch --array=161 --time=00:20:00 --export=RUN_ARGS="--limit 2" slurm/block1_campaign.slurm  # smoke test
#   sbatch --array=161 slurm/block1_campaign.slurm                                                # pilot 2023-05
#   sbatch slurm/block1_campaign.slurm                                                            # full campaign
# Task id of a month: run_aifs_month.py --config ... --year-month YYYY-MM --dry-run

#SBATCH --job-name=b1_aifs
#SBATCH --account=tbeucler_default
#SBATCH --partition=gpu
#SBATCH --qos=dcsr
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --array=0-181%4
#SBATCH --chdir=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico
#SBATCH --output=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/b1_aifs-%A_%a.log
#SBATCH --export=NONE

set -uo pipefail
module load apptainer/1.4.1
export SLURM_EXPORT_ENV=ALL

BASE=/work/FAC/FGSE/IDYST/tbeucler/default/apereze
CONTAINER="${BASE}/aifs/aifs_single_v2_era5.sif"
CONFIG=conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

echo "job ${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID} on $(hostname), $(date)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

# RUN_ARGS (optional): extra runner arguments, e.g. "--limit 2"
srun apptainer exec --nv --bind /work --env PYTHONPATH="${BASE}/aifs/pylibs/aifs11" "${CONTAINER}" \
    python -u scripts/block1/run_aifs_month.py --config "${CONFIG}" --task-id "${SLURM_ARRAY_TASK_ID}" ${RUN_ARGS:-}
status=$?

sacct -j "${SLURM_JOB_ID}" --format=JobID,JobName%20,Elapsed,MaxRSS,AllocCPUS,TotalCPU,State
echo "end $(date), exit ${status}"
exit "${status}"

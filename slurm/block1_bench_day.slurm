#!/bin/bash -l
# Benchmark de un día del bloque 1 sin interfaz: ejecuta el notebook 02 y registra sacct.
# Uso (desde la raíz del repo): sbatch slurm/block1_bench_day.slurm

#SBATCH --job-name=b1_bench_day
#SBATCH --account=tbeucler_default
#SBATCH --partition=gpu
#SBATCH --qos=dcsr
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --chdir=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico
#SBATCH --output=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/b1_bench_day-%j.log
#SBATCH --export=NONE

set -euo pipefail
module load apptainer/1.4.1
export SLURM_EXPORT_ENV=ALL

BASE=/work/FAC/FGSE/IDYST/tbeucler/default/apereze
CONTAINER="${BASE}/aifs/aifs_single_v2_era5.sif"
NB=notebooks/02_block1_benchmark_un_dia.ipynb
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

echo "job ${SLURM_JOB_ID} en $(hostname), $(date)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

# Notebook ejecutado (con salidas) en logs/; resultados numéricos en ${BASE}/benchmarks/block1/
srun apptainer exec --nv --bind /work --env PYTHONPATH="${BASE}/aifs/pylibs/aifs11" "${CONTAINER}" \
    jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 \
    --output-dir logs --output "02_block1_benchmark_un_dia.${SLURM_JOB_ID}.ipynb" "${NB}"

sacct -j "${SLURM_JOB_ID}" --format=JobID,JobName%20,Elapsed,MaxRSS,AllocCPUS,TotalCPU,State
echo "fin $(date)"

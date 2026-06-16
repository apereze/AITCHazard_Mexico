#!/bin/bash -l

# ==============================================================================
# SLURM job: AIFS Single v2 Jupyter Server
#
# Purpose:
#   Start a Jupyter server inside the AIFS Single v2 Apptainer container
#   on a GPU node in Curnagl.
#
# Notes:
#   - Jupyter assigns the internal port automatically.
#   - Jupyter assigns the token automatically.
#   - No secondary raw log is created.
#   - The main SLURM log prints only the useful connection information.
# ==============================================================================


# ==============================================================================
# Job general details
# ==============================================================================

#SBATCH --job-name=AIFS_single_v2
#SBATCH --account=tbeucler_default
#SBATCH --mail-user=adolfo.perezestrada@unil.ch
#SBATCH --mail-type=NONE
#SBATCH --time=00:09:59


# ==============================================================================
# Working directory and logs
# ==============================================================================

#SBATCH --chdir=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico
#SBATCH --output=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/AIFSAPE-%j.log
#SBATCH --error=/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico/logs/AIFSAPE-%j.log


# ==============================================================================
# Resources
# ==============================================================================

#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=8G
#SBATCH --qos=dcsr
#SBATCH --partition=gpu-h100


# ==============================================================================
# Environment
# ==============================================================================

#SBATCH --export=NONE

set -euo pipefail


# ==============================================================================
# User configuration
# ==============================================================================

PROJECT_DIR="/work/FAC/FGSE/IDYST/tbeucler/default/apereze/repos/AITCHazard_Mexico"
AIFS_DIR="/work/FAC/FGSE/IDYST/tbeucler/default/apereze/aifs"
CONTAINER="${AIFS_DIR}/aifs_single_v2.sif"
LOG_DIR="${PROJECT_DIR}/logs"

# Local SSH alias defined in your local ~/.ssh/config
LOGIN_ALIAS="curnagl"

# Local port on your laptop or WSL.
LOCAL_PORT="8080"


# ==============================================================================
# Load required modules
# ==============================================================================

module load apptainer/1.4.1


# ==============================================================================
# Runtime environment
# ==============================================================================

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MV2_ENABLE_AFFINITY=0
export SLURM_EXPORT_ENV=ALL

export PROJECT_DIR
export AIFS_DIR
export CONTAINER


# ==============================================================================
# Prepare and validate paths
# ==============================================================================

mkdir -p "${LOG_DIR}"

if [[ ! -d "${PROJECT_DIR}" ]]; then
    echo "ERROR: Repository not found: ${PROJECT_DIR}" >&2
    exit 1
fi

if [[ ! -f "${CONTAINER}" ]]; then
    echo "ERROR: Container not found: ${CONTAINER}" >&2
    exit 1
fi


# ==============================================================================
# Job information
# ==============================================================================

COMPUTE_NODE="$(hostname)"
MAIN_LOG="${LOG_DIR}/AIFSAPE-${SLURM_JOB_ID}.log"

# Initial fallback IP.
# The preferred IP will be extracted from the Jupyter URL when available.
NODE_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

if [[ -z "${NODE_IP}" ]]; then
    NODE_IP="${COMPUTE_NODE}"
fi

echo
echo "=============================================================================="
echo " AIFS Single v2 Jupyter job"
echo "=============================================================================="
echo "Job ID:              ${SLURM_JOB_ID}"
echo "Job name:            ${SLURM_JOB_NAME}"
echo "Compute node:        ${COMPUTE_NODE}"
echo "Initial node IP:     ${NODE_IP}"
echo "Project directory:   ${PROJECT_DIR}"
echo "Container:           ${CONTAINER}"
echo "Working directory:   $(pwd)"
echo "Started at:          $(date)"
echo "Main log:            ${MAIN_LOG}"
echo "=============================================================================="
echo


# ==============================================================================
# Start Jupyter server using a FIFO
#
# Why FIFO?
#   It allows the script to read the Jupyter output, extract the real URL,
#   port and token, and suppress verbose Jupyter logs from the main SLURM log.
# ==============================================================================

cd "${PROJECT_DIR}"

JUPYTER_FIFO="/tmp/jupyter-${SLURM_JOB_ID}.fifo"

rm -f "${JUPYTER_FIFO}"
mkfifo "${JUPYTER_FIFO}"

echo "Starting Jupyter server inside container..."
echo

srun apptainer run \
    --nv \
    --bind "${PROJECT_DIR}:${PROJECT_DIR}" \
    --pwd "${PROJECT_DIR}" \
    --app jup-server \
    "${CONTAINER}" \
    > "${JUPYTER_FIFO}" 2>&1 &

SRUN_PID=$!


# ==============================================================================
# Cleanup
# ==============================================================================

cleanup() {
    echo
    echo "Stopping Jupyter server..."
    kill "${SRUN_PID}" 2>/dev/null || true

    if [[ -n "${DRAIN_PID:-}" ]]; then
        kill "${DRAIN_PID}" 2>/dev/null || true
    fi

    rm -f "${JUPYTER_FIFO}" 2>/dev/null || true

    wait "${SRUN_PID}" 2>/dev/null || true
    echo "Stopped at: $(date)"
}

trap cleanup EXIT TERM INT


# ==============================================================================
# Wait until Jupyter prints the URL with token
# ==============================================================================

echo "Waiting for Jupyter to generate its URL..."
echo

JUPYTER_URL=""
JUPYTER_PORT=""
JUPYTER_TOKEN=""

exec 3< "${JUPYTER_FIFO}"

for i in {1..120}; do

    if read -r -t 1 JUPYTER_LINE <&3; then

        if [[ "${JUPYTER_LINE}" =~ http://([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)/[^[:space:]]*token=([^[:space:]]+) ]]; then
            NODE_IP="${BASH_REMATCH[1]}"
            JUPYTER_PORT="${BASH_REMATCH[2]}"
            JUPYTER_TOKEN="${BASH_REMATCH[3]}"
            JUPYTER_URL="${JUPYTER_LINE}"
            break
        fi

        if [[ "${JUPYTER_LINE}" =~ http://127\.0\.0\.1:([0-9]+)/[^[:space:]]*token=([^[:space:]]+) ]]; then
            JUPYTER_PORT="${BASH_REMATCH[1]}"
            JUPYTER_TOKEN="${BASH_REMATCH[2]}"
            JUPYTER_URL="${JUPYTER_LINE}"
            break
        fi

    fi

done

exec 3<&-


# ==============================================================================
# Validate extracted Jupyter information
# ==============================================================================

if [[ -z "${JUPYTER_PORT}" || -z "${JUPYTER_TOKEN}" ]]; then
    echo "ERROR: Jupyter URL with token was not detected."
    echo
    echo "Possible causes:"
    echo "  - Jupyter did not start correctly."
    echo "  - The container app changed the URL format."
    echo "  - The job ended before Jupyter printed the token."
    echo
    echo "Check job state with:"
    echo
    echo "  sacct -j ${SLURM_JOB_ID} --format=JobID,JobName,State,ExitCode,Elapsed"
    echo
    exit 1
fi


# ==============================================================================
# Keep draining Jupyter output silently
#
# This prevents the FIFO from blocking while keeping the main log clean.
# ==============================================================================

cat "${JUPYTER_FIFO}" > /dev/null &
DRAIN_PID=$!


# ==============================================================================
# Build connection commands
# ==============================================================================

LOCAL_URL="http://127.0.0.1:${LOCAL_PORT}/?token=${JUPYTER_TOKEN}"

SSH_TUNNEL_COMMAND="ssh -n -N -L ${LOCAL_PORT}:${NODE_IP}:${JUPYTER_PORT} ${LOGIN_ALIAS}"


# ==============================================================================
# Clean connection summary
# ==============================================================================

echo
echo "=============================================================================="
echo " AIFS Single v2 Jupyter connection information"
echo "=============================================================================="
echo "Job ID:              ${SLURM_JOB_ID}"
echo "Job name:            ${SLURM_JOB_NAME}"
echo "Compute node:        ${COMPUTE_NODE}"
echo "Node IP:             ${NODE_IP}"
echo "Project directory:   ${PROJECT_DIR}"
echo "Container:           ${CONTAINER}"
echo "Working directory:   $(pwd)"
echo "Jupyter node port:   ${JUPYTER_PORT}"
echo "Local port:          ${LOCAL_PORT}"
echo "Jupyter token:       ${JUPYTER_TOKEN}"
echo "Started at:          $(date)"
echo "=============================================================================="
echo
echo "Run this command from your LOCAL computer or WSL terminal:"
echo
echo "ssh -n -N -L ${LOCAL_PORT}:${NODE_IP}:${JUPYTER_PORT} ${LOGIN_ALIAS}"
echo
echo "For VS Code:"
echo "  Command Palette > Jupyter: Select Jupyter Server > Existing"
echo "  Paste:"
echo "  ${LOCAL_URL}"
echo
echo "Keep this SLURM job running while using the notebook."
echo "=============================================================================="
echo


# ==============================================================================
# Keep the job alive while Jupyter is running
# ==============================================================================

wait "${SRUN_PID}"
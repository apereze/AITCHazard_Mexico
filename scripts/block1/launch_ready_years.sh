#!/bin/bash
# Submit the Block 1 AIFS array of every year whose ERA5 download is complete and that was not submitted yet.
# A year is ready when $BASE/data/era5/<year>/.complete exists (written by download_era5_years.sh); after
# submission, $BASE/data/era5/<year>/.submitted holds the Slurm job id. Years with an existing regional output
# directory are skipped (the runner would skip those forecasts anyway).
# Usage (login node): bash scripts/block1/launch_ready_years.sh            # one pass
#   tmux new -d -s aifs_launch "source ~/.aitchazard_env; bash -c 'while true; do bash $REPO/scripts/block1/launch_ready_years.sh; sleep 1800; done' 2>&1 | tee -a $BASE/logs/aifs_launch.log"
source ~/.aitchazard_env
set -uo pipefail
cd "$REPO"
for Y in $(seq 2000 2022); do
  D=$BASE/data/era5/$Y
  [ -f "$D/.complete" ] || continue
  [ -f "$D/.submitted" ] && continue
  if [ -d "$BASE/outputs/block1/regional/$Y" ]; then
    echo "$(date '+%F %T') $Y: regional/$Y exists, skipped"; continue
  fi
  T0=$((7 * (Y - 2000))); T1=$((T0 + 6))
  J=$(sbatch --parsable --array=${T0}-${T1}%4 slurm/block1_campaign.slurm) || { echo "$(date '+%F %T') $Y: sbatch failed"; continue; }
  echo "$J" > "$D/.submitted"
  echo "$(date '+%F %T') $Y: submitted job $J (tasks $T0-$T1)"
done

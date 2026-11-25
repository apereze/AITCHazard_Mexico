#!/bin/bash
# Download ERA5 initial conditions for several years, one full year per call to download_era5.py.
# A year is skipped when $BASE/data/era5/<year>/.complete exists; the marker is written only after a clean exit
# with the 21 GRIB files (May-November x sfc, pl, soil).
# Do not call download_era5.py with --months for a single month: it also writes the preceding month's block.
# Usage (login node, inside tmux, after `source ~/.aitchazard_env; module load apptainer/1.4.1`):
#   bash scripts/block1/download_era5_years.sh 2005 2010 2013
source ~/.aitchazard_env
set -uo pipefail
command -v apptainer >/dev/null || { echo "apptainer not found: module load apptainer/1.4.1"; exit 1; }
CONF=conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml
mkdir -p "$BASE/logs/era5"
cd "$REPO"
for Y in "$@"; do
  if [ -f "$BASE/data/era5/$Y/.complete" ]; then echo "$Y: already complete, skipped"; continue; fi
  LOG=$BASE/logs/era5/${Y}_$(date +%Y%m%dT%H%M).log
  echo "$(date '+%F %T') $Y: start -> $LOG"
  apptainer exec --bind /work --env PYTHONPATH="$REPO/src" "$SIF" \
    python -u scripts/block1/download_era5.py --config "$CONF" --year "$Y" > "$LOG" 2>&1
  rc=$?
  n=$(ls "$BASE"/data/era5/"$Y"/{05,06,07,08,09,10,11}/{sfc,pl,soil}.grib 2>/dev/null | wc -l)
  if [ "$rc" -eq 0 ] && [ "$n" -eq 21 ]; then
    date '+%F %T' > "$BASE/data/era5/$Y/.complete"
    echo "$(date '+%F %T') $Y: done ($(du -sh "$BASE/data/era5/$Y" | cut -f1))"
  else
    echo "$(date '+%F %T') $Y: FAILED (exit $rc, $n/21 files) -- see $LOG"
  fi
done

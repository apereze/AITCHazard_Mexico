#!/bin/bash
# DetectNodes + StitchNodes on every Block 1 tempest file of one month (one forecast per file).
# Parameters: TCBench table 2 (docs/tracking-tcbench.md, D10); range, maxgap and the wind
# threshold are provisional until checked in the TCBench track_processing code.
# Candidates kept >= 6.5 deg inside the stored domain -5..45 N, 220..310 E (O3).
# Usage (CPU node): bash scripts/tracking/te_month.sh 2023 05
source ~/.aitchazard_env
set -euo pipefail
Y=$1; M=$2
IN=$BASE/outputs/block1/tempest/$Y/$M
OUT=$BASE/outputs/tracking/te_tcbench/$Y/$M
BIN=${TE:-$BASE/software/tempestextremes}
[ -x "$BIN/bin/DetectNodes" ] && BIN=$BIN/bin
mkdir -p "$OUT"
n=0
for f in "$IN"/aifs11_tempest_*.nc; do
  b=$(basename "$f" .nc); n=$((n + 1))
  "$BIN/DetectNodes" --in_data "$f" --out "$OUT/${b}_nodes.txt" --regional \
    --latname latitude --lonname longitude --searchbymin msl \
    --closedcontourcmd "msl,200.0,6.5,0;_DIFF(z_300,z_500),-58.8,5.5,1.0" \
    --mergedist 6.0 --outputcmd "msl,min,0;_VECMAG(u10,v10),max,2" \
    --minlat 1.5 --maxlat 38.5 --minlon 226.5 --maxlon 303.5 > "$OUT/${b}_dn.log" 2>&1
  "$BIN/StitchNodes" --in "$OUT/${b}_nodes.txt" --out "$OUT/${b}_tracks.txt" \
    --in_fmt "lon,lat,msl,wind" --range 5.0 --mintime 3 --maxgap 0 \
    --threshold "wind,>=,10.0,1" > "$OUT/${b}_sn.log" 2>&1
done
# First point of every track: init, lon, lat, msl (Pa), wind (m/s), valid date
awk '/^start/{getline; split(FILENAME, a, "aifs11_tempest_"); print substr(a[2], 1, 10), $3, $4, $5, $6, $7"-"$8"-"$9"_"$10}' \
  "$OUT"/*_tracks.txt > "$OUT/first_points.txt" || true
ntr=$(wc -l < "$OUT/first_points.txt")
nfc=$(cut -d' ' -f1 "$OUT/first_points.txt" | sort -u | wc -l)
echo "$Y-$M: $n forecasts | $nfc with >= 1 track | $ntr tracks | detail: $OUT/first_points.txt"
